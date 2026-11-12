# Semana 3 — Comparação RAG × LLM pura (e Telas 1 a 3 do app)

**Entregável:** comparação entre respostas da LLM pura e do RAG, com evidências. Em paralelo, o app real ([guia oficial](../../GUIA_OFICIAL_PROJETO.md), seção 4).

## Registro

- 2026-11-10: o grupo publicou o [guia oficial](../../GUIA_OFICIAL_PROJETO.md) na `main`, que passa a ser a fonte da verdade sobre o app: ciclo completo do rolê com pós-rolê e Pix, sem voz, 4 campos de texto secretos, base oficial de 93 lugares do TikTok, transporte pelas 35 RAs com a regra da Menor Miséria e banco no Supabase. `src/base/` e `src/voz/` saíram do repositório.
- 2026-11-10 (Cauan): back-end das Telas 1 a 3 na branch `feat/salas-backend`.
  - Os 4 campos viram perfil por regras (`src/interpretador/campos.py`): RA por apelidos, siglas de quadra e estações de metrô; janelas pelo `tempo.py`; teto pelo `numeros.py`; tags com os rótulos da base. O LLM do ADR 0007 só entra se as regras não acharem nenhum dia.
  - Salas, cruzamento de horários, leitura do horário de funcionamento dos lugares, cartões com Menor Miséria e votação múltipla em `src/salas/`, com o estado em `src/state.py` e as rotas em `/api/salas`.
  - As peças da Eduarda (teto do grupo, Supabase), da Samara (deslocamento, nota de justiça) e da Letícia (busca) entram por `src/salas/integracoes.py`, com uma reserva simples até chegarem.
  - 59 testes novos; 99 no total. O CI passou a rodar todos.
  - ADR 0008 (base de 93 lugares e LGPD) e ADR 0009 (4 campos, sem voz); requisitos v0.4 com a voz removida.
- 2026-11-10 (Cauan): issue #33, PR #49. Modo A da comparação com o DeepSeek V4.1 Flash pela OpenRouter, no lugar do Gemini 1.5 Flash, que foi descontinuado ([ADR 0010](../decisoes/0010-baseline-llm-pura-e-guardrails.md)). Guardrails do RAG em código: pergunta fora do DF, aderência abaixo de 0,65 e teto em reais. Com raciocínio alto, o modelo quase não inventou endereços, mas não indicou nenhum lugar em 13 de 16 respostas, com p90 de 11,9 s ([experimento](../experimentos/2026-11-10-llm-pura-raciocinio.md)); o relatório usa o modo sem raciocínio como principal.
- 2026-11-12 (Cauan): issue #34. Motor da comparação A/B e rotas `/api/comparativo`. O Modo B passou a gerar a resposta com o mesmo LLM do Modo A, recebendo os lugares recuperados ([ADR 0011](../decisoes/0011-comparativo-ab-com-o-mesmo-llm.md)). Prévia com os 10 casos do golden: o lugar certo veio nas fontes do Modo B em 6 de 8 casos do DF, e as 2 perguntas fora do DF foram recusadas sem chamar o LLM ([resultados](../../eval/resultados/comparativo-ab-previa-golden-01-10-2026-11-12.json)).
- 2026-11-12 (Samara): issue #32. O golden dataset fechou em 20 casos. Os 10 novos cobrem preço exato (rodízio, ingresso de parque infantil, teto estrito de R$ 30), ambiência e restrição alimentar (Kid Friendly, sem trigo, lactose e açúcar refinado, jantar romântico) e conflito e gírias candangas. Nome, RA e preço foram copiados da base; são 18 lugares diferentes para 20 perguntas, e um teste trava a contagem, as 6 categorias e o preço contra o `custo_medio_rs` ([catálogo e regras](../dados/golden-dataset-semana3.md)).
- 2026-11-10: a leitura do horário de funcionamento dos 93 lugares, num sábado à noite, deu 32 abertos, 5 prováveis, 23 incertos, 19 fechados e 14 encerrados (eventos e promoções com datas passadas). Os 2 eventos do Gama têm coordenadas no Plano Piloto, e o lugar de Planaltina não tem coordenadas.

## Decisões da semana

- [ADR 0008](../decisoes/0008-base-2fa-de-93-lugares-e-lgpd.md): base oficial de 93 lugares com validação em 2 fatores e medidas de LGPD (substitui o ADR 0005).
- [ADR 0009](../decisoes/0009-entrada-pelos-4-campos-de-texto.md): entrada pelos 4 campos de texto, interpretados por regras, sem voz (substitui o ADR 0006).
- [ADR 0010](../decisoes/0010-baseline-llm-pura-e-guardrails.md): Modo A com o DeepSeek V4.1 Flash e guardrails determinísticos no RAG.
- [ADR 0011](../decisoes/0011-comparativo-ab-com-o-mesmo-llm.md): no comparativo, o Modo B gera a resposta com o mesmo LLM do Modo A.

## Aprendizados e dúvidas

- Com os campos separados, a intenção de cada texto já é conhecida, e regras simples resolvem os exemplos do guia sem mandar localização nem dinheiro para um LLM externo.
- Checar o orçamento pelo menor teto do grupo contra o maior gasto descartava lugares demais: misturava o teto de uma pessoa com o transporte de outra. A checagem por pessoa (consumo + transporte dela ≤ teto dela), feita só no servidor, segue o RF-17 sem expor ninguém.
- A rota de RAG da semana 2 não chamava LLM nenhum: o texto era fixo, preenchido com o 1º lugar. Comparar isso com um LLM mediria o template, não a base. Com o mesmo modelo nos dois modos, o Modo B escolheu o lugar certo mesmo quando ele vinha em 2º ou 3º na busca.
- Quem diz "metrô ou Uber" não deve pagar Uber à toa: o deslocamento escolhe o meio mais barato que chega em até 75 minutos.
- O teste do golden confere que o gabarito bate com a base, não que a base bate com a realidade: a Lefit passa com um preço que o vídeo não cita. Os 3 casos com limitação conhecida de preço (golden_13, 15 e 16) estão registrados no doc, para a auditoria não contá-los como acerto ou erro do RAG sem ressalva.
