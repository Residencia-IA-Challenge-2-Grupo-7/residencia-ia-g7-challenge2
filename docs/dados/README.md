# Documentação de Dados & Base de Conhecimento
**RES IA ELD UNB - Turma 2 | Grupo 7 — Orquestrador de Rolês (Brasília/DF)**

Este diretório contém as **especificações conceituais, schemas e diretrizes de curadoria** que orientam a modelagem e validação dos dados de gastronomia e lazer no Distrito Federal.

---

## 1. Conteúdo Deste Diretório

| Documento | Descrição |
| :--- | :--- |
| **[`esquema-base.md`](esquema-base.md)** | Especificação do esquema de dados dos estabelecimentos, tipos de rolês permitidos, regras de geolocalização por Região Administrativa (RA) e categorização de preços. |
| **[`guia-curadoria.md`](guia-curadoria.md)** | Diretrizes metodológicas de curadoria, protocolo de dupla validação (2 Fatores - 2FA) e critérios de descarte (propagandas) e quarentena (dados incompletos). |
| **[`golden-dataset-semana3.md`](golden-dataset-semana3.md)** | Golden dataset da Semana 3: as 20 perguntas com gabarito ancorado na base 2FA, as regras do gabarito e as decisões de cada parte, usados na comparação RAG vs. IA pura. |

---

## 2. Onde Encontrar os Arquivos Relacionados no Projeto

* **Arquivos de Dados Brutos e Vetoriais:**  
  Estão localizados na pasta raiz **[`data/`](../../data/)** (`banco_aprovado_2fa.json`, `banco_vetorial_embeddings.json`, planilhas `.csv`, etc.).
* **Scripts de Ingestão e Busca Vetorial:**  
  Estão implementados no módulo **[`src/rag/`](../../src/rag/)** (`coletor_tiktok_2fa.py`, `banco_vetorial.py`, `prototipo_rag.py`).
* **Relatório Oficial da Semana 2:**  
  A entrega técnica consolidada com métricas de RAG e telemetria encontra-se em **[`docs/entregas/semana-02/`](../entregas/semana-02/)**.
