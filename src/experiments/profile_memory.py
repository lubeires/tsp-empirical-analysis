"""Profiling de memória por sub-rotina com tracemalloc (RF5, T16, D11, D28).

Uso (na raiz do projeto):
    .venv/bin/python -m experiments.profile_memory

- Uma execução por combinação: as alocações são determinísticas (diferente do tempo).
- Aproximados e heurísticas: 15 instâncias x 5 algoritmos.
- B&B: 12 sub-instâncias + eil51 + berlin52, com Christofides como rota inicial (D28).
- Só o pico de memória é gravado: o tempo medido aqui é inflado pelo tracemalloc (D11).
- Antes de medir, cada algoritmo roda uma vez sem tracemalloc (aquecimento), para que
  importações tardias e caches das bibliotecas não entrem no pico.
- Grava cada combinação assim que termina e retoma de onde parou (P6).
"""

import argparse
import csv
import time
from pathlib import Path

from experiments.run import STRATEGIES, append_rows, load_manifest, repair_csv
from tsp.bnb import branch_and_bound
from tsp.distance import distance_matrix
from tsp.instrument import Profiler
from tsp.tsplib import read_tsp

ROOT = Path(__file__).resolve().parents[2]
FIELDS = ["instance", "n", "algorithm", "strategy", "status", "subroutine", "calls",
          "peak_bytes"]

BNB_EXTRA = {"eil51", "berlin52"}   # além das sub-instâncias (st70 não fecharia)
BNB_STRATEGY = "christofides"        # rota inicial do B&B neste profiling (D13)
BNB_TIME_LIMIT = 600.0


def profile_run(row: dict, algorithm: str, strategy: str = "",
                bnb_time_limit: float = BNB_TIME_LIMIT) -> list[dict]:
    """Executa uma combinação com Profiler(memory=True) e devolve as linhas do CSV."""
    instance = read_tsp(ROOT / row["path"])
    coords = instance.coords

    # Aquecimento sem tracemalloc
    warm_dist = distance_matrix(coords)
    STRATEGIES[strategy or algorithm](coords, warm_dist, Profiler())

    status = "ok"
    with Profiler(memory=True) as prof:
        with prof.timed("distance_matrix"):
            dist = distance_matrix(coords)
        if algorithm == "bnb":
            with prof.timed("bnb_total"):
                initial = STRATEGIES[strategy](coords, dist, prof)
                result = branch_and_bound(dist, initial,
                                          time.perf_counter() + bnb_time_limit, prof)
            status = "ok" if result.optimal else "NA"
        else:
            STRATEGIES[algorithm](coords, dist, prof)

    return [{"instance": row["instance"], "n": int(row["n"]), "algorithm": algorithm,
             "strategy": strategy, "status": status, "subroutine": r["subroutine"],
             "calls": r["calls"], "peak_bytes": r["peak_bytes"]}
            for r in prof.records()]


def combinations(manifest: list[dict]) -> list[tuple[dict, str, str]]:
    """Aproximados primeiro (rápidos), depois o B&B; ambos das menores para as maiores."""
    rows = sorted(manifest, key=lambda r: (int(r["n"]), r["instance"]))
    combos = [(r, name, "") for r in rows for name in STRATEGIES]
    combos += [(r, "bnb", BNB_STRATEGY) for r in rows
               if r["kind"] == "sub" or r["instance"] in BNB_EXTRA]
    return combos


def main() -> None:
    parser = argparse.ArgumentParser(description="Profiling de memória por sub-rotina")
    parser.add_argument("--out", type=Path, default=ROOT / "results" / "profile_memory.csv")
    parser.add_argument("--bnb-time-limit", type=float, default=BNB_TIME_LIMIT)
    args = parser.parse_args()

    repair_csv(args.out, FIELDS)
    done = set()
    if args.out.exists():
        with args.out.open() as f:
            done = {(r["instance"], r["algorithm"], r["strategy"]) for r in csv.DictReader(f)}

    combos = [c for c in combinations(load_manifest())
              if (c[0]["instance"], c[1], c[2]) not in done]
    print(f"{len(combos)} combinações pendentes", flush=True)
    for i, (row, algorithm, strategy) in enumerate(combos, 1):
        start = time.perf_counter()
        rows = profile_run(row, algorithm, strategy, args.bnb_time_limit)
        append_rows(args.out, FIELDS, rows)
        peak = max(r["peak_bytes"] for r in rows) / 1024
        print(f"[{i}/{len(combos)}] {row['instance']} {algorithm} {strategy} -> "
              f"{rows[0]['status']}, maior pico {peak:.0f} KB "
              f"({time.perf_counter() - start:.1f}s)", flush=True)


if __name__ == "__main__":
    main()
