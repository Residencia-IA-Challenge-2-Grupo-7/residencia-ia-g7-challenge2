# 0010 — Baseline LLM pura (DeepSeek V4.1 Flash) e guardrails determinísticos do RAG

- **Status:** proposta
- **Data:** 2026-11-10
- **Semana do roadmap:** 3 — Comparação RAG × LLM pura
- **Origem:** issue #33. Troca o modelo do Modo A pedido na issue (Gemini 1.5 Flash) a pedido do Cauan
- **Requisitos:** RNF-01, RNF-03, RNF-04, RNF-05, RNF-10, RNF-12, RNF-14, RNF-15

## Contexto

A entrega da semana 3 compara duas respostas para a mesma pergunta: **Modo A**, um LLM sem nenhum documento (zero-shot), e **Modo B**, o RAG sobre a base de 93 lugares. A issue #33 pedia o Gemini 1.5 Flash no Modo A e dois guardrails em código no Modo B: bloquear perguntas fora do DF ou com aderência abaixo de 0,65 e aplicar o teto em reais por filtro, nunca pelo modelo.

Pontos levantados ao implementar:

- O `.env` do grupo já tem a chave da OpenRouter, usada pelo interpretador (ADR 0007). Não tem chave do Gemini.
- A família Gemini 1.5 foi descontinuada pelo Google em 2025; um modelo fora do ar não serve de linha de base reproduzível.
- O Modo B que a API usa hoje (`simular_recuperacao_rag`) ordena os lugares por uma pontuação léxica (`calcular_similaridade_leticia`, de 0,20 a 0,98), não por cosseno de vetores. O limiar de 0,65 da issue passa a valer sobre essa pontuação.

## Opções consideradas

1. **Gemini 1.5 Flash, como na issue:** modelo descontinuado e sem chave no `.env`.
2. **Um Gemini atual pela API do Google:** exigiria uma chave nova e não tem o roteamento sem retenção que o grupo já usa.
3. **DeepSeek V4.1 Flash pela OpenRouter (escolhida):** mesmo modelo, mesma chave e mesmo roteamento do interpretador: só provedores sem retenção, sem coleta para treino e sem fp4. O modelo pode ser trocado por `LLM_PURA_MODELO` no `.env`.

## Decisão

- **Modo A** em `src/rag/llm_pura.py` (`gerar_resposta_llm_pura`):
  - DeepSeek V4.1 Flash, temperatura 0, sem raciocínio;
  - prompt de sistema com o mesmo formato pedido ao Modo B (nome, RA, endereço, preço em R$, horário) e a mesma regra de não inventar, mas sem documentos;
  - cache e registro de métricas da telemetria (RNF-10, RNF-15);
  - sem chave ou com a API fora do ar, devolve uma reserva determinística sem nenhum lugar (`disponivel: False`).
- **Guardrails do Modo B** em `src/rag/guardrails.py`, ligados em `simular_recuperacao_rag`:
  - **1a:** lugar fora do DF citado sem nenhuma RA do DF → nenhum lugar recomendado. Cobre Copacabana, Pinheiros, Goiânia e o Entorno;
  - **1b:** maior pontuação da recuperação abaixo de 0,65 → nenhum lugar recomendado;
  - **2:** teto em reais ou "grátis" → filtro `custo_medio_rs <= teto` em Python;
  - **2b:** "luxo" com teto abaixo de R$ 50 (o lugar "Caro ($$$)" mais barato da base) → aviso de conflito.
  - A resposta da API ganhou o campo `guardrails`, com o motivo e o teto aplicado.

## Justificativa e evidências

- Primeiras chamadas reais (10/11): de 3,0 a 4,6 s e cerca de US$ 0,00012 por pergunta (R$ 0,0007). As 20 perguntas do golden dataset custam menos de R$ 0,02.
- Com a regra de não inventar, o modelo:
  - deixou de afirmar endereço e horário que não conhecia e disse que não conhecia um rodízio de caldos com brinquedoteca em Águas Claras, que a base tem (Dona Cleide);
  - ainda citou duas hamburguerias em Taguatinga sem endereço.
  - Esses são os dois tipos de erro que a comparação vai contar: invenção e omissão.
- Limiar de 0,65, medido em 10/11 sobre a pontuação atual: perguntas fora do tema da base (oficina mecânica, boliche, museu) ficaram entre 0,50 e 0,56; pedidos que a base atende, entre 0,80 e 0,98.
- 25 testes em `tests/test_guardrails_e_baseline.py`, sem rede.

## Riscos e limitações

- **Comparação com outro modelo do que o planejado:** os resultados não valem para o Gemini. O relatório deve citar o modelo, a data e a versão do prompt (`VERSAO_PROMPT`).
- **A regra de não inventar no Modo A reduz a alucinação medida.** Ela foi mantida porque o Modo B tem a mesma regra; sem ela, a comparação mediria o prompt, e não a base.
- **Raciocínio do modelo:** o resultado do Modo A depende dele. Com raciocínio alto, numa prévia de 8 perguntas, o modelo deixou de afirmar endereços, mas não indicou nenhum lugar em 13 de 16 respostas, com p90 de 11,9 s e custo 3 vezes maior ([experimento de 10/11](../experimentos/2026-11-10-llm-pura-raciocinio.md)). Decidido em 10/11: o relatório mostra as duas, com a sem raciocínio como Modo A principal (mais útil, dentro do RNF-14 e mais barata), e a com raciocínio alto como comparação secundária.
- **Latência:** o p90 do Modo A pode passar dos 5 s do RNF-14. O cache evita repetir chamadas no benchmark, mas não na primeira execução.
- **Guardrail 1a por lista:** cidades fora da lista passam pelo escopo e dependem do limiar 1b. Nomes ambíguos (Paris 6, Natal, Santos) ficaram de fora de propósito.
- **Limiar sobre pontuação léxica:** se o Modo B passar a usar cosseno de vetores (issue #34), o 0,65 precisa ser medido de novo, porque as escalas não são comparáveis.
- **Privacidade:** a pergunta vai para a OpenRouter. As perguntas do benchmark não têm dados pessoais; no app, o Modo A não é usado com dados de participantes.

## Como vamos validar

- Na execução das 20 perguntas (issues #34 e #38): taxa de alucinação do Modo A × Modo B, acerto de preço e horário (RNF-03, meta de 95% no RAG) e acerto da RA.
- Guardrails: nenhuma recomendação para as perguntas de pegadinha fora do DF e 100% dos lugares dentro do teto quando há teto (testes automáticos).
- Latência p90 do Modo A medida no benchmark, comparada aos 5 s do RNF-14.
