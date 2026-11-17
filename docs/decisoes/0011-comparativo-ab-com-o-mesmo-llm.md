# 0011 — Comparativo A/B: o Modo B gera a resposta com o mesmo LLM do Modo A

- **Status:** proposta
- **Data:** 2026-11-12
- **Semana do roadmap:** 3 — Comparação RAG × LLM pura
- **Origem:** issue #34 (motor da comparação e rotas `/api/comparativo`)
- **Requisitos:** RNF-03, RNF-10, RNF-12, RNF-14, RNF-15

## Contexto

A entrega da semana 3 compara, para a mesma pergunta, o **Modo A** (LLM sem documentos, [ADR 0010](0010-baseline-llm-pura-e-guardrails.md)) e o **Modo B** (RAG sobre a base de 93 lugares). A issue #34 pede o motor que roda os dois e as rotas que a interface (#37), o avaliador (#36) e o benchmark (#38) consomem.

Ao implementar, apareceu um problema no Modo B. A rota `/rag/buscar` da semana 2 (`simular_recuperacao_rag`) recupera os lugares e **não chama nenhum LLM**: a resposta é um texto fixo preenchido com o primeiro lugar. Mesmo assim, ela registrava no Langfuse o modelo "gemini-1.5-flash" e tokens estimados.

## Opções consideradas

1. **Usar o texto fixo no Modo B:** rápido (cerca de 20 ms) e sem custo, mas compara um LLM com um template. A taxa de alucinação do Modo B seria zero por construção, e a comparação mediria só a recuperação.
2. **Usar o mesmo LLM no Modo B, com os lugares recuperados como contexto (escolhida):** a única diferença entre os modos passa a ser a base, que é o que a semana 3 quer medir.
3. **Usar outro LLM no Modo B:** misturaria o efeito da base com o efeito do modelo.

## Decisão

- **Modo B** em `src/rag/llm_rag.py` (`gerar_resposta_rag`):
  - mesmo modelo (DeepSeek V4.1 Flash), temperatura 0, roteamento sem retenção, limite de palavras e regra de não inventar do Modo A;
  - o prompt recebe até 3 lugares recuperados como `[FONTE #n]` (nome, tipo, RA, endereço, horário, faixa e preço médio, descrição) e pede que a resposta use só esses documentos e cite as fontes;
  - quando um guardrail bloqueia (fora do DF, aderência abaixo de 0,65, nada no teto), o LLM **não é chamado**, e a recusa do guardrail é a resposta;
  - sem chave da OpenRouter, a resposta é o texto fixo da semana 2, marcada com `disponivel: false` e `modelo: "texto-fixo-sem-llm"`.
- **Motor** em `src/rag/comparador_ab.py` (`executar_comparacao_ab`):
  - roda os dois modos **em paralelo** (a latência de cada um é medida separadamente) e devolve o contrato JSON da issue #34;
  - com `id_golden`, a pergunta vem do golden dataset e a resposta traz o `gabarito`; pergunta diferente da do caso é recusada (422), para o gabarito não ser aplicado à pergunta errada;
  - não calcula notas: alucinação e fidelidade são do avaliador da issue #36.
- **Rotas:** `GET /api/comparativo/golden` (perguntas, sem o gabarito) e `POST /api/comparativo/executar`.
- A rota `/rag/buscar` continua igual, mas passou a registrar no Langfuse `texto-fixo-sem-llm` no lugar de "gemini-1.5-flash".

## Justificativa e evidências

Prévia com os 10 casos do golden (golden_01 a golden_10), em 12/11, sem cache ([resultados](../../eval/resultados/comparativo-ab-previa-golden-01-10-2026-11-12.json), `eval/comparativo_ab.py`):

| | Modo A | Modo B |
|---|---|---|
| Latência p50 / p90 | 4,0 s / 5,1 s | 3,0 s / 4,8 s |
| Acima dos 5 s do RNF-14 | 2 de 10 | 0 de 10 |
| Lugar do gabarito entre as fontes, nos 8 casos do DF | não se aplica | 6 de 8 |
| Perguntas fora do DF recusadas | não se aplica (o modelo responde) | 2 de 2, sem chamar o LLM |

- Nos 6 acertos, o Modo B escolheu o lugar do gabarito mesmo quando ele não estava em 1º lugar na recuperação (golden_01, golden_04 e golden_08). O texto fixo da semana 2 teria recomendado o 1º lugar, que estava errado nesses casos.
- Os 2 erros vêm da recuperação, não do LLM:
  - **golden_05:** o VBQ (Samambaia) não ficou entre os 3 primeiros, e o modelo respondeu que a base não tinha um lugar que atendesse;
  - **golden_06:** o guardrail 1b bloqueou a pergunta com aderência 0,62, abaixo do limiar de 0,65, embora o New Mercadito esteja na base.

- Com o raciocínio alto ligado nos dois modos, o Modo B acertou os mesmos 6 casos, com p90 de 7,3 s e 3 de 10 respostas acima de 5 s ([experimento de 12/11](../experimentos/2026-11-12-comparativo-raciocinio.md)). O padrão continua sem raciocínio; `raciocinio="high"` em `executar_comparacao_ab` liga nos dois modos.

## Riscos e limitações

- **Custo e latência do Modo B sobem:** de cerca de 20 ms e custo zero (texto fixo) para cerca de 3 s e R$ 0,001 por pergunta. A latência fica dentro do RNF-14 na prévia, e o cache (RNF-15) evita pagar duas vezes no benchmark.
- **A recuperação léxica limita o Modo B.** Os erros da prévia são de recuperação. Melhorar a busca (filtro por RA, sinônimos, vetores) é trabalho à parte, e, se a escala da pontuação mudar, o limiar de 0,65 precisa ser medido de novo ([ADR 0010](0010-baseline-llm-pura-e-guardrails.md)).
- **Paralelismo:** os dois modos gravam o cache no mesmo arquivo. O `logger_metricas` ganhou uma trava para as escritas em disco não se perderem; ela vale dentro de um processo, não entre processos.
- **Langfuse:** um trace por comparação, com os dois modos dentro. O link (`trace_url`) só aparece quando há chaves do Langfuse; sem chaves, ele vem nulo, em vez de apontar para um trace que não existe.
- **Prévia pequena:** 10 casos e uma rodada. A medida oficial é a do benchmark da issue #38, com os 20 casos.

## Como vamos validar

- Benchmark da issue #38 com os 20 casos: latência p90 de cada modo contra os 5 s do RNF-14, taxa de alucinação e fidelidade (avaliador da issue #36) e acerto de RA e preço.
- Testes automáticos em `tests/test_comparador_ab.py` (16, sem rede): contrato das duas rotas, mesmo modelo e mesmos parâmetros nos dois modos, documentos só no Modo B, guardrail que impede a chamada ao LLM, reserva sem chave, cache e entradas inválidas.
