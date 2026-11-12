# Status do projeto

> Arquivo vivo. Toda sessão (humana ou de agente) lê no início e atualiza no fim.
> Mantenha curto: o histórico fica em `docs/semanas/` e no `git log`.

**Atualizado em:** 2026-11-10
**Semana do roadmap:** 3 — Comparação RAG × LLM pura, com as Telas 1 a 3 do app em paralelo

## Agora

- **Fonte da verdade sobre o app: [GUIA_OFICIAL_PROJETO.md](GUIA_OFICIAL_PROJETO.md)** (10/11). Resumo do que ele fechou:
  - ciclo completo do rolê: sala, 4 campos secretos, 3 a 4 cartões, votação múltipla e, depois, foto da nota fiscal, divisão e Pix;
  - **sem voz** ([ADR 0009](docs/decisoes/0009-entrada-pelos-4-campos-de-texto.md)); a multimodalidade da semana 5 é a foto da nota fiscal;
  - **base oficial de 93 lugares** do TikTok com validação em 2 fatores ([ADR 0008](docs/decisoes/0008-base-2fa-de-93-lugares-e-lgpd.md)); `src/base/` (Overture) e `src/voz/` saíram do repositório, e os ADRs 0005 e 0006 ficaram como substituídos;
  - distância e transporte pelas 35 RAs com a regra da Menor Miséria; banco das salas no Supabase.
  - As tarefas da semana de cada integrante estão na seção 4 do guia.
- **Back-end das salas (Cauan, 10/11), na branch `feat/salas-backend`:**
  - `src/interpretador/campos.py`: os 4 campos viram RA (apelidos, quadras como SQN e QNM, estações de metrô), janelas pelo `tempo.py`, teto pelo `numeros.py` e tags com os rótulos da base. Tudo por regras; o LLM do ADR 0007 só entra se as regras não acharem nenhum dia ([ADR 0009](docs/decisoes/0009-entrada-pelos-4-campos-de-texto.md));
  - `src/state.py` (repositório em memória, pronto para trocar pelo Supabase) e `src/salas/` (gerenciador, cruzamento de horários, horário de funcionamento dos lugares, cartões, votação);
  - rotas em `/api/salas`: criar, painel, participantes (entrar, corrigir, confirmar, própria visão), gerar sugestões, votar e fechar votação. Contrato e exemplo em [src/salas/README.md](src/salas/README.md);
  - **110 testes passam** (`python -m pytest tests`), entre eles o fluxo de 3 participantes da issue #43 (`tests/test_salas_backend.py`) e uma varredura das respostas públicas atrás do teto de cada um; o CI e o `make test` passaram a rodar todos os testes;
  - códigos de sala no formato `ROLE-7KQ2`; PR aberto para fechar a issue #43.
- **Encaixes pendentes** (o código usa uma reserva simples até chegarem; assinaturas em [src/salas/README.md](src/salas/README.md#encaixe-das-peças-das-colegas)):
  - Eduarda: `teto_seguro_grupo` em `src/financas/` e um `Repositorio` do Supabase em `src/db/`;
  - Samara: **entregue na issue #44** (`estimar_deslocamento`, `nota_menor_miseria` e `calcular_score_justica_espacial` em `src/logistica/transporte_df.py`, pontos das 35 RAs em `data/regioes_df_gps.json`); as salas já usam o módulo no lugar da reserva. Regra, números e pendências no [ADR 0012](docs/decisoes/0012-deslocamento-e-menor-miseria.md);
  - Letícia: a busca com filtros, que hoje entra pela `calcular_similaridade_leticia`;
  - Maria Carolina: as Telas 1 a 3 chamando as rotas acima (tokens no cabeçalho `X-Token`).
- **Problemas achados na base** (para a Letícia, registrados no [ADR 0008](docs/decisoes/0008-base-2fa-de-93-lugares-e-lgpd.md#riscos-e-limitações)):
  - os 2 eventos do Gama têm coordenadas no Plano Piloto, e o lugar de Planaltina não tem coordenadas;
  - 14 itens são eventos ou promoções com datas que já passaram e saem das sugestões;
  - 21 lugares só dizem "Consultar no local".
- **Risco aberto:** os termos do TikTok e o direito autoral do perfil de origem. O app mostra só fatos curtos e o link do vídeo; para uso além do acadêmico, pedir permissão por escrito ao autor.
- **Requisitos v0.4** em [docs/produto/requisitos.md](docs/produto/requisitos.md): voz removida (RF-39, RF-40), 4 campos no lugar da conversa privada, votação múltipla. A revisão completa com o grupo continua pendente.
- **Mapa da arquitetura** atualizado com o guia oficial (base de 93, 4 campos, sem voz, Supabase, salas e pós-rolê) em [docs/arquitetura/index.html](docs/arquitetura/index.html). **Falta publicar** com `publicar.sh`.
- **Plano do MVP navegável** ([docs/produto/plano-mvp.md](docs/produto/plano-mvp.md), rascunho local, fora do git): propõe Jinja2 + HTMX e voz, o que o guia oficial mudou. Revisar antes de usar.
- Histórico da semana 2 (pipeline da Overture, voz, interpretador medido com 97,1% no RNF-08): [docs/semanas/semana-02.md](docs/semanas/semana-02.md) e [docs/experimentos/](docs/experimentos/2026-11-05-voz-e-interpretador.md).
- Relatórios: semana 1 em [docs/entregas/semana-01/](docs/entregas/semana-01/), semana 2 em [docs/entregas/semana-02/](docs/entregas/semana-02/).
- Mapa da arquitetura publicado em [residencia-ia-challenge-2-grupo-7.github.io/residencia-ia-g7-arquitetura](https://residencia-ia-challenge-2-grupo-7.github.io/residencia-ia-g7-arquitetura/); como editar: [docs/arquitetura/AGENTS.md](docs/arquitetura/AGENTS.md).
- Repositório na organização do grupo: [Residencia-IA-Challenge-2-Grupo-7](https://github.com/Residencia-IA-Challenge-2-Grupo-7/residencia-ia-g7-challenge2) (privado).

## Próximos passos (Cauan, conforme o guia)

- Hoje: issue #33 (LLM pura e guardrails do RAG), que destrava a #34.
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
