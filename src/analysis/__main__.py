"""Refaz todas as tabelas e figuras a partir dos CSVs de resultados (T21, P5).

Uso (na raiz do projeto):
    .venv/bin/python -m analysis           # completo (bootstrap da complexidade: minutos)
    .venv/bin/python -m analysis --quick   # reaproveita os intervalos do bootstrap

Etapas: características → complexidade → warm-start e colapso → sensibilidade →
caso adversarial do limite inferior.
No fim, confere se todos os arquivos esperados foram (re)gerados nesta execução.
"""

import argparse
import sys
import time
from pathlib import Path

from analysis import adversarial, complexity, sensitivity, warmstart
from tsp import features

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results"

FIGURES = ["complexity_time_algorithms", "complexity_time_subroutines", "complexity_memory",
           "complexity_bnb_nodes", "warmstart_nodes_ratio", "warmstart_gap_vs_nodes",
           "warmstart_find_vs_prove", "collapse", "sensitivity_heatmap",
           "sensitivity_coefficients", "adversarial_structure"]
TABLES = ["complexity_time.csv", "complexity_time.tex", "complexity_memory.csv",
          "complexity_memory.tex", "complexity_bnb_nodes.csv", "complexity_bnb_nodes.tex",
          "warmstart_per_instance.csv", "warmstart_summary.csv", "warmstart_summary.tex",
          "warmstart_checks.json", "collapse.csv", "collapse.tex",
          "sensitivity_spearman.csv", "sensitivity_spearman.tex", "sensitivity_regression.csv",
          "sensitivity_regression.tex", "sensitivity_regression_info.json",
          "sensitivity_trees.csv", "sensitivity_trees.txt", "sensitivity_adversarial.csv",
          "adversarial_root.csv", "adversarial_root.tex", "bound_fix.csv",
          "bound_fix_summary.json"]


def expected_outputs() -> list[Path]:
    """Todos os arquivos que esta execução precisa gerar."""
    figures = [RESULTS / "figures" / f"{name}.{ext}" for name in FIGURES for ext in ("pdf", "png")]
    tables = [RESULTS / "tables" / name for name in TABLES]
    return [RESULTS / "features.csv", *tables, *figures]


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="Refaz todas as tabelas e figuras (T21)")
    parser.add_argument("--quick", action="store_true",
                        help="pula o bootstrap da complexidade e reaproveita os intervalos")
    args = parser.parse_args(argv)

    start = time.time()
    steps = [
        ("características", features.main),
        ("complexidade", lambda: complexity.main(["--quick"] if args.quick else [])),
        ("warm-start e colapso", warmstart.main),
        ("sensibilidade", sensitivity.main),
        ("caso adversarial", adversarial.main),
    ]
    for name, step in steps:
        t0 = time.perf_counter()
        print(f"== {name} ...", flush=True)
        step()
        print(f"== {name}: {time.perf_counter() - t0:.1f}s", flush=True)

    stale = [p for p in expected_outputs() if not p.exists() or p.stat().st_mtime < start]
    if stale:
        print("ERRO: arquivos não gerados nesta execução:", file=sys.stderr)
        for p in stale:
            print(f"  {p.relative_to(ROOT)}", file=sys.stderr)
        sys.exit(1)
    print(f"OK: {len(expected_outputs())} arquivos gerados em {time.time() - start:.0f}s")


if __name__ == "__main__":
    main()
