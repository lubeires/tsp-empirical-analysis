# Constituição do TP2 — TSP Geométrico (Algoritmos 2)

Regras gerais que valem para todo o projeto. Especificação, plano e tarefas devem obedecê-las.

## P1. Entendimento antes de entrega
A nota depende da arguição. Todo código é escrito em módulos pequenos e diretos, sem abstrações desnecessárias. Cada função é explicada antes de ser aceita; nada entra sem aprovação da autora.

## P2. Fidelidade ao enunciado
- Distância `EUC_2D` com arredondamento `nint` (definição da TSPLIB).
- Limite de 30 min por execução, incluindo o tempo da heurística de warm-start.
- Execuções que estouram o limite são registradas como `NA`, preservando os contadores parciais.
- Apenas bibliotecas permitidas (padrão, NumPy, SciPy, scikit-learn, Pandas); NetworkX somente como apoio e sempre com profiling.

## P3. Corretude verificável
Todo algoritmo tem testes automáticos:
- a rota é uma permutação válida dos vértices;
- o custo é recalculado de forma independente;
- o ótimo do Branch-and-Bound confere com força bruta para N ≤ 10;
- os aproximados respeitam as razões 2 (Twice-around-the-tree) e 1,5 (Christofides) em relação ao ótimo.

## P4. Instrumentação de primeira classe
As sub-rotinas caras são instrumentadas desde a primeira versão. Tempo e memória são medidos em execuções separadas, para que uma medição não distorça a outra. A instrumentação não pode alterar a complexidade do algoritmo.

## P5. Reprodutibilidade
Sementes fixas, versões das bibliotecas fixadas e um script que refaz tudo do zero (instâncias → execuções → tabelas → figuras). Dados brutos nunca são editados à mão.

## P6. Dados à prova de falhas
Um registro por execução, com esquema fixo, gravado logo que a execução termina. Se o processo cair, o que já rodou continua salvo e o experimento retoma de onde parou.

## P7. Honestidade científica
Timeouts, falhas e resultados ruins aparecem no relatório. Limitações (por exemplo, poucas instâncias para a regressão) ficam explícitas.

## P8. Mínimo completo primeiro
O fluxo inteiro precisa rodar de ponta a ponta antes de qualquer melhoria. Os experimentos longos começam o quanto antes. Extras (por exemplo, limite de Held-Karp) só entram se sobrar tempo.

## P9. Rastreabilidade
Decisões são registradas com justificativa em `docs/decisions.md`, que alimenta a seção de Auditoria do relatório. O histórico de prompts é guardado para o anexo obrigatório.

## P10. Controle de versão pela autora
Commits, push e criação do repositório são feitos apenas pela autora. O assistente sugere mensagens de commit em cada ponto de parada.

## P11. Idioma
Nomes no código (variáveis, funções), de arquivos e de pastas em inglês; comentários e docstrings em português. Documentação e relatório em português.

## Governança
A constituição só muda com aprovação explícita da autora.
