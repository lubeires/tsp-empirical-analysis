# Tarefas — TP2: TSP Geométrico

Derivadas de `docs/plan.md`. Uma tarefa por vez: explicação → aprovação → implementação → revisão. Marcada como concluída só após a revisão aprovada.

## Fase 0: Preparação (20/11)
- [x] **T01** Criar as pastas, o `.venv`, o `requirements.txt` com versões fixadas e o `.gitignore`. *Pronto quando:* todos os imports funcionam.
- [x] **T02** Baixar da TSPLIB as instâncias de origem e de teste, com os ótimos publicados, e confirmar a lista `EUC_2D` (D1). *Pronto quando:* arquivos em `data/tsplib/`; D1 confirmada ou corrigida.

## Fase 1: Base (20/11)
- [x] **T03** `tsplib.py` + `distance.py` (leitura e matriz com `nint`). *Pronto quando:* a rota ótima oficial do berlin52 custa 7542.
- [x] **T04** `generate.py`: 12 sub-instâncias + `manifest.csv` (RF1). *Pronto quando:* gerar duas vezes produz arquivos idênticos.
- [x] **T05** `instrument.py`: `timed` e modo de memória (RF5). *Pronto quando:* teste com uma função falsa passa.

## Fase 2: Algoritmos (21/11)
- [x] **T06** Auxiliares de teste (validar rota, força bruta) + rota trivial + vizinho mais próximo. *Pronto quando:* testes do P3 passam.
- [x] **T07** Fecho convexo + inserção mais barata. *Pronto quando:* testes passam.
- [x] **T08** `mst.py` (Prim). *Pronto quando:* o custo bate com o `scipy` em instâncias aleatórias.
- [x] **T09** Twice-around-the-tree. *Pronto quando:* rota válida e custo ≤ 2 × ótimo.
- [x] **T10** Christofides (emparelhamento, Hierholzer, atalhos). *Pronto quando:* rota válida e custo ≤ 1,5 × ótimo.
- [x] **T11** `bnb.py` (limite inferior, DFS, contadores, prazo). *Pronto quando:* ótimo = força bruta para N ≤ 9 e o prazo interno funciona.
- [x] **T12** Ponto de decisão: auditoria com `cProfile` e medição do B&B com N = 20, 30 e 40. *Pronto quando:* decidido se N = 36/40 ficam (D5) e se vale ajustar algo.

## Fase 3: Experimentos (21/11 à noite → 22/11)
- [x] **T13** `run.py`: executor paralelo, retomável, com limite de segurança (RF4). *Pronto quando:* ensaio com limite de 10 s gera linhas `NA` com os contadores.
- [x] **T14** Rodar aproximados e heurísticas em sequência. *Pronto quando:* `runs.csv` completo para esses algoritmos.
- [x] **T15** Disparar o B&B completo (75 execuções). *Pronto quando:* em andamento; o resto da fase segue em paralelo.
- [x] **T16** `profile_memory.py` (RF5). *Pronto quando:* `profile.csv` com os picos de memória.
- [x] **T17** `features.py` + `features.csv` (RF6). *Pronto quando:* 15 linhas sem valores faltando.

## Fase 4: Análises (22/11)
- [x] **T18** `complexity.py`: curvas com R² e RMSE (RF7a). *Pronto quando:* tabela e figura geradas.
- [x] **T19** `warmstart.py` (RF7b), depende do T15. *Pronto quando:* tabela e figura geradas.
- [x] **T20** `sensitivity.py` (RF7c). *Pronto quando:* correlações e modelos gerados.
- [x] **T21** Um único comando que refaz todas as tabelas e figuras (RF8). *Pronto quando:* critério de aceitação atendido.

## Fase 5: Relatório e entrega (23–24/11)
- [x] **T22** Rascunho da Introdução e de Implementação/Auditoria (pode começar durante o T15). *Pronto quando:* PDF compilando sem erros, com as seções 1, 2 e a configuração experimental.
- [x] **T23** Resultados e Conclusões. *Pronto quando:* artigo completo.
- [x] **T24** README de reprodução, exportar prompts, checar a especificação ponto a ponto. *Pronto quando:* tudo pronto para subir no GitHub.

**Em paralelo ao T15:** T16, T17, T18, T20 e T22. Só o T19 espera o B&B terminar.
