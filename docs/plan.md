# Plano técnico — TP2: TSP Geométrico

Descreve *como* implementar `docs/specification.md`, obedecendo a `docs/constitution.md`. As decisões D7–D17 estão em `docs/decisions.md`.

## 1. Ambiente (D7)
- Python 3.12 em ambiente virtual `.venv`, versões fixadas em `requirements.txt`.
- Bibliotecas: numpy, scipy, pandas, scikit-learn, networkx.
- Ferramentas de apoio (fora dos algoritmos): matplotlib (figuras) e pytest (testes).
- Máquina: 8 núcleos, ~3 GB de RAM (WSL).

## 2. Estrutura de pastas (raiz: `tsp-empirical-analysis/`, D18)
```
data/tsplib/        arquivos .tsp originais
data/instances/     15 instâncias geradas + manifest.csv
src/tsp/            tsplib.py, distance.py, generate.py, heuristics.py, mst.py,
                    approx.py, bnb.py, features.py, instrument.py
src/experiments/    run.py (executor), profile_memory.py
src/analysis/       complexity.py, warmstart.py, sensitivity.py, figures.py
tests/              testes com pytest
results/            runs.csv, profile.csv, features.csv, figures/, tables/
report/             .tex do modelo SBC
prompts/            transcrições exportadas
```

## 3. Algoritmos

| Componente | Implementação | Custo |
|---|---|---|
| Matriz de distâncias | NumPy vetorizado + `nint` | O(n²) |
| Rota trivial | 0 → 1 → … → n−1 | O(n) |
| Vizinho mais próximo | começa no vértice 0 | O(n²) |
| Fecho convexo + inserção | fecho pelo método de Andrew; inserção mais barata simples | O(n log n) + O(n³) |
| MST (D8) | Prim com NumPy, implementação própria | O(n²) |
| Twice-around-the-tree | MST + pré-ordem a partir do vértice 0 | O(n²) |
| Christofides (D8) | MST → vértices de grau ímpar → `networkx.min_weight_matching` → circuito euleriano (Hierholzer, próprio) → atalhos | ~O(n³), dominado pelo emparelhamento |

### Branch-and-Bound (D9 → D20, D10, D21)
- **Exploração em profundidade (DFS) recursiva:** memória O(n), importante com 3 GB de RAM.
- **Limite inferior de cada nó:**
  ```
  custo do caminho parcial
  + MST dos vértices ainda não visitados
  + menor aresta do último vértice do caminho até esse conjunto
  + menor aresta do vértice inicial até esse conjunto
  ```
  (limite 1-tree adaptado para caminhos parciais; **substituído na T12 pelo Held-Karp**, que é esta mesma fórmula com penalidades π por vértice ajustadas por subgradiente — D20, D21)
- **Ordem dos filhos:** do mais próximo para o mais distante.
- **Poda:** quando o limite inferior é ≥ ao limite superior.
- **Prazo interno:** o relógio é conferido a cada nó; ao chegar a 30 min o B&B para e devolve os contadores parciais. O executor tem um limite de segurança de 31 min, que encerra o processo se ele travar.

## 4. Instrumentação (D11)
- **Tempo:** gerenciador de contexto `timed("nome")` que acumula `perf_counter` por sub-rotina em cada execução.
- **Memória:** modo separado com `tracemalloc`, registrando o pico de cada sub-rotina.
- `cProfile` só durante a auditoria, para encontrar gargalos.

## 5. Execução (D12, D13)

| O que roda | Como roda |
|---|---|
| B&B | 75 execuções, 6 processos em paralelo |
| Aproximados e heurísticas | em sequência, 5 repetições, mediana |
| Memória do B&B | só instâncias com N ≤ 24, warm-start de Christofides |

- Cada execução terminada vira imediatamente uma linha em `results/runs.csv`; ao reiniciar, o executor pula o que já existe.
- Estimativa: se 25 execuções do B&B baterem 30 min, ~12,5 h de processamento, ou seja, ~2 a 3 h de relógio com 6 processos.
- A disputa de memória e cache entre processos paralelos é relatada como limitação.

## 6. Esquema de dados
- **`runs.csv`:** instância, N, algoritmo, estratégia, repetição, status (`ok`/`NA`), custo, ótimo, gap, tempo total, tempo da heurística, nós expandidos, nós podados, profundidade máxima, melhorias do limite superior.
- **`profile.csv`:** instância, algoritmo, sub-rotina, chamadas, tempo, pico de memória.
- **`features.csv`:** uma linha por instância, com as características do RF6.

## 7. Análises (D14)
- **Complexidade:** `scipy.optimize.curve_fit` comparando n², n² log n e n³ para os aproximados; a·bⁿ para os nós expandidos do B&B (regressão em escala logarítmica); R² e RMSE de cada ajuste.
- **Warm-start:** tabela e gráfico de nós expandidos/podados e tempo por estratégia; tempo da heurística somado ao tempo da busca.
- **Sensibilidade:** correlação de Spearman entre características e gap; árvore de decisão rasa (profundidade 2); regressão linear com variáveis padronizadas. Limitação explícita: ~15 instâncias.

## 8. Testes
pytest cobrindo o P3 da constituição; força bruta para N ≤ 9 com `itertools.permutations`.

## 9. Relatório e prompts (D15, D16)
Artigo no Overleaf com o modelo SBC; `.tex` final copiado para `report/`. Transcrições do Claude Code exportadas para `prompts/` no fim.

## 10. Cronograma (D17)

| Dia | Meta |
|---|---|
| 20/11 | Tarefas + ambiente + leitura e geração das instâncias |
| 21/11 | Algoritmos + testes; disparar o B&B à noite |
| 22/11 | Características, profiling de memória, análises |
| 23/11 | Relatório |
| 24/11 | Revisão, exportar prompts, entrega (até 23h59) |
