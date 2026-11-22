"""Estilo e figuras das análises (T18).

Regras (skill de visualização): cores categóricas em ordem fixa e validadas para
daltonismo; a cor segue a entidade (cada algoritmo tem sempre a mesma cor, inclusive
como rota inicial do B&B); um único eixo y por figura; marcas finas; grade discreta;
legenda sempre presente. Três cores têm contraste < 3:1 com o fundo, então cada série
tem também um marcador próprio (codificação secundária, útil na impressão em P&B).
Figuras em PDF (vetorial, para o LaTeX) e PNG (para revisão).
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.ticker import FixedLocator, NullFormatter, ScalarFormatter  # noqa: E402

# Paleta categórica de referência, slots 1–5 (validada: CVD ΔE ≥ 9,1; normal ≥ 19,6)
PALETTE = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]
MARKERS = ["o", "s", "^", "D", "v"]
TEXT = "#2b2b29"
MUTED = "#6b6a64"
GRID = "#e6e5e0"
SURFACE = "#ffffff"

ENTITY_ORDER = ["trivial", "nn", "hull", "twice_around", "christofides"]
LABELS = {
    "trivial": "Trivial", "nn": "Vizinho mais próximo", "hull": "Fecho + inserção",
    "twice_around": "Twice-around", "christofides": "Christofides",
    "mst": "MST (Prim)", "insertion": "Inserção (fecho)", "matching_build":
    "Montar grafo (networkx)", "matching": "Emparelhamento", "euler": "Circuito euleriano",
    "distance_matrix": "Matriz de distâncias", "bnb_search": "Busca do B&B",
}

plt.rcParams.update({
    "font.size": 9, "axes.titlesize": 10, "axes.labelsize": 9, "legend.fontsize": 8,
    "text.color": TEXT, "axes.labelcolor": TEXT, "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.edgecolor": GRID, "axes.facecolor": SURFACE, "figure.facecolor": SURFACE,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
    "axes.spines.top": False, "axes.spines.right": False, "lines.linewidth": 1.5,
    "pdf.fonttype": 42,
})


def style(series: list[str]) -> dict[str, tuple[str, str]]:
    """Cor e marcador por série, na ordem fixa de entrada (nunca reciclados)."""
    assert len(series) <= len(PALETTE), "mais séries que cores: agrupar ou separar figuras"
    return {s: (PALETTE[i], MARKERS[i]) for i, s in enumerate(series)}


def _save(fig, out_dir: Path, name: str) -> None:
    fig.savefig(out_dir / f"{name}.pdf", bbox_inches="tight")
    fig.savefig(out_dir / f"{name}.png", bbox_inches="tight", dpi=150)
    plt.close(fig)


NO_TREND_R2 = 0.5  # abaixo disso, nenhum modelo explica a série: "sem tendência"
N_TICKS = [12, 20, 30, 40, 50, 70]


def _best_curve(fits, series: str, n_grid):
    """Curva do melhor modelo de forma fixa da série, no grid de n, e o rótulo do modelo."""
    from analysis.complexity import MODELS
    best = fits[(fits.series == series) & fits.best].iloc[0]
    label = "constante, sem tendência" if best.r2 < NO_TREND_R2 else best.model
    return MODELS[best.model](n_grid, best.a, best.c), label


def _n_axis(ax) -> None:
    """Eixo x em log com os valores de N escritos por extenso."""
    ax.xaxis.set_major_locator(FixedLocator(N_TICKS))
    ax.xaxis.set_major_formatter(ScalarFormatter())
    ax.xaxis.set_minor_formatter(NullFormatter())


def _legend_below(ax) -> None:
    """Legenda abaixo do gráfico, para nunca cobrir os dados."""
    ax.legend(frameon=False, loc="upper left", bbox_to_anchor=(0, -0.16), ncol=2,
              handletextpad=0.4, columnspacing=1.5)


def _loglog_panel(ax, data: dict, fits, scale: float, ylabel: str, title: str) -> None:
    """data: série -> (n, mediana, q25, q75). Pontos com faixa interquartil + curva ajustada."""
    colors = style(list(data))
    for name, (n, med, q25, q75) in data.items():
        color, marker = colors[name]
        grid = np.linspace(n.min(), n.max(), 200)
        curve, model = _best_curve(fits, name, grid)
        ax.plot(grid, curve * scale, color=color, linewidth=1.5, alpha=0.9)
        ax.errorbar(n, med * scale, yerr=[(med - q25) * scale, (q75 - med) * scale],
                    fmt=marker, color=color, markersize=5, elinewidth=0.8, capsize=0,
                    markeredgecolor=SURFACE, markeredgewidth=0.8,
                    label=f"{LABELS[name]}  ({model})")
    ax.set_xscale("log")
    ax.set_yscale("log")
    _n_axis(ax)
    ax.set_xlabel("N (vértices)")
    ax.set_ylabel(ylabel)
    ax.set_title(title, loc="left")
    _legend_below(ax)


def _quantiles(df):
    g = df.groupby("n").value
    return (g.median().index.to_numpy(), g.median().to_numpy(),
            g.quantile(0.25).to_numpy(), g.quantile(0.75).to_numpy())


def plot_time(samples: dict, fits, out_dir: Path) -> None:
    groups = {
        "complexity_time_algorithms": (ENTITY_ORDER, "Tempo por algoritmo"),
        "complexity_time_subroutines": (["mst", "insertion", "matching_build", "matching",
                                         "euler"], "Tempo por sub-rotina"),
    }
    for name, (series, title) in groups.items():
        fig, ax = plt.subplots(figsize=(6.3, 3.8))
        data = {s: _quantiles(samples[s]) for s in series}
        _loglog_panel(ax, data, fits, 1e3, "Tempo (ms, mediana; barra = IQR)",
                      f"{title} (escala log-log; linha = melhor modelo)")
        _save(fig, out_dir, name)


def plot_memory(memory, fits, series_spec, out_dir: Path) -> None:
    fig, ax = plt.subplots(figsize=(6.3, 3.8))
    data = {}
    for name, algorithm, sub, _ in series_spec:
        part = memory[(memory.algorithm == algorithm) & (memory.subroutine == sub)]
        peak = part.groupby("n").peak_bytes.max()
        n, v = peak.index.to_numpy(), peak.to_numpy().astype(float)
        data[name] = (n, v, v, v)  # uma medição por ponto: sem faixa
    _loglog_panel(ax, data, fits, 1 / 1024, "Pico de memória (KB)",
                  "Pico de memória por sub-rotina (escala log-log)")
    _save(fig, out_dir, "complexity_memory")


def plot_bnb_nodes(runs, fits, out_dir: Path) -> None:
    bnb = runs[runs.group == "bnb"]
    colors = style(ENTITY_ORDER)
    fig, ax = plt.subplots(figsize=(6.3, 3.8))
    for strategy in ENTITY_ORDER:
        part = bnb[bnb.strategy == strategy].sort_values("n")
        fit = fits[fits.strategy == strategy].iloc[0]
        color, marker = colors[strategy]
        grid = np.linspace(part.n.min(), part.n.max(), 200)
        ax.plot(grid, fit.a * fit.b ** grid, color=color, linewidth=1.5, alpha=0.9)
        ax.plot(part.n, part.nodes_expanded, marker, color=color, markersize=5,
                markeredgecolor=SURFACE, markeredgewidth=0.8,
                label=f"{LABELS[strategy]}  (b = {fit.b:.3f}, $R^2_{{log}}$ = {fit.r2_log:.2f})")
    ax.set_yscale("log")
    ax.set_xlabel("N (vértices)")
    ax.set_ylabel("Nós expandidos")
    ax.set_title("Nós expandidos do B&B por rota inicial (escala semilog; linha = a·bⁿ)",
                 loc="left")
    _legend_below(ax)
    _save(fig, out_dir, "complexity_bnb_nodes")


# ---------------------------------------------------------------------------
# Figuras da T19 (warm-start e colapso)
# ---------------------------------------------------------------------------

FIND = "#6b6a64"    # cinza escuro: tempo até achar a rota ótima
PROVE = "#c9c8c1"   # cinza claro: tempo para provar a otimalidade
LIMIT_LINE = "#8a8983"


def plot_nodes_ratio(df, out_dir: Path) -> None:
    """Razão de nós em relação à rota trivial, por instância (ordenada por N)."""
    colors = style(ENTITY_ORDER)
    order = df.drop_duplicates("instance").sort_values("n")
    x = {inst: i for i, inst in enumerate(order.instance)}
    others = [s for s in ENTITY_ORDER if s != "trivial"]
    offsets = dict(zip(others, np.linspace(-0.24, 0.24, len(others))))
    fig, ax = plt.subplots(figsize=(6.3, 3.9))
    ax.axhline(1, color=LIMIT_LINE, linewidth=1, linestyle="--")
    ax.text(-0.4, 1.12, "linha tracejada = rota trivial", color=MUTED, ha="left", fontsize=8)
    for s in others:
        g = df[df.strategy == s]
        color, marker = colors[s]
        ax.plot([x[i] + offsets[s] for i in g.instance], g.nodes_ratio, marker, color=color,
                markersize=5, markeredgecolor=SURFACE, markeredgewidth=0.8, label=LABELS[s],
                linestyle="none")
    ax.set_yscale("log")
    ax.set_xticks(range(len(x)))
    ax.set_xticklabels([f"{i}\n(N={n})" for i, n in zip(order.instance, order.n)],
                       rotation=60, ha="right", fontsize=7)
    ax.set_ylabel("Nós expandidos ÷ nós da rota trivial")
    ax.set_title("Redução da árvore de busca por rota inicial (escala log)", loc="left")
    ax.grid(axis="x", visible=False)
    ax.legend(frameon=False, loc="upper left", bbox_to_anchor=(0, -0.36), ncol=4,
              handletextpad=0.3, columnspacing=1.2)
    _save(fig, out_dir, "warmstart_nodes_ratio")


def plot_gap_vs_nodes(df, out_dir: Path) -> None:
    """Gap da rota inicial x razão de nós em relação à trivial."""
    colors = style(ENTITY_ORDER)
    fig, ax = plt.subplots(figsize=(6.3, 3.6))
    for s in ENTITY_ORDER:
        g = df[df.strategy == s]
        color, marker = colors[s]
        ax.plot(g.initial_gap_pct, g.nodes_ratio, marker, color=color, markersize=5,
                markeredgecolor=SURFACE, markeredgewidth=0.8, label=LABELS[s], linestyle="none")
    ax.set_xscale("symlog", linthresh=1)
    ax.set_yscale("log")
    ax.set_xlabel("Gap da rota inicial em relação ao ótimo (%)")
    ax.set_ylabel("Nós ÷ nós da rota trivial")
    ax.set_title("Qualidade da rota inicial x tamanho da árvore", loc="left")
    _legend_below(ax)
    _save(fig, out_dir, "warmstart_gap_vs_nodes")


def plot_find_vs_prove(df, out_dir: Path, limit: float) -> None:
    """Barras empilhadas por estratégia: achar a melhor rota + provar a otimalidade.

    Em execuções NA (prazo estourado), o 1º segmento é a melhor rota encontrada (não
    provada ótima) e o 2º, hachurado, é a busca até o prazo sem conclusão.
    """
    instances = list(df.sort_values("n").instance.unique())
    fig, axes = plt.subplots(1, len(instances), figsize=(6.3, 3.1), sharey=True)
    axes = np.atleast_1d(axes)
    y = np.arange(len(ENTITY_ORDER))
    for ax, inst in zip(axes, instances):
        g = df[df.instance == inst].set_index("strategy").loc[ENTITY_ORDER]
        find = g.t_found.to_numpy() / 60
        total = g.time_total.to_numpy() / 60
        na = (g.status == "NA").to_numpy()
        prove = np.where(na, 0.0, total - find)
        unfinished = np.where(na, total - find, 0.0)
        ax.barh(y, find, color=FIND, height=0.6, label="achar a melhor rota")
        ax.barh(y, prove, left=find, color=PROVE, height=0.6, edgecolor=SURFACE,
                linewidth=1.5, label="provar a otimalidade")
        ax.barh(y, unfinished, left=find, color=SURFACE, height=0.6, edgecolor=FIND,
                linewidth=0.8, hatch="////", label="busca até o prazo, sem prova (NA)")
        ax.axvline(limit / 60, color=LIMIT_LINE, linewidth=1, linestyle="--")
        ax.set_title(f"{inst} (N={int(g.n.iloc[0])})" + ("  —  NA" if na.all() else ""),
                     loc="left")
        ax.set_xlabel("Minutos")
        ax.grid(axis="y", visible=False)
    axes[0].set_yticks(y)
    axes[0].set_yticklabels([LABELS[s] for s in ENTITY_ORDER])
    axes[0].invert_yaxis()
    handles, labels = [], []
    for ax in axes:  # junta as entradas de todos os painéis, sem repetir
        for h, lab in zip(*ax.get_legend_handles_labels()):
            if lab not in labels:
                handles.append(h)
                labels.append(lab)
    fig.legend(handles, labels, frameon=False, loc="upper left", bbox_to_anchor=(0.02, 0.0),
               ncol=3, fontsize=8)
    fig.suptitle("Tempo do B&B: achar × provar (tracejado = prazo de 30 min)",
                 x=0.02, y=1.04, ha="left", fontsize=10)
    _save(fig, out_dir, "warmstart_find_vs_prove")


def plot_collapse(test, stress, collapse, out_dir: Path, limit: float) -> None:
    """Tempo x N (semilog) com o ajuste exponencial, o prazo e a instância de estresse."""
    colors = style(ENTITY_ORDER)
    fig, ax = plt.subplots(figsize=(6.3, 3.9))
    grid = np.linspace(test.n.min(), 80, 200)
    for s in ENTITY_ORDER:
        g = test[test.strategy == s]
        fit = collapse[collapse.strategy == s].iloc[0]
        color, marker = colors[s]
        ax.plot(grid, np.exp(fit.alpha + fit.beta * grid), color=color, linewidth=1.2, alpha=0.8)
        ax.plot(g.n, g.time_total, marker, color=color, markersize=5, markeredgecolor=SURFACE,
                markeredgewidth=0.8, linestyle="none",
                label=f"{LABELS[s]} (N previsto = {fit.n_collapse:.0f})")
        st = stress[stress.strategy == s]
        if len(st):
            r = st.iloc[0]
            filled = r.status == "ok"
            ax.plot(r.n, r.time_total, marker, markersize=8, linestyle="none",
                    color=color if filled else SURFACE, markeredgecolor=color,
                    markeredgewidth=1.5)
    ax.axhline(limit, color=LIMIT_LINE, linewidth=1, linestyle="--")
    ax.text(grid.min(), limit * 1.25, "prazo de 30 min", color=MUTED, fontsize=8)
    ax.set_yscale("log")
    ax.set_xlabel("N (vértices)")
    ax.set_ylabel("Tempo do B&B (s)")
    ax.set_title("Ponto de colapso do B&B (marcador grande: rd100-n75; vazado = NA)",
                 loc="left")
    _legend_below(ax)
    _save(fig, out_dir, "collapse")


# ---------------------------------------------------------------------------
# Figuras da T20 (sensibilidade)
# ---------------------------------------------------------------------------

FEATURE_LABELS = {
    "n": "N", "aspect_ratio": "Razão de aspecto", "hull_ratio": "Proporção no fecho",
    "spatial_entropy": "Entropia espacial", "clark_evans": "Clark-Evans",
    "mst_max_degree": "Grau máx. na MST", "mst_leaf_ratio": "Folhas na MST",
    "nn_cv": "CV do vizinho mais próximo", "odd_ratio": "Ímpares na MST",
}
# Divergente azul <-> vermelho com cinza neutro no zero (paleta de referência):
# vermelho = a característica PIORA o gap (ρ > 0); azul = FACILITA (ρ < 0)
DIVERGING = ["#1c5cab", "#86b6ef", "#f0efec", "#f0a3a2", "#c03332"]


def plot_sensitivity_heatmap(corr, algorithms, features, out_dir: Path) -> None:
    from matplotlib.colors import LinearSegmentedColormap
    cmap = LinearSegmentedColormap.from_list("div", DIVERGING)
    wide = corr.pivot(index="feature", columns="algorithm", values="rho_partial_n")
    pvals = corr.pivot(index="feature", columns="algorithm", values="p_partial_n")
    wide, pvals = wide.loc[features, algorithms], pvals.loc[features, algorithms]
    fig, ax = plt.subplots(figsize=(6.3, 4.0))
    im = ax.imshow(wide.to_numpy(), cmap=cmap, vmin=-1, vmax=1, aspect="auto")
    for i in range(len(features)):
        for j in range(len(algorithms)):
            v, p = wide.iat[i, j], pvals.iat[i, j]
            mark = "*" if p < 0.05 else ""
            ax.text(j, i, f"{v:+.2f}{mark}", ha="center", va="center", fontsize=8,
                    color=SURFACE if abs(v) > 0.6 else TEXT)
    ax.set_xticks(range(len(algorithms)))
    ax.set_xticklabels([LABELS[a].replace(" + ", " +\n").replace("Vizinho mais ", "Vizinho mais\n")
                        for a in algorithms])
    ax.set_yticks(range(len(features)))
    ax.set_yticklabels([FEATURE_LABELS[f] for f in features])
    ax.grid(False)
    ax.tick_params(length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)
    cbar = fig.colorbar(im, ax=ax, fraction=0.04, pad=0.02)
    cbar.set_label("ρ parcial (controlando N)")
    cbar.outline.set_visible(False)
    ax.set_title("Característica x gap (vermelho = piora, azul = facilita; * = p < 0,05)",
                 loc="left")
    _save(fig, out_dir, "sensitivity_heatmap")


def plot_regression_coefficients(reg, info, out_dir: Path) -> None:
    reg = reg.iloc[::-1]  # primeira característica no topo
    y = np.arange(len(reg))
    fig, ax = plt.subplots(figsize=(6.3, 3.4))
    ax.axvline(0, color=LIMIT_LINE, linewidth=1, linestyle="--")
    for yi, (_, r) in zip(y, reg.iterrows()):
        color = TEXT if r.ci_excludes_zero else MUTED
        ax.plot([r.ci_low, r.ci_high], [yi, yi], color=color, linewidth=1.5)
        ax.plot(r.beta, yi, "o", markersize=6, markeredgecolor=color, markeredgewidth=1.2,
                markerfacecolor=color if r.ci_excludes_zero else SURFACE)
    ax.set_yticks(y)
    ax.set_yticklabels([FEATURE_LABELS[f] for f in reg.feature])
    ax.set_xlabel("β padronizado (gap em desvios-padrão por 1 desvio-padrão da característica)")
    ax.grid(axis="y", visible=False)
    ax.set_title(f"Peso das características no gap (R² = {info['r2_in_sample']:.2f} na amostra, "
                 f"{info['r2_loo_instance']:.2f} fora)", loc="left")
    ax.text(1.0, -0.25, "cheio = IC 95% não contém 0; vazado = contém 0",
            transform=ax.transAxes, ha="right", fontsize=8, color=MUTED)
    _save(fig, out_dir, "sensitivity_coefficients")
