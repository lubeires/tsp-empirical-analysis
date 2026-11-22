import numpy as np
import pandas as pd
import pytest

import analysis.complexity as cx
from analysis.complexity import (
    MEMORY_SERIES,
    TIME_SERIES,
    bootstrap_exponent,
    fit_exponential,
    fit_models,
    fit_power,
)

N = np.array([12, 16, 20, 24, 30, 36, 40, 51, 70], dtype=float)


def test_quadratic_data_picks_n2_and_exponent_2():
    rng = np.random.default_rng(0)
    y = 3e-6 * N**2 * rng.normal(1, 0.02, size=len(N))  # ruído relativo de 2%
    rows = fit_models(N, y)
    assert next(r for r in rows if r["best"])["model"] == "n^2"
    assert fit_power(N, y)[1] == pytest.approx(2, abs=0.15)


def test_cubic_with_overhead_picks_n3():
    # Custo fixo + termo cúbico: o modelo com constante precisa achar n^3
    y = 1e-4 + 2e-9 * N**3
    assert next(r for r in fit_models(N, y) if r["best"])["model"] == "n^3"


def test_exponential_nodes():
    nodes = 2 * 1.3 ** N
    fit = fit_exponential(N, nodes)
    assert fit["b"] == pytest.approx(1.3, rel=1e-6)
    assert fit["a"] == pytest.approx(2, rel=1e-6)
    assert fit["r2_log"] == pytest.approx(1.0)


def test_bootstrap_interval_contains_true_exponent(monkeypatch):
    monkeypatch.setattr(cx, "BOOTSTRAP", 200)
    rng = np.random.default_rng(1)
    reps = [5e-6 * n**2 * rng.lognormal(0, 0.2, size=30) for n in N]  # ruído de ~20%
    lo, hi = bootstrap_exponent(N, reps, np.random.default_rng(2))
    assert lo < 2 < hi


def test_saved_tables_are_complete():
    # Integração: as tabelas geradas por `python -m analysis.complexity`
    tables = cx.RESULTS / "tables"
    time_fits = pd.read_csv(tables / "complexity_time.csv")
    memory_fits = pd.read_csv(tables / "complexity_memory.csv")
    nodes = pd.read_csv(tables / "complexity_bnb_nodes.csv")
    assert set(time_fits.series) == {s for s, *_ in TIME_SERIES}
    assert set(memory_fits.series) == {s for s, *_ in MEMORY_SERIES}
    assert len(nodes) == 5 and (nodes.points == 15).all()  # sem a instância de estresse
    assert time_fits.groupby("series").best.sum().eq(1).all()
    assert not time_fits[["a", "c", "r2", "rmse_rel_pct"]].isna().any().any()
