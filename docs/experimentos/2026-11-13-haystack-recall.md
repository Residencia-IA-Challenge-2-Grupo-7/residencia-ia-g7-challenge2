# Haystack: recall@3 do retriever BM25 (PR #60)

**Data:** 13/11/2026 · **Script:** `PYTHONPATH=. python scripts/medir_recall_haystack.py` (sem LLM e sem rede) · **Casos:** os 18 do golden com lugar no gabarito (os 2 fora do DF não têm lugar).

| Versão do pipeline | Lugar certo entre os 3 primeiros |
|---|---|
| Antes: campos que a base não tem (`descricao`, `resumo_experiencia`, `faixa_preco_estimada_reais`) | 2 de 18 |
| Depois: nome, tipo, RA, vibes e `resumo_sensorial` no conteúdo; preço por `custo_medio_rs` | **14 de 18 (77,8%)** |

Erros que restam: golden_06, golden_11, golden_14 e golden_17. O Haystack aqui só troca o framework: o BM25 é o mesmo tipo de busca por palavras do Modo B, então o resultado não diz nada sobre o framework em si.
Teste que trava o número: `tests/test_pipeline_haystack.py::test_recall_at_3_do_haystack_no_golden`.
