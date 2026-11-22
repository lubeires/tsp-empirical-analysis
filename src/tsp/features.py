"""Características geométricas e topológicas das instâncias (RF6, T17, D29).

Uso (na raiz do projeto):
    .venv/bin/python -m tsp.features

As características usam a distância euclidiana REAL (float), não o nint da TSPLIB:
descrevem a geometria dos pontos, não o custo da rota.
"""

import csv
import math
from pathlib import Path

import numpy as np

from tsp.heuristics import convex_hull
from tsp.mst import prim
from tsp.tsplib import read_tsp

ROOT = Path(__file__).resolve().parents[2]
FEATURES = ["n", "aspect_ratio", "hull_ratio", "spatial_entropy", "clark_evans",
            "mst_max_degree", "mst_leaf_ratio", "nn_cv", "odd_ratio"]


def _polygon_area(points: np.ndarray) -> float:
    """Área pela fórmula do laço (shoelace)."""
    x, y = points[:, 0], points[:, 1]
    return 0.5 * abs(float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y)))


def compute_features(coords: np.ndarray) -> dict:
    n = len(coords)
    lo, hi = coords.min(axis=0), coords.max(axis=0)
    span = hi - lo

    # Razão de aspecto: lado menor / lado maior (1 = quadrado, ~0 = alongado)
    aspect_ratio = float(span.min() / span.max()) if span.max() > 0 else 1.0

    # Proporção no fecho, contando os colineares sobre a borda (decisão 3 da T17)
    hull_ratio = len(convex_hull(coords, include_collinear=True)) / n

    # Entropia espacial normalizada numa grade g x g sobre o retângulo envolvente
    g = math.ceil(math.sqrt(n))
    safe_span = np.where(span > 0, span, 1.0)
    cells = np.minimum(np.floor((coords - lo) / safe_span * g), g - 1).astype(int)
    counts = np.bincount(cells[:, 0] * g + cells[:, 1], minlength=g * g)
    p = counts[counts > 0] / n
    spatial_entropy = float(-(p * np.log(p)).sum() / math.log(g * g))

    # Distâncias reais e vizinho mais próximo
    diff = coords[:, None, :] - coords[None, :, :]
    dist = np.sqrt((diff ** 2).sum(axis=2))
    nn = np.where(np.eye(n, dtype=bool), np.inf, dist).min(axis=1)
    nn_cv = float(nn.std() / nn.mean())

    # Clark-Evans: média do vizinho mais próximo / esperado para pontos aleatórios
    # numa região de mesma área (área do fecho convexo). <1 agrupado, ~1 aleatório,
    # >1 regular. Indefinido (nan) se todos os pontos estiverem alinhados (área 0).
    area = _polygon_area(coords[convex_hull(coords)])
    clark_evans = float(nn.mean() / (0.5 * math.sqrt(area / n))) if area > 0 else math.nan

    # Estatísticas da MST. O grau médio NÃO entra: em toda árvore é 2(n-1)/n.
    edges, _ = prim(dist)
    degree = np.zeros(n, dtype=int)
    for a, b in edges:
        degree[a] += 1
        degree[b] += 1

    return {
        "n": n,
        "aspect_ratio": aspect_ratio,
        "hull_ratio": hull_ratio,
        "spatial_entropy": spatial_entropy,
        "clark_evans": clark_evans,
        "mst_max_degree": int(degree.max()),
        "mst_leaf_ratio": float((degree == 1).sum() / n),
        "nn_cv": nn_cv,
        "odd_ratio": float((degree % 2 == 1).sum() / n),  # tamanho do emparelhamento
    }


def main() -> None:
    with (ROOT / "data" / "instances" / "manifest.csv").open() as f:
        manifest = sorted(csv.DictReader(f), key=lambda r: (int(r["n"]), r["instance"]))
    rows = []
    for r in manifest:
        feats = compute_features(read_tsp(ROOT / r["path"]).coords)
        rows.append({"instance": r["instance"], "kind": r["kind"], "source": r["source"],
                     **feats})
    out = ROOT / "results" / "features.csv"
    with out.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["instance", "kind", "source", *FEATURES])
        writer.writeheader()
        writer.writerows(rows)
    print(f"{len(rows)} instâncias -> {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
