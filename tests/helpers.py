"""Funções auxiliares usadas só pelos testes (P3 da constituição)."""

import csv
import math
from itertools import permutations
from pathlib import Path

from tsp.tsplib import read_tsp

ROOT = Path(__file__).resolve().parents[1]


def assert_valid_tour(tour, n: int) -> None:
    """A rota deve visitar cada vértice 0..n-1 exatamente uma vez."""
    assert sorted(int(v) for v in tour) == list(range(n)), "rota não é uma permutação"


def independent_cost(tour, coords) -> int:
    """Custo calculado direto das coordenadas, sem distance_matrix nem tour_cost.

    Serve para pegar erros nessas duas funções: se elas estiverem erradas,
    os dois cálculos não batem.
    """
    total = 0
    for i in range(len(tour)):
        a, b = coords[tour[i]], coords[tour[(i + 1) % len(tour)]]
        d = math.hypot(a[0] - b[0], a[1] - b[1])
        total += int(math.floor(d + 0.5))  # nint da TSPLIB
    return total


def brute_force(dist) -> int:
    """Custo ótimo por força bruta: fixa o vértice 0 e testa as (n-1)! ordens.

    Só para n <= 9 (até 40.320 rotas).
    """
    n = len(dist)
    assert n <= 9, "força bruta só para n <= 9"
    best = None
    for perm in permutations(range(1, n)):
        tour = (0, *perm)
        cost = sum(int(dist[tour[i], tour[(i + 1) % n]]) for i in range(n))
        if best is None or cost < best:
            best = cost
    return best


def load_test_instances():
    """As 15 instâncias de teste do manifesto: lista de (nome, Instance)."""
    with (ROOT / "data" / "instances" / "manifest.csv").open() as f:
        rows = list(csv.DictReader(f))
    return [(r["instance"], read_tsp(ROOT / r["path"])) for r in rows]
