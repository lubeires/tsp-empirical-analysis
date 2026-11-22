import json
import math

import numpy as np
import pandas as pd
import pytest

from analysis.warmstart import (
    RESULTS,
    collapse_n,
    holm,
    monotonicity_violations,
    per_instance,
    root_bound_spread,
)


def synthetic():
    """Uma instância, três estratégias, ótimo = 100."""
    bnb = pd.DataFrame({
        "instance": ["x"] * 3, "n": [10] * 3, "strategy": ["trivial", "nn", "hull"],
        "status": ["ok"] * 3, "cost": [100] * 3,
        "nodes_expanded": [40, 20, 5], "nodes_pruned": [60, 30, 5], "max_depth": [10] * 3,
        "time_total": [4.0, 2.0, 1.0], "time_heuristic": [0.0, 0.1, 0.2],
        "ub_history": [json.dumps([[1.0, 120], [3.0, 100]]), json.dumps([[1.5, 100]]), "[]"],
        "root_bound": [95.0] * 3,
    })
    approx = pd.DataFrame({"instance": ["x"] * 3, "algorithm": ["trivial", "nn", "hull"],
                           "cost": [200, 110, 100]})
    return per_instance(bnb, approx, {"x": "sub"})


def test_metrics():
    df = synthetic().set_index("strategy")
    assert df.loc["trivial", "initial_gap_pct"] == pytest.approx(100.0)
    assert df.loc["hull", "initial_gap_pct"] == pytest.approx(0.0)
    assert df.loc["nn", "nodes_ratio"] == pytest.approx(0.5)
    assert df.loc["hull", "time_ratio"] == pytest.approx(0.25)
    assert df.loc["trivial", "prune_rate"] == pytest.approx(0.6)
    assert df.loc["trivial", "t_found"] == 3.0 and df.loc["trivial", "t_prove"] == 1.0
    assert df.loc["hull", "t_found"] == 0.0  # rota inicial já era a ótima


def test_monotonicity_detects_violation():
    df = synthetic()
    assert monotonicity_violations(df).empty
    df.loc[df.strategy == "hull", "nodes_expanded"] = 50  # melhor início, mais nós
    assert len(monotonicity_violations(df)) == 2  # viola contra trivial e contra nn


def test_holm():
    assert holm([0.01, 0.04, 0.03]) == pytest.approx([0.03, 0.06, 0.06])


def test_collapse_recovers_exponential():
    n = np.arange(10, 60, 5)
    times = 0.01 * 1.2 ** n
    fit = collapse_n(n, times, limit=1800)
    assert fit["growth_per_vertex"] == pytest.approx(1.2)
    assert fit["n_collapse"] == pytest.approx(math.log(1800 / 0.01) / math.log(1.2))


def test_real_data_consistency():
    # Integração: tabela gerada por `python -m analysis.warmstart`
    df = pd.read_csv(RESULTS / "tables" / "warmstart_per_instance.csv",
                     keep_default_na=False, na_values=[""])
    test = df[df.kind.isin(["sub", "full"])]
    assert len(test) == 15 * 5
    assert monotonicity_violations(test).empty      # D21: monotonicidade nos dados reais
    assert root_bound_spread(test) == 0.0           # D21: raiz independe da rota inicial
    assert (test.opt_proven).all()


def test_na_status_survives_csv_reading():
    # Regressão (T19): o pandas lê o texto "NA" como ausente por padrão, o que
    # descartava as execuções que estouraram o prazo. Elas precisam chegar à análise.
    df = pd.read_csv(RESULTS / "tables" / "warmstart_per_instance.csv",
                     keep_default_na=False, na_values=[""])
    stress = df[df.kind == "stress"]
    assert len(stress) == 5 and (stress.status == "NA").all()
    collapse = pd.read_csv(RESULTS / "tables" / "collapse.csv",
                           keep_default_na=False, na_values=[""])
    assert (collapse.n75_status == "NA").all()
