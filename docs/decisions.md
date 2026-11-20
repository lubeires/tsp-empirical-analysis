# Registro de decisões

Cada decisão aprovada pela autora, com justificativa (constituição, P9). Alimenta a seção de Auditoria do relatório.

| ID | Decisão | Justificativa |
|---|---|---|
| D1 | Instâncias com N ≤ 40 são sub-instâncias amostradas (semente fixa) de instâncias `EUC_2D` reais; a faixa limite usa eil51, berlin52 e st70. | A TSPLIB não parece ter instâncias `EUC_2D` com N ≤ 40 (a confirmar ao baixar), e os exemplos do enunciado usam outros tipos de distância. A amostragem permite variar a geometria das instâncias. |
| D2 | Distância `nint(sqrt(...))`. | Definição oficial da TSPLIB; mantém válidos os ótimos publicados. |
| D3 | Gap: em relação ao ótimo do B&B nas sub-instâncias e ao ótimo publicado nas instâncias completas. | Não há ótimo publicado para as sub-instâncias. |
| D4 | Nomes de código, arquivos e pastas em inglês; comentários em português; documentos em `docs/`. | Padrão de código, e consistência com o relatório em português. |
| D5 | Sub-instâncias com N ∈ {12, 14, 16, 18, 20, 22, 24, 27, 30, 33, 36, 40}. | Espaçamento regular para ajuste de curvas, mais denso onde o B&B deve resolver. Se N = 36 ou 40 não fechar, substituir por tamanhos menores e relatar (P7). |
| D6 | Sorteio de subconjuntos aleatórios de pontos, alternando instâncias de origem uniformes (ex.: kroA100, rd100) e agrupadas/estruturadas (ex.: lin105, pr76). | Variar as características geométricas para a análise de sensibilidade; janelas retangulares gerariam instâncias parecidas. |
| D7 | Python 3.12 em `.venv` com versões fixadas; numpy, scipy, pandas, scikit-learn, networkx; matplotlib e pytest como apoio. | Python é a linguagem preferida no enunciado; matplotlib e pytest não fazem parte dos algoritmos (só figuras e testes) e são citados no relatório. |
| D8 | MST por Prim próprio com NumPy; emparelhamento perfeito de custo mínimo via `networkx.min_weight_matching`, com profiling. | Prim é simples de defender; implementar Blossom do zero não cabe no prazo, e o enunciado permite NetworkX como apoio. |
| D9 | Limite inferior do B&B: caminho parcial + MST dos não visitados + menores arestas ligando as pontas do caminho a esse conjunto (1-tree adaptado). | Bem mais forte que o limite das 2 arestas mais baratas ou a redução de matriz, e ainda simples de explicar. Held-Karp fica como extra (P8). |
| D10 | B&B em profundidade (DFS) recursiva, filhos do mais próximo ao mais distante, prazo verificado a cada nó. | Memória O(n) (máquina com 3 GB); aproveita bem o warm-start; best-first arriscaria estourar a memória. |
| D11 | Tempo por sub-rotina com `perf_counter` (gerenciador `timed`); memória em execuções separadas com `tracemalloc`; `cProfile` só na auditoria. | `tracemalloc` deixa a execução 2 a 5× mais lenta e distorceria os tempos. |
| D12 | B&B com 6 processos em paralelo; aproximados e heurísticas em sequência. | 8 núcleos: sobram 2 para o sistema. Em sequência o B&B levaria mais de 10 h. A interferência entre processos é relatada como limitação. |
| D13 | Aproximados e heurísticas: 5 repetições (mediana); B&B: 1 execução; memória do B&B só com N ≤ 24 e warm-start de Christofides. | B&B é determinístico e caro; os demais são rápidos e sujeitos a ruído de medição. |
| D14 | Complexidade por `curve_fit` (n², n² log n, n³; a·bⁿ para nós do B&B) com R² e RMSE; sensibilidade por Spearman + árvore de profundidade 2 + regressão linear padronizada. | Com ~15 instâncias, modelos maiores superajustariam; a limitação é declarada no relatório. |
| D15 | Relatório escrito no Overleaf com o modelo SBC; `.tex` final copiado para `report/`. | Evita instalar TeX localmente. |
| D16 | Transcrições do Claude Code exportadas para `prompts/` no fim. | Anexo obrigatório do enunciado. |
| D17 | Cronograma: 20/11 base e instâncias; 21/11 algoritmos e disparo do B&B; 22/11 análises; 23/11 relatório; 24/11 revisão e entrega. | Prazo sem atraso; os experimentos longos precisam começar cedo (P8). |
| D18 | Projeto em `/home/code/alg-II/tsp-empirical-analysis/` (raiz do repositório); `docs/` entra no repositório. | A pasta `alg-II` guarda material do TP1; o TP2 precisa de repositório próprio. Os documentos de planejamento mostram o processo e alimentam a Auditoria e a arguição. |
