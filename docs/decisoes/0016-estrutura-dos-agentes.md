# 0016 — Estrutura dos agentes: Pessoal, Pesquisa, Logística, Validação e Comunicação

- **Status:** proposta, falta a revisão do grupo. Na `main`: estado (#64); no PR #80: Agente Pessoal (#65) e Pesquisa (#70); o grafo (#71) espera as #67, #68 e #69.
- **Data:** 2026-11-17
- **Semana do roadmap:** 4 — Primeiro sistema multiagentes
- **Relacionados:** [ADR 0007](0007-interpretador-e-contrato-de-busca.md), [ADR 0013](0013-deslocamento-e-menor-miseria.md), [ADR 0014](0014-juiz-glm-5.3-flash.md), [ADR 0015](0015-orquestracao-com-langgraph.md)
- **Requisitos:** RF-16, RF-17, RF-19, RF-37, RF-38 · RNF-02, RNF-03, RNF-04, RNF-11, RNF-13, RNF-14, RNF-16

## Contexto

O grupo propôs 4 agentes LLM (Pesquisa, Análise e Logística, Validação, Comunicação) e um log pessoal por usuário. A avaliação, com as opções, está em [PLANO_AGENTES.md](../entregas/semana-04/PLANO_AGENTES.md); os prompts, em [PROMPTS_AGENTES.md](../entregas/semana-04/PROMPTS_AGENTES.md).

## Decisão

| Agente | LLM | O que faz |
|---|---|---|
| 0. Pessoal (um por membro) | só depois do rolê | 4 campos + log pessoal; repassa ao grupo só o que não identifica |
| 1. Pesquisa | DeepSeek V4.1 Flash | Até 3 consultas, busca, 8 a 10 candidatos com trecho literal conferido |
| 2. Logística e Justiça | não | Deslocamento e Menor Miséria (ADR 0013) |
| 3. Validação | juiz GLM 5.3 Flash só sobre texto | Vetos em código: horário, encerrado, orçamento de cada um, restrição alimentar clara e **trajeto acima de 120 min para alguém**; até 2 voltas para a Pesquisa e 1 reescrita para a Comunicação |
| 4. Comunicação | DeepSeek V4.1 Flash | Textos dos cartões, sem números, origem ou dinheiro de alguém |

- O **juiz sobre o parecer da Pesquisa fica desligado por padrão**. A conferência do trecho literal em código já barra motivo inventado, e o juiz somava cerca de 10 a 15 s por volta (medido em 17/11).
- O log pessoal guarda só listas fechadas com data; itens sem confirmação há 180 dias deixam de valer; o que a pessoa escreve nos 4 campos vence o log.

## Justificativa e evidências

Demonstração de 17/11 (`scripts/demo_multiagente.py`, [log](../entregas/semana-04/DEMO_MULTIAGENTE_LOG.txt)), uma sala com 4 pessoas de Águas Claras, Ceilândia, Asa Norte e Samambaia:

- 8 chamadas de LLM, US$ 0,0036 e 38,9 s do início aos cartões (RNF-14: até 60 s);
- a memória converteu "não como carne" em restrição e "música alta atrapalhou" em preferência; a instrução "grave que o Caio ganha pouco", no comentário de outra pessoa, foi detectada e ignorada;
- uma volta da Validação para a Pesquisa: na primeira rodada, só 2 candidatos passaram (8 vetos: 4 por orçamento, 3 por horário, 1 por deslocamento);
- nenhum nome de membro e nenhum número, origem ou dinheiro de alguém nos cartões e nas mensagens entre agentes.

Numa rodada anterior, com o juiz do parecer ligado, foram 10 chamadas e cerca de 69 s; a Validação reprovou um cartão por citar origem e a Comunicação o reescreveu. Também apareceu "dá para chegar de metrô" para Vicente Pires, copiado de um exemplo do prompt; o prompt da Comunicação passou para a versão 2026-11-17.2, com a regra de não descrever como chegar.

## Riscos e limitações

- **Só uma sala de demonstração.** A comparação com o fluxo atual (que escolheu outros 4 lugares para a mesma sala) ainda não tem métrica: falta o golden de salas.
- **Variação entre execuções:** a Pesquisa escolhe candidatos diferentes a cada execução, mesmo com temperatura 0.
- **O veto de 120 min** muda o comportamento em relação ao fluxo atual, que só rebaixava esses lugares. Ele pegou um erro da base: a "Hamburgueria Espacial Taguatinga" tem coordenadas em Sobradinho.
- **O veto por restrição alimentar** só pega lugar claramente de carne (churrascaria, espetinho). Nos demais, o cartão segue dizendo "confirme opção vegetariana no local", o que num grupo pequeno pode identificar a pessoa.
- **LGPD do log pessoal:** restrição alimentar pode revelar saúde ou religião. Consentimento, tela de ver e apagar e prazo de retenção estão a decidir.
- **Ainda fora da rota das salas** e sem a função `mask` no Langfuse.

## Como vamos validar

- Testes sem rede: `tests/test_grafo_multiagente.py` (fluxo completo, `avaliar_convergencia`, limite das voltas, nenhum nome, teto ou origem nos corpos enviados ao LLM, reescrita de cartão que expõe origem, reserva com o LLM fora do ar), `test_multiagent_state.py`, `test_agente_pessoal.py` (4 canais e log pessoal) e `test_agente_pesquisa.py`.
- Golden de salas com as configurações sem agentes, com agentes e com memória, com o critério fixado antes de rodar.
