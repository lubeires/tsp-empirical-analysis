import numpy as np
import pandas as pd

import analysis.complexity as cx
from analysis.__main__ import FIGURES, TABLES, expected_outputs


def test_expected_outputs():
    outputs = expected_outputs()
    assert len(FIGURES) == 11 and len(TABLES) == 24
    assert len(outputs) == 1 + 24 + 11 * 2  # features + tabelas + figuras em pdf e png
    assert len(set(outputs)) == len(outputs)


def test_quick_mode_skips_bootstrap(monkeypatch):
    def boom(*args, **kwargs):
        raise AssertionError("o modo --quick não pode rodar o bootstrap")

    monkeypatch.setattr(cx, "bootstrap_exponent", boom)
    n = np.array([12, 20, 30, 40, 51, 70])
    samples = {"nn": pd.DataFrame({"n": np.repeat(n, 3),
                                   "value": np.repeat(1e-6 * n**2, 3)})}
    previous = pd.DataFrame({"series": ["nn"], "model": ["a*n^b"],
                             "b_ci_low": [1.9], "b_ci_high": [2.1]})
    fits = cx.analyze_time(samples, np.random.default_rng(0), previous)
    row = fits[fits.model == "a*n^b"].iloc[0]
    assert (row.b_ci_low, row.b_ci_high) == (1.9, 2.1)
