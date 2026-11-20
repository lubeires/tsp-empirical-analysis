from pathlib import Path

import pytest

from tsp.tsplib import read_tour, read_tsp

TSPLIB_DIR = Path(__file__).resolve().parents[1] / "data" / "tsplib"


def test_read_berlin52():
    instance = read_tsp(TSPLIB_DIR / "berlin52.tsp")
    assert instance.name == "berlin52"
    assert instance.n == 52
    assert tuple(instance.coords[0]) == (565.0, 575.0)


def test_rejects_non_euc_2d(tmp_path):
    path = tmp_path / "geo.tsp"
    path.write_text(
        "NAME: geo\nTYPE: TSP\nDIMENSION: 2\nEDGE_WEIGHT_TYPE: GEO\n"
        "NODE_COORD_SECTION\n1 0 0\n2 1 1\nEOF\n"
    )
    with pytest.raises(ValueError, match="EUC_2D"):
        read_tsp(path)


def test_read_tour_is_zero_based_permutation():
    tour = read_tour(TSPLIB_DIR / "berlin52.opt.tour")
    assert sorted(tour) == list(range(52))
