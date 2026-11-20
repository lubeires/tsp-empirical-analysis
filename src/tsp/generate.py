"""Gera as 12 sub-instâncias (D1, D5, D6) e o manifesto com as 15 instâncias de teste.

Uso (na raiz do projeto):
    .venv/bin/python -m tsp.generate
"""

import csv
from pathlib import Path

import numpy as np

from tsp.tsplib import Instance, read_tsp, write_tsp

ROOT = Path(__file__).resolve().parents[2]
TSPLIB_DIR = ROOT / "data" / "tsplib"
INSTANCES_DIR = ROOT / "data" / "instances"

SEED_BASE = 20261120

# (origem, N): cada origem recebe um N pequeno (12–22) e um grande (24–40),
# para que a geometria não fique confundida com o tamanho.
SUB_INSTANCES = [
    ("kroA100", 12), ("kroA100", 33),  # uniforme, alongada
    ("rd100", 14), ("rd100", 40),      # uniforme
    ("pr76", 16), ("pr76", 24),        # grade
    ("lin105", 18), ("lin105", 36),    # faixas
    ("pr107", 20), ("pr107", 27),      # duas colunas
    ("d198", 22), ("d198", 30),        # aglomerado + ponto isolado
]

# Faixa limite: instâncias completas, usadas direto de data/tsplib/
FULL_INSTANCES = ["eil51", "berlin52", "st70"]

MANIFEST_FIELDS = ["instance", "n", "kind", "source", "seed", "indices", "optimum", "path"]


def load_optima(tsplib_dir: Path) -> dict[str, int]:
    with (tsplib_dir / "optima.csv").open() as f:
        return {row["instance"]: int(row["optimum"]) for row in csv.DictReader(f)}


def sample_instance(source: Instance, n: int, seed: int) -> tuple[Instance, np.ndarray]:
    """Sorteia n pontos distintos da origem.

    Os índices são ordenados para manter a ordem do arquivo de origem
    (opção (a) da T04: a rota trivial 1 → 2 → … → n segue essa ordem).
    """
    rng = np.random.default_rng(seed)
    indices = np.sort(rng.choice(source.n, size=n, replace=False))
    return Instance(name=f"{source.name}-n{n}", coords=source.coords[indices]), indices


def generate(out_dir: Path = INSTANCES_DIR, tsplib_dir: Path = TSPLIB_DIR) -> list[dict]:
    """Grava as sub-instâncias e o manifest.csv em out_dir; devolve as linhas do manifesto.

    A coluna `path` é relativa à raiz do projeto (fixa), para que o manifesto
    não dependa da pasta onde foi gerado.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    optima = load_optima(tsplib_dir)
    rows = []

    for i, (source_name, n) in enumerate(SUB_INSTANCES):
        seed = SEED_BASE + i
        source = read_tsp(tsplib_dir / f"{source_name}.tsp")
        sub, indices = sample_instance(source, n, seed)
        write_tsp(sub, out_dir / f"{sub.name}.tsp",
                  comment=f"Subconjunto de {source_name} (seed {seed})")
        rows.append({
            "instance": sub.name, "n": n, "kind": "sub", "source": source_name,
            "seed": seed, "indices": " ".join(map(str, indices)), "optimum": "",
            "path": f"data/instances/{sub.name}.tsp",
        })

    for name in FULL_INSTANCES:
        n = read_tsp(tsplib_dir / f"{name}.tsp").n
        rows.append({
            "instance": name, "n": n, "kind": "full", "source": name,
            "seed": "", "indices": "", "optimum": optima[name],
            "path": f"data/tsplib/{name}.tsp",
        })

    with (out_dir / "manifest.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=MANIFEST_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return rows


if __name__ == "__main__":
    for row in generate():
        print(f"  {row['instance']:14} n={row['n']:<3} {row['kind']}")
