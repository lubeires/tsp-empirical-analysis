# Conferência da especificação (T24)

Cada requisito e critério de aceitação de `docs/specification.md`, com a evidência e a
situação. Conferido em 23/11/2026, depois da rodada final do B&B (limite corrigido, D35).

Legenda: **OK** atendido · **OK\*** atendido com divergência registrada · **Autora** depende de ação da autora.

## Requisitos funcionais

| Requisito | Evidência | Situação |
|---|---|---|
| **RF1** Ler TSPLIB `EUC_2D` | `tsp/tsplib.py` rejeita outros tipos; `tests/test_tsplib.py` | OK |
| **RF1** 12 sub-instâncias com os N da D5, de origens variadas (D6) | `data/instances/manifest.csv` (2 por origem, 6 origens); `tests/test_generate.py` | OK |
| **RF1** eil51, berlin52, st70; 15 instâncias | manifesto: 12 `sub` + 3 `full`; 80% com N ≤ 40 | OK |
| **RF1** Manifesto com origem, semente, índices, N, ótimo | colunas `source`, `seed`, `indices`, `n`, `optimum` | OK |
| **RF1** (extra, D30) Instância de estresse rd100-n75 | `kind = stress`, fora do conjunto de teste | OK |
| **RF2** B&B, Twice-around, Christofides | `tsp/bnb.py`, `tsp/approx.py`; validados contra força bruta (`tests/test_bnb.py`) e pelos fatores 2 e 1,5 (`tests/test_approx.py`, `tests/test_christofides.py`) | OK |
| **RF2** Heurísticas trivial, vizinho mais próximo, inserção pelo fecho | `tsp/heuristics.py`; `tests/test_heuristics.py`, `tests/test_hull.py` | OK |
| **RF3** Nós expandidos e podados, profundidade, melhorias, tempo total e da heurística | colunas de `results/runs.csv` (`BnBResult`) | OK |
| **RF3** Timeout guarda contadores parciais e melhor rota | as 5 execuções `NA` da rd100-n75 têm nós (68–76 mil), podas, profundidade 75 e rota (7 205 ou 7 230) | OK |
| **RF4** B&B: 15 instâncias × 5 estratégias | 75 execuções `ok` + 5 `NA` (estresse) em `runs.csv` | OK |
| **RF4** Aproximados e heurísticas: repetições | 30 repetições × coletor ligado/desligado (D26; a especificação original previa 5) | OK\* |
| **RF4** Limite de 30 min com a heurística, `NA` | prazo absoluto em `tsp/bnb.py`; `time_limit = 1800` em cada linha | OK |
| **RF4** Retomada e paralelismo | `experiments/run.py` (`pending_tasks`, `repair_csv`); usada de fato na rodada final, interrompida e retomada; `tests/test_run.py` | OK |
| **RF5** Tempo por sub-rotina | `results/profile.csv`: matriz, MST, ímpares, emparelhamento (e montagem do grafo), euleriano, atalhos, limite inferior, fecho, inserção | OK |
| **RF5** Pico de memória por sub-rotina | `results/profile_memory.csv` (mesmas sub-rotinas, `tracemalloc`) | OK |
| **RF6** As 9 características | `results/features.csv` (n, aspecto, fecho, entropia, Clark-Evans, grau máx. e folhas da MST, CV do vizinho, ímpares); `tests/test_features.py` | OK |
| **RF7a** Complexidade com R² e RMSE | `results/tables/complexity_*.csv`; artigo, seção 3.2 | OK |
| **RF7b** Warm-start: nós, podas, tempo, custo da heurística | `results/tables/warmstart_*.csv`; artigo, seção 3.3 | OK |
| **RF7c** Sensibilidade: características × gap | `results/tables/sensitivity_*`; artigo, seção 3.5 | OK |
| **RF8** CSVs, figuras, tabelas LaTeX | `results/` (11 figuras em PDF e PNG, 24 tabelas) | OK |
| **RF9** Artigo SBC em PDF e `.tex` | `report/main.pdf` e `report/` | OK\* (corpo com 15 páginas, D36; nome e e-mail a preencher) |
| **RF9** Repositório GitHub | — | Autora |
| **RF9** Histórico de prompts | `prompts/session-72d17e35.md` | OK\* (refazer a exportação ao fim da sessão) |

## Critérios de aceitação

| Critério | Evidência | Situação |
|---|---|---|
| Os testes da constituição (P3) passam | `pytest`: 501 testes passando | OK |
| B&B encontra o ótimo publicado de eil51, berlin52 e st70 quando termina | 426, 7 542 e 675 nas 5 estratégias das 3 instâncias | OK |
| Gap do Christofides ≤ 50% e do Twice-around ≤ 100% | máximos de 13,2% e 42,5% nas 15 instâncias | OK |
| Um único comando refaz tabelas e figuras | `python -m analysis`: 47 arquivos, idênticos byte a byte entre execuções | OK |
| Nenhuma execução que estourou o limite perde os contadores parciais | ver RF3 | OK |

## Pendências da autora antes da entrega

1. Preencher nome e e-mail em `report/main.tex` e recompilar (`cd report && latexmk -pdf main.tex`).
2. Criar o repositório no GitHub e fazer o commit e o push.
3. Pedir a exportação final dos prompts, depois da última mensagem da sessão.
