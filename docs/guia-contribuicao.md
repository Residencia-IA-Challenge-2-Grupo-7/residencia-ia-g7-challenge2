# Guia de Contribuição da Equipe — Orquestrador de Rolês (Grupo 7)

Este guia define as boas práticas de engenharia de software e os padrões obrigatórios de Git adotados pelo Grupo 7 para o Challenge 2 (Residência em IA | Instituto Eldorado & UnB).

---

## 1. Fluxo de Trabalho com Branches

- A branch **`main`** é protegida e representa o código estável em produção.
- **Nunca suba código diretamente na `main`** nem faça upload de arquivos pela interface web do GitHub.
- Crie sempre uma branch a partir da `main` atualizada:

```bash
git checkout main
git pull origin main
git checkout -b <prefixo>/<nome-da-tarefa>
```

### Prefixos Permitidos de Branch:
- `feat/`: Desenvolvimento de novas funcionalidades (ex: `feat/rag-busca-hibrida`).
- `fix/`: Correções de bugs ou falhas (ex: `fix/latencia-gemini-cache`).
- `docs/`: Documentações, relatórios e manuais (ex: `docs/relatorio-semana-2`).
- `ci/`: Alterações em pipelines, Docker ou infraestrutura (ex: `ci/adiciona-linter`).

---

## 2. Padrão de Mensagens de Commit (Conventional Commits)

Todas as mensagens de commit devem seguir a convenção internacional:
`<tipo>(<escopo>): <descrição no imperativo e em minúsculas>`

### Tipos Obrigatórios:
- `feat`: Nova funcionalidade para o usuário ou sistema.
- `fix`: Correção de um bug ou erro.
- `docs`: Modificações em arquivos de documentação (Markdown, PDF, LaTeX).
- `ci`: Ajustes em scripts de CI/CD, GitHub Actions ou Dockerfile.
- `refactor`: Mudança no código que não corrige bug nem adiciona funcionalidade.
- `test`: Criação ou ajuste de testes automatizados.
- `chore`: Tarefas rotineiras de manutenção ou dependências.

**Exemplos:**
- `feat(rag): implementa similaridade de cosseno em memoria`
- `fix(telemetria): normaliza calculo de latencia no trace do langfuse`
- `docs(relatorio): atualiza analise de casos de borda da semana 2`
- `ci(docker): otimiza instalacao do pytorch para versao cpu`

---

## 3. Checklist Obrigatório para Pull Requests (PRs)

Antes de solicitar a revisão de um colega de equipe:
1. **Rode os testes:** Verifique se `pytest` executa 100% verde.
2. **Segurança de Segredos:** Certifique-se de que nenhuma chave (`.env`) entrou no commit.
3. **Template preenchido:** Preencha todos os campos do template automático de PR do repositório.
4. **Vínculo com a Issue:** Insira `Closes #XX` na descrição para fechar a issue automaticamente após o merge.
