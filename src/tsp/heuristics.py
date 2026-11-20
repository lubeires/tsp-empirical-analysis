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
