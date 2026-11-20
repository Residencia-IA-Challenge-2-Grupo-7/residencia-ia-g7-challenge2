# 0015 — Orquestração dos agentes com LangGraph

- **Status:** aceita (Cauan, 17/11/2026). A estrutura dos agentes continua em proposta ([PLANO_AGENTES.md](../entregas/semana-04/PLANO_AGENTES.md))
- **Data:** 2026-11-17
- **Semana do roadmap:** 4 — Primeiro sistema multiagentes
- **Requisitos:** RNF-02, RNF-04, RNF-10, RNF-12, RNF-14, RNF-15

## Contexto

A semana 4 liga agentes especialistas às rotas das salas, como camada sobre o que já existe (RNF-12). O fluxo tem um agente pessoal por membro, rodando em paralelo, e um ciclo entre a Validação e a Pesquisa quando sobram menos de 3 candidatos. A orquestração precisa manter o dado de cada membro fora dos agentes do grupo (RNF-02), sobreviver à falha de um LLM (RNF-15) e mostrar o progresso (RNF-14).

## Opções consideradas

Comparação completa, com as versões do PyPI de 17/11, na seção 6 do [PLANO_AGENTES.md](../entregas/semana-04/PLANO_AGENTES.md).

1. **LangGraph (escolhida):** grafo com ciclos, estado tipado, execução paralela (`Send`), checkpoint, *store* de longo prazo para o log pessoal e diagrama gerado do código. Traz o `langchain-core` e o `langsmith` como dependências.
2. **Pydantic AI com `pydantic-graph`:** saída tipada e uma dependência só, mas o grafo é menos conhecido e o projeto lança versão quase todo dia.
3. **Código próprio:** nenhuma dependência, mas ciclo, checkpoint e diagrama feitos à mão.
4. OpenAI Agents SDK, Google ADK, Microsoft Agent Framework, CrewAI, LlamaIndex Workflows, Haystack Agents, AG2 e smolagents: descartados por compartilhar o histórico entre agentes (RNF-02), pelo peso, por exigirem Python abaixo de 3.14 ou por o LLM escrever código para agir (RNF-04).

## Decisão

- LangGraph 1.2 só como orquestrador: os nós chamam os módulos do projeto e o cliente da OpenRouter que já existe, sem os modelos da LangChain.
- As mensagens entre agentes são modelos Pydantic; o estado compartilhado do grafo não guarda teto, origem nem texto dos 4 campos.
- Checkpointer em memória nos testes e no Postgres do Supabase (`langgraph-checkpoint-postgres`) quando o banco entrar.
- Observabilidade pelo Langfuse com `@observe` explícito nos nós e uma função `mask`; o LangSmith fica desligado. Detalhes em [FERRAMENTAS_E_OBSERVABILIDADE.md](../entregas/semana-04/FERRAMENTAS_E_OBSERVABILIDADE.md).

## Justificativa e evidências

- O ciclo Validação → Pesquisa e a execução paralela dos agentes pessoais são recursos nativos do grafo, e o diagrama do entregável sai do código compilado.
- O checkpoint guarda o estado de cada etapa, então uma falha de LLM retoma do último nó, em vez de recomeçar a sala (RNF-15).
- Manter os LLMs no cliente do projeto preserva o roteamento sem retenção do ADR 0007 e os testes com cliente falso que já existem.

## Riscos e limitações

- **Curva de aprendizado** em 3 dias. Mitigação: o primeiro passo é o grafo com nós falsos, que o grupo usa de modelo.
- **Vazamento pelo próprio rastreio:** o `CallbackHandler` do Langfuse para LangGraph registra o estado inteiro de cada nó. Ele só pode ser usado em nós sem dado pessoal.
- **LangSmith:** vem como dependência e envia dados para fora se `LANGSMITH_TRACING=true`.
- **Dependências novas no deploy** (Render e Docker com Python 3.12): conferir o tamanho da imagem e o tempo de build.

## Como vamos validar

- Teste do fluxo completo sem rede, com LLMs falsos, do `gerar-sugestoes` à votação.
- Teste de que nenhum corpo enviado à OpenRouter e nenhum trace contém teto, origem ou nome de participante.
- Benchmark do golden de salas: p90 da geração até 60 s (RNF-14) e custo por sala, comparado ao fluxo atual sem agentes.
