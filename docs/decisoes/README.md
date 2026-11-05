# Decisões técnicas (ADRs)

Cada decisão relevante vira um arquivo numerado (`0001-escolha-do-vector-store.md`, `0002-...`), criado a partir de [0000-template.md](0000-template.md). As seções do template seguem as restrições do desafio: justificar, explicitar riscos, validar com métricas e citar evidências.

Não apague nem reescreva uma decisão antiga: se ela mudar, crie uma nova e marque a anterior como "substituída por NNNN".

## Índice

| Nº | Decisão | Status |
|---|---|---|
| [0001](0001-escolha-do-orquestrador-de-roles.md) | Seguir com o Orquestrador de Rolês | aceita |
| [0002](0002-recorte-do-mvp.md) | Recorte do MVP: só o modo com amigos | aceita |
| [0003](0003-canal-app-web.md) | Canal do MVP: app web próprio | proposta |
| [0004](0004-fonte-e-manutencao-da-base.md) | Fonte e manutenção da base de lugares e eventos | aceita (v2, após [crítica](revisoes/0004-critica.md)); parcialmente substituída por 0005 |
| [0005](0005-coleta-automatica-e-base-vetorial.md) | Coleta automática e base vetorial (PostgreSQL + pgvector) | proposta |
| [0006](0006-transcricao-de-fala.md) | Transcrição de fala: Whisper, provedor escolhido por medição | proposta |
| [0007](0007-interpretador-e-contrato-de-busca.md) | Interpretador de mensagens e contrato da busca usada pelos agentes | proposta |

A pasta [revisoes/](revisoes/) guarda as críticas feitas por outros agentes ou pessoas a um ADR (`NNNN-critica.md`), as respostas do autor e o prompt usado para pedir a crítica.
