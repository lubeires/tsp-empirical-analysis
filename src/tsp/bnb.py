"""Branch-and-Bound exato para o TSP (D9, D10, D20).

- Busca em profundidade (DFS) recursiva a partir do vértice 0 (fixar o início
  elimina as n rotações equivalentes de cada rota).
- Filhos do mais próximo ao mais distante do último vértice do caminho.
- Limite inferior de Held-Karp adaptado a caminhos parciais (ver `lower_bound`
  e `held_karp_bound`). Com penalidades π = 0 ele é o limite 1-tree simples
  da T11; o subgradiente ajusta π para fortalecê-lo (T12).
- Prazo absoluto (`deadline`, em perf_counter): o tempo da heurística de
  warm-start, rodada antes, conta dentro do limite de 30 min (P2).

Contagem de nós (T11): para cada filho candidato calcula-se o limite inferior;
se LB >= limite superior atual, o filho é PODADO; senão, é EXPANDIDO e a busca
desce nele. A raiz conta como expandida. Folhas (rota completa) que melhoram o
limite superior também contam como expandidas.
"""

import math
import time
from dataclasses import dataclass, field

import numpy as np

from tsp.distance import tour_cost
from tsp.instrument import Profiler
from tsp.mst import prim

# Subgradiente (T12, D21): muitas iterações na raiz, poucas nos demais nós,
# que herdam as penalidades do pai e já partem de um ponto bom.
ROOT_ITERATIONS = 300
NODE_ITERATIONS = 10
DELTA = 0.15        # alvo do passo = (1 + DELTA) x melhor LB (não usa o limite superior)
ROOT_LAMBDA = 2.0   # multiplicador inicial do passo na raiz
NODE_LAMBDA = 0.05  # multiplicador nos demais nós (ajustado na T12: platô entre 0,02 e 0,05)
HALVE_EVERY = 30    # o multiplicador cai pela metade a cada HALVE_EVERY iterações

# Tolerância para arredondar o limite para cima com segurança (ver `_prunes`)
_EPS = 1e-6


@dataclass
class BnBResult:
    tour: list[int]
    cost: int
    optimal: bool = False             # False se parou por timeout
    nodes_expanded: int = 0
    nodes_pruned: int = 0
    max_depth: int = 0                # maior número de vértices num caminho parcial
    ub_improvements: int = 0          # quantas vezes o limite superior melhorou
    ub_history: list[tuple[float, int]] = field(default_factory=list)  # (segundos, custo)
    bound_iterations: int = 0         # total de iterações do subgradiente
    root_bound: float = 0.0           # limite inferior na raiz (qualidade do limite)
    elapsed: float = 0.0


class _Timeout(Exception):
    """Usada para sair de toda a recursão de uma vez quando o prazo vence."""


def lower_bound(dist, first: int, last: int, path_cost: int,
                unvisited: np.ndarray, pi: np.ndarray) -> tuple[float, np.ndarray]:
    """Limite inferior com penalidades π para completar o caminho first -> ... -> last.

    U = não visitados; pi[i] = penalidade de unvisited[i]; w(i,j) = d(i,j) + πi + πj.

        LB(π) = custo(caminho) + MST_w(U) + min_u (d(last,u) + πu)
                + min_u (d(first,u) + πu) - 2·Σ πu

    Válido para QUALQUER π: em toda forma de completar a rota (aresta de last até U,
    caminho por todo U, aresta de U até first), cada vértice de U tem grau exatamente 2,
    então o custo com pesos w é o custo real + 2·Σπ. E esse custo com pesos w é
    >= MST_w(U) + as duas menores arestas (o caminho por U é uma árvore geradora de U).
    Com π = 0, é o limite 1-tree simples da T11.

    Devolve (LB, graus): graus[i] = grau de unvisited[i] na estrutura (MST + as duas
    arestas escolhidas). É o que o subgradiente usa (grau - 2).
    """
    k = len(unvisited)
    out = dist[last, unvisited] + pi    # arestas saindo do fim do caminho
    back = dist[first, unvisited] + pi  # arestas voltando ao início
    a, b = int(np.argmin(out)), int(np.argmin(back))

    weights = dist[np.ix_(unvisited, unvisited)] + pi[:, None] + pi[None, :]
    edges, mst_cost = prim(weights)  # posições 0..k-1

    bound = path_cost + mst_cost + out[a] + back[b] - 2.0 * pi.sum()
    degree = np.zeros(k)
    for p, c in edges:
        degree[p] += 1
        degree[c] += 1
    degree[a] += 1
    degree[b] += 1
    return float(bound), degree


def _prunes(bound: float, upper: int) -> bool:
    """O nó pode ser podado se nenhuma completação pode custar menos que `upper`.

    Os custos reais são inteiros, então qualquer completação custa >= ceil(LB).
    O _EPS evita que um erro de arredondamento em ponto flutuante (ex.: 99.9999999
    em vez de 100) suba o limite indevidamente. >= (e não >): basta uma rota ótima,
    e a atual já atinge `upper`.
    """
    return math.ceil(bound - _EPS) >= upper


def held_karp_bound(dist, first: int, last: int, path_cost: int, unvisited: np.ndarray,
                    pi: np.ndarray, iterations: int, upper: int,
                    lam: float = ROOT_LAMBDA,
                    deadline: float = math.inf) -> tuple[float, np.ndarray, int]:
    """Maximiza LB(π) por subgradiente, partindo de `pi`.

    Cada vértice com grau > 2 na estrutura ganha penalidade (fica mais "caro" e tende
    a perder arestas); com grau < 2, perde penalidade. Isso empurra a estrutura a ter
    grau 2 em todos os vértices, ou seja, a parecer uma rota.

    Passo de Polyak: passo = lam x (alvo - LB) / ||g||², com alvo = (1 + DELTA) x melhor LB.
    O alvo clássico é o limite superior; aqui ele NÃO é usado (D21): assim a sequência
    de π é a mesma para qualquer warm-start, e um limite superior melhor nunca expande
    mais nós (monotonicidade, base da análise de warm-start). `upper` só é usado para
    parar cedo quando o nó já pode ser podado; nesse caso ele não tem filhos, então o
    π interrompido não é herdado por ninguém.

    Histórico (T12): a 1ª versão encolhia o passo 10% por iteração; a soma dos passos
    ficava limitada e π parava cedo (1000 iterações davam o mesmo LB que 100).

    Devolve (melhor LB, π final, iterações feitas).
    """
    best = -math.inf
    for it in range(1, iterations + 1):
        # O prazo vale também aqui: na raiz são centenas de iterações
        if time.perf_counter() >= deadline:
            raise _Timeout
        bound, degree = lower_bound(dist, first, last, path_cost, unvisited, pi)
        best = max(best, bound)
        if _prunes(best, upper):
            break
        g = degree - 2.0
        norm2 = float(g @ g)
        if norm2 == 0:  # todos com grau 2: a estrutura já é uma completação da rota
            break
        pi = pi + lam * DELTA * abs(best) / norm2 * g
        if it % HALVE_EVERY == 0:
            lam *= 0.5
    return best, pi, it


def branch_and_bound(dist, initial_tour, deadline: float, prof=None) -> BnBResult:
    """Busca a rota ótima partindo do limite superior dado por `initial_tour`."""
    prof = prof or Profiler()
    n = len(dist)
    start = time.perf_counter()

    result = BnBResult(tour=list(initial_tour), cost=tour_cost(initial_tour, dist))
    result.nodes_expanded = 1  # raiz
    path = [0]
    visited = np.zeros(n, dtype=bool)
    visited[0] = True

    def search(path_cost: int, pi: np.ndarray) -> None:
        """pi: penalidades de todos os n vértices (só as dos não visitados importam)."""
        if time.perf_counter() >= deadline:
            raise _Timeout
        depth = len(path)
        result.max_depth = max(result.max_depth, depth)
        last = path[-1]

        if depth == n:  # folha: rota completa
            cost = path_cost + int(dist[last, 0])
            if cost < result.cost:
                result.cost = cost
                result.tour = path.copy()
                result.ub_improvements += 1
                result.ub_history.append((time.perf_counter() - start, cost))
            return

        candidates = np.flatnonzero(~visited)
        # Filhos do mais próximo ao mais distante (stable: empates pelo menor índice)
        children = candidates[np.argsort(dist[last, candidates], kind="stable")]
        for v in children:
            v = int(v)
            child_cost = path_cost + int(dist[last, v])
            path.append(v)
            visited[v] = True
            unvisited = np.flatnonzero(~visited)

            if len(unvisited) == 0:  # filho completa a rota: custo exato
                bound, child_pi, iters = child_cost + int(dist[v, 0]), pi, 0
            else:
                with prof.timed("lower_bound"):
                    bound, unvisited_pi, iters = held_karp_bound(
                        dist, 0, v, child_cost, unvisited, pi[unvisited],
                        NODE_ITERATIONS, result.cost, lam=NODE_LAMBDA, deadline=deadline)
                child_pi = pi.copy()
                child_pi[unvisited] = unvisited_pi
            result.bound_iterations += iters

            if _prunes(bound, result.cost):
                result.nodes_pruned += 1
            else:
                result.nodes_expanded += 1
                search(child_cost, child_pi)
            path.pop()
            visited[v] = False

    with prof.timed("bnb_search"):
        try:
            # Raiz: muitas iterações para obter boas penalidades iniciais
            pi = np.zeros(n)
            root_unvisited = np.arange(1, n)
            with prof.timed("root_bound"):
                root_bound, root_pi, iters = held_karp_bound(
                    dist, 0, 0, 0, root_unvisited, pi[root_unvisited],
                    ROOT_ITERATIONS, result.cost, deadline=deadline)
            pi[root_unvisited] = root_pi
            result.root_bound = root_bound
            result.bound_iterations += iters
            if not _prunes(root_bound, result.cost):
                search(0, pi)
            result.optimal = True
        except _Timeout:
            pass  # contadores e melhor rota até aqui são preservados (RF3)

    result.elapsed = time.perf_counter() - start
    return result
