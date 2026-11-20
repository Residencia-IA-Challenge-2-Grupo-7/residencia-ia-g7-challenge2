# src/agentes — sistema multiagentes da semana 4

Grafo em LangGraph ([ADR 0015](../../docs/decisoes/0015-orquestracao-com-langgraph.md)) sobre o que já existe nas salas, sem reescrevê-lo (RNF-12). Estrutura e motivos em [ADR 0016](../../docs/decisoes/0016-estrutura-dos-agentes.md) e [PLANO_AGENTES.md](../../docs/entregas/semana-04/PLANO_AGENTES.md).

| Arquivo | Agente ou papel | LLM? |
|---|---|---|
| `pessoal.py` | 0. Agente Pessoal, um por membro (issue #65): `executar_agente_pessoal(campos)` devolve os 4 canais (orçamento, restrições, preferências públicas, logística); log pessoal antes do rolê; comentário → memória depois | só depois do rolê |
| `pesquisa.py` | 1. Pesquisa (issue #70): `executar_agente_pesquisa(perfil_grupo, feedback_validacao)` planeja até 3 consultas, chama a ferramenta `buscar_lugares_rag` e escolhe 8 a 10 candidatos com `trecho_citado` conferido | sim (DeepSeek V4.1 Flash) |
| `logistica.py` | 2. Logística e Justiça (issue #67): `executar_agente_logistica` mede o trajeto de cada um, aplica a Menor Miséria e ordena; `gerar_parecer` escreve o parecer sem apontar ninguém | não |
| `validacao.py` | 3. Validação: `validar_candidatos_regras` faz os vetos em código (issue #68); `selecionar_cartoes` e a varredura de vazamento dos cartões (`varrer_cartao`, `verificar_cartoes`) ficam no fim do arquivo (issue #71). O juiz LLM em 2 passagens é da issue #72 (PR #86, `juiz.py`) e entra no grafo depois | não (o juiz da #72 usa o GLM 5.3 Flash) |
| `comunicacao.py` | 4. Comunicação: `executar_agente_comunicacao` (issue #69) e, no fim do arquivo, `montar_fatos`, `escrever` e `texto_reserva`, que o grafo usa para reescrever um cartão só | sim (DeepSeek V4.1 Flash) |
| `grafo.py` | Orquestrador (issue #71): os nós `no_*`, a aresta `avaliar_convergencia` (volta para a Pesquisa enquanto houver menos de 3 validados, até 2 voltas; sem nenhum validado, vai direto ao fim), a reescrita dos cartões, o cofre, `executar_fluxo_multiagente(dados_sala)` e os spans do Langfuse | não |
| `estado.py` | `MultiAgentState` (issue #64): o estado público do grafo, os esquemas que o validam e a serialização em JSON que recusa dado do cofre | — |
| `contratos.py` | Mensagens entre agentes (Pydantic) e o cofre do servidor | — |
| `ferramentas.py` | Busca, documento legível por LLM e conferência do trecho literal | — |
| `llm.py` | Cliente da OpenRouter com JSON Schema estrito e roteamento sem retenção | — |
| `prompts/*.md` | Prompts de sistema, com a versão no topo ([PROMPTS_AGENTES.md](../../docs/entregas/semana-04/PROMPTS_AGENTES.md)) | — |

## Usar

```python
from src.agentes.grafo import executar_fluxo_multiagente
from src.agentes.llm import ClienteLLM

final = executar_fluxo_multiagente({"codigo": "ROLE-7KQ2", "membros": [
    {"nome": "Bia", "origem": "Ceilândia", "horarios": "sábado depois das 18h", "teto": "80",
     "preferencias": "barzinho animado, vou de metrô"},
    ...                                               # pelo menos 2 membros
]}, cliente=ClienteLLM())                             # ClienteLLM(offline=True): tudo por regras
final["resultado_final_cartoes"], final["mensagens"], final["historico_erros"], final["iteracao_pesquisa"]
```

Com uma sala de `src/salas` (participantes confirmados): `executar(cofre_da_sala(sala, lugares, agora, store), ClienteLLM())`.

Demonstração completa: `scripts/demo_multiagente.py`, que entra no PR da issue #74. Testes sem rede: `python -m pytest tests/test_grafo_multiagente.py tests/test_multiagent_state.py tests/test_agente_pessoal.py tests/test_agente_pesquisa.py`.

## Regras do RNF-02 no código

- O **cofre** (4 campos, teto, origem, nomes) fica fora do estado do grafo; só os nós de código o leem. `serializar_estado` confere isso a cada gravação: chave do cofre ou nome de membro no estado é erro.
- Os agentes LLM recebem só modelos anônimos, e todo dado de usuário ou da base chega marcado como dado (`embrulhar`, com marca aleatória por chamada).
- O que volta de um agente para outro numa repetição (Validação → Pesquisa, Validação → Comunicação) é contagem ou enumeração, nunca texto livre.
- Cada nó registra no Langfuse uma entrada e uma saída escolhidas à mão, nunca o estado inteiro.

## Ainda não feito

- Ligar o grafo à rota `POST /api/salas/{codigo}/gerar-sugestoes` (hoje só a demonstração e os testes o usam).
- Função `mask` no cliente do Langfuse e o golden de salas com a comparação contra o fluxo atual.
