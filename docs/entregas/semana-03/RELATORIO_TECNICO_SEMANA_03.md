# Relatório Técnico da Semana 3: Comparação entre LLM pura e RAG

**Instituto de Pesquisas Eldorado · Universidade de Brasília · Residência em Inteligência Artificial — Brasília**
**Grupo 07 — Orquestrador de Rolês (Distrito Federal)**
Letícia Miti Takahashi, Maria Eduarda, Maria Carolina, Cauan Soares e Samara Letícia
Challenge 2, Semana 3 — Brasília, novembro de 2026

- Comparação interativa (as duas respostas lado a lado): <https://orquestrador-roles.onrender.com/comparativo>
- Central de Entregáveis: <https://orquestrador-roles.onrender.com/entregaveis>

---

## 1. Resumo e desenho experimental

O entregável da Semana 3 pede respostas baseadas em evidências: mostrar, com medição, se o RAG construído na Semana 2 responde melhor do que um modelo de linguagem sozinho. Testamos seis configurações nas 20 perguntas do golden dataset, cada uma rodada duas vezes, com as respostas avaliadas por código e por um segundo modelo que atua como juiz.

**Resultado principal.** A LLM pura não acertou o lugar do gabarito em nenhuma das 18 perguntas sobre o DF (0 de 18). O RAG com a busca por palavras acertou 10 de 18, e com a busca por embeddings, 16 de 18. Nas configurações com RAG, a fidelidade à base ficou entre 96,8% e 100%, acima da meta de 95% do RNF-03.

**Achado que orienta a próxima semana.** Com a busca por palavras, colocar o LLM depois da busca não aumentou o acerto: o texto fixo da Semana 2 e o RAG com LLM acertaram os mesmos 12 de 20. Quem limita o acerto é a recuperação: o lugar certo só chega entre os 3 documentos em 10 de 18 perguntas. Com a busca por embeddings, isso sobe para 16 de 18, mas a latência passa do limite de 5 s do RNF-14.

**Mesmo modelo nos dois modos.** O Modo A (LLM pura) e o Modo B (RAG) usam o mesmo modelo, o DeepSeek V4.1 Flash (`deepseek/deepseek-v4.1-flash-1017`, pela OpenRouter), com temperatura 0, o mesmo limite de palavras e a mesma instrução de não inventar. A única diferença é que o Modo B recebe até 3 lugares da base como `[FONTE #n]` e precisa citá-los. Assim, a diferença entre os modos mede a base, e não o modelo nem o prompt ([ADR 0011](../../decisoes/0011-comparativo-ab-com-o-mesmo-llm.md)).

**Por que não o Gemini 1.5 Flash.** O plano inicial previa o Gemini 1.5 Flash, que foi descontinuado e para o qual o grupo não tinha chave. O DeepSeek V4.1 Flash custa cerca de R$ 0,0008 por pergunta, responde em 3 a 4 s e permite ligar o raciocínio, o que virou uma das configurações testadas ([ADR 0010](../../decisoes/0010-baseline-llm-pura-e-guardrails.md)). As chamadas usam o roteamento sem retenção de dados da OpenRouter (`zdr`, `data_collection: deny`).

## 2. Golden dataset

O golden dataset (`data/golden_dataset_semana3.json`) tem 20 perguntas escritas como um usuário faria, cada uma com um gabarito copiado da base de 93 lugares validados em dois fatores: nome, região administrativa (RA), preço médio e horário, além do vídeo do TikTok que serve de evidência ([catálogo e regras](../../dados/golden-dataset-semana3.md)).

| Categoria | Casos | O que testa |
|---|---|---|
| `geoespacial_ra_fora_centro` | 5 | Lugares reais fora do Plano Piloto (RNF-13) |
| `janela_horario` | 3 | Horário real (madrugada depois da 1h, domingo) |
| `fora_de_escopo_df` | 2 | Recusar perguntas sobre outras cidades |
| `precisao_financeira` | 5 | Preço exato e teto estrito em reais (RNF-03) |
| `vibes_e_restricoes` | 3 | Ambiente e restrição alimentar descritos só no vídeo |
| `conflito_e_girias` | 2 | Pedido que parece impossível e pergunta em candanguês (RNF-08) |

- **Uma resposta certa por pergunta.** Cada pergunta é específica o bastante para ter um único lugar certo na base: são 18 lugares diferentes para as 18 perguntas do DF.
- **Gabarito travado por teste.** `tests/test_golden_dataset.py`, que roda no CI, confere que nome, RA e preço do gabarito são iguais aos da base e que as 6 categorias têm a distribuição acima.
- **Armadilha registrada.** Cada caso anota o erro que esperamos da LLM pura, por exemplo "sugerir hamburguerias do Plano Piloto" para uma pergunta sobre Taguatinga.

## 3. Configurações testadas

| # | Configuração | Como funciona |
|---|---|---|
| 1 | LLM pura, sem raciocínio | Modo A: o modelo responde só com o que sabe |
| 2 | LLM pura, raciocínio alto | Modo A com `reasoning.effort = "high"` |
| 3 | RAG sem LLM | Busca por palavras e o texto fixo da Semana 2, preenchido com o 1º lugar |
| 4 | RAG + LLM, busca por palavras | Modo B: busca por palavras e o modelo redige a resposta com as fontes |
| 5 | RAG + LLM, busca por palavras, raciocínio alto | Configuração 4 com o raciocínio alto |
| 6 | RAG + LLM, busca por embeddings | Configuração 4 com a busca vetorial (`google/gemini-embedding-001`) |

As três configurações com LLM e RAG compartilham os mesmos ajustes da busca e os mesmos guardrails, que vêm antes do modelo e são escritos em Python:

- **3 documentos por pergunta.** O modelo recebe no máximo 3 lugares, com nome, tipo, RA, endereço, horário, faixa e preço médio e descrição.
- **Limiar de aderência.** Se a maior pontuação da busca fica abaixo do limiar, nenhum lugar é recomendado e o modelo nem é chamado. O limiar é 0,65 na busca por palavras e 0,63 no cosseno da busca vetorial. Os dois foram calibrados com perguntas fora do tema da base:
  - na busca por palavras, as perguntas fora do tema ficaram entre 0,50 e 0,56;
  - no cosseno, ficaram entre 0,574 e 0,624, e as perguntas do golden, entre 0,625 e 0,812 ([ADR 0012](../../decisoes/0012-busca-vetorial-pela-openrouter.md)).
- **Escopo do DF.** Perguntas que citam um lugar fora do DF, sem nenhuma RA, são recusadas antes da busca.
- **Teto em reais.** Quando a pergunta tem teto ou pede algo grátis, os lugares acima do teto são retirados em Python, antes de chegar ao modelo.

A busca híbrida (palavras e embeddings juntos, por Reciprocal Rank Fusion) foi medida na prévia de 12/11 e ficou de fora do benchmark, porque não superou a vetorial no acerto (6 de 8 contra 7 de 8) ([experimento](../../experimentos/2026-11-12-busca-vetorial.md)). Como teste de ferramenta, também montamos a busca por palavras no framework Haystack (BM25): ela traz o lugar certo entre os 3 primeiros em 14 de 18 perguntas. É o mesmo tipo de busca, então o resultado não diz nada sobre o framework em si ([experimento](../../experimentos/2026-11-13-haystack-recall.md)).

## 4. Como as respostas foram avaliadas

O avaliador (`src/telemetria/evals_semana3.py`) funciona em duas etapas.

1. **Verificação em código (RNF-04).** Antes do juiz, o código confere:
   - se os lugares citados existem entre os 93 da base;
   - se a RA do lugar recomendado é a esperada;
   - se os preços citados batem com os da base;
   - se a pergunta fora do DF foi recusada.
2. **Juiz.** O MiMo-V2.6-Pro (`xiaomi/mimo-v2.6-pro`), de outra família que o modelo avaliado, roda com temperatura 0 e saída em JSON. Ele classifica cada afirmação da resposta sobre lugar, preço, endereço ou horário como "confere com a base", "contradiz a base" ou "não está na base".
   - Para o Modo B, o juiz recebe os mesmos documentos que o modelo recebeu.
   - Para o Modo A, ele recebe os lugares citados que existem na base e os do gabarito.
   - Usamos um juiz de outra família porque um modelo tende a favorecer as próprias respostas.

A partir dos vereditos, cada resposta recebe as notas abaixo.

| Nota | O que mede |
|---|---|
| Acerto do gabarito | O lugar do gabarito aparece na resposta (fora do DF, a recusa conta como acerto) |
| Fidelidade (RNF-03) | Proporção das afirmações que conferem com a base |
| Alucinação | Proporção das afirmações que a base desmente |
| Fora da base | Proporção das afirmações que a base não permite verificar |
| Precisão da RA (RNF-13) | Algum lugar recomendado está na RA esperada |
| Recall@3 e MRR | O lugar do gabarito está entre os 3 documentos recuperados, e em que posição |
| Latência (RNF-14) | Tempo de resposta, com meta de p90 até 5 s |
| Custo (RNF-15) | Custo das chamadas pagas por pergunta, em reais (cotação de R$ 5,80 por dólar) |

Uma recusa ou um "não sei" não tem afirmação a medir. Nesse caso, a resposta conta como abstenção nos dois modos, fica sem nota de fidelidade e de alucinação, e o erro, quando havia resposta na base, aparece no acerto do gabarito.

## 5. Resultados

### 5.1 Comparação das seis configurações

Rodada 1, 20 perguntas por configuração. Contagens sobre os casos em que a nota se aplica. O p90 é calculado sobre as 20 latências com `statistics.quantiles` do Python (método exclusivo, que interpola entre a 18ª e a 19ª).

| # | Configuração | Acerto (20) | Acerto no DF (18) | Fidelidade | Alucinação | Fora da base | Precisão da RA | Recall@3 / MRR | Latência p50 / p90 | Custo por pergunta |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | LLM pura | 2 de 20 | 0 de 18 | 0,0% | 3,0% | 97,0% | 0 de 15 | — | 3,75 s / 5,26 s | R$ 0,00079 |
| 2 | LLM pura, raciocínio alto | 2 de 20 | 0 de 18 | 0,0% | 28,6%¹ | 71,4% | 0 de 14 | — | 6,84 s / 14,58 s | R$ 0,00198 |
| 3 | RAG sem LLM | 12 de 20 | 10 de 18 | 99,2% | 0,0% | 0,8% | 13 de 16 | 10 de 18 / 0,37 | 0,02 s / 0,03 s | R$ 0 |
| 4 | RAG + LLM, palavras | 12 de 20 | 10 de 18 | 98,7% | 0,0% | 1,4% | 13 de 16 | 10 de 18 / 0,37 | 3,15 s / 3,61 s | R$ 0,00081 |
| 5 | RAG + LLM, palavras, raciocínio alto | 12 de 20 | 10 de 18 | 100,0% | 0,0% | 0,0% | 13 de 16 | 10 de 18 / 0,37 | 4,51 s / 6,88 s | R$ 0,00121 |
| 6 | RAG + LLM, embeddings | 18 de 20 | 16 de 18 | 96,8% | 0,7% | 2,5% | 16 de 17 | 16 de 18 / 0,83 | 5,10 s / 5,83 s | R$ 0,00092 |

¹ Valor inflado por um defeito do avaliador, explicado na seção 8. As quatro respostas que somam essa taxa são recusas que só repetem o teto da pergunta.

- **A LLM pura não erra o preço: ela fala de lugares que não pode comprovar.** Na configuração 1, 97% das afirmações citam lugares fora da base. São 32 nomes em 13 das 20 respostas: parte existe, como o Coco Bambu; parte são descrições genéricas ("Feira de Vicente Pires", "praça de alimentação de shopping próximo") ou palavras que o extrator tomou por nome ("Alternativa"). Contradições reais, em que a base desmente o que foi dito, apareceram em 3 respostas. Com o raciocínio alto, o modelo se recusa em 6 das 20 perguntas (5 sem o raciocínio) e continua sem acertar nenhum lugar do DF.
- **O RAG fica fiel à base.** Nas configurações 3 a 6, nenhum lugar fora da base foi recomendado. A única contradição da rodada 1 está na configuração 6 e é discutida na seção 7.
- **O raciocínio alto não ajuda o RAG.** A configuração 5 acerta o mesmo que a 4, custa 50% mais e passa dos 5 s em 7 de 20 perguntas.
- **A busca por embeddings acerta mais, mas é mais lenta.** O embedding da pergunta leva cerca de 1,5 s pela rede, e 11 de 20 respostas passam de 5 s.

### 5.2 Resultados por categoria

Acerto do gabarito e fidelidade, rodada 1.

| Categoria | Casos | LLM pura (1) | RAG sem LLM (3) | RAG + LLM, palavras (4) | RAG + LLM, embeddings (6) |
|---|---|---|---|---|---|
| RA fora do centro | 5 | 0 de 5 | 4 de 5 | 4 de 5 | 5 de 5 |
| Janela de horário | 3 | 0 de 3 | 2 de 3 | 2 de 3 | 2 de 3 |
| Fora do DF | 2 | 2 de 2 | 2 de 2 | 2 de 2 | 2 de 2 |
| Precisão financeira | 5 | 0 de 5 | 3 de 5 | 3 de 5 | 5 de 5 |
| Ambiente e restrições | 3 | 0 de 3 | 1 de 3 | 1 de 3 | 3 de 3 |
| Conflito e gírias | 2 | 0 de 2 | 0 de 2 | 0 de 2 | 1 de 2 |

A busca por embeddings ganha sobretudo em preço, ambiente e restrição alimentar, perguntas que descrevem a experiência mais do que o nome ou o tipo do lugar. Nessas categorias, 4 perguntas só foram acertadas pela busca vetorial: "jantar romântico a dois num restaurante chique" (Lucca), "rodízio de churrasco japonês" (Yaki Nikuya), "doceria sem trigo, sem lactose e sem açúcar refinado" (Lefit) e "prato executivo em Samambaia por até R$ 30" (Saguari).

### 5.3 Variação entre as duas rodadas

As duas rodadas foram feitas sem cache.

- **Acerto estável.** O acerto do gabarito foi idêntico nas duas rodadas, em todas as configurações.
- **Variação pequena no RAG.** Nas configurações 4 a 6, a nota do juiz mudou em no máximo 3 das 20 perguntas, e a alucinação média variou menos de 1 ponto percentual.
- **Variação maior na LLM pura.** A latência da LLM pura variou mais: o p90 da configuração 2 foi de 14,6 s para 18,1 s.

## 6. Critério de escolha e configuração escolhida

O critério foi definido antes de rodar o benchmark (issue #38): entre as configurações com p90 de até 5 s e nenhum lugar recomendado fora da base, vence a de maior acerto do gabarito, e no empate, a mais barata.

- **Configurações elegíveis.** Só a 3 e a 4 passam pelos dois filtros. A 1 e a 2 recomendam lugares fora da base; a 5 e a 6 passam de 5 s no p90.
- **Vencedora pelo critério: configuração 3, RAG sem LLM.** Ela empata com a 4 em 12 de 20 de acerto e vence no desempate por não ter custo de modelo.
- **Configuração adotada no produto: a 4, RAG + LLM com a busca por palavras.** Fica dentro do RNF-14 (p90 de 3,61 s), tem 98,7% de fidelidade e custa R$ 0,0008 por pergunta. É uma decisão de produto, à parte do critério. O texto fixo só sabe recomendar o 1º lugar da busca; o LLM explica quando o lugar atende só em parte ("isso ultrapassa seus R$ 30 em cerca de R$ 3"), contextualiza as recusas e escolhe entre os 3 documentos o que de fato responde à pergunta.
- **Próximo passo: a busca vetorial.** Ela é a candidata para depois que o embedding da pergunta ficar mais rápido, com cache ou um modelo local. Com 16 de 18 de recall, é a configuração que mais acerta. O ganho estimado no p90 ainda não foi medido.

## 7. Análise qualitativa de casos

**Caso 1 — RA fora do centro (golden_01).** "Onde tem rodízio de mini hambúrguer e pão de queijo em Taguatinga para ir com amigos?"
- **LLM pura.** Disse que não tinha certeza e, mesmo assim, sugeriu "Bar do Caldo (Taguatinga)", "Boteco da Asa (Taguatinga)" e o Taguatinga Shopping, sempre com "não sei confirmar". Nenhum está na base.
- **RAG + LLM.** Indicou o Filomenambúrguer [FONTE #2] em Taguatinga Norte, a R$ 49,99, com o rodízio de pão de queijo e a brinquedoteca descritos no [vídeo de evidência](https://www.tiktok.com/@rolezandoembrasilia/video/7626405885388197128). O lugar do gabarito era o 2º da busca, e o modelo o escolheu em vez do 1º.

**Caso 2 — quando a busca falha (golden_05).** "Onde comer rodízio de pizza e sushi à noite em Samambaia com a família?"
- **Busca por palavras.** Não trouxe o VBQ. O modelo respondeu, com honestidade, que a base não tinha um lugar com rodízio de pizza e sushi em Samambaia, e listou as opções mais próximas em outras RAs.
- **Busca por embeddings.** Trouxe o VBQ em 1º lugar (Samambaia, R$ 44,90, mais de 30 sabores de pizza e ilha de sushi, [vídeo](https://www.tiktok.com/@rolezandoembrasilia/video/7678112514009304338)), e a resposta acertou.
- **Leitura.** O erro é da recuperação, não da geração.

**Caso 3 — recusa indevida (golden_06).** "Onde dá para comer e beber com os amigos depois da 1h da manhã num sábado?"
- **O que aconteceu.** As duas buscas recusaram a pergunta: a aderência ficou em 0,62 na busca por palavras (limiar de 0,65) e em 0,6248 no cosseno (limiar de 0,63). O New Mercadito, aberto até 1h30, está na base.
- **Leitura.** O limiar que protege contra perguntas fora do tema também barra uma pergunta válida. A margem no cosseno é de cinco milésimos.

**Caso 4 — fora do DF (golden_09).** "Quais são os melhores bares em Copacabana, no Rio de Janeiro, para ir com amigos numa sexta à noite?"
- **RAG.** O guardrail recusou em menos de 1 ms, sem chamar o modelo.
- **LLM pura.** Também recusou, porque o prompt a apresenta como assistente de rolês no DF, e se ofereceu para sugerir bares em Brasília.
- **Leitura.** As duas recusas contam como acerto.

**Caso 5 — a única contradição do RAG (golden_15).** "Tenho só R$ 30, nem um centavo a mais. Dá para almoçar no buffet à vontade com tempero nordestino em Vicente Pires numa terça-feira?"
- **O que o modelo respondeu.** Com a busca vetorial, "Sim, dá." e, na frase seguinte, que o preço médio do Restaurante do Daniel é R$ 32,99, acima dos R$ 30.
- **Por que o juiz marcou contradição.** O "Sim, dá" pressupõe um preço de até R$ 30, e o documento traz R$ 32,99.
- **Leitura.** Nenhum dado foi inventado, e a própria resposta corrige o preço na frase seguinte. O problema é a resposta começar por uma conclusão errada. Com a busca por palavras, o mesmo modelo começou com "Sim, dá — mas por pouco" e foi marcado como fiel. A diferença entre as duas frases é pequena, e é nesse tipo de caso que o juiz e uma leitura humana podem discordar.

**Caso 6 — guardrail literal demais (golden_19).** "Quero comemorar meu aniversário num rodízio japonês completo na Asa Norte, mas sem pagar nada. Existe rodízio caro totalmente de graça?"
- **O que o RAG respondeu.** Leu "sem pagar nada" como teto de R$ 0, retirou todos os lugares e respondeu que nenhum lugar da base é grátis.
- **O que a base tem.** O gabarito é o Blue Sushi: segundo o vídeo, o aniversariante que leva 10 convidados não paga o próprio rodízio.
- **Leitura.** O filtro de teto, que protege o orçamento, não sabe ler uma condição.

## 8. Limitações

- **Amostra pequena.** São 20 perguntas e uma base de 93 lugares. Uma pergunta vale 5 pontos percentuais de acerto, então diferenças de uma ou duas perguntas não devem ser lidas como tendência.
- **Defeito no avaliador da LLM pura com raciocínio.** Os 28,6% de alucinação da configuração 2 vêm de quatro recusas (golden_07, 14, 15 e 20) que só repetem o teto da pergunta, como em "não tenho informação confiável para indicar buffet… por menos de R$ 30". O código toma esse valor como preço inventado. Lidas à mão, essas respostas não contêm contradição.
- **Juiz diferente na rodada 1 da LLM pura.** Na rodada 1, as configurações 1 e 2 foram julgadas com a versão anterior do prompt do juiz, e as configurações 3 a 6, com a versão corrigida. A rodada 2 usa a versão corrigida em todas.
- **"Fora da base" não é invenção comprovada.** A nota mostra o que não conseguimos verificar. Parte dos lugares citados pela LLM pura existe.
- **O juiz também erra.** Antes da correção do prompt, ele marcava como contradição respostas que diziam "a base não tem", comparando-as com documentos que o modelo não tinha recebido. As contradições que sobraram foram conferidas à mão (seção 7).
- **Uma data e um modelo.** Os resultados valem para o DeepSeek V4.1 Flash, as versões de prompt de 10/11 (Modo A) e 12/11 (Modo B) e a base de novembro de 2026.

## 9. Telemetria e auditoria

- **Langfuse.** Cada comparação gera um trace no Langfuse Cloud, com os dois modos, a busca, os guardrails e as notas do avaliador. O benchmark foi registrado como seis experimentos sobre o dataset `golden_dataset_semana3`, um por configuração, com o trace de cada resposta. Os links estão no [log do benchmark](BENCHMARK_LLM_VS_RAG_LOG.txt); o projeto no Langfuse é de acesso do grupo.
- **Registro sem dados pessoais (RNF-10).** O `logger_metricas` grava em JSONL a latência, os tokens, o custo e o modo de cada chamada, e mascara CPF, e-mail, telefone e valores de orçamento.
- **Cache (RNF-15).** O cache por SHA-256 da pergunta evita pagar duas vezes pela mesma chamada; o benchmark foi rodado com ele desligado.
- **Reprodução.** `PYTHONPATH=. python scripts/executar_benchmark_semana3.py` refaz o benchmark. Os resultados estão em `data/resultados_benchmark_semana3.json` e `.csv`, e o log comprobatório, com as 20 respostas lado a lado, em `docs/entregas/semana-03/BENCHMARK_LLM_VS_RAG_LOG.txt`.
- **Testes automáticos.** O golden dataset, o avaliador, o comparador e a integridade dos resultados têm testes que rodam no CI do GitHub Actions.

## Referências

BRASIL. **Lei nº 13.709, de 14 de agosto de 2018**. Lei Geral de Proteção de Dados Pessoais (LGPD). Diário Oficial da União: seção 1, Brasília, DF, 15 ago. 2018.

CORMACK, Gordon V.; CLARKE, Charles L. A.; BUETTCHER, Stefan. Reciprocal rank fusion outperforms Condorcet and individual rank learning methods. In: **Proceedings of the 32nd International ACM SIGIR Conference on Research and Development in Information Retrieval**. 2009. p. 758-759.

LEWIS, Patrick et al. Retrieval-augmented generation for knowledge-intensive NLP tasks. **Advances in Neural Information Processing Systems**, v. 33, p. 9459-9474, 2020.

ZHENG, Lianmin et al. Judging LLM-as-a-judge with MT-Bench and Chatbot Arena. **Advances in Neural Information Processing Systems**, v. 36, 2023.
