"""Algoritmos aproximados: Twice-around-the-tree (2-aproximação) e Christofides (1,5).

Mesma interface das heurísticas (T06): algoritmo(coords, dist, prof=None) -> list[int].
"""

import networkx as nx

from tsp.instrument import Profiler
from tsp.mst import prim


def _preorder(edges: list[tuple[int, int]], n: int, root: int = 0) -> list[int]:
    """Pré-ordem da árvore a partir de `root`, com pilha explícita (sem recursão).

    Filhos visitados em ordem crescente de índice (T09). Em uma árvore cada vértice
    é empilhado uma única vez (pelo pai), então não há repetições na saída.
    """
    adj: list[list[int]] = [[] for _ in range(n)]
    for a, b in edges:
        adj[a].append(b)
        adj[b].append(a)

    visited = [False] * n
    order = []
    stack = [root]
    while stack:
        v = stack.pop()
        visited[v] = True
        order.append(v)
        # Empilha em ordem decrescente para que o menor índice saia primeiro da pilha
        for w in sorted(adj[v], reverse=True):
            if not visited[w]:
                stack.append(w)
    return order


def twice_around_the_tree(coords, dist, prof=None) -> list[int]:
    """2-aproximação: pré-ordem da MST a partir do vértice 0. O(n²).

    Dar "duas voltas" na árvore percorre cada aresta duas vezes (custo 2 x MST);
    pular os vértices repetidos desse passeio é exatamente a pré-ordem.
    Garantia: custo <= 2 x MST <= 2 x ótimo, supondo desigualdade triangular
    (que o nint pode violar por 1 unidade por atalho; ver T09).
    """
    prof = prof or Profiler()
    with prof.timed("twice_around"):
        with prof.timed("mst"):
            edges, _ = prim(dist)
        with prof.timed("preorder"):
            return _preorder(edges, len(dist), root=0)


# ---------------------------------------------------------------------------
# Christofides (T10)
# ---------------------------------------------------------------------------

def _odd_vertices(edges: list[tuple[int, int]], n: int) -> list[int]:
    """Vértices de grau ímpar. São sempre em número par (lema do aperto de mãos)."""
    degree = [0] * n
    for a, b in edges:
        degree[a] += 1
        degree[b] += 1
    return [v for v in range(n) if degree[v] % 2 == 1]


def _build_matching_graph(dist, odd: list[int]) -> nx.Graph:
    """Grafo completo sobre os vértices ímpares, no formato do networkx."""
    graph = nx.Graph()
    for i, a in enumerate(odd):
        for b in odd[i + 1:]:
            graph.add_edge(a, b, weight=int(dist[a, b]))
    return graph


def _min_weight_perfect_matching(graph: nx.Graph, odd: list[int]) -> list[tuple[int, int]]:
    """Emparelhamento perfeito de custo mínimo (networkx, D8).

    No networkx 3.x, min_weight_matching devolve um emparelhamento de cardinalidade
    máxima com peso mínimo; em grafo completo com número par de vértices, é perfeito.
    O resultado vem como conjunto: as arestas são ordenadas para o algoritmo ser
    determinístico.
    """
    matching = nx.min_weight_matching(graph)
    assert 2 * len(matching) == len(odd), "emparelhamento não é perfeito"
    return sorted(tuple(sorted(e)) for e in matching)


def _eulerian_circuit(n: int, edges: list[tuple[int, int]], start: int = 0) -> list[int]:
    """Circuito euleriano por Hierholzer iterativo. O(arestas).

    Supõe multigrafo conexo com todos os graus pares. Arestas repetidas são
    distinguidas pelo identificador (posição em `edges`), então ambas as cópias
    são percorridas. Devolve len(edges) + 1 vértices, começando e terminando em start.
    """
    adj: list[list[tuple[int, int]]] = [[] for _ in range(n)]  # (vizinho, id da aresta)
    for edge_id, (a, b) in enumerate(edges):
        adj[a].append((b, edge_id))
        adj[b].append((a, edge_id))

    used = [False] * len(edges)
    next_pos = [0] * n  # próxima posição a examinar em adj[v]
    stack = [start]
    circuit = []
    while stack:
        v = stack[-1]
        # Pula arestas já usadas (cada uma é examinada no máximo 2 vezes no total)
        while next_pos[v] < len(adj[v]) and used[adj[v][next_pos[v]][1]]:
            next_pos[v] += 1
        if next_pos[v] == len(adj[v]):
            # Sem arestas livres: v entra no circuito (em ordem inversa)
            circuit.append(stack.pop())
        else:
            w, edge_id = adj[v][next_pos[v]]
            used[edge_id] = True
            stack.append(w)
    return circuit[::-1]


def _shortcut(circuit: list[int]) -> list[int]:
    """Atalhos: mantém só a primeira ocorrência de cada vértice."""
    seen = set()
    tour = []
    for v in circuit:
        if v not in seen:
            seen.add(v)
            tour.append(v)
    return tour


def christofides(coords, dist, prof=None) -> list[int]:
    """1,5-aproximação de Christofides.

    MST + emparelhamento perfeito mínimo dos vértices ímpares formam um multigrafo
    euleriano; o circuito euleriano com atalhos é a rota.
    Garantia: custo <= MST + emparelhamento <= ótimo + ótimo/2 (com a mesma
    ressalva do nint sobre a desigualdade triangular, ver T09).
    """
    prof = prof or Profiler()
    n = len(dist)
    with prof.timed("christofides"):
        with prof.timed("mst"):
            mst_edges, _ = prim(dist)
        with prof.timed("odd_vertices"):
            odd = _odd_vertices(mst_edges, n)
        # Separados para distinguir o custo da biblioteca (montar o grafo)
        # do custo do algoritmo de emparelhamento em si (T10)
        with prof.timed("matching_build"):
            graph = _build_matching_graph(dist, odd)
        with prof.timed("matching"):
            matching = _min_weight_perfect_matching(graph, odd)
        with prof.timed("euler"):
            circuit = _eulerian_circuit(n, mst_edges + matching, start=0)
        with prof.timed("shortcut"):
            return _shortcut(circuit)
