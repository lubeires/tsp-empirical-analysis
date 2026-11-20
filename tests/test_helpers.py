"""Testes das próprias funções auxiliares: se elas estiverem erradas, os demais testes não valem."""

import numpy as np
import pytest
from helpers import ROOT, assert_valid_tour, brute_force, independent_cost

from tsp.distance import distance_matrix
from tsp.tsplib import read_tour, read_tsp


def test_brute_force_square():
    # Quadrado de lado 10: rota ótima é o perímetro (40)
    coords = np.array([[0, 0], [10, 10], [10, 0], [0, 10]], dtype=float)
    assert brute_force(distance_matrix(coords)) == 40


def test_independent_cost_berlin52():
    instance = read_tsp(ROOT / "data" / "tsplib" / "berlin52.tsp")
    tour = read_tour(ROOT / "data" / "tsplib" / "berlin52.opt.tour")
    assert independent_cost(tour, instance.coords) == 7542


def test_assert_valid_tour_rejects_repeated_vertex():
    with pytest.raises(AssertionError):
        assert_valid_tour([0, 1, 1], 3)
