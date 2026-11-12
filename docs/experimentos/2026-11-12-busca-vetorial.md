# Busca do Modo B: por palavras × por embeddings × híbrida

- **Data:** 2026-11-12
- **Contexto:** a base tem vetores `gemini-embedding-001` (3.072 dimensões) desde a semana 2, mas a API buscava só por palavras (`calcular_similaridade_leticia`). Este experimento liga a busca vetorial e a híbrida no Modo B do comparativo ([ADR 0012](../decisoes/0012-busca-vetorial-pela-openrouter.md)) e mede o efeito.
- **Como reproduzir:**
  - busca, sem LLM: `PYTHONPATH=. python eval/calibrar_busca.py <saída.json>`
  - comparativo completo: `PYTHONPATH=. python eval/comparativo_ab.py <saída.json> desligado <lexica|vetorial|hibrida>`
- **Resultados completos:**
  - [calibração](../../eval/resultados/calibracao-busca-2026-11-12.json)
  - [busca por palavras](../../eval/resultados/comparativo-ab-previa-golden-01-10-2026-11-12.json)
  - [busca vetorial](../../eval/resultados/comparativo-ab-busca-vetorial-golden-01-10-2026-11-12.json)
  - [busca híbrida](../../eval/resultados/comparativo-ab-busca-hibrida-golden-01-10-2026-11-12.json)

## Antes de medir: os vetores da OpenRouter são os mesmos da base

Os vetores de 2 lugares da base foram gerados de novo pelo `google/gemini-embedding-001` da OpenRouter e comparados com os guardados: cosseno 1,0 nos dois. A pergunta pode, então, ser convertida em vetor pela mesma chave (`OPENROUTER_API_KEY`) que o projeto já usa, sem chave do Google. A chamada aceita o roteamento sem retenção (`zdr`, `data_collection: deny`). O filtro de quantização dos LLMs não vale para embeddings: com ele, a OpenRouter recusa a chamada.

## 1. A busca sozinha (sem LLM)

Posição do lugar do gabarito em cada busca, nos 8 casos do golden dentro do DF:

| Caso | Por palavras | Por embeddings | Híbrida |
|---|---|---|---|
| golden_01 | 2 | 1 | 1 |
| golden_02 | 1 | 1 | 1 |
| golden_03 | 1 | 1 | 1 |
| golden_04 | 3 | 1 | 1 |
| golden_05 | 11 | 1 | 5 |
| golden_06 | 9 | 5 | 3 |
| golden_07 | 4 | 1 | 2 |
| golden_08 | 3 | 2 | 2 |
| **Em 1º lugar** | 2 de 8 | 6 de 8 | 4 de 8 |
| **Entre os 3 primeiros** | 5 de 8 | 7 de 8 | 7 de 8 |

- A híbrida junta as duas ordens pela posição (Reciprocal Rank Fusion, `fundir_rankings`). Ela herda os erros da busca por palavras: no golden_05, o VBQ estava em 11º por palavras e caiu para 5º.
- **Limiar do guardrail 1b na escala do cosseno:**
  - as 8 perguntas fora do tema da base (oficina, boliche, museu, academia, dentista, loja de roupa, pet shop, curso de inglês) tiveram maior cosseno entre 0,574 e 0,624;
  - as do golden, entre 0,625 e 0,812;
  - limiar escolhido: **0,63** (`LIMIAR_COSSENO`).
  - A margem é pequena: o golden_06 (0,625) e o golden_08 (0,639) ficam perto da fronteira.
- **A busca por palavras deixa passar pedido fora do tema:** "loja de roupa de festa barata" teve 0,96 nela, acima do limiar de 0,65, e seria respondida com um lugar qualquer. Na vetorial, ela teve 0,62 e é recusada.

## 2. O comparativo completo (busca + LLM)

Mesmas 10 perguntas, raciocínio desligado, uma rodada por busca:

| | Por palavras | Por embeddings | Híbrida |
|---|---|---|---|
| Lugar do gabarito na resposta (8 casos do DF) | 6 de 8 | **7 de 8** | 6 de 8 |
| Latência do Modo B, p50 / p90 | 3,0 s / 4,8 s | 4,4 s / 6,1 s | 3,9 s / 5,6 s |
| Respostas do Modo B acima de 5 s | 0 de 10 | 2 de 10 | 3 de 10 |
| Tempo do embedding da pergunta (mediana) | — | 1,6 s | 1,5 s |

- **A busca vetorial acerta o golden_05:** o VBQ, de Samambaia, vem em 1º, e o modelo o recomenda com endereço, preço e horário da base.
- **O golden_06 continua errado nas três:** o New Mercadito fica longe do topo, e o guardrail recusa a pergunta (cosseno 0,625, logo abaixo do limiar).
- **O custo extra está na latência, não no preço:** o embedding custa menos de R$ 0,0001 por pergunta, mas acrescenta cerca de 1,6 s antes da chamada ao LLM. Com isso, o p90 do Modo B passa dos 5 s do RNF-14.

## Leitura

- **Para acertar, a busca vetorial é a melhor das três:** 7 de 8 lugares certos e a recusa correta de um pedido fora do tema que a busca por palavras deixava passar.
- **Para o RNF-14, ela não fecha ainda:** p90 de 6,1 s. Para manter a busca vetorial e voltar para menos de 5 s, há três opções a testar:
  - um modelo de embedding mais rápido (exige gerar de novo os 93 vetores com ele);
  - cache dos embeddings de perguntas frequentes;
  - medir de novo a latência da OpenRouter em outro horário.
- **A híbrida não compensa** nesta base: é tão lenta quanto a vetorial (precisa do embedding) e erra o que a busca por palavras erra.
- **O padrão do código continua sendo a busca por palavras** até o benchmark da issue #38, que escolhe pelo critério definido lá (p90 de até 5 s, nenhum lugar inventado, maior acerto).

## Limitações

- 10 perguntas, uma rodada: dá a direção, não números finais.
- O limiar de 0,63 foi escolhido com as mesmas perguntas em que é avaliado. As perguntas de 11 a 20 do golden (issue #32) servem para conferir se ele se mantém.
- **A base tem lugares repetidos**, que ocupam vagas nas fontes recuperadas:
  - o mesmo nome em mais de um registro: Espaguete, Dunkin' Donuts, Johnny Joy, Anime Summit e ExpoFlores 2026;
  - grafias diferentes do mesmo lugar: "Filomenambúrguer" e "Filomenamburger".

  Podem ser vídeos diferentes do mesmo lugar; fica para a curadoria da base.
