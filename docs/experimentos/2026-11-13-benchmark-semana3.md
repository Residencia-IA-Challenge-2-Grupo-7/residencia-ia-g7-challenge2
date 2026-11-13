# Benchmark Oficial da Semana 3: 20 Consultas × 6 Configurações (LLM Pura vs. RAG 2FA)

- **Data:** 2026-11-13
- **Contexto:** issue #38, [ADR 0010](../decisoes/0010-baseline-llm-pura-e-guardrails.md), [ADR 0011](../decisoes/0011-comparativo-ab-com-o-mesmo-llm.md) e [ADR 0012](../decisoes/0012-busca-vetorial-pela-openrouter.md). Execução oficial nas 20 perguntas do Golden Dataset (`data/golden_dataset_semana3.json`, issues #31 e #32) avaliadas pelo motor híbrido da issue #36 (`src/telemetria/evals_semana3.py`: verificação determinística RNF-04 + juiz `xiaomi/mimo-v2.6-pro`).
- **Como reproduzir:**
  - `PYTHONPATH=. python scripts/executar_benchmark_semana3.py`
  - validação automatizada: `PYTHONPATH=. pytest -v tests/test_resultados_benchmark.py`
- **Artefatos gerados:**
  - [data/resultados_benchmark_semana3.json](../../data/resultados_benchmark_semana3.json)
  - [data/resultados_benchmark_semana3.csv](../../data/resultados_benchmark_semana3.csv)
  - [docs/entregas/semana-03/BENCHMARK_LLM_VS_RAG_LOG.txt](../entregas/semana-03/BENCHMARK_LLM_VS_RAG_LOG.txt)

## 1. Resumo Comparativo das 6 Configurações (20 Consultas)

| # | Configuração | Acerto (20) | Acerto DF (18) | Fidelidade (RNF-03) | Alucinação | Lugares Inventados | Precisão RA | Recall@3 / MRR | Latência p50 / p90 | Acima de 5 s | Custo Médio |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | LLM pura, sem raciocínio | 2 de 20 (10%) | 0 de 18 | 0,0% | 3,0% (97,0% fora da base) | 32 (em 13 casos) | 0 de 15 (0%) | — | 3,75 s / 5,26 s | 3 de 20 | R\$ 0,00079 |
| 2 | LLM pura, raciocínio alto | 2 de 20 (10%) | 0 de 18 | 0,0% | 28,6% (71,4% fora da base) | 2 (em 1 caso) | 0 de 14 (0%) | — | 6,84 s / 14,58 s | 19 de 20 | R\$ 0,00198 |
| 3 | RAG sem LLM (texto fixo semana 2) | 12 de 20 (60%) | 10 de 18 | 84,4% | 13,9% | 0 (em 0 casos) | 13 de 16 (81,2%) | 10 de 18 / 0,3704 | 0,02 s / 0,03 s | 0 de 20 | R\$ 0,00087 |
| **4** | **RAG + LLM, busca léxica (Vencedora)** | **12 de 20 (60%)** | **10 de 18** | **88,8%** | **10,6%** | **0 (em 0 casos)** | **13 de 16 (81,2%)** | **10 de 18 / 0,3704** | **3,15 s / 3,61 s** | **0 de 20** | **R\$ 0,00081** |
| 5 | RAG + LLM, busca léxica, raciocínio alto | 12 de 20 (60%) | 10 de 18 | 83,5% | 16,5% | 0 (em 0 casos) | 13 de 16 (81,2%) | 10 de 18 / 0,3704 | 4,51 s / 6,88 s | 7 de 20 | R\$ 0,00121 |
| 6 | RAG + LLM, busca vetorial | **18 de 20 (90%)** | **16 de 18** | **91,0%** | **7,2%** | **0 (em 0 casos)** | **16 de 17 (94,1%)** | **16 de 18 / 0,8333** | 5,10 s / 5,83 s | 11 de 20 | R\$ 0,00092 |

## 2. Escolha da Configuração Vencedora

Pelo critério definido antes da execução na issue #38 (*"Entre as configurações com p90 de até 5 s (RNF-14) e nenhum lugar inventado, a de maior acerto do lugar do gabarito; no empate, a mais barata"*):

- **Configuração eleita:** **#4 — RAG + LLM, busca léxica (`4_rag_llm_busca_lexica`)**.
  - Cumpre 100% do SLA de latência RNF-14: **p50 de 3,15 s e p90 de 3,61 s** (**20 de 20 respostas abaixo de 5 s**).
  - **Zero lugares inventados** nas 20 consultas (contra 32 estabelecimentos inventados na LLM pura sem raciocínio).
  - **Fidelidade factual média de 88,8%** (atingindo **96,5%** na categoria `geoespacial_ra_fora_centro` e **95,0%** em `janela_horario`).
  - Supera a configuração #3 (texto fixo sem LLM) em fidelidade factual (+4,4 p.p.), redução de contradições (-3,3 p.p.) e menor custo médio por consulta (R\$ 0,000807 vs. R\$ 0,000872).

## 3. Consolidação por Categoria (RNF-10)

| Categoria | Casos | Acerto Modo A (Cfg 1) | Acerto Modo B Léxica (Cfg 4) | Acerto Modo B Vetorial (Cfg 6) | Fidelidade Cfg 4 | Fidelidade Cfg 6 |
|---|---|---|---|---|---|---|
| `geoespacial_ra_fora_centro` | 5 | 0 de 5 | 4 de 5 | **5 de 5** | **96,5%** | **100,0%** |
| `janela_horario` | 3 | 0 de 3 | 2 de 3 | 2 de 3 | **95,0%** | **95,0%** |
| `fora_de_escopo_df` | 2 | 2 de 2 | 2 de 2 | 2 de 2 | — (recusa correta) | — (recusa correta) |
| `precisao_financeira` | 5 | 0 de 5 | 3 de 5 | **5 de 5** | 88,0% | 84,8% |
| `vibes_e_restricoes` | 3 | 0 de 3 | 1 de 3 | **3 de 3** | 83,3% | **94,4%** |
| `conflito_e_girias` | 2 | 0 de 2 | 0 de 2 | 1 de 2 | 50,0% | 75,0% |

## 4. Principais Conclusões para o Produto e Relatório

1. **A LLM pura (Modo A) é inviável para recomendação factual local no DF:** acertou **0 de 18** lugares do gabarito dentro do DF nas duas configurações (sem e com raciocínio) e inventou **32 estabelecimentos/quadras inexistentes** sem raciocínio.
2. **O gargalo do Modo B léxico está na recuperação, não na geração:** a busca léxica recupera o lugar do gabarito no Top-3 em **10 de 18** casos do DF, e o LLM acerta todos os 10 casos em que o documento veio no Top-3.
3. **A busca vetorial (`gemini-embedding-001`, Configuração #6) eleva o acerto de 12/20 para 18/20 (90%) e o Recall@3 para 16/18 (88,9%):** os dois únicos casos não recuperados no DF são `golden_06` (bloqueado pelo limiar de cosseno 0,625 < 0,63) e `golden_19` (bloqueado pelo guardrail de "totalmente de graça"). O único motivo pelo qual a busca vetorial não vence pelo filtro automático do RNF-14 é o tempo da chamada HTTP de embedding na OpenRouter (~1,5 s), que leva o p90 a 5,83 s. Com cache de embeddings ou geração local do vetor da pergunta, o p90 cai para ~4,2 s e a Configuração #6 passa a atender simultaneamente RNF-03 e RNF-14.
