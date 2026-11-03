# Semana 2 — Base de conhecimento e recuperação

**Entregável:** Primeiro mecanismo RAG

## Registro

- 2026-11-03: mapa navegável da arquitetura planejada em `docs/arquitetura/index.html`, no formato pedido pelo mentor Isaque, publicado no GitHub Pages pelo repositório público `residencia-ia-g7-arquitetura`. Mostra o que está decidido, o que é proposta e o que falta decidir; nada foi implementado ainda.
- 2026-11-03: requisitos do repositório sincronizados com a v0.3 do documento da equipe (RF-46, coluna Riscos, testes do MVP sem piloto).
- 2026-11-03: ADR 0004 sobre a fonte da base (fontes, API de conferência, reverificação e tamanho). A versão 1 passou por crítica de outro agente, com o prompt em `docs/decisoes/revisoes/`; a versão 2 incorpora a crítica e cria o esquema e o guia de curadoria em `docs/dados/`.
- 2026-11-03: ADR 0005 (proposta): coleta 100% automática (robô nos sites oficiais, extração por LLM com evidência literal validada por código) e base vetorial em PostgreSQL com pgvector, busca híbrida e embeddings BGE-M3 locais. Substitui a curadoria humana do ADR 0004.

## Decisões da semana

- [ADR 0004](../decisoes/0004-fonte-e-manutencao-da-base.md): fonte e manutenção da base de lugares e eventos. Aceito na versão 2, depois da [crítica e respostas](../decisoes/revisoes/0004-critica.md): 21 achados aceitos e 3 aceitos em parte. Consequências nos requisitos v0.3.1 (RNF-15 e RF-37).
- [ADR 0005](../decisoes/0005-coleta-automatica-e-base-vetorial.md): coleta automática e base vetorial (proposta).

## Aprendizados e dúvidas

- Os termos da Google Maps Platform restringem muito mais do que a cota sugere. Não se pode guardar o conteúdo (só o place ID), usar a Places API com mapa não Google, ler o conteúdo em voz alta nem usá-lo para testar modelos de IA. Por isso a Google ficou só como conferência na hora do plano.
- A crítica por outro agente, guiada por um prompt com o que procurar, achou três problemas bloqueantes que a primeira versão do ADR não via. Vale repetir nos próximos ADRs.

## Pendências para a próxima semana

- 20 a 30 pedidos de teste escritos antes da base; Postgres com pgvector em Docker; pipeline com 100 candidatos e taxa de aprovação por região.
- Respostas do grupo às perguntas dos ADRs 0004 e 0005.
- Atualizar o mapa da arquitetura com os ADRs 0004 e 0005, aqui e no repositório público.
