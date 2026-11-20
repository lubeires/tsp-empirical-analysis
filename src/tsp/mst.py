"""Árvore geradora mínima (MST) por Prim com vetor, O(k²) (D8).

Num grafo completo (~k² arestas), Prim com vetor é assintoticamente melhor que
Prim com heap ou Kruskal, ambos O(k² log k).

A função não recebe o profiler: quem chama mede com `with prof.timed("mst")`.
"""

import numpy as np

_INF = np.iinfo(np.int64).max


def prim(dist: np.ndarray, vertices=None) -> tuple[list[tuple[int, int]], int | float]:
    """MST dos `vertices` (todos, se None).

    Devolve (arestas, custo). Cada aresta é (pai, filho) com índices originais.
    Aceita pesos inteiros (custo int) ou reais (custo float, usado no Held-Karp).
    Empates decididos pelo menor índice (argmin): resultado determinístico.
    """
    if vertices is None:
        vertices = np.arange(len(dist))
    else:
        vertices = np.asarray(vertices)
    k = len(vertices)
    if k <= 1:
        return [], 0

    # Posições 0..k-1 referem-se a vertices[0..k-1]
    in_tree = np.zeros(k, dtype=bool)
    in_tree[0] = True
    best = dist[vertices[0], vertices].copy()  # menor distância de cada vértice até a árvore
    parent = np.zeros(k, dtype=np.int64)        # posição do vértice da árvore que dá `best`

    edges = []
    total = 0
    for _ in range(k - 1):
        # Vértice fora da árvore mais próximo dela
        u = int(np.argmin(np.where(in_tree, _INF, best)))
        in_tree[u] = True
        # .item(): int para matriz inteira, float para pesos reais (Held-Karp, T12)
        total += best[u].item()
        edges.append((int(vertices[parent[u]]), int(vertices[u])))

        # Atualiza best/parent com a linha de u (só vértices fora da árvore que melhoram)
        row = dist[vertices[u], vertices]
        improve = ~in_tree & (row < best)
        best[improve] = row[improve]
        parent[improve] = u

    return edges, total
