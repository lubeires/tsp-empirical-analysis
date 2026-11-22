import math

import numpy as np
import pytest
from scipy.spatial import ConvexHull

from tsp.features import compute_features
from tsp.heuristics import _cross, convex_hull

GRID = np.array([[x, y] for x in range(4) for y in range(4)], dtype=float)


def test_regular_grid():
    f = compute_features(GRID)
    assert f["aspect_ratio"] == 1.0
    assert f["nn_cv"] == pytest.approx(0.0)
    assert f["clark_evans"] > 1  # regular
    assert f["hull_ratio"] == 12 / 16  # borda inteira, com colineares
    assert f["spatial_entropy"] == pytest.approx(1.0)  # um ponto por célula


def test_hull_with_and_without_collinear_on_grid():
    assert len(convex_hull(GRID)) == 4
    assert len(convex_hull(GRID, include_collinear=True)) == 12


def test_line_does_not_break():
    line = np.array([[i, 2 * i] for i in range(6)], dtype=float)
    f = compute_features(line)
    assert f["aspect_ratio"] == 0.5  # retângulo envolvente 5 x 10
    flat = compute_features(np.array([[i, 0.0] for i in range(6)]))
    assert flat["aspect_ratio"] == 0.0
    assert math.isnan(flat["clark_evans"])  # área zero: indefinido
    assert flat["hull_ratio"] == 1.0


def test_clustered_vs_uniform():
    rng = np.random.default_rng(0)
    uniform = rng.uniform(0, 1000, size=(100, 2))
    centers = np.array([[100, 100], [900, 200], [500, 900]])
    clustered = np.vstack([c + rng.normal(0, 15, size=(34, 2)) for c in centers])[:100]
    fu, fc = compute_features(uniform), compute_features(clustered)
    assert fc["spatial_entropy"] < fu["spatial_entropy"]
    assert fc["clark_evans"] < fu["clark_evans"]
    assert 0.8 < fu["clark_evans"] < 1.3  # aleatório: perto de 1


def on_boundary(coords, strict_hull, p) -> bool:
    """Referência independente: p está sobre alguma aresta do fecho estrito."""
    for a, b in zip(strict_hull, strict_hull[1:] + strict_hull[:1]):
        A, B, P = coords[a], coords[b], coords[p]
        if _cross(A, B, P) == 0 and min(A[0], B[0]) <= P[0] <= max(A[0], B[0]) \
                and min(A[1], B[1]) <= P[1] <= max(A[1], B[1]):
            return True
    return False


@pytest.mark.parametrize("seed", range(15))
def test_collinear_hull_matches_reference(seed):
    # Pontos inteiros numa grade pequena: muitos colineares na borda
    coords = np.random.default_rng(seed).integers(0, 6, size=(25, 2)).astype(float)
    coords = np.unique(coords, axis=0)
    strict = convex_hull(coords)
    assert set(strict) == set(ConvexHull(coords).vertices)
    expected = {p for p in range(len(coords)) if on_boundary(coords, strict, p)}
    assert set(convex_hull(coords, include_collinear=True)) == expected


def test_mst_stats_on_star():
    # Estrela: centro com 5 folhas num pentágono de raio 10. O lado do pentágono
    # (~11,76) é maior que o raio, então a MST é única: todas as folhas no centro.
    # (Com 6 folhas, o lado do hexágono = raio e há empate: a MST não é única.)
    star = np.array([[0, 0]] + [[10 * math.cos(a), 10 * math.sin(a)]
                                for a in np.linspace(0, 2 * math.pi, 5, endpoint=False)])
    f = compute_features(star)
    assert f["mst_max_degree"] == 5
    assert f["mst_leaf_ratio"] == pytest.approx(5 / 6)
    assert f["odd_ratio"] == pytest.approx(1.0)  # centro com grau 5 e folhas com grau 1
