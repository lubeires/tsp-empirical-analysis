"""Testes do executor (T13). Gravam numa pasta temporária, sem tocar em results/."""

import csv
import time

from experiments.run import (
    PROFILE_FIELDS,
    RUN_FIELDS,
    build_tasks,
    load_manifest,
    run_tasks,
)

MANIFEST = load_manifest()


def read_rows(path):
    with path.open() as f:
        return list(csv.DictReader(f))


def hang_worker(conn, task):
    """Tarefa falsa que nunca responde (para testar o limite de segurança).

    Precisa ser de nível de módulo: com spawn, o filho importa esta função pelo nome.
    """
    time.sleep(60)


def test_tasks_sorted_by_size():
    tasks = build_tasks("bnb", MANIFEST, time_limit=10)
    assert len(tasks) == 15 * 5
    sizes = [t.n for t in tasks]
    assert sizes == sorted(sizes)


def test_bnb_short_limit_gives_na_with_counters_and_resumes(tmp_path):
    # Critério de pronto da T13: prazo curto gera NA com os contadores preenchidos
    tasks = build_tasks("bnb", MANIFEST, time_limit=1.0,
                        instances=["kroA100-n33", "st70"], strategies=["trivial"])
    run_tasks(tasks, tmp_path, workers=2)
    rows = read_rows(tmp_path / "runs.csv")
    assert len(rows) == 2
    for row in rows:
        assert row["status"] == "NA"
        assert int(row["nodes_expanded"]) >= 1
        assert float(row["time_limit"]) == 1.0
        assert int(row["max_rss_kb"]) > 0
        assert float(row["time_total"]) < 2.0
    profile = read_rows(tmp_path / "profile.csv")
    assert {p["run_id"] for p in profile} == {r["run_id"] for r in rows}

    # Retomada: rodar de novo não duplica nada
    run_tasks(tasks, tmp_path, workers=2)
    assert len(read_rows(tmp_path / "runs.csv")) == 2


def test_killed_is_retried_once(tmp_path):
    tasks = build_tasks("bnb", MANIFEST, time_limit=0.5,
                        instances=["kroA100-n12"], strategies=["trivial"])
    for _ in range(3):
        run_tasks(tasks, tmp_path, workers=1, safety_margin=1.0, worker_fn=hang_worker)
    statuses = [r["status"] for r in read_rows(tmp_path / "runs.csv")]
    assert statuses == ["killed", "killed"]  # 1ª tentativa + 1 repetição; a 3ª não roda


def test_incomplete_last_line_is_discarded(tmp_path):
    tasks = build_tasks("bnb", MANIFEST, time_limit=5.0,
                        instances=["kroA100-n12"], strategies=["trivial", "nn"])
    run_tasks(tasks, tmp_path, workers=2)
    runs = tmp_path / "runs.csv"
    # Simula queda no meio da escrita: corta a última linha pela metade
    text = runs.read_text()
    runs.write_text(text[: len(text) - 40])
    run_tasks(tasks, tmp_path, workers=2)
    rows = read_rows(runs)
    assert len(rows) == 2
    assert all(len(r) == len(RUN_FIELDS) and r["status"] == "ok" for r in rows)


def test_approx_group(tmp_path):
    tasks = build_tasks("approx", MANIFEST, time_limit=60, repetitions=5,
                        instances=["kroA100-n12"])
    run_tasks(tasks, tmp_path, workers=1)
    rows = read_rows(tmp_path / "runs.csv")
    assert len(rows) == 5 * 5  # 5 algoritmos x 5 repetições (aquecimento não gravado)
    assert sorted({r["repetition"] for r in rows}) == ["0", "1", "2", "3", "4"]
    assert all(r["status"] == "ok" and int(r["max_rss_kb"]) > 0 for r in rows)
    profile = read_rows(tmp_path / "profile.csv")
    assert set(profile[0]) == set(PROFILE_FIELDS)
    assert {p["run_id"] for p in profile} == {r["run_id"] for r in rows}


def test_gc_variants_interleaved_with_alternating_order():
    tasks = build_tasks("approx", MANIFEST, time_limit=60, instances=["kroA100-n12"],
                        strategies=["trivial", "nn", "hull"], gc_variants=(True, False))
    # Pares por algoritmo, alternando qual variante vem primeiro
    assert [(t.algorithm, t.gc_enabled) for t in tasks] == [
        ("trivial", True), ("trivial", False),
        ("nn", False), ("nn", True),
        ("hull", True), ("hull", False),
    ]


def test_gc_variants_coexist_and_resume(tmp_path):
    tasks = build_tasks("approx", MANIFEST, time_limit=60, repetitions=3,
                        instances=["kroA100-n12"], strategies=["christofides"],
                        gc_variants=(True, False))
    run_tasks(tasks, tmp_path, workers=1)
    rows = read_rows(tmp_path / "runs.csv")
    assert len(rows) == 6
    off = [r for r in rows if r["gc_enabled"] == "False"]
    assert len(off) == 3 and all(r["gc_collections"] == "0" for r in off)
    # Retomada distingue as variantes: nada roda de novo
    run_tasks(tasks, tmp_path, workers=1)
    assert len(read_rows(tmp_path / "runs.csv")) == 6


def test_inner_loops_for_fast_algorithms(tmp_path):
    # Rota trivial leva microssegundos: k precisa ser grande; o tempo gravado é por execução
    tasks = build_tasks("approx", MANIFEST, time_limit=60, repetitions=2,
                        instances=["kroA100-n12"], strategies=["trivial"])
    run_tasks(tasks, tmp_path, workers=1)
    rows = read_rows(tmp_path / "runs.csv")
    k = int(rows[0]["inner_loops"])
    assert k > 100
    assert float(rows[0]["time_total"]) < 0.001
    profile = read_rows(tmp_path / "profile.csv")
    assert all(p["calls"] == "1" for p in profile)  # profile normalizado por execução
