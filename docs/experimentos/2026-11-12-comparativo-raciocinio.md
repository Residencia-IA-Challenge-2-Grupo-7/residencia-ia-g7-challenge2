# Comparativo A/B: sem raciocínio × raciocínio alto nos dois modos

- **Data:** 2026-11-12
- **Contexto:** issue #34 e [ADR 0011](../decisoes/0011-comparativo-ab-com-o-mesmo-llm.md). O comparativo roda a mesma pergunta no Modo A (DeepSeek V4.1 Flash sem documentos) e no Modo B (busca com guardrails e o mesmo modelo com os lugares recuperados). Aqui, o raciocínio do modelo foi ligado nos dois modos, para ver se ele muda o resultado. O [experimento de 10/11](2026-11-10-llm-pura-raciocinio.md) fez a mesma pergunta só para o Modo A.
- **Como reproduzir:**
  - sem raciocínio: `PYTHONPATH=. python eval/comparativo_ab.py <saída.json>`
  - com raciocínio alto: `PYTHONPATH=. python eval/comparativo_ab.py <saída.json> high`
- **Resultados completos:**
  - [sem raciocínio](../../eval/resultados/comparativo-ab-previa-golden-01-10-2026-11-12.json)
  - [raciocínio alto](../../eval/resultados/comparativo-ab-raciocinio-alto-golden-01-10-2026-11-12.json)

## O que foi medido

- **Perguntas:** os 10 casos do golden dataset (golden_01 a golden_10): 5 de RAs fora do centro, 3 de horário e 2 fora do DF.
- **Execução:**
  - uma rodada por configuração, sem cache, temperatura 0;
  - raciocínio alto com `reasoning.effort = "high"` e limite de 8.000 tokens, porque o raciocínio conta no limite.
- **Acerto:** o nome do lugar do gabarito aparece na resposta. Vale para os 8 casos do DF; nos 2 casos fora do DF, o gabarito é vazio.

## Resultados

| | Modo A, sem raciocínio | Modo A, raciocínio alto | Modo B, sem raciocínio | Modo B, raciocínio alto |
|---|---|---|---|---|
| Acerto do lugar (8 casos do DF) | 0 de 8 | 0 de 8 | 6 de 8 | 6 de 8 |
| Latência p50 / p90 | 4,0 s / 5,1 s | 6,3 s / 11,0 s | 3,0 s / 4,8 s | 3,8 s / 7,3 s |
| Acima dos 5 s do RNF-14 | 2 de 10 | 9 de 10 | 0 de 10 | 3 de 10 |
| Custo médio por pergunta | R$ 0,00083 | R$ 0,00180 | R$ 0,00065 | R$ 0,00122 |
| Tokens de raciocínio (média) | 0 | 336 | 0 | 168 |
| Respostas sem nenhum nome em destaque | 1 de 10 | 6 de 10 | 3 de 10 | 3 de 10 |

- No Modo B, a média de custo e de latência inclui os 3 casos em que o guardrail recusou a pergunta sem chamar o modelo: golden_06 (aderência 0,62) e as 2 perguntas fora do DF.
- A última linha conta os nomes em negrito como sinal de que a resposta indica algum lugar. Ela tem ruído (o negrito às vezes marca um preço ou uma região), mas a leitura das respostas confirma a direção.

## Leitura

- **No Modo B, o raciocínio não mudou o acerto.** Os mesmos 6 casos acertaram e os mesmos 2 erraram (golden_05 e golden_06). Os 2 erros vêm da busca: o VBQ não foi recuperado, e o golden_06 foi barrado pelo limiar. Pensar mais sobre os 3 lugares recuperados não traz o lugar que ficou de fora.
- **No Modo A, o raciocínio trocou invenção por recusa**, como no experimento de 10/11. Em 6 de 10 respostas, o modelo não indicou nenhum lugar ("não sei indicar com segurança"). O acerto continuou zero.
- **O custo do raciocínio é a latência.** O Modo B passou a estourar os 5 s do RNF-14 em 3 de 10 perguntas (p90 de 7,3 s), e o Modo A em 9 de 10. O custo por pergunta quase dobrou, mas continua abaixo de R$ 0,002.
- **Consequência para o produto:** o Modo B sem raciocínio é a melhor das quatro configurações. Ele acerta o mesmo número de casos, é o mais rápido e o mais barato. Para melhorar o acerto, o caminho é a busca (filtro por RA, busca vetorial), não o raciocínio do modelo.

## Limitações

- 10 perguntas e uma rodada por configuração: dá a direção, não números finais. O benchmark da issue #38, com 20 perguntas, dá a medida oficial.
- O acerto aqui é só a presença do nome certo. A fidelidade de preço, endereço e horário e a contagem de lugares inventados são do avaliador da issue #36.
- A latência varia com o provedor que a OpenRouter escolhe a cada chamada.
