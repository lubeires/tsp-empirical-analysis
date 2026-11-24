# T23 — origem dos números citados no artigo

Todos conferidos contra os arquivos abaixo em 23/11, após a rodada final do B&B e `python -m analysis`.
`T/` = `results/tables/`.

## 3.2 Complexidade
| Número no texto | Fonte |
|---|---|
| b = 1,05 (NN), 1,30 (Prim), 1,30 (hull), 2,84 [2,72; 2,97] (Christofides), 2,98 [2,89; 3,11] (matching), 2,65 (montar grafo) | `T/complexity_time.csv`, modelo `a*n^b` |
| trivial ≈ 1,4 µs, R² < 0 | `T/complexity_time.csv`, `c` = 1,37e-6, `r2` = −0,26 |
| 430 coletas (Christofides), 45 (hull), 0 (demais), 450 repetições | `results/runs.csv`, soma de `gc_collections` com `gc_enabled=True`, sem a n75 |
| razão com/sem coletor: medianas 0,85–1,02; faixa 0,49–1,61 | `results/runs.csv`, mediana por (instância, algoritmo, gc) |
| memória: matriz b = 1,90 (R² 0,99); B&B n² (R² 0,99); inserção b = 2,45, n² com R² 0,99 e RMSE 6,4% vs 4,6% | `T/complexity_memory.csv` |
| nós: fator 1,11–1,17 por vértice, R² 0,78–0,90 | `T/complexity_bnb_nodes.csv` |

## 3.3 Warm-start (rodada final, limite corrigido)
| Número no texto | Fonte |
|---|---|
| −77% (0,233), 15 vitórias, p Holm 0,003, gap inicial 0,9%; Christofides −23% (0,772), 11 vitórias; NN −8% (0,920) e Twice-around −8% (0,923) | `T/warmstart_summary.csv` |
| Friedman χ² = 42,9, p = 1,1e-8; Spearman 0,78 | `T/warmstart_checks.json` |
| Twice-around empata com a trivial em 10 de 15; 1.ª folha = rota do NN em 14 de 15 | `T/warmstart_per_instance.csv`; `ub_history` da trivial × `ub0` do NN (reconferido) |
| heurística máx. 45 ms (Christofides, rd100-n75); 11% (hull, kroA100-n12, 0,02 s) | `T/warmstart_per_instance.csv`, `time_heuristic`, `heuristic_share` |
| tempo mediano −40% (0,601); 658 s no total; st70 1 461 → 796 s | `T/warmstart_summary.csv`; `time_saved`; `time_total` |
| st70: achar 1 270–1 330 s, provar 180–190 s; hull acha em 509 s; mediana 86% achando (trivial) | `T/warmstart_per_instance.csv`, `t_found`, `t_prove` |
| e^β 1,17–1,18; dobra a cada ~4,3 vértices; N previsto 72–74; rodada anterior previa 78 (hull) | `T/collapse.csv`; `results/archive/` + tabela da rodada anterior |
| rd100-n75: 7 205 (hull, Twice-around, Christofides) por volta de 1 490 s; 7 230 (trivial, NN); raiz 6 985; ≤ 3,15% | `T/warmstart_per_instance.csv`; `T/adversarial_root.csv` |

## 3.4 Caso adversarial
| Número no texto | Fonte |
|---|---|
| gaps da raiz: 0 em 7 das 12 sub-instâncias, < 0,03% na maioria; eil51 0,85%; st70 0,61%; kroA100-n33 2,1%; rd100-n75 3,15% | `T/adversarial_root.csv`, `root_gap_pct` |
| kroA100-n33 1 424 nós vs rd100-n40 641 (trivial) | `results/runs.csv` |
| 4 vértices de grau ≠ 2, 7 arestas fora da rota | `T/adversarial_root.csv` |
| 10 000 iterações: 2,1% / 0,84% / 0,60% | medição avulsa da T23 com o limite corrigido (registrada na D35) |
| correção: mesmo custo nas 75 fechadas; razão mediana 1,00; 35 com menos nós, 23 com mais; st70 −6 a −10%; d198-n22 até 1,95×; raiz menor em 2 instâncias (≤ 0,02%) | `T/bound_fix.csv`, `T/bound_fix_summary.json` |
| Spearman parcial gap da raiz × nós = −0,11, p = 0,70; berlin52 2 968 nós vs eil51 1 703 | `T/adversarial_root.csv` + `T/warmstart_per_instance.csv` (trivial) |
| B&B: 455 mil chamadas do limite, ≈ 1,7 ms, 98% do tempo (st70, hull) | `results/profile.csv` |

## 3.5 Sensibilidade
| Número no texto | Fonte |
|---|---|
| gaps medianos 0,9% / 6,3% / 17% / 26%; máximos 13% (Christofides) e 42% (Twice-around) | `analysis.sensitivity.load_gaps()` |
| ρ parcial: entropia → Christofides 0,61 (p 0,020), Twice-around 0,56 (p 0,037); Clark-Evans → Christofides 0,53 (p 0,0496); NN: folhas −0,47, ímpares −0,45 | `T/sensitivity_spearman.csv` |
| regressão: R² 0,44 / −0,27; 60 linhas; 1 removida por VIF; nenhum IC exclui 0 | `T/sensitivity_regression_info.json`, `T/sensitivity_regression.csv` |
| árvores: R² 0,70–0,86 na amostra; Christofides 0,19 fora; divisão N ≤ 34,5 e entropia; 3,5% → 12% | `T/sensitivity_trees.csv`, `T/sensitivity_trees.txt` |
| d198-n22 abaixo da mediana em todos; pr107-n20 0,4% (NN) e 25,8% (Twice-around) | `T/sensitivity_adversarial.csv` |
