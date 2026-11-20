import numpy as np
import pytest
from helpers import assert_valid_tour, brute_force, independent_cost, load_test_instances

from tsp.distance import distance_matrix, tour_cost
from tsp.heuristics import nearest_neighbor, trivial_tour

HEURISTICS = [trivial_tour, nearest_neighbor]
INSTANCES = load_test_instances()


def test_nearest_neighbor_hand_example():
    # De 0 (0,0): mais próximo é 2 (1,0); de 2: é 3 (3,0); sobra 1 (10,0)
    coords = np.array([[0, 0], [10, 0], [1, 0], [3, 0]], dtype=float)
    assert nearest_neighbor(coords, distance_matrix(coords)) == [0, 2, 3, 1]


def test_trivial_is_file_order():
    coords = np.random.default_rng(1).uniform(0, 100, size=(7, 2))
    assert trivial_tour(coords, distance_matrix(coords)) == list(range(7))


@pytest.mark.parametrize("heuristic", HEURISTICS)
@pytest.mark.parametrize("name,instance", INSTANCES, ids=[n for n, _ in INSTANCES])
def test_valid_on_test_instances(heuristic, name, instance):
    dist = distance_matrix(instance.coords)
    tour = heuristic(instance.coords, dist)
    assert_valid_tour(tour, instance.n)
    assert tour_cost(tour, dist) == independent_cost(tour, instance.coords)


@pytest.mark.parametrize("heuristic", HEURISTICS)
@pytest.mark.parametrize("seed", range(10))
def test_not_better_than_optimum(heuristic, seed):
    rng = np.random.default_rng(seed)
    n = int(rng.integers(5, 10))  # N de 5 a 9
    coords = rng.uniform(0, 1000, size=(n, 2))
    dist = distance_matrix(coords)
    assert tour_cost(heuristic(coords, dist), dist) >= brute_force(dist)
