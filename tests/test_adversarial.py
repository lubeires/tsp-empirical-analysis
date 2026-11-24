import numpy as np
import pandas as pd
import pytest
from test_bnb import best_completion, random_instance, random_partial_path

from analysis.adversarial import RESULTS, lower_bound_repeated, root_structure
from tsp.bnb import lower_bound


@pytest.mark.parametrize("seed", range(30))
def test_fixed_bound_is_never_weaker_than_first_version(seed):
    # D35: o limite corrigido continua válido e nunca é mais fraco que a 1ª versão
    coords, dist = random_instance(seed, n=8)
    path, path_cost, unvisited, rng = random_partial_path(seed, dist)
    best = best_completion(dist, path)
    for pi in (np.zeros(len(unvisited)), rng.uniform(-300, 300, size=len(unvisited))):
        old, _ = lower_bound_repeated(dist, path[0], path[-1], path_cost, unvisited, pi)
        new, _ = lower_bound(dist, path[0], path[-1], path_cost, unvisited, pi)
        assert old - 1e-9 <= new <= best + 1e-9


def test_root_uses_two_distinct_edges():
    # D35: na raiz (first == last) a 1ª versão repetia a aresta do vértice 0
    _, dist = random_instance(0, n=9)
    fixed = root_structure(dist)
    ends = [e for e in fixed["edges"] if 0 in e]
    assert ends[0] != ends[1] and fixed["degree"][0] == 2
    _, degree = lower_bound(dist, 0, 0, 0, np.arange(1, 9), np.zeros(8))
    assert degree.sum() == 2 * 8  # 7 arestas da AGM + 2 do vértice 0, sem repetição
    old = root_structure(dist, lower_bound_repeated)
    ends = [e for e in old["edges"] if 0 in e]
    assert ends[0] == ends[1] and old["degree"].max() >= 3


def test_root_structure_reproduces_official_runs():
    # A análise refaz o subgradiente da raiz: tem que dar o mesmo limite do B&B oficial
    table = pd.read_csv(RESULTS / "tables" / "adversarial_root.csv").set_index("instance")
    runs = pd.read_csv(RESULTS / "runs.csv", keep_default_na=False, na_values=[""])
    official = runs[runs.group == "bnb"].groupby("instance").root_bound.first()
    assert np.allclose(table.root_bound, official[table.index])
