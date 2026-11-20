"""Matriz de distâncias EUC_2D e custo de rotas."""

import numpy as np


def distance_matrix(coords: np.ndarray) -> np.ndarray:
    """Matriz n x n de distâncias euclidianas arredondadas como na TSPLIB.

    Custo O(n²) em tempo e memória. O arredondamento é nint(d) = floor(d + 0.5):
    np.round não serve, porque arredonda 2.5 para 2 ("arredondamento do banqueiro"),
    enquanto a TSPLIB arredonda para 3.
    """
    # diff[i, j] = coords[i] - coords[j], calculado de uma vez por broadcasting
    diff = coords[:, None, :] - coords[None, :, :]
    dist = np.sqrt((diff**2).sum(axis=2))
    return np.floor(dist + 0.5).astype(np.int64)


def tour_cost(tour, dist: np.ndarray) -> int:
    """Custo de uma rota fechada (inclui a aresta de volta ao vértice inicial)."""
    tour = np.asarray(tour)
    # np.roll(tour, -1) é a rota deslocada: pares (tour[i], tour[i+1]), com o último ligando ao primeiro
    return int(dist[tour, np.roll(tour, -1)].sum())
