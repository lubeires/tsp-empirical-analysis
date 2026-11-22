"""Análise de sensibilidade: características das instâncias x gap (RF7c, T20, D34).

Uso (na raiz do projeto):
    .venv/bin/python -m analysis.sensitivity

15 instâncias e 9 características: qualquer modelo com todas superajusta. Por isso
três camadas, da mais robusta para a mais exploratória:
1. Spearman por algoritmo, bruto e PARCIAL controlando N (hull_ratio cai com N, T17).
2. Regressão múltipla padronizada agrupando os 4 algoritmos (gap em escore z dentro de
   cada algoritmo; 60 linhas), com VIF e IC de 95% por bootstrap que reamostra
   INSTÂNCIAS (as 4 linhas de uma instância não são independentes).
3. Árvore de decisão de profundidade 2 por algoritmo, com R² fora da amostra por
   validação cruzada deixando uma instância de fora.
A rota trivial fica de fora: o gap dela depende da ordem do arquivo (T06), não da geometria.
"""

import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.tree import DecisionTreeRegressor, export_text

from analysis import plotting
from analysis.complexity import write_latex
from tsp.features import FEATURES

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results"
TEST_KINDS = {"sub", "full"}
ALGORITHMS = ["nn", "hull", "twice_around", "christofides"]
BOOTSTRAP = 2000
SEED = 20261122
VIF_LIMIT = 10.0
ADVERSARIAL = ["d198-n22", "pr107-n20", "pr107-n27"]


# ---------------------------------------------------------------------------
# Dados
# ---------------------------------------------------------------------------

def load_gaps() -> tuple[pd.DataFrame, pd.DataFrame]:
    """(features por instância, gap % por instância x algoritmo), só o conjunto de teste."""
    manifest = pd.read_csv(ROOT / "data" / "instances" / "manifest.csv")
    test = set(manifest[manifest.kind.isin(TEST_KINDS)].instance)
    runs = pd.read_csv(RESULTS / "runs.csv", keep_default_na=False, na_values=[""])  # D33
    opt = runs[(runs.group == "bnb") & (runs.status == "ok")].groupby("instance").cost.min()
    approx = runs[(runs.group == "approx") & (runs.gc_enabled == True)  # noqa: E712
                  & runs.instance.isin(test)]
    cost = approx.groupby(["instance", "algorithm"]).cost.first().unstack()[ALGORITHMS]
    gaps = (cost.div(opt[cost.index], axis=0) - 1) * 100
    features = pd.read_csv(RESULTS / "features.csv").set_index("instance").loc[gaps.index, FEATURES]
    return features, gaps


# ---------------------------------------------------------------------------
# 1. Correlações
# ---------------------------------------------------------------------------

def partial_spearman(x, y, z) -> tuple[float, float]:
    """Spearman parcial de x e y controlando z: correlação dos resíduos dos postos.

    p-valor pelo teste t com n - 3 graus de liberdade.
    """
    rx, ry, rz = (stats.rankdata(v) for v in (x, y, z))

    def residual(r):
        slope, intercept = np.polyfit(rz, r, 1)
        return r - (slope * rz + intercept)

    ex, ey = residual(rx), residual(ry)
    if np.allclose(ex, 0) or np.allclose(ey, 0):
        return math.nan, math.nan
    rho = float(np.corrcoef(ex, ey)[0, 1])
    dof = len(x) - 3
    t = rho * math.sqrt(dof / max(1 - rho**2, 1e-12))
    return rho, float(2 * stats.t.sf(abs(t), dof))


def correlations(features: pd.DataFrame, gaps: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for alg in ALGORITHMS:
        for feat in FEATURES:
            rho = stats.spearmanr(features[feat], gaps[alg])
            if feat == "n":
                partial = (math.nan, math.nan)  # controlar N por N não faz sentido
            else:
                partial = partial_spearman(features[feat], gaps[alg], features["n"])
            rows.append({"algorithm": alg, "feature": feat, "rho": float(rho.statistic),
                         "p": float(rho.pvalue), "rho_partial_n": partial[0],
                         "p_partial_n": partial[1]})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 2. Regressão agrupada
# ---------------------------------------------------------------------------

def vif(X: pd.DataFrame) -> pd.Series:
    """Fator de inflação da variância de cada coluna (regressão de cada uma nas outras)."""
    out = {}
    for col in X:
        others = X.drop(columns=col).to_numpy()
        A = np.column_stack([np.ones(len(X)), others])
        coef, *_ = np.linalg.lstsq(A, X[col].to_numpy(), rcond=None)
        resid = X[col].to_numpy() - A @ coef
        r2 = 1 - resid.var() / X[col].to_numpy().var()
        out[col] = math.inf if r2 >= 1 else 1 / (1 - r2)
    return pd.Series(out)


def select_by_vif(X: pd.DataFrame) -> tuple[list[str], list[str]]:
    """Remove, uma por vez, a característica de maior VIF enquanto ele passar do limite."""
    kept, dropped = list(X), []
    while len(kept) > 1:
        v = vif(X[kept])
        if v.max() <= VIF_LIMIT:
            break
        worst = v.idxmax()
        kept.remove(worst)
        dropped.append(worst)
    return kept, dropped


def pooled_design(features: pd.DataFrame, gaps: pd.DataFrame, kept: list[str]):
    """Linhas (instância, algoritmo): gap em escore z dentro do algoritmo; X padronizado."""
    Z = (features[kept] - features[kept].mean()) / features[kept].std(ddof=0)
    zgap = (gaps - gaps.mean()) / gaps.std(ddof=0)
    long = zgap.stack().rename("y").reset_index()
    long.columns = ["instance", "algorithm", "y"]
    X = Z.loc[long.instance].to_numpy()
    return long, X


def ols(X, y) -> np.ndarray:
    A = np.column_stack([np.ones(len(X)), X])
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    return coef


def pooled_regression(features, gaps, rng) -> tuple[pd.DataFrame, dict]:
    kept, dropped = select_by_vif(features)
    long, X = pooled_design(features, gaps, kept)
    y = long.y.to_numpy()
    coef = ols(X, y)
    fitted = np.column_stack([np.ones(len(X)), X]) @ coef
    r2_in = 1 - np.sum((y - fitted) ** 2) / np.sum((y - y.mean()) ** 2)

    # Bootstrap por instância: as 4 linhas de uma instância entram ou saem juntas
    instances = np.array(features.index)
    rows_of = {inst: np.flatnonzero(long.instance.to_numpy() == inst) for inst in instances}
    samples = []
    for _ in range(BOOTSTRAP):
        chosen = rng.choice(instances, size=len(instances))
        idx = np.concatenate([rows_of[i] for i in chosen])
        samples.append(ols(X[idx], y[idx])[1:])
    samples = np.array(samples)

    # Validação cruzada deixando uma INSTÂNCIA (4 linhas) de fora
    sse = 0.0
    for inst in instances:
        test = rows_of[inst]
        train = np.setdiff1d(np.arange(len(y)), test)
        c = ols(X[train], y[train])
        sse += np.sum((y[test] - np.column_stack([np.ones(len(test)), X[test]]) @ c) ** 2)
    r2_loo = 1 - sse / np.sum((y - y.mean()) ** 2)

    vifs = vif(features[kept])
    table = pd.DataFrame({
        "feature": kept, "beta": coef[1:],
        "ci_low": np.percentile(samples, 2.5, axis=0),
        "ci_high": np.percentile(samples, 97.5, axis=0),
        "vif": [vifs[k] for k in kept],
    })
    table["ci_excludes_zero"] = (table.ci_low > 0) | (table.ci_high < 0)
    return table, {"r2_in_sample": float(r2_in), "r2_loo_instance": float(r2_loo),
                   "rows": len(y), "dropped_by_vif": dropped}


# ---------------------------------------------------------------------------
# 3. Árvores
# ---------------------------------------------------------------------------

def loo_r2(model_factory, X: np.ndarray, y: np.ndarray) -> float:
    """R² fora da amostra por validação cruzada deixando um de fora."""
    preds = np.empty(len(y))
    for i in range(len(y)):
        mask = np.arange(len(y)) != i
        preds[i] = model_factory().fit(X[mask], y[mask]).predict(X[i:i + 1])[0]
    return float(1 - np.sum((y - preds) ** 2) / np.sum((y - y.mean()) ** 2))


def trees(features: pd.DataFrame, gaps: pd.DataFrame) -> tuple[str, pd.DataFrame]:
    def factory():
        return DecisionTreeRegressor(max_depth=2, min_samples_leaf=2, random_state=0)
    X = features.to_numpy()
    text, rows = [], []
    for alg in ALGORITHMS:
        y = gaps[alg].to_numpy()
        tree = factory().fit(X, y)
        r2_in = tree.score(X, y)
        r2_cv = loo_r2(factory, X, y)
        rows.append({"algorithm": alg, "r2_in_sample": r2_in, "r2_loo": r2_cv})
        text.append(f"== {plotting.LABELS[alg]}: R² na amostra = {r2_in:.2f}; "
                    f"R² fora da amostra (deixa uma de fora) = {r2_cv:.2f}")
        text.append(export_text(tree, feature_names=list(FEATURES), decimals=3))
    return "\n".join(text), pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Principal
# ---------------------------------------------------------------------------

def main() -> None:
    rng = np.random.default_rng(SEED)
    features, gaps = load_gaps()
    tables, figures = RESULTS / "tables", RESULTS / "figures"

    corr = correlations(features, gaps)
    reg, reg_info = pooled_regression(features, gaps, rng)
    tree_text, tree_scores = trees(features, gaps)
    adversarial = gaps.loc[ADVERSARIAL].T.assign(median=gaps.median()).T.round(2)

    corr.to_csv(tables / "sensitivity_spearman.csv", index=False)
    reg.to_csv(tables / "sensitivity_regression.csv", index=False)
    tree_scores.to_csv(tables / "sensitivity_trees.csv", index=False)
    (tables / "sensitivity_trees.txt").write_text(tree_text)
    adversarial.to_csv(tables / "sensitivity_adversarial.csv")
    pd.Series(reg_info).to_json(tables / "sensitivity_regression_info.json", indent=2)

    wide = corr.pivot(index="feature", columns="algorithm", values="rho_partial_n")
    wide = wide.loc[[f for f in FEATURES if f != "n"], ALGORITHMS].reset_index()
    write_latex(wide, tables / "sensitivity_spearman.tex",
                "Correlação de Spearman parcial (controlando N) entre característica e gap.",
                "tab:sensitivity-spearman",
                {"feature": "Característica", **{a: plotting.LABELS[a] for a in ALGORITHMS}})
    write_latex(reg, tables / "sensitivity_regression.tex",
                "Regressão padronizada agrupada (gap em escore z por algoritmo; IC 95\\% por "
                f"bootstrap de instâncias). $R^2$ = {reg_info['r2_in_sample']:.2f} na amostra, "
                f"{reg_info['r2_loo_instance']:.2f} fora da amostra.",
                "tab:sensitivity-regression",
                {"feature": "Característica", "beta": "$\\beta$", "ci_low": "IC inf.",
                 "ci_high": "IC sup.", "vif": "VIF"})

    plotting.plot_sensitivity_heatmap(corr, ALGORITHMS, [f for f in FEATURES if f != "n"],
                                      figures)
    plotting.plot_regression_coefficients(reg, reg_info, figures)

    print(wide.round(2).to_string(index=False))
    print()
    print(reg.round(3).to_string(index=False))
    print(reg_info)
    print()
    print(tree_scores.round(2).to_string(index=False))
    print()
    print(adversarial.to_string())


if __name__ == "__main__":
    main()
