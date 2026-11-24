# Status do projeto

> Arquivo vivo. Toda sessão (humana ou de agente) lê no início e atualiza no fim.
> Mantenha curto: o histórico fica em `docs/semanas/` e no `git log`.

**Atualizado em:** 2026-11-24
**Semana do roadmap:** 4 — Primeiro Protótipo Multiagente (LangGraph + Ferramentas Determinísticas)

## Agora

- **Relatório técnico da semana 4 (Cauan, 20/11), issue #76, branch `docs/76-relatorio-semana4`:** concluído e entregue; por acordo do grupo, o relatório ficou com o Cauan.
  - [RELATORIO_TECNICO_SEMANA_04.md](docs/entregas/semana-04/RELATORIO_TECNICO_SEMANA_04.md), com o `.tex` em ABNT para o Overleaf, o PDF e o ZIP, no formato da semana 3;
  - o demo foi rodado de novo depois dos merges dos PRs #85 (diagrama, #75) e #89 (telemetria, #73): o padrão termina sem cartões em 19,5 s (US$ 0,0045) e o controle com 3 cartões viáveis em 24,6 s (US$ 0,0034); registro na Seção 8.13 do [semana-04.md](docs/semanas/semana-04.md);
  - os prints do Langfuse viraram figuras geradas das observações lidas pela API, porque a conta do Cauan no Langfuse não tem acesso ao projeto do grupo; dá para trocar por prints reais depois;
  - PR #90 (refinamentos da telemetria pedidos na revisão do #89) mesclado; 906 testes passam;
  - mapa da arquitetura atualizado: os 5 agentes e as etapas do grafo como prontos, e o rastreio decidido pelo ADR 0015; falta publicar no site.
- **Diagrama Visual da Arquitetura do Grafo Multiagente (Maria Carolina, 20/11), issue #75, PR #85 mesclado em 20/11:**
  - Documentação técnica em `docs/arquitetura/multiagente.md` e página web `docs/arquitetura/multiagente.html` atualizadas para refletir o grafo real implementado em `src/agentes/grafo.py` (`grafo_agentes.mmd`) e o contrato de `src/agentes/estado.py`;
  - Diagrama vetorial `docs/arquitetura/img/grafo_multiagente.svg` (gerado por `scripts/gerar_grafo_multiagente_svg.py`) e Mermaid com fan-out dos Agentes Pessoais (`Send`) + `no_consolidar_grupo`, `Cofre` do servidor fora do `MultiAgentState` (Canais 1, 2 e 4 no Cofre; Canal 3 como único público), saídas diretas para `no_finalizar` (sem janela comum ou sem lugar viável), laço `avaliar_convergencia` (até 2 voltas), reescrita seletiva em `no_validacao_textos` (máximo 1 vez), Juiz LLM em 2 passagens (#72), preenchimento de preços/tempos/`tiktok_url` em `no_finalizar`, spans reais do Langfuse e SLA do RNF-14 ($\le 60\text{ s}$ para gerar planos);
  - Removido o botão para `multiagente.html` do `docs/arquitetura/index.html` (evitando 404 no site público) e mantida a página no `mkdocs.yml`;
  - Suíte de 6 testes em `tests/test_arquitetura_multiagente.py`; 890 testes passam no total (`pytest tests`).
- **Semana 4, issues do Cauan (17/11):** #64 concluída (PR [#77](https://github.com/Residencia-IA-Challenge-2-Grupo-7/residencia-ia-g7-challenge2/pull/77) mesclado: `MultiAgentState` em `src/agentes/estado.py`). #65 (Agente Pessoal), #70 (Pesquisa) e #71 (grafo) entraram com o PR [#80](https://github.com/Residencia-IA-Challenge-2-Grupo-7/residencia-ia-g7-challenge2/pull/80), e o juiz da #72 com o #86. A #74 (demo, PR #88 mesclado em 20/11) liga o juiz no grafo e roda os dois cenários da #66 com LLM: o padrão termina sem cartões (15 s, US$ 0,0026) e o de controle com 3 cartões viáveis (25 s, US$ 0,0035), com os traces no Langfuse; números e links na Seção 8.11 do [semana-04.md](docs/semanas/semana-04.md). Pendências: o juiz dos cartões pode estourar o RNF-14 quando a 1ª chamada esgota o tempo (uma rodada levou 74 s); a #73 (forma do rastreio) segue em aberto; sem LLM, a Pesquisa acha só 1 dos 5 viáveis do controle (a nota léxica satura); juntar a Comunicação do grafo com o `executar_agente_comunicacao` da #69. As Seções 2 a 4 do `semana-04.md` já descrevem o grafo implementado e servem de base ao diagrama da #75.
- **Dataset de cenários do multiagente (Samara Letícia, 19/11), issue #66, PR na branch `feat/semana4-dataset-cenarios` (revisão atendida):**
  - `data/cenarios_teste_multiagente.json` com dois cenários dos 4 amigos: o padrão da issue (Ceilândia, Águas Claras, Asa Norte e Sobradinho), **sem lugar viável** na base atual, e o de controle (m1 sem vegetariano, m4 saindo de Taguatinga), com 5 lugares viáveis para o caminho feliz;
  - a causa estável do "sem lugar viável" é a restrição vegetariana com o teto de R$ 40 (só 3 lugares da base comprovam opção vegetariana); o deslocamento também veta tudo com o estimador atual, mas isso depende da calibração (#67);
  - `src/agentes/cenarios.py` converte um cenário na entrada do grafo (`para_entrada_do_grafo`), para a #74 e os testes da #67 e da #68 usarem a mesma conversão;
  - achados para a #67, a #68 e a curadoria: o gerador de cartões das salas não descarta trajetos acima de 75 min (sugere o Cachorrão da 5 com mais de 3 h para Sobradinho), a Hamburgueria Espacial tem RA contraditória (Taguatinga no registro, Sobradinho no endereço e na coordenada) e o R$ 1,99 do Golden Black é preço de promoção;
  - 97 testes em `tests/test_cenarios_multiagente.py`; detalhes na Seção 8.3 de [docs/semanas/semana-04.md](docs/semanas/semana-04.md).
- **Agente 4 (Comunicação): Prompt do Anfitrião e Formatação de Cartões em JSON (Maria Carolina, 17/11), issue #69, na branch `feat/semana4-agente-comunicacao`:**
  - Implementação de `src/agentes/comunicacao.py` (`executar_agente_comunicacao(candidatos_validados) -> list[dict]`) e do nó `no_comunicacao` para o LangGraph;
  - System prompt configurado com a persona "Anfitrião de Brasília" em `src/agentes/prompts/comunicacao.md` gerando estritamente `titulo`, `resumo_acesso` e `por_que_combina`;
  - Preço médio, tempos de chegada, endereço oficial e links do TikTok preenchidos deterministicamente fora da LLM no esquema `Sugestao` (RF-06, RNF-04);
  - Zero citação ou vazamento de orçamentos, origens ou restrições individuais (RNF-02);
  - Validação estrita dos cartões via Pydantic (`CartaoSugestaoValidado`) e fallback determinístico offline;
  - 10 testes unitários em `tests/test_agente_comunicacao.py`; 625 testes passam no total (`make test-local`).
- **Agente 2 (Logística & Justiça) (Samara Letícia, 19/11), issue #67, na branch `feat/semana4-agente-logistica`:**
  - `src/agentes/logistica.py`: `executar_agente_logistica` avalia cada candidato da Pesquisa em código puro (RNF-04): primeira janela comum em que o lugar abre, trajeto de cada membro pelo meio mais barato que chega em até 75 min, `nota_menor_miseria` e pontuação 45% aderência, 35% justiça, 20% horário;
  - saída em `CandidatoAvaliado` só com agregados; o trajeto de cada pessoa fica em `Cofre.analises` (RNF-02); a Logística não veta, a Validação (#68) decide;
  - `gerar_parecer`: texto feito por regra ("pior trajeto 85 min de ônibus/metrô; média 62 min"), sem marcador nem RA de origem; o meio só aparece quando pelo menos 2 presentes o usam (RNF-02);
  - `escolher_meio` passou de `src/salas/sugestoes.py` para `src/logistica/transporte_df.py`, compartilhado com a Tela 3;
  - 47 testes novos (40 em `tests/test_agente_logistica.py`, 19 deles rodando os cenários da #66 com a base real; 7 em `tests/test_transporte_df.py`); 789 testes passam no total (`make test-local`, com a `main` do #82 mesclada). Detalhes na Seção 8.4 de [docs/semanas/semana-04.md](docs/semanas/semana-04.md).
- **Telas 1 a 3 do aplicativo (Maria Carolina, 17/11), issue #42, PR #79 (revisão atendida):** implementadas em [src/telas/](src/telas/rotas.py) (branch `feat/frontend-issue-42`): navegação unificada por 3 abas superiores interativas (`1. Criar Sala`, `2. Meus Dados`, `3. Painel e Votação`), alternância dinâmica com histórico e modo demonstração (`DEMO`) com lugares reais de Brasília do catálogo TikTok quando acessado em `/sala/demo`. Revisão da issue #42 / PR #79 totalmente atendida: modo dev oculto por padrão (ativo apenas com `?dev=1` ou `DEMO`), remoção de `onclick` inline (CSP compliance), tratamento de erros 404/5xx sem fallback cego para demo, datas dinâmicas de fim de semana e teste automatizado de RNF-02 cobrindo HTML estático. Suíte de testes de interface passa (`tests/test_interface_app.py`).
- **Juiz do avaliador trocado (Cauan, 17/11):** `z-ai/glm-5.3-flash` no lugar do `xiaomi/mimo-v2.6-pro` ([ADR 0014](docs/decisoes/0014-juiz-glm-5.3-flash.md)). Nas mesmas 94 respostas da rodada 2 da semana 3: US$ 0,057 contra US$ 0,731, p90 de 10,1 s contra 18,8 s, concordância de 90 de 94 sobre haver contradição ([experimento](docs/experimentos/2026-11-17-juiz-glm.md)). O GLM é mais leniente no caso limite do golden_15. Os resultados da semana 3 continuam os do MiMo.
- **Relatório da Semana 3 (Cauan, 13/11), issue #40, branch `feat/40-relatorio-semana3`:**
  - texto em [docs/entregas/semana-03/RELATORIO_TECNICO_SEMANA_03.md](docs/entregas/semana-03/RELATORIO_TECNICO_SEMANA_03.md) e `.tex` (preâmbulo ABNT da semana 2), com as 6 configurações, o critério, a escolha, 6 casos e as limitações da medição da LLM pura;
  - PDF compilado com o Tectonic (`tectonic -X compile docs/entregas/semana-03/RELATORIO_TECNICO_SEMANA_03.tex`; o Overleaf também serve) e pacote `Entregavel_Grupo7_Semana_03.zip`, com o nome que a rota de download do PR #62 procura, gerado por `python scripts/gerar_pacote_semana3.py`. Mudou o `.md`? Atualize o `.tex`, recompile e gere o ZIP de novo;
  - os links do PDF (`/comparativo` e `/entregaveis` em `orquestrador-roles.onrender.com`) são provisórios: trocar pelo endereço do deploy antes da correção dos mentores (segunda, 16/11).
- **Central de Entregáveis da Semana 3 (Maria Carolina, 13/11), issue #39, na branch `feat/frontend-issue-39`:**
  - Interface `/entregaveis` evoluída com o painel da Semana 03 (Comparação LLM Pura vs. RAG) e botão de destaque para `/comparativo`, mantendo os 7 módulos da Semana 02 100% preservados (`RNF-12`);
  - Placar comparativo preenchido dinamicamente a partir de `/api/entregaveis/dados?colecao=benchmark_semana3` para as configurações #1, #3, #4 e #6 (alucinação, afirmações fora da base, acerto do gabarito, precisão de RA, RNF-03 e RNF-14);
  - Visualizador interativo do Golden Dataset com 20 casos (`colecao=golden_semana3`) com filtros por categoria e busca textual;
  - Visualizador dos resultados auditados do Benchmark A/B (`colecao=benchmark_semana3`) com seletor para comparar as 6 configurações avaliadas, notas (`scores`) do avaliador híbrido e escape HTML (`escapeHtml`) contra XSS;
  - Novas rotas em `src/main.py` com helper `_primeiro_arquivo`: `/visualizar/relatorio-semana3-pdf`, `/download/relatorio-semana3-pdf` e `/download/entregavel-semana3-zip`;
  - Nova suíte de testes em `tests/test_entregaveis_semana3.py` (cobrindo integridade da Semana 2, coleções da Semana 3, códigos 200/400/404, elementos HTML da interface e escape de `<script>`).
- **Benchmark oficial A/B das 20 consultas (Letícia Miti, 13/11), issue #38 (revisão da @cadasiso atendida):**
  - `scripts/executar_benchmark_semana3.py` executa as 20 perguntas de `data/golden_dataset_semana3.json` nas 6 configurações da Semana 3 em 2 rodadas, aciona o avaliador híbrido (`src/telemetria/evals_semana3.py`) e registra os 6 experimentos no dataset `golden_dataset_semana3` do Langfuse Cloud via `run_experiment`;
  - resultados detalhados salvos em `data/resultados_benchmark_semana3.json`, `data/resultados_benchmark_semana3.csv`, `docs/entregas/semana-03/BENCHMARK_LLM_VS_RAG_LOG.txt` e documentados em [docs/experimentos/2026-11-13-benchmark-semana3.md](docs/experimentos/2026-11-13-benchmark-semana3.md);
  - **configuração vencedora pelo critério estrito da #38** (p90 <= 5 s, 0 lugares inventados, maior acerto do gabarito, menor custo no desempate): **#3 — RAG sem LLM, texto fixo (`3_rag_sem_llm_texto_fixo`)**, que empata em acerto com a **#4** (**12 de 20** no geral e **10 de 18** no DF), tem **99,2% de fidelidade factual**, **0,0% de alucinação**, **p50 de 0,02 s / p90 de 0,03 s** e vence no desempate por ter **custo real zero (R$ 0,00 e 0 tokens)**. Como decisão de produto à parte para síntese em linguagem natural, usa-se a **#4 — RAG + LLM, busca léxica (`4_rag_llm_busca_lexica`)** (**98,7% de fidelidade**, **0,0% de alucinação na Rodada 1**, **p50 de 3,15 s / p90 de 3,61 s**, **R$ 0,00081/consulta**), evidenciando que na busca por palavras o LLM não aumenta o acerto porque o gargalo está na recuperação (`Recall@3 = 10 de 18`);
  - a **#6 — RAG + LLM, busca vetorial** alcança **18 de 20 (90,0%)** de acerto (16 de 18 no DF, Recall@3 de 88,9% e MRR de 0,8333) e **96,8% de fidelidade factual** (0,7% de alucinação: 1 afirmação em `golden_15`), mas o embedding adiciona ~1,5 s e leva o p90 a **5,83 s**; a **#1 — LLM pura sem raciocínio** acerta **0 de 18** no DF e inventa **32 lugares em 13 de 20 casos**;
  - `tests/test_resultados_benchmark.py` adicionado (10 testes validando completude dos 20 casos × 6 configurações, métricas, CSV, respostas da Rodada 2 e log TXT).
- **Fonte da verdade sobre o app: [GUIA_OFICIAL_PROJETO.md](GUIA_OFICIAL_PROJETO.md)** (10/11). Resumo do que ele fechou:
  - ciclo completo do rolê: sala, 4 campos secretos, 3 a 4 cartões, votação múltipla e, depois, foto da nota fiscal, divisão e Pix;
  - **sem voz** ([ADR 0009](docs/decisoes/0009-entrada-pelos-4-campos-de-texto.md)); a multimodalidade da semana 5 é a foto da nota fiscal;
  - **base oficial de 93 lugares** do TikTok com validação em 2 fatores ([ADR 0008](docs/decisoes/0008-base-2fa-de-93-lugares-e-lgpd.md)); `src/base/` (Overture) e `src/voz/` saíram do repositório, e os ADRs 0005 e 0006 ficaram como substituídos;
  - distância e transporte pelas 35 RAs com a regra da Menor Miséria; banco das salas no Supabase.
  - As tarefas da semana de cada integrante estão na seção 4 do guia.
- **Comparação LLM pura × RAG (Cauan, 12/11), issue #34, na branch `feat/34-comparador-ab`:**
  - `POST /api/comparativo/executar` roda a mesma pergunta nos dois modos, em paralelo, e devolve o contrato JSON da issue, com o gabarito quando a pergunta vem do golden; `GET /api/comparativo/golden` lista as perguntas ([ADR 0011](docs/decisoes/0011-comparativo-ab-com-o-mesmo-llm.md));
  - **Modo A:** DeepSeek V4.1 Flash sem documentos ([ADR 0010](docs/decisoes/0010-baseline-llm-pura-e-guardrails.md), PR #49). **Modo B:** busca com guardrails e o mesmo modelo com os lugares recuperados (`src/rag/llm_rag.py`). Antes, o Modo B era um texto fixo sem LLM;
  - prévia com os 10 casos do golden: o lugar do gabarito veio nas fontes do Modo B em 6 de 8 casos do DF, e as 2 perguntas fora do DF foram recusadas sem chamar o LLM. p90 de 5,1 s no Modo A e 4,8 s no Modo B. Os 2 erros são da busca: o VBQ (Samambaia) não foi recuperado, e o golden_06 foi bloqueado com aderência 0,62;
  - com o raciocínio alto ligado nos dois modos ([experimento](docs/experimentos/2026-11-12-comparativo-raciocinio.md)), o Modo B acertou os mesmos 6 de 8, mas o p90 foi a 7,3 s; a LLM pura passou a recusar em 6 de 10. O Modo B sem raciocínio continua a melhor configuração;
  - PRs #52 (tela) e #53 (motor) na `main`.
- **Busca vetorial e raciocínio no comparativo (Cauan, 12/11), PR #56 na `main`:**
  - busca vetorial com o `gemini-embedding-001` pela OpenRouter, a mesma chave do resto do projeto (vetores idênticos aos da base, cosseno 1,0), e híbrida ([ADR 0012](docs/decisoes/0012-busca-vetorial-pela-openrouter.md));
  - prévia com 10 casos ([experimento](docs/experimentos/2026-11-12-busca-vetorial.md)): lugar certo em 7 de 8 com a vetorial (6 de 8 por palavras), mas o p90 do Modo B vai a 6,1 s por causa do embedding (1,6 s). O padrão segue sendo a busca por palavras até a #38 escolher;
  - a rota e a tela do comparativo ganharam a escolha do raciocínio (dois modos) e da busca (Modo B);
  - a base tem lugares repetidos (Espaguete, Dunkin' Donuts, Johnny Joy, Anime Summit, ExpoFlores 2026; Filomenambúrguer com duas grafias), para a curadoria;
  - 208 testes no PR.
- **Golden dataset completo (Samara, 12/11), issue #32, PR #57 na `main`:**
  - os 20 casos em `data/golden_dataset_semana3.json`: 5 geoespaciais, 3 de horário, 2 fora do DF, 5 de preço exato, 3 de ambiência e restrição alimentar e 2 de conflito e gírias;
  - catálogo, regras e limitações conhecidas em [docs/dados/golden-dataset-semana3.md](docs/dados/golden-dataset-semana3.md); `tests/test_golden_dataset.py` trava os 20 casos, as 6 categorias e o preço contra o `custo_medio_rs`;
  - a prévia do comparativo usou só os 10 primeiros; os casos 11 a 20 já aparecem em `GET /api/comparativo/golden`.
- **Avaliação automatizada híbrida e Haystack (Eduarda, 12/11), issue #36, PR #60 (revisão da @cadasiso atendida em 13/11):**
  - `src/telemetria/evals_semana3.py`: checagem em código (RNF-04) + juiz MiMo-V2.6-Pro (`xiaomi/mimo-v2.6-pro`, temperatura 0, sem retenção), com fallback offline. Detalhe de regras e notas no docstring do módulo;
  - notas (`None` = não avaliado): `fidelidade_factual_rnf03`, `taxa_alucinacao` (só o que a base desmente), `taxa_fora_da_base` (não verificável), `precisao_geoespacial_ra`, `acerto_gabarito`, `abstencao` e `sla_latencia_rnf14`. Recusa e "não sei" valem igual nos dois modos; sem piso fixo; o juiz vê os mesmos campos do Modo B e não vê o veredito do código;
  - `POST /api/comparativo/avaliar` recebe só o `id_comparativo` devolvido por `/executar` (resultado guardado 15 min em memória, avaliado uma vez por id); erros viram 404 ou 500 sem a mensagem da exceção;
  - Langfuse: `input` e `output` nas gerações, scores no trace, sem a nota fixa `fidelidade_rnf03_zero_alucinacao`;
  - Haystack (`src/rag/pipeline_haystack.py`) com os campos reais da base: recall@3 de 2 para 14 de 18 ([experimento](docs/experimentos/2026-11-13-haystack-recall.md));
  - **565 testes passam** (`PYTHONPATH=. pytest tests`, fora o `test_smoke`, que precisa do `torch`).
- **Back-end das salas (Cauan, 10/11), PR #48 na `main`:**
  - `src/interpretador/campos.py`: os 4 campos viram RA (apelidos, quadras como SQN e QNM, estações de metrô), janelas pelo `tempo.py`, teto pelo `numeros.py` e tags com os rótulos da base. Tudo por regras; o LLM do ADR 0007 só entra se as regras não acharem nenhum dia ([ADR 0009](docs/decisoes/0009-entrada-pelos-4-campos-de-texto.md));
  - `src/state.py` (repositório em memória, pronto para trocar pelo Supabase) e `src/salas/` (gerenciador, cruzamento de horários, horário de funcionamento dos lugares, cartões, votação);
  - rotas em `/api/salas`: criar, painel, participantes (entrar, corrigir, confirmar, própria visão), gerar sugestões, votar e fechar votação. Contrato e exemplo em [src/salas/README.md](src/salas/README.md);
  - **110 testes passam** (`python -m pytest tests`), entre eles o fluxo de 3 participantes da issue #43 (`tests/test_salas_backend.py`) e uma varredura das respostas públicas atrás do teto de cada um; o CI e o `make test` passaram a rodar todos os testes;
  - códigos de sala no formato `ROLE-7KQ2`; issue #43 fechada.
- **Banco das salas (Eduarda), PR #50 na `main`:** `RepositorioSupabase` com `ROLES_REPOSITORIO=supabase`; o caminho do Postgres ainda não roda em nenhum teste, então o padrão continua `memoria`.
- **Finanças (Cauan, 12/11), issue #45, na branch `feat/45-financas`:** `src/financas/` com o orçamento sigiloso (só respostas sim ou não para fora), a divisão da conta com itens que só parte consumiu e centavos com quem pagou (RF-32), e o código Pix copia e cola estático (BR Code com CRC16, RF-33). O gerador reproduz um exemplo de código estático que tomamos como do manual do Banco Central (não conferido na fonte). `teto_seguro_grupo` já encaixa nas salas. Faltam as rotas da Tela 4 (lançar gasto, ver dívida, marcar como pago) e a criptografia da chave Pix no banco. 236 testes.
- **Encaixes pendentes** (o código usa uma reserva simples até chegarem; assinaturas em [src/salas/README.md](src/salas/README.md#encaixe-das-peças-das-colegas)):
  - Eduarda: `teto_seguro_grupo` em `src/financas/`;
  - Samara: **entregue na issue #44** (`estimar_deslocamento`, `nota_menor_miseria` e `calcular_score_justica_espacial` em `src/logistica/transporte_df.py`, pontos das 35 RAs em `data/regioes_df_gps.json`); as salas já usam o módulo no lugar da reserva. Regra, números e pendências no [ADR 0012](docs/decisoes/0012-deslocamento-e-menor-miseria.md);
  - Letícia: a busca com filtros, que hoje entra pela `calcular_similaridade_leticia`;
  - Maria Carolina: as Telas 1 a 3 chamando as rotas acima (tokens no cabeçalho `X-Token`).
- **Problemas achados na base** (para a Letícia, registrados no [ADR 0008](docs/decisoes/0008-base-2fa-de-93-lugares-e-lgpd.md#riscos-e-limitações)):
  - os 2 eventos do Gama têm coordenadas no Plano Piloto, e o lugar de Planaltina não tem coordenadas;
  - 14 itens são eventos ou promoções com datas que já passaram e saem das sugestões;
  - 21 lugares só dizem "Consultar no local";
  - a Lefit tem `custo_medio_rs = 28.0` e `trava_2_preco_ok = true`, mas o vídeo não cita preço; o `horario_funcionamento` do Saguari é o do happy hour, não o de abertura.
- **Risco aberto:** os termos do TikTok e o direito autoral do perfil de origem. O app mostra só fatos curtos e o link do vídeo; para uso além do acadêmico, pedir permissão por escrito ao autor.
- **Requisitos v0.4** em [docs/produto/requisitos.md](docs/produto/requisitos.md): voz removida (RF-39, RF-40), 4 campos no lugar da conversa privada, votação múltipla. A revisão completa com o grupo continua pendente.
- **Mapa da arquitetura** atualizado com o guia oficial (base de 93, 4 campos, sem voz, Supabase, salas e pós-rolê) em [docs/arquitetura/index.html](docs/arquitetura/index.html). **Falta publicar** com `publicar.sh`.
- **Plano do MVP navegável** ([docs/produto/plano-mvp.md](docs/produto/plano-mvp.md), rascunho local, fora do git): propõe Jinja2 + HTMX e voz, o que o guia oficial mudou. Revisar antes de usar.
- Histórico da semana 2 (pipeline da Overture, voz, interpretador medido com 97,1% no RNF-08): [docs/semanas/semana-02.md](docs/semanas/semana-02.md) e [docs/experimentos/](docs/experimentos/2026-11-05-voz-e-interpretador.md).
- Relatórios: semana 1 em [docs/entregas/semana-01/](docs/entregas/semana-01/), semana 2 em [docs/entregas/semana-02/](docs/entregas/semana-02/).
- Mapa da arquitetura publicado em [residencia-ia-challenge-2-grupo-7.github.io/residencia-ia-g7-arquitetura](https://residencia-ia-challenge-2-grupo-7.github.io/residencia-ia-g7-arquitetura/); como editar: [docs/arquitetura/AGENTS.md](docs/arquitetura/AGENTS.md).
- Repositório na organização do grupo: [Residencia-IA-Challenge-2-Grupo-7](https://github.com/Residencia-IA-Challenge-2-Grupo-7/residencia-ia-g7-challenge2) (privado).

## Próximos passos (Cauan, conforme o guia)

- Abrir o PR da issue #34, que destrava a #36 (Eduarda), a #37 (Maria Carolina) e a #38 (Letícia Miti). O PR #52 (interface do comparativo) precisa passar a usar estas rotas.
- Melhorar a busca do Modo B (filtro por RA; o golden_06 bloqueado pelo limiar), sem misturar com a avaliação da #38.
- Quinta: ligar as peças da Eduarda, da Samara e da Letícia quando chegarem e apoiar a Maria Carolina na integração das telas.
- Sexta: rodar o fluxo de uma sala inteira com as peças reais e o Supabase; revisar os ADRs 0008 e 0009 com o grupo.
- Ainda faltam no back-end das salas: prazos de resposta (RF-12), confirmação de presença (RF-26), modo "palavra final do organizador" (RF-24) e regra de datas do organizador (RF-14).

## Pacote de definição do projeto (entregável da semana 1)

- [x] Cenário escolhido
- [x] Problema
- [x] Essential Question
- [x] Mapa de stakeholders (PDF da equipe; precisa tirar jogos)
- [x] Personas (PDF da equipe; limite de sala a corrigir para 20)
- [ ] Requisitos funcionais e não funcionais (v0.3; falta revisão do grupo e coluna Métrica)
- [x] Riscos (PDF da equipe; R-01 a R-09 na numeração nova, no relatório os 6 de maior P × I)
- [x] Premissas (PDF da equipe)
- [x] Métricas de sucesso (PDF da equipe; 7 métricas, no relatório as 3 de resultado)
- [x] Guiding questions (PDF da equipe)
- [x] Montar o relatório .docx a partir do plano (falta completar os sobrenomes na capa e conferir duas referências)

## Próximos passos dos requisitos

- Revisar a v0.4 com o grupo, principalmente as escolhas de comportamento de 29/10 e a seção "Questões em aberto" do documento.
- Preencher a coluna Métrica (M-NN) quando o plano de métricas fechar. O resultado do formulário ajusta as prioridades, e as métricas dão os números dos RNF.
- No documento final, só os Must, agrupados nas 12 capacidades sugeridas no próprio arquivo.
- Escrever os requisitos das extensões futuras (Modo Descoberta, videogames, versão para menores), se sobrar tempo.
- Quando houver código (semana 2), avaliar `openspec init` e migrar cada capacidade para `openspec/specs/`.

## Em aberto

- Convidar os integrantes do grupo para a organização no GitHub
- Confirmar as datas do roadmap
- Combinar com o grupo a convenção de IDs (RF, RNF, R, M) para a rastreabilidade
- Confirmar com o grupo o canal do MVP (ADR 0003)
- No documento da equipe: criar a P19 e a P20 na guia Premissas e alinhar a numeração das guias à do relatório (4 Stakeholders, 8 Riscos, 9 Métricas, 10 Guiding Questions)
- Decidir se o RF-37 (avaliação) sobe para Must, já que a métrica M-03 depende dele
- Painel da sala: o guia mostra quem já preencheu, e o RF-45 dizia para não mostrar quem falta (requisitos v0.4)
- LGPD das salas (ADR 0008): região do Supabase (`sa-east-1`) e prazo para apagar as salas (proposta: 30 dias depois do rolê)

## Integrantes

Papéis definidos em 29/10 ([ata](docs/atas/2026-10-29.md)); a divisão mais detalhada (DevOps, UX/UI e front-end, back-end, testes, engenharia de IA) segue em discussão.

- Cauan Soares: Arquiteto da Solução
- Letícia Miti: Cientista de Dados
- Maria Carolina: Engenheira de Dados
- Maria Eduarda: ML/LLMOps
- Samara Letícia: Engenheira de Dados
