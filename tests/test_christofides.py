"""Testes das etapas internas do Christofides (T10)."""

from collections import Counter

import numpy as np
import pytest
from helpers import load_test_instances

from tsp.approx import (
    _build_matching_graph,
    _eulerian_circuit,
    _min_weight_perfect_matching,
    _odd_vertices,
    christofides,
)
from tsp.distance import distance_matrix, tour_cost
from tsp.mst import prim

INSTANCES = load_test_instances()


def brute_force_matching_cost(dist, vertices: list[int]) -> int:
    """Custo do emparelhamento perfeito mínimo testando todos (recursivo).

    O primeiro vértice é pareado com cada um dos outros; o resto é resolvido
    recursivamente. Para 8 vértices: 7 x 5 x 3 x 1 = 105 emparelhamentos.
    """
    if not vertices:
        return 0
    first, rest = vertices[0], vertices[1:]
    return min(
        int(dist[first, partner]) + brute_force_matching_cost(dist, rest[:i] + rest[i + 1:])
        for i, partner in enumerate(rest)
    )


def matching_cost(dist, matching) -> int:
    return sum(int(dist[a, b]) for a, b in matching)


@pytest.mark.parametrize("seed", range(15))
def test_matching_is_minimum(seed):
    # Confere o uso da biblioteca (ex.: engano entre "máximo" e "mínimo")
    rng = np.random.default_rng(seed)
    size = int(rng.choice([2, 4, 6, 8]))
    dist = distance_matrix(rng.uniform(0, 1000, size=(size, 2)))
    vertices = list(range(size))
    matching = _min_weight_perfect_matching(_build_matching_graph(dist, vertices), vertices)
    assert matching_cost(dist, matching) == brute_force_matching_cost(dist, vertices)


@pytest.mark.parametrize("name,instance", INSTANCES, ids=[n for n, _ in INSTANCES])
def test_odd_vertices_perfectly_matched(name, instance):
    dist = distance_matrix(instance.coords)
    edges, _ = prim(dist)
    odd = _odd_vertices(edges, instance.n)
    assert len(odd) % 2 == 0
    matching = _min_weight_perfect_matching(_build_matching_graph(dist, odd), odd)
    covered = Counter(v for edge in matching for v in edge)
    assert set(covered) == set(odd) and all(c == 1 for c in covered.values())


def assert_eulerian_circuit(circuit, edges, start=0):
    assert circuit[0] == circuit[-1] == start
    assert len(circuit) == len(edges) + 1
    # Cada aresta (com multiplicidade) usada exatamente uma vez
    used = Counter(tuple(sorted(p)) for p in zip(circuit, circuit[1:]))
    assert used == Counter(tuple(sorted(e)) for e in edges)


def test_eulerian_bowtie():
    # Dois triângulos que compartilham o vértice 0
    edges = [(0, 1), (1, 2), (2, 0), (0, 3), (3, 4), (4, 0)]
    assert_eulerian_circuit(_eulerian_circuit(5, edges), edges)


def test_eulerian_with_repeated_edge():
    # Arestas (0, 1) e (1, 2) duplicadas, como quando MST e emparelhamento coincidem.
    # Graus: 0 -> 2, 1 -> 4, 2 -> 2 (todos pares)
    edges = [(0, 1), (0, 1), (1, 2), (1, 2)]
    assert_eulerian_circuit(_eulerian_circuit(3, edges), edges)


@pytest.mark.parametrize("name,instance", INSTANCES, ids=[n for n, _ in INSTANCES])
def test_cost_at_most_mst_plus_matching(name, instance):
    dist = distance_matrix(instance.coords)
    edges, mst_cost = prim(dist)
    odd = _odd_vertices(edges, instance.n)
    matching = _min_weight_perfect_matching(_build_matching_graph(dist, odd), odd)
    tour = christofides(instance.coords, dist)
    assert tour_cost(tour, dist) <= mst_cost + matching_cost(dist, matching)
