import numpy as np
import pytest
from scipy.spatial import ConvexHull

from tsp.distance import distance_matrix
from tsp.heuristics import convex_hull, convex_hull_insertion


def signed_area(coords, polygon) -> float:
    """Fórmula do laço (shoelace): positiva se o polígono está em sentido anti-horário."""
    pts = coords[polygon]
    x, y = pts[:, 0], pts[:, 1]
    return 0.5 * float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))


def test_square_corners_only_ccw():
    # 4 cantos + 2 pontos internos + 1 ponto no meio da aresta de baixo (colinear)
    coords = np.array([[0, 0], [10, 0], [10, 10], [0, 10], [5, 5], [2, 3], [5, 0]], dtype=float)
    hull = convex_hull(coords)
    assert set(hull) == {0, 1, 2, 3}
    assert signed_area(coords, hull) > 0


@pytest.mark.parametrize("coords,expected", [
    (np.array([[3.0, 4.0]]), {0}),
    (np.array([[3.0, 4.0], [1.0, 1.0]]), {0, 1}),
    (np.array([[2.0, 2.0], [0.0, 0.0], [3.0, 3.0], [1.0, 1.0]]), {1, 2}),  # todos alinhados
])
def test_degenerate_cases(coords, expected):
    assert set(convex_hull(coords)) == expected


@pytest.mark.parametrize("seed", range(20))
def test_matches_scipy(seed):
    coords = np.random.default_rng(seed).uniform(0, 1000, size=(40, 2))
    assert set(convex_hull(coords)) == set(ConvexHull(coords).vertices)


@pytest.mark.parametrize("seed", range(10))
def test_insertion_preserves_hull_order(seed):
    coords = np.random.default_rng(seed).uniform(0, 1000, size=(30, 2))
    hull = convex_hull(coords)
    tour = convex_hull_insertion(coords, distance_matrix(coords))
    # Subsequência da rota formada só pelos vértices do fecho, girada para começar em hull[0]
    on_hull = [v for v in tour if v in set(hull)]
    k = on_hull.index(hull[0])
    assert on_hull[k:] + on_hull[:k] == hull


def test_degenerate_insertion_collinear():
    coords = np.array([[2.0, 2.0], [0.0, 0.0], [3.0, 3.0], [1.0, 1.0]])
    tour = convex_hull_insertion(coords, distance_matrix(coords))
    assert sorted(tour) == [0, 1, 2, 3]
