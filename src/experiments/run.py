"""Executor dos experimentos (RF4, T13, D24).

Uso (na raiz do projeto):
    .venv/bin/python -m experiments.run bnb    --workers 6 --time-limit 1800
    .venv/bin/python -m experiments.run approx --repetitions 30 [--gc both|on|off]

Grupos:
- bnb:    uma execução por (instância, estratégia de warm-start), em paralelo (D12).
- approx: um processo por (instância, algoritmo), em sequência (D12): uma execução de
          aquecimento descartada e depois as repetições medidas.

Robustez (P6):
- Cada tarefa roda num processo próprio (contexto spawn: interpretador limpo, então o
  pico de memória max_rss_kb reflete só a execução, sem herdar a memória do pai).
- O resultado volta por um Pipe exclusivo do processo; matar um processo não corrompe
  a comunicação dos demais. O resultado é lido ANTES do join(), para o filho nunca
  ficar bloqueado esperando o pai esvaziar o Pipe.
- Processo que passa de time_limit + margem de segurança é morto (status killed).
- Só o processo principal escreve nos CSVs, e cada tarefa é gravada assim que termina.
- Retomada: a última linha incompleta do CSV é descartada; tarefas concluídas (ok/NA)
  são puladas; tarefas killed/error são repetidas uma única vez.
- Tarefas ordenadas das instâncias menores para as maiores.
- Grupo approx com e sem coletor de lixo (opção --gc, padrão both): as duas variantes
  são intercaladas por (instância, algoritmo), alternando qual vem primeiro, para que
  variações de carga da máquina afetem as duas igualmente (D26, D27).
- Laço interno (approx): cada medição executa o algoritmo k vezes seguidas, com k
  calibrado para somar pelo menos MIN_MEASURE_S, e divide o tempo por k (como o timeit).
  Tempos abaixo de 1 ms ficam perto da resolução do relógio e do tamanho de uma
  interrupção do sistema operacional (D27).
"""

import argparse
import csv
import gc
import json
import math
import multiprocessing as mp
import os
import resource
import sys
import time
import traceback
import uuid
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from multiprocessing.connection import wait
from pathlib import Path

from tsp.approx import christofides, twice_around_the_tree
from tsp.bnb import branch_and_bound
from tsp.distance import distance_matrix, tour_cost
from tsp.heuristics import convex_hull_insertion, nearest_neighbor, trivial_tour
from tsp.instrument import Profiler
from tsp.tsplib import read_tsp

ROOT = Path(__file__).resolve().parents[2]

# Rotas iniciais do B&B e, ao mesmo tempo, os algoritmos do grupo approx
STRATEGIES = {
    "trivial": trivial_tour,
    "nn": nearest_neighbor,
    "hull": convex_hull_insertion,
    "twice_around": twice_around_the_tree,
    "christofides": christofides,
}

RUN_FIELDS = [
    "run_id", "instance", "n", "group", "algorithm", "strategy", "repetition",
    "status", "time_limit", "gc_enabled", "inner_loops", "cost", "time_total", "time_heuristic",
    "nodes_expanded", "nodes_pruned", "max_depth", "ub_improvements",
    "bound_iterations", "root_bound", "gc_collections", "max_rss_kb",
    "ub_history", "tour", "started_at",
]
PROFILE_FIELDS = ["run_id", "instance", "algorithm", "strategy", "repetition",
                  "subroutine", "calls", "time_s"]

DONE = {"ok", "NA"}          # concluídas: não rodam de novo
RETRYABLE = {"killed", "error"}
MAX_ATTEMPTS = 2             # killed/error: repete uma única vez
SAFETY_MARGIN = 60.0         # segundos além do time_limit antes de matar o processo
MIN_MEASURE_S = 0.02         # duração mínima de cada medição com laço interno (D27)
MAX_INNER_LOOPS = 10_000


@dataclass
class Task:
    group: str
    instance: str
    n: int
    path: str
    algorithm: str
    strategy: str
    repetitions: int
    time_limit: float
    gc_enabled: bool = True

    def keys(self) -> list[tuple]:
        """Chaves (instance, algorithm, strategy, repetition, gc_enabled) das linhas da tarefa."""
        return [(self.instance, self.algorithm, self.strategy, str(r), str(self.gc_enabled))
                for r in range(self.repetitions)]


# ---------------------------------------------------------------------------
# Montagem das tarefas
# ---------------------------------------------------------------------------

def load_manifest() -> list[dict]:
    with (ROOT / "data" / "instances" / "manifest.csv").open() as f:
        return list(csv.DictReader(f))


def build_tasks(group: str, manifest: list[dict], time_limit: float, repetitions: int = 5,
                instances=None, strategies=None, gc_variants=(True,)) -> list[Task]:
    """Tarefas do grupo, das instâncias menores para as maiores.

    approx: uma tarefa por variante de coletor de lixo em `gc_variants`, intercaladas
    por (instância, algoritmo) e alternando a ordem a cada par (D27).
    """
    rows = [r for r in manifest if instances is None or r["instance"] in instances]
    rows.sort(key=lambda r: (int(r["n"]), r["instance"]))
    names = [s for s in STRATEGIES if strategies is None or s in strategies]
    tasks = []
    pair = 0
    for row in rows:
        for name in names:
            if group == "bnb":
                tasks.append(Task("bnb", row["instance"], int(row["n"]), row["path"],
                                  "bnb", name, 1, time_limit))
            else:
                variants = list(gc_variants) if pair % 2 == 0 else list(gc_variants)[::-1]
                pair += 1
                for gc_enabled in variants:
                    tasks.append(Task("approx", row["instance"], int(row["n"]), row["path"],
                                      name, "", repetitions, time_limit, gc_enabled))
    return tasks


# ---------------------------------------------------------------------------
# Processos filhos (rodam com spawn: precisam ser funções de nível de módulo)
# ---------------------------------------------------------------------------

def _max_rss_kb() -> int:
    # No Linux, ru_maxrss vem em KB
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss


def _base_row(task: Task, repetition: int, run_id: str) -> dict:
    return {
        "run_id": run_id, "instance": task.instance, "n": task.n, "group": task.group,
        "algorithm": task.algorithm, "strategy": task.strategy, "repetition": repetition,
        "time_limit": task.time_limit, "gc_enabled": task.gc_enabled, "inner_loops": 1,
        "started_at": datetime.now().isoformat(timespec="seconds"),
    }


def _profile_rows(prof: Profiler, row: dict) -> list[dict]:
    return [{"run_id": row["run_id"], "instance": row["instance"],
             "algorithm": row["algorithm"], "strategy": row["strategy"],
             "repetition": row["repetition"], "subroutine": r["subroutine"],
             "calls": r["calls"], "time_s": r["time_s"]} for r in prof.records()]


def bnb_worker(conn, task: Task) -> None:
    """Uma execução do B&B: heurística de warm-start + busca, dentro do mesmo prazo."""
    try:
        instance = read_tsp(ROOT / task.path)
        prof = Profiler()
        with prof.timed("distance_matrix"):  # pré-processamento: fora do time_total
            dist = distance_matrix(instance.coords)
        row = _base_row(task, 0, uuid.uuid4().hex)

        start = time.perf_counter()
        initial = STRATEGIES[task.strategy](instance.coords, dist, prof)
        time_heuristic = time.perf_counter() - start
        result = branch_and_bound(dist, initial, start + task.time_limit, prof)
        time_total = time.perf_counter() - start

        row.update({
            "status": "ok" if result.optimal else "NA",
            "cost": result.cost, "time_total": time_total, "time_heuristic": time_heuristic,
            "nodes_expanded": result.nodes_expanded, "nodes_pruned": result.nodes_pruned,
            "max_depth": result.max_depth, "ub_improvements": result.ub_improvements,
            "bound_iterations": result.bound_iterations, "root_bound": result.root_bound,
            "gc_collections": prof.gc_collections(), "max_rss_kb": _max_rss_kb(),
            "ub_history": json.dumps([[round(t, 4), c] for t, c in result.ub_history]),
            "tour": " ".join(map(str, result.tour)),
        })
        conn.send({"rows": [row], "profile": _profile_rows(prof, row)})
    except Exception:
        conn.send({"error": traceback.format_exc()})
    finally:
        conn.close()


def approx_worker(conn, task: Task) -> None:
    """Um processo por (instância, algoritmo, variante de GC): aquecimento + repetições.

    Cada repetição executa o algoritmo `inner_loops` = k vezes seguidas (k calibrado
    para somar >= MIN_MEASURE_S) e grava o tempo POR EXECUÇÃO (total / k). No profile,
    calls e time_s também são por execução. gc_collections é o total das k execuções
    (contagem de eventos); por execução, divida por inner_loops.
    """
    try:
        instance = read_tsp(ROOT / task.path)
        dist = distance_matrix(instance.coords)
        algorithm = STRATEGIES[task.algorithm]
        # Aquecimento: importações tardias, caches etc. ficam fora das medições
        algorithm(instance.coords, dist, Profiler())
        if not task.gc_enabled:
            # Variante sem coletor de lixo (D26): coleta o que houver e desliga
            # durante as repetições medidas. O processo termina logo depois.
            gc.collect()
            gc.disable()

        # Calibração do laço interno: uma execução medida isoladamente
        start = time.perf_counter()
        algorithm(instance.coords, dist, Profiler())
        single = time.perf_counter() - start
        k = max(1, min(MAX_INNER_LOOPS, math.ceil(MIN_MEASURE_S / max(single, 1e-9))))

        rows, profile = [], []
        for rep in range(task.repetitions):
            row = _base_row(task, rep, uuid.uuid4().hex)
            prof = Profiler()
            start = time.perf_counter()
            for _ in range(k):
                tour = algorithm(instance.coords, dist, prof)
            elapsed = (time.perf_counter() - start) / k
            row.update({
                "status": "ok", "inner_loops": k, "cost": tour_cost(tour, dist),
                "time_total": elapsed, "time_heuristic": elapsed,
                "gc_collections": prof.gc_collections(), "tour": " ".join(map(str, tour)),
            })
            rows.append(row)
            for prof_row in _profile_rows(prof, row):  # por execução
                prof_row["calls"] //= k
                prof_row["time_s"] /= k
                profile.append(prof_row)
        rss = _max_rss_kb()  # pico do processo inteiro (igual para as repetições)
        for row in rows:
            row["max_rss_kb"] = rss
        conn.send({"rows": rows, "profile": profile})
    except Exception:
        conn.send({"error": traceback.format_exc()})
    finally:
        conn.close()


WORKERS = {"bnb": bnb_worker, "approx": approx_worker}


# ---------------------------------------------------------------------------
# CSVs: reparo, retomada e escrita
# ---------------------------------------------------------------------------

def repair_csv(path: Path, fields: list[str]) -> None:
    """Descarta a última linha se estiver incompleta e confere o cabeçalho."""
    if not path.exists() or path.stat().st_size == 0:
        return
    text = path.read_text()
    if not text.endswith("\n"):
        kept = text[: text.rfind("\n") + 1]
        print(f"[aviso] {path.name}: última linha incompleta descartada", file=sys.stderr)
        path.write_text(kept)
        text = kept
    header = text.splitlines()[0] if text else ""
    if header and header.split(",") != fields:
        raise ValueError(f"{path}: cabeçalho diferente do esperado (esquema mudou?)")


def append_rows(path: Path, fields: list[str], rows: list[dict]) -> None:
    """Acrescenta linhas e força a gravação no disco (fsync)."""
    new = not path.exists() or path.stat().st_size == 0
    with path.open("a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        if new:
            writer.writeheader()
        writer.writerows(rows)
        f.flush()
        os.fsync(f.fileno())


def pending_tasks(tasks: list[Task], runs_path: Path) -> list[Task]:
    """Tarefas que ainda precisam rodar, segundo o runs.csv existente."""
    done, failures = set(), Counter()
    if runs_path.exists():
        with runs_path.open() as f:
            for row in csv.DictReader(f):
                key = (row["instance"], row["algorithm"], row["strategy"], row["repetition"],
                       row["gc_enabled"])
                if row["status"] in DONE:
                    done.add(key)
                elif row["status"] in RETRYABLE:
                    failures[key] += 1
    result = []
    for task in tasks:
        keys = task.keys()
        if all(k in done for k in keys):
            continue
        if max(failures[k] for k in keys) >= MAX_ATTEMPTS:
            print(f"[aviso] {task.instance}/{task.algorithm}/{task.strategy}: "
                  f"desistindo após {MAX_ATTEMPTS} falhas", file=sys.stderr)
            continue
        result.append(task)
    return result


def _failure_rows(task: Task, status: str, elapsed: float) -> list[dict]:
    rows = []
    for rep in range(task.repetitions):
        row = _base_row(task, rep, uuid.uuid4().hex)
        row.update({"status": status, "time_total": elapsed})
        rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# Laço principal
# ---------------------------------------------------------------------------

def run_tasks(tasks: list[Task], out_dir: Path, workers: int,
              safety_margin: float = SAFETY_MARGIN, worker_fn=None) -> None:
    """Roda as tarefas pendentes com até `workers` processos ao mesmo tempo."""
    out_dir.mkdir(parents=True, exist_ok=True)
    runs_path, profile_path = out_dir / "runs.csv", out_dir / "profile.csv"
    repair_csv(runs_path, RUN_FIELDS)
    repair_csv(profile_path, PROFILE_FIELDS)

    queue = pending_tasks(tasks, runs_path)
    total = len(queue)
    print(f"{total} tarefas pendentes ({len(tasks) - total} já concluídas)", flush=True)
    ctx = mp.get_context("spawn")
    running = {}  # conexão -> (processo, tarefa, início)
    finished = 0

    def finish(conn, status: str, message: dict | None) -> None:
        nonlocal finished
        proc, task, started = running.pop(conn)
        elapsed = time.monotonic() - started
        if message is not None and "rows" in message:
            # profile primeiro: a linha do runs.csv é a marca de tarefa concluída
            append_rows(profile_path, PROFILE_FIELDS, message["profile"])
            append_rows(runs_path, RUN_FIELDS, message["rows"])
            status = message["rows"][0]["status"]
        else:
            if message is not None:
                print(message["error"], file=sys.stderr)
            append_rows(runs_path, RUN_FIELDS, _failure_rows(task, status, elapsed))
        finished += 1
        print(f"[{finished}/{total}] {task.instance} {task.algorithm} {task.strategy} "
              f"-> {status} ({elapsed:.1f}s)", flush=True)

    while queue or running:
        while queue and len(running) < workers:
            task = queue.pop(0)
            receiver, sender = ctx.Pipe(duplex=False)
            fn = worker_fn or WORKERS[task.group]
            proc = ctx.Process(target=fn, args=(sender, task))
            proc.start()
            sender.close()  # o pai só lê; fechar aqui permite detectar EOF se o filho morrer
            running[receiver] = (proc, task, time.monotonic())

        for conn in wait(list(running), timeout=1.0):
            proc = running[conn][0]
            try:
                message = conn.recv()  # lê ANTES do join
            except EOFError:
                message = None  # filho morreu sem enviar nada
            proc.join()
            finish(conn, "error", message)

        for conn, (proc, task, started) in list(running.items()):
            if time.monotonic() - started > task.time_limit + safety_margin:
                proc.kill()
                proc.join()
                finish(conn, "killed", None)


def main() -> None:
    parser = argparse.ArgumentParser(description="Executor dos experimentos do TP2")
    parser.add_argument("group", choices=["bnb", "approx"])
    parser.add_argument("--workers", type=int, default=6,
                        help="processos em paralelo (só para bnb; approx é sempre 1)")
    parser.add_argument("--time-limit", type=float, default=1800.0)
    parser.add_argument("--repetitions", type=int, default=30)
    parser.add_argument("--gc", choices=["on", "off", "both"], default="both",
                        help="approx: coletor de lixo ligado, desligado ou as duas variantes "
                             "intercaladas (padrão both); bnb: sempre ligado")
    parser.add_argument("--out-dir", type=Path, default=ROOT / "results")
    parser.add_argument("--instances", nargs="*", help="filtra instâncias (padrão: todas)")
    parser.add_argument("--strategies", nargs="*", help="filtra estratégias/algoritmos")
    args = parser.parse_args()

    tasks = build_tasks(args.group, load_manifest(), args.time_limit, args.repetitions,
                        args.instances, args.strategies,
                        gc_variants={"on": (True,), "off": (False,), "both": (True, False)}[args.gc])
    workers = args.workers if args.group == "bnb" else 1  # D12: approx em sequência
    run_tasks(tasks, args.out_dir, workers)


if __name__ == "__main__":
    main()
