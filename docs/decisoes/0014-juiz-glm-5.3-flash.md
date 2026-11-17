# 0014 — Juiz do avaliador: GLM 5.3 Flash no lugar do MiMo-V2.6-Pro

- **Status:** aceita (Cauan, 17/11/2026)
- **Data:** 2026-11-17
- **Semana do roadmap:** 4 — o juiz passa a ser a base do agente de validação
- **Origem:** pedido do Cauan: o MiMo estava caro demais
- **Requisitos:** RNF-03, RNF-10, RNF-12, RNF-15

## Contexto

O avaliador híbrido da semana 3 (`src/telemetria/evals_semana3.py`, issue #36) confere em código os lugares, a RA e os preços citados (RNF-04) e pede a um juiz LLM que classifique cada afirmação como "confere com a base", "contradiz a base" ou "não está na base". O juiz era o `xiaomi/mimo-v2.6-pro`, de outra família que o DeepSeek V4.1 Flash avaliado, com temperatura 0, saída em JSON e o roteamento sem retenção do [ADR 0007](0007-interpretador-e-contrato-de-busca.md).

Na rodada 2 do benchmark da semana 3, o MiMo custou US$ 0,73 em 94 julgamentos (média de US$ 0,0078 por julgamento), mais de 50 vezes o custo da resposta do RAG que ele julgava (R$ 0,00081, ou US$ 0,00014, na configuração 4). Na semana 4, o juiz deve passar a validar cada sala (agente de validação), o que multiplica as chamadas.

## Opções consideradas

1. **Manter o MiMo e restringir o provedor:** com o roteamento do projeto (sem retenção e fp8 ou melhor), só a DeepInfra e o PrimaLabs servem o MiMo, e o `sort: latency` levou 63 de 94 chamadas ao PrimaLabs, 10 vezes mais caro. Fixar a DeepInfra baixaria o custo, mas deixaria o juiz com um provedor só (RNF-15).
2. **`xiaomi/mimo-v2.6-flash`:** mesma família, US$ 0,14 e US$ 0,28 por milhão no catálogo, mas não foi medido.
3. **`z-ai/glm-5.3-flash` (escolhida, pedido do Cauan):** outra família que o DeepSeek, com saída em JSON, e 8 provedores sem retenção em fp8 no roteamento do projeto, o mais caro a US$ 0,175 de entrada e US$ 0,49 de saída por milhão (catálogo público da OpenRouter, 17/11/2026).

## Decisão

- `MODELO_JUIZ_PADRAO = "z-ai/glm-5.3-flash"` em `src/telemetria/evals_semana3.py`. Prompt, temperatura, `response_format`, `max_tokens` e roteamento continuam iguais.
- `JUIZ_LLM_MODELO` no `.env` continua trocando o juiz sem mudar código (RNF-12); o `.env.example` passou a listar a variável.
- O benchmark da semana 3 continua registrado com o MiMo: os resultados, o log e o relatório não foram julgados de novo.

## Justificativa e evidências

Medido em 17/11 nas mesmas 94 respostas da rodada 2 da semana 3 ([experimento](../experimentos/2026-11-17-juiz-glm.md)):

| | MiMo-V2.6-Pro | GLM 5.3 Flash |
|---|---|---|
| Julgamentos sem falha | 94 de 94 | 94 de 94 |
| Custo das 94 chamadas | US$ 0,731 | US$ 0,057 |
| Latência p50 / p90 | 5,9 s / 18,8 s | 5,8 s / 10,1 s |
| Concordância sobre haver contradição | — | 90 de 94 |
| Concordância sobre fidelidade de 100% | — | 89 de 94 |

A ordem das 6 configurações e as conclusões da semana 3 não mudam.

## Riscos e limitações

- **O GLM é mais leniente no caso limite do golden_15** ("Sim, dá" com R$ 30, quando o lugar custa R$ 32,99): o MiMo marca contradição, o GLM não. Com o GLM, a única contradição do RAG apontada na semana 3 desaparece. Comparar números da semana 3 com os da semana 4 exige dizer qual juiz julgou cada um.
- **Um erro do GLM contra o prompt:** no golden_05, ele marcou como contradição uma resposta que só dizia não conhecer um lugar (regra 3 do prompt).
- **Concordância não é acerto:** não houve leitura humana das 94 respostas, e o GLM foi rodado uma vez só.
- **Roteamento por latência:** o mesmo `sort: latency` que encareceu o MiMo pode mandar o GLM ao provedor mais caro da lista. Hoje o pior caso é US$ 0,49 por milhão de saída; um teto de preço por provedor (`max_price` da OpenRouter) impediria surpresas se a lista de provedores mudar.
- **Privacidade:** o juiz recebe a pergunta, a resposta e os documentos da base, sem dado de participante. Se o agente de validação da semana 4 julgar textos das salas, o que vai ao juiz precisa seguir o RNF-02 (só restrições sem identificação).

## Como vamos validar

- `tests/test_evals_semana3.py` trava o modelo, a temperatura, o JSON e o roteamento sem retenção da chamada ao juiz.
- O benchmark da semana 4 registra o modelo do juiz em cada resultado (`modelo_juiz`), como na semana 3.
- Antes de usar o juiz em textos novos (explicações dos cartões, mensagens do mediador), conferir à mão uma amostra das contradições que ele apontar.
