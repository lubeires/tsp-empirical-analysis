"""Caso adversarial do limite inferior e efeito da correção da D35 (T23).

Uso (na raiz do projeto):
    .venv/bin/python -m analysis.adversarial

1. Caso adversarial: para cada instância, refaz o subgradiente da raiz exatamente como o
   B&B (determinístico) e reconstrói a estrutura que realiza o limite: AGM com pesos
   penalizados sobre os vértices 1..n-1 mais as duas arestas do vértice 0. Compara essa
   estrutura com a melhor rota do B&B (a ótima, exceto na rd100-n75):
   - gap da raiz = ótimo / limite - 1;
   - vértices com grau diferente de 2 (onde a estrutura ainda não é uma rota);
   - arestas da estrutura que não estão na rota ótima.
2. Correção da D35: a 1ª versão do limite podia usar a mesma aresta duas vezes. As 80
   execuções feitas com ela estão em `results/archive/runs_bnb_v1_repeated_edge.csv`;
   aqui são comparadas às execuções oficiais, refeitas com o limite corrigido.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

import tsp.bnb as bnb
from analysis import plotting
from analysis.complexity import write_latex
from tsp.distance import distance_matrix
from tsp.mst import prim
from tsp.tsplib import read_tsp

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results"
ARCHIVE = RESULTS / "archive" / "runs_bnb_v1_repeated_edge.csv"
FIGURE_PAIR = ("kroA100-n33", "rd100-n40")  # adversarial x instância "fácil" de N parecido


def lower_bound_repeated(dist, first: int, last: int, path_cost: int,
                         unvisited: np.ndarray, pi: np.ndarray) -> tuple[float, np.ndarray]:
    """1ª versão de `tsp.bnb.lower_bound` (antes da D35), mantida só para comparação:
    cada ponta escolhe o seu vizinho mais próximo, mesmo que seja o mesmo vértice."""
    k = len(unvisited)
    out = dist[last, unvisited] + pi
    back = dist[first, unvisited] + pi
    a, b = int(np.argmin(out)), int(np.argmin(back))
    weights = dist[np.ix_(unvisited, unvisited)] + pi[:, None] + pi[None, :]
    edges, mst_cost = prim(weights)
    bound = path_cost + mst_cost + out[a] + back[b] - 2.0 * pi.sum()
    degree = np.zeros(k)
    for p, c in edges:
        degree[p] += 1
        degree[c] += 1
    degree[a] += 1
    degree[b] += 1
    return float(bound), degree


def best_tours() -> tuple[pd.Series, pd.Series]:
    """Melhor custo e rota do B&B por instância (entre as 5 rotas iniciais)."""
    runs = pd.read_csv(RESULTS / "runs.csv", keep_default_na=False, na_values=[""])  # D33
    bnb_runs = runs[runs.group == "bnb"].sort_values(["instance", "cost", "strategy"])
    first = bnb_runs.groupby("instance").first()
    tours = first.tour.map(lambda t: [int(v) for v in t.split()])
    return first.cost, tours


def root_structure(dist: np.ndarray, bound_fn=None) -> dict:
    """Subgradiente da raiz como no B&B e a estrutura (lista de arestas) no π final.

    `bound_fn=None` usa o limite oficial; `lower_bound_repeated` reproduz a 1ª versão.
    """
    n = len(dist)
    unvisited = np.arange(1, n)
    original = bnb.lower_bound
    if bound_fn is not None:
        bnb.lower_bound = bound_fn
    try:
        best, pi, _ = bnb.held_karp_bound(dist, 0, 0, 0, unvisited, np.zeros(n - 1),
                                          bnb.ROOT_ITERATIONS, upper=np.iinfo(np.int64).max)
    finally:
        bnb.lower_bound = original
    weights = dist[np.ix_(unvisited, unvisited)] + pi[:, None] + pi[None, :]
    tree, _ = prim(weights)
    edges = [(int(unvisited[p]), int(unvisited[c])) for p, c in tree]
    # Na raiz as duas pontas são o vértice 0: a versão oficial usa os dois vizinhos
    # penalizados mais próximos; a 1ª versão, o mais próximo duas vezes
    order = np.argsort(dist[0, unvisited] + pi, kind="stable")
    ends = [order[0], order[0]] if bound_fn is lower_bound_repeated else [order[0], order[1]]
    edges += [(0, int(unvisited[e])) for e in ends]
    degree = np.zeros(n, dtype=int)
    for u, v in edges:
        degree[u] += 1
        degree[v] += 1
    return {"bound": best, "edges": edges, "degree": degree}


def tour_edges(tour: list[int]) -> set[frozenset]:
    return {frozenset((tour[i], tour[(i + 1) % len(tour)])) for i in range(len(tour))}


def analyze() -> tuple[pd.DataFrame, dict]:
    manifest = pd.read_csv(ROOT / "data" / "instances" / "manifest.csv")
    cost, tours = best_tours()
    rows, details = [], {}
    for _, row in manifest.sort_values("n").iterrows():
        coords = read_tsp(ROOT / row.path).coords
        dist = distance_matrix(coords)
        s = root_structure(dist)
        old = root_structure(dist, lower_bound_repeated)
        opt_edges = tour_edges(tours[row.instance])
        outside = sum(e not in opt_edges for e in set(map(frozenset, s["edges"])))
        rows.append({
            "instance": row.instance, "n": row.n, "kind": row.kind,
            "best_cost": int(cost[row.instance]), "proven": row.kind != "stress",
            "root_bound": s["bound"],
            "root_gap_pct": (cost[row.instance] / s["bound"] - 1) * 100,
            "root_gap_repeated_pct": (cost[row.instance] / old["bound"] - 1) * 100,
            "degree_not_2": int((s["degree"] != 2).sum()),
            "edges_outside_tour": outside,
        })
        details[row.instance] = {"coords": coords, "tour": tours[row.instance], "structure": s}
    return pd.DataFrame(rows), details


def bound_fix_comparison() -> tuple[pd.DataFrame, dict]:
    """Execuções oficiais (limite corrigido) x arquivadas (1ª versão), por (instância, rota)."""
    kw = {"keep_default_na": False, "na_values": [""]}  # D33
    runs = pd.read_csv(RESULTS / "runs.csv", **kw)
    new = runs[runs.group == "bnb"]
    old = pd.read_csv(ARCHIVE, **kw)
    cols = ["instance", "n", "strategy", "status", "cost", "nodes_expanded", "time_total",
            "root_bound"]
    df = old[cols].merge(new[cols], on=["instance", "n", "strategy"], suffixes=("_v1", "_v2"))
    df["nodes_ratio"] = df.nodes_expanded_v2 / df.nodes_expanded_v1
    df["time_ratio"] = df.time_total_v2 / df.time_total_v1
    df = df.sort_values(["n", "instance", "strategy"]).reset_index(drop=True)
    closed = df[(df.status_v1 == "ok") & (df.status_v2 == "ok")]
    summary = {
        "pairs": len(df), "both_closed": len(closed),
        "same_cost_when_closed": bool((closed.cost_v1 == closed.cost_v2).all()),
        "nodes_ratio_median": float(closed.nodes_ratio.median()),
        "nodes_ratio_geomean": float(np.exp(np.log(closed.nodes_ratio).mean())),
        "fewer_nodes": int((closed.nodes_ratio < 1).sum()),
        "more_nodes": int((closed.nodes_ratio > 1).sum()),
        "time_ratio_median": float(closed.time_ratio.median()),
        "root_bound_never_lower": bool((df.root_bound_v2 >= df.root_bound_v1 - 1e-6).all()),
        "status_v2": {str(k): int(v) for k, v in df.groupby("status_v2").size().items()},
    }
    return df, summary


def main() -> None:
    table, details = analyze()
    fix, fix_summary = bound_fix_comparison()
    tables, figures = RESULTS / "tables", RESULTS / "figures"
    table.to_csv(tables / "adversarial_root.csv", index=False)
    fix.to_csv(tables / "bound_fix.csv", index=False)
    (tables / "bound_fix_summary.json").write_text(json.dumps(fix_summary, indent=2))
    write_latex(table[["instance", "n", "root_gap_pct", "root_gap_repeated_pct",
                       "degree_not_2", "edges_outside_tour"]],
                tables / "adversarial_root.tex",
                "Limite de Held-Karp na raiz: distância ao ótimo (na rd100-n75, à melhor "
                "rota encontrada), com o limite corrigido e com a 1ª versão (aresta "
                "repetida, D35), e vértices de grau $\\neq 2$ na estrutura.",
                "tab:adversarial",
                {"instance": "Instância", "n": "$N$", "root_gap_pct": r"Gap da\\raiz (\%)",
                 "root_gap_repeated_pct": r"Gap 1ª\\versão (\%)",
                 "degree_not_2": r"Grau\\$\neq 2$",
                 "edges_outside_tour": r"Arestas fora\\da rota"},
                {"root_gap_pct": 3, "root_gap_repeated_pct": 3})
    plotting.plot_root_structure([details[i] | {"name": i, **table.set_index("instance")
                                                .loc[i, ["root_gap_pct"]].to_dict()}
                                  for i in FIGURE_PAIR], figures)
    print(table.round(3).to_string(index=False))
    print(fix_summary)


if __name__ == "__main__":
    main()
