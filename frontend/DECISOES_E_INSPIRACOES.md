# Decisões de Design, UX/UI e Inspirações — Home da Sala (`v2`)

Este diretório contém o protótipo web interativo da tela **Home da Sala (etapa de votação)** do **Orquestrador de Rolês em Brasília**, evoluído a partir do protótipo criado no Figma ([abrir `Home da Sala (v2)`](https://www.figma.com/design/NwODIKznrGjn24i1HWNjiP/Untitled?node-id=53-3)).

---

## 1. Inspirações e Referências

- **Base visual do projeto (Figma):** estrutura contínua em desktop com barra lateral recolhida, barra de progresso no topo, destaque para a principal sugestão (*Menor Miséria*) e painel direito com a turma.
- **Sugestões de fluxo da equipe (`origin/frontend_miti`):**
  - Bloco *"Por que sugerimos"* explicando de forma transparente por que o local atende o grupo.
  - Botão de preview em modal vertical do **TikTok** para sentir a vibe do lugar antes de votar.
  - Foco em **3 opções validadas** em vez de listas longas.
- **Referências de produtos sociais de consumo (Partiful, Luma, Beli):**
  - Priorizar decisão rápida entre amigos em vez de visual denso de painel corporativo (SaaS/CRM).
  - Reduzir competição visual entre ações principais e metadados informativos.

---

## 2. Decisões de UX/UI Aplicadas

### A. Paleta do Figma com Contraste Corrigido
- Mantivemos a identidade índigo/lilás do protótipo do Figma (`#4B4590`, `#2E2A5E`, `#EFEBFA`, `#DDF5EF`).
- **Remoção de manchas/degradês no fundo:** o fundo passou a usar `#F6F4FB` sólido e os cards passaram a usar `#FFFFFF` com borda nítida (`1.5px solid #C4BCE4`), eliminando a sensação de seções misturadas.

### B. Distinção Clara entre Clicável vs. Informação Estática
- **Elementos clicáveis** (`Votar`, `Votar neste rolê`, `Ver no TikTok`, `Convidar`, `Abrir/Fechar aba`, pins do mapa):
  - Bordas visíveis (`1.5px`), cantos de `12px`, sombra seca inferior (`0 3px 0 #2E2A5E`), cursor pointer e feedback visual imediato ao clicar.
  - Ao votar, o botão muda para `✓ Voto registrado` em verde (`#146356`), destaca o card e atualiza a barra de votos da turma.
- **Tags e status informativos** (`Sem glúten`, `Vegano`, `Cabe no teto`, `Pronto`, `Aguardando`, `88%`, `81%`):
  - Cantos menores (`6px`), sem borda e sem sombra, visualmente planos para não parecerem botões.

### C. Redução de Ruído e Ansiedade
- **Sem timer regressivo:** o cronômetro de contagem regressiva foi removido para não gerar ansiedade; em seu lugar ficou apenas o status tranquilo **`Votos da turma`** (`2 de 4 votos`).
- **Remoção de "Conte o que você espera" na votação:** como as sugestões só existem depois que as preferências são enviadas, o formulário saiu desta etapa.

### D. Mapa do DF e Histórico de Rolês Retráteis + Zero Scroll
- **Mapa do DF:** inicia **aberto por padrão** no painel direito com pins clicáveis (*Asa Norte*, *Asa Sul*, *Guará*), mas conta com o botão **`Fechar aba ▴`** caso o usuário prefira recolher.
- **Histórico de rolês:** movido para uma aba retrátil logo abaixo do mapa (inicia fechado com **`Abrir aba ▾`**). Abrir uma aba recolhe a outra automaticamente.
- **Sem scroll vertical no desktop:** container ajustado para `100vh` (`calc(100vh - 32px)`) e cards compactados verticalmente para manter os botões próximos ao conteúdo e tudo visível na tela sem rolagem.

---

## 3. Como Visualizar

Abra o arquivo [`home_sala_v2.html`](./home_sala_v2.html) diretamente no navegador:

```bash
xdg-open frontend/home_sala_v2.html
```
