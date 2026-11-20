"""Branch-and-Bound exato para o TSP (D9, D10).

- Busca em profundidade (DFS) recursiva a partir do vértice 0 (fixar o início
  elimina as n rotações equivalentes de cada rota).
- Filhos do mais próximo ao mais distante do último vértice do caminho.
- Limite inferior 1-tree adaptado a caminhos parciais (ver `lower_bound`).
- Prazo absoluto (`deadline`, em perf_counter): o tempo da heurística de
  warm-start, rodada antes, conta dentro do limite de 30 min (P2).

Contagem de nós (T11): para cada filho candidato calcula-se o limite inferior;
se LB >= limite superior atual, o filho é PODADO; senão, é EXPANDIDO e a busca
desce nele. A raiz conta como expandida. Folhas (rota completa) que melhoram o
limite superior também contam como expandidas.
"""

import time
from dataclasses import dataclass, field

import numpy as np

from tsp.distance import tour_cost
from tsp.instrument import Profiler
from tsp.mst import prim


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
    elapsed: float = 0.0


class _Timeout(Exception):
    """Usada para sair de toda a recursão de uma vez quando o prazo vence."""


def lower_bound(dist, path: list[int], path_cost: int, unvisited: np.ndarray) -> int:
    """Limite inferior para completar o caminho path = v0 -> ... -> vk.

    LB = custo(caminho) + MST(U) + min d(vk, U) + min d(v0, U), U = não visitados.

    Válido porque toda forma de completar a rota é: uma aresta de vk até U,
    um caminho passando por todo U (que é uma árvore geradora de U, logo custa
    >= MST(U)) e uma aresta de U de volta a v0.
    Com U vazio, é o custo exato da rota (caminho + aresta de volta).
    """
    first, last = path[0], path[-1]
    if len(unvisited) == 0:
        return path_cost + int(dist[last, first])
    _, mst_cost = prim(dist, unvisited)
    return (path_cost + mst_cost
            + int(dist[last, unvisited].min())
            + int(dist[first, unvisited].min()))


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

    def search(path_cost: int) -> None:
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
            with prof.timed("lower_bound"):
                lb = lower_bound(dist, path, child_cost, np.flatnonzero(~visited))
            # >= (e não >): basta uma rota ótima, e a atual já atinge result.cost
            if lb >= result.cost:
                result.nodes_pruned += 1
            else:
                result.nodes_expanded += 1
                search(child_cost)
            path.pop()
            visited[v] = False

    with prof.timed("bnb_search"):
        try:
            search(0)
            result.optimal = True
        except _Timeout:
            pass  # contadores e melhor rota até aqui são preservados (RF3)

    result.elapsed = time.perf_counter() - start
    return result
