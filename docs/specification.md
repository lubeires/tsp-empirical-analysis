# Especificação — TP2: TSP Geométrico

Descreve *o que* o sistema faz e *como saber se ficou pronto*. O *como* fica em `docs/plan.md`. Obedece a `docs/constitution.md`.

## 1. Objetivo
Implementar, instrumentar e avaliar empiricamente um algoritmo exato (Branch-and-Bound) e dois aproximados (Twice-around-the-tree e Christofides) para o TSP `EUC_2D`, produzindo dados para três análises: complexidade empírica, impacto do warm-start e sensibilidade às características das instâncias.

## 2. Requisitos funcionais

### RF1 – Instâncias
- Ler arquivos TSPLIB do tipo `EUC_2D`.
- Gerar 12 sub-instâncias com N ∈ {12, 14, 16, 18, 20, 22, 24, 27, 30, 33, 36, 40} (D5), sorteando subconjuntos aleatórios de pontos de instâncias de origem com geometrias variadas (D6).
- Incluir as instâncias completas eil51, berlin52 e st70 (faixa limite). Total: 15 instâncias.
- Um manifesto registra, por instância: origem, semente, índices sorteados, N e ótimo conhecido (quando houver).

### RF2 – Algoritmos
Todos recebem uma instância e devolvem uma rota e o custo dela:
- exatos e aproximados: Branch-and-Bound, Twice-around-the-tree e Christofides;
- heurísticas de limite superior inicial do B&B: rota trivial (1 → 2 → … → n → 1), vizinho mais próximo e inserção a partir do fecho convexo.

### RF3 – Contadores do B&B
Nós expandidos, nós podados, profundidade máxima, número de melhorias do limite superior, tempo total e tempo da heurística inicial. Em caso de timeout, guarda os valores parciais e a melhor rota encontrada até ali.

### RF4 – Execução experimental

| Algoritmo | Execuções |
|---|---|
| B&B | 15 instâncias × 5 estratégias de limite inicial (1 execução cada) |
| Twice-around-the-tree e Christofides | 15 instâncias × 5 repetições |
| Heurísticas | 15 instâncias × 5 repetições |

- Limite de 30 min por execução, incluindo a heurística inicial; quem estoura fica `NA`.
- A execução pode ser retomada de onde parou e roda em paralelo.

### RF5 – Profiling
Tempo e pico de memória das sub-rotinas: matriz de distâncias, MST, vértices de grau ímpar, emparelhamento, circuito euleriano, atalhos, cálculo do limite inferior, fecho convexo e inserção.

### RF6 – Características das instâncias
N; razão de aspecto do retângulo envolvente; proporção de pontos no fecho convexo; entropia espacial (grade); grau máximo e grau médio na MST; coeficiente de variação da distância ao vizinho mais próximo.

### RF7 – Análises
- **(a) Complexidade empírica:** ajuste de curvas candidatas de tempo e memória em função de N, com R² e RMSE.
- **(b) Warm-start:** comparação de nós expandidos, nós podados e tempo total entre as 5 estratégias, incluindo se o custo da heurística compensa.
- **(c) Sensibilidade:** relação entre as características (RF6) e o gap dos aproximados e das heurísticas.

### RF8 – Saídas
CSVs de execuções, profiling e características; figuras; tabelas prontas para LaTeX.

### RF9 – Entrega
Artigo no padrão SBC (PDF e `.tex`), repositório GitHub e anexo com o histórico de prompts.

## 3. Fora do escopo
- Instâncias que não são `EUC_2D`.
- Algoritmos além dos pedidos no enunciado.
- Otimização de desempenho além do necessário para cumprir o prazo.

## 4. Critérios de aceitação
- Os testes do P3 da constituição passam.
- O B&B encontra o ótimo publicado de eil51, berlin52 ou st70 sempre que termina antes do limite.
- Gap de Christofides ≤ 50% e de Twice-around-the-tree ≤ 100% em todas as instâncias com ótimo conhecido.
- Um único comando refaz tabelas e figuras a partir dos CSVs.
- Nenhuma execução que estourou o limite perde os contadores parciais.
