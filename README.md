# TSP geométrico: análise empírica de algoritmos exatos e aproximados

Trabalho prático 2 de Algoritmos 2 (DCC/UFMG). Implementação, instrumentação e
avaliação empírica de um **Branch-and-Bound** exato (limite inferior de Held-Karp) e dos
aproximados **Twice-around-the-tree** e **Christofides** para o PCV `EUC_2D` da TSPLIB,
com cinco estratégias de *warm-start* para o B&B (trivial, vizinho mais próximo,
inserção pelo fecho convexo, Twice-around e Christofides).

- **Artigo (SBC):** [`report/main.pdf`](report/main.pdf), com o código-fonte LaTeX em [`report/`](report/)
- **Dados brutos:** [`results/`](results/) (execuções, profiling, características)
- **Histórico de prompts (uso de IA):** [`prompts/`](prompts/)
- **Processo e decisões:** [`docs/`](docs/)

## Estrutura

| Pasta | Conteúdo |
|---|---|
| `src/tsp/` | Algoritmos: leitura TSPLIB, distâncias, heurísticas, Prim, Twice-around, Christofides, B&B, instrumentação, características |
| `src/experiments/` | Download da TSPLIB, executor dos experimentos, profiling de memória |
| `src/analysis/` | Ajustes de complexidade, warm-start, sensibilidade, caso adversarial, tabelas e figuras |
| `tests/` | Testes automatizados (`pytest`) |
| `data/tsplib/` | Instâncias originais da TSPLIB (conferidas por SHA-256) e ótimos publicados |
| `data/instances/` | 12 sub-instâncias sorteadas, a instância de estresse e o `manifest.csv` |
| `results/` | `runs.csv` (uma linha por execução), `profile.csv` (tempo por sub-rotina), `profile_memory.csv`, `features.csv`, `tables/`, `figures/`, `archive/` |
| `report/` | Artigo no modelo SBC |
| `docs/` | Constituição, especificação, plano, tarefas, decisões (D1–D36) e conferência da especificação |
| `prompts/` | Transcrição da sessão do Claude Code usada no trabalho |

## Ambiente

Python 3.12 (Linux). Versões fixadas em `requirements.txt`.

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/pip install -e .
.venv/bin/python -m pytest        # ~30 s
```

O artigo precisa de uma instalação TeX com `pdflatex`, `latexmk`, `babel` (português) e
`booktabs` (por exemplo, TeX Live). O modelo SBC (`sbc-template.sty` e `sbc.bst`) já está
em `report/`.

## Reprodução

Todos os comandos rodam na raiz do projeto. As sementes são fixas, e as etapas de
análise geram arquivos idênticos byte a byte a cada execução. Os dados de todas as
etapas já estão no repositório; para só refazer tabelas, figuras e artigo, pule para o
passo 6.

| # | Etapa | Comando | Duração (i5-1135G7, 3 GB) |
|---|---|---|---|
| 1 | Baixar a TSPLIB e conferir os arquivos | `.venv/bin/python -m experiments.fetch_tsplib` | segundos |
| 2 | Gerar as sub-instâncias e o manifesto | `.venv/bin/python -m tsp.generate` | segundos |
| 3 | Heurísticas e aproximados (30 repetições × coletor de lixo ligado/desligado) | `.venv/bin/python -m experiments.run approx` | ~5 min |
| 4 | Branch-and-Bound (80 execuções, 6 processos, prazo de 30 min) | `.venv/bin/python -m experiments.run bnb --workers 6 --time-limit 1800` | ~1 h |
| 5 | Profiling de memória (`tracemalloc`) | `.venv/bin/python -m experiments.profile_memory` | ~10 min |
| 6 | Características, tabelas e figuras | `.venv/bin/python -m analysis` (ou `--quick`, sem refazer o *bootstrap*) | ~1–3 min (`--quick`: ~20 s) |
| 7 | Artigo | `cd report && latexmk -pdf main.tex` | segundos |

**Retomada.** Os passos 3, 4 e 5 gravam cada execução no CSV assim que ela termina. Se
forem interrompidos, basta repetir o mesmo comando: as execuções concluídas são puladas,
e só as que faltam rodam. Uma execução do B&B interrompida no meio recomeça do zero.

**Medições de tempo.** As execuções do B&B rodam em paralelo; por isso os tempos dele
só são comparados dentro da mesma rodada, e as curvas de complexidade usam os
aproximados, que rodam em sequência (D25). Para medir tempos, evite usar a máquina
durante as rodadas e não deixe o computador suspender.

## Onde está cada requisito

| Requisito | Implementação |
|---|---|
| Instâncias `EUC_2D` e sub-instâncias (RF1) | `src/tsp/tsplib.py`, `src/tsp/generate.py` |
| Algoritmos (RF2) | `src/tsp/heuristics.py`, `src/tsp/mst.py`, `src/tsp/approx.py`, `src/tsp/bnb.py` |
| Contadores do B&B e prazo (RF3) | `src/tsp/bnb.py` (`BnBResult`) |
| Execução experimental (RF4) | `src/experiments/run.py` |
| Profiling de tempo e memória (RF5) | `src/tsp/instrument.py`, `src/experiments/profile_memory.py` |
| Características das instâncias (RF6) | `src/tsp/features.py` |
| Análises (RF7) | `src/analysis/complexity.py`, `warmstart.py`, `sensitivity.py`, `adversarial.py` |
| Saídas (RF8) | `src/analysis/__main__.py`, `src/analysis/plotting.py` |

A conferência ponto a ponto está em [`docs/spec-check.md`](docs/spec-check.md).

## Uso de IA

O código, os testes, os documentos e o artigo foram produzidos com o assistente
**Claude Code** (Anthropic), num processo guiado por especificação: constituição,
especificação, plano e lista de tarefas foram aprovados pela autora antes de qualquer
código, e cada tarefa foi apresentada e aprovada antes de ser executada. A seção 2.5 do
artigo descreve a auditoria do código; as 36 decisões estão em
[`docs/decisions.md`](docs/decisions.md), e a transcrição completa da sessão está em
[`prompts/`](prompts/).
