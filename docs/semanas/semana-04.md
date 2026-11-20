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

> **Atualizado em 20/11 para o que foi implementado** (`src/agentes/grafo.py`, PRs #80, #86 e #88). A versão anterior desta seção era o plano de 17/11, escrito antes do código.

O fluxo é um `StateGraph` do LangGraph ([ADR 0015](../decisoes/0015-orquestracao-com-langgraph.md)), com 8 nós, um ciclo condicional entre a Validação e a Pesquisa e outro entre a validação dos textos e a Comunicação.
- O estado do grafo (`MultiAgentState`, Seção 4) só tem dados públicos e mensagens anônimas.
- Teto, origem, janelas e restrições de cada pessoa ficam no **cofre**, um objeto do servidor preso ao grafo na construção, que só os nós de código leem (RNF-02).

```mermaid
flowchart TD
    classDef llm fill:#e1f5fe,stroke:#0288d1,stroke-width:2px;
    classDef code fill:#e8f5e9,stroke:#388e3c,stroke-width:2px;
    classDef hybrid fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px;
    classDef decision fill:#fff3e0,stroke:#f57c00,stroke-width:2px;
    classDef data fill:#eceff1,stroke:#546e7a,stroke-width:1.5px;

    START(["Sala com os 4 campos de cada membro"]):::data -->|"Send: um por membro, em paralelo"| P["0. Agente Pessoal (um por membro)<br/>código; canais 1, 2 e 4 vão para o cofre,<br/>canal 3 (preferências) vai para o grupo"]:::code
    P --> G["Consolidação do grupo<br/>tipos, vibes e restrições somados, sem dizer de quem"]:::code
    G -->|"sem janela comum"| F
    G --> PQ["1. Pesquisa<br/>LLM DeepSeek V4.1 Flash planeja até 3 consultas;<br/>a ferramenta busca nos 93 lugares (ADR 0008)"]:::llm
    PQ --> L["2. Logística e Justiça<br/>código: trajeto de cada um, Menor Miséria,<br/>pontuação 45/35/20; não veta"]:::code
    L --> V["3. Validação<br/>código: horário, restrição, deslocamento acima de 75 min, orçamento;<br/>juiz LLM da 1ª passagem opcional"]:::hybrid
    V --> C1{"menos de 3 validados<br/>e menos de 2 voltas?"}:::decision
    C1 -->|"sim: pedido só com contagens de vetos"| PQ
    C1 -->|"não, e há validados"| CM["4. Comunicação<br/>LLM DeepSeek V4.1 Flash: título, acesso e<br/>por que combina, sem números"]:::llm
    C1 -->|"não, e nada passou"| F
    CM --> VT["Validação dos textos<br/>varredura em código (nomes e RAs do cofre)<br/>+ juiz LLM GLM 5.3 Flash (2ª passagem)"]:::hybrid
    VT -->|"reprovado: 1 reescrita, só dos reprovados"| CM
    VT -->|"aprovado ou já reescrito"| F["Finalização<br/>código: preço, horário, tempos, endereço e link<br/>do TikTok em cada cartão; aviso se houver menos de 3"]:::code
    F --> END(["Tela 3: 3 a 4 cartões para votação,<br/>ou o aviso de que nada atende o grupo"]):::data
```

**Como ler o diagrama**
- **Ciclo da Pesquisa:** volta enquanto houver menos de 3 lugares validados, no máximo 2 vezes (`avaliar_convergencia`). O pedido de nova busca leva só a contagem dos vetos por motivo (`PedidoNovaBusca`), nunca texto livre, para uma instrução injetada não passar de um agente a outro.
- **Saídas para o fim:** quando não há horário em que pelo menos 2 pessoas possam, o grafo vai direto da consolidação para o fim. Quando nada passa depois das 2 voltas, vai da Validação para o fim, sem chamar a Comunicação. É o caso do cenário padrão da #66.
- **Ciclo da Comunicação:** um cartão reprovado volta uma vez, e só os reprovados vão de novo para o LLM. Se continuar reprovado, o cartão sai com o texto de reserva por regras.
- **Limite de passos:** `recursion_limit` 40. O pior caso usa 16 passos.
- **Estado:** fica no `InMemorySaver`, por sala (`thread_id`).
- **Observabilidade:** cada nó é um span do Langfuse com entrada e saída escolhidas à mão, nunca o estado inteiro (ADR 0015). Desde o PR #89 (#73), os nomes dos spans são `agente_0_pessoal`, `agente_orquestrador_consolidar`, `agente_1_pesquisa`, `agente_2_logistica`, `agente_3_validacao`, `agente_4_comunicacao`, `agente_3_validacao_textos` e `agente_orquestrador_finalizar`, debaixo do span raiz `grafo_sala_multiagente`. Os links dos traces do demo estão nas Seções 8.11 e 8.13.
- **Diagrama do grafo compilado:** o desenhado pelo próprio LangGraph fica em [`grafo_agentes.mmd`](../entregas/semana-04/grafo_agentes.mmd), gerado pelo demo.

---

## 3. Os 5 Agentes como Implementados

Os exemplos de mensagem abaixo são do demo com LLM de 20/11, cenário de controle da #66 ([log](../entregas/semana-04/DEMO_MULTIAGENTE_LOG.txt)).

### 🔒 0. Agente Pessoal (`src/agentes/pessoal.py`, issue #65)
* **Natureza:** código, antes do rolê; LLM só depois do rolê, para ler o comentário de avaliação (RF-37).
* **O que faz:** um por membro, em paralelo. Lê os 4 campos da Tela 2 pelo interpretador (`src/interpretador/campos.py`, ADR 0009) e soma o log pessoal da pessoa (itens válidos por 180 dias; o que a pessoa escreve nos campos vale mais que o log). Depois, separa tudo em 4 canais:
  1. **orçamento** (teto), para o veto de orçamento da Validação, fica no cofre;
  2. **restrições duras**, para o veto de restrição, ficam no cofre;
  3. **preferências** (tipos, vibes, o que evitar, trecho do pedido sem nomes, regiões nem números), o **único canal público**, vão para o grupo;
  4. **logística** (origem, janelas e transporte), para a Logística e o cruzamento de horários, fica no cofre.
* **Depois do rolê:** o LLM propõe o que lembrar do comentário; a pessoa confirma; só enumerações vão para o log, sem o texto. Instrução sobre outra pessoa é ignorada, e proposta que se contradiz não é gravada.
* **Mensagem real:**
  > *"4 agentes pessoais responderam. Tipos pedidos: Ao Ar Livre (1 de 4), Restaurante (1 de 4). Restrições do grupo: 0. Itens de memória usados: 1. Melhor janela: sáb 21/11, 15h–18h (4 de 4 podem)."*

### 🔎 1. Pesquisa (`src/agentes/pesquisa.py`, issue #70)
* **Natureza:** LLM (DeepSeek V4.1 Flash pela OpenRouter, roteamento sem retenção) + ferramenta determinística de busca (`buscar_lugares_rag`, léxica ou vetorial, ADR 0012).
* **Sem *tool calling* nativo:** o LLM escreve até 3 consultas numa resposta só (JSON Schema estrito), o código executa a busca, e o LLM escolhe de 8 a 10 candidatos com `motivo` e `trecho` literal do documento. Assim é uma chamada a menos por rodada (RNF-14), e o modelo não decide quantas vezes buscar.
* **Zero alucinação (RNF-03):** candidato com id que a busca não trouxe, repetido ou com trecho que não está no documento é descartado. A ferramenta não entrega ao LLM preço, horário nem endereço.
* **Na volta da Validação:** recebe só o `PedidoNovaBusca` (contagens) e não repete lugares já vistos. Sem LLM, consultas e seleção saem por regras.
* **Limitação medida:** sem LLM, a nota léxica quase não separa os lugares, e a Pesquisa acha só 1 dos 5 viáveis do cenário de controle (Seção 8.8). Com LLM, acha 3.
* **Mensagem real:**
  > *"Encontrei 10 candidatos na base (3 consultas, busca lexica). Destaques: Fábrica de Bolos Valzira, Denise Suítez, The Coffee Talk, Restaurante Tete a Tete. Observação: A base trouxe poucas opções de ao ar livre…"*

### 🚌 2. Logística e Justiça (`src/agentes/logistica.py`, issue #67)
* **Natureza:** código (RNF-04, [ADR 0013](../decisoes/0013-deslocamento-e-menor-miseria.md)).
* **O que faz:** para cada candidato, usa a primeira janela comum em que o lugar abre. Para cada presente, estima o trajeto pelo meio mais barato que chega em até 75 min (ou o mais rápido, se nenhum chega) com o módulo de transporte das 35 RAs. Com isso, calcula a nota da Menor Miséria (o pior trajeto pesa mais que a média) e a pontuação: 45% aderência ao pedido, 35% justiça e 20% certeza do horário.
* **Não veta:** só mede e ordena. O trajeto de cada pessoa fica no cofre (`Cofre.analises`), e para o estado saem só agregados (`CandidatoAvaliado`).
* **Parecer por regra, sem LLM:** cita o meio do pior trajeto só quando pelo menos 2 presentes usam esse meio, para não apontar quem mora longe.
* **Mensagem real:**
  > *"Ranking Logístico: Uzuki Sushi (score 78; pior trajeto 109 min de ônibus/metrô; média 70 min), Farol Restaurante (score 77), Dudu Bar (score 77), Saguari Gastro House (score 73)…"*

### 🛡️ 3. Validação (`src/agentes/validacao.py` e `src/agentes/juiz.py`, issues #68 e #72)
* **Natureza:** código, mais o juiz LLM (GLM 5.3 Flash, [ADR 0014](../decisoes/0014-juiz-glm-5.3-flash.md)) em 2 passagens.
* **Vetos em código** (`validar_candidatos_regras`). Todos os motivos de cada lugar são contados:
  - **horário:** o lugar não abre na janela comum, ou o evento já passou (`encerrado`);
  - **restrição:** o texto do vídeo não comprova a restrição do grupo (ex.: opção vegetariana);
  - **deslocamento:** o trajeto de algum presente passa de 75 min, ou não há trajeto estimado para ninguém;
  - **orçamento:** consumo mais ida e volta passa do teto de algum presente na janela.
* **Seleção dos cartões:** até 4, na ordem do ranking, no máximo 2 por RA e sem nome repetido.
* **Juiz, 1ª passagem (opcional, `juiz_parecer=True`):** confere os motivos da Pesquisa contra o documento do lugar. Só o que **contradiz** é derrubado; `sem_apoio` fica.
* **Validação dos textos:**
  - uma varredura em código procura número, nome ou parte de nome de membro e a RA de onde alguém sai, com os dados do cofre, que o juiz não vê;
  - o juiz, 2ª passagem, procura contradição com a base e exposição de origem, orçamento, restrição ou texto pessoal;
  - qualquer achado manda o cartão para reescrita.
* **Mensagens reais:**
  > *"Só 2 lugares passaram (vetos: 3 por horario, 8 por orcamento, 4 por deslocamento). Pesquisa, preciso de mais 1 candidatos."*
  >
  > *"3 cartões aprovados: a varredura não achou número, nome nem origem de ninguém, e o juiz (LLM) não achou contradição nem exposição."*

### 💬 4. Comunicação (`src/agentes/comunicacao.py`, issue #69)
* **Natureza:** LLM (DeepSeek V4.1 Flash), com o prompt do Anfitrião e JSON Schema estrito.
* **O que recebe:** só fatos do grupo por cartão: nome, tipo e região do lugar, trechos do documento citados pela Pesquisa e sinais booleanos (chegada equilibrada, cabe no orçamento do grupo, todos podem na janela). Nenhum tempo, valor ou origem de ninguém.
* **O que escreve:** `titulo`, `resumo_acesso` e `por_que_combina`, sem números. Preço, horário, tempos, endereço e link do TikTok entram por código na finalização. Sem LLM, ou com o cartão reprovado duas vezes, o texto sai por regras (`texto_por` diz qual).
* **Pendência:** o grafo usa `montar_fatos` e `escrever` para poder reescrever um cartão só. Juntar com o `executar_agente_comunicacao` da #69 fica para depois da entrega.
* **Mensagem real:**
  > *"Escrevi 3 cartões: A) Jantar caprichado e conversa tranquila; B) Fatias de bolo sem pesar no bolso; C) Confeitaria aconchegante para conversar."*

---

## 4. Estado do Grafo (`MultiAgentState`) e Cofre

O estado do grafo (`src/agentes/estado.py`, issue #64) só tem dados públicos. `serializar_estado` recusa o estado que tiver nome, usuário, teto ou origem de alguém. Os campos, por agente:

```python
class MultiAgentState(TypedDict, total=False):
    # entrada
    sala_id: str                                           # código da sala (não identifica ninguém)
    trace_url: str | None                                  # link do trace no Langfuse
    membros: list[str]                                     # marcadores m1..mN; o Send abre um Agente Pessoal por um
    # Agente 0 (Pessoal) -> grupo
    membros_anonimos: Annotated[list[dict], operator.add]  # canal 3 de cada membro, em paralelo
    preferencias_grupo: dict                               # tipos e vibes agregados, restrições sem dizer de quem
    # Agente 1 (Pesquisa)
    candidatos_pesquisa: list[dict]                        # id, motivo e trecho literal conferido
    documentos: dict[str, dict]                            # documentos da base que a Pesquisa leu
    vistos: list[str]                                      # ids já devolvidos (não repetir)
    pedido_nova_busca: dict | None                         # PedidoNovaBusca: só contagens
    iteracao_pesquisa: int                                 # voltas Validação -> Pesquisa (máximo 2)
    # Agente 2 (Logística)
    candidatos_avaliados: list[dict]                       # agregados de deslocamento e nota
    # Agente 3 (Validação)
    julgados: list[str]                                    # ids que já passaram pelo juiz do parecer
    relatorio_validacao: dict                              # aprovados, vetos (id e motivo) e contagem
    candidatos_validados: list[dict]                       # os escolhidos para os cartões
    # Agente 4 (Comunicação) e validação dos textos
    fatos: list[dict]                                      # o que a Comunicação pode afirmar de cada cartão
    cartoes: list[dict]                                    # textos escritos pela Comunicação
    cartoes_por_llm: bool
    reprovados: dict[str, list[str]]                       # cartão -> motivos (só enumerações)
    reescritas: int                                        # voltas Validação -> Comunicação (máximo 1)
    # saída
    resultado_final_cartoes: list[dict]                    # cartões públicos para a votação (Tela 3)
    mensagens: Annotated[list[dict], operator.add]         # a conversa entre os agentes
    historico_erros: Annotated[list[str], operator.add]    # vetos, reprovações e falhas, em ordem
```

**O cofre** (`Cofre`, em `src/agentes/contratos.py`) fica fora do estado, no servidor, e só os nós de código o leem. Ele guarda:
- os membros, com nome e os 4 campos;
- os perfis efetivos (campos mais log pessoal);
- as janelas comuns;
- a base de lugares;
- o trajeto de cada pessoa por lugar (`analises`);
- os cartões com o custo e o tempo de cada um (`sugestoes`, para a visão privada).

Para o LLM, só vai o que está no estado e nos fatos dos cartões. Um teste confere, em cada corpo enviado à OpenRouter, que não há nome, teto nem origem de membro.

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
* **Status:** Concluída (PR [#77](https://github.com/Residencia-IA-Challenge-2-Grupo-7/residencia-ia-g7-challenge2/pull/77), mesclado em 17/11)
* **O que foi feito:**
  - `MultiAgentState` (TypedDict) com os campos da issue (`sala_id`, `membros_anonimos`, `preferencias_grupo`, `candidatos_pesquisa`, `candidatos_avaliados`, `candidatos_validados`, `resultado_final_cartoes`, `iteracao_pesquisa`, `historico_erros`), mais `trace_url` e os campos auxiliares do grafo (documentos lidos, ids já vistos, pedido de nova busca, cartões, reprovações e mensagens entre agentes).
  - Reducers `operator.add` em `membros_anonimos` (um perfil por Agente Pessoal, em paralelo), `mensagens` e `historico_erros`.
  - `serializar_estado` e `desserializar_estado`, que validam o estado com um espelho Pydantic (`EstadoSerializado`) com `extra="forbid"`.
* **Decisões Técnicas e Arquitetura:**
  - **Os dados privados de cada membro não entram no estado.** Os 4 campos, o teto, a origem e o nome ficam num *cofre* (`contratos.py`) que só os nós de código leem. Assim nada disso vai para o checkpoint do LangGraph, para o Langfuse ou para um LLM (RNF-02). A issue sugeria separar canais privados e públicos dentro do estado; tirar os privados do estado é mais seguro.
  - **A serialização recusa vazamento** (`VazamentoNoEstado`) em dois casos:
    - chave do cofre (`teto`, `origem`, `usuario`, `por_participante`…) em qualquer nível;
    - id de usuário, nome ou parte de nome composto de algum membro em qualquer texto, sem diferenciar maiúsculas nem acentos.
  - **Na revisão da Maria Eduarda**, a varredura de nomes passou a tirar os nomes dos lugares da base e a ignorar partículas. Sem isso, o lugar "Maria Fumaça" e a palavra "dos" dariam falso positivo.
* **Arquivos:** `src/agentes/estado.py`, `src/agentes/contratos.py`, `src/agentes/__init__.py`, `tests/test_multiagent_state.py`, `AGENTS.md` (convenção de commits).
* **Testes e Validação:**
  - `pytest -v tests/test_multiagent_state.py`: 22 testes sem rede (campos, reducers, ida e volta em JSON, chave privada, nome em minúsculas, nome composto, "Maria Fumaça", partículas, campo desconhecido).
  - `docker compose up -d`: 616 testes passaram no container; CI verde no PR.

---

### 8.2. Issue #65 — Agente 0 (Pessoal): Sanitização de PII e Segregação dos 4 Canais
* **Responsável:** Cauan Soares (`@cadasiso`)
* **Status:** Concluída, em revisão (PR [#80](https://github.com/Residencia-IA-Challenge-2-Grupo-7/residencia-ia-g7-challenge2/pull/80), junto com a #70)
* **O que foi feito:** `executar_agente_pessoal(campos_usuario)` interpreta os 4 campos por regras (`src/interpretador/campos.py`). Devolve `PerfilMembroAnonimizado`, identificado só pelo marcador da sala (m1, m2…), com 4 canais:
  1. orçamento: teto individual, para os vetos financeiros da Validação;
  2. restrições duras: para os vetos da Validação;
  3. preferências anônimas: para o perfil do grupo e a Pesquisa. É o único canal público;
  4. origem, janelas e transporte: para a Logística e o cruzamento de janelas.

  O agente também lê o log pessoal antes do rolê. Depois do rolê, um LLM transforma o comentário da pessoa numa proposta de memória.
* **Decisões Técnicas e Arquitetura:**
  - **Proteção contra vazamento em log:** os canais 1, 2 e 4 ficam fora do `repr`, então um `print` do objeto não mostra teto nem origem.
  - **Pedido sanitizado:** o pedido do campo 4 que vai ao grupo sai sem nomes da sala, regiões e números.
  - **Entrada fechada:** campos fora do contrato e marcador que não seja da sala (m1, m2…) são erro.
  - **Log pessoal:** guarda só listas fechadas com data, nunca texto livre, o que evita envenenar a memória. Um item vale por 180 dias, e o que a pessoa escreve nos campos vence o log.
  - **Pós-rolê:** o LLM só propõe o que guardar. O código descarta trecho que não está no comentário, e nada é gravado sem a confirmação da pessoa.
  - **Cliente LLM:** `src/agentes/llm.py` é o cliente da OpenRouter dos agentes, com JSON Schema estrito, a mesma chave do projeto e o roteamento sem retenção. Com ele, `langgraph` entrou no `requirements.txt` (ADR 0015).
* **Arquivos:** `src/agentes/pessoal.py`, `src/agentes/llm.py`, `src/agentes/prompts/pessoal_pos_role.md`, `requirements.txt`, `tests/test_agente_pessoal.py`.
* **Testes e Validação:** `pytest -v tests/test_agente_pessoal.py`, com 15 testes sem rede: os 4 canais, o canal público sem nome, origem, valor nem id, o `repr`, campos fora do contrato, o log pessoal com validade e o pós-rolê com trecho inventado.

---

### 8.3. Issue #66 — Dataset de Teste com Cenário dos 4 Amigos no DF (Golden de Rolê)
* **Responsável:** Samara Letícia (`@samarawwleticia`)
* **Status:** Concluída (revisão do PR atendida)
* **O que foi feito:**
  - Criação de `data/cenarios_teste_multiagente.json` com dois cenários de pessoas fictícias (marcadores `m1` a `m4`), cada um com código de sala fixo:
    - `cenario_padrao_4_amigos` (`ROLE-PADR`), o pedido pela issue: Ceilândia (teto R$ 40, metrô, vegetariana), Águas Claras (R$ 70, ônibus/metrô, ar livre), Asa Norte/Plano Piloto (R$ 120, carro/Uber, gastronomia) e Sobradinho (R$ 50, transporte público, "nada muito longe");
    - `cenario_controle_viavel` (`ROLE-CTRL`), o mesmo grupo com só duas mudanças (m1 sem a restrição vegetariana e m4 saindo de Taguatinga), para cobrir o caminho feliz.
  - Para cada amigo, os 4 campos de texto da Tela 2 como seriam digitados (`campos_tela2`) e o que o Agente 0 deve entender deles (`interpretacao_esperada`: RA oficial, macrorregião, teto, janelas, tipos, vibes, restrições e transporte).
  - Para cada cenário, `resultados_esperados`: janela comum (sábado 21/11, 15h–18h, os 4 presentes), teto do grupo (R$ 40), restrições duras, veredito, lugares viáveis, lugares plausíveis com os vetos esperados e lugares que nunca devem ser sugeridos.
  - `src/agentes/cenarios.py`: `carregar_cenario()` e `para_entrada_do_grafo()`, a conversão única de um cenário para a entrada do fluxo (`{"codigo", "agora", "membros"}`), para a demonstração (#74) e os testes da #67 e da #68.
  - Suíte `tests/test_cenarios_multiagente.py` com 97 testes.
* **Decisões Técnicas e Arquitetura:**
  - *Entrada e gabarito no mesmo registro:* o texto cru alimenta o Agente 0 e a demonstração; a interpretação esperada é o gabarito. O teste roda `interpretar_campos()` sobre cada texto e exige a saída exata. A conversão para o grafo leva só o que a Tela 2 teria recebido: nada do gabarito nem os marcadores chegam ao sistema testado.
  - *Data de referência fixa (`agora_referencia` = 17/11/2026 12h):* "sábado das 14h às 22h" só vira data relativa a um "agora". Sem ela, o teste quebraria sozinho depois do sábado (pendência `janela_passada`). A conversão para o grafo sempre usa esse valor.
  - *Dois cenários: estresse e controle.* O cenário pedido na issue **não tem lugar viável**: o veredito é `sem_lugar_viavel` e o comportamento esperado é vetar tudo, devolver à Pesquisa só a contagem dos vetos (até 2 voltas) e avisar que há menos de 3 opções, sem inventar cartão (RNF-03). Com só esse cenário, um sistema que nunca gera cartão passaria em tudo e a demonstração terminaria vazia; por isso o cenário de controle tem 5 lugares viáveis (Fábrica de Bolos Valzira, Denise Suítez, Debeche Açaí, Golden Black e Saguari Gastro House). Mudar só uma das duas coisas, ou subir o teto do m1 para R$ 80, ainda deixa 0 viáveis.
  - *Causa estável do veredito do cenário padrão:* a restrição vegetariana com o teto de R$ 40. Só 3 lugares da base comprovam opção vegetariana (Pizzaria Natureto, Yaki Nikuya e The Plenty) e nenhum cabe no teto do m1 com a passagem. Com o estimador atual de transporte público, o deslocamento também veta os 93 lugares (Ceilândia e Sobradinho ficam em pontas opostas do DF), mas isso depende da calibração do `estimar_deslocamento` (#67); o teste do veredito não depende dela e continua passando com um estimador simulado que dá 10 min para tudo.
  - *Regra dos vetos "nem na melhor hipótese":* `deslocamento` usa o meio mais rápido da pessoa contra o teto de 75 min da Logística, o mesmo para todos (o "nada muito longe" do m4 fica só no texto, porque o sistema não lê minutos da Tela 2); `orcamento` usa o meio mais barato (consumo médio + ida e volta). Os motivos são os de `MotivoVeto` (`src/agentes/contratos.py`).
  - *Vetos do lugar separados dos vetos por membro:* `vetos_do_lugar` (horário, encerrado) e `vetos_por_membro` (deslocamento, orçamento, restrição, sempre com alguém barrado). A saída da Validação (`Veto(id, motivo)`) é comparada só pelo conjunto de motivos de cada lugar, porque ela não diz quem foi barrado (RNF-02); os marcadores servem só aos testes internos da Logística e da Validação.
  - *Oráculo independente:* o teste recalcula os vetos com regra própria e usa do repositório só as medidas (`estimar_deslocamento` e `ler_funcionamento`) e os parâmetros (teto de 75 min, motivos de veto), não a decisão dos agentes; assim o gabarito pode pegar erro neles em vez de repeti-los.
  - *Lugares citados por `id` da base 2FA:* o teste confere id, nome e RA contra `data/banco_aprovado_2fa.json` (RNF-03, RNF-04).
  - *Achados para outras issues:* (1) a Hamburgueria Espacial está como Taguatinga, mas endereço e coordenada são de Sobradinho; no cenário de controle a armadilha se inverte (mesma RA do m4, mas longe de verdade); (2) o gerador atual de cartões (`src/salas/sugestoes.py`) não descarta trajetos acima de 75 min: para o cenário padrão sugere o Cachorrão da 5 (Santa Maria) com mais de 3 horas para quem sai de Sobradinho; (3) o Golden Black (R$ 1,99) é viável no controle, mas o valor é preço de promoção (Raio-X da base) e deve ser revisado pela curadoria antes da demonstração. Os três estão anotados no dataset e devem orientar a Logística (#67), a Validação (#68) e a curadoria da base.
* **Arquivos:**
  - `data/cenarios_teste_multiagente.json`
  - `src/agentes/cenarios.py`
  - `tests/test_cenarios_multiagente.py`
  - `docs/semanas/semana-04.md` (esta seção) e `STATUS.md`
* **Testes e Validação:**
  - `pytest -v tests/test_cenarios_multiagente.py`: 97 testes aprovados (estrutura, 35 RAs oficiais, vocabulário do interpretador, contraste dos perfis, `interpretar_campos()` reproduzindo o gabarito, janela comum via `cruzar()`, teto via `teto_seguro_grupo()`, vetos de cada lugar citado nos dois cenários, lugares viáveis iguais aos calculados, causa estável do veredito, diferença mínima entre os cenários e conversão para a entrada do grafo).
  - Testes de mutação manuais: retirar um veto anotado, trocar um viável, pôr `horario` em `vetos_por_membro` ou mudar um teto no JSON faz os testes correspondentes falharem; simular um estimador que dá 10 min para tudo não muda o veredito do cenário padrão.
  - `make test-local`: 742 aprovados, 1 pulado (`test_ambiente_container_ok`, só roda no Docker).

---

### 8.4. Issue #67 — Agente 2 (Logística & Justiça): Deslocamento e Regra da Menor Miséria
* **Responsável:** Samara Letícia (`@samarawwleticia`)
* **Status:** Concluída
* **O que foi feito:**
  - `src/agentes/logistica.py` com `executar_agente_logistica(candidatos, origens_membros, *, lugares, janelas, agora, analises=None) -> list[dict]`. Para cada candidato da Pesquisa:
    1. escolhe a primeira janela comum em que o lugar não está fechado nem encerrado, com a certeza do horário (aberto 1,0; provável 0,7; incerto 0,4; fechado em todas as janelas: a primeira janela, com certeza 0);
    2. calcula o trajeto de cada membro que pode na janela pelo meio que ele usaria: o mais barato que chega em até 75 min, senão o mais rápido (`escolher_meio`), via `estimar_deslocamento` com a reserva das salas;
    3. dá a `nota_menor_miseria` pelos tempos (pior trajeto acima de 20 min + desigualdade entre o pior e o melhor, ADR 0013);
    4. calcula a pontuação de 0 a 1: 45% aderência, 35% justiça, 20% certeza do horário; ordena por pontuação, nota de justiça e id.
  - `gerar_parecer(avaliados, analises=None)`: texto feito por regra para a mensagem do agente. Exemplo dos testes (grupo de Ceilândia, Samambaia e Plano Piloto; lugares sintéticos no ponto de cada RA): *"Ranking Logístico: Lugar Águas Claras (score 68; pior trajeto 85 min de ônibus/metrô; média 62 min), Lugar Taguatinga (score 66), Lugar Plano Piloto (score 63; pior trajeto 120 min de ônibus/metrô; média 86 min). 3 lugares com trajeto acima de 75 min para alguém do grupo."*
  - `escolher_meio` e `TEMPO_ACEITAVEL_MIN` saíram de `src/salas/sugestoes.py` para `src/logistica/transporte_df.py`: a Tela 3 e o agente usam a mesma regra (refatoração sem mudança de comportamento).
* **Decisões Técnicas e Arquitetura:**
  - *Público e privado separados (RNF-02):* o retorno é uma lista de `CandidatoAvaliado` (Pydantic com `extra="forbid"`), só com agregados (pior trajeto, média, diferença, nota). O trajeto de cada pessoa vai para `analises` (`Cofre.analises`), que a Validação usa no orçamento individual. Um campo privado acrescentado por engano à saída faz o código falhar em vez de vazar.
  - *A Logística mede, não veta:* lugar fechado ou com trajeto acima de 75 min fica com nota baixa e segue para a Validação (#68), que tem os motivos `horario`, `encerrado` e `deslocamento`. Cada agente com uma responsabilidade.
  - *Aderência sem busca vetorial (RNF-04):* os pesos da Tela 3 (tipo 0,45, vibe 0,25, restrição 0,15, busca 0,15) sem o termo da busca, redistribuídos na mesma proporção (÷ 0,85). A busca usa embeddings e não roda offline; a ordem relativa de tipo, vibe e restrição continua a mesma.
  - *`agora` obrigatório:* dá o ano das datas dos vídeos (`ano_do_lugar`); sem ele a função dependeria do relógio e deixaria de ser determinística.
  - *Escala do score:* `pontuacao` de 0 a 1, como `Sugestao.pontuacao`; o parecer mostra ×100 ("score 81").
  - *Parecer sem identificar ninguém:* cita o meio do pior trajeto pelo rótulo genérico ("ônibus/metrô", "Uber/99") só quando pelo menos 2 presentes usariam esse meio naquele lugar (`MINIMO_PARA_CITAR_MEIO`); com um só, "de carro" apontaria quem mora longe, e o texto fica só "pior trajeto 50 min". Nunca cita o marcador nem a RA; trajetos acima de 75 min só em contagem. Achado da revisão do PR com o `cenario_controle_viavel` da #66, em que só o m3 vai de carro ou de app. Primeiro e último colocados vêm com os tempos, os do meio só com o score, para o texto não crescer com 8 a 10 candidatos.
  - *Vai de Graça:* o deslocamento usa o início do trecho aberto da janela; num domingo ou feriado, ônibus e metrô custam zero.
* **Arquivos:**
  - `src/agentes/logistica.py` (novo)
  - `src/logistica/transporte_df.py` (`escolher_meio`, `TEMPO_ACEITAVEL_MIN`)
  - `src/salas/sugestoes.py` (passa a usar `escolher_meio`)
  - `tests/test_agente_logistica.py` (novo, 40 testes)
  - `tests/test_transporte_df.py` (6 testes de `escolher_meio`)
  - `docs/semanas/semana-04.md` (esta seção) e `STATUS.md`
* **Testes e Validação:**
  - `pytest -v tests/test_agente_logistica.py`: 40 aprovados (21 com lugares sintéticos e 19 com os cenários da #66; 2 dos sintéticos para o meio do pior trajeto: não aparece com uma pessoa só nesse meio, aparece com duas). Cenários periféricos com lugares sintéticos no ponto de cada RA:
    - Ceilândia + Samambaia + Plano Piloto: Taguatinga (meio do caminho) vence o Plano, com pior trajeto menor e nota maior;
    - Ceilândia + Sobradinho (pontas opostas): pior trajeto acima de 75 min, avaliado sem veto, nota abaixo de 60% da de um grupo que mora perto e maior que zero;
    - Ceilândia com "metrô ou Uber": vai de Uber/99 até o Plano (~120 min de ônibus/metrô contra ~68 de app) e de ônibus/metrô até Taguatinga (~40 min);
    - domingo: ônibus e metrô a R$ 0,00 para todos.
  - Também cobertos: pesos 45/35/20 recalculados à mão, lugar pedido pelo grupo subindo no ranking, lugar fechado com certeza 0 (perde exatamente 0,20), primeira janela em que o lugar abre, saída igual ao contrato `CandidatoAvaliado` e vazia em `dados_privados_no_estado`, nenhuma RA de origem nem teto na saída ou no parecer, mesma saída em qualquer ordem de entrada, id fora da base, sem janela e lugar sem coordenada (nota 30, estimativa provisória).
  - `pytest -v tests/test_transporte_df.py`: 6 testes novos de `escolher_meio` (mais barato a tempo, mais rápido quando nada cabe, limite de 75 min inclusivo, desempate pelo tempo, opções sem estimativa). Os testes existentes de `sugestoes` passam sem alteração, o que prova a refatoração.
  - `make test-local`: 789 aprovados, 1 pulado (`test_ambiente_container_ok`, só roda no Docker), já com a `main` do #82 mesclada (os 97 testes de `tests/test_cenarios_multiagente.py` incluídos).
  - Cenários da #66 com a base real (19 testes): os dois cenários de `data/cenarios_teste_multiagente.json` passam pelo agente como no grafo (4 campos -> `interpretar_campos` -> `cruzar` -> 93 lugares), o que a revisão do PR tinha feito à mão e que achou o meio do pior trajeto apontando o m3:
    - os 93 lugares saem avaliados, no contrato `CandidatoAvaliado` e em ordem de pontuação;
    - nos 12 lugares do gabarito (locais plausíveis e "nunca sugerir"), quem passa de 75 min no trajeto do agente é exatamente quem o gabarito veta por deslocamento (o gabarito usa o meio mais rápido; o agente, o mais barato que chega em até 75 min, senão o mais rápido: as duas regras vetam as mesmas pessoas);
    - em todos os 93 lugares, o parecer só cita o meio do pior trajeto quando pelo menos 2 presentes o usam, e o cenário de controle tem os dois casos (meio único que some e meio de 3 pessoas que aparece), para o teste não passar por falta de caso;
    - saída e parecer passam na varredura do cofre do #64 (`dados_privados_no_estado`) com os nomes fictícios dos amigos.
  - Teste de mutação: voltar `MINIMO_PARA_CITAR_MEIO` para 1 (o bug da revisão) faz 3 testes falharem, 2 deles dos cenários.

---

### 8.5. Issue #68 — Agente 3 (Validação): Filtros Determinísticos de Horário, Orçamento e Restrições
* **Responsável:** Maria Eduarda (`@eduarda-ogomes`)
* **Status:** Concluída (PR pronto com testes e revisão atendida)
* **O que foi feito:**
  - Implementação da camada completa de Vetos Duros Determinísticos do Agente de Validação em código Python puro (`src/agentes/validacao.py`).
  - Veto 1 (Orçamento Sigiloso com Deslocamento): `dentro_do_orcamento_individual` (com alias `cabe_para_cada_um`), conferindo se consumo estimado + custo de deslocamento de ida e volta <= teto individual de cada membro participante, ignorando membros sem teto informado (RF-17). Trata com robustez dados de trajetos ausentes (`None`).
  - Veto 2 e 3 (Horário e Validade de Evento): `validar_horario_e_evento`, integrando com `horario_lugar.py` para verificar sobreposição com a janela comum do grupo (`aberto`, `provavel`, `incerto`) e vetando locais fechados no dia/horário (`"horario"`) ou eventos com datas expiradas (`"encerrado"`).
  - Veto 4 (Restrições Duras): `atende_restricoes_duras`, conferindo compatibilidade contra `TERMOS_RESTRICAO` oficial de `src/salas/sugestoes.py`, vetando qualquer local que não comprove evidência da restrição dura no texto/vídeo da base.
  - Veto de Deslocamento (Menor Miséria): `validar_deslocamento_membros`, vetando candidatos cujo trajeto para qualquer membro presente exceda 75 minutos (`TEMPO_ACEITAVEL_MIN`), alinhado à ADR 0013 e aos cenários de controle da Issue #66.
  - Orquestrador determinístico `validar_candidatos_regras`, que avalia todos os 4 filtros para cada candidato (acumulando todos os motivos violados em `contagem` para orientar a Pesquisa e registrando o primeiro veto em `vetos`), extraindo trajetos e tetos diretamente do `Cofre`.
  - Função de feedback condicional `gerar_pedido_nova_busca` para alimentar o loop do LangGraph com `PedidoNovaBusca` quando restarem menos de 3 candidatos viáveis.
* **Decisões Técnicas e Arquitetura:**
  - *RNF-04 (Cálculos Fora do LLM):* Toda a checagem de viabilidade temporal, financeira, geográfica e alimentar roda em Python puro antes de qualquer acionamento de LLM, eliminando risco de alucinação aritmética.
  - *RF-17 e RNF-02 (Orçamento Sigiloso):* A validação de gastos é estritamente individual e roda na memória do servidor sem expor quem estourou o teto nem vazar valores em reais para o estado compartilhado ou para prompts.
  - *ADR 0013 e Menor Miséria:* Aplicação do limite de 75 min por membro, garantindo que locais isolados com deslocamento abusivo não alcancem a geração de cartões.
  - *Ciclo Condicional LangGraph:* O relatório estruturado agrega as contagens completas de todos os motivos de veto (`horario`, `orcamento`, `restricao`, `encerrado`, `deslocamento`), permitindo à Pesquisa recalibrar a busca vetorial sem quebrar a privacidade.
* **Arquivos:**
  - `src/agentes/validacao.py`
  - `tests/test_agente_validacao_regras.py`
* **Testes e Validação:**
  - 14 testes unitários e de integração em `tests/test_agente_validacao_regras.py` cobrindo todos os filtros determinísticos, tratamento de `None` vindo da Logística, veto de deslocamento > 75 min e os dois cenários reais da Issue #66 (cenário padrão com 0 aprovados e cenário de controle aprovando exatamente os 5 lugares viáveis esperados).
  - Suíte completa do repositório validada localmente via pytest com 100% de sucesso.

---

### 8.6. Issue #69 — Agente 4 (Comunicação): Prompt do Anfitrião e Formatação de Cartões em JSON
* **Responsável:** Maria Carolina (`@mcznh`)
* **Status:** Concluída
* **O que foi feito:**
  - Criação do Agente de Síntese e Comunicação (`src/agentes/comunicacao.py`) e da função principal `executar_agente_comunicacao(candidatos_validados) -> list[dict]`.
  - Elaboração do system prompt do Anfitrião de Brasília (`src/agentes/prompts/comunicacao.md`) com tom caloroso, empático e candango.
  - Implementação do preenchimento determinístico de preços médios, tempos de trajeto, links do TikTok e endereços oficiais no esquema `Sugestao` da aplicação.
  - Validação estrita dos cartões de saída via Pydantic (`CartaoSugestaoValidado`) e integração com o nó do LangGraph (`no_comunicacao`).
  - Implementação de fallback determinístico offline/gracioso para operação sem chave externa ou em caso de instabilidade na API.
  - Suíte completa de 10 testes unitários em `tests/test_agente_comunicacao.py`.
* **Decisões Técnicas e Arquitetura:**
  - *RF-06 (Apresentação Clara de Sugestões):* Os cartões contêm títulos convidativos (`titulo`), justificativas de afinidade com o grupo (`por_que_combina`) e resumos de conveniência logística (`resumo_acesso`).
  - *RNF-02 (Privacidade e Orçamento Sigiloso):* Zero citação de quem tem restrições alimentares, de onde cada membro sai ou quanto cada um pode gastar. O Anfitrião recebe apenas fatos aprovados e agregados anônimos do grupo.
  - *RNF-04 (Cálculos Fora do LLM):* Todos os dados numéricos (consumo estimado, faixa de gasto com transporte, tempos de chegada e notas de justiça) são preenchidos por código determinístico a partir da base oficial curada de 93 lugares (2FA) e dos cálculos de logística.
  - *JSON Schema Estrito:* Saída gerada pela LLM validada contra o contrato Pydantic `SaidaComunicacao` com `extra="forbid"`, eliminando alucinações de formato.
* **Arquivos:**
  - `src/agentes/comunicacao.py`
  - `src/agentes/prompts/comunicacao.md`
  - `src/agentes/llm.py`
  - `tests/test_agente_comunicacao.py`
* **Testes e Validação:**
  - `tests/test_agente_comunicacao.py`: 10 testes aprovados cobrindo geração offline, mock de LLM, preenchimento determinístico, sigilo RNF-02, fallbacks, compatibilidade com dataclass `Sugestao`, instâncias de `CandidatoAvaliado` e integração com `no_comunicacao`.
  - Suíte completa de testes locais passando via pytest.


---

### 8.7. Issue #70 — Agente 1 (Pesquisa): Prompt do Curador + Tool RAG dos 93 Lugares do TikTok
* **Responsável:** Cauan Soares (`@cadasiso`)
* **Status:** Concluída, em revisão (PR [#80](https://github.com/Residencia-IA-Challenge-2-Grupo-7/residencia-ia-g7-challenge2/pull/80))
* **O que foi feito:**
  - `buscar_lugares_rag(query, categorias)` é a ferramenta determinística, sobre a base oficial de 93 lugares (ADR 0008), com a busca léxica ou vetorial do RAG (ADR 0012).
  - `executar_agente_pesquisa(perfil_grupo, feedback_validacao=None)` devolve de 8 a 10 candidatos com `fonte_id`, `nome`, `tipo`, `motivo` e `trecho_citado`. O LLM é o DeepSeek V4.1 Flash pela OpenRouter.
* **Decisões Técnicas e Arquitetura:**
  - **Sem *tool calling* nativo:** o LLM escreve até 3 consultas numa resposta só, com JSON Schema estrito, e o código executa a ferramenta. É uma chamada de LLM a menos por rodada (RNF-14), e o modelo não decide quantas vezes buscar.
  - **Zero alucinação (RNF-03):** o código descarta candidato com id que a busca não trouxe, repetido ou com `trecho_citado` que não está no documento.
  - **A ferramenta não entrega ao LLM preço, horário nem endereço.** Esses dados vão por código para a Logística e a Validação.
  - **Entrada validada:** o perfil passa pelo esquema `PreferenciasGrupo`, e o retorno da Validação pelo `PedidoNovaBusca`, que só tem contagens de veto. Chave a mais, como um teto ou um texto livre, é erro antes de chegar ao LLM (RNF-02).
  - **Reserva por regras:** sem chave ou com o LLM fora do ar, a Pesquisa funciona por regras, e os vetos de orçamento e de horário ampliam a busca.
* **Arquivos:** `src/agentes/pesquisa.py`, `src/agentes/ferramentas.py`, `src/agentes/prompts/pesquisa.md`, `tests/test_agente_pesquisa.py`.
* **Testes e Validação:**
  - `pytest -v tests/test_agente_pesquisa.py`: 14 testes sem rede, com um LLM falso que inventa trecho, cita id que não existe e repete candidato.
  - `docker compose up -d`: 645 testes passaram no container.

---

### 8.8. Issue #71 — Orquestrador do Grafo no LangGraph com Ciclo Condicional Pesquisa-Validação
* **Responsável:** Cauan Soares (`@cadasiso`)
* **Status:** Concluída, em revisão (no PR [#80](https://github.com/Residencia-IA-Challenge-2-Grupo-7/residencia-ia-g7-challenge2/pull/80), junto com as #65 e #70)
* **O que foi feito:**
  - `src/agentes/grafo.py` monta o `StateGraph` com os nós `no_pessoal` (um por membro, em paralelo com `Send`), `no_consolidar_grupo`, `no_pesquisa`, `no_logistica`, `no_validacao`, `no_comunicacao`, `no_validacao_textos` e `no_finalizar`, e exporta `executar_fluxo_multiagente(dados_sala)`.
  - O grafo chama as implementações das issues de cada agente:
    - Logística (#67): `executar_agente_logistica` e `gerar_parecer`;
    - Validação (#68): `validar_candidatos_regras`.
  - A aresta condicional `avaliar_convergencia` tem três saídas:
    - volta para a Pesquisa enquanto houver menos de 3 lugares validados e menos de 2 voltas;
    - segue para a Comunicação quando há pelo menos um validado;
    - vai direto para o fim quando nada passou.
  - `validacao.selecionar_cartoes` escolhe os cartões na ordem do ranking da Logística: até 4, no máximo 2 por RA e sem nome repetido (a base tem o mesmo lugar em mais de um vídeo).
  - A varredura de vazamento dos cartões (`varrer_cartao`, `verificar_cartoes`), em código, foi para o fim de `validacao.py`, sem mudar as funções da #68. Ela procura número, nome ou parte de nome composto de membro (sem contar nomes de lugares da base) e a RA de onde alguém sai (sem contar formas que são palavras comuns, como "plano" e "gama").
  - **O juiz LLM ficou de fora:** é a entrega da #72 (PR #86, `src/agentes/juiz.py`). Uma versão provisória dele estava neste PR e foi tirada na revisão. Depois que o #86 entrou, o grafo passou a chamar o `juiz.py` (ver Seção 8.11).
  - As funções da Comunicação que o grafo usa (`montar_fatos`, `escrever`, `texto_reserva`) foram para o fim de `comunicacao.py`, ao lado do `executar_agente_comunicacao` da #69.
* **Decisões Técnicas e Arquitetura:**
  - **Sem aprovado, sem Comunicação:** com 0 lugares depois das 2 voltas, o grafo não chama o LLM para escrever cartão nenhum. As mensagens dizem que nada passou e que o grupo precisa flexibilizar algum critério. Antes, a Validação dizia "Autorizado para a síntese" e a varredura dizia "Cartões aprovados" mesmo com 0 cartões.
  - **Menos de 3 opções é dito ao grupo:** o fim avisa "Só N cartões prontos (menos de 3 opções viáveis na base)", em vez de completar com lugar vetado (RNF-03).
  - **Janela parcial:** a Logística e a Validação avaliam cada lugar na primeira janela comum em que ele abre, que pode não ter todos. O cartão mostra a contagem ("3 de 4 podem"), e a Validação avisa quantos cartões estão nessa situação.
  - **Dois ajustes na Validação, apontados na revisão do PR #84:**
    - o orçamento só conta os presentes da janela em que o lugar foi avaliado;
    - lugar sem nenhum trajeto estimado é vetado por deslocamento, em vez de passar com R$ 0 de transporte.
  - **Comunicação:** o grafo ainda usa o esquema `SaidaComunicacao` para poder pedir a reescrita de um cartão só. Juntar com `executar_agente_comunicacao` (#69) fica para depois da entrega de 19/11.
  - **Revisão do PR #80 (Maria Eduarda), atendida em 19/11:**
    - na reescrita, só os cartões reprovados vão para o LLM; a resposta parcial é aceita, e os outros cartões ficam como estavam (antes, a resposta parcial caía na reserva por regras e marcava todos como "reserva_por_regras");
    - `texto_por` foi declarado no `CartaoSugestaoValidado`, e o cartão final do grafo valida nesse esquema;
    - a varredura passou a pegar parte de nome composto ("Maria" de "Maria Eduarda") e RA no fim da frase ("…de Ceilândia."), e deixou de reprovar "um ótimo plano" e nome de lugar igual ao de membro;
    - a Pesquisa só marca `usou_llm` quando a seleção final veio do LLM (o planejamento vai em `planejou_com_llm`);
    - o juiz LLM provisório e os prompts `juiz_parecer.md` e `juiz_cartoes.md` saíram (ficam na #72).
* **Arquivos:** `src/agentes/grafo.py`, `src/agentes/validacao.py` (fim do arquivo e os dois ajustes), `src/agentes/comunicacao.py` (fim do arquivo e o campo `texto_por` do `CartaoSugestaoValidado`), `src/agentes/pesquisa.py` (`usou_llm`), `src/agentes/README.md`, `tests/test_grafo_multiagente.py`, `tests/test_agente_validacao_regras.py`.
* **Testes e Validação:**
  - `pytest tests/test_grafo_multiagente.py`: 32 testes sem rede, com um LLM falso que grava cada corpo enviado à OpenRouter. Eles cobrem:
    - o grafo e as três saídas da aresta;
    - o limite de 2 voltas;
    - a reescrita de um cartão que expõe a origem;
    - o LLM fora do ar;
    - que nenhum nome, teto ou origem vai para o LLM;
    - os dois cenários da #66;
    - a seleção dos cartões;
    - a reescrita parcial, o cartão final no esquema da Comunicação e a varredura de nomes e RAs (revisão do #80).
  - Cenários da #66 pelo grafo inteiro, sem LLM:
    - o padrão termina sem cartões depois de 2 voltas e sem passar pela Comunicação;
    - o de controle termina com 1 cartão, que está entre os 5 viáveis do gabarito, e avisa que há menos de 3 opções.
  - Suíte inteira (`python -m pytest tests`, sem o `test_pipeline_haystack.py`, que pede o Haystack): 862 aprovados.
* **Limitação medida (pendência):** sem LLM, a Pesquisa vê 24 dos 93 lugares em 3 rodadas e acha só 1 dos 5 viáveis do cenário de controle.
  - Causa: a nota da busca léxica satura (0,97 a 0,98 nos 12 primeiros), então a ordem é quase arbitrária.
  - Fator a mais: 3 dos 5 viáveis são cafeterias, e o grupo pediu restaurante e lugar ao ar livre.
  - Tentei duas mudanças: priorizar as consultas pelo motivo de veto mais frequente, com uma consulta nas RAs centrais do DF quando o deslocamento veta, e intercalar os resultados das consultas. Nenhuma das duas mudou o resultado, e ambas foram revertidas.
  - Correção provável: a busca vetorial (ADR 0012) ou outra nota na ferramenta, medida nos dois cenários.

---

### 8.9. Issue #72 — Juiz LLM em 2 Passagens para Validação Factual e Prevenção de Vazamento (ADR 0014)
* **Responsável:** Maria Eduarda (`@eduarda-ogomes`)
* **Status:** Concluída (PR pronto com testes)
* **O que foi feito:**
  - Implementação do Avaliador Semântico (LLM-as-a-Judge) em 2 Passagens em `src/agentes/juiz.py` e prompts em `src/agentes/prompts/`.
  - **Passagem 1 (Auditoria da Pesquisa - `julgar_parecer_pesquisa`):** Audita semanticamente os candidatos propostos pelo Agente de Pesquisa, verificando se cada afirmação/trecho `confere`, `contradiz` ou está `sem_apoio` na base oficial 2FA de 93 locais curados (RNF-03).
  - **Passagem 2 (Auditoria da Comunicação - `julgar_cartoes_comunicacao`):** Audita os textos gerados pelo Anfitrião (`titulo`, `resumo_acesso`, `por_que_combina`), assegurando fidelidade factual e prevenção absoluta de vazamento de PII (orçamento individual, origem de membros, restrições pessoais ou citações diretas) (RNF-02).
  - Implementação de fallback determinístico robusto em ambas as passagens para operação offline e resiliência a indisponibilidades do endpoint da OpenRouter.
  - Funções de integração e orquestração: `filtrar_candidatos_aprovados_pelo_juiz` (segregação de candidatos aptos e catalogação de `derrubados_pelo_juiz`) e `avaliar_reprovacoes_cartoes` (mapeamento estruturado de reprovações de cartões por vazamento e alucinação).
* **Decisões Técnicas e Arquitetura:**
  - *ADR 0014 (Juiz semântico):* Utilização de `z-ai/glm-5.3-flash` como padrão de baixo custo e alta fidelidade (com suporte a `xiaomi/mimo-v2.6-pro` via variável `JUIZ_LLM_MODELO`, atendendo RNF-12).
  - *JSON Schema Estrito (`esquema_estrito`):* Validação estrita via Pydantic com `extra="forbid"` (`SaidaJuizParecer` e `SaidaJuizCartoes`), garantindo estruturação determinística dos julgamentos.
  - *RNF-03 (Fidelidade e Alucinação):* Separação explícita entre afirmações corroboradas e alucinações sem apoio no vídeo/legenda oficial 2FA.
  - *RNF-02 (Prevenção de Vazamento de PII):* Varredura em 4 categorias de exposição (`origem`, `orcamento`, `restricao`, `texto_pessoal`), impedindo que textos públicos contenham pistas identificáveis de participantes.
  - *Spotlighting de Segurança:* Entrada do modelo delimitada via `embrulhar` para mitigar injeção de prompt vinda de conteúdos externos.
* **Arquivos:**
  - `src/agentes/juiz.py`
  - `src/agentes/prompts/juiz_pesquisa.md`
  - `src/agentes/prompts/juiz_comunicacao.md`
  - `tests/test_juiz_agentes.py`
* **Testes e Validação:**
  - 16 testes automatizados em `tests/test_juiz_agentes.py` cobrindo fallback offline, MockLLM, detecção estrita de vazamento de PII em todas as categorias, integração com a base 2FA e troca de modelo via env.
  - Validação de tipagem e execução rápida em 0.03s.

---

### 8.10. Issue #73 — Instrumentação de Telemetria e Tracing do Grafo Multiagente no Langfuse Cloud
* **Responsável:** Maria Eduarda (`@eduarda-ogomes`)
* **Status:** Concluída, em revisão
* **O que foi feito:**
  - **Aderência Estrita ao ADR 0015 (Spans Explícitos vs. CallbackHandler Automático):** Conforme deliberado no ADR 0015, a instrumentação do grafo multiagente adota spans explícitos (`@_observado` e `_registrar`) nos nós e arestas condicionalmente relevantes. O uso do `CallbackHandler` padrão do LangGraph/LangChain foi descartado por inflar em 52× o volume enviado ao Langfuse (634 mil caracteres contra ~12 mil caracteres de entrada e saída por execução) e expor o estado serializado bruto desnecessariamente.
  - **Spans Canônicos Padronizados:** Registro de spans nomeados para cada nó do grafo no Langfuse Cloud (`src/telemetria/langfuse_agentes.py`):
    - `agente_0_pessoal` (spans paralelos por membro via `Send`)
    - `agente_orquestrador_consolidar` (consolidação de preferências e janelas)
    - `agente_1_pesquisa` (planejamento e seleção de candidatos na base)
    - `agente_2_logistica` (avaliação de deslocamento e cálculo de justiça)
    - `agente_3_validacao` (checagem de regras de negócio, orçamento e vetos; metadados do juiz da #72 quando ativo)
    - `agente_4_comunicacao` (geração dos cartões com LLM ou fallback)
    - `agente_3_validacao_textos` (auditoria do juiz e varredura determinística contra PII)
    - `agente_orquestrador_finalizar` (consolidação final dos cartões públicos)
    - `grafo_sala_multiagente` (span raiz que engloba a execução do grafo)
    *(Nota: as duas passagens do juiz da #72 rodam internamente nos nós de Validação, gravando seus vereditos e contagens de exposição como metadados estruturados, como `juiz.confere`, `juiz_llm` e `exposicoes`, sem criar nós redundantes).*
  - **Métricas de Tokens, Custo e Latência por Agente:** Coleta e agregação a partir de `ClienteLLM.chamadas` (`tokens`, `custo_usd`, `latencia_llm_s`, `chamadas_llm`, `tentativas_sem_resposta` e `modelos`), registrando os custos reais e volumetria de cada nó no Langfuse sem depender de generations opacas do LangChain. O total da rodada fica consolidado no span raiz `grafo_sala_multiagente`.
  - **Metadados Estruturados de Convergência:** Registro nos spans de cada volta de pesquisa (`iteracao_pesquisa`), contagem e motivos de vetos (`quantidade_vetos` e `motivos_vetos`), status de convergência (`convergido`) e resultados das auditorias do juiz (`juiz`, `juiz_llm`, `exposicoes`).
  - **Sanitização Ativa de PII (`mascarar_pii`):** Algoritmo recursivo que expurga dados sensíveis por chaves privadas (`teto`, `origem`, `usuario`...) e por padrões (telefones, e-mails, CPFs e menções explícitas a origens ou participantes), preservando preços públicos dos estabelecimentos para conferência do juiz e assegurando que o teto individual fique isolado no cofre (RNF-02).
  - **Captura Dinâmica do Trace Link (`obter_trace_url`):** Priorização do método dinâmico `get_client().get_trace_url()` do SDK do Langfuse (que detecta automaticamente o ID do projeto a partir das credenciais ativas), utilizando o fallback estruturado apenas quando o SDK estiver indisponível.
  - **Campo Unificado de Rastreio (`trace_url`):** Manutenção do campo canônico e consistente `trace_url` no `MultiAgentState` e no `EstadoSerializado` (`src/agentes/estado.py`), eliminando redundâncias.
  - **Harmonização com o PR #88:** Integração dos parâmetros `juiz_parecer` em `construir_grafo`, `executar` e `executar_fluxo_multiagente`, garantindo merge limpo e sem conflitos com a demonstração da Semana 4.
* **Decisões Técnicas e Arquitetura:**
  - *ADR 0015 (Spans Explícitos vs. CallbackHandler Automático):* Spans explícitos selecionam apenas fatos públicos sanitizados, eliminando a gravação indiscriminada do estado e reduzindo o consumo de rede em mais de 98%.
  - *RNF-10 e RNF-14 (Observabilidade Estruturada e SLAs):* Spans canônicos permitem aferição de tempo p50/p90/p99 de cada agente, quantidade de chamadas e gasto financeiro em USD no Langfuse Cloud v5.x.
  - *RNF-02 (Defesa em Profundidade contra PII):* O cofre isola dados privados na origem, e a telemetria aplica mascaramento preventivo em qualquer dado repassado aos spans.
* **Arquivos:**
  - `src/telemetria/__init__.py`
  - `src/telemetria/langfuse_agentes.py`
  - `src/agentes/grafo.py`
  - `src/agentes/estado.py`
  - `tests/test_telemetria_agentes.py`
  - `docs/semanas/semana-04.md`
* **Testes e Validação:**
  - 16 testes automatizados em `tests/test_telemetria_agentes.py` (100% de aprovação) cobrindo mascaramento de PII privada com preservação de preços públicos, mapeamento canônico de spans, geração de trace URLs dinâmicas e de fallback, decoradores, registro de métricas de tokens/custo/latência, resiliência offline e retorno do `trace_url` na execução do grafo.
  - Suíte completa de 281 testes dos agentes da Semana 4 aprovada.
  - Suíte geral de 896 testes do projeto aprovada com 100% de sucesso.

---

### 8.11. Issue #74 — Script Executável de Demonstração CLI do Fluxo Multiagente (`demo_multiagente.py`)
* **Responsável:** Cauan Soares (`@cadasiso`)
* **Status:** Concluída, em revisão
* **O que foi feito:**
  - `scripts/demo_multiagente.py` (ou `make demo-agentes`; `OFFLINE=1` roda sem LLM) roda os dois cenários da #66 de ponta a ponta, em 5 atos:
    1. a memória do Agente Pessoal depois de um rolê anterior;
    2. os 4 amigos entrando pelo back-end real das salas;
    3. o fluxo atual sem agentes, para comparar;
    4. a conversa entre os agentes, ao vivo;
    5. o resultado, com o gabarito da #66, a visão privada de um membro, a varredura de vazamento, o custo e a latência por agente e o link do trace.
  - No fim, um resumo dos dois cenários (tempo, chamadas, tokens, custo, voltas, reescritas, vetos e cartões) para o relatório (#76).
  - O log fica em `docs/entregas/semana-04/DEMO_MULTIAGENTE_LOG.txt`, e o diagrama do grafo compilado em `docs/entregas/semana-04/grafo_agentes.mmd`.
  - O juiz LLM da #72 (`src/agentes/juiz.py`, PR #86) entrou no grafo:
    - a 2ª passagem, sobre os cartões, roda sempre na validação dos textos, junto com a varredura em código (que olha os nomes e as RAs do cofre, que o juiz não vê);
    - a 1ª passagem, sobre os motivos da Pesquisa, é opcional (`--juiz-parecer`) e derruba só o que contradiz o documento.
* **Decisões Técnicas e Arquitetura:**
  - **Os dois cenários da #66, e não uma sala própria:** o demo compara o resultado com um gabarito independente. O padrão mostra o ciclo condicional e o aviso sem cartão; o de controle mostra o caminho feliz.
  - **A memória não muda os vetos:** os comentários do ato 1 viram preferência (lugar sem barulho) ou são uma instrução injetada que o agente ignora. Assim o gabarito da #66 continua valendo depois da memória.
  - **Proposta contraditória não é gravada:** na primeira rodada, o LLM do pós-rolê leu "a música alta atrapalhou" como `barulho:evita` e "prefiro lugar mais tranquilo" como `barulho:gosta`, e o log gravava o último. Agora, se a mesma proposta trouxer "gosta" e "evita" para o mesmo aspecto, nada é gravado sobre ele (`pessoal.depois_do_role`).
* **Arquivos:** `scripts/demo_multiagente.py`, `Makefile` (`demo-agentes`), `src/agentes/grafo.py` (juiz da #72), `src/agentes/pessoal.py`, `src/agentes/llm.py` (tentativas sem resposta), `tests/test_demo_multiagente.py`, `tests/test_grafo_multiagente.py`, `tests/test_agente_pessoal.py`, `docs/entregas/semana-04/DEMO_MULTIAGENTE_LOG.txt`, `docs/entregas/semana-04/grafo_agentes.mmd`.
* **Testes e Validação:**
  - `pytest tests/test_demo_multiagente.py`: roda o demo sem LLM e confere os 5 atos nos dois cenários, o veredito do padrão, os cartões do controle dentro dos viáveis e a varredura sem nome de membro.
  - `pytest tests/test_grafo_multiagente.py`: 34 testes, entre eles o juiz usando o GLM e os agentes o DeepSeek, nenhum nome, teto ou origem nas mensagens enviadas aos LLMs (inclusive ao juiz) e a reescrita quando o juiz acha uma exposição que a varredura não pega.
  - Suíte inteira, sem o `test_pipeline_haystack.py`: 884 aprovados.
  - Demo com LLM e Langfuse, em 20/11 (o log está em `DEMO_MULTIAGENTE_LOG.txt`):

    | Sala | Tempo | Chamadas | Tokens | Custo | Voltas | Cartões | Trace |
    |---|---|---|---|---|---|---|---|
    | ROLE-PADR (sem lugar viável) | 15,1 s | 6 | 19.545 | US$ 0,0026 | 2 | 0, com o aviso ao grupo | [39bfd356](https://cloud.langfuse.com/project/cmw59be2y01d8ad0jqbgsjut6/traces/39bfd356e4ef94d7e760d91be8baacb8) |
    | ROLE-CTRL (5 viáveis) | 24,6 s | 6 | 21.660 | US$ 0,0035 | 1 | 3, os 3 entre os viáveis | [d8628952](https://cloud.langfuse.com/project/cmw59be2y01d8ad0jqbgsjut6/traces/d862895248205cffc031c42bef3d4376) |

    - Cada trace tem um span por etapa do grafo (`agente_pessoal` ×4, `consolidar_grupo`, `pesquisa`, `logistica`, `validacao` por volta, `comunicacao`, `validacao_textos`, `finalizar`), conferido pela API do Langfuse.
    - No controle, o juiz dos cartões é a chamada mais lenta (12,9 s) e a mais cara (US$ 0,0012).
    - **RNF-14 em risco:** numa rodada anterior, o controle levou 73,9 s, acima dos 60 s. A 1ª chamada ao juiz estourou o limite de 40 s do cliente, e a 2ª respondeu em 20 s. Essa tentativa sem resposta não aparecia no custo nem no tempo por agente; agora o cliente registra cada tentativa (`Chamada.falhou`), e o demo mostra quantas houve.
    - O fluxo atual das salas, sem agentes, sugere o Cachorrão da 5, que está no `nunca_sugerir` da #66, nos dois cenários (pior trajeto de 218 min no padrão). O fluxo com agentes não sugere.

---

### 8.12. Issue #75 — Diagrama Visual da Arquitetura do Grafo Multiagente (Mermaid & SVG)
* **Responsável:** Maria Carolina (`@mcznh`)
* **Status:** Concluída (revisão do PR #85 atendida)
* **O que foi feito:**
  - Elaboração da documentação técnica arquitetural completa em `docs/arquitetura/multiagente.md` alinhada ao grafo real implementado em `src/agentes/grafo.py` e ao estado em `src/agentes/estado.py`;
  - Criação de página web completa e responsiva em `docs/arquitetura/multiagente.html` com Mermaid.js e SVG integrado (sem botão no `index.html`, preservando o mapa público como arquivo único conforme `docs/arquitetura/AGENTS.md`);
  - Diagrama estrutural em Mermaid e diagrama vetorial em alta resolução (`docs/arquitetura/img/grafo_multiagente.svg`, gerado por `scripts/gerar_grafo_multiagente_svg.py`) refletindo todas as arestas do grafo compilado (`grafo_agentes.mmd`): fan-out de `no_pessoal` ×N via `Send` + `no_consolidar_grupo`, saídas diretas para `no_finalizar` (sem janela comum ou sem lugar viável após as buscas), laço `avaliar_convergencia` (até 2 voltas com `PedidoNovaBusca`), `no_validacao_textos` com reescrita seletiva de no máximo 1 volta, Juiz LLM em 2 passagens (#72) e preenchimento determinístico de números e `tiktok_url` em `no_finalizar`;
  - Atualização do menu de navegação e suporte a diagramas Mermaid no `mkdocs.yml`;
  - Criação de suíte de testes automatizados em `tests/test_arquitetura_multiagente.py`.
* **Decisões Técnicas e Arquitetura:**
  - *RNF-04 (Cálculos Fora do LLM):* Diferenciação visual e estrutural estrita entre nós com LLM (`no_pesquisa`, `no_comunicacao` e Juiz LLM) e nós em código puro Python (`no_pessoal`, `no_consolidar_grupo`, `no_logistica` com Menor Miséria, vetos duros de `no_validacao`, varredura de `no_validacao_textos` e `no_finalizar`).
  - *RNF-02 e RF-17 (Cofre do Servidor e 4 Canais):* Representação explícita do `Cofre` fora do `MultiAgentState` (ADR 0015 e 0016) e dos 4 canais na ordem de `src/agentes/pessoal.py` (Canais 1, 2 e 4 retidos no Cofre; Canal 3 como único público no estado).
  - *Observabilidade e SLA (RNF-14):* Documentação dos nomes reais dos spans no Langfuse (`agente_pessoal`, `consolidar_grupo`, `pesquisa`, `logistica`, `validacao`, `comunicacao`, `validacao_textos` e `finalizar`) e do limite do RNF-14 ($\le 5\text{ s}$ na conversa e $\le 60\text{ s}$ para gerar os planos).
* **Arquivos:**
  - `docs/arquitetura/multiagente.md`
  - `docs/arquitetura/multiagente.html`
  - `docs/arquitetura/img/grafo_multiagente.svg`
  - `scripts/gerar_grafo_multiagente_svg.py`
  - `mkdocs.yml`
  - `tests/test_arquitetura_multiagente.py`
  - `docs/semanas/semana-04.md`
* **Testes e Validação:**
  - Execução de `pytest tests/test_arquitetura_multiagente.py` com 6 testes aprovados cobrindo integridade do SVG, nós reais do grafo, canais, contrato `MultiAgentState`, página HTML e configuração do MkDocs.
  - Execução da suíte completa de testes locais com 890 testes passando.

---

### 8.13. Issue #76 — Relatório Técnico da Semana 4 para o Teams e Submissão Oficial
* **Responsável:** Cauan Soares (`@cadasiso`), por acordo do grupo (a issue foi aberta para a Letícia Miti); revisão da Maria Eduarda
* **Status:** Concluída, em revisão
* **O que foi feito:**
  - Relatório técnico em `docs/entregas/semana-04/RELATORIO_TECNICO_SEMANA_04.md`, com a versão em LaTeX para o Overleaf (`.tex`), o PDF e o pacote ZIP, no formato da Semana 3 e com a formatação da ABNT.
  - Conteúdo: arquitetura do grafo e dos 5 agentes, juiz em 2 passagens, privacidade (RNF-02), cenários da #66, resultados do demo com LLM, comparação com o fluxo sem agentes, custo e latência por agente, observabilidade no Langfuse, decisões da semana, limitações, conclusão e próximos passos.
  - O demo foi rodado de novo em 20/11, depois dos merges dos PRs #85 e #89, para o log e os traces terem os nomes canônicos dos spans:

    | Sala | Tempo | Chamadas | Tokens | Custo | Voltas | Cartões | Trace |
    |---|---|---|---|---|---|---|---|
    | ROLE-PADR (sem lugar viável) | 19,5 s | 6 | 21.326 | US$ 0,0045 | 2 | 0, com o aviso ao grupo | [c79c277c](https://cloud.langfuse.com/project/cmw59be2y01d8ad0jqbgsjut6/traces/c79c277ce1627d3a63be8c6815d9b11f) |
    | ROLE-CTRL (5 viáveis) | 24,6 s | 6 | 21.654 | US$ 0,0034 | 1 | 3, os 3 entre os viáveis | [e4f11619](https://cloud.langfuse.com/project/cmw59be2y01d8ad0jqbgsjut6/traces/e4f11619f662d0fc9e9c99460427f129) |

* **Decisões Técnicas e Arquitetura:**
  - *Figura do grafo:* o relatório usa o Mermaid da Seção 2, que cabe numa página A4; o SVG detalhado da #75 (1300 × 2752) fica citado como versão completa.
  - *PDF gerado do HTML:* sem LaTeX instalado na máquina, o PDF sai do HTML com as mesmas regras da ABNT (A4, margens 3/2/3/2 cm, Times 12, entrelinha 1,5, legenda acima e fonte abaixo). O `.tex` gera o mesmo documento no Overleaf.
* **Arquivos:**
  - `docs/entregas/semana-04/RELATORIO_TECNICO_SEMANA_04.md`, `.tex` e `.pdf`
  - `docs/entregas/semana-04/Entregavel_Grupo7_Semana_04.zip`
  - `docs/entregas/semana-04/img/` (figura do grafo e prints dos traces)
  - `docs/entregas/semana-04/DEMO_MULTIAGENTE_LOG.txt` (nova rodada)
* **Testes e Validação:**
  - Números do relatório conferidos com o log do demo e com as observações dos traces pela API do Langfuse (15 observações no controle e 16 no padrão, sem nome, origem ou teto de membro).
  - Suíte inteira na `main` com os PRs #85, #89 e #90: 906 aprovados (sem o `test_pipeline_haystack.py`, que pede o Haystack instalado).

---

## 9. Registro do dia

### 17/11 (Cauan)

- **Juiz do avaliador:** passou do MiMo-V2.6-Pro para o GLM 5.3 Flash, por custo ([ADR 0014](../decisoes/0014-juiz-glm-5.3-flash.md), PR #78 mesclado). Nas mesmas 94 respostas da rodada 2 da semana 3:
  - custo de US$ 0,057 contra US$ 0,731;
  - p90 de 10,1 s contra 18,8 s;
  - concordância de 90 em 94 sobre haver contradição.

  Parte do custo do MiMo vinha do roteamento: o `sort: latency` mandou 63 das 94 chamadas ao provedor 10 vezes mais caro.
- **Plano dos agentes:** avaliado e reestruturado em [PLANO_AGENTES.md](../entregas/semana-04/PLANO_AGENTES.md): Logística sem LLM, Validação com vetos em código, Comunicação sem dado pessoal e um Agente Pessoal por membro com log de preferências. LangGraph decidido ([ADR 0015](../decisoes/0015-orquestracao-com-langgraph.md)).
  - Ferramentas e observabilidade: [FERRAMENTAS_E_OBSERVABILIDADE.md](../entregas/semana-04/FERRAMENTAS_E_OBSERVABILIDADE.md).
  - Prompts: [PROMPTS_AGENTES.md](../entregas/semana-04/PROMPTS_AGENTES.md).
  - Estrutura em proposta: [ADR 0016](../decisoes/0016-estrutura-dos-agentes.md).
- **Demonstração com LLMs** numa sala de 4 pessoas ([log](../entregas/semana-04/DEMO_MULTIAGENTE_LOG.txt)): 8 chamadas, US$ 0,0036 e 38,9 s até os cartões, dentro dos 60 s do RNF-14.
  - A memória do Agente Pessoal virou restrição vegetariana e preferência por lugar calmo, e uma instrução injetada num comentário foi ignorada.
  - A varredura não achou vazamento.
- **Encontrado no caminho:**
  - A "Hamburgueria Espacial Taguatinga" está com as coordenadas em Sobradinho.
  - O GLM 5.3 Flash não aceita desligar o raciocínio.
  - Um exemplo do prompt da Comunicação fez o modelo inventar "dá para chegar de metrô".
  - O primeiro build do Docker levou cerca de 15 min, por causa do espelho do Debian; o ffmpeg ainda está no Dockerfile.
- **Reviews:**
  - #77: a revisão da Maria Eduarda foi atendida (varredura de nomes, `trace_url`, commits e template).
  - #79 (Telas 1 a 3): mudanças pedidas à Maria Carolina (conflito no `STATUS.md`, descrição vazia, barra "Modo Dev" em produção, ida para a DEMO em qualquer erro da API).
- **Pendências:**
  - **#71 (grafo):** segue bloqueada. Há um rascunho local com a aresta `avaliar_convergencia` e `executar_fluxo_multiagente`, mas ele precisa usar as implementações das #67, #68 e #69 quando entrarem. A Maria Carolina já tem a #69 numa branch. *(Atualização de 19/11: concluída; ver Seção 8.8.)*
  - **#73:** pede o `CallbackHandler` do Langfuse, o que contradiz o ADR 0015.
  - **#74:** depende do cenário da #66.
