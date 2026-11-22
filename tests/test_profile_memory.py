from experiments.profile_memory import FIELDS, combinations, profile_run
from experiments.run import load_manifest

MANIFEST = load_manifest()
SMALL = next(r for r in MANIFEST if r["instance"] == "kroA100-n12")


def by_subroutine(rows):
    return {r["subroutine"]: r for r in rows}


def test_christofides_subroutines_have_peaks():
    rows = by_subroutine(profile_run(SMALL, "christofides"))
    expected = {"distance_matrix", "christofides", "mst", "odd_vertices",
                "matching_build", "matching", "euler", "shortcut"}
    assert expected <= set(rows)
    assert all(rows[s]["peak_bytes"] > 0 for s in expected - {"odd_vertices", "shortcut"})
    assert set(next(iter(rows.values()))) == set(FIELDS)


def test_distance_matrix_peak_at_least_matrix_size():
    # Coerência: a matriz final sozinha ocupa 8 bytes x n² (int64)
    rows = by_subroutine(profile_run(SMALL, "trivial"))
    n = int(SMALL["n"])
    assert rows["distance_matrix"]["peak_bytes"] >= 8 * n * n


def test_bnb_profile():
    rows = by_subroutine(profile_run(SMALL, "bnb", "christofides", bnb_time_limit=60))
    assert rows["bnb_total"]["status"] == "ok"
    assert {"bnb_search", "root_bound", "christofides"} <= set(rows)
    assert rows["bnb_total"]["peak_bytes"] >= rows["root_bound"]["peak_bytes"] > 0


def test_combinations():
    combos = combinations(MANIFEST)
    bnb = [c for c in combos if c[1] == "bnb"]
    assert len(combos) == 15 * 5 + 14
    assert {c[0]["instance"] for c in bnb} >= {"eil51", "berlin52"}
    assert "st70" not in {c[0]["instance"] for c in bnb}
