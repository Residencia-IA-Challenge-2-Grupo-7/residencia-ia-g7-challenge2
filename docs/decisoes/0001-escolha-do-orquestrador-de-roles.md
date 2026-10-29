# 0001 — Seguir com o Orquestrador de Rolês

- **Status:** aceita
- **Data:** 2026-10-29
- **Semana do roadmap:** 1

## Contexto

No brainwriting de 27/10 ([ata](../atas/2026-10-27.md)), o grupo chegou a duas ideias para o Challenge 2: o **Orquestrador de Rolês** (IA que medeia a organização de encontros entre amigos, com o Modo Descoberta para formar grupos novos) e o **Organiza Suas Compras** (despensa digital e lista de compras com IA). Era preciso escolher uma para montar o pacote de definição do projeto.

## Opções consideradas

1. **Orquestrador de Rolês.** Ataca a solidão e a conexão social, que a OMS trata como problema de saúde pública. A IA apoia uma decisão coletiva com restrições reais (agenda, orçamento, distância, preferências). Encaixa naturalmente no roadmap: RAG para lugares e preços, multiagentes para representar cada membro, multimodal com fotos de notas fiscais e locais. Pontos fracos: privacidade (localização e dinheiro), segurança no Modo Descoberta e dependência de APIs de mapas.
2. **Organiza Suas Compras.** Tem boa evidência sobre desperdício doméstico de alimentos e um uso multimodal claro (foto da nota fiscal). Pontos fracos: o núcleo tende a virar um cadastro de estoque, e manter esse estoque atualizado depende de registro manual do que é consumido.

## Decisão

Seguir com o **Orquestrador de Rolês**, incluindo o Modo Descoberta como extensão.

## Justificativa e evidências

- A dor está ligada a um determinante de saúde: a solidão afeta 1 em cada 6 pessoas e está associada a cerca de 871 mil mortes por ano (OMS, 2025).
- As barreiras que a ideia ataca aparecem em pesquisas: custo escondido (CFP Board, 2026), medo de incomodar (Liu et al., 2022) e falta de tempo junto para manter amizades (Hall, 2018; Roberts e Dunbar, 2015).
- Atende ao critério que o grupo usou para filtrar ideias: a IA precisa apoiar uma decisão de verdade, não só organizar registros.
- Há espaço no mercado: existem ferramentas para partes do problema, mas nenhuma junta disponibilidade, orçamento, transporte e decisão justa do grupo.

Evidências e concorrentes detalhados em [docs/produto/visao.md](../produto/visao.md).

## Riscos e limitações

- Dados sensíveis (localização, rotina, orçamento): LGPD é requisito.
- Modo Descoberta junta desconhecidos: exige regras de segurança, idade mínima e moderação.
- A versão para amigos não atende quem não tem rede; o Modo Descoberta cobre isso só em parte.
- Dependência de APIs de lugares, mapas e jogos, algumas pagas ou fechadas.
- Escopo grande para 7 semanas: o MVP precisa ser recortado.

## Como vamos validar

- Formulário "Pesquisa de Hábitos Sociais" para confirmar a dor com o nosso público.
- Métricas de sucesso a definir no pacote da semana 1 (por exemplo, taxa de planos que viram encontros e taxa de lugares sugeridos que existem de fato).
