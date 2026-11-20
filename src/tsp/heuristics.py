"""Heurísticas construtivas usadas como limite superior inicial do B&B (warm-start).

Interface única de todos os algoritmos que devolvem uma rota (T06):
    algoritmo(coords, dist, prof=None) -> list[int]
A rota não repete o vértice inicial no fim; o custo é calculado à parte (tour_cost).
"""

import numpy as np

from tsp.instrument import Profiler

# Valor usado para "esconder" vértices já visitados no argmin
_INF = np.iinfo(np.int64).max


def trivial_tour(coords, dist, prof=None) -> list[int]:
    """Cold start: 0 -> 1 -> ... -> n-1 (ordem do arquivo). O(n)."""
    prof = prof or Profiler()
    with prof.timed("trivial"):
        return list(range(len(dist)))


def nearest_neighbor(coords, dist, prof=None) -> list[int]:
    """Vizinho mais próximo a partir do vértice 0. O(n^2).

    Empates são decididos pelo menor índice (comportamento do argmin),
    o que torna o resultado determinístico.
    """
    prof = prof or Profiler()
    with prof.timed("nearest_neighbor"):
        n = len(dist)
        visited = np.zeros(n, dtype=bool)
        tour = [0]
        visited[0] = True
        for _ in range(n - 1):
            current = tour[-1]
            # Distâncias a partir do vértice atual, com os visitados "infinitos"
            candidates = np.where(visited, _INF, dist[current])
            nxt = int(np.argmin(candidates))
            tour.append(nxt)
            visited[nxt] = True
        return tour


def _cross(o, a, b) -> float:
    """Produto vetorial (a - o) x (b - o).

    > 0: o -> a -> b vira à esquerda (anti-horário); < 0: à direita; = 0: colineares.
    """
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def convex_hull(coords) -> list[int]:
    """Fecho convexo pelo método de Andrew (monotone chain). O(n log n).

    Devolve os índices dos vértices do fecho em sentido anti-horário.
    Pontos colineares na borda NÃO entram (decisão da T07): só os "cantos".
    """
    n = len(coords)
    order = sorted(range(n), key=lambda i: (coords[i][0], coords[i][1]))
    if n <= 2:
        return order

    def half(points: list[int]) -> list[int]:
        chain: list[int] = []
        for i in points:
            # Remove o último enquanto a curva não for estritamente à esquerda.
            # O "<= 0" descarta também os colineares.
            while len(chain) >= 2 and _cross(coords[chain[-2]], coords[chain[-1]], coords[i]) <= 0:
                chain.pop()
            chain.append(i)
        return chain

    lower = half(order)            # metade de baixo, da esquerda para a direita
    upper = half(order[::-1])      # metade de cima, da direita para a esquerda
    # O último de cada metade é o primeiro da outra: removido para não repetir
    return lower[:-1] + upper[:-1]


def convex_hull_insertion(coords, dist, prof=None) -> list[int]:
    """Começa pelo fecho convexo e insere os demais vértices por inserção mais barata. O(n^3).

    A cada passo escolhe, entre todos os pares (vértice de fora k, aresta (i, j) da rota),
    o de menor acréscimo d(i,k) + d(k,j) - d(i,j).
    """
    prof = prof or Profiler()
    with prof.timed("hull_insertion"):
        with prof.timed("convex_hull"):
            tour = [int(v) for v in convex_hull(coords)]

        with prof.timed("insertion"):
            in_tour = np.zeros(len(dist), dtype=bool)
            in_tour[tour] = True
            remaining = np.flatnonzero(~in_tour)
            while remaining.size > 0:
                start = np.array(tour)
                end = np.roll(start, -1)  # aresta e = (start[e], end[e])
                # delta[r, e] = acréscimo de inserir remaining[r] na aresta e
                delta = (dist[np.ix_(remaining, start)] + dist[np.ix_(remaining, end)]
                         - dist[start, end])
                r, e = np.unravel_index(np.argmin(delta), delta.shape)
                tour.insert(int(e) + 1, int(remaining[r]))
                remaining = np.delete(remaining, r)
        return tour
