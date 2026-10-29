# 0003 — Canal do MVP: app web próprio

- **Status:** proposta (definida na sessão de requisitos de 29/10; confirmar com o grupo)
- **Data:** 2026-10-29
- **Semana do roadmap:** 1

## Contexto

A [visão do produto](../produto/visao.md) deixava o canal em aberto: app próprio ou bot no grupo de conversa. No Brasil o grupo de amigos costuma estar no WhatsApp, mas a Meta restringe chatbots de IA de uso geral na API do WhatsApp Business, que também exige conta comercial e cobra por conversa.

## Opções consideradas

1. **App web próprio.** Controle total da interface (comparar planos, mapa, grade de horários, votação, voz, acessibilidade). Exige mais front-end, e o grupo precisa sair do WhatsApp para usar.
2. **Bot no Telegram.** API aberta e gratuita, com grupo e conversa privada nativos. Pouco usado pelo público para combinar encontros.
3. **Bot no WhatsApp.** É onde o público está, mas depende das políticas e do custo da Meta.
4. **Bot no Discord.** Aberto e gratuito, com público mais gamer.

## Decisão

App web próprio, pensado primeiro para o celular e instalável (PWA). Quando o plano é fechado, o app exporta o resumo para o WhatsApp, pelo compartilhamento nativo do celular, e o evento para as agendas (Google, Apple, Android).

## Justificativa e evidências

- A interface precisa mostrar planos lado a lado, custo e deslocamento por pessoa, votação e transcrição de voz, o que um bot de chat mostra mal.
- O público inclui pessoas mais velhas e com pouca experiência em apps (RNF-07 de [requisitos.md](../produto/requisitos.md)), o que pede controle sobre fonte, contraste e fluxos.
- A conversa privada e o chat do grupo ficam dentro do app, o que facilita garantir o sigilo do orçamento (RNF-02).
- A exportação para o WhatsApp mantém o grupo onde ele já conversa, sem depender da API da Meta.

## Riscos e limitações

- Atrito de adoção: os amigos precisam entrar em mais um app. Mitigação: convite por link, poucas idas ao app (RNF-06), notificações agrupadas (RF-41).
- No iOS, notificações de app web só funcionam com o app adicionado à tela inicial.
- Mais trabalho de front-end que um bot.

## Como vamos validar

- No piloto, medir a porcentagem de convidados que entram na sala e a de rolês que chegam até a votação.
