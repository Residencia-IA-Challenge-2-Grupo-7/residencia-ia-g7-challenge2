# 🚀 GUIA OFICIAL DO PROJETO — ORQUESTRADOR DE ROLÊS (GRUPO 7)

**Última atualização:** 10/11/2026 (Semana 3 do Challenge 2)  
**Status:** Documento Oficial Único na `main` (Substitui versões antigas e unifica toda a equipe)

---

## 1. O Que É o Nosso Aplicativo (Definição Oficial e Definitiva)

O **Orquestrador de Rolês** é um aplicativo web pensado para celular e computador que resolve o problema de grupos de amigos no **Distrito Federal (DF)** que querem sair juntos, mas travam na hora de combinar horário, local, distância e dinheiro.

### Decisões Oficiais Fechadas pelo Grupo:

1. **Ciclo Completo do Rolê (Início, Meio e Pós-Rolê):**
   - O aplicativo resolve **antes do rolê** (criar sala, coletar preferências em segredo, sugerir 3 a 4 lugares reais e fazer a votação) **e depois do rolê** (subir foto da nota fiscal/comanda, dividir a conta entre quem foi e gerar o código Pix copia e cola para ninguém ficar no prejuízo).
2. **Sem Áudio / Sem Microfone:**
   - **Não usaremos entrada ou saída por voz.** Tudo o que o usuário informa é **por texto** ou **por foto da nota fiscal**.
   - A exigência de **Multimodalidade (Semana 5)** do curso será cumprida 100% pela **leitura de imagem da Nota Fiscal / Comanda do restaurante** junto com texto.
3. **Como o Usuário Informa seus Dados (Os 4 Campos de Texto em Segredo):**
   - Nada de formulário cheio de caixinhas por bairro (o DF funciona por Regiões Administrativas, quadras e pontos de referência) e nada de bate-papo longo com robô.
   - Ao entrar na sala, a pessoa preenche **4 campos de texto simples e secretos**:
     1. **De onde você vai sair no DF?** *(Ex: "Águas Claras perto da estação", "Asa Norte 408", "Ceilândia Centro")*
     2. **Quais dias e horários você pode?** *(Ex: "Sexta depois das 19h ou sábado à tarde")*
     3. **Qual seu limite máximo de gasto em R$?** *(Ex: "60" — 100% secreto, ninguém da sala vê)*
     4. **O que você anima fazer e como vai?** *(Ex: "Barzinho ou café calmo, sou vegetariana, vou de metrô/Uber")*
4. **Base Oficial Única de Lugares (`data/banco_aprovado_2fa.json`):**
   - A base oficial do projeto é a **lista da Miti com 93 lugares reais do DF** (extraídos e validados em 2 etapas a partir de vídeos reais do DF, com preços, horários, coordenadas GPS e links comprobatórios).
   - As pastas antigas de testes descartados (`src/base/` da Overture e `src/voz/`) foram **apagadas do repositório** para manter o código limpo.
5. **Cálculo de Distância e Transporte no DF (100% Grátis):**
   - Calculamos a distância (km), o tempo estimado (carro vs. ônibus/metrô) e o custo de passagem cruzando as **35 Regiões Administrativas do DF** com o **GPS dos 93 lugares da Miti**, sem depender de chave paga ou cartão de crédito no Google Maps.
   - Usamos a regra da **"Menor Miséria"**: o sistema protege quem tem menos dinheiro e quem mora mais longe do Plano Piloto.
6. **Banco de Dados Oficial na Nuvem (Supabase / PostgreSQL):**
   - Todas as salas criadas, participantes, respostas secretas dos 4 campos, votos e contas divididas ficam salvos em um banco **PostgreSQL gratuito na nuvem (Supabase)**, acessível por toda a equipe via `.env`.

---

## 2. As 4 Telas do Aplicativo Completo (O Que Vamos Construir)

Para o aplicativo estar 100% pronto e funcional até a Semana 6, o sistema terá **4 telas principais** (além da página `/rag` e `/entregaveis` que já mostramos aos monitores):

### 📱 Tela 1: Criar ou Entrar na Sala (`/app`)
- O organizador digita seu nome, dá um nome para o rolê (ex: *"Aniversário da Galera"*) e clica em **Criar Sala**.
- O sistema gera um **Link/Código de Convite** (ex: `/sala/ROLE123`) para mandar no WhatsApp do grupo (de 2 a 20 amigos, todos 18+).

### 🔒 Tela 2: Meus Dados Secretos (`/sala/{codigo}/perfil`)
- Cada amigo que abre o link preenche os **4 campos de texto** (Onde está no DF, Dias/Horários livres, Limite de gasto em R$ em segredo e O que quer fazer/transporte).
- O sistema lê os 4 campos, mostra na tela o resumo do que entendeu (*"Sábado das 18h às 23h, saindo de Águas Claras, teto de R$ 60"*) e a pessoa clica em **Confirmar em Segredo**.

### 🗳️ Tela 3: Painel da Sala e Votação nos 3 a 4 Cards (`/sala/{codigo}`)
- Mostra quem já preencheu os dados secretos (sem nunca mostrar o dinheiro de ninguém!).
- Quando todos preenchem (ou o organizador clica em *"Gerar Sugestões"*), o sistema cruza os horários, respeita o menor orçamento do grupo, calcula a distância no DF e exibe **3 a 4 Cartões de Sugestão de Rolê**.
- Cada cartão mostra: **Nome do lugar, Região Administrativa, Endereço, Dia e Horário sugerido, Faixa de gasto (consumo + transporte), Tempo médio de chegada, Link do vídeo no TikTok e Explicação de por que é justo para o grupo**.
- Os amigos podem votar em uma ou mais opções (**Votação Múltipla**).
- Quando a votação fecha, aparece o aviso oficial: **"🎉 Rolê orquestrado com sucesso!"**, com botão de **Copiar Resumo para o WhatsApp** e **Adicionar na Agenda**.

### 🧾 Tela 4: Pós-Rolê — Nota Fiscal, Divisão da Conta e Pix (`/sala/{codigo}/conta`)
- Depois do encontro, quem pagou a conta pode **enviar a foto da Nota Fiscal / Comanda** (ou digitar o valor e os itens) e informar sua **Chave Pix**.
- A IA lê a foto da nota fiscal, divide o valor entre os amigos presentes (permitindo desmarcar quem não consumiu algum item) e gera automaticamente o **Código Pix Copia e Cola (padrão Banco Central)** com o valor exato de cada um.
- Cada amigo clica em *"Copiar código Pix"* e marca como **"Já paguei"**; ao final, dá uma nota de 1 a 5 dizendo se o preço e o horário do lugar bateram com o esperado.

---

## 3. Como Cada Semana do Curso Se Encaixa no Nosso Projeto

| Semana | Entregável para os Monitores | O Que Construímos do Nosso Aplicativo |
| :--- | :--- | :--- |
| **Semana 1** *(Feita)* | Definições do projeto, personas, riscos e métricas | Escolha do Orquestrador de Rolês e requisitos base |
| **Semana 2** *(Feita)* | Primeiro mecanismo RAG | Base de 93 lugares do DF, busca semântica, Langfuse e deploy no Render |
| **Semana 3** *(AGORA)* | **Comparação RAG vs. IA Pura (Respostas com Evidências)** | **Banco na Nuvem (Supabase) + Telas 1, 2 e 3 + Rotas de Sala/Votação + Cálculo de Transporte DF + Calculadora Pix** |
| **Semana 4** | Primeiro sistema Multiagentes | Conectar os Agentes especialistas (Intérprete dos 4 campos, Buscador RAG, Calculador de Rotas DF, Filtro Financeiro e Mediador) nas rotas das Salas |
| **Semana 5** | Agentes Multimodais | Conectar o **Leitor de Foto de Nota Fiscal (Visão Computacional)** na Tela 4 de Pós-Rolê e Divisão de Conta |
| **Semana 6** | Aplicação Funcional Completa | Costura final de todas as 4 telas, exportação para WhatsApp/Agenda e teste de um rolê inteiro do início ao Pix |
| **Semana 7** | Relatório Final + Apresentação | Testes de segurança (garantir zero vazamento de orçamento), ajustes visuais e slides finais |

---

## 4. Plano Completo da Semana 3 (92 Horas de Trabalho da Equipe)

**Carga horária da semana:**
- **Terça-feira (Hoje):** 8h *(Cauan, Carol, Duda e Samara presentes; Miti ausente)*
- **Quinta-feira:** 8h *(Todos os 5 presentes)*
- **Sexta-feira:** 4h *(Todos os 5 presentes)*
- **Total:** 20h para Duda, Carol, Samara e Cauan + 12h para Miti = **92 horas de trabalho.**

Para não sobrar tempo ocioso e garantirmos tanto a **nota máxima na entrega da Semana 3** quanto o **avanço pesado do aplicativo final e da gestão do grupo**, o trabalho está dividido em **3 Frentes Obrigatórias para cada integrante**:
1. 🎯 **Entregável dos Monitores (Semana 3: RAG vs. IA Pura)**
2. 🛠️ **Construção do Aplicativo Completo (Código e Telas Reais)**
3. 📋 **Gestão do Grupo e Documentação**

---

### 👩‍💻 1. DUDA / MARIA EDUARDA (20h: 8h Terça + 8h Quinta + 4h Sexta)
**Foco:** Banco na Nuvem (Supabase), DevOps, Avaliador Automático da Semana 3 e Módulo de Conta/Pix.

* **Terça-feira (8h):**
  1. **[Gestão & Git - 1h]:** Subir a limpeza do repositório (`src/base` e `src/voz` removidos), publicar este `GUIA_OFICIAL_PROJETO.md` na `main` e garantir que o GitHub Actions (`pipeline.yaml`) passe 100% verde.
  2. **[App Real - 4h]:** Criar o projeto gratuito no **Supabase (PostgreSQL na nuvem)** e criar as 5 tabelas oficiais do aplicativo (`salas`, `participantes`, `sugestoes_role`, `votos`, `despesas_pos_role`). Criar o arquivo `src/db/supabase_client.py` para conectar o FastAPI ao banco na nuvem.
  3. **[Entregável Semana 3 - 3h]:** Criar a rota `/rag/comparar` e o script de comparação A/B que recebe uma pergunta e roda em paralelo: **(A) Gemini puro sem contexto** vs. **(B) Nosso RAG com os 93 lugares**, registrando os dois traces no Langfuse Cloud com notas automáticas de alucinação e endereço.
* **Quinta-feira (8h):**
  1. **[App Real - 5h]:** Construir o módulo `src/financas/` (o coração financeiro do app):
     - Função que recebe os limites de gasto de todos da sala e devolve apenas o teto seguro do grupo (sem nunca expor quem tem menos dinheiro).
     - Função de **Divisão de Conta Pós-Rolê** (divide o valor total entre os presentes, permite tirar quem não consumiu e trata os centavos).
     - Função **Geradora de Código Pix Copia e Cola (Padrão Banco Central)** que recebe a chave Pix do amigo que pagou + valor e gera o código pronto para colar no banco.
  2. **[Infraestrutura - 3h]:** Configurar o servidor na **DigitalOcean** (usando os $200 do GitHub Student Pack) ou variáveis do Supabase no Render para o aplicativo nunca perder dados quando reiniciar.
* **Sexta-feira (4h):**
  1. **[Entregável Semana 3 - 2h]:** Gerar o **Relatório Técnico da Semana 3 em PDF** (no mesmo padrão de excelência em LaTeX/ABNT da Semana 2) com as tabelas e gráficos da Miti e da Samara.
  2. **[Gestão & Testes - 2h]:** Criar os testes automatizados (`tests/test_financas_pix.py` e `tests/test_comparacao_semana3.py`) e fechar o pacote ZIP de entrega da Semana 3.

---

### 👩‍🎨 2. MARIA CAROLINA (20h: 8h Terça + 8h Quinta + 4h Sexta)
**Foco:** Construção das Telas Reais do Aplicativo (Front-End) e Tela Comparativa da Semana 3.

* **Terça-feira (8h):**
  1. **[Entregável Semana 3 - 3h]:** Criar na interface web a página/aba **`/comparacao` (Semana 3: RAG vs. IA Pura)**: uma tela dividida ao meio (Lado A: *"Resposta da IA Comum sem Base — Alucinação"* em vermelho vs. Lado B: *"Resposta do Nosso RAG — Comprovada"* em verde com vídeo do TikTok, GPS e link do Langfuse).
  2. **[App Real - 5h]:** Começar a construir o aplicativo real separando o visual em páginas organizadas:
     - **Tela 1 (`/app`):** Tela bonita para Criar Sala (nome do rolê, nome do organizador) e gerar o link compartilhável de convite.
     - **Tela 2 (`/sala/{codigo}/perfil`):** Tela com os **4 campos de texto secretos** (De onde sai no DF, Dias e horários, Limite de gasto em R$ com aviso de sigilo, O que anima fazer/transporte) + caixa de confirmação do que o sistema entendeu.
* **Quinta-feira (8h):**
  1. **[App Real - 5h]:** Construir a **Tela 3 (`/sala/{codigo}` — Painel da Sala e Votação)**:
     - Lista de amigos que já entraram na sala (mostrando status *"Já preencheu ✅"* ou *"Falta preencher ⏳"*).
     - Exibição dos **3 a 4 Cartões de Sugestão de Rolê** (com badge da Região Administrativa, horário, gasto estimado no local + transporte, tempo de deslocamento e botão de assistir ao vídeo do TikTok).
     - Botões de **Votação Múltipla** em cada cartão, placar em tempo real e o banner comemorativo **"🎉 Rolê orquestrado com sucesso!"** + botão *"Compartilhar no WhatsApp"*.
  2. **[App Real - 3h]:** Construir o visual da **Tela 4 (`/sala/{codigo}/conta` — Pós-Rolê e Pix)**:
     - Botão de subir a foto da Nota Fiscal / digitar valor da conta, caixinhas para marcar quem dividiu, exibição de quanto cada um deve e botão **"Copiar Código Pix"**.
* **Sexta-feira (4h):**
  1. **[App Real & Integração - 3h]:** Conectar as 4 telas criadas com as rotas do FastAPI feitas pelo Cauan e pela Duda, testando no celular (responsivo).
  2. **[Gestão - 1h]:** Gravar os prints/GIFs da tela comparativa `/comparacao` e das novas telas do app para entrarem no relatório de sexta e na documentação do grupo.

---

### 👩‍💻 3. SAMARA LETÍCIA (20h: 8h Terça + 8h Quinta + 4h Sexta)
**Foco:** Perguntas e Gabarito da Semana 3 (cobrindo a Miti hoje), Cálculo de Transporte/Distância nas 35 RAs do DF e Ampliação da Base fora do Plano Piloto.

* **Terça-feira (8h):**
  1. **[Entregável Semana 3 - 4h]:** Criar o **Conjunto de Teste da Semana 3 (`data/golden_dataset_semana3.json`) com 20 perguntas desafiadoras sobre Brasília** e o gabarito completo olhando os 93 lugares:
     - 5 perguntas sobre preços exatos e pratos específicos (ex: rodízio no Dona Cleide em Águas Claras, café na Asa Norte);
     - 5 perguntas sobre horários difíceis (ex: aberto na madrugada, domingo de manhã, segunda-feira);
     - 5 perguntas fora do Plano Piloto (Taguatinga, Águas Claras, Guará, etc.);
     - 5 perguntas de pegadinha / restrições combinadas (ex: lugar barato, ao ar livre e para ir com crianças ou pet friendly).
  2. **[App Real - 4h]:** Mapear as coordenadas GPS centrais das **35 Regiões Administrativas do DF** em `data/regioes_df_gps.json` (Asa Sul, Asa Norte, Águas Claras, Taguatinga, Ceilândia, Samambaia, Guará, Gama, Sobradinho, Planaltina, etc.) com tarifa média de ônibus/metrô (R$ 5,50) e velocidade média.
* **Quinta-feira (8h):**
  1. **[App Real - 5h]:** Construir o módulo `src/logistica/transporte_df.py`:
     - Função que recebe a Região Administrativa de onde cada amigo sai e calcula a distância em km até qualquer um dos 93 lugares da base da Miti.
     - Calcula o tempo estimado de ida (de carro/Uber vs. transporte público) e o custo estimado de ida e volta em R$.
     - Implementa a fórmula da **"Menor Miséria"**: dá uma nota de justiça espacial para cada lugar (para que um amigo de Ceilândia ou Samambaia não seja obrigado a atravessar o DF inteiro se houver opção boa no meio do caminho, como Águas Claras ou Taguatinga).
  2. **[Dados do App - 3h]:** Junto com a Miti, revisar quantos dos 93 lugares ficam fora do Plano Piloto e catalogar **mais 10 a 15 lugares fortes nas RAs periféricas** (Taguatinga, Ceilândia, Samambaia, Gama, Sobradinho) para a base ficar ainda mais justa.
* **Sexta-feira (4h):**
  1. **[Entregável Semana 3 - 2h]:** Auditar os resultados das 20 perguntas rodadas na IA Pura vs. RAG e montar a tabela de erros da IA Pura (quantas quadras inventou, quantos preços errou) para o relatório.
  2. **[Gestão & Testes - 2h]:** Escrever os testes unitários do cálculo de transporte (`tests/test_transporte_df.py`) e documentar a regra de deslocamento.

---

### 👨‍💻 4. CAUAN SOARES (20h: 8h Terça + 8h Quinta + 4h Sexta)
**Foco:** Rotas de Salas/Votação no Back-End, Adaptação do Interpretador para os 4 Campos de Texto e Atualização da Documentação/Arquitetura.

* **Terça-feira (8h):**
  1. **[App Real - 4h]:** Adaptar o `src/interpretador/` para funcionar diretamente com os **4 campos de texto da Tela 2**:
     - Receber o texto livre de localização (ex: *"moro perto da estação Arniqueiras"* ou *"SQN 210"*) e identificar automaticamente qual das 35 RAs do DF é.
     - Receber o texto de horário (ex: *"sexta depois das 19h ou sábado à tarde"*) e transformar em datas e horas exatas usando o `tempo.py`.
     - Receber o texto de preferências/restrições e extrair tags para buscar nos 93 lugares da Miti.
  2. **[App Real - 4h]:** Criar o arquivo `src/state.py` e `src/salas/gerenciador_salas.py` com toda a lógica de salas:
     - Criar sala com código único (2 a 20 pessoas, bloqueio para menores de 18 anos).
     - Salvar o perfil secreto de cada participante no banco da Duda.
     - Cruzar os horários livres de todos os participantes para achar a melhor janela de encontro do grupo.
* **Quinta-feira (8h):**
  1. **[App Real - 5h]:** Criar as rotas da API do aplicativo real no FastAPI (`src/main.py`):
     - `POST /api/salas` (cria a sala e devolve o link de convite).
     - `POST /api/salas/{codigo}/participantes` (recebe os 4 campos de texto do amigo, passa pelo interpretador e salva em segredo).
     - `POST /api/salas/{codigo}/gerar-sugestoes` (chama o teto financeiro da Duda + o cálculo de transporte da Samara + a busca nos 93 lugares da Miti e devolve os **3 a 4 Cards de Sugestão**).
     - `POST /api/salas/{codigo}/votar` (registra os votos de múltipla escolha, aplica o desempate pela nota de justiça e fecha com *"Rolê orquestrado com sucesso!"*).
  2. **[Gestão & Documentação - 3h]:** Atualizar o **Mapa Interativo da Arquitetura (`docs/arquitetura/index.html`)** e o `STATUS.md` para refletir as decisões oficiais deste guia (tirar Overture, tirar Voz/Groq, colocar os 93 lugares da Miti, os 4 campos de texto, Supabase e o fluxo completo com Pós-Rolê/Pix).
* **Sexta-feira (4h):**
  1. **[Gestão & ADRs - 2h]:** Escrever o **ADR 0008** (oficializando a base 2FA de 93 lugares da Miti e conformidade com LGPD) e atualizar o `requisitos.md` marcando voz como removida.
  2. **[Testes - 2h]:** Garantir que todos os testes de cruzamento de horários, criação de salas, votação e interpretador passem no comando `pytest`.

---

### 👩‍🔬 5. LETÍCIA MITI (12h: Ausente na Terça | 8h Quinta + 4h Sexta)
**Foco:** Liderança Científica do Entregável da Semana 3 (RAG vs. IA Pura), Refinamento do Prompt Anti-Alucinação e Integração da Busca com as Salas.

* **Quinta-feira (8h):**
  1. **[Entregável Semana 3 - 4h]:** Pegar as 20 perguntas preparadas pela Samara e o script A/B da Duda, rodar a bateria completa de testes **LLM Pura vs. RAG**, analisar caso a caso onde a LLM pura alucinou (endereços inventados, lugares fechados, preços errados) e calcular as métricas oficiais da Semana 3:
     - Taxa de Alucinação (*Hallucination Rate*): meta 0% no RAG vs. alta na LLM pura;
     - Precisão de Preço e Horário (RNF-03: $\ge 95\%$ no RAG);
     - Precisão Geográfica por Região Administrativa.
  2. **[App Real - 4h]:** Conectar o motor de busca dela (`src/rag/banco_vetorial.py`) com a geração dos **3 a 4 Cartões da Sala**:
     - Ajustar a busca para receber o filtro de orçamento máximo da sala (feito pela Duda), o horário em comum (feito pelo Cauan) e a nota de distância das RAs (feita pela Samara), devolvendo os 3 a 4 lugares ideais com justificativa personalizada para o grupo.
* **Sexta-feira (4h):**
  1. **[Entregável Semana 3 - 3h]:** Escrever a análise qualitativa e quantitativa dos resultados da Semana 3 (tabelas comparativas, exemplos reais de alucinação da IA pura vs. resposta ancorada do RAG) e revisar o PDF final com a Duda.
  2. **[Gestão - 1h]:** Atualizar o catálogo `data/banco_aprovado_2fa.json` e `data/banco_vetorial_embeddings.json` com os novos lugares fora do Plano Piloto levantados com a Samara.

---

## 5. Resumo Rápido das Regras de Ouro da Equipe

1. **Fonte Única da Verdade:** Qualquer dúvida sobre como o app funciona deve seguir **este documento (`GUIA_OFICIAL_PROJETO.md`)**.
2. **Nada de Subir Arquivos Soltos pelo Site do GitHub:** Sempre usar `git pull`, criar sua branch ou commitar organizado para não bagunçar as pastas `data/`, `src/` e `docs/`.
3. **Sem Voz, Sem Overture:** Nosso foco é **Texto nos 4 campos + Base de 93 lugares da Miti + Transporte nas 35 RAs + Votação em 3 a 4 Cards + Foto da Nota Fiscal e Pix no Pós-Rolê**.
4. **Foco Duplo Toda Semana:** Toda semana entregamos o que o monitor pede na sexta-feira, mas construímos as peças reais do aplicativo em paralelo para chegarmos na Semana 6 com tudo pronto!

---

## 6. Atalhos Rápidos Multiplataforma (DevOps) e Guia de Pull Requests

Para que ninguém da equipe perca tempo decorando comandos longos do Docker, foram configurados atalhos automáticos compatíveis com qualquer computador (Mac, Linux e Windows):

### ⚡ Atalhos Rápidos de 1 Palavra:

| O que você quer fazer? | Mac / Linux / WSL (Terminal) | Windows Nativo (CMD / PowerShell) |
| :--- | :--- | :--- |
| **Rodar todos os testes no Docker** | `make test` *(ou `./scripts/testar.sh`)* | `scripts\testar.bat` |
| **Subir os containers (Postgres + App)** | `make up` | `docker compose up -d` |
| **Parar os containers** | `make down` | `docker compose down` |
| **Ver logs dos containers** | `make logs` | `docker compose logs -f` |
| **Rodar testes no Python local (venv)** | `make test-local` | `pytest` *(com `.venv` ativo)* |

---

### 🛡️ Regra de Ouro para Abertura e Fechamento de Pull Requests (PRs)

1. **Antes de Abrir o PR (Validação Obrigatória):**
   - Execute sempre os testes no seu terminal usando `make test` (ou `scripts\testar.bat`).
   - Se os testes passarem 100% verde localmente, seu código está seguro para ser enviado.
2. **Ao Abrir o PR no GitHub:**
   - Crie a branch sempre com prefixo: `feat/` (novidade), `fix/` (correção) ou `docs/` (documentação).
   - O template de PR carregará automaticamente o checklist de qualidade e segurança.
   - Insira `Closes #NUMERO_DA_ISSUE` na descrição para que a issue seja encerrada automaticamente.
3. **Aprovação e Merge (Fechamento do PR):**
   - Todo PR exige que os testes do GitHub Actions fiquem verdinhos (✅).
   - O arquivo `.github/CODEOWNERS` atribui automaticamente a revisão para a Maria Eduarda (DevOps).
   - Com os testes passando e a revisão aprovada, o merge é realizado com segurança na `main`!

