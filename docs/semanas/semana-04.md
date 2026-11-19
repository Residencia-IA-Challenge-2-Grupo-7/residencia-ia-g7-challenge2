# Semana 4 — Primeiro Protótipo Multiagente (LangGraph + Ferramentas Determinísticas)

**Projeto:** Orquestrador de Rolês (*Challenge 2 — Residência em IA \| Instituto Eldorado & UnB*)  
**Entregável Oficial:** Primeiro protótipo funcional do sistema multiagente baseado em **LangGraph**, integrando agentes amparados por **LLM** (curadoria, síntese e avaliação semântica) e **ferramentas determinísticas em Python** (cálculo financeiro, deslocamento pelas 35 RAs do DF com a regra da *Menor Miséria*, checagem de horários e vetos duros), com **rastreabilidade completa no Langfuse Cloud**, script de demonstração CLI executável e **Relatório Técnico ABNT** para submissão no canal `4_Second Challenge` do Microsoft Teams.

---

## 1. Contexto, Desafio e Princípios Arquiteturais

### 1.1. Big Idea & Essential Question
* **Big Idea:** Qualidade de Vida e Bem-Estar Social no Distrito Federal.
* **Essential Question:** *"Como sistemas de IA podem ajudar amigos a transformar a vontade de se encontrar em encontros reais, de forma justa para todos?"*
* **Problema Resolvido:** Planos de encontro que morrem pela vergonha de expor limitações financeiras, fadiga de decisão e assimetria logística de deslocamento entre quem mora no Plano Piloto e nas demais Regiões Administrativas periféricas do DF.

### 1.2. Princípios Não Negociáveis de Design (Manual dos Agentes)
Estes princípios operam como restrições rígidas de arquitetura. Toda decisão de modelagem e código deriva deles:

| Princípio | Consequência Arquitetural no Código |
| :--- | :--- |
| **Sigilo Estrito do Perfil (`RNF-02`)** | Os dados cadastrados no perfil (teto financeiro, endereço/RA exata e restrições) ficam isolados no servidor; nenhuma resposta pública da IA ou card expõe quem limitou o orçamento do grupo. |
| **Consenso Assistido, Não Imposição** | A IA nunca impõe uma decisão: ela filtra incompatibilidades e publica de **3 a 4 propostas viáveis** para votação democrática com suporte a múltipla escolha (`RF-06`). |
| **Grounding em Dados Reais (`RNF-03`)** | Zero alucinação: nenhum local, horário ou preço é inventado. A pesquisa consome estritamente os **93 lugares oficiais aprovados em 2 fatores (2FA)** validados pelo TikTok. |
| **Cálculos Fora do LLM (`RNF-04`)** | Interseção de agendas, teto financeiro individual, estimativas de custo de transporte e cálculo da nota de justiça social rodam em **funções Python determinísticas**, jamais via texto gerado por IA. |
| **Justiça Espacial ('Menor Miséria' — `ADR 0013`)** | O ranqueamento protege quem tem menor orçamento e quem depende de transporte público em RAs afastadas (Ceilândia, Samambaia, Planaltina), penalizando locais que imponham trajetos desumanos ao participante mais desfavorecido. |
| **Transparência e Fechamento** | Cada card exibe claramente local, dia/horário, faixa de preço média e modal sugerido, encerrando o ciclo de votação com o banner fixo: *"Rolê orquestrado com sucesso!"*. |

### 1.3. Escopo Negativo (O que o sistema NÃO faz)
* **Não expõe dados privados:** Jamais revela no chat público o orçamento individual ou quem vetou financeiramente uma opção.
* **Não atende eventos corporativos (Antipersona Patrícia):** Salas limitadas a grupos de amigos (2 a 20 adultos), sem emissão de notas fiscais, venda de ingressos ou contratação de fornecedores.
* **Não promove encontros entre desconhecidos:** Não opera como rede social aberta ou app de relacionamento (Modo Descoberta fora do MVP).
* **Não atende menores de 18 anos:** Cadastros de menores são bloqueados em conformidade com o Art. 14 da LGPD.
* **Sem dependência de áudio/voz:** A entrada de dados opera exclusivamente pelos 4 campos de texto secretos (ADR 0009).

---

## 2. Arquitetura do Grafo Multiagente (LangGraph)

O fluxo é orquestrado como um grafo de estados (`StateGraph`) cíclico e condicional, no qual nós especializados interagem através de um estado compartilhado estritamente tipado (`MultiAgentState`), com controle de loops e fallback automático.

```mermaid
flowchart TD
    classDef llm fill:#e1f5fe,stroke:#0288d1,stroke-width:2px;
    classDef code fill:#e8f5e9,stroke:#388e3c,stroke-width:2px;
    classDef decision fill:#fff3e0,stroke:#f57c00,stroke-width:2px;
    classDef data fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px;

    IN["Perfis Privados (4 Campos dos Amigos)"]:::data --> AG0["0. AGENTE PESSOAL<br/>(Regras em Código Puro)<br/>• Anonimização e Eliminação de PII<br/>• Segregação Estrita em 4 Canais"]:::code

    AG0 -- "Canal 4: Vibes do Grupo" --> AG1["1. AGENTE DE PESQUISA<br/>(LLM: DeepSeek V4.1 Flash)<br/>• Persona: Curador da Cena do DF<br/>• Tool RAG: 93 Locais 2FA TikTok<br/>• Gera 8 a 10 Candidatos"]:::llm
    AG0 -. "Canal 1 e 2: Teto e Restrições" .-> AG3
    AG0 -. "Canal 3: RAs de Origem" .-> AG2

    AG1 --> AG2["2. AGENTE DE LOGÍSTICA & JUSTIÇA<br/>(Código Puro — RNF-04, ADR 0013)<br/>• Estimativa Multimodal 35 RAs (<= 75 min)<br/>• Cálculo da 'Menor Miséria'<br/>• Score: 45% Vibe + 35% Justiça + 20% Horário"]:::code

    AG2 --> AG3["3. AGENTE DE VALIDAÇÃO<br/>(Híbrido: Código + Juiz LLM)<br/>• Vetos Duros em Python (Teto, Horário, Restrições)<br/>• Juiz LLM: MiMo-V2.6-Pro (ADR 0014)<br/>• Auditoria de Fatos vs Documentos"]:::code

    AG3 --> COND{"Avaliador de Convergência<br/>Aprovados >= 3?"}:::decision

    COND -- "Não (e iteração < 2)<br/>[Ciclo Condicional]" -->|Contagem de Motivos dos Vetos| AG1
    COND -- "Sim (ou atingiu 2 voltas)" --> AG4["4. AGENTE DE COMUNICAÇÃO<br/>(LLM: Anfitrião de Brasília)<br/>• Persona acolhedora e calorosa<br/>• Síntese sem citar orçamentos individuais<br/>• Formatação JSON dos 3 a 4 Cartões"]:::llm

    AG4 --> END_VAL["3. VALIDAÇÃO (2ª Passagem)<br/>• Juiz LLM audita vazamento de PII<br/>• Preenchimento determinístico de preços"]:::code
    END_VAL --> PUB["Aba Pública da Sala<br/>Cards da Votação Democrática Multi-Escolha"]:::data

    subgraph TELEMETRIA ["Observabilidade & Auditoria (Langfuse Cloud v5.x)"]
        TRACE["Traces End-to-End • Spans por Agente • Latência (RNF-14) • Tokens • Scores de Alucinação"]
    end
    AG0 -.-> TRACE
    AG1 -.-> TRACE
    AG2 -.-> TRACE
    AG3 -.-> TRACE
    AG4 -.-> TRACE
```

---

## 3. Especificação Detalhada dos 5 Agentes

### 🤖 0. Agente Pessoal (Personal Agent)
* **Natureza Técnica:** 100% código determinístico na fase de organização do rolê (`src/interpretador/campos.py`); LLM acionado apenas no pós-rolê para leitura de comentários livres (`RF-37`).
* **Responsabilidade Principal:** Lê os 4 campos de texto secretos de cada participante, sanitiza completamente nomes e identificadores de rede (PII) e segrega os dados em 4 canais privados independentes:
  1. **Canal 1 (Orçamento Sigiloso):** Encaminhado exclusivamente para verificação do veto financeiro (`cabe_para_cada_um`);
  2. **Canal 2 (Restrições Duras):** Encaminhado para a checagem de restrições alimentares e de acessibilidade na Validação;
  3. **Canal 3 (Origem Geoespacial & Janelas):** Encaminhado para a matriz de deslocamento da Logística e cruzamento de horários comuns;
  4. **Canal 4 (Vibes e Preferências):** Agregado anonimamente no perfil coletivo da sala para o Agente de Pesquisa.
* **Exemplo de Mensagem Emitida:**
  > *"Grupo de 4 pessoas. Tipos pedidos: bar (3 de 4), café (1 de 4). Vibes: descontraído, ar livre. Evitar: lugares barulhentos (pedido de 1 pessoa). Texto do pedido consolidado: 'comemorar aniversário, boa comida, espaço arejado'."*

---

### 🤖 1. Agente de Pesquisa (Research Agent)
* **Natureza Técnica:** Agente autônomo com LLM (**DeepSeek V4.1 Flash** via OpenRouter) dotado de *Tool Calling* determinístico.
* **Persona & System Prompt:**
  > *"Você é um curador da cena cultural, gastronômica e de lazer do Distrito Federal. Você recebe o perfil anônimo de um grupo e usa a ferramenta de busca para levantar candidatos da base oficial de 93 lugares. Você só cita fatos que estão nos documentos recebidos. Você não sabe e não pergunta o orçamento de ninguém."*
* **Responsabilidade Principal:**
  1. Constrói consultas estruturadas (`ConsultaBusca`, ADR 0007) e aciona a tool de busca vetorial (`buscar_lugares_rag`);
  2. Recupera de **8 a 10 candidatos** sustentados por evidências (`trecho_citado`, `fonte_id`);
  3. **No ciclo de retorno da Validação**, refaz a busca recebendo apenas a contagem anônima dos vetos (ex: *"faltam 2 candidatos; motivos dos vetos: 3 por horário fechado, 2 por estouro de teto"*).
* **Exemplo de Mensagem Emitida:**
  > *"Encontrei 9 candidatos na base oficial. Destaques: Local A (ar livre, 'quiosque com mesas no gramado', FONTE #2) e Local B (gastronomia, 'cardápio variado de petiscos', FONTE #5). Seguem os IDs para análise de logística."*

---

### ⚙️ 2. Agente de Logística & Justiça (Logistics Agent)
* **Natureza Técnica:** 100% código determinístico Python (`src/agentes/logistica.py`), sem uso de LLM (`RNF-04`, `ADR 0013`).
* **Responsabilidade Principal:** Especialista na malha de transporte das 35 Regiões Administrativas do DF e guardião da equidade espacial:
  1. Para cada candidato e cada membro da sala, calcula `estimar_deslocamento(ra_origem, lat, lng, modo, quando)` adotando o meio mais econômico que cumpra o teto de 75 minutos;
  2. Aplica a **Regra da Menor Miséria**, calculando a `nota_menor_miseria` baseada na discrepância e tempo máximo do pior trajeto;
  3. Gera o **Score Ponderado do Rolê**:
     $$\text{Score} = 0{,}45 \times \text{Aderência Vibe} + 0{,}35 \times \text{Justiça Deslocamento} + 0{,}20 \times \text{Certeza Horário}$$
  4. Redige o parecer de rota por regras parametrizadas (ex: *"pior trajeto de 38 min de metrô; média de 27 min entre os membros"*).
* **Exemplo de Mensagem Emitida:**
  > *"Ranking Logístico: Local A (Score 81; pior trajeto 38 min; média 27 min), Local C (74), Local D (70), Local B (41; pior trajeto 92 min de ônibus). Local B fica por último pela Menor Miséria."*

---

### 🛡️ 3. Agente de Validação e Consistência (Validation Agent)
* **Natureza Técnica:** Arquitetura híbrida combinando filtros determinísticos em Python puro com **LLM-as-a-Judge** (**MiMo-V2.6-Pro**, `xiaomi/mimo-v2.6-pro` via OpenRouter, ADR 0014).
* **Persona & System Prompt do Juiz:**
  > *"Você é um auditor factual. Compare cada afirmação do texto com os documentos da base e diga se confere, se contradiz ou se não está na base. Aponte também qualquer trecho que permita deduzir o orçamento, a origem ou as restrições de uma pessoa específica."*
* **Responsabilidade Principal:**
  1. **Filtros Duros em Código:**
     - `cabe_para_cada_um`: confere se $\text{Consumo Estimado} + \text{Deslocamento Individual} \le \text{Teto Individual}$ para cada participante (sem expor quem estourou);
     - Horário de funcionamento sobreposto à janela comum do grupo (`horario_lugar.py`);
     - Expiração de eventos e promoções passadas;
     - Restrições alimentares inegociáveis.
  2. **Juiz LLM — 1ª Passagem (Auditoria da Pesquisa):** Confere fidelidade factual das afirmações do Agente 1 contra a base curada; afirmações alucinadas são desconsideradas;
  3. **Controle de Loop de Realimentação:** Se restarem menos de 3 candidatos viáveis, aciona o retorno para o Agente 1 (máximo de 2 voltas);
  4. **Juiz LLM — 2ª Passagem (Auditoria da Comunicação):** Confere ausência absoluta de pistas sobre orçamentos ou origens individuais nos cartões.
* **Exemplo de Mensagem Emitida:**
  > *"Validação concluída: 4 locais passam nos critérios de horário, restrições e orçamento. 3 vetados (2 por horário fechado, 1 por orçamento do grupo). Aprovado para síntese final."*

---

### 🤖 4. Agente de Síntese e Comunicação (Communication Agent)
* **Natureza Técnica:** Agente gerador via LLM com prompt de tom empático e formatação JSON estrita.
* **Persona & System Prompt:**
  > *"Você é o anfitrião do rolê em Brasília. Você escreve convites calorosos e claros para um grupo de amigos a partir dos fatos recebidos. Você nunca menciona de onde alguém sai, quanto alguém pode gastar ou a restrição de uma pessoa, e nunca escreve números: eles são preenchidos pelo sistema."*
* **Responsabilidade Principal:**
  1. Recebe apenas agregados do grupo e fatos confirmados da base;
  2. Redige com tom candango e envolvente os campos `titulo`, `resumo_acesso` e `por_que_combina`;
  3. Emite a lista de 3 a 4 cartões estruturados no esquema da classe `Sugestao` da aplicação; dados financeiros, endereços oficiais e links do TikTok são injetados diretamente por código após a geração do texto.
* **Exemplo de Mensagem Emitida:**
  > *JSON contendo os 3 a 4 cartões de sugestão completos prontos para renderização nos componentes de votação da interface pública.*

---

## 4. Contratos de Dados e Estado (`MultiAgentState`)

O fluxo trafega uma única estrutura tipada derivada de `TypedDict` em `src/agentes/estado.py`:

```python
from typing import Annotated, TypedDict
from operator import add

class MultiAgentState(TypedDict):
    sala_id: str
    # Canais privados (isolados e protegidos)
    membros_privados: list[dict]       # orçamentos, origens e restrições individuais
    # Canal anônimo do grupo
    perfil_grupo_anonimizado: dict     # vibes agregadas, janela comum de horários
    # Estados intermediários
    candidatos_pesquisa: list[dict]    # 8 a 10 candidatos retornados pelo Agente 1
    candidatos_avaliados: list[dict]   # notas e tempos calculados pelo Agente 2
    candidatos_validados: list[dict]   # locais aprovados nos vetos do Agente 3
    motivos_vetos: dict[str, int]      # contagem estruturada de reprovações
    # Saída final
    resultado_cartoes: list[dict]      # 3 a 4 cartões consolidados pelo Agente 4
    # Controle de execução
    iteracao_pesquisa: int             # contador do loop (máximo 2 voltas)
    historico_mensagens: Annotated[list[str], add] # log cumulativo da sala
    trace_id_langfuse: str             # identificador de rastreabilidade
```

---

## 5. Mapeamento Oficial das 13 Issues no GitHub

Todas as tarefas foram cadastradas no GitHub no padrão unificado `[Semana 4] [ÁREA]`, vinculadas ao **Milestone #4** e ao **Projeto #1**:

> [!IMPORTANT]
> **Ponto de Atenção para o Time sobre o Início do Desenvolvimento e PRs:**  
> Os módulos dos agentes (**#65**, **#67**, **#68**, **#69** e **#70**) **NÃO precisam esperar** a modelagem do grafo para serem codificados. Todos os responsáveis podem (e devem) começar a implementar as funções de negócio, prompts e testes unitários locais imediatamente em suas branches!  
> **Atenção 1:** Só **não façam Pull Request (PR) de integração** no LangGraph antes que o Cauan (`@cadasiso`) finalize e publique a **#64** (`MultiAgentState`), pois o grafo precisa dessa estrutura compartilhada para conectar as pontas.  
> **Atenção 2 (Critério Obrigatório de Aceitação para Todas as Issues):** Todo membro deve, obrigatoriamente, registrar na **Seção 8** deste documento (`docs/semanas/semana-04.md`) o que foi feito na sua issue, justificando as **decisões técnicas e de arquitetura** tomadas, listando os arquivos criados/modificados e anexando as evidências de testes locais. Nenhum PR deve ser mergeado sem este registro.

| Issue | Título Oficial | Responsável | Área | Início | Prazo | Status Oficial | Dependência e Regra de PR |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **#64** | `[Semana 4] [BACKEND] Modelagem do Estado Compartilhado (MultiAgentState) no LangGraph` | `@cadasiso` | `BACKEND` | Ter (17/11) | Ter 18:00 | `status:liberada` | Início imediato |
| **#65** | `[Semana 4] [BACKEND] Agente 0 (Pessoal): Sanitização de PII e Segregação dos 4 Canais` | `@cadasiso` | `BACKEND` | Ter (17/11) | Ter 18:00 | `status:liberada` | Desenvolvimento em paralelo; PR aguarda #64 |
| **#66** | `[Semana 4] [DATA] Dataset de Teste com Cenário dos 4 Amigos no DF (Golden de Rolê)` | `@samarawwleticia` | `DATA` | Ter (17/11) | Ter 18:00 | `status:liberada` | Início imediato |
| **#67** | `[Semana 4] [BACKEND] Agente 2 (Logística & Justiça): Deslocamento e Regra da Menor Miséria` | `@samarawwleticia` | `BACKEND` | Ter (17/11) | Qui 12:00 | `status:liberada` | Desenvolvimento em paralelo; PR aguarda #64 |
| **#68** | `[Semana 4] [BACKEND] Agente 3 (Validação): Filtros Determinísticos de Horário, Orçamento e Restrições` | `@eduarda-ogomes` | `BACKEND` | Ter (17/11) | Ter 18:00 | `status:liberada` | Desenvolvimento em paralelo; PR aguarda #64 |
| **#69** | `[Semana 4] [BACKEND] Agente 4 (Comunicação): Prompt do Anfitrião e Formatação de Cartões em JSON` | `@mcznh` | `BACKEND` | Ter (17/11) | Ter 18:00 | `status:liberada` | Desenvolvimento em paralelo; PR aguarda #64 |
| **#70** | `[Semana 4] [BACKEND] Agente 1 (Pesquisa): Prompt do Curador + Tool RAG dos 93 Lugares do TikTok` | `@cadasiso` | `BACKEND` | Qui (19/11) | Qui 12:00 | `status:liberada` | Desenvolvimento em paralelo; PR aguarda #64 |
| **#71** | `[Semana 4] [BACKEND] Orquestrador do Grafo no LangGraph com Ciclo Condicional Pesquisa-Validação` | `@cadasiso` | `BACKEND` | Qui (19/11) | Qui 15:00 | `status:bloqueada` | Bloqueada por #65, #67, #68, #69, #70 |
| **#72** | `[Semana 4] [LLMOPS] Juiz LLM em 2 Passagens para Validação Factual e Prevenção de Vazamento (ADR 0014)` | `@eduarda-ogomes` | `LLMOPS` | Qui (19/11) | Qui 14:00 | `status:liberada` | Desenvolvimento em paralelo; integração com #68 |
| **#73** | `[Semana 4] [LLMOPS] Instrumentação de Telemetria e Tracing do Grafo Multiagente no Langfuse Cloud` | `@eduarda-ogomes` | `LLMOPS` | Qui (19/11) | Qui 16:00 | `status:bloqueada` | Bloqueada por #71 (Grafo Compilado) |
| **#74** | `[Semana 4] [BACKEND] Script Executável de Demonstração CLI do Fluxo Multiagente (demo_multiagente.py)` | `@cadasiso` | `BACKEND` | Qui (19/11) | Qui 17:00 | `status:bloqueada` | Bloqueada por #71, #73 |
| **#75** | `[Semana 4] [DOCS] Diagrama Visual da Arquitetura do Grafo Multiagente (Mermaid & SVG)` | `@mcznh` | `DOCS` | Ter (17/11) | Qui 15:00 | `status:concluida` | Concluída com docs, SVG e testes locais |
| **#76** | `[Semana 4] [DOCS] Relatório Técnico da Semana 4 para o Teams e Submissão Oficial` | `@mitii05` | `DOCS` | Qui (19/11) | **Qui 18:00** | `status:bloqueada` | Bloqueada por #74, #75 (Submissão Final) |

---

## 6. Distribuição de Carga Horária (~12h por Integrante)

O cronograma do time opera estritamente nas terças (4h presenciais) e quintas (8h de desenvolvimento integrado), totalizando ~12 horas úteis por membro:

* **Cauan Soares (`@cadasiso`):**
  - Terça: Modelagem do Estado Compartilhado (#64 - 2h) + Agente 0 Pessoal (#65 - 2h) = 4h
  - Quinta: Agente 1 Pesquisa (#70 - 3h) + Orquestrador LangGraph (#71 - 3h) + Script Demo CLI (#74 - 2h) = 8h  
  *Total: 12h*
* **Maria Eduarda (`@eduarda-ogomes`):**
  - Terça: Agente 3 Validação — Vetos Duros em Código (#68 - 4h) = 4h
  - Quinta: Juiz LLM em 2 Passagens (#72 - 4h) + Telemetria/Tracing Langfuse (#73 - 4h) = 8h  
  *Total: 12h*
* **Samara Letícia (`@samarawwleticia`):**
  - Terça: Dataset do Cenário dos 4 Amigos no DF (#66 - 2h) + Agente 2 Logística início (#67 - 2h) = 4h
  - Quinta: Agente 2 Logística conclusão e testes com Menor Miséria (#67 - 4h) + Testes de Integração = 8h  
  *Total: 12h*
* **Maria Carolina (`@mcznh`):**
  - Terça: Agente 4 Comunicação e Schema JSON dos Cards (#69 - 4h) = 4h
  - Quinta: Diagramas Arquiteturais Mermaid & SVG (#75 - 4h) + Alinhamento do formato dos Cards = 8h  
  *Total: 12h*
* **Letícia Miti Takahashi (`@mitii05`):**
  - Terça: Apoio em testes de contrato e validação preliminar dos dados (4h) = 4h
  - Quinta: Compilação do Relatório Técnico ABNT e Submissão Oficial no Teams (#76 - 8h) = 8h  
  *Total: 12h*

---

## 7. Instruções Operacionais e Comandos do Time

### 7.1. Fluxo Git e Convenção de Branches
Todo desenvolvimento ocorre em branches isoladas partindo da `main` atualizada:
```bash
git checkout main
git pull origin main
git checkout -b feat/semana4-<nome-da-tarefa>
```

### 7.2. Execução de Testes Automatizados Locais
Nenhum Pull Request pode ser aberto sem os testes passando localmente:
```bash
# Executa testes unitários rápidos
pytest -v tests/test_<sua_tarefa>.py

# Executa toda a suíte oficial do repositório
make test-local
```

### 7.3. Demonstração Oficial do Multiagente (CLI)
Para validar o fluxo completo e obter a URL do trace no Langfuse:
```bash
python scripts/demo_multiagente.py
# ou pelo Makefile
make demo-agentes
```

### 7.4. Submissão no Microsoft Teams
O envio formal do entregável deve ser postado impreterivelmente até **Quinta-feira, 19/11/2026, às 18:00 (BRT)** no canal `4_Second Challenge` contendo:
1. Link do Pull Request / Repositório na branch `main`;
2. PDF oficial do Relatório Técnico compilado;
3. Prints dos logs de execução do `scripts/demo_multiagente.py`;
4. Link público e capturas de tela da árvore de execução e traces no Langfuse Cloud.

### 7.5. Critério de Aceitação Obrigatório: Registro de Entregas e Decisões
Para garantir a rastreabilidade do projeto, a consistência com os relatórios das semanas anteriores (Semana 02 e 03) e facilitar a compilação do Relatório Técnico ABNT (#76), **todo integrante deve atualizar a Seção 8 abaixo ao concluir sua issue**:
- Descrever o que foi implementado;
- Justificar as decisões técnicas e de design tomadas (por que foi feito dessa forma);
- Listar arquivos criados ou modificados;
- Registrar comandos de teste executados e evidências de validação (pytest/make).
Nenhum Pull Request será aprovado sem que a respectiva entrada na Seção 8 esteja preenchida.

---

## 8. Registro de Execução e Decisões Técnicas por Issue

> **Regra do Time:** Atualize o bloco da sua issue assim que concluir a implementação e testes locais, antes de abrir o PR.

### 8.1. Issue #64 — Modelagem do Estado Compartilhado (`MultiAgentState`)
* **Responsável:** Cauan Soares (`@cadasiso`)
* **Status:** Em andamento / Concluída
* **O que foi feito:**
* **Decisões Técnicas e Arquitetura:**
* **Arquivos:**
* **Testes e Validação:**

---

### 8.2. Issue #65 — Agente 0 (Pessoal): Sanitização de PII e Segregação dos 4 Canais
* **Responsável:** Cauan Soares (`@cadasiso`)
* **Status:** A iniciar
* **O que foi feito:**
* **Decisões Técnicas e Arquitetura:**
* **Arquivos:**
* **Testes e Validação:**

---

### 8.3. Issue #66 — Dataset de Teste com Cenário dos 4 Amigos no DF (Golden de Rolê)
* **Responsável:** Samara Letícia (`@samarawwleticia`)
* **Status:** A iniciar
* **O que foi feito:**
* **Decisões Técnicas e Arquitetura:**
* **Arquivos:**
* **Testes e Validação:**

---

### 8.4. Issue #67 — Agente 2 (Logística & Justiça): Deslocamento e Regra da Menor Miséria
* **Responsável:** Samara Letícia (`@samarawwleticia`)
* **Status:** A iniciar
* **O que foi feito:**
* **Decisões Técnicas e Arquitetura:**
* **Arquivos:**
* **Testes e Validação:**

---

### 8.5. Issue #68 — Agente 3 (Validação): Filtros Determinísticos de Horário, Orçamento e Restrições
* **Responsável:** Maria Eduarda (`@eduarda-ogomes`)
* **Status:** Em andamento
* **O que foi feito:**
* **Decisões Técnicas e Arquitetura:**
  - *RNF-04 (Cálculos Fora do LLM):* Implementação dos 4 vetos duros (`cabe_para_cada_um`, `horario`, `encerrado`, `restricao`) em Python puro para garantir 100% de determinismo e zero alucinação aritmética.
  - *RF-17 e RNF-02 (Orçamento Sigiloso):* Validação estritamente individual ($\text{consumo} + \text{transporte individual} \le \text{teto individual}$) sem expor quem estourou o teto nem vazar valores para o estado público.
  - *Ciclo Condicional:* Emissão de relatório estruturado com contagem agregada de motivos de veto para realimentar o Agente de Pesquisa caso restem menos de 3 candidatos viáveis.
* **Arquivos:**
  - `src/agentes/validacao.py`
  - `tests/test_agente_validacao_regras.py`
* **Testes e Validação:**

---

### 8.6. Issue #69 — Agente 4 (Comunicação): Prompt do Anfitrião e Formatação de Cartões em JSON
* **Responsável:** Maria Carolina (`@mcznh`)
* **Status:** A iniciar
* **O que foi feito:**
* **Decisões Técnicas e Arquitetura:**
* **Arquivos:**
* **Testes e Validação:**

---

### 8.7. Issue #70 — Agente 1 (Pesquisa): Prompt do Curador + Tool RAG dos 93 Lugares do TikTok
* **Responsável:** Cauan Soares (`@cadasiso`)
* **Status:** A iniciar
* **O que foi feito:**
* **Decisões Técnicas e Arquitetura:**
* **Arquivos:**
* **Testes e Validação:**

---

### 8.8. Issue #71 — Orquestrador do Grafo no LangGraph com Ciclo Condicional Pesquisa-Validação
* **Responsável:** Cauan Soares (`@cadasiso`)
* **Status:** Bloqueada
* **O que foi feito:**
* **Decisões Técnicas e Arquitetura:**
* **Arquivos:**
* **Testes e Validação:**

---

### 8.9. Issue #72 — Juiz LLM em 2 Passagens para Validação Factual e Prevenção de Vazamento (ADR 0014)
* **Responsável:** Maria Eduarda (`@eduarda-ogomes`)
* **Status:** Bloqueada
* **O que foi feito:**
* **Decisões Técnicas e Arquitetura:**
* **Arquivos:**
* **Testes e Validação:**

---

### 8.10. Issue #73 — Instrumentação de Telemetria e Tracing do Grafo Multiagente no Langfuse Cloud
* **Responsável:** Maria Eduarda (`@eduarda-ogomes`)
* **Status:** Bloqueada
* **O que foi feito:**
* **Decisões Técnicas e Arquitetura:**
* **Arquivos:**
* **Testes e Validação:**

---

### 8.11. Issue #74 — Script Executável de Demonstração CLI do Fluxo Multiagente (`demo_multiagente.py`)
* **Responsável:** Cauan Soares (`@cadasiso`)
* **Status:** Bloqueada
* **O que foi feito:**
* **Decisões Técnicas e Arquitetura:**
* **Arquivos:**
* **Testes e Validação:**

---

### 8.12. Issue #75 — Diagrama Visual da Arquitetura do Grafo Multiagente (Mermaid & SVG)
* **Responsável:** Maria Carolina (`@mcznh`)
* **Status:** Concluída
* **O que foi feito:**
  - Elaboração da documentação técnica arquitetural completa em `docs/arquitetura/multiagente.md` com especificações detalhadas do grafo no LangGraph;
  - Criação de página web completa e responsiva em `docs/arquitetura/multiagente.html` para visualização e leitura direta da documentação com Mermaid.js e SVG integrado, vinculada ao mapa geral (`docs/arquitetura/index.html`);
  - Criação de diagrama estrutural em Mermaid evidenciando os nós cognitivos (LLM), nós determinísticos (código puro Python), canais de dados e o loop condicional de feedback;
  - Desenvolvimento de gerador vetorial automatizado em Python (`scripts/gerar_grafo_multiagente_svg.py`) e exportação de imagem vetorial de alta resolução em `docs/arquitetura/img/grafo_multiagente.svg`;
  - Atualização do menu de navegação e suporte a diagramas Mermaid no `mkdocs.yml`;
  - Criação de suíte de testes automatizados em `tests/test_arquitetura_multiagente.py`.
* **Decisões Técnicas e Arquitetura:**
  - *RNF-04 (Cálculos Fora do LLM):* Diferenciação visual e estrutural estrita entre nós com LLM (Pesquisa, Comunicação e Juiz) e nós em código puro Python (Sanitização do Agente 0, Logística com Menor Miséria do Agente 2 e Vetos Duros do Agente 3).
  - *RNF-02 e RF-17 (Sigilo do Perfil e Orçamento):* Representação explícita da segregação em 4 canais privados independentes, garantindo que teto financeiro e localização exata jamais cheguem aos agentes cognitivos generativos.
  - *Ciclo Condicional e Controle de Convergência:* Modelagem da checagem de parada (Aprovados >= 3 ou máximo de 2 voltas) com feedback anônimo contendo apenas a contagem estruturada dos motivos de veto.
  - *Observabilidade Ponta a Ponta:* Inclusão do painel de telemetria Langfuse Cloud v5.x com rastreamento por trace raiz e spans individuais por agente para monitoramento de latência (RNF-14) e fidelidade factual (RNF-03).
* **Arquivos:**
  - `docs/arquitetura/multiagente.md`
  - `docs/arquitetura/multiagente.html`
  - `docs/arquitetura/index.html`
  - `docs/arquitetura/img/grafo_multiagente.svg`
  - `scripts/gerar_grafo_multiagente_svg.py`
  - `mkdocs.yml`
  - `tests/test_arquitetura_multiagente.py`
  - `docs/semanas/semana-04.md`
* **Testes e Validação:**
  - Execução de `pytest tests/test_arquitetura_multiagente.py` com 6 testes aprovados cobrindo integridade do SVG, nós, canais, requisitos, estrutura markdown, página HTML e configuração do MkDocs.
  - Execução da suíte completa de testes locais com 625 testes passando.

---

### 8.13. Issue #76 — Relatório Técnico da Semana 4 para o Teams e Submissão Oficial
* **Responsável:** Letícia Miti Takahashi (`@mitii05`)
* **Status:** Bloqueada
* **O que foi feito:**
* **Decisões Técnicas e Arquitetura:**
* **Arquivos:**
* **Testes e Validação:**

