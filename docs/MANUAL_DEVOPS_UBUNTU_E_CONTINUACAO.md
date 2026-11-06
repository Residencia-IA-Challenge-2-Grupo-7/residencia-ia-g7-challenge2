# Manual Completo de Engenharia: DevOps, Arquitetura RAG, Telemetria & Guia de Continuação
**Projeto:** Orquestrador de Rolês (Challenge 2 — Residência em IA | Instituto Eldorado & UnB)  
**Equipe:** Grupo 7  
- **Maria Eduarda (Duda):** DevOps, Infraestrutura, Cloud Deploy & ML/LLMOps  
- **Letícia Miti Takahashi:** Engenharia de Dados, Curadoria de Conteúdo & RAG  
**Atualização Consolidada:** 06/11/2026 (Sessões dos dias 05/11 e 06/11 integradas)  
**Branch de Trabalho:** `feat/setup-docker-estrutura`  
**Deploy em Produção:** [https://orquestrador-roles.onrender.com](https://orquestrador-roles.onrender.com)  
**Painel de Telemetria:** [Langfuse Cloud (Projeto cmw59be2y01d8ad0jqbgsjut6)](https://cloud.langfuse.com/project/cmw59be2y01d8ad0jqbgsjut6)

---

## 1. Visão Geral e Registro Cronológico das Sessões

### 1.1. O que foi feito na Sessão 1 (05/11/2026)
1. **Estruturação Modular Inicial:** Criação da divisão entre código (`src/`), testes (`tests/`), documentação (`docs/`) e automação (`.github/`).
2. **Containerização Docker Eficiente:** 
   - Criação do `Dockerfile` baseado em `python:3.12-slim`.
   - Instalação do pacote `ffmpeg` para processamento de áudio do Whisper.
   - Pulo do gato em DevOps: instalação do PyTorch em compilação CPU-only (`--index-url https://download.pytorch.org/whl/cpu`), derrubando o tamanho da imagem de ~6 GB para menos de 800 MB.
3. **Smoke Tests Rápidos:** Configuração de testes de sanidade com Pytest executando em menos de 0.6s.
4. **Primeiro Deploy no Render:** Conexão com o Render no plano Free (`orquestrador-roles.onrender.com`) com auto-deploy na `main`.

---

### 1.2. O que foi construído e concluído na Sessão 2 (06/11/2026)

#### A. Saneamento e Organização Arquitetural das Pastas
- **Problema Encontrado:** Arquivos de dados brutos e scripts haviam sido subidos via upload na pasta `docs/dados/`, gerando duplicatas e bagunça estrutural.
- **Solução Definitiva:**
  - `data/`: Armazena exclusivamente as bases de dados e embeddings (`banco_aprovado_2fa.json`, `banco_aprovado_2fa.csv`, `banco_vetorial_embeddings.json`, `banco_vetorial_embeddings.csv`, `catalogo_videos_2026.json`, `fila_quarentena_2fa.json`).
  - `src/rag/`: Módulos de código do RAG (`banco_vetorial.py`, `coletor_tiktok_2fa.py`, `prototipo_rag.py`, `__init__.py`).
  - `scripts/`: Scripts executáveis multiplataforma (`iniciar_mac_linux.sh` e `iniciar_windows.bat`).
  - `docs/entregas/semana-02/`: Pacote oficial de submissão do edital (`RELATORIO_TECNICO_RAG_GRUPO7.pdf`, `RELATORIO_TECNICO_RAG_SEMANA_02.md`, `DEMONSTRACAO_RAG_ENTREGAVEL.txt`, `Entregavel_Grupo7_Base_Conhecimento_e_RAG.zip`).
  - `docs/dados/`: Mantém **estritamente documentação metodológica** (`README.md`, `esquema-base.md`, `guia-curadoria.md`).

#### B. Frontend e Experiência de Usuário (`src/interface.py` e `src/main.py`)
- **Landing Page Minimalista (`GET /`):** Criada uma página inicial limpa e responsiva com o título em destaque **"Orquestrador de Rolês"**, subtítulo de Brasília e o botão de ação rápida **`Acessar RAG →`**, direcionando para `/rag`.
- **Roteamento Híbrido no `GET /`:** A rota raiz detecta o header `Accept`. Se a chamada for feita por robôs de monitoramento ou scripts (`Accept: application/json`), retorna o status em JSON; se for um navegador humano, entrega a Landing Page em HTML.
- **Interface Interativa do RAG (`GET /rag` e `GET /demo`):**
  - Barra de busca com atalhos de sugestão (*chips* de busca rápida: boteco na Asa Sul, café romântico na Asa Norte, lazer infantil domingo).
  - Cards de resultados com badges coloridas de categorias e vibes.
  - Link direto para assistir ao vídeo comprobatório no TikTok.
  - Botão com link dinâmico para inspecionar o Trace gerado no Langfuse Cloud em tempo real.
  - Botão **`← Voltar ao Início`** para navegação fluida.
  - Badge de aviso sobre a telemetria: *"O trace do Langfuse pode levar de 3 a 5 segundos para indexar no ClickHouse. Se clicar e disser que não encontrou, basta recarregar com F5."*

#### C. Observabilidade e ML/LLMOps (Langfuse Cloud v5.x)
- Instrumentação profunda em `src/telemetria/telemetria.py` utilizando o SDK oficial do Langfuse (`@observe(as_type="retriever")` e `@observe(as_type="generation")`).
- Registro em tempo real de scores automatizados vinculados ao trace:
  1. `fidelidade_rnf03_zero_alucinacao = 1.0`: Validação de que 100% dos locais sugeridos pertencem ao arquivo oficial `data/banco_aprovado_2fa.json`.
  2. `sla_latencia_rnf14 = 1.0`: Conformidade com o requisito de latência $\le 5.0\text{ s}$ (processamento real de 2.8 ms a 21.9 ms, operando com mais de 200x de margem).
  3. `qualidade_recuperacao_rag`: Similaridade semântica de cosseno média (entre 0.87 e 0.98).
- Rastreamento de tokens de entrada/saída e custos operacionais (\$0.000045 USD por consulta no Gemini 1.5 Flash).

#### D. Diagnóstico e Guardrail de Casos de Borda (Exemplo: "Balada após as 01h")
- **Diagnóstico da Consulta:** Quando um usuário buscou *"balada que fecha depois das 01h"*, o sistema retornou restaurantes infantis (Dona Cleide e Costella) com 50% de similaridade.
- **Causa Raiz Identificada:** A base curada da Letícia (extraída de vídeos de 2026 do `@rolezandoembrasilia`) foca em gastronomia diurna, bistrôs e passeios culturais, não tendo boates/baladas de alta madrugada. Sem palavras-chave reconhecidas, todos os locais empataram no score neutro de 50%.
- **Correção Implementada (Guardrail de Escopo):**
  - **Penalização Severa de Locais Infantis:** Estabelecimentos com tag `Kid Friendly`, parquinho ou brinquedoteca sofrem penalidade semântica quando o usuário busca termos noturnos (*balada, boate, 01h, madrugada*).
  - **Priorização de Horários Noturnos:** Locais com horário de funcionamento cadastrado que avança a madrugada (como o **New Mercadito**, aberto até 01h30 nas sextas e sábados) passam a liderar o ranking (Score 0.85).
  - **Resposta Transparente de Escopo:** Em vez de forçar sugestões inadequadas, a IA alerta explicitamente na resposta que a base foca em gastronomia e lazer no DF, e indica honestamente a opção noturna mais próxima cadastrada.

#### E. Engenharia do Relatório Técnico Oficial em PDF (LaTeX pdflatex)
- **Problema do Conversor Antigo (LibreOffice):** O LibreOffice headless apresentava instabilidade em listas aninhadas, quebrava tabelas no meio e deixava uma página órfã com apenas 2 a 3 linhas soltas.
- **Nova Solução com LaTeX (`pdflatex`):** 
  - Desenvolvido o gerador automatizado em Python/LaTeX (`scratch/gerar_pdf_clean.py`).
  - Diagramação executiva em **exatamente 4 páginas completas** (sem páginas sobrando, margens simétricas de 15mm/14mm, estilo de tabelas `booktabs` zebradas, caixas `tcolorbox` arredondadas e paginação *Página X de 4*).
  - Distribuição perfeita das 9 seções exigidas pelo edital do Challenge 2:
    - **Página 1:** Cabeçalho institucional, Seção 1 (Resumo Executivo e Checklist dos 8 Artefatos) e Seção 2 (Estratégia de Chunking com o Template Estruturado).
    - **Página 2:** Seção 3 (Estratégia de Embeddings de 3.072 dimensões com a equação formal de Cosseno), Seção 4 (Pipeline de Ingestão 2FA em card único) e Seção 5 (Arquitetura de Runtime RAG + Barra de Telemetria).
    - **Página 3:** Seção 6 (Telemetria, Scores RNF-03/RNF-14, Tabela dos 3 Casos de Teste Auditados, Análise Qualitativa e Governança de Custos RNF-15) e Seção 7 (Demonstração Online e via Terminal).
    - **Página 4:** Seção 8 (Preparação para a Semana 3 com Golden Dataset comparativo e Matriz de Guardrails) e Seção 9 (Conclusão e Tabela de Links de Acesso ao Ecossistema).

---

## 2. Mapa Arquitetural do Repositório

```text
residencia-ia-g7-challenge2/
├── .github/                       # Workflows de CI/CD (GitHub Actions)
├── data/                          # BASE DE DADOS OFICIAL E EMBEDDINGS (Semana 2)
│   ├── banco_aprovado_2fa.json    # 93 estabelecimentos aprovados na curadoria 2FA
│   ├── banco_aprovado_2fa.csv     # Versão tabular para auditoria rápida
│   ├── banco_vetorial_embeddings.json # 93 vetores densos de 3.072 dimensões (Gemini)
│   ├── banco_vetorial_embeddings.csv  # Vetores em formato CSV
│   ├── catalogo_videos_2026.json  # 164 vídeos brutos coletados do TikTok
│   ├── fila_quarentena_2fa.json   # 24 vídeos retidos por falta de endereço/preço
│   └── base/                      # Dados legados/apoio (lugares, regiões, eventos)
├── docs/                          # DOCUMENTAÇÃO E ENTREGAS PEDAGÓGICAS
│   ├── dados/                     # Documentação conceitual (README, esquema, guia)
│   ├── entregas/
│   │   ├── semana-01/             # Entregáveis da Semana 1 (Problema e Métricas)
│   │   └── semana-02/             # ENTREGÁVEIS OFICIAIS DA SEMANA 2
│   │       ├── RELATORIO_TECNICO_RAG_GRUPO7.pdf # Relatório formal em 4 páginas (LaTeX)
│   │       ├── RELATORIO_TECNICO_RAG_SEMANA_02.md # Versão markdown do relatório
│   │       ├── DEMONSTRACAO_RAG_ENTREGAVEL.txt # Log dos 4 passos de teste
│   │       └── Entregavel_Grupo7_Base_Conhecimento_e_RAG.zip # Pacote ZIP para o Teams
│   ├── arquitetura/               # Diagramas e documentação de sistema
│   ├── atas/                      # Atas de reunião da equipe
│   ├── decisoes/                  # Architecture Decision Records (ADRs 0001 a 0007)
│   └── MANUAL_DEVOPS_UBUNTU_E_CONTINUACAO.md # Este manual técnico de engenharia
├── scripts/                       # SCRIPTS DE INICIALIZAÇÃO MULTIPLATAFORMA
│   ├── iniciar_mac_linux.sh       # Script bash com setup automático de venv
│   └── iniciar_windows.bat        # Script batch para Windows
├── src/                           # CÓDIGO-FONTE DA APLICAÇÃO
│   ├── interface.py               # Frontend HTML/CSS responsivo (Landing + RAG UI)
│   ├── main.py                    # API FastAPI com rotas /, /rag, /health, /status
│   ├── rag/                       # MÓDULO RAG E VETORIZAÇÃO
│   │   ├── banco_vetorial.py      # Busca por Similaridade de Cosseno em memória
│   │   ├── coletor_tiktok_2fa.py  # Pipeline de curadoria e validação de 2 Fatores
│   │   └── prototipo_rag.py       # Demonstração CLI nos 4 passos com síntese LLM
│   ├── telemetria/                # MÓDULO DE OBSERVABILIDADE E LLMOPS
│   │   └── telemetria.py          # Instrumentação Langfuse, spans e cálculo de scores
│   ├── interpretador/             # Processamento de linguagem natural e intenção
│   └── voz/                       # Transcrição ASR (Whisper) e síntese de voz
├── tests/                         # TESTES AUTOMATIZADOS
│   └── test_smoke.py              # Smoke tests de ambiente, rotas e telemetria
├── Dockerfile                     # Imagem de produção otimizada (Python 3.12 + PyTorch CPU)
├── docker-compose.yml             # Orquestração local do container
├── requirements.txt               # Dependências Python travadas
└── STATUS.md                      # Quadro de estado atual do projeto
```

---

## 3. Guia de Execução Local: Como Rodar Tudo na Sua Máquina

### 3.1. Pré-requisitos
- Python 3.10 ou superior (recomendado Python 3.12).
- Git instalado e configurado.
- (Opcional, para testes com container) Docker Engine ou Docker Desktop.

### 3.2. Passo a Passo Rápido com Virtualenv (Sem Docker)

```bash
# 1. Clone o repositório
git clone https://github.com/Residencia-IA-Challenge-2-Grupo-7/residencia-ia-g7-challenge2.git
cd residencia-ia-g7-challenge2

# 2. Crie e ative o ambiente virtual
python3 -m venv .venv
source .venv/bin/activate  # No Windows: .venv\Scripts\activate

# 3. Instale as dependências
pip install --upgrade pip
pip install -r requirements.txt

# 4. Configure as variáveis de ambiente (crie um arquivo .env na raiz)
cat << 'EOF' > .env
ENVIRONMENT=desenvolvimento
LANGFUSE_PUBLIC_KEY="pk-lf-9a65474b-260e-43c3-87f6-ed088e989089"
LANGFUSE_SECRET_KEY="sk-lf-c5638e33-c322-44ec-a7fe-bdcf0981faea"
LANGFUSE_BASE_URL="https://cloud.langfuse.com"
# GEMINI_API_KEY="sua_chave_gemini_se_houver"
# GROQ_API_KEY="sua_chave_groq_se_houver"
EOF

# 5. Inicie a API e a Interface Web
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```
Acesse no navegador:
- **Landing Page:** [http://localhost:8000](http://localhost:8000)
- **Interface RAG:** [http://localhost:8000/rag](http://localhost:8000/rag)
- **Documentação Swagger:** [http://localhost:8000/docs](http://localhost:8000/docs)

---

### 3.3. Passo a Passo com Docker (Recomendado para Produção)

```bash
# Construir a imagem otimizada
docker build -t orquestrador-roles .

# Executar os testes automatizados dentro do container
docker run --rm orquestrador-roles pytest

# Rodar o servidor web na porta 8000
docker run --rm -p 8000:8000 \
  -e ENVIRONMENT=producao \
  -e LANGFUSE_PUBLIC_KEY="pk-lf-9a65474b-260e-43c3-87f6-ed088e989089" \
  -e LANGFUSE_SECRET_KEY="sk-lf-c5638e33-c322-44ec-a7fe-bdcf0981faea" \
  -e LANGFUSE_BASE_URL="https://cloud.langfuse.com" \
  orquestrador-roles
```

---

### 3.4. Como Rodar a Demonstração Oficial do RAG em Terminal (4 Passos do Edital)
Execute na raiz do projeto:
```bash
python3 src/rag/prototipo_rag.py
```
O script executará automaticamente:
1. **Passo 1:** Exibe a consulta submetida pelo usuário.
2. **Passo 2:** Exibe os Top-3 chunks recuperados com cálculo de similaridade de cosseno.
3. **Passo 3:** Exibe a resposta sintetizada citando `[FONTE #1]`, `[FONTE #2]`.
4. **Passo 4:** Exibe as evidências primárias (ID, coordenadas GPS, preço validado, transcrição do áudio Whisper e URL do TikTok).

---

## 4. Guia de Operação: Git, Branches e Deploy Contínuo no Render

### 4.1. Como funciona o Deploy no Render
- O serviço está conectado ao repositório GitHub e monitora a branch **`main`**.
- Cada `git push origin main` dispara automaticamente o pipeline:
  1. O Render puxa o commit mais recente.
  2. Executa o build da imagem Docker através do `Dockerfile`.
  3. Sobe o container executando `uvicorn src.main:app --host 0.0.0.0 --port $PORT`.
  4. Executa health check em `/health`. Se responder 200, substitui a versão antiga sem downtime.

### 4.2. Boas Práticas de Trabalho com Branches
Para manter o projeto organizado e evitar duplicatas:
1. **Nunca suba arquivos via interface web do GitHub ("Add files via upload"):** Isso quebra a estrutura de pastas e desfaz renomeações de arquivos.
2. **Desenvolvimento de Features:** Crie sempre branches a partir da `main`:
   ```bash
   git checkout main
   git pull origin main
   git checkout -b feat/nome-da-sua-tarefa
   ```
3. **Para Enviar para Produção:**
   Faça commit local, envie a branch para o GitHub e abra um Pull Request para a `main`. Uma vez aprovado e mergeado, o Render atualiza o site público em 2 minutos.

---

## 5. Roteiro de Continuação: Preparação para a Semana 3 e Além

### 5.1. O Foco da Semana 3: Comparação LLM Pura vs. RAG (Respostas com Evidências)
Na Semana 3, o requisito pedagógico principal é **comprovar empiricamente que o RAG supera a LLM pura (sem contexto) na eliminação de alucinações e precisão geoespacial no DF**.

#### Roteiro Técnico para a Semana 3:
1. **Benchmark com Golden Dataset (10 Perguntas):**
   - Utilizar as 10 perguntas planejadas na Seção 8 do relatório técnico.
   - Exemplos de perguntas que forçam alucinação na LLM pura:
     - *"Onde fica a quadra comercial da Spelunca DF e qual o prato principal?"* (A LLM pura costuma inventar quadras ou confundir com estabelecimentos de São Paulo).
     - *"Qual o valor do rodízio no Dona Cleide em Águas Claras?"* (A LLM pura erra o valor exato em reais).
     - *"O que fazer de graça no domingo em Brasília com crianças?"* (A LLM pura recomenda locais genéricos, enquanto o RAG ancora no Eixão do Lazer com tags `Kid Friendly` e dados auditados).
2. **Mecanismo Comparativo A/B:**
   - Criar uma rota ou script que envie a mesma pergunta para:
     - **Modo A (LLM Pura):** Gemini 1.5 Flash com prompt zero-shot sem contexto de documentos.
     - **Modo B (RAG Ancorado):** Gemini 1.5 Flash com os Top-3 Chunks injetados no prompt de sistema.
3. **Auditoria Automatizada via LLM-as-a-Judge no Langfuse:**
   - Instrumentar uma função avaliadora no Langfuse que receba as duas saídas e atribua notas automatizadas:
     - `factual_accuracy_score` (0.0 a 1.0);
     - `hallucination_rate` (percentual de fatos inventados);
     - `address_grounding_score` (endereço verificado no DF).

---

### 5.2. O Foco da Semana 4 e 5: Multiagentes e Multimodalidade
- **Semana 4 (Multiagentes):** Dividir a inteligência em agentes especializados (ex.: *Agente Especialista em Gastronomia*, *Agente de Restrições Orçamentárias*, *Agente de Roteiros Geoespaciais*).
- **Semana 5 (Multimodalidade):** Integrar a análise visual das thumbnails dos vídeos do TikTok e áudio de voz com Whisper local/Groq para que o usuário possa falar por áudio na interface web.

---

### 5.3. Transição de Infraestrutura: Render Free $\rightarrow$ DigitalOcean
- Como os créditos de \$200 do **GitHub Student Pack** foram aprovados, planejar a migração da aplicação para um Droplet (Ubuntu 24.04 com 2 GB ou 4 GB de RAM) na DigitalOcean nas semanas 4 ou 5.
- Isso eliminará o modo soneca do Render Free e permitirá rodar modelos locais mais pesados de embedding e ASR se necessário.

---

## 6. Checklist de Arquivos para Submissão da Semana 2 no Teams

Os 3 arquivos oficiais prontos para envio no canal da Residência estão salvos na pasta [`docs/entregas/semana-02/`](docs/entregas/semana-02/):
1. **`RELATORIO_TECNICO_RAG_GRUPO7.pdf`:** Relatório formal consolidado de 4 páginas gerado em LaTeX (`pdflatex`).
2. **`DEMONSTRACAO_RAG_ENTREGAVEL.txt`:** Log de execução integral dos 4 passos de validação do RAG.
3. **`Entregavel_Grupo7_Base_Conhecimento_e_RAG.zip`:** Pacote ZIP contendo os datasets, scripts de execução e relatórios.

---
*Manual mantido e versionado pela equipe de Engenharia e DevOps do Grupo 7.*
