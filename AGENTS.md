# AGENTS.md — Residência IA UnB · Grupo 7 · Challenge 2

Instruções para qualquer agente de IA (Claude Code, Codex, Cursor, Copilot, Gemini…) e para as pessoas que trabalham neste repositório. Mantenha este arquivo curto e estável: o que muda toda hora vai em `STATUS.md`.

## O projeto

Programa de Residência em IA (Instituto Eldorado + UnB), metodologia CBL (Challenge Based Learning).

- **Big Idea:** Qualidade de Vida — *"Empoderando pessoas com IA para compreender melhor, decidir melhor e viver melhor."*
- **Desafio:** projetar e desenvolver uma solução baseada em IA que apoie a tomada de decisão em um contexto de qualidade de vida. O grupo define a própria Essential Question.
- **Restrições (valem para toda decisão):** entender o problema antes da solução · justificar decisões técnicas · explicitar riscos e limitações · validar com métricas objetivas · usar evidências confiáveis.
- Enunciado completo e roadmap de 7 semanas: [docs/desafio/challenge-2.md](docs/desafio/challenge-2.md)

## Comece por aqui (toda sessão)

1. Leia [STATUS.md](STATUS.md): semana atual, o que está em andamento e próximos passos.
2. Leia apenas os documentos relevantes para a tarefa (mapa abaixo). Não carregue tudo.
3. Antes de tomar uma decisão técnica relevante, confira [docs/decisoes/](docs/decisoes/) para não contradizer algo já decidido.

## Mapa do repositório

| Caminho | Conteúdo |
|---|---|
| `STATUS.md` | Estado vivo do projeto: a fonte da verdade sobre o "agora" |
| `docs/desafio/` | Enunciado do Challenge 2 (PDF original + versão em Markdown) |
| `docs/produto/` | Visão do produto escolhido (Orquestrador de Rolês) e requisitos do MVP |
| `docs/decisoes/` | ADRs: decisões técnicas e suas justificativas; críticas e respostas em `revisoes/` |
| `docs/dados/` | Esquema da base de lugares e eventos e regras de extração (ADRs 0004 e 0005) |
| `docs/arquitetura/` | Mapa navegável da arquitetura (HTML único), publicado num repositório público à parte; guia de edição no `AGENTS.md` da pasta |
| `docs/entregas/` | Entregáveis semanais (relatórios .docx) e o plano de cada um, uma pasta por semana |
| `docs/semanas/` | Registro semanal alinhado ao roadmap (alimenta o relatório final) |
| `docs/atas/` | Atas das reuniões do grupo, uma por data (`AAAA-MM-DD.md`) |
| `src/base/` | Pipeline de população da base (ADR 0005): `python -m base <etapa>`; como rodar no `README.md` da pasta |
| `data/base/` | CSVs aprovados da base e relatório da rodada (versionados); `data/raw/` e `data/processed/` ficam fora do git |
| `src/interpretador/` | Interpretador de mensagens (ADR 0007): texto → intenções estruturadas, destino e confirmação; `python -m interpretador` |
| `src/voz/` | Transcrição de fala (ADR 0006), com provedor trocável; `python -m voz` |
| `src/base/contrato.py` | Contrato da busca usada pelos agentes (ADR 0007): `buscar(ConsultaBusca) → ResultadoBusca` |
| `eval/` | Conjuntos de teste com gabarito (50 frases), roteiro de gravação e resultados das medições; os áudios ficam em `data/raw/voz/` |
| `tests/` | Testes do pipeline, do interpretador, do contrato e da voz (`PYTHONPATH=src python -m pytest tests`) |
| `docs/pesquisa/` | Instrumentos de pesquisa com usuários (questionários, roteiros de entrevista) e o script que gera o Google Forms |

Atualize esta tabela ao criar pastas novas (ex.: `src/`, `data/`, `notebooks/`, `eval/`).

## Convenções

- Documentação em português; código e identificadores podem ser em inglês.
- Commits curtos no imperativo, com prefixo: `docs: ...`, `feat: ...`, `fix: ...`, `exp: ...` (experimentos).
- Nunca commitar segredos (`.env`, chaves de API) nem dados pessoais. O tema envolve dados de qualidade de vida/saúde: trate LGPD como requisito.
- Datasets e índices vetoriais grandes ficam fora do git (ver `.gitignore`); registre a origem e como reproduzi-los na documentação.
- Prefira linkar a duplicar: um fato vive em um lugar só.

## Ao terminar uma sessão

1. Atualize `STATUS.md`: o que mudou, o que ficou pendente, próximos passos.
2. Tomou uma decisão técnica? Crie um ADR em `docs/decisoes/` a partir de `0000-template.md`.
3. Registre o progresso relevante em `docs/semanas/semana-NN.md`.
4. Mudou algo que aparece no mapa da arquitetura (decisão, componente, fluxo, situação de algo planejado)? Atualize `docs/arquitetura/index.html` seguindo [docs/arquitetura/AGENTS.md](docs/arquitetura/AGENTS.md).
