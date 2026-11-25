# Conferência da especificação (T24)

Cada requisito e critério de aceitação de `docs/specification.md`, com a evidência e a
situação. Conferido em 23/11/2026, depois da rodada final do B&B (limite corrigido, D35), e revisado em 24/11 após uma auditoria independente contra o enunciado.

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
| **RF7b** Warm-start: nós expandidos e podados, tempo, custo da heurística | `results/tables/warmstart_*.csv` (colunas de podados e taxa de poda); artigo, seção 3.3 e Tabela 4 | OK |
| **RF7c** Sensibilidade: características × gap | `results/tables/sensitivity_*`; artigo, seção 3.5 | OK |
| **RF8** CSVs, figuras, tabelas LaTeX | `results/` (11 figuras em PDF e PNG, 24 tabelas) | OK |
| **RF9** Artigo SBC em PDF e `.tex` | `report/main.pdf` e `report/` | OK\* (corpo com 15 páginas, D36) |
| **RF9** Repositório GitHub | repositório criado e sincronizado pela autora | OK |
| **RF9** Histórico de prompts | `prompts/session-72d17e35.md` | OK (exportação final feita; sem e-mail nem nome) |

## Critérios de aceitação

| Critério | Evidência | Situação |
|---|---|---|
| Os testes da constituição (P3) passam | `pytest`: 501 testes passando | OK |
| B&B encontra o ótimo publicado de eil51, berlin52 e st70 quando termina | 426, 7 542 e 675 nas 5 estratégias das 3 instâncias | OK |
| Gap do Christofides ≤ 50% e do Twice-around ≤ 100% | máximos de 13,2% e 42,5% nas 15 instâncias | OK |
| Um único comando refaz tabelas e figuras | `python -m analysis`: 47 arquivos, idênticos byte a byte entre execuções | OK |
| Nenhuma execução que estourou o limite perde os contadores parciais | ver RF3 | OK |

## Auditoria independente (24/11)

Um agente sem acesso às conclusões anteriores conferiu o trabalho contra o enunciado
(veredito: pronto com ressalvas). Correções feitas: comparação dos **nós podados** no
artigo e na Tabela 4 (pedida no enunciado e antes ausente); frase sobre o R² das árvores;
contagens de testes (501) e decisões (36); "instâncias derivadas da TSPLIB" no resumo;
memória do B&B medida só com Christofides e N ≤ 52; contexto das medições da AGM e do
limite inferior. Mantido e justificado (D30): nenhuma das 15 instâncias estourou o prazo;
o colapso é mostrado pela instância de estresse, fora do conjunto, para manter os 80%
com N ≤ 40.

## Pendências

Nenhuma. Após estas correções: novo commit e push.
