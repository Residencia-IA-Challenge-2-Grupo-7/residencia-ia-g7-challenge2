# Visão do produto: Orquestrador de Rolês

Documento de referência para quem vai detalhar requisitos, riscos, personas e métricas. Reúne a ideia, a pesquisa de concorrentes e evidências, e o que ainda está em aberto. Decisão de seguir com esta ideia: [ADR 0001](../decisoes/0001-escolha-do-orquestrador-de-roles.md). O MVP cobre só o modo com amigos ([ADR 0002](../decisoes/0002-recorte-do-mvp.md)); requisitos em [requisitos.md](requisitos.md).

## Em uma frase

Uma IA mediadora que tira dos amigos o peso social de combinar encontros (dinheiro, convite, logística) e decide de forma justa para o grupo, para que se encontrem mais. O Modo Descoberta estende isso a quem não tem com quem combinar.

## Essential Question

- **Nível 1:** Como a IA pode aproximar as pessoas?
- **Nível 2:** Como sistemas de IA podem ajudar amigos a transformar a vontade de se encontrar em encontros reais, de forma justa para todos?
- **Modo Descoberta:** Como sistemas de IA podem cruzar perfis, interesses e disponibilidades para formar proativamente novos grupos de amigos, assumindo o peso do convite inicial e eliminando o medo da rejeição?

## Problema

Amigos querem se ver, mas o encontro morre na organização:

- **Comunicação:** ninguém toma a iniciativa; há vergonha de falar de dinheiro, de incomodar ou de parecer "pidão".
- **Decisão:** dá "branco" na hora de escolher o que fazer e aonde ir.
- **Ferramentas:** agenda, mapa e divisão de contas ficam em apps diferentes, e organizar vira trabalho.

Para quem está sozinho, a maior dor não é organizar, e sim não ter quem convidar, somada ao medo da rejeição.

**Por que isso é qualidade de vida.** A OMS define solidão como a distância entre a conexão social que a pessoa quer e a que ela tem; isolamento social é a falta objetiva de vínculos. Amigos que quase nunca se veem podem estar sós mesmo tendo rede. O cenário com amigos ataca a solidão; o Modo Descoberta ataca o isolamento.

## Como funciona

**Com amigos**

- Cada pessoa informa localização, dias e horários livres, preferências, orçamento (em sigilo) e, se quiser, contas de jogos.
- Os usuários criam salas com os amigos.
- A IA conversa em particular com cada membro, pesquisa lugares e eventos, planeja rota, transporte, horários, comida e itens para levar, e propõe 2 ou 3 planos completos com o custo de cada pessoa.
- O grupo escolhe; a IA divide os custos e aprende com a avaliação depois do encontro.
- Quando não dá para sair, sugere jogos baratos para jogar online.

**Modo Descoberta**

- Quem ativa informa interesses, orçamento, horários, idade, gênero e preferências de grupo (mesmo gênero, misto, faixa etária).
- A IA agrupa pessoas compatíveis (4 a 6), monta um evento pronto num local central e envia convites privados, que podem ser aceitos ou recusados sem pressão.
- A sala de conversa só é criada quando o evento está confirmado. Quem se der bem pode passar a usar o modo com amigos.

**Os três verbos**

- **Compreender:** cada pessoa vê, antes de aceitar, o custo, o tempo de deslocamento e a disponibilidade do grupo.
- **Decidir:** a decisão é coletiva, com preferências em conflito; a IA gera opções viáveis, mostra os prós e contras e conduz a escolha sem decidir pelo grupo.
- **Viver melhor:** menos atrito para combinar, ninguém excluído por dinheiro ou distância, mais encontros.

## Diferenciais

1. **IA como intermediária social:** conversa com cada pessoa em particular e assume o papel de quem organiza e de quem faz o primeiro convite.
2. **Orçamento em sigilo:** cada pessoa informa seu limite, e a IA respeita o menor sem expor ninguém.
3. **Plano completo com custo por pessoa:** local, transporte, comida, itens e divisão da conta antes do encontro.
4. **Decisão justa:** equilibrar tempo de deslocamento e custo entre os membros, em vez de só tirar a média.
5. **Plano B online barato:** jogos que todos já têm, promoções e Remote Play Together da Steam, em que só o anfitrião precisa ter o jogo.

## Concorrentes

| Categoria | Exemplos | O que fazem | O que não fazem |
|---|---|---|---|
| IA em grupos de conversa | Continua, Meta AI no WhatsApp | Acompanham disponibilidade, propõem horários, sugerem lugares | Orçamento, transporte por pessoa, plano B online |
| Agenda compartilhada | Howbout, Sha, Gatherly | Cruzam disponibilidade, enquetes, reservas | Planejar o encontro inteiro, dinheiro |
| Convites e eventos | Partiful, eventos e enquetes do WhatsApp | Convite, confirmação, votação | Inteligência: alguém ainda decide tudo |
| Ponto de encontro justo | midway@, Split The Drive | Local com tempo de viagem equilibrado | Preferências, orçamento, horários |
| Divisão de contas | Splitwise, SplitSnap | Leitura de nota fiscal e divisão por item | Planejar antes do encontro |
| Conhecer pessoas | Timeleft (já no Brasil), Bumble BFF | Grupos de desconhecidos por afinidade | Integração com o grupo de amigos existente |

Não foi encontrado app brasileiro com IA para combinar encontros entre amigos.

## Decisões em aberto

- **Canal:** app próprio ou bot no grupo de conversa. No Brasil o grupo vive no WhatsApp, mas a Meta passou a restringir chatbots de IA de propósito geral na API do WhatsApp Business (verificar se um bot com função específica é permitido). Telegram e Discord são mais abertos. Proposta: app web próprio ([ADR 0003](../decisoes/0003-canal-app-web.md)).
- **Disponibilidade:** pedir dias e horários, importar do calendário ou deduzir da conversa.
- **Regra de decisão do grupo:** média, "menor miséria" (proteger quem fica menos satisfeito) ou rodízio. A literatura não aponta uma regra universalmente melhor, e agentes LLM tendem a simplesmente tirar a média quando não recebem uma regra explícita. Precisa virar ADR.
- **LLM orquestra, solver otimiza:** caronas e ponto de encontro são problemas de otimização (roteamento), que um LLM resolve mal sozinho.
- **Quem decide:** todo o grupo ou um anfitrião.
- **Dados de lugares e preços:** Google Places (pago) ou OpenStreetMap (grátis, com poucos preços e avaliações); eventos via Sympla ou agenda cultural do GDF; dados abertos de transporte do DF (GTFS) a verificar.
- **Jogos:** Steam tem API (só perfis públicos); Xbox e PlayStation não têm API pública aberta. Sugestão: só Steam no MVP.
- **Divisão de custos:** igual ou por consumo; gerar cobrança Pix ou só calcular.
- **Partida a frio:** o que sugerir antes de haver avaliações de encontros anteriores.
- **Presencial versus online:** o plano B não pode virar substituto do encontro; o app prioriza o presencial.

## Riscos conhecidos

- **Privacidade:** localização, rotina, renda e rede de amizades são dados sensíveis (LGPD).
- **Exclusão financeira:** a divisão de custos pode constranger quem tem menos dinheiro.
- **Dados inventados:** a IA pode sugerir lugares, preços ou horários que não existem.
- **Segurança:** encontros à noite, volta para casa e, no Modo Descoberta, encontros entre desconhecidos (perfis falsos, assédio).
- **Álcool:** churrasco e bares envolvem bebida.
- **Dependência de APIs:** custo, limites e políticas de terceiros.
- **Métricas de vaidade:** medir encontros realizados, não downloads (o app de eventos IRL fechou após admitir que 95% dos usuários eram falsos).

## Encaixe no roadmap

| Semana | Como aparece |
|---|---|
| 2. RAG | Base de lugares, eventos, preços, horários, regras de transporte e catálogo de jogos |
| 3. LLM x RAG | Medir quantos lugares, preços e horários o LLM puro inventa e o RAG acerta |
| 4. Multiagentes | Um agente por membro, mais planejador, logística, finanças e mediador |
| 5. Multimodal | Foto da nota fiscal para dividir a conta, fotos e mapas dos locais, mensagens de voz |
| 6. Integração | Aplicação funcional, possivelmente como bot |
| 7. Testes | Métricas e piloto com grupos reais |

## Evidências

- OMS, Comissão sobre Conexão Social (2025): 1 em cada 6 pessoas afetada pela solidão; cerca de 871 mil mortes por ano associadas; 17% a 21% entre 13 e 29 anos. [Link](https://www.who.int/NEWS/ITEM/30-06-2025-SOCIAL-CONNECTION-LINKED-TO-IMPROVED-HEATH-AND-REDUCED-RISK-OF-EARLY-DEATH)
- Holt-Lunstad, Smith e Layton (2010): relações sociais fortes associadas a cerca de 50% mais chance de sobrevivência. *PLoS Medicine* 7(7): e1000316.
- Ipsos (2021): Brasil em 1º lugar entre 28 países em solidão (50%, durante a pandemia). [Link](https://www.ipsos.com/pt-br/brasil-fica-em-1o-lugar-entre-28-paises-em-ranking-dos-que-mais-sentem-solidao)
- Hall (2018): cerca de 50 horas juntos para virar amigo casual, 90 para amigo, mais de 200 para amigo próximo. [Link](https://news.ku.edu/2018/03/06/study-reveals-number-hours-it-takes-make-friend)
- Roberts e Dunbar (2015): a queda na qualidade das amizades é contida por contato frequente e atividades juntos. [Link](https://www.neuroscience.ox.ac.uk/publications/572905)
- Teo et al. (2015): contato presencial frequente associado a menos depressão; telefone e e-mail sem efeito consistente (estudo observacional). [Link](https://www.healthday.com/health-news/public-health/face-to-face-contact-may-beat-email-phone-for-staving-off-depression-703896.html)
- CFP Board (2026): 67% recusaram eventos por custo em 2 anos; 56% não disseram que o motivo era dinheiro. [Link](https://www.cfp.net/news/2026/03/financial-fomo-quietly-straining-american-relationships)
- Liu et al. (2022): quem entra em contato subestima o quanto o outro gosta de ser chamado. [Link](https://psypost.org/study-identifies-a-robust-tendency-to-underestimate-how-much-others-appreciate-being-reached-out-to)
- Epley e Schroeder (2014): as pessoas subestimam o quanto vão gostar de conversar com desconhecidos. [Link](https://www.chicagobooth.edu/review/talk-to-a-stranger-itll-make-you-happier)
- Recomendação para grupos: não há regra de agregação universalmente melhor. [Link](https://arxiv.org/pdf/2205.11127)
- Consenso entre agentes LLM tende à média sem estratégia explícita. [Link](https://arxiv.org/pdf/2310.20151)

Pesquisas encomendadas por empresas (Ally, Bumble, Talker Research) e números divulgados pelas próprias empresas devem ser citados com ressalva.
