# 0012 — Busca vetorial do Modo B com o gemini-embedding-001 pela OpenRouter

- **Status:** proposta
- **Data:** 2026-11-12
- **Semana do roadmap:** 3 — Comparação RAG × LLM pura
- **Origem:** issue #38 (configuração 6: RAG com busca vetorial) e pedido do mentor de testar formas diferentes de usar o RAG
- **Requisitos:** RF-16, RNF-01, RNF-03, RNF-12, RNF-14

## Contexto

A base de 93 lugares tem vetores `gemini-embedding-001` (3.072 dimensões) desde a semana 2 (`data/banco_vetorial_embeddings.json`), mas a API buscava só por palavras. Para comparar a pergunta com esses vetores, ela precisa ser convertida em vetor pelo mesmo modelo. O grupo não tem chave do Google; tem a da OpenRouter.

## Opções consideradas

1. **API do Google com chave nova:** mais uma chave para distribuir, e sem o roteamento sem retenção que o grupo já usa.
2. **Gerar de novo os 93 vetores com um modelo local** (sentence-transformers): sem custo por chamada, mas com download de modelo, uma dependência pesada no servidor e vetores novos a validar.
3. **O mesmo `gemini-embedding-001` pela OpenRouter (escolhida):** mesma chave e mesmo modelo da base. Os vetores gerados de novo por ela deram cosseno 1,0 com os guardados.

## Decisão

- `src/rag/busca_vetorial.py` converte a pergunta em vetor pela OpenRouter, com o roteamento sem retenção (`zdr`, `data_collection: deny`), e calcula o cosseno com os 93 vetores em memória (numpy, sem banco vetorial).
  - O modelo pode ser trocado por `BUSCA_EMBEDDING_MODELO`, desde que os vetores da base sejam gerados de novo com ele.
  - Os vetores das perguntas ficam num cache em memória.
- `recuperar_com_guardrails(..., busca=...)` tem três modos:
  - **`lexica`:** a busca por palavras, que continua sendo o padrão;
  - **`vetorial`:** ordena pelo cosseno;
  - **`hibrida`:** junta as duas ordens pela posição (Reciprocal Rank Fusion).
- O guardrail 1b usa o limiar da escala de cada busca: 0,65 na busca por palavras e **0,63 no cosseno** (`LIMIAR_COSSENO`).
- Sem chave ou com a API de embeddings fora do ar, a busca volta para a de palavras, e `guardrails.busca_erro` diz por quê.
- O comparativo e a rota `/api/comparativo/executar` recebem `busca` (só o Modo B) e `raciocinio` (os dois modos). A tela `/comparativo` ganhou os dois seletores.

## Justificativa e evidências

Detalhes em [docs/experimentos/2026-11-12-busca-vetorial.md](../experimentos/2026-11-12-busca-vetorial.md) (10 casos do golden, 12/11).

| | Por palavras | Por embeddings | Híbrida |
|---|---|---|---|
| Lugar do gabarito entre os 3 primeiros (busca sozinha) | 5 de 8 | 7 de 8 | 7 de 8 |
| Lugar do gabarito na resposta do comparativo | 6 de 8 | 7 de 8 | 6 de 8 |
| Latência do Modo B, p90 | 4,8 s | 6,1 s | 5,6 s |

- **Calibração do limiar:** perguntas fora do tema tiveram maior cosseno entre 0,574 e 0,624; as do golden, entre 0,625 e 0,812.
- **A busca vetorial recusa um pedido fora do tema que a de palavras deixava passar:** "loja de roupa de festa barata" teve 0,96 na busca por palavras e 0,62 no cosseno.

## Riscos e limitações

- **Latência:** o embedding da pergunta leva cerca de 1,6 s e leva o p90 do Modo B a 6,1 s, acima dos 5 s do RNF-14. Por isso, a busca por palavras continua sendo o padrão até o benchmark da issue #38 escolher.
- **Limiar com margem pequena** (0,624 × 0,625), escolhido com as mesmas perguntas em que foi avaliado. Precisa ser conferido com os casos 11 a 20 do golden.
- **Privacidade:** a pergunta vai para o Google, pela OpenRouter, com roteamento sem retenção. As perguntas do benchmark não têm dados pessoais, e as salas não usam a busca vetorial (os 4 campos não vão para o embedding).
- **Lugares novos** precisam ter o vetor gerado com o mesmo modelo e o mesmo formato de texto (`documento_indexado`); senão, ficam fora da busca vetorial.
- **Lugares repetidos na base** (mesmo nome em mais de um registro) ocupam vagas entre as fontes recuperadas.

## Como vamos validar

- Benchmark da issue #38, com as 20 perguntas e as configurações de busca por palavras, vetorial e híbrida: acerto, alucinação (issue #36) e p90 de latência.
- Testes em `tests/test_busca_vetorial.py` (10, sem rede): vetor de um lugar como pergunta traz o próprio lugar, limiar do cosseno, volta para a busca por palavras sem chave ou com a API fora, pergunta fora do DF barrada antes do embedding, rota e tela.
