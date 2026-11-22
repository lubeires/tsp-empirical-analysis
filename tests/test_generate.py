import csv

import numpy as np

from tsp.generate import TSPLIB_DIR, generate
from tsp.tsplib import Instance, read_tsp, write_tsp


def test_generation_is_deterministic(tmp_path):
    # Critério de pronto da T04: duas gerações produzem arquivos idênticos
    first, second = tmp_path / "a", tmp_path / "b"
    generate(out_dir=first)
    generate(out_dir=second)
    files = sorted(p.name for p in first.iterdir())
    assert files == sorted(p.name for p in second.iterdir())
    for name in files:
        assert (first / name).read_bytes() == (second / name).read_bytes()


def test_sub_instances_match_source_points(tmp_path):
    rows = generate(out_dir=tmp_path)
    for row in rows:
        if row["kind"] != "sub":
            continue
        sub = read_tsp(tmp_path / f"{row['instance']}.tsp")
        source = read_tsp(TSPLIB_DIR / f"{row['source']}.tsp")
        indices = [int(i) for i in row["indices"].split()]
        assert len(set(indices)) == row["n"] == sub.n
        assert np.array_equal(sub.coords, source.coords[indices])


def test_manifest_composition(tmp_path):
    generate(out_dir=tmp_path)
    with (tmp_path / "manifest.csv").open() as f:
        rows = list(csv.DictReader(f))
    # Conjunto de teste (sub + full): 15 instâncias, 80% com N <= 40 (enunciado)
    test_set = [r for r in rows if r["kind"] in ("sub", "full")]
    assert len(test_set) == 15
    assert sum(int(r["n"]) <= 40 for r in test_set) == 12
    assert all(r["optimum"] for r in rows if r["kind"] == "full")
    # Teste de estresse fora do conjunto (D30)
    stress = [r for r in rows if r["kind"] == "stress"]
    assert [(r["instance"], r["n"]) for r in stress] == [("rd100-n75", "75")]


def test_write_read_roundtrip(tmp_path):
    coords = np.array([[0.1, 1e-7], [551.2, 996.4], [1234.5678901234, 3.0]])
    path = tmp_path / "x.tsp"
    write_tsp(Instance("x", coords), path)
    assert np.array_equal(read_tsp(path).coords, coords)
