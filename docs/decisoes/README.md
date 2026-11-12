# Decisões técnicas (ADRs)

Cada decisão relevante vira um arquivo numerado (`0001-escolha-do-vector-store.md`, `0002-...`), criado a partir de [0000-template.md](0000-template.md). As seções do template seguem as restrições do desafio: justificar, explicitar riscos, validar com métricas e citar evidências.

Não apague nem reescreva uma decisão antiga: se ela mudar, crie uma nova e marque a anterior como "substituída por NNNN".

## Índice

| Nº | Decisão | Status |
|---|---|---|
| [0001](0001-escolha-do-orquestrador-de-roles.md) | Seguir com o Orquestrador de Rolês | aceita |
| [0002](0002-recorte-do-mvp.md) | Recorte do MVP: só o modo com amigos | aceita |
| [0003](0003-canal-app-web.md) | Canal do MVP: app web próprio | proposta |
| [0004](0004-fonte-e-manutencao-da-base.md) | Fonte e manutenção da base de lugares e eventos | aceita (v2, após [crítica](revisoes/0004-critica.md)); parcialmente substituída por 0005 e, nas fontes, por 0008 |
| [0005](0005-coleta-automatica-e-base-vetorial.md) | Coleta automática e base vetorial (PostgreSQL + pgvector) | substituída por 0008 |
| [0006](0006-transcricao-de-fala.md) | Transcrição de fala: Whisper pelo Groq como padrão, MLX no Mac como opção local | substituída por 0009 (sem voz) |
| [0007](0007-interpretador-e-contrato-de-busca.md) | Interpretador de mensagens e contrato da busca usada pelos agentes | proposta; a conversa privada deu lugar aos 4 campos (0009) |
| [0008](0008-base-2fa-de-93-lugares-e-lgpd.md) | Base oficial de 93 lugares (validação em 2 fatores) e conformidade com a LGPD | aceita (medidas de LGPD em proposta) |
| [0009](0009-entrada-pelos-4-campos-de-texto.md) | Entrada pelos 4 campos de texto, interpretados por regras (sem voz) | aceita (escopo); interpretação por regras em proposta |
| [0010](0010-baseline-llm-pura-e-guardrails.md) | Baseline LLM pura (DeepSeek V4.1 Flash) e guardrails determinísticos do RAG | proposta |
| [0011](0011-comparativo-ab-com-o-mesmo-llm.md) | Comparativo A/B: o Modo B gera a resposta com o mesmo LLM do Modo A | proposta |
| [0012](0012-busca-vetorial-pela-openrouter.md) | Busca vetorial do Modo B com o gemini-embedding-001 pela OpenRouter | proposta |
| [0013](0013-deslocamento-e-menor-miseria.md) | Deslocamento no DF (Haversine × fator de rota) e nota de justiça da Menor Miséria | proposta |


A pasta [revisoes/](revisoes/) guarda as críticas feitas por outros agentes ou pessoas a um ADR (`NNNN-critica.md`), as respostas do autor e o prompt usado para pedir a crítica.
