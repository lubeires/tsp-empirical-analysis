"""Algoritmos aproximados: Twice-around-the-tree (2-aproximação) e Christofides (1,5).

Mesma interface das heurísticas (T06): algoritmo(coords, dist, prof=None) -> list[int].
"""

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
