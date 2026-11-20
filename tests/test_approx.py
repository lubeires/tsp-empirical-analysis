import numpy as np
import pytest
from helpers import ROOT, assert_valid_tour, brute_force, independent_cost, load_test_instances

from tsp.approx import twice_around_the_tree
from tsp.distance import distance_matrix, tour_cost
from tsp.generate import load_optima
from tsp.mst import prim

INSTANCES = load_test_instances()
OPTIMA = load_optima(ROOT / "data" / "tsplib")
FULL = [(n, i) for n, i in INSTANCES if n in ("eil51", "berlin52", "st70")]

# (algoritmo, fator de aproximação garantido)
APPROX = [(twice_around_the_tree, 2.0)]


def test_twice_around_hand_example():
    # MST: 0-3, 3-1, 3-2 (todas de custo 10). Pré-ordem a partir de 0,
    # filhos de 3 em ordem crescente: 0, 3, 1, 2
    coords = np.array([[0, 0], [20, 0], [10, 10], [10, 0]], dtype=float)
    assert twice_around_the_tree(coords, distance_matrix(coords)) == [0, 3, 1, 2]


@pytest.mark.parametrize("algorithm,factor", APPROX)
@pytest.mark.parametrize("name,instance", INSTANCES, ids=[n for n, _ in INSTANCES])
def test_valid_on_test_instances(algorithm, factor, name, instance):
    dist = distance_matrix(instance.coords)
    tour = algorithm(instance.coords, dist)
    assert_valid_tour(tour, instance.n)
    assert tour_cost(tour, dist) == independent_cost(tour, instance.coords)


@pytest.mark.parametrize("algorithm,factor", APPROX)
@pytest.mark.parametrize("seed", range(10))
def test_factor_vs_brute_force(algorithm, factor, seed):
    rng = np.random.default_rng(seed)
    coords = rng.uniform(0, 1000, size=(int(rng.integers(5, 10)), 2))
    dist = distance_matrix(coords)
    assert tour_cost(algorithm(coords, dist), dist) <= factor * brute_force(dist)


@pytest.mark.parametrize("algorithm,factor", APPROX)
@pytest.mark.parametrize("name,instance", FULL, ids=[n for n, _ in FULL])
def test_factor_vs_published_optimum(algorithm, factor, name, instance):
    dist = distance_matrix(instance.coords)
    assert tour_cost(algorithm(instance.coords, dist), dist) <= factor * OPTIMA[name]


@pytest.mark.parametrize("name,instance", INSTANCES, ids=[n for n, _ in INSTANCES])
def test_twice_around_mst_bounds(name, instance):
    # MST <= custo <= 2 x MST. O limite de cima depende da desigualdade
    # triangular, que o nint pode violar (ver T09).
    dist = distance_matrix(instance.coords)
    _, mst_cost = prim(dist)
    cost = tour_cost(twice_around_the_tree(instance.coords, dist), dist)
    assert mst_cost <= cost <= 2 * mst_cost
