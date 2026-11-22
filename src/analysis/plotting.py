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
