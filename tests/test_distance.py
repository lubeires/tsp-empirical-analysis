from pathlib import Path

import numpy as np

from tsp.distance import distance_matrix, tour_cost
from tsp.tsplib import read_tour, read_tsp

TSPLIB_DIR = Path(__file__).resolve().parents[1] / "data" / "tsplib"


def test_matrix_properties():
    coords = np.random.default_rng(0).uniform(0, 1000, size=(30, 2))
    dist = distance_matrix(coords)
    assert dist.shape == (30, 30)
    assert np.issubdtype(dist.dtype, np.integer)
    assert np.array_equal(dist, dist.T)
    assert np.all(np.diag(dist) == 0)


def test_nint_rounds_half_up():
    # Distância exata 2.5: a TSPLIB arredonda para 3 (np.round daria 2)
    coords = np.array([[0.0, 0.0], [1.5, 2.0]])
    assert distance_matrix(coords)[0, 1] == 3


def test_berlin52_optimal_tour_cost():
    # Critério de pronto da T03: ótimo publicado do berlin52
    instance = read_tsp(TSPLIB_DIR / "berlin52.tsp")
    tour = read_tour(TSPLIB_DIR / "berlin52.opt.tour")
    assert tour_cost(tour, distance_matrix(instance.coords)) == 7542
