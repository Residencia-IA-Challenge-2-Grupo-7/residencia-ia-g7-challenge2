# Manual de Continuação: DevOps, Docker no Ubuntu & Arquitetura RAG
**Projeto:** Orquestrador de Rolês (Challenge 2 — Residência em IA | Instituto Eldorado & UnB)  
**Data da Sessão:** 05/11/2026  
**Responsável:** Maria Eduarda (ML/LLMOps & DevOps)  
**Branch de Trabalho:** `feat/setup-docker-estrutura` (permanece nesta branch sem merge na `main`)

---

## 1. Resumo Executivo: O que fizemos hoje (05/11/2026)

1. **Estruturação Modular do Repositório:**
   - Organização padronizada do projeto dividindo código (`src/`), testes (`tests/`), documentação (`docs/`) e automação (`.github/`).
   - Criação dos módulos: `src/base/` (dados DF), `src/interpretador/` (RAG), `src/telemetria/` (observabilidade) e `src/main.py` (API FastAPI).
2. **Construção e Otimização do Docker:**
   - Criação do `Dockerfile` baseado em `python:3.12-slim`.
   - Instalação do `ffmpeg` no sistema operacional para suporte à transcrição de áudio.
   - Pulo do gato em DevOps: instalação do PyTorch em versão CPU-only (`--index-url https://download.pytorch.org/whl/cpu`), reduzindo a imagem de ~6 GB para menos de 800 MB.
   - Implementação de cache de camadas inteligente (dependências instaladas antes do código).
   - Criação de testes de sanidade com Pytest executando em apenas **0.59s**.
3. **Validação Local e Exposição de Portas:**
   - Teste de servidor web FastAPI com mapeamento de portas (`-p 8000:8000`) e documentação interativa Swagger em `/docs`.
4. **Deploy Contínuo na Nuvem (Render):**
   - Conexão do repositório GitHub com o Render no plano Free.
   - Publicação bem-sucedida do serviço em produção: [https://orquestrador-roles.onrender.com](https://orquestrador-roles.onrender.com).
   - Pull Request `#28` aberto e mergeado na `main`, ativando Auto-Deploy contínuo.

---

## 2. Decisões Arquiteturais: O que foi Decidido e o que foi Descartado

### A. O que foi DESCARTADO e por quê:
1. **Multi-stage build em Java/Maven (do tutorial da Kipper):**
   - *Motivo:* Python é interpretado e não compila `.jar`. Usamos uma imagem limpa e direta em estágio único com `python:3.12-slim`.
2. **Imagem Alpine Linux (`python:alpine`):**
   - *Motivo:* Falta de compatibilidade nativa com `glibc`, gerando erros críticos de compilação em bibliotecas de IA (PyTorch, NumPy, pgvector).
3. **PostgreSQL Gratuito do Render:**
   - *Motivo:* O Render apaga o banco gratuito após 30 dias. Como a residência dura 7 semanas (~50 dias), o banco seria destruído no meio do projeto.
4. **Hospedar modelos gigantescos (2 GB) localmente no Render Free:**
   - *Motivo:* O Render Free oferece apenas **512 MB de RAM**. Carregar modelos como `multilingual-e5-base` (~2 GB) causaria queda imediata por **OOM (Out Of Memory / Erro 137)**.

### B. O que foi DECIDIDO:
1. **A Base de Dados da Semana 2 (Scraping da Letícia):**
   - A Letícia auditou 164 vídeos de 2026 do TikTok (`@rolezandoembrasilia`), aplicou filtro cultural e geolocalização DF (2FA) e aprovou **93 rolês**.
   - Os 93 rolês e seus vetores de 3.072 dimensões (`gemini-embedding-001`) foram salvos em arquivo JSON: `data/banco_vetorial_embeddings.json` (~2,5 MB).
   - **Grande ganho:** Não dependemos de banco externo complexo para a busca inicial! O cálculo vetorial roda em memória RAM via **Similaridade de Cosseno com NumPy** em menos de 3ms.
2. **Estratégia de Nuvem e Transição:**
   - **Hoje / Provisório:** **Render Free** (roda a API leve em container consumindo ~120 MB de RAM).
   - **Semana que vem / Definitivo:** **DigitalOcean** usando os **$200 de crédito do GitHub Student Pack** (já aprovado em 03/11, liberando em 72h). Permitirá máquina de 2 GB a 4 GB de RAM sem modo soneca.
3. **Uso de IA por API:**
   - Consultas de LLM e embeddings feitas via API (Gemini/Groq), garantindo consumo de memória mínimo e altíssima velocidade.

---

## 3. Manual Completo: Como Instalar e Rodar o Docker no Ubuntu (Em Casa)

Como você estará no seu computador com **Linux Ubuntu**, siga este roteiro direto no terminal para preparar o ambiente:

### Passo 1: Atualizar o sistema e instalar dependências
Abra o terminal (`Ctrl + Alt + T`) e execute:
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y ca-certificates curl gnupg lsb-release git
```

### Passo 2: Adicionar a chave GPG oficial do Docker
```bash
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
```

### Passo 3: Adicionar o repositório oficial do Docker no Ubuntu
```bash
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
```

### Passo 4: Instalar o Docker Engine e o Docker Compose
```bash
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

### Passo 5: Permitir rodar o Docker sem precisar digitar `sudo` toda hora
*(Passo essencial de conforto e boas práticas de DevOps)*
```bash
sudo usermod -aG docker $USER
```
> **IMPORTANTE:** Para essa permissão entrar em vigor, **feche o terminal e abra novamente** (ou faça logoff e login no Ubuntu).

### Passo 6: Testar se a instalação do Docker no Ubuntu está OK
```bash
docker run hello-world
```
*(Deve exibir a mensagem clássica "Hello from Docker!").*

---

## 4. Como Baixar e Rodar o Nosso Projeto no Ubuntu de Casa

### 1. Clonar o repositório do projeto:
```bash
git clone https://github.com/Residencia-IA-Challenge-2-Grupo-7/residencia-ia-g7-challenge2.git
cd residencia-ia-g7-challenge2
```

### 2. Mudar para a branch de trabalho (sem misturar com a main):
```bash
git checkout feat/setup-docker-estrutura
git pull origin feat/setup-docker-estrutura
```

### 3. Construir a imagem Docker do projeto no Ubuntu:
```bash
docker build -t orquestrador-app .
```
*(Ele vai baixar o Python slim, o ffmpeg, o PyTorch CPU e as dependências).*

### 4. Executar os testes automatizados dentro do container:
```bash
docker run --rm orquestrador-app pytest
```
*(Deve passar 100% dos testes em menos de 1 segundo).*

### 5. Executar a API e testar no navegador (`localhost:8000`):
```bash
docker run --rm -p 8000:8000 orquestrador-app
```
Acesse no navegador:
- [http://localhost:8000](http://localhost:8000) (Status da API)
- [http://localhost:8000/docs](http://localhost:8000/docs) (Swagger interativo)

*(Para desligar o servidor, aperte `Ctrl + C` no terminal).*

---

## 4.1. Como Instalar e Rodar o Docker em Outros Macs (Apple Silicon e Intel)

Se você ou alguém do time for rodar em outro Mac:

1. **Baixar o Docker Desktop para Mac:**
   - Acesse: [https://www.docker.com/products/docker-desktop/](https://www.docker.com/products/docker-desktop/)
   - **Mac M1/M2/M3/M4 (Apple Silicon):** Escolha o instalador *"Mac with Apple chip"*.
   - **Mac antigo com processador Intel:** Escolha o instalador *"Mac with Intel chip"*.
2. **Instalação:**
   - Abra o arquivo `.dmg` baixado e arraste o ícone do Docker para a pasta **Aplicativos**.
   - Abra o Docker no Launchpad e aguarde o ícone da baleia parar de piscar no topo da barra de tarefas.
3. **No Terminal do Mac:**
   ```bash
   git clone https://github.com/Residencia-IA-Challenge-2-Grupo-7/residencia-ia-g7-challenge2.git
   cd residencia-ia-g7-challenge2
   git checkout feat/setup-docker-estrutura
   docker build -t orquestrador-app .
   docker run --rm orquestrador-app pytest
   ```

---

## 4.2. Como Instalar e Rodar o Docker no Windows (10 e 11)

Se alguém da equipe usa Windows, o Docker precisa do subsistema Linux (WSL 2) ativo:

1. **Instalar o WSL 2 (Subsistema Windows para Linux):**
   - Abra o **PowerShell como Administrador** e digite:
     ```powershell
     wsl --install
     ```
   - Reinicie o computador se for solicitado.
2. **Baixar e Instalar o Docker Desktop para Windows:**
   - Acesse: [https://www.docker.com/products/docker-desktop/](https://www.docker.com/products/docker-desktop/)
   - Baixe a versão para Windows e execute o instalador `.exe`.
   - Na tela de instalação, certifique-se de que a caixinha **"Use WSL 2 instead of Hyper-V (recommended)"** está marcada.
   - Conclua a instalação e reinicie o PC se necessário.
3. **No Terminal do Windows (PowerShell ou Git Bash):**
   ```bash
   git clone https://github.com/Residencia-IA-Challenge-2-Grupo-7/residencia-ia-g7-challenge2.git
   cd residencia-ia-g7-challenge2
   git checkout feat/setup-docker-estrutura
   docker build -t orquestrador-app .
   docker run --rm orquestrador-app pytest
   ```
4. **Para abrir no navegador do Windows:**
   ```bash
   docker run --rm -p 8000:8000 orquestrador-app
   ```
   Abra no Chrome/Edge: [http://localhost:8000](http://localhost:8000).

---

## 5. Roteiro para Amanhã: O que Falta para a Entrega da Semana 2

A sua tarefa oficial no GitHub é:  
**"Plataforma de monitoramento de RAG: configuração da infraestrutura de monitoramento, tracing, métricas de latência/custo e qualidade de recuperação do RAG (ML/LLMOps)."**

Com a infraestrutura de Docker e Deploy pronta, o foco de amanhã é a **Observabilidade com Langfuse**:

1. **Conta no Langfuse Cloud:**
   - Criar conta gratuita em [cloud.langfuse.com](https://cloud.langfuse.com) via login com GitHub.
   - Criar um projeto chamado `orquestrador-roles` e obter:
     - `LANGFUSE_PUBLIC_KEY`
     - `LANGFUSE_SECRET_KEY`
     - `LANGFUSE_HOST` (`https://cloud.langfuse.com`)
2. **Configuração de Segredos:**
   - Colocar essas chaves no arquivo `.env` local (fora do git) e no painel do Render (*Environment Variables*).
3. **Implementar a Telemetria (`src/telemetria/telemetria.py`):**
   - Configurar o decorador `@observe` para instrumentar a função de busca do RAG da Letícia (`banco_vetorial.py`).
4. **Métricas a Demonstrar no Painel:**
   - **Latência (RNF-14):** Medir tempo de geração do embedding + busca semântica no JSON em memória ($\le 5\text{ s}$).
   - **Custos/Tokens (RNF-15):** Acompanhar consumo de tokens no Gemini para caber no plano gratuito.
   - **Fidelidade (Zero Alucinação - RNF-03):** Garantir que os rolês retornados constam nos 93 itens auditados do TikTok.
5. **Ativação da DigitalOcean:**
   - Checar se o e-mail de aprovação dos $200 do GitHub Student Pack foi liberado (prazo de 72h vence entre 05/11 e 06/11).

---

## 6. Comandos para Salvar este Manual na Branch Atual

Para deixar este arquivo registrado na branch `feat/setup-docker-estrutura` e enviado para o GitHub (sem mexer na `main`), rode no terminal:

```bash
git add docs/MANUAL_DEVOPS_UBUNTU_E_CONTINUACAO.md
git commit -m "docs(infra): adiciona manual completo de docker no ubuntu e resumo de decisoes de arquitetura"
git push origin feat/setup-docker-estrutura
```
