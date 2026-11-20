import time
from itertools import permutations

import numpy as np
import pytest
from helpers import ROOT, assert_valid_tour, brute_force

from tsp.bnb import branch_and_bound, lower_bound
from tsp.distance import distance_matrix, tour_cost
from tsp.heuristics import nearest_neighbor, trivial_tour
from tsp.tsplib import read_tsp

FAR_FUTURE = float("inf")  # prazo que nunca vence


def random_instance(seed: int, n: int | None = None):
    rng = np.random.default_rng(seed)
    n = n or int(rng.integers(5, 10))  # N de 5 a 9
    coords = rng.uniform(0, 1000, size=(n, 2))
    return coords, distance_matrix(coords)


def best_completion(dist, path: list[int]) -> int:
    """Custo da melhor rota que começa com `path` (força bruta sobre o resto)."""
    rest = [v for v in range(len(dist)) if v not in path]
    best = None
    for perm in permutations(rest):
        cost = tour_cost(path + list(perm), dist)
        best = cost if best is None else min(best, cost)
    return best


@pytest.mark.parametrize("seed", range(30))
def test_lower_bound_is_valid(seed):
    # LB nunca pode passar do custo real da melhor forma de completar o caminho
    coords, dist = random_instance(seed, n=8)
    rng = np.random.default_rng(1000 + seed)
    k = int(rng.integers(1, 8))  # tamanho do caminho parcial
    path = [0] + [int(v) for v in rng.permutation(np.arange(1, 8))[: k - 1]]
    path_cost = sum(int(dist[a, b]) for a, b in zip(path, path[1:]))
    unvisited = np.array([v for v in range(8) if v not in path])
    assert lower_bound(dist, path, path_cost, unvisited) <= best_completion(dist, path)


@pytest.mark.parametrize("heuristic", [trivial_tour, nearest_neighbor])
@pytest.mark.parametrize("seed", range(20))
def test_optimal_equals_brute_force(heuristic, seed):
    # Critério de pronto da T11
    coords, dist = random_instance(seed)
    result = branch_and_bound(dist, heuristic(coords, dist), deadline=FAR_FUTURE)
    assert result.optimal
    assert result.cost == brute_force(dist)
    assert_valid_tour(result.tour, len(dist))
    assert tour_cost(result.tour, dist) == result.cost


@pytest.mark.parametrize("seed", range(10))
def test_better_initial_bound_never_expands_more(seed):
    # Monotonicidade: base da análise de warm-start
    coords, dist = random_instance(seed, n=9)
    optimal_tour = branch_and_bound(dist, trivial_tour(coords, dist), FAR_FUTURE).tour
    initial_tours = [trivial_tour(coords, dist), nearest_neighbor(coords, dist), optimal_tour]
    initial_tours.sort(key=lambda t: tour_cost(t, dist), reverse=True)  # do pior ao melhor
    expanded = [branch_and_bound(dist, t, FAR_FUTURE).nodes_expanded for t in initial_tours]
    assert expanded == sorted(expanded, reverse=True)


def test_initial_tour_already_optimal():
    coords, dist = random_instance(7, n=9)
    optimal_tour = branch_and_bound(dist, trivial_tour(coords, dist), FAR_FUTURE).tour
    result = branch_and_bound(dist, optimal_tour, FAR_FUTURE)
    assert result.optimal and result.cost == tour_cost(optimal_tour, dist)
    assert result.ub_improvements == 0
    assert_valid_tour(result.tour, len(dist))


def load_n40():
    instance = read_tsp(ROOT / "data" / "instances" / "rd100-n40.tsp")
    return instance.coords, distance_matrix(instance.coords)


def test_expired_deadline():
    coords, dist = load_n40()
    initial = trivial_tour(coords, dist)
    result = branch_and_bound(dist, initial, deadline=time.perf_counter())
    assert not result.optimal
    assert result.tour == initial and result.nodes_expanded == 1


def test_short_deadline_keeps_partial_counters():
    coords, dist = load_n40()
    result = branch_and_bound(dist, trivial_tour(coords, dist),
                              deadline=time.perf_counter() + 0.2)
    assert not result.optimal
    assert result.nodes_expanded > 1 and result.nodes_pruned > 0
    assert_valid_tour(result.tour, 40)
    assert tour_cost(result.tour, dist) == result.cost <= tour_cost(trivial_tour(coords, dist), dist)
    assert 1 <= result.max_depth <= 40
    assert result.elapsed < 1.0  # parou perto do prazo
