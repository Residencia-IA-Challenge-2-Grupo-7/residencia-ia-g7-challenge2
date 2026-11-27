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

---

## 4. Próxima Evolução: Naming, Tom de Voz e Identidade Retrô Pop (Proposta para o Grupo)

Direção definida em exploração de marca e visual para ser **apresentada e validada com o grupo na próxima semana**.

### A. Nome Provisório: **Qual o Plano?**
- **Por que esse nome:** une em três palavras uma expressão natural de grupo de amigos (*"qual é o plano de hoje?"*) com uma referência imediata ao **Plano Piloto** de Brasília, sem soar literal ou turístico demais.
- **Alternativas levantadas durante o brainstorm (caso o grupo queira comparar na reunião):** *Nos Eixos*, *Cabe na Brasília?*, *Hoje é no Plano?*, *A Boa do Plano*, *Em Bloco*, *Qual o Setor?*, *Amarelê*, *Pilotis* e *Cobogó*.

### B. Tom de Voz na Interface
- Trazer para os textos da interface (saudações, tela de criar sala, placeholders e chamadas da IA) expressões reais usadas no dia a dia para combinar rolê:
  - *"E aí, qual a boa?"*
  - *"Hoje é onde?"*
  - *"Bora achar a boa de hoje"*

### C. Estética Visual: Retrô Pop / Neobrutalismo Alegre
Evolução direta das bordas nítidas e sombras secas já aplicadas na `v2`, combinando três referências:
- **UI em estilo *Sticker* / 3D Retrô:** fundo em **grid quadriculado suave**, cards e botões com borda escura nítida (`2px`) e sombra dura deslocada (`4px 4px 0`).
- **Toque *Groovy* Anos 70:** tipografia retrô com contorno e sombra dura reservada para **logo, títulos principais e selos**, mantendo fonte limpa e de alta leitura dentro dos cards e listas.
- **Brasília Amarela como elemento icônico:**
  - **Logo / Cabeçalho:** ilustração em estilo *sticker* com contorno escuro ao lado do título **Qual o Plano?**.
  - **Barra de votos da turma:** mini Brasília Amarela avançando conforme os amigos votam (`2 de 4 votos`).
  - **Carregamento dos agentes de IA:** carro em movimento enquanto a turma aguarda as 3 opções validadas.
  - **Mapa do DF:** pins das Regiões Administrativas inspirados nas placas verdes tradicionais das quadras de Brasília.

### D. Paleta Retrô Pop Proposta
- **Amarelo Retrô (`#FFC567`)** *(com opção de `#FFE500` na lataria da Brasília Amarela)*: botões principais de ação (CTAs), destaque da sugestão nº 1 e identidade do carro.
- **Roxo (`#552CB7`):** mantém conexão com a base índigo/roxa do protótipo original do Figma; uso em avatares e destaques secundários.
- **Verde (`#00995E`):** feedback de `✓ Voto registrado` e pins/placas do mapa do DF.
- **Coral (`#FD5A46`) e Rosa (`#FB7DA8`):** selos de compatibilidade (`88%`), tags informativas e diferenciação dos participantes.
- **Azul (`#058CD7`):** rotas, informações de transporte no DF e links.
- **Base e Contornos:** fundo claro/creme com grid sutil, e traços/textos principais em grafite escuro ou marrom café retrô (como o `#5B2F15` da paleta complementar salva em `inspiracoes/`).

### E. Kit de Logos e Ícones Gerados (`assets/logos/`)
Para visualizar todas as variações em tamanho real e simulações de interface, abra [`logos_marca.html`](./logos_marca.html) (`xdg-open frontend/logos_marca.html`). Arquivos em PNG transparente e ICO disponíveis em `frontend/assets/logos/`:
- **Completa Horizontal (Nome + Carro):** `logo_completa_horizontal_1200.png`, `_600.png`, `_320.png` (hero, slides, capa).
- **Badge / Selo Quadrado (Nome + Carro):** `logo_badge_512.png`, `_256.png`, `_128.png` (avatar, splash, cards).
- **Só o Nome (Wordmark):** `logo_nome_800.png`, `_400.png`, `_220.png` (navbar estreita, rodapé).
- **Só o Carro — Ícone & Favicon:** `carro_icone_512.png`, `_192.png`, `_64.png`, `_32.png` e `favicon.ico`.
- **Só o Carro — Perfil Lateral:** `carro_lateral_480.png`, `_160.png`, `_64.png` (barra de votos da turma e loading da IA).

---

## 5. Direção Consolidada para Implementação (`v3` — *Qual o Plano?*)

Decisões finais definidas para transformar a interface atual (`v2`) na nova identidade visual do site:

1. **Paleta Solar como Base Principal:**
   - **Fundo e superfícies:** Creme Baunilha suave (`#FFF9DC` / `#FFF5B4`) com cards limpos em marfim claro (`#FFFDF6`) para garantir leitura confortável sem degradês ou manchas lavadas.
   - **Tipografia e bordas:** Marrom Café (`#5B2F15`) nos títulos, textos principais e contornos nítidos (`1.5px`–`2px`), e Terracota (`#834A29`) nos textos secundários e apoios.
   - **Ações clicáveis (CTAs):** Amarelo Ouro / Ipê (`#FFC800` / `#FFE500`) com texto e borda em `#5B2F15` e sombra seca (`0 3px 0 #5B2F15`), reforçando o contraste com as tags informativas planas.
   - **Apoio semântico (do kit Retrô Pop):** Verde (`#00995E`) para confirmações (`✓ Voto registrado`, `Pronto`) e placas do mapa do DF; Roxo (`#552CB7`) reservado apenas para avatares e detalhes pontuais de diferenciação.

2. **Adeus Barra Lateral Roxa (Topbar Leve e Social):**
   - Remoção da barra lateral escura que dava aspecto de painel SaaS/CRM.
   - Substituição por uma **barra superior horizontal leve** contendo o logo oficial **Qual o Plano?** (`assets/logos/logo_completa_horizontal_320.png` ou `logo_nome_220.png`) à esquerda e os controles globais de conta (**Meu Perfil**, **Notificações** e **Configurações**) à direita, deixando a navegação limpa e com cara de app social.

3. **Identidade Oficial e Elementos da Brasília Amarela:**
   - Substituição definitiva do placeholder `LOGO` pelos assets oficiais em `frontend/assets/logos/` e `favicon.ico`.
   - Uso da Brasília Amarela lateral (`carro_lateral_64.png` / `_160.png`) como marcador dinâmico na barra de progresso **`Votos da turma`**.

4. **Cards Minimalistas Limpos (Sem Fotos, Foco em Tipografia e Ícones):**
   - Nos cards de **Votação** (`home_sala_v2.html`) e no **Card Vencedor** (`resultado_role.html`), visual minimalista **sem fotos**, com foco em tipografia marcante, ícones leves, tags planas e espaçamento limpo para leitura instantânea e layout sem scroll no desktop.

5. **Tipografia, Cantos e Tom de Voz:**
   - Títulos em `Space Grotesk` / `Poppins` bold com cantos arredondados modernos (`16px`–`20px` nos cards, `12px` nos botões, `6px` nas tags estáticas) e microcopy brasiliense descontraído (*"E aí, qual a boa?"*, *"Hoje é onde?"*).

