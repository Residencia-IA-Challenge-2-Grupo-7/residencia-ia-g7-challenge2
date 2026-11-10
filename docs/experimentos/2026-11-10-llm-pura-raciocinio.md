# LLM pura (Modo A): sem raciocínio × raciocínio alto

- **Data:** 2026-11-10
- **Contexto:** issue #33 e [ADR 0010](../decisoes/0010-baseline-llm-pura-e-guardrails.md). O Modo A da comparação da semana 3 é o DeepSeek V4.1 Flash pela OpenRouter, zero-shot. A dúvida: ligar o raciocínio do modelo muda o que ele responde?
- **Como reproduzir:** `PYTHONPATH=. python eval/llm_pura_raciocinio.py <saída.json>`. Respostas completas em [eval/resultados/llm-pura-raciocinio-deepseek-v4.1-flash-2026-11-10.json](../../eval/resultados/llm-pura-raciocinio-deepseek-v4.1-flash-2026-11-10.json).

## O que foi medido

- **Perguntas:** 8 perguntas sobre o DF, de tipos diferentes:
  - um pedido que a base atende (rodízio de caldos com brinquedoteca em Águas Claras, que a base tem: Dona Cleide);
  - pedidos com preço, horário e RA fora do centro;
  - duas pegadinhas (Copacabana; restaurante de luxo grátis).
- **Modos:**
  - **desligado:** `reasoning.enabled = false`, limite de 700 tokens;
  - **high:** `reasoning.effort = "high"`, sem o "xhigh", limite de 8.000 tokens, porque o raciocínio conta no limite.
- **Execução:** duas rodadas, com a ordem dos modos alternada, temperatura 0 e o mesmo prompt de sistema, que inclui a regra de não inventar. Total de 32 chamadas, todas com resposta.

## Resultados

| | Sem raciocínio | Raciocínio alto |
|---|---|---|
| Latência p50 / p90 / máx. | 3,1 s / 3,7 s / 3,9 s | 7,0 s / 11,9 s / 12,7 s |
| Respostas acima dos 5 s do RNF-14 | 0 de 16 | 12 de 16 |
| Tokens de raciocínio (média) | 0 | 506 |
| Tokens de saída (média) | 202 | 670 |
| Custo por pergunta | R$ 0,00075 | R$ 0,00232 (3,1×) |
| Respostas sem nenhum lugar nomeado | 3 de 16 | 13 de 16 |
| Lugares nomeados (aprox.) | cerca de 25 | 6 |
| Lugares com endereço afirmado (quadra, bloco, loja) | 6 | 0 |
| Lugares com horário afirmado | 3 | 1 |
| Lugares citados que estão na base de 93 | 0 | 0 |

A contagem de lugares é automática (nomes em negrito na resposta), com ruído de itens genéricos; a leitura das respostas da rodada 1 confirma o padrão.

**Exemplos (rodada 1):**
- **"café calmo na Asa Norte":** sem raciocínio, o modelo deu 3 cafés com quadra, bloco, loja, faixa de preço e horário de funcionamento, tudo afirmado. Com raciocínio alto, recusou-se a indicar e sugeriu procurar no Google Maps.
- **"domingo cedo no Plano Piloto":**
  - sem raciocínio: 3 padarias com endereço completo, marcando só o horário de domingo como "não sei";
  - com raciocínio alto: 3 nomes com "endereço: não sei".
- **"rodízio de caldos com brinquedoteca em Águas Claras":** nos dois modos, o modelo não achou o lugar que a base tem. Sem raciocínio, ainda sugeriu dois restaurantes sem relação com o pedido.
- **Pegadinhas:** os dois modos acertaram que Copacabana está fora do DF e que não existe restaurante de luxo grátis. Sem raciocínio, o modelo ainda citou dois restaurantes de luxo pelo nome.

## Impactos

- **O raciocínio alto troca invenção por recusa.** Ele quase zera os endereços e horários afirmados, mas também quase zera a utilidade: em 13 de 16 respostas, nenhum lugar é indicado. Na métrica de alucinação, ele parece melhor; na de cobertura (achar o lugar certo), os dois modos ficam em 0, e o RAG continua sendo a única via de chegar à base.
- **O raciocínio alto descumpre o RNF-14:** 12 de 16 respostas passaram de 5 s, com p90 de 11,9 s, e o custo triplica. Sem raciocínio, todas ficaram abaixo de 4 s.
- **Para a comparação da semana 3:**
  - **sem raciocínio:** a linha de base representa o uso comum de um LLM rápido, o que dá mais casos de invenção para auditar;
  - **raciocínio alto:** representa um LLM "cauteloso".
  - Relatar só um dos dois esconde que a taxa de alucinação do Modo A depende muito dessa configuração.
- **Decidido em 10/11:** o relatório mostra as duas configurações, com a **sem raciocínio como Modo A principal**. O padrão do código continua sem raciocínio (`LLM_PURA_RACIOCINIO` no `.env` ou o parâmetro `raciocinio="high"` trocam isso).

## Texto para o entregável da semana 3

> Para a linha de base sem RAG (Modo A), usamos o DeepSeek V4.1 Flash pela OpenRouter, sem acesso à base de 93 lugares, em duas configurações: sem raciocínio e com raciocínio alto. A principal é a **sem raciocínio**, que teve os melhores resultados de uso: respondeu todas as 16 chamadas em até 3,9 s (p90 de 3,7 s, dentro dos 5 s do RNF-14), custou R$ 0,00075 por pergunta e indicou lugares em 13 de 16 respostas. É também a configuração que mais se parece com o uso comum de um assistente rápido, o que torna a comparação com o RAG representativa.
>
> A configuração com raciocínio alto foi pior por três motivos. Primeiro, ficou lenta: p90 de 11,9 s, com 12 de 16 respostas acima do limite de 5 s. Segundo, custou cerca de 3 vezes mais (R$ 0,00232 por pergunta), por gastar em média 506 tokens raciocinando. Terceiro, e principal, ela evitou inventar endereços (0 afirmados, contra 6 sem raciocínio) recusando-se a responder: em 13 de 16 respostas, não indicou nenhum lugar. Ela não sabe mais sobre o DF, só arrisca menos. Nenhuma das duas citou um único lugar da base, nem mesmo o único rodízio de caldos com brinquedoteca de Águas Claras, que a base tem. Isso mostra que, sem recuperação, o modelo erra por invenção (sem raciocínio) ou por omissão (com raciocínio alto).

## Limitações

- 8 perguntas e 2 rodadas: serve para ver a direção, não para dar números finais. As 20 perguntas do golden dataset (issues #31 e #32) vão dar a medida oficial.
- A verificação dos lugares foi contra a base de 93, não contra o mundo: um lugar que não está na base pode existir. Saber se cada nome, endereço e horário existe de fato é a auditoria manual da issue #38.
- Um único provedor por chamada (escolhido pela OpenRouter, sem retenção); a latência varia com o provedor.
