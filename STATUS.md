# Status do projeto

> Arquivo vivo. Toda sessão (humana ou de agente) lê no início e atualiza no fim.
> Mantenha curto: o histórico fica em `docs/semanas/` e no `git log`.

**Atualizado em:** 2026-11-12
**Semana do roadmap:** 3 — Comparação RAG × LLM pura, com as Telas 1 a 3 do app em paralelo

## Agora

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
- **Avaliação automatizada híbrida e Haystack (Eduarda, 12/11), issue #36, na branch `feat/entrega-semana3-comparativo-relatorio`:**
  - `src/telemetria/evals_semana3.py` (`avaliar_par_comparativo` e `POST /api/comparativo/avaliar`): Etapa 1 determinística em Python (RNF-04) conferindo se os lugares existem nos 93 de `data/banco_aprovado_2fa.json`, se a RA corresponde à `ra_esperada` e se o preço respeita o gabarito; Etapa 2 com LLM-as-a-Judge pelo MiMo-V2.6-Pro (`xiaomi/mimo-v2.6-pro` na OpenRouter, família distinta do DeepSeek avaliado, temperatura 0, roteamento sem retenção e saída em JSON) classificando cada afirmação em "confere com a base", "contradiz a base" ou "não está na base" (com fallback determinístico offline);
  - calcula os 4 scores padronizados (`fidelidade_factual_rnf03`, `taxa_alucinacao`, `precisao_geoespacial_ra`, `sla_latencia_rnf14`) e as métricas da busca sem LLM (`recall_at_k`, `mrr`, `recusa_correta`, `recusa_indevida`);
  - registra os scores no trace ativo do Langfuse Cloud e remove de `simular_recuperacao_rag` (`src/telemetria/telemetria.py`) a nota fixa `fidelidade_rnf03_zero_alucinacao = 1.0`;
  - correção no rastreamento Langfuse (`src/rag/llm_pura.py`, `src/rag/llm_rag.py`, `src/rag/comparador_ab.py`): envio de `input` e `output` explícitos nas gerações e spans, eliminando traces vazios na web do Langfuse;
  - pipeline corporativo Haystack demonstrador em `src/rag/pipeline_haystack.py` (`InMemoryDocumentStore`, `InMemoryBM25Retriever`, `ChatPromptBuilder` e `GeradorOpenRouter`);
  - **269 testes passam** (`PYTHONPATH=. pytest tests`).
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
