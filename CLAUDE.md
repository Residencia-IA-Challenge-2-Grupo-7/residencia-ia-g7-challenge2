@AGENTS.md

## Específico do Claude Code

- Sessões paralelas que alteram código: uma worktree por tarefa, para uma sessão não sobrescrever os arquivos da outra.
- Se uma subpasta ganhar regras próprias (ex.: `src/rag/`), crie um `CLAUDE.md` nela; ele só é carregado quando o trabalho acontece ali.
