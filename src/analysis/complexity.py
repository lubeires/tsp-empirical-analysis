"""Complexidade empírica: ajuste de curvas a tempo, memória e nós do B&B (RF7a, T18, D14, D31).

Uso (na raiz do projeto):
    .venv/bin/python -m analysis.complexity

Dados:
- Tempo: grupo approx, coletor de lixo LIGADO, só o conjunto de teste (15 instâncias,
  sem a de estresse, D30). Só execuções em sequência (D25).
- Memória: results/profile_memory.csv (pico por sub-rotina).
- B&B: nós expandidos por estratégia (o tempo do B&B foi medido em paralelo, D25).

Ajuste:
- Modelos de forma fixa com termo constante: a·n + c, a·n² + c, a·n²·log n + c, a·n³ + c.
- Modelo livre a·n^b + c: estima o expoente empírico b.
- Erro relativo (sigma = valor medido): os valores vão de microssegundos a dezenas de
  milissegundos; com erro absoluto, os maiores N dominariam o ajuste.
- Métricas: R² (escala original) e RMSE relativo (%). Melhor modelo = menor RMSE relativo
  entre os de forma fixa.
- Bootstrap (só tempo): reamostra as repetições de cada ponto, recalcula as medianas e
  reajusta o modelo livre; o intervalo de 95% de b mostra se o ruído compromete a conclusão.
- B&B: log(nós) = log a + n·log b (crescimento exponencial; b = fator por vértice a mais).
"""

import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import curve_fit

from analysis import plotting

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results"
TEST_KINDS = {"sub", "full"}
BOOTSTRAP = 1000
SEED = 20261122

MODELS = {
    "n": lambda n, a, c: a * n + c,
    "n^2": lambda n, a, c: a * n**2 + c,
    "n^2 log n": lambda n, a, c: a * n**2 * np.log(n) + c,
    "n^3": lambda n, a, c: a * n**3 + c,
}


def _power(n, a, b, c):
    return a * np.power(n, b) + c


# Séries de tempo: (nome, algoritmo de origem, sub-rotina ou None = tempo total, teoria)
TIME_SERIES = [
    ("trivial", "trivial", None, "O(n)"),
    ("nn", "nn", None, "O(n^2)"),
    ("hull", "hull", None, "O(n^3)"),
    ("twice_around", "twice_around", None, "O(n^2)"),
    ("christofides", "christofides", None, "O(n^3)"),
    ("mst", "twice_around", "mst", "O(n^2)"),
    ("insertion", "hull", "insertion", "O(n^3)"),
    ("matching_build", "christofides", "matching_build", "O(|O|^2)"),
    ("matching", "christofides", "matching", "O(|O|^3)"),
    ("euler", "christofides", "euler", "O(n)"),
]

# Séries de memória: (nome, algoritmo, sub-rotina, teoria)
MEMORY_SERIES = [
    ("distance_matrix", "trivial", "distance_matrix", "O(n^2)"),
    ("mst", "twice_around", "mst", "O(n)"),
    ("insertion", "hull", "insertion", "O(n^2)"),
    ("matching_build", "christofides", "matching_build", "O(|O|^2)"),
    ("bnb_search", "bnb", "bnb_search", "O(n^2)"),
]


# ---------------------------------------------------------------------------
# Ajuste
# ---------------------------------------------------------------------------

def _metrics(y, y_hat) -> tuple[float, float]:
    ss_res = float(np.sum((y - y_hat) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else math.nan
    rmse_rel = float(np.sqrt(np.mean(((y - y_hat) / y) ** 2)) * 100)
    return r2, rmse_rel


def fit_power(n, y) -> np.ndarray | None:
    """Ajusta a·n^b + c com erro relativo; devolve (a, b, c) ou None se não convergir."""
    b0 = 2.0
    a0 = max(y[-1] / n[-1] ** b0, 1e-30)
    try:
        params, _ = curve_fit(_power, n, y, p0=[a0, b0, 0.0], sigma=y,
                              bounds=([0, 0.1, 0], [np.inf, 5, np.inf]), maxfev=20000)
        return params
    except RuntimeError:
        return None


def fit_models(n, y) -> list[dict]:
    """Ajusta todos os modelos de forma fixa e o livre; marca o melhor de forma fixa."""
    n, y = np.asarray(n, float), np.asarray(y, float)
    rows = []
    for name, f in MODELS.items():
        a0 = max(y[-1] / max(f(n[-1], 1.0, 0.0), 1e-30), 1e-30)
        params, _ = curve_fit(f, n, y, p0=[a0, 0.0], sigma=y,
                              bounds=([0, 0], [np.inf, np.inf]), maxfev=20000)
        r2, rmse = _metrics(y, f(n, *params))
        rows.append({"model": name, "a": params[0], "b": math.nan, "c": params[1],
                     "r2": r2, "rmse_rel_pct": rmse})
    best = min(rows, key=lambda r: r["rmse_rel_pct"])
    for r in rows:
        r["best"] = r is best
    power = fit_power(n, y)
    if power is not None:
        r2, rmse = _metrics(y, _power(n, *power))
        rows.append({"model": "a*n^b", "a": power[0], "b": power[1], "c": power[2],
                     "r2": r2, "rmse_rel_pct": rmse, "best": False})
    return rows


def bootstrap_exponent(n, reps_by_point: list[np.ndarray], rng) -> tuple[float, float]:
    """Intervalo de 95% do expoente b reamostrando as repetições de cada ponto."""
    estimates = []
    for _ in range(BOOTSTRAP):
        y = np.array([np.median(rng.choice(reps, size=len(reps))) for reps in reps_by_point])
        params = fit_power(np.asarray(n, float), y)
        if params is not None:
            estimates.append(params[1])
    return float(np.percentile(estimates, 2.5)), float(np.percentile(estimates, 97.5))


def fit_exponential(n, nodes) -> dict:
    """log(nós) = log a + n·log b. Devolve a, b (fator por vértice) e R² em escala log."""
    n, log_nodes = np.asarray(n, float), np.log(np.asarray(nodes, float))
    slope, intercept = np.polyfit(n, log_nodes, 1)
    pred = slope * n + intercept
    ss_res = float(np.sum((log_nodes - pred) ** 2))
    ss_tot = float(np.sum((log_nodes - log_nodes.mean()) ** 2))
    return {"a": math.exp(intercept), "b": math.exp(slope), "r2_log": 1 - ss_res / ss_tot}


# ---------------------------------------------------------------------------
# Dados
# ---------------------------------------------------------------------------

def load_data():
    manifest = pd.read_csv(ROOT / "data" / "instances" / "manifest.csv")
    kind = dict(zip(manifest.instance, manifest.kind))
    runs = pd.read_csv(RESULTS / "runs.csv")
    runs = runs[runs.instance.map(kind).isin(TEST_KINDS)]
    profile = pd.read_csv(RESULTS / "profile.csv")
    memory = pd.read_csv(RESULTS / "profile_memory.csv")
    memory = memory[memory.instance.map(kind).isin(TEST_KINDS)]
    return runs, profile, memory


def time_samples(runs, profile) -> dict[str, pd.DataFrame]:
    """Para cada série de tempo: DataFrame (n, valor por repetição)."""
    approx = runs[(runs.group == "approx") & (runs.gc_enabled == True)]  # noqa: E712
    out = {}
    for name, algorithm, sub, _ in TIME_SERIES:
        part = approx[approx.algorithm == algorithm]
        if sub is None:
            out[name] = part[["n", "time_total"]].rename(columns={"time_total": "value"})
        else:
            p = profile[profile.subroutine == sub].merge(part[["run_id", "n"]], on="run_id")
            out[name] = p[["n", "time_s"]].rename(columns={"time_s": "value"})
    return out


# ---------------------------------------------------------------------------
# Análises
# ---------------------------------------------------------------------------

def analyze_time(samples, rng) -> pd.DataFrame:
    theory = {name: t for name, *_, t in TIME_SERIES}
    rows = []
    for name, df in samples.items():
        grouped = df.groupby("n").value
        n = np.array(sorted(grouped.groups))
        reps = [grouped.get_group(k).to_numpy() for k in n]
        median = np.array([np.median(r) for r in reps])
        lo, hi = bootstrap_exponent(n, reps, rng)
        for r in fit_models(n, median):
            rows.append({"series": name, "theory": theory[name], **r,
                         "b_ci_low": lo if r["model"] == "a*n^b" else math.nan,
                         "b_ci_high": hi if r["model"] == "a*n^b" else math.nan})
    return pd.DataFrame(rows)


def analyze_memory(memory) -> pd.DataFrame:
    rows = []
    for name, algorithm, sub, theory in MEMORY_SERIES:
        part = memory[(memory.algorithm == algorithm) & (memory.subroutine == sub)]
        part = part.groupby("n").peak_bytes.max()
        for r in fit_models(part.index.to_numpy(), part.to_numpy()):
            rows.append({"series": name, "theory": theory, **r})
    return pd.DataFrame(rows)


def analyze_bnb_nodes(runs) -> pd.DataFrame:
    bnb = runs[runs.group == "bnb"]
    rows = []
    for strategy in plotting.ENTITY_ORDER:
        part = bnb[bnb.strategy == strategy].sort_values("n")
        rows.append({"strategy": strategy, "points": len(part),
                     **fit_exponential(part.n, part.nodes_expanded)})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Saídas
# ---------------------------------------------------------------------------

def _summary(df: pd.DataFrame) -> pd.DataFrame:
    """Uma linha por série: teoria, melhor modelo de forma fixa, expoente livre."""
    rows = []
    for name, g in df.groupby("series", sort=False):
        best = g[g.best].iloc[0]
        power = g[g.model == "a*n^b"]
        model = "constante (sem tendência)" if best.r2 < plotting.NO_TREND_R2 else best.model
        row = {"series": name, "theory": best.theory, "best_model": model,
               "r2": best.r2, "rmse_rel_pct": best.rmse_rel_pct,
               "b": power.b.iloc[0] if len(power) else math.nan}
        if "b_ci_low" in g:
            row["b_ci"] = (f"[{power.b_ci_low.iloc[0]:.2f}, {power.b_ci_high.iloc[0]:.2f}]"
                           if len(power) else "")
        rows.append(row)
    return pd.DataFrame(rows)


def write_latex(df: pd.DataFrame, path: Path, caption: str, label: str, headers: dict) -> None:
    """Tabela LaTeX simples (booktabs), sem depender do jinja2."""
    def fmt(v):
        if isinstance(v, float):
            return "--" if math.isnan(v) else f"{v:.3f}" if abs(v) < 100 else f"{v:.1f}"
        return str(v).replace("_", r"\_").replace("^", r"\^{}").replace("|", r"$|$")
    cols = list(headers)
    lines = [r"\begin{table}[htb]", r"\centering", rf"\caption{{{caption}}}", rf"\label{{{label}}}",
             r"\begin{tabular}{" + "l" * len(cols) + "}", r"\toprule",
             " & ".join(headers[c] for c in cols) + r" \\", r"\midrule"]
    lines += [" & ".join(fmt(row[c]) for c in cols) + r" \\" for _, row in df.iterrows()]
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]
    path.write_text("\n".join(lines) + "\n")


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Complexidade empírica (T18)")
    parser.add_argument("--plots-only", action="store_true",
                        help="refaz só as figuras a partir das tabelas já salvas")
    args = parser.parse_args()

    rng = np.random.default_rng(SEED)
    runs, profile, memory = load_data()
    tables, figures = RESULTS / "tables", RESULTS / "figures"
    samples = time_samples(runs, profile)

    if args.plots_only:
        time_fits = pd.read_csv(tables / "complexity_time.csv")
        memory_fits = pd.read_csv(tables / "complexity_memory.csv")
        nodes_fits = pd.read_csv(tables / "complexity_bnb_nodes.csv")
        plotting.plot_time(samples, time_fits, figures)
        plotting.plot_memory(memory, memory_fits, MEMORY_SERIES, figures)
        plotting.plot_bnb_nodes(runs, nodes_fits, figures)
        return

    time_fits = analyze_time(samples, rng)
    memory_fits = analyze_memory(memory)
    nodes_fits = analyze_bnb_nodes(runs)

    time_fits.to_csv(tables / "complexity_time.csv", index=False)
    memory_fits.to_csv(tables / "complexity_memory.csv", index=False)
    nodes_fits.to_csv(tables / "complexity_bnb_nodes.csv", index=False)

    headers = {"series": "Série", "theory": "Teoria", "best_model": "Melhor modelo",
               "r2": "$R^2$", "rmse_rel_pct": "RMSE rel. (\\%)", "b": "$b$ livre"}
    write_latex(_summary(time_fits), tables / "complexity_time.tex",
                "Ajuste de complexidade do tempo (mediana de 30 repetições).",
                "tab:complexity-time", {**headers, "b_ci": "IC 95\\% de $b$"})
    write_latex(_summary(memory_fits), tables / "complexity_memory.tex",
                "Ajuste de complexidade do pico de memória por sub-rotina.",
                "tab:complexity-memory", headers)
    write_latex(nodes_fits, tables / "complexity_bnb_nodes.tex",
                "Crescimento exponencial dos nós expandidos do B\\&B: nós $\\approx a\\cdot b^n$.",
                "tab:complexity-nodes",
                {"strategy": "Rota inicial", "a": "$a$", "b": "$b$", "r2_log": "$R^2$ (log)"})

    plotting.plot_time(samples, time_fits, figures)
    plotting.plot_memory(memory, memory_fits, MEMORY_SERIES, figures)
    plotting.plot_bnb_nodes(runs, nodes_fits, figures)

    print(_summary(time_fits).round(3).to_string(index=False))
    print()
    print(_summary(memory_fits).round(3).to_string(index=False))
    print()
    print(nodes_fits.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
