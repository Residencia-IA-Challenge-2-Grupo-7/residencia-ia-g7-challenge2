# Orquestrador de Rolês — Documentação Oficial

<p align="center">
  <img src="https://img.shields.io/badge/Residência%20em%20IA-Eldorado%20%7C%20UnB-blueviolet?style=for-the-badge" alt="Residência IA" />
  <img src="https://img.shields.io/badge/Challenge-2-orange?style=for-the-badge" alt="Challenge 2" />
  <img src="https://img.shields.io/badge/Status-Semana%204%20Concluída-success?style=for-the-badge" alt="Status" />
  <img src="https://img.shields.io/badge/Python-3.12-blue?style=for-the-badge&logo=python" alt="Python" />
  <img src="https://img.shields.io/badge/LangGraph-Multiagente-purple?style=for-the-badge" alt="LangGraph" />
</p>

Bem-vindo ao portal de documentação e engenharia do **Orquestrador de Rolês**, desenvolvido pelo **Grupo 7** no âmbito da **Residência em Inteligência Artificial** (parceria entre o **Instituto de Pesquisas Eldorado** e a **Universidade de Brasília — UnB**), seguindo a metodologia *Challenge-Based Learning (CBL)*.

---

## 🎯 Contexto e Propósito

* **Big Idea:** Qualidade de Vida e Bem-Estar Social no Distrito Federal.
* **Essential Question:** *"Como sistemas de IA podem ajudar amigos a transformar a vontade de se encontrar em encontros reais, de forma justa para todos?"*
* **O Problema:** Planos de encontro que morrem por fadiga de decisão, assimetria logística de deslocamento entre o Plano Piloto e as demais Regiões Administrativas periféricas do DF, e pelo constrangimento social de expor restrições financeiras e alimentares individuais.
* **A Solução:** Um ecossistema **multiagente autônomo** baseado em **LangGraph** e ferramentas determinísticas em Python, orquestrando preferências anônimas, checagem factual em vídeos reais do TikTok (curadoria 2FA) e aplicando o princípio da **Menor Miséria** espacial.

---

## 🏛️ Pilares da Arquitetura

1. **🔒 Sigilo Absoluto e Cofre de Dados Privados (`RNF-02`):** Orçamentos individuais, endereços exatos e restrições pessoais nunca entram no estado compartilhado nem chegam aos prompts públicos de LLM.
2. **⚖️ Justiça Espacial pela Menor Miséria (`ADR 0013`):** Algoritmo logístico determinístico que calcula tempos de trajeto por ônibus, metrô e app nas 35 RAs do DF, priorizando opções que minimizem o cansaço do membro mais distante.
3. **🎯 Grounding Estrito em 2 Fatores (`RNF-03`):** Zero alucinação — candidatos extraídos exclusivamente da base curada de 93 locais oficiais com evidência em vídeo no TikTok.
4. **🧑‍⚖️ Avaliação Factual com Juiz LLM em 2 Passagens (`ADR 0014`):** LLM avaliador semântico auditando a pesquisa contra contradições e os cartões finais contra qualquer vazamento de dados.
5. **📡 Telemetria e Tracing Canônico (`ADR 0015` / `RNF-10`):** Spans explícitos no Langfuse Cloud medindo tokens, latência p90 e custo em USD de cada nó do fluxo.

---

## 🚀 Acessos Rápidos & Links Úteis

| Recurso | Descrição | Link de Acesso |
| :--- | :--- | :--- |
| **Código-Fonte** | Repositório oficial no GitHub com branches, testes e CI | [github.com/Residencia-IA-.../residencia-ia-g7-challenge2](https://github.com/Residencia-IA-Challenge-2-Grupo-7/residencia-ia-g7-challenge2) |
| **Langfuse Cloud** | Painel de observabilidade, métricas e tracing dos agentes | [cloud.langfuse.com](https://cloud.langfuse.com) |
| **Aplicação Web (Render)** | Sistema em nuvem com salas, interface RAG e API | [orquestrador-roles.onrender.com](https://orquestrador-roles.onrender.com) |
| **Diagrama do Grafo** | Visualização interativa e SVG do grafo multiagente | [Ver Diagrama](arquitetura/multiagente.md) |

---

## 👥 Integrantes da Equipe (Grupo 7)

Tabela 1: Integrantes da equipe e áreas de atuação

| Integrante | Papel Principal | GitHub |
| :--- | :--- | :--- |
| **Cauan Soares** | Arquitetura da Solução & Orquestração Multiagente (LangGraph) | [@cadasiso](https://github.com/cadasiso) |
| **Letícia Miti Takahashi** | Engenharia de Dados, Curadoria de Conteúdo & RAG | [@mitii05](https://github.com/mitii05) |
| **Maria Carolina** | Front-End, Design de Interação (UI/UX) & Diagramas | [@mcznh](https://github.com/mcznh) |
| **Maria Eduarda (Duda)** | DevOps, Infraestrutura Cloud, Avaliação & LLMOps | [@eduarda-ogomes](https://github.com/eduarda-ogomes) |
| **Samara Letícia** | Engenharia de Dados & Logística Geoespacial (DF) | [@samarawwleticia](https://github.com/samarawwleticia) |

---

## 📅 Fases e Entregas Semanais

Tabela 2: Resumo das entregas de cada semana do Challenge 2

| Semana | Escopo & Entregáveis Principais | Status |
| :---: | :--- | :---: |
| **Semana 01** | Definição da Big Idea, Essência do Problema, Pesquisa com Usuários, MVP e Configuração do Ambiente Docker. | <span style="color:#2da44e;font-weight:bold;">Concluída</span> |
| **Semana 02** | Base curada de 93 locais em 2 Fatores (TikTok + Metadados), Pipeline de RAG e Central de Entregáveis. | <span style="color:#2da44e;font-weight:bold;">Concluída</span> |
| **Semana 03** | Golden Dataset de 20 perguntas, Benchmark comparativo A/B (LLM Pura vs. RAG) e Relatório Técnico ABNT. | <span style="color:#2da44e;font-weight:bold;">Concluída</span> |
| **Semana 04** | Grafo Multiagente no LangGraph (5 Agentes), Juiz LLM, Observabilidade no Langfuse e Demonstração CLI. | <span style="color:#2da44e;font-weight:bold;">Concluída</span> |

---

## 📝 Histórico de Versões do Portal

Tabela 3: Histórico de versões do portal de documentação

| Versão | Data | Descrição das Alterações | Autor(es) | Revisor(es) |
| :---: | :---: | :--- | :--- | :--- |
| `1.0` | 10/11/2026 | Estruturação inicial do MkDocs Material, padrões de contribuição e templates. | [@eduarda-ogomes](https://github.com/eduarda-ogomes) | [@cadasiso](https://github.com/cadasiso) |
| `1.1` | 12/11/2026 | Inclusão da documentação da base de dados e catálogo do Golden Dataset da Semana 3. | [@samarawwleticia](https://github.com/samarawwleticia) | [@eduarda-ogomes](https://github.com/eduarda-ogomes) |
| `1.2` | 17/11/2026 | Adição da especificação da arquitetura do grafo multiagente e diagrama visual SVG. | [@mcznh](https://github.com/mcznh) | [@cadasiso](https://github.com/cadasiso) |
| `2.0` | 20/11/2026 | Reformulação visual completa no padrão Parnas/Karen Jones: abas superiores, catálogo de 16 ADRs, semanas 1 a 4 e telemetria. | [@eduarda-ogomes](https://github.com/eduarda-ogomes) | [@cadasiso](https://github.com/cadasiso) |
