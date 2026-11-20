import numpy as np
import pytest
from helpers import load_test_instances
from scipy.sparse.csgraph import minimum_spanning_tree

from tsp.distance import distance_matrix
from tsp.mst import prim

INSTANCES = load_test_instances()


def scipy_mst_cost(dist) -> int:
    """Custo da MST pelo scipy (referência independente).

    O scipy trata 0 (e valores minúsculos, como 1e-9) como "aresta inexistente".
    Com o nint, pontos a menos de 0,5 de distância viram distância 0 (aconteceu
    na semente 6 do teste aleatório). Por isso as distâncias 0 fora da diagonal
    viram 0,001: continuam menores que qualquer distância inteira >= 1, e a soma
    dos acréscimos (no máximo n-1 arestas x 0,001) é < 1, então o floor recupera
    o custo inteiro exato.
    """
    d = dist.astype(float)
    off_diagonal = ~np.eye(len(d), dtype=bool)
    d[(d == 0) & off_diagonal] = 1e-3
    return int(np.floor(minimum_spanning_tree(d).sum()))


def is_spanning_tree(edges, vertices) -> bool:
    """k-1 arestas e todos os vértices alcançáveis a partir do primeiro (busca simples)."""
    vertices = set(int(v) for v in vertices)
    if len(edges) != len(vertices) - 1:
        return False
    adj = {v: [] for v in vertices}
    for a, b in edges:
        adj[a].append(b)
        adj[b].append(a)
    start = next(iter(vertices))
    seen, stack = {start}, [start]
    while stack:
        for w in adj[stack.pop()]:
            if w not in seen:
                seen.add(w)
                stack.append(w)
    return seen == vertices


@pytest.mark.parametrize("seed", range(20))
def test_matches_scipy_random(seed):
    coords = np.random.default_rng(seed).uniform(0, 1000, size=(40, 2))
    dist = distance_matrix(coords)
    edges, cost = prim(dist)
    assert cost == scipy_mst_cost(dist)
    assert is_spanning_tree(edges, range(40))


@pytest.mark.parametrize("name,instance", INSTANCES, ids=[n for n, _ in INSTANCES])
def test_matches_scipy_test_instances(name, instance):
    dist = distance_matrix(instance.coords)
    edges, cost = prim(dist)
    assert cost == scipy_mst_cost(dist)
    assert sum(int(dist[a, b]) for a, b in edges) == cost


@pytest.mark.parametrize("seed", range(10))
def test_subset(seed):
    rng = np.random.default_rng(seed)
    dist = distance_matrix(rng.uniform(0, 1000, size=(40, 2)))
    vertices = np.sort(rng.choice(40, size=15, replace=False))
    edges, cost = prim(dist, vertices)
    assert cost == scipy_mst_cost(dist[np.ix_(vertices, vertices)])
    assert is_spanning_tree(edges, vertices)  # arestas com índices originais


def test_edge_cases():
    dist = distance_matrix(np.array([[0.0, 0.0], [3.0, 4.0], [10.0, 10.0]]))
    assert prim(dist, [2]) == ([], 0)
    assert prim(dist, [0, 1]) == ([(0, 1)], 5)
