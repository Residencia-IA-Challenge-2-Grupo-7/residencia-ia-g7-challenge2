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

## 1. Resumo Comparativo das 6 Configurações (Rodada 1 — 20 Consultas)

Os números abaixo correspondem à **Rodada 1** (`n = 20` consultas por configuração; a comparação completa entre Rodada 1 e Rodada 2 está na Seção 4). Na Configuração #3 (`3_rag_sem_llm_texto_fixo`), `tokens_total = 0` e `custo_estimado_brl = 0.0` porque não há chamada paga a nenhum LLM (os valores de `simular_recuperacao_rag` na telemetria da Semana 2 eram apenas estimativas).

| # | Configuração | Acerto (20) | Acerto DF (18) | Fidelidade (RNF-03) | Alucinação | Fora da Base | Lugares Inventados | Precisão RA | Recall@3 / MRR | Latência p50 / p90 | Acima de 5 s | Custo Médio |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | LLM pura, sem raciocínio | 2 de 20 (10%) | 0 de 18 | 0,0% | 3,0% | 97,0% | 32 (em 13 casos) | 0 de 15 (0%) | — | 3,75 s / 5,26 s | 3 de 20 | R\$ 0,00079 |
| 2 | LLM pura, raciocínio alto | 2 de 20 (10%) | 0 de 18 | 0,0% | 28,6% | 71,4% | 2 (em 1 caso) | 0 de 14 (0%) | — | 6,84 s / 14,58 s | 19 de 20 | R\$ 0,00198 |
| **3** | **RAG sem LLM (texto fixo semana 2) — Vencedora pelo critério** | **12 de 20 (60%)** | **10 de 18** | **99,2%** | **0,0%** | **0,8%** | **0 (em 0 casos)** | **13 de 16 (81,2%)** | **10 de 18 / 0,3704** | **0,02 s / 0,03 s** | **0 de 20** | **R\$ 0,00000** |
| 4 | RAG + LLM, busca léxica *(Decisão de produto com LLM)* | 12 de 20 (60%) | 10 de 18 | 98,7% | 0,0% | 1,4% | 0 (em 0 casos) | 13 de 16 (81,2%) | 10 de 18 / 0,3704 | 3,15 s / 3,61 s | 0 de 20 | R\$ 0,00081 |
| 5 | RAG + LLM, busca léxica, raciocínio alto | 12 de 20 (60%) | 10 de 18 | 100,0% | 0,0% | 0,0% | 0 (em 0 casos) | 13 de 16 (81,2%) | 10 de 18 / 0,3704 | 4,51 s / 6,88 s | 7 de 20 | R\$ 0,00121 |
| 6 | RAG + LLM, busca vetorial | **18 de 20 (90%)** | **16 de 18** | **96,8%** | **0,7%** | **2,5%** | **0 (em 0 casos)** | **16 de 17 (94,1%)** | **16 de 18 / 0,8333** | 5,10 s / 5,83 s | 11 de 20 | R\$ 0,00092 |

## 2. Escolha da Configuração Vencedora vs. Decisão de Produto

1. **Vencedora pelo critério estrito da Issue #38** (*"Entre as configurações com p90 de até 5 s (RNF-14) e nenhum lugar inventado, a de maior acerto do lugar do gabarito; no empate, a mais barata"*):
   - **#3 — RAG sem LLM (`3_rag_sem_llm_texto_fixo`)**.
   - As configurações **#3** e **#4** são as duas únicas que atendem simultaneamente ao SLA de latência RNF-14 (`p90 <= 5 s`: `0,03 s` na #3 e `3,61 s` na #4) e a `0 lugares inventados`. Ambas empatam em acerto do gabarito (**12 de 20** no geral e **10 de 18** nos casos do DF, pois compartilham a mesma busca léxica com `Recall@3 = 10 de 18`). No critério de desempate pelo menor custo, vence a **#3** por ter **custo real zero (`R$ 0,00000` e `0` tokens)** contra `R$ 0,000807` por consulta na #4.
2. **Decisão de produto à parte do critério (quando há síntese em linguagem natural):**
   - Para a experiência conversacional do assistente (que precisa redigir respostas naturais, explicar por que um local recuperado atende apenas parcialmente a restrições como horário ou prato, e contextualizar recusas sem exibir um template engessado), a escolha prática entre as configurações com LLM que respeitam o RNF-14 é a **#4 — RAG + LLM, busca léxica (`4_rag_llm_busca_lexica`)**, com **98,7% de fidelidade factual**, **0,0% de alucinação na Rodada 1** e **p90 de 3,61 s** (`20 de 20` consultas dentro de 5 s).
   - **Achado central para o relatório (#40):** com a busca por palavras (léxica), adicionar o LLM (#4 e #5) **não aumentou o acerto do gabarito** em relação ao texto fixo (#3) — todas cravam os mesmos **12 de 20** (`10 de 18` no DF) — porque **quem limita o acerto é a etapa de recuperação (`Recall@3 = 10 de 18`)**. Quando a busca muda para vetorial (#6), o `Recall@3` salta para **16 de 18 (88,9%)** e o acerto sobe para **18 de 20 (90,0%)**.

## 3. Consolidação por Categoria (RNF-10 — Rodada 1)

Com o ajuste do avaliador híbrido (`src/telemetria/evals_semana3.py`) para que o juiz no Modo B receba apenas os documentos que o modo efetivamente recebeu (`fontes_utilizadas`) e marque `"contradiz a base"` exclusivamente quando um fato sobre um lugar divergir do documento desse mesmo lugar, **todas as 4 configurações RAG (#3 a #6) superam a meta de 95% de fidelidade factual (RNF-03)**:

| Categoria | Casos | Acerto Modo A (Cfg 1) | Acerto Cfg 3 (Sem LLM) | Acerto Cfg 4 (Léxica + LLM) | Acerto Cfg 6 (Vetorial + LLM) | Fidelidade Cfg 3 | Fidelidade Cfg 4 | Fidelidade Cfg 6 |
|---|---|---|---|---|---|---|---|---|
| `geoespacial_ra_fora_centro` | 5 | 0 de 5 | 4 de 5 | 4 de 5 | **5 de 5** | **100,0%** | **95,7%** | **95,5%** |
| `janela_horario` | 3 | 0 de 3 | 2 de 3 | 2 de 3 | 2 de 3 | **100,0%** | **100,0%** | **100,0%** |
| `fora_de_escopo_df` | 2 | 2 de 2 | 2 de 2 | 2 de 2 | 2 de 2 | — (recusa correta) | — (recusa correta) | — (recusa correta) |
| `precisao_financeira` | 5 | 0 de 5 | 3 de 5 | 3 de 5 | **5 de 5** | **96,9%** | **100,0%** | **96,0%** |
| `vibes_e_restricoes` | 3 | 0 de 3 | 1 de 3 | 1 de 3 | **3 de 3** | **100,0%** | **100,0%** | **95,8%** |
| `conflito_e_girias` | 2 | 0 de 2 | 0 de 2 | 0 de 2 | 1 de 2 | **100,0%** | **100,0%** | **100,0%** |

## 4. Variação Entre as Duas Rodadas (Rodada 1 × Rodada 2)

As duas rodadas foram executadas sem cache (`usar_cache=False`) para medir a estabilidade do gerador e do juiz. O texto completo das respostas da Rodada 2 também está salvo em `resultados_configuracoes[<cfg>]["rodada_2"]["resposta"]` em `data/resultados_benchmark_semana3.json`.

| # | Configuração | Acerto R1 × R2 | Fidelidade R1 × R2 | Alucinação R1 × R2 | Latência p50 R1 × R2 | Latência p90 R1 × R2 | Casos com mudança na nota do juiz |
|---|---|---|---|---|---|---|---|
| 1 | LLM pura, sem raciocínio | 2/20 × 2/20 | 0,0% × 0,0% | 3,0% × 7,9% | 3,75 s × 3,85 s | 5,26 s × 4,83 s | 7 de 20 (`golden_01, 04, 07, 08, 13, 15, 16`) |
| 2 | LLM pura, raciocínio alto | 2/20 × 2/20 | 0,0% × 3,6% | 28,6% × 25,0% | 6,84 s × 7,38 s | 14,58 s × 18,12 s | 4 de 20 (`golden_06, 12, 14, 16`) |
| 3 | RAG sem LLM (texto fixo) | 12/20 × 12/20 | 99,2% × 99,2% | 0,0% × 0,0% | 0,02 s × 0,02 s | 0,03 s × 0,04 s | 0 de 20 (determinístico) |
| 4 | RAG + LLM, busca léxica | 12/20 × 12/20 | 98,7% × 99,1% | 0,0% × 0,9% | 3,15 s × 2,82 s | 3,61 s × 3,90 s | 3 de 20 (`golden_02, 05, 15`) |
| 5 | RAG + LLM, léxica + raciocínio alto | 12/20 × 12/20 | 100,0% × 100,0% | 0,0% × 0,0% | 4,51 s × 5,13 s | 6,88 s × 8,23 s | 0 de 20 |
| 6 | RAG + LLM, busca vetorial | 18/20 × 18/20 | 96,8% × 97,7% | 0,7% × 0,8% | 5,10 s × 4,79 s | 5,83 s × 5,35 s | 3 de 20 (`golden_05, 14, 15`) |

- **Estabilidade do acerto:** em todas as 6 configurações, o `acerto_gabarito` foi **idêntico nas duas rodadas** (`2/20` nas configurações #1 e #2; `12/20` nas configurações #3, #4 e #5; `18/20` na configuração #6).
- **Variação das notas do juiz:** no Modo B com LLM (#4, #5 e #6), a nota do juiz variou em apenas **0 a 3 casos de 20** (diferenças de no máximo 0,9 p.p. na média), sempre por pequenas variações de redação na forma como o gerador mencionou detalhes secundários.

## 5. Auditoria Manual das Contradições Restantes (Item por Item)

Após o rejulgamento das 120 respostas da Rodada 1 (e 120 da Rodada 2) com o juiz corrigido, todas as contradições remanescentes foram inspecionadas manualmente:

1. **Configurações RAG (#3, #4, #5 e #6):**
   - **#3 (`3_rag_sem_llm_texto_fixo`):** **0 contradições** em 20 casos (Rodada 1 e Rodada 2: `0,0%` de alucinação).
   - **#4 (`4_rag_llm_busca_lexica`):** **0 contradições na Rodada 1** (`0,0%` de alucinação em 20 de 20 casos). Na **Rodada 2**, houve **1 única contradição** (`golden_15`, 1 de 7 afirmações = `14,3%` no caso, `0,9%` na média).
   - **#5 (`5_rag_llm_busca_lexica_raciocinio_alto`):** **0 contradições** em 20 casos (Rodada 1 e Rodada 2: `0,0%` de alucinação, `100,0%` de fidelidade).
   - **#6 (`6_rag_llm_busca_vetorial`):** **1 única contradição** na Rodada 1 (`golden_15`, 1 de 8 afirmações = `12,5%` no caso, `0,7%` na média) e a mesma **1 contradição** na Rodada 2 (`golden_15`).
   - **Por que ocorreu a contradição de `golden_15` (#6 R1/R2 e #4 R2):** a pergunta impõe `"Tenho só R$ 30, nem um centavo a mais. Dá para almoçar no buffet à vontade com tempero nordestino em Vicente Pires numa terça-feira?"`. No documento recuperado do **Restaurante do Daniel**, o texto da descrição menciona *"opções a partir de R$ 29,99"*, enquanto o campo estruturado `Preço médio por pessoa` é **`R$ 32,99`**. O modelo respondeu `"Sim, dá."` na primeira frase e logo em seguida ressalvou `"O preço médio por pessoa é R$ 32,99 (que passa de R$ 30,00)"`. O juiz marcou apenas a afirmação inicial (`"Sim, dá."`) como contradição contra o preço médio estruturado (`R$ 32,99 > R$ 30,00`). Nenhum dado foi inventado fora do documento.
2. **Configurações LLM Pura (#1 e #2):**
   - **#1 (`1_llm_pura_sem_raciocinio`):** além de **97,0% de afirmações fora da base** (32 lugares inventados em 13 de 20 casos), teve contradições em 3 casos na Rodada 1: `golden_07` (afirmou que buffet abaixo de R\$ 30 em Taguatinga está fora da realidade, desmentido pelo Casa Bar a R\$ 29,99), `golden_16` (negou existência de doceria sem trigo/lactose/açúcar em Brasília, desmentido pela Lefit) e `golden_19` (citou rodízios de R\$ 90–180 sem local da base).
   - **#2 (`2_llm_pura_raciocinio_alto`):** em `golden_07`, `golden_14`, `golden_15` e `golden_20`, recusou-se a indicar locais mas repetiu o valor em reais da pergunta (`R$ 30`) sem usar a frase-padrão de abstenção, acionando a trava determinística de preço sem local da base (`preco_contradiz`).
