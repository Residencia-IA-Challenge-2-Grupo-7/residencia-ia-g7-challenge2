# Status do projeto

> Arquivo vivo. Toda sessão (humana ou de agente) lê no início e atualiza no fim.
> Mantenha curto: o histórico fica em `docs/semanas/` e no `git log`.

**Atualizado em:** 2026-11-03
**Semana do roadmap:** 2 — Base de conhecimento e recuperação (datas a confirmar)

## Agora

- **Ideia escolhida: Orquestrador de Rolês**, com o Modo Descoberta ([ADR 0001](docs/decisoes/0001-escolha-do-orquestrador-de-roles.md)). Visão, diferenciais, concorrentes, decisões em aberto e riscos: [docs/produto/visao.md](docs/produto/visao.md).
- **Recorte do MVP: só o modo com amigos.** Modo Descoberta, videogames e versão para menores ficam para depois ([ADR 0002](docs/decisoes/0002-recorte-do-mvp.md)). Canal proposto: app web próprio ([ADR 0003](docs/decisoes/0003-canal-app-web.md), a confirmar com o grupo).
- **Requisitos v0.3** em [docs/produto/requisitos.md](docs/produto/requisitos.md): 46 RF e 16 RNF, com cenários no estilo OpenSpec e colunas Persona e Riscos (R-NN) preenchidas. Sincronizados com o documento da equipe em 03/11. Falta a revisão do grupo.
- **Fonte da base do RAG** ([ADR 0004](docs/decisoes/0004-fonte-e-manutencao-da-base.md), aceita na versão 2, depois da [crítica](docs/decisoes/revisoes/0004-critica.md)):
  - candidatos da Overture e curadoria humana de horário e preço;
  - Google Places só para conferir os finalistas na hora do plano, sob cinco condições dos termos: sem mapa não Google, só o place ID guardado, nada exibido nem lido em voz, nada na avaliação LLM × RAG, sem benchmark público;
  - TomTom medida no piloto;
  - meta de lugares derivada das horas, com teto de 200;
  - aceite pelo teste de cobertura por região e por faixa de orçamento.
  Esquema e guia em [docs/dados/](docs/dados/).
- **Coleta automática e base vetorial** ([ADR 0005](docs/decisoes/0005-coleta-automatica-e-base-vetorial.md), proposta): substitui a curadoria humana do ADR 0004.
  - Robô nos sites oficiais e nas agendas, com extração por LLM e evidência literal conferida por código; nenhum campo é digitado por uma pessoa.
  - Rodada semanal (eventos duas vezes por semana).
  - PostgreSQL com pgvector, busca híbrida e embeddings BGE-M3 locais.
  - Limitação principal: lugares sem site ficam fora, o que pode concentrar a base no centro.
  **Próximos passos da base:** pedidos de teste, Postgres com pgvector em Docker e etapas 1 a 5 do pipeline com 100 candidatos na semana 2. O grupo responde às perguntas dos ADRs 0004 e 0005 (conta de faturamento, plano sem mapa embutido, lugares sem site, e-mail do robô, provedor de LLM da extração).
- **Mapa da arquitetura atualizado** com os ADRs 0004 e 0005 (coleta automática, PostgreSQL com pgvector, Google só para conferir finalistas). **Falta publicar** no repositório público com `publicar.sh`.
- **Relatório da semana 1** (até 5 páginas de texto, ABNT): [relatorio-semana-01.docx](docs/entregas/semana-01/relatorio-semana-01.docx) e o [PDF](docs/entregas/semana-01/relatorio-semana-01.pdf), montados conforme o [plano](docs/entregas/semana-01/plano-relatorio.md) e alinhados ao documento da equipe revisado (46 RF, riscos renumerados, sem piloto). 5 páginas de texto, com cerca de 1,5 cm de folga. As partes da equipe estão no [documento do grupo](https://docs.google.com/document/d/1mlxgJ9XoadAl4qKV28bw6qexQxF6xpwcSx5aENsRPF4/edit?tab=t.mm6pfcuj8dpt#heading=h.tyssdhkqxqfd) (Google Docs).
- **Mapa da arquitetura planejada** (pedido do mentor Isaque): [docs/arquitetura/index.html](docs/arquitetura/index.html), publicado em [residencia-ia-challenge-2-grupo-7.github.io/residencia-ia-g7-arquitetura](https://residencia-ia-challenge-2-grupo-7.github.io/residencia-ia-g7-arquitetura/). O site fica num repositório público à parte, porque o plano gratuito da organização não tem Pages em repositório privado. Como editar e publicar: [docs/arquitetura/AGENTS.md](docs/arquitetura/AGENTS.md).
- Formulário curto "Pesquisa de Hábitos Sociais" (15 afirmações) em uso para validar a dor. A versão completa fica como referência em [docs/pesquisa/](docs/pesquisa/).
- Repositório na organização do grupo: [Residencia-IA-Challenge-2-Grupo-7](https://github.com/Residencia-IA-Challenge-2-Grupo-7/residencia-ia-g7-challenge2) (privado).

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

- Revisar a v0.3 com o grupo, principalmente as escolhas de comportamento de 29/10 e a seção "Questões em aberto" do documento.
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

## Integrantes

Papéis definidos em 29/10 ([ata](docs/atas/2026-10-29.md)); a divisão mais detalhada (DevOps, UX/UI e front-end, back-end, testes, engenharia de IA) segue em discussão.

- Cauan Soares: Arquiteto da Solução
- Letícia Miti: Cientista de Dados
- Maria Carolina: Engenheira de Dados
- Maria Eduarda: ML/LLMOps
- Samara Letícia: Engenheira de Dados
