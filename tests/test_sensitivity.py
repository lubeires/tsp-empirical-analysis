import numpy as np
import pandas as pd
import pytest

import analysis.sensitivity as sens
from analysis.sensitivity import (
    ALGORITHMS,
    correlations,
    partial_spearman,
    pooled_regression,
    select_by_vif,
)
from tsp.features import FEATURES


def synthetic(seed: int = 0):
    """15 instâncias: o gap de todos os algoritmos depende só de 'clark_evans'."""
    rng = np.random.default_rng(seed)
    idx = [f"i{k}" for k in range(15)]
    features = pd.DataFrame(rng.normal(size=(15, len(FEATURES))), index=idx, columns=FEATURES)
    features["n"] = np.arange(12, 42, 2)
    gaps = pd.DataFrame({a: 2 * features.clark_evans + rng.normal(0, 0.3, 15) + k
                         for k, a in enumerate(ALGORITHMS)}, index=idx)
    return features, gaps


def test_correlation_finds_the_driving_feature():
    corr = correlations(*synthetic())
    best = corr.loc[corr.groupby("algorithm").rho_partial_n.apply(lambda s: s.abs().idxmax())]
    assert (best.feature == "clark_evans").all()


def test_partial_removes_effect_that_comes_only_from_n():
    n = np.arange(15, dtype=float)
    rng = np.random.default_rng(3)
    x = n + rng.normal(0, 0.5, 15)   # característica que só acompanha N
    y = n + rng.normal(0, 0.5, 15)   # gap que só acompanha N
    from scipy.stats import spearmanr
    assert spearmanr(x, y).statistic > 0.9
    rho, p = partial_spearman(x, y, n)
    assert abs(rho) < 0.6 and p > 0.05


def test_regression_ci_separates_signal_from_noise(monkeypatch):
    monkeypatch.setattr(sens, "BOOTSTRAP", 300)
    features, gaps = synthetic(1)
    table, info = pooled_regression(features[["clark_evans", "nn_cv"]], gaps,
                                    np.random.default_rng(0))
    table = table.set_index("feature")
    assert table.loc["clark_evans", "ci_excludes_zero"]
    assert not table.loc["nn_cv", "ci_excludes_zero"]
    assert info["rows"] == 15 * 4


def test_bootstrap_resamples_instances_not_rows(monkeypatch):
    # Com uma única instância repetida, todas as 4 linhas dela precisam vir juntas:
    # se o bootstrap sorteasse linhas soltas, o número de linhas variaria
    calls = []
    original = sens.ols

    def spy(X, y):
        calls.append(len(y))
        return original(X, y)

    monkeypatch.setattr(sens, "ols", spy)
    monkeypatch.setattr(sens, "BOOTSTRAP", 20)
    features, gaps = synthetic(2)
    pooled_regression(features[["clark_evans"]], gaps, np.random.default_rng(0))
    assert all(c % len(ALGORITHMS) == 0 for c in calls)


def test_vif_drops_collinear_feature():
    rng = np.random.default_rng(4)
    a = rng.normal(size=30)
    X = pd.DataFrame({"a": a, "b": a + rng.normal(0, 0.01, 30), "c": rng.normal(size=30)})
    kept, dropped = select_by_vif(X)
    assert len(dropped) == 1 and dropped[0] in {"a", "b"} and "c" in kept


def test_saved_outputs():
    tables = sens.RESULTS / "tables"
    corr = pd.read_csv(tables / "sensitivity_spearman.csv")
    assert len(corr) == len(ALGORITHMS) * len(FEATURES)
    assert corr[corr.feature != "n"].rho_partial_n.notna().all()
    assert "trivial" not in set(corr.algorithm)
