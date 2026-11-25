"""Impacto do warm-start no B&B e ponto de colapso (RF7b, T19, D32).

Uso (na raiz do projeto):
    .venv/bin/python -m analysis.warmstart

Pergunta do enunciado: o tempo gasto na heurística inicial compensa a restrição do
espaço de busca? E onde o algoritmo exato colapsa?

- Conjunto de teste (15 instâncias): métricas por (instância, rota inicial), comparação
  com a rota trivial, testes estatísticos e duas verificações de consistência.
- Instância de estresse (rd100-n75, D30): só na análise de colapso.
- Tempos do B&B foram medidos com processos em paralelo (D25): comparações de tempo são
  entre estratégias da mesma rodada; os nós expandidos são a medida principal.
"""

import json
import math
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from analysis import plotting
from analysis.complexity import p_value, write_latex

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results"
TEST_KINDS = {"sub", "full"}
TIME_LIMIT = 1800.0
STRATEGIES = plotting.ENTITY_ORDER
BASELINE = "trivial"


# ---------------------------------------------------------------------------
# Métricas
# ---------------------------------------------------------------------------

def _time_found(history: str) -> float:
    """Instante (s) da última melhoria do limite superior; 0 se a rota inicial já era a melhor."""
    points = json.loads(history) if isinstance(history, str) and history else []
    return float(points[-1][0]) if points else 0.0


def per_instance(bnb: pd.DataFrame, approx: pd.DataFrame, kind: dict) -> pd.DataFrame:
    """Uma linha por (instância, estratégia) com as métricas da T19."""
    ub0 = approx.groupby(["instance", "algorithm"]).cost.first()
    df = bnb.copy()
    df["kind"] = df.instance.map(kind)
    df["ub0"] = [ub0[(i, s)] for i, s in zip(df.instance, df.strategy)]
    # Ótimo: custo das execuções que fecharam; sem nenhuma, o melhor custo encontrado
    best = df.groupby("instance").cost.min()
    proven = df[df.status == "ok"].groupby("instance").cost.min()
    df["opt"] = df.instance.map(proven).fillna(df.instance.map(best))
    df["opt_proven"] = df.instance.isin(proven.index)
    df["initial_gap_pct"] = (df.ub0 / df.opt - 1) * 100
    df["prune_rate"] = df.nodes_pruned / (df.nodes_pruned + df.nodes_expanded)
    df["t_found"] = df.ub_history.map(_time_found)
    df["t_prove"] = np.where(df.status == "ok", df.time_total - df.t_found, np.nan)
    df["heuristic_share"] = df.time_heuristic / df.time_total

    base = df[df.strategy == BASELINE].set_index("instance")
    df["nodes_ratio"] = df.nodes_expanded / df.instance.map(base.nodes_expanded)
    # Podados: o enunciado pede comparar também esta contagem. Pode ser 0 (raiz já podada),
    # então o resumo usa mediana, não média geométrica
    df["pruned_ratio"] = df.nodes_pruned / df.instance.map(base.nodes_pruned)
    df["time_ratio"] = df.time_total / df.instance.map(base.time_total)
    df["time_saved"] = df.instance.map(base.time_total) - df.time_total
    cols = ["instance", "n", "kind", "strategy", "status", "cost", "ub0", "opt", "opt_proven",
            "initial_gap_pct", "nodes_expanded", "nodes_pruned", "prune_rate", "max_depth",
            "time_total", "time_heuristic", "heuristic_share", "t_found", "t_prove",
            "nodes_ratio", "pruned_ratio", "time_ratio", "time_saved", "root_bound"]
    return df[cols].sort_values(["n", "instance", "strategy"]).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Verificações de consistência
# ---------------------------------------------------------------------------

def monotonicity_violations(df: pd.DataFrame) -> pd.DataFrame:
    """Pares em que uma rota inicial MELHOR expandiu MAIS nós (ou empate de custo com nós
    diferentes). Pela D21 deve ser vazio: o π do subgradiente não depende do limite superior."""
    bad = []
    for instance, g in df.groupby("instance"):
        for (_, a), (_, b) in combinations(g.iterrows(), 2):
            if a.ub0 > b.ub0:
                a, b = b, a
            if (a.ub0 < b.ub0 and a.nodes_expanded > b.nodes_expanded) or \
               (a.ub0 == b.ub0 and a.nodes_expanded != b.nodes_expanded):
                bad.append({"instance": instance, "better": a.strategy, "worse": b.strategy,
                            "ub0": (a.ub0, b.ub0), "nodes": (a.nodes_expanded, b.nodes_expanded)})
    return pd.DataFrame(bad)


def root_bound_spread(df: pd.DataFrame) -> float:
    """Maior diferença do limite da raiz entre estratégias da mesma instância (deve ser 0)."""
    return float(df.groupby("instance").root_bound.agg(lambda s: s.max() - s.min()).max())


# ---------------------------------------------------------------------------
# Estatística
# ---------------------------------------------------------------------------

def holm(pvalues: list[float]) -> list[float]:
    """Correção de Holm-Bonferroni para comparações múltiplas."""
    order = np.argsort(pvalues)
    m, adjusted, running = len(pvalues), [0.0] * len(pvalues), 0.0
    for rank, idx in enumerate(order):
        running = max(running, min(1.0, (m - rank) * pvalues[idx]))
        adjusted[idx] = running
    return adjusted


def statistics(df: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    """Friedman (5 estratégias, instâncias como blocos), Wilcoxon contra a trivial (Holm),
    Spearman entre gap inicial e razão de nós."""
    nodes = df.pivot(index="instance", columns="strategy", values="nodes_expanded")[STRATEGIES]
    friedman = stats.friedmanchisquare(*[nodes[s] for s in STRATEGIES])
    others = [s for s in STRATEGIES if s != BASELINE]
    raw = []
    for s in others:
        diff = nodes[s] - nodes[BASELINE]
        raw.append(1.0 if (diff == 0).all() else
                   float(stats.wilcoxon(nodes[s], nodes[BASELINE], zero_method="wilcox").pvalue))
    adjusted = holm(raw)
    rho = stats.spearmanr(df.initial_gap_pct, df.nodes_ratio)
    summary = {"friedman_stat": float(friedman.statistic), "friedman_p": float(friedman.pvalue),
               "spearman_rho_gap_vs_nodes_ratio": float(rho.statistic),
               "spearman_p": float(rho.pvalue), "instances": len(nodes)}
    tests = pd.DataFrame({"strategy": others, "wilcoxon_p": raw, "wilcoxon_p_holm": adjusted})
    return summary, tests


def strategy_summary(df: pd.DataFrame, tests: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for s in STRATEGIES:
        g = df[df.strategy == s]
        rows.append({
            "strategy": s,
            "initial_gap_pct_median": g.initial_gap_pct.median(),
            "nodes_ratio_median": g.nodes_ratio.median(),
            "nodes_ratio_geomean": float(np.exp(np.log(g.nodes_ratio).mean())),
            "fewer_nodes_than_trivial": int((g.nodes_ratio < 1).sum()),
            "pruned_ratio_median": g.pruned_ratio.median(),
            "prune_rate_median": g.prune_rate.median() * 100,
            "time_ratio_median": g.time_ratio.median(),
            "heuristic_time_max_s": g.time_heuristic.max(),
            "heuristic_share_max_pct": g.heuristic_share.max() * 100,
        })
    out = pd.DataFrame(rows).merge(tests, on="strategy", how="left")
    return out


# ---------------------------------------------------------------------------
# Colapso
# ---------------------------------------------------------------------------

def collapse_n(n, times, limit: float = TIME_LIMIT) -> dict:
    """Ajusta log(tempo) = α + β·n e devolve o N em que o tempo previsto atinge `limit`."""
    beta, alpha = np.polyfit(np.asarray(n, float), np.log(np.asarray(times, float)), 1)
    return {"alpha": alpha, "beta": beta, "growth_per_vertex": math.exp(beta),
            "n_collapse": (math.log(limit) - alpha) / beta,
            "predicted_time_n75": math.exp(alpha + beta * 75)}


def collapse_table(df_test: pd.DataFrame, df_stress: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for s in STRATEGIES:
        g = df_test[df_test.strategy == s]
        fit = collapse_n(g.n, g.time_total)
        row = {"strategy": s, **fit}
        st = df_stress[df_stress.strategy == s]
        if len(st):
            r = st.iloc[0]
            row.update({"n75_status": r.status, "n75_time": r.time_total,
                        "n75_nodes": r.nodes_expanded, "n75_ub0": int(r.ub0),
                        "n75_best_cost": int(r.cost)})  # com NA: melhor rota até o prazo
        rows.append(row)
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Principal
# ---------------------------------------------------------------------------

def main() -> None:
    manifest = pd.read_csv(ROOT / "data" / "instances" / "manifest.csv")
    kind = dict(zip(manifest.instance, manifest.kind))
    runs = pd.read_csv(RESULTS / "runs.csv", keep_default_na=False, na_values=[""])  # "NA" é status, não ausente
    bnb = runs[(runs.group == "bnb") & runs.status.isin(["ok", "NA"])]
    approx = runs[(runs.group == "approx") & (runs.gc_enabled == True)]  # noqa: E712

    df = per_instance(bnb, approx, kind)
    test, stress = df[df.kind.isin(TEST_KINDS)], df[df.kind == "stress"]

    violations = monotonicity_violations(test)
    spread = root_bound_spread(test)
    summary_stats, tests = statistics(test)
    summary = strategy_summary(test, tests)
    collapse = collapse_table(test, stress)

    tables, figures = RESULTS / "tables", RESULTS / "figures"
    df.to_csv(tables / "warmstart_per_instance.csv", index=False)
    summary.to_csv(tables / "warmstart_summary.csv", index=False)
    collapse.to_csv(tables / "collapse.csv", index=False)
    (tables / "warmstart_checks.json").write_text(json.dumps({
        **summary_stats, "monotonicity_violations": len(violations),
        "root_bound_max_spread": spread}, indent=2))

    write_latex(summary, tables / "warmstart_summary.tex",
                "Efeito da rota inicial no B\\&B (15 instâncias). Nós expandidos e podados em razão à rota trivial na mesma instância; taxa de poda = podados / (podados + expandidos).",
                "tab:warmstart",
                {"strategy": "Rota inicial", "initial_gap_pct_median": r"Gap\\inicial (\%)",
                 "nodes_ratio_geomean": r"Nós (média\\geométrica)",
                 "fewer_nodes_than_trivial": "Vitórias",
                 "pruned_ratio_median": r"Podados\\(mediana)",
                 "prune_rate_median": r"Taxa de\\poda (\%)",
                 "time_ratio_median": r"Tempo\\(mediana)",
                 "heuristic_share_max_pct": r"Heurística\\(\% máx.)",
                 "wilcoxon_p_holm": "$p$ (Holm)"},
                {"initial_gap_pct_median": 1, "heuristic_share_max_pct": 1,
                 "prune_rate_median": 1,
                 "wilcoxon_p_holm": p_value},
                fit=True)
    write_latex(collapse, tables / "collapse.tex",
                "Ponto de colapso: ajuste $\\log t = \\alpha + \\beta n$ nas 15 instâncias e "
                "resultado observado na instância de estresse rd100-n75.",
                "tab:collapse",
                {"strategy": "Rota inicial", "growth_per_vertex": "$e^{\\beta}$",
                 "n_collapse": r"N previsto\\(30 min)", "predicted_time_n75": r"Previsto\\N = 75 (s)",
                 "n75_status": r"Observado\\N = 75", "n75_time": r"Tempo\\obs. (s)"},
                {"growth_per_vertex": 3, "n_collapse": 1, "predicted_time_n75": 0,
                 "n75_time": 0})

    plotting.plot_nodes_ratio(test, figures)
    plotting.plot_gap_vs_nodes(test, figures)
    plotting.plot_find_vs_prove(df[df.instance.isin(["st70", "rd100-n75"])], figures, TIME_LIMIT)
    plotting.plot_collapse(test, stress, collapse, figures, TIME_LIMIT)

    print("Verificações:", {"violações de monotonicidade": len(violations),
                            "maior diferença do limite da raiz": spread})
    print("Estatística:", {k: round(v, 4) for k, v in summary_stats.items()})
    print(summary.round(3).to_string(index=False))
    print(collapse.round(2).to_string(index=False))


if __name__ == "__main__":
    main()
