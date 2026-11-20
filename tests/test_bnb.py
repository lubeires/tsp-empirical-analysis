import time
from itertools import permutations

import numpy as np
import pytest
from helpers import ROOT, assert_valid_tour, brute_force

from tsp.bnb import branch_and_bound, held_karp_bound, lower_bound
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


def random_partial_path(seed: int, dist):
    """Caminho parcial aleatório começando em 0 (1 a 7 vértices, em n = 8)."""
    rng = np.random.default_rng(1000 + seed)
    k = int(rng.integers(1, 8))
    path = [0] + [int(v) for v in rng.permutation(np.arange(1, 8))[: k - 1]]
    path_cost = sum(int(dist[a, b]) for a, b in zip(path, path[1:]))
    unvisited = np.array([v for v in range(8) if v not in path])
    return path, path_cost, unvisited, rng


@pytest.mark.parametrize("seed", range(30))
def test_lower_bound_is_valid_for_any_penalties(seed):
    # LB(π) nunca pode passar do custo real da melhor forma de completar o caminho,
    # para QUALQUER π (aqui: zero e aleatório, inclusive negativo)
    coords, dist = random_instance(seed, n=8)
    path, path_cost, unvisited, rng = random_partial_path(seed, dist)
    best = best_completion(dist, path)
    for pi in (np.zeros(len(unvisited)), rng.uniform(-300, 300, size=len(unvisited))):
        bound, _ = lower_bound(dist, path[0], path[-1], path_cost, unvisited, pi)
        assert bound <= best + 1e-9


@pytest.mark.parametrize("seed", range(30))
def test_held_karp_is_valid_and_not_weaker(seed):
    coords, dist = random_instance(seed, n=8)
    path, path_cost, unvisited, _ = random_partial_path(seed, dist)
    zero = np.zeros(len(unvisited))
    simple, _ = lower_bound(dist, path[0], path[-1], path_cost, unvisited, zero)
    hk, _, _ = held_karp_bound(dist, path[0], path[-1], path_cost, unvisited, zero,
                               iterations=50, upper=10**9)
    assert simple <= hk <= best_completion(dist, path) + 1e-9


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


def load_hard():
    # kroA100-n33: a mais demorada das sub-instâncias (~30 s com o fecho como início),
    # então não termina dentro dos prazos curtos usados abaixo
    instance = read_tsp(ROOT / "data" / "instances" / "kroA100-n33.tsp")
    return instance.coords, distance_matrix(instance.coords)


def test_expired_deadline():
    # Prazo já vencido: para ainda no cálculo da raiz (que também confere o prazo)
    coords, dist = load_hard()
    initial = trivial_tour(coords, dist)
    result = branch_and_bound(dist, initial, deadline=time.perf_counter())
    assert not result.optimal
    assert result.tour == initial and result.nodes_expanded == 1
    assert result.elapsed < 0.1


def test_short_deadline_keeps_partial_counters():
    coords, dist = load_hard()
    result = branch_and_bound(dist, trivial_tour(coords, dist),
                              deadline=time.perf_counter() + 1.5)
    assert not result.optimal
    assert result.nodes_expanded > 1 and result.nodes_pruned > 0
    assert_valid_tour(result.tour, 33)
    assert tour_cost(result.tour, dist) == result.cost <= tour_cost(trivial_tour(coords, dist), dist)
    assert 1 <= result.max_depth <= 33
    assert result.elapsed < 2.5  # parou perto do prazo
