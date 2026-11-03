# Requisitos do MVP: Orquestrador de Rolês

- **Versão:** 0.3.1, 2026-11-03
- **Status:** para revisão do grupo. As escolhas de comportamento foram feitas na sessão de requisitos de 29/10 e ainda precisam ser validadas com o grupo, as personas e o resultado do formulário. O fechamento do MVP estava previsto para 30/10/2026 (premissa P04).
- **Base:** [visão do produto](visao.md) · recorte do MVP no [ADR 0002](../decisoes/0002-recorte-do-mvp.md) · canal no [ADR 0003](../decisoes/0003-canal-app-web.md)

## Como ler

- **IDs fixos.** RF-NN são funcionais e RNF-NN são não funcionais. Um ID nunca é reaproveitado: requisito que sai fica marcado como *removido*.
- **Prioridade provisória (MoSCoW):** **Must** (sem isso o MVP não resolve o problema), **Should** (importante, entra se couber nas 7 semanas), **Could** (desejável). O que está fora do MVP fica em [Extensões futuras](#7-extensões-futuras).
- **Notação (estilo OpenSpec):** cada requisito tem um enunciado com **DEVE** e cenários **QUANDO / ENTÃO**, que servem de critério de aceitação e, depois, de casos de teste.
- **Rastreabilidade:** a coluna Persona (só na tabela de RF) usa as personas da equipe (Rafaela, primária; Cadu, Bia e Márcio, secundárias). A coluna Riscos usa os IDs da guia Riscos do documento da equipe (lista em [Riscos referenciados](#riscos-referenciados)). A coluna Métrica fica em branco até o plano de métricas de sucesso ser fechado.
- **Documento final:** entra só o que é Must, agrupado por capacidade (ver [seção 4.12](#412-agrupamento-para-o-documento-final)). Esta lista completa fica no repositório.

## 1. Escopo do MVP

**Dentro**

- Organização de rolês entre amigos que já se conhecem, em salas de 2 a 20 pessoas.
- App web, pensado primeiro para o celular. A exportação do plano fechado para o WhatsApp e para a agenda entra se couber (Should, RF-27 e RF-28).
- Distrito Federal inteiro; adultos (18+) de qualquer idade.
- Quatro tipos de rolê: comer e beber fora, eventos com data marcada, ao ar livre ou gratuitos e, se couber, em casa de alguém (Should, RF-20).
- Conversa por texto e por voz.

**Fora** (ver [Extensões futuras](#7-extensões-futuras))

- Modo Descoberta, videogames e plano B online, versão para menores de idade.

## 2. Glossário

| Termo | Significado |
|---|---|
| Sala | Grupo fixo de amigos no app (2 a 20 membros), com um chat do grupo |
| Organizador | Quem criou a sala, com papel transferível. Configura o modo de decisão, a regra de preferência de datas, os prazos de resposta e a iniciativa da IA |
| Rolê | Um encontro em organização dentro de uma sala, do pedido até a avaliação |
| Participante | Membro da sala convidado para um rolê específico |
| Conversa privada | Chat individual entre um participante e a IA. O que é dito ali não aparece para os outros |
| Plano | Proposta completa de rolê: o quê, onde, quando, como cada um chega e volta, e custo estimado por pessoa |
| Restrição dura | Condição que elimina um plano: orçamento, disponibilidade, horário de funcionamento, restrições declaradas e, quando houver caronas, a capacidade dos carros |
| Janela | Intervalo de data e hora em que os participantes estão livres |
| Prazo de resposta | Tempo que a IA espera por uma resposta antes de seguir com uma ação padrão (o organizador pode ajustar; valores padrão em aberto) |
| Gasto | Valor pago por um participante durante o rolê e dividido com os outros |
| Saldo | O que cada membro deve ou tem a receber na sala, somando os rolês |

## 3. Fluxo principal

1. Um membro cria a sala e convida os amigos por link. Quem criou vira organizador.
2. Um membro pede um rolê ("bora sair sábado?"), ou a IA sugere um quando a sala passa um tempo sem se encontrar.
3. A IA conversa em particular com cada participante: disponibilidade, preferências, orçamento, ponto de partida e transporte.
4. A IA cruza as janelas, aplica a regra de preferência de datas do organizador e busca lugares e eventos na base de conhecimento.
5. A IA descarta planos que violam restrições duras. Se o orçamento de alguém travar as opções, pergunta em particular se a pessoa pode flexibilizar.
6. A IA apresenta 2 ou 3 planos ranqueados por justiça, com prós, contras e custo por pessoa.
7. O grupo vota, ou o organizador decide, conforme o modo da sala. Os participantes confirmam presença.
8. O plano fechado é compartilhado no WhatsApp e exportado para a agenda. A IA lembra cada um do horário de saída.
9. Depois do rolê, a IA pergunta se alguém pagou algo para rachar, divide os gastos, envia o Pix de quem pagou e lembra quem deve.
10. A IA pergunta se o encontro aconteceu e oferece uma avaliação opcional por item, que alimenta os próximos planos.

## 4. Requisitos funcionais

### Resumo

| ID | Requisito | Prioridade | Riscos | Persona | Métrica |
|---|---|---|---|---|---|
| RF-01 | Cadastro e perfil | Must | R-01 | Todas | |
| RF-02 | Consentimento e controle dos dados | Must | R-01, R-09 | Márcio, Cadu | |
| RF-03 | Sala e convites (2 a 20 membros) | Must | | Rafaela | |
| RF-04 | Gestão da sala pelo organizador | Must | | Rafaela | |
| RF-05 | Pedido de rolê por qualquer membro | Must | | Rafaela | |
| RF-06 | Iniciativa da IA | Must | R-04 | Rafaela | |
| RF-07 | Conversa privada com cada participante | Must | R-01 | Cadu, Rafaela | |
| RF-08 | Disponibilidade por conversa livre | Must | | Cadu, Márcio | |
| RF-09 | Disponibilidade por grade de horários | Should | | Cadu, Márcio | |
| RF-10 | Disponibilidade pelo Google Agenda | Could | R-01 | | |
| RF-11 | Orçamento sigiloso | Must | R-01, R-02 | Cadu, Rafaela | |
| RF-12 | Prazo de resposta e ação padrão | Must | R-04 | Rafaela | |
| RF-13 | Cruzamento de disponibilidades | Must | | Cadu, Rafaela | |
| RF-14 | Regra de preferência de datas do organizador | Must | | Rafaela | |
| RF-15 | Planos completos com custo por pessoa | Must | R-03 | Rafaela, Cadu | |
| RF-16 | Fundamentação na base de conhecimento | Must | R-03 | Rafaela | |
| RF-17 | Filtro de restrições duras | Must | R-02 | Cadu, Bia | |
| RF-18 | Negociação privada de orçamento | Must | R-02 | Cadu | |
| RF-19 | Ranqueamento justo e explicação | Must | R-02 | Cadu | |
| RF-20 | Rolê em casa de alguém | Should | | Márcio | |
| RF-21 | Deslocamento por pessoa | Must | R-05 | Cadu | |
| RF-22 | Aviso de volta para casa | Should | R-05 | Cadu, Rafaela | |
| RF-23 | Caronas otimizadas | Should | R-05 | Rafaela, Márcio | |
| RF-24 | Modo de decisão da sala | Must | | Rafaela | |
| RF-25 | Votação | Must | | Rafaela, Márcio | |
| RF-26 | Confirmação de presença | Must | | Cadu, Bia | |
| RF-27 | Compartilhar no WhatsApp | Should | R-01 | Márcio | |
| RF-28 | Adicionar à agenda | Should | | Cadu | |
| RF-29 | Lembretes antes do encontro | Should | | Márcio | |
| RF-30 | Lançamento de gastos no chat | Must | | Rafaela | |
| RF-31 | Lançamento por foto da nota fiscal | Should | R-09 | | |
| RF-32 | Divisão dos gastos | Must | R-02 | Cadu | |
| RF-33 | Código Pix de quem pagou | Should | R-01 | Rafaela | |
| RF-34 | Quitação e lembretes discretos | Should | R-02 | Rafaela | |
| RF-35 | Saldo entre rolês | Could | | | |
| RF-36 | Confirmação de que o encontro aconteceu | Must | R-06 | | |
| RF-37 | Avaliação opcional por item | Should | | Rafaela | |
| RF-38 | Aprendizado com as avaliações | Should | | | |
| RF-39 | Entrada por voz | Must | R-09 | Márcio | |
| RF-40 | Resposta em voz | Should | R-09 | Márcio | |
| RF-41 | Notificações agrupadas | Must | R-04 | Márcio, Rafaela | |
| RF-42 | Login sem senha | Must | R-01 | Márcio | |
| RF-43 | Disponibilidade recorrente | Should | | Cadu | |
| RF-44 | Preferências de ambiente e informações do local | Should | R-01 | Bia | |
| RF-45 | Status de preenchimento | Should | R-04 | Rafaela | |
| RF-46 | Imprevistos no dia do rolê | Could | R-05 | Cadu, Bia | |

### 4.1 Conta e sala

#### RF-01 · Cadastro e perfil (Must)

O sistema DEVE permitir criar uma conta e um perfil com nome de exibição, região de partida (região administrativa, bairro ou ponto de referência, sem exigir endereço), meios de transporte que a pessoa usa, tipos de rolê preferidos, restrições alimentares e de acessibilidade e, opcionalmente, um orçamento padrão sigiloso.

**Cenário: menor de idade**
- **QUANDO** a pessoa informa idade abaixo de 18 anos
- **ENTÃO** o cadastro é recusado com uma explicação, e os dados informados não são guardados

**Cenário: perfil incompleto**
- **QUANDO** a pessoa pula os campos opcionais
- **ENTÃO** ela consegue entrar em salas, e a IA pergunta o que faltar na conversa privada do primeiro rolê

#### RF-02 · Consentimento e controle dos dados (Must)

O sistema DEVE pedir consentimento separado para cada finalidade sensível (localização, agenda, voz, foto da nota fiscal, chave Pix) e permitir que a pessoa veja, corrija, exporte e apague os próprios dados e a conta.

**Cenário: revogação**
- **QUANDO** a pessoa desconecta a agenda
- **ENTÃO** a conexão é removida e os horários importados são apagados

**Cenário: exclusão da conta**
- **QUANDO** a pessoa pede para apagar a conta
- **ENTÃO** o app avisa se há saldos em aberto e, depois da confirmação, remove os dados pessoais; nos rolês passados ela aparece como "ex-membro"

#### RF-03 · Sala e convites (Must)

O sistema DEVE permitir que qualquer usuário crie uma sala, da qual passa a ser o organizador, e convide amigos por um link compartilhável. Uma sala tem no máximo 20 membros e precisa de pelo menos 2 para iniciar um rolê.

**Cenário: sala cheia**
- **QUANDO** uma 21ª pessoa abre o link de convite
- **ENTÃO** a entrada é recusada com uma explicação, e o organizador é avisado

**Cenário: sala com uma pessoa só**
- **QUANDO** a sala tem só 1 membro
- **ENTÃO** não é possível iniciar um rolê, e o app sugere convidar alguém

#### RF-04 · Gestão da sala (Must)

O sistema DEVE permitir que o organizador transfira o papel para outro membro, remova membros e configure a sala: modo de decisão (RF-24), regra de preferência de datas (RF-14), prazos de resposta (RF-12) e iniciativa da IA (RF-06). Qualquer membro pode sair da sala.

**Cenário: organizador sai**
- **QUANDO** o organizador tenta sair sem transferir o papel
- **ENTÃO** o app pede que ele escolha um sucessor; se ele não escolher, o papel passa ao membro mais antigo

#### RF-42 · Login sem senha (Must)

O sistema DEVE permitir entrar sem criar senha, com um código de uso único enviado ao telefone ou ao e-mail, ou com uma conta Google. O método do MVP está em aberto, porque SMS e WhatsApp têm custo.

**Cenário: primeiro acesso pelo convite**
- **QUANDO** alguém abre o link de convite sem ter conta
- **ENTÃO** entra informando só o telefone ou o e-mail e o código recebido, e cai direto na sala

**Cenário: código expirado**
- **QUANDO** o código passa da validade
- **ENTÃO** o app oferece reenviar com um toque

### 4.2 Início do rolê

#### RF-05 · Pedido de rolê (Must)

O sistema DEVE permitir que qualquer membro peça um rolê em linguagem natural, por texto ou voz, indicando, se quiser, o período, o tipo de rolê e quem convidar (por padrão, a sala toda). Um rolê precisa de pelo menos 2 participantes.

**Cenário: pedido vago**
- **QUANDO** alguém escreve "bora sair semana que vem?"
- **ENTÃO** a IA abre o rolê para a sala toda, com a próxima semana como período, e inicia as conversas privadas

**Cenário: parte da sala**
- **QUANDO** o pedido cita só alguns membros
- **ENTÃO** apenas eles recebem o convite para aquele rolê

#### RF-06 · Iniciativa da IA (Must)

O sistema DEVE sugerir um rolê no chat da sala quando ela passar um período configurável sem encontro realizado, respeitando um limite de frequência. O organizador pode ajustar o período ou desligar a iniciativa.

**Cenário: sala parada**
- **QUANDO** a sala ultrapassa o período sem rolê realizado
- **ENTÃO** a IA posta uma sugestão ("faz 3 semanas que vocês não se veem, querem que eu organize algo?"), e o rolê começa quando qualquer membro aceita

**Cenário: ninguém responde**
- **QUANDO** a sugestão fica sem resposta até o prazo
- **ENTÃO** a IA não insiste até o próximo período

### 4.3 Conversa privada e disponibilidade

#### RF-07 · Conversa privada com cada participante (Must)

O sistema DEVE abrir uma conversa privada entre a IA e cada participante do rolê para coletar disponibilidade, preferências para aquele rolê, orçamento, ponto de partida e meio de transporte, reaproveitando o que já está no perfil e perguntando só o que falta.

**Cenário: dados já no perfil**
- **QUANDO** o participante já tem transporte e orçamento padrão no perfil
- **ENTÃO** a IA só pede confirmação ("vai de ônibus e gasta até R$ 60, como sempre?")

**Cenário: tentativa de bisbilhotar**
- **QUANDO** um membro pede à IA o que outro disse em particular
- **ENTÃO** a IA se recusa a revelar

#### RF-08 · Disponibilidade por conversa livre (Must)

O sistema DEVE extrair janelas de disponibilidade de frases livres, ditas por texto ou voz, e mostrar a interpretação para confirmação antes de usá-la.

**Cenário: frase clara**
- **QUANDO** a pessoa diz "sexta depois das 19h ou sábado o dia todo"
- **ENTÃO** a IA mostra as janelas com data e hora ("sex 19h–24h; sáb dia todo. Está certo?") e só as usa depois da confirmação

**Cenário: frase ambígua**
- **QUANDO** a pessoa diz "de tarde"
- **ENTÃO** a IA assume um intervalo explícito (13h–18h) e pede confirmação

#### RF-09 · Disponibilidade por grade de horários (Should)

O sistema DEVE oferecer uma grade em que a pessoa marca e corrige blocos de horário, inclusive os extraídos da conversa.

**Cenário: ajuste fino**
- **QUANDO** a pessoa abre a grade depois de falar com a IA
- **ENTÃO** vê os blocos já preenchidos e pode ajustá-los

#### RF-10 · Disponibilidade pelo Google Agenda (Could)

O sistema DEVE permitir conectar o Google Agenda com permissão só de livre/ocupado, sem ler títulos, locais ou participantes dos eventos.

**Cenário: agenda conectada**
- **QUANDO** a agenda está conectada
- **ENTÃO** os horários ocupados saem das janelas, e a pessoa ainda pode corrigir pela conversa ou pela grade

#### RF-43 · Disponibilidade recorrente (Should)

O sistema DEVE permitir registrar uma única vez, no perfil, uma disponibilidade que se repete (semanal ou em escala, como plantões 12x36) e aplicá-la automaticamente a cada rolê, com exceções por data.

**Cenário: escala 12x36**
- **QUANDO** o participante informa "plantão 12x36 a partir de segunda, das 7h às 19h"
- **ENTÃO** a IA calcula os dias de plantão das semanas seguintes, mostra para confirmação e desconta esses dias das janelas de todo rolê

**Cenário: troca de plantão**
- **QUANDO** ele troca um plantão
- **ENTÃO** pode marcar a exceção só naquela data

#### RF-11 · Orçamento sigiloso (Must)

O sistema DEVE coletar em particular quanto cada participante quer gastar no rolê, transporte incluído, e usar esse valor só como restrição. O valor individual nunca é mostrado a outro membro nem atribuído a alguém nas explicações.

**Cenário: plano descartado por custo**
- **QUANDO** um plano é descartado por orçamento
- **ENTÃO** a explicação ao grupo diz "fora do orçamento do grupo", nunca "fora do orçamento da Ana"

**Cenário: sem resposta**
- **QUANDO** o participante não informa o orçamento até o prazo
- **ENTÃO** a IA usa o orçamento padrão do perfil ou, se não houver, o menor orçamento informado no grupo

#### RF-12 · Prazo de resposta e ação padrão (Must)

O sistema DEVE associar a cada pergunta que trava o rolê (disponibilidade, orçamento, voto, presença, lançamento de gastos) um prazo e uma ação padrão, para que o rolê avance sem depender de todos e sem que a pessoa precise voltar ao app várias vezes. O organizador pode ajustar os prazos da sala; os valores padrão estão em aberto.

**Cenário: participante não responde**
- **QUANDO** um participante não informa a disponibilidade até o prazo
- **ENTÃO** a IA segue com quem respondeu e avisa essa pessoa de que ela ainda pode entrar até a votação

**Cenário: lembrete único**
- **QUANDO** o prazo está perto do fim
- **ENTÃO** a IA manda um único lembrete

#### RF-45 · Status de preenchimento (Should)

O sistema DEVE mostrar aos participantes, e em destaque ao organizador, quantas pessoas já responderam cada etapa do rolê (disponibilidade, orçamento, voto, presença) e quanto falta para o prazo, sem mostrar o conteúdo das respostas nem quem ainda não respondeu.

**Cenário: acompanhamento**
- **QUANDO** 5 de 7 participantes informaram a disponibilidade
- **ENTÃO** a sala mostra "5 de 7 responderam" e o prazo restante, e os lembretes a quem falta ficam por conta da IA (RF-12)

### 4.4 Datas

#### RF-13 · Cruzamento de disponibilidades (Must)

O sistema DEVE encontrar as janelas em que todos os participantes estão livres e, se não houver nenhuma, as janelas com mais participantes, informando quantos poderiam ir (sem dizer quem não pode).

**Cenário: sem janela comum**
- **QUANDO** nenhuma janela reúne todos
- **ENTÃO** a IA usa as melhores janelas parciais ("sábado à noite: 6 de 7 podem") e, se nenhuma reunir pelo menos 2 participantes, propõe ampliar o período

#### RF-14 · Regra de preferência de datas do organizador (Must)

O sistema DEVE permitir que o organizador defina, em ordem de prioridade, critérios para escolher entre várias janelas livres: fim de semana, à noite e mais próxima da data atual (lista extensível, por exemplo feriados ou à tarde). Sem regra definida, vale a mais próxima da data atual.

**Cenário: várias janelas livres**
- **QUANDO** a regra é "fim de semana, depois à noite" e há janelas na quinta às 20h, no sábado às 14h e no sábado às 20h
- **ENTÃO** os planos usam primeiro sábado às 20h, depois sábado às 14h

**Cenário: empate**
- **QUANDO** duas janelas empatam em todos os critérios
- **ENTÃO** vale a mais próxima da data atual

**Cenário: transparência**
- **QUANDO** os planos são apresentados
- **ENTÃO** o grupo vê qual regra de datas foi aplicada

### 4.5 Planos

#### RF-15 · Planos completos com custo por pessoa (Must)

O sistema DEVE propor 2 ou 3 planos para o rolê, cada um com atividade e local (ou evento), data e horário, como cada participante chega e volta, comida, itens para levar quando houver e custo estimado por pessoa (atividade, comida e transporte). Os planos podem ser de qualquer um dos tipos do MVP; o rolê em casa depende do RF-20.

**Cenário: apresentação**
- **QUANDO** a IA apresenta os planos
- **ENTÃO** cada participante vê em destaque o próprio custo e tempo de deslocamento, e o grupo vê a faixa de custo (do menor ao maior)

**Cenário: poucas opções**
- **QUANDO** só 1 plano atende todas as restrições, mesmo depois da negociação de orçamento (RF-18)
- **ENTÃO** a IA apresenta esse plano e explica por que não há outros

#### RF-16 · Fundamentação na base de conhecimento (Must)

O sistema DEVE montar planos só com lugares, eventos, preços e horários da base de conhecimento (RAG) e mostrar, em cada item, a fonte e a data da última verificação.

**Cenário: lugar fora da base**
- **QUANDO** o modelo sugere um lugar que não está na base
- **ENTÃO** o lugar é descartado antes de chegar ao usuário

**Cenário: dado antigo**
- **QUANDO** um preço ou horário foi verificado há mais tempo que o limite (a definir)
- **ENTÃO** ele aparece como "aproximado", com a data da verificação (limites por tipo de dado definidos no [ADR 0004](../decisoes/0004-fonte-e-manutencao-da-base.md#pergunta-3-reverificação-e-aproximado))

#### RF-17 · Filtro de restrições duras (Must)

O sistema DEVE descartar planos que violem o orçamento de algum participante, as janelas de disponibilidade, o horário de funcionamento do lugar ou evento, as restrições declaradas (alimentares, de acessibilidade) ou, quando houver caronas (RF-23), a capacidade dos carros.

**Cenário: lugar fecha antes**
- **QUANDO** o restaurante fecha às 22h e o plano vai até as 23h
- **ENTÃO** o plano é descartado ou tem o horário ajustado

#### RF-18 · Negociação privada de orçamento (Must)

O sistema DEVE, quando o orçamento de algum participante deixar menos de 2 planos viáveis, perguntar em particular a essa pessoa se aceita gastar mais, mostrando quanto a mais e o que ganharia. Se ela recusar ou não responder no prazo, a IA segue automaticamente com os planos dentro do menor orçamento.

**Cenário: aceite**
- **QUANDO** a pessoa aceita o valor maior
- **ENTÃO** o novo limite vale só para esse rolê

**Cenário: silêncio**
- **QUANDO** o prazo acaba sem resposta
- **ENTÃO** a IA segue com os planos de menor orçamento, sem avisar o grupo de que houve uma pergunta

**Cenário: mais de uma pessoa limita**
- **QUANDO** o orçamento de mais de uma pessoa trava as opções
- **ENTÃO** cada uma recebe a pergunta separadamente, sem saber das outras

#### RF-19 · Ranqueamento justo e explicação (Must)

O sistema DEVE ordenar os planos viáveis por um critério de justiça explícito, que protege quem fica pior em custo e tempo de deslocamento (regra a fixar em ADR), e mostrar os prós e contras de cada plano sem expor dados privados.

**Cenário: média engana**
- **QUANDO** o plano A tem deslocamento médio menor, mas obriga um participante a viajar 90 minutos, e o plano B deixa todos com cerca de 40 minutos
- **ENTÃO** B vem antes de A, e a explicação diz por quê

#### RF-20 · Rolê em casa de alguém (Should)

O sistema DEVE, em planos na casa de alguém, usar só a casa de quem se ofereceu como anfitrião na conversa privada, montar a lista de itens e compras com custo estimado e indicar quem leva o quê.

**Cenário: ninguém se oferece**
- **QUANDO** nenhum participante se oferece como anfitrião
- **ENTÃO** a IA não gera planos em casa

#### RF-44 · Preferências de ambiente e informações do local (Should)

O sistema DEVE permitir que cada pessoa informe em particular preferências de ambiente (calmo, pouco ruído, ao ar livre, pouca lotação), usá-las no ranqueamento sem revelar ao grupo de quem vieram, e mostrar em cada plano as informações do local que existirem na base: fotos, faixa de preço, nível de ruído e horários de maior movimento.

**Cenário: preferência sigilosa**
- **QUANDO** a Bia marca "ambiente calmo" e o plano escolhido é um café tranquilo
- **ENTÃO** a explicação ao grupo cita o ambiente calmo como vantagem, sem dizer quem pediu

**Cenário: dado ausente**
- **QUANDO** a base não tem a informação de lotação de um lugar
- **ENTÃO** o plano diz "sem informação", em vez de estimar

### 4.6 Transporte

#### RF-21 · Deslocamento por pessoa (Must)

O sistema DEVE estimar, para cada participante, o tempo e o custo de ida e volta conforme o meio que ele usa (ônibus ou metrô, aplicativo, carro, a pé ou bicicleta), a partir da região de partida informada.

**Cenário: transporte público**
- **QUANDO** o participante vai de ônibus ou metrô
- **ENTÃO** a estimativa usa dados do transporte público do DF (fonte a confirmar) e indica a linha principal

#### RF-22 · Aviso de volta para casa (Should)

O sistema DEVE avisar em particular quem, pelo horário de término do plano, ficaria sem transporte público para voltar, e oferecer alternativas (carona, horário mais cedo, custo do aplicativo).

**Cenário: depois do último ônibus**
- **QUANDO** o plano termina depois do último ônibus de um participante
- **ENTÃO** só ele recebe o aviso com as alternativas e o custo extra estimado, e isso pesa no ranqueamento (RF-19)

#### RF-23 · Caronas otimizadas (Should)

O sistema DEVE, quando há participantes de carro dispostos a dar carona, distribuir os passageiros entre os motoristas com um otimizador (não com o modelo de linguagem), respeitando as vagas e o desvio máximo aceito por cada motorista, e pedir a confirmação dos motoristas.

**Cenário: motorista recusa**
- **QUANDO** um motorista recusa a rota proposta
- **ENTÃO** o otimizador refaz a distribuição sem ele e avisa os passageiros afetados

### 4.7 Decisão

#### RF-24 · Modo de decisão da sala (Must)

O sistema DEVE oferecer dois modos de decisão, escolhidos pelo organizador: votação dos participantes (padrão) ou palavra final do organizador, que vê o ranking e a recomendação da IA.

**Cenário: modo organizador**
- **QUANDO** a sala está no modo palavra final do organizador
- **ENTÃO** os participantes veem os planos e podem comentar, mas a escolha é do organizador, e todos são avisados dela

#### RF-25 · Votação (Must)

O sistema DEVE permitir que cada participante vote em um plano até o prazo. Vence o plano mais votado; em empate, vence o plano mais bem colocado no ranking de justiça. Quem não vota não trava o resultado.

**Cenário: empate**
- **QUANDO** 3 votam no plano A, 3 no plano B, 1 não vota, e B está acima no ranking
- **ENTÃO** B vence, e o resultado informa que o desempate foi pelo ranking

#### RF-26 · Confirmação de presença (Must)

O sistema DEVE pedir que cada participante confirme presença no plano escolhido. Se menos de 2 confirmarem, o rolê é cancelado e a IA oferece reabrir com outra janela.

**Cenário: desistência depois de confirmar**
- **QUANDO** alguém desconfirma depois da decisão
- **ENTÃO** as caronas e as estimativas de custo são recalculadas, e os afetados são avisados

**Cenário: recusa discreta**
- **QUANDO** um participante recusa o convite ou desconfirma
- **ENTÃO** a IA não pede justificativa, e o grupo vê só o número de confirmados

### 4.8 Depois da decisão

#### RF-27 · Compartilhar no WhatsApp (Should)

O sistema DEVE gerar um resumo do plano fechado (o quê, onde, quando, link do mapa e link da sala) para compartilhar no WhatsApp pelo compartilhamento nativo do celular, sem dados privados de ninguém.

**Cenário: compartilhar**
- **QUANDO** um participante toca em "compartilhar"
- **ENTÃO** o resumo abre no WhatsApp pronto para enviar ao grupo

#### RF-28 · Adicionar à agenda (Should)

O sistema DEVE permitir adicionar o rolê confirmado à agenda (Google, Apple ou Android), com data, horário, local e o horário de saída sugerido para aquela pessoa.

**Cenário: exportar**
- **QUANDO** o participante toca em "adicionar à agenda"
- **ENTÃO** o evento é criado na agenda escolhida com o horário de saída dele

#### RF-29 · Lembretes antes do encontro (Should)

O sistema DEVE lembrar cada participante antes do encontro, com horário de saída, como chegar e o que levar.

**Cenário: véspera**
- **QUANDO** falta o tempo de antecedência configurado
- **ENTÃO** cada participante recebe um lembrete com as próprias informações de saída

#### RF-46 · Imprevistos no dia do rolê (Could)

O sistema DEVE, quando um imprevisto afetar um plano já confirmado (chuva em rolê ao ar livre, linha de metrô ou ônibus parada, lugar fechado de última hora), avisar os participantes afetados e propor um ajuste ou um plano alternativo da base de conhecimento, decidido conforme o modo da sala (RF-24). As fontes de previsão do tempo e de alertas de transporte estão em aberto.

**Cenário: chuva no rolê ao ar livre**
- **QUANDO** a previsão indica chuva no horário de um rolê no parque
- **ENTÃO** a IA avisa o grupo e propõe um lugar coberto próximo, com o custo por pessoa recalculado, ou adiar para outra janela

**Cenário: transporte interrompido**
- **QUANDO** a linha que um participante usaria para de funcionar
- **ENTÃO** só ele recebe o aviso, com uma rota ou um meio alternativo e o custo extra estimado

### 4.9 Custos depois do rolê

#### RF-30 · Lançamento de gastos no chat (Must)

O sistema DEVE, ao fim do rolê, perguntar no chat da sala se alguém pagou algo para rachar e aceitar lançamentos de qualquer participante, por texto ou voz ("paguei 180 do bar"), confirmando valor e quem pagou antes de registrar.

**Cenário: lançamento por outra pessoa**
- **QUANDO** a Bia escreve "o Caio pagou 90 do Uber"
- **ENTÃO** a IA pede a confirmação do Caio antes de dividir

**Cenário: nada a rachar**
- **QUANDO** ninguém lança gastos até o prazo
- **ENTÃO** o rolê é encerrado sem divisão

#### RF-31 · Lançamento por foto da nota fiscal (Should)

O sistema DEVE aceitar a foto da nota fiscal como forma de lançar um gasto, extraindo o total (e os itens, quando possível) e pedindo confirmação.

**Cenário: foto ilegível**
- **QUANDO** a IA não consegue ler o total
- **ENTÃO** pede o valor por texto ou voz

#### RF-32 · Divisão dos gastos (Must)

O sistema DEVE dividir cada gasto igualmente entre os participantes presentes, permitindo que quem lançou desmarque quem não participou daquele gasto. Quem confirmou presença e não foi não entra em nenhuma divisão.

**Cenário: alguém fora de um gasto**
- **QUANDO** a conta do bar é de R$ 200 e quem lançou desmarca a Duda
- **ENTÃO** os R$ 200 são divididos só entre os outros presentes

**Cenário: centavos**
- **QUANDO** a divisão não fecha em centavos
- **ENTÃO** a diferença fica com quem pagou, e ninguém paga mais do que a própria parte

#### RF-33 · Código Pix de quem pagou (Should)

O sistema DEVE gerar, para cada devedor, um código Pix copia e cola estático (padrão do Banco Central) com a chave cadastrada por quem pagou e o valor devido, e enviá-lo em particular. O código é gerado por código determinístico, nunca pelo modelo de linguagem.

**Cenário: sem chave cadastrada**
- **QUANDO** quem pagou não tem chave Pix cadastrada
- **ENTÃO** a IA pede a chave em particular e sugere usar uma chave aleatória

**Cenário: conferência**
- **QUANDO** o devedor cola o código no app do banco
- **ENTÃO** o banco mostra o nome de quem recebe e o valor, e o app orienta a conferir antes de pagar

#### RF-34 · Quitação e lembretes discretos (Should)

O sistema DEVE permitir que quem recebeu marque cada dívida como paga e enviar lembretes discretos, só em particular a quem deve, até a quitação, com limite de frequência.

**Cenário: pago**
- **QUANDO** quem recebeu marca a dívida como paga
- **ENTÃO** os lembretes param

#### RF-35 · Saldo entre rolês (Could)

O sistema DEVE manter o saldo de cada membro na sala, somando os rolês, e cobrar pelo Pix só o valor líquido.

**Cenário: compensação**
- **QUANDO** a Ana deve R$ 15 ao Caio e, no rolê seguinte, o Caio passa a dever R$ 20 à Ana
- **ENTÃO** o saldo mostra apenas o Caio devendo R$ 5 à Ana

### 4.10 Avaliação

#### RF-36 · Confirmação de que o encontro aconteceu (Must)

O sistema DEVE perguntar a cada participante, depois do horário previsto, se o encontro aconteceu e se a pessoa foi, com resposta de um toque.

**Cenário: não aconteceu**
- **QUANDO** a maioria responde que o encontro não aconteceu
- **ENTÃO** a IA pergunta o motivo, com opções curtas, para as métricas

#### RF-37 · Avaliação opcional por item (Should)

O sistema DEVE oferecer, de forma opcional, notas de 1 a 5 para lugar, custo, transporte e horário, com comentário livre por texto ou voz, e a pergunta "o lugar estava aberto e o preço bateu?". Uma divergência relatada só põe o lugar na fila de reconferência da base, sem registrar quem respondeu ([ADR 0004](../decisoes/0004-fonte-e-manutencao-da-base.md)).

**Cenário: pessoa pula**
- **QUANDO** a pessoa pula a avaliação
- **ENTÃO** nada mais é pedido sobre aquele rolê

#### RF-38 · Aprendizado com as avaliações (Should)

O sistema DEVE usar as avaliações e escolhas anteriores da sala para ajustar as próximas sugestões e, sem histórico, usar as preferências declaradas nos perfis (partida a frio).

**Cenário: transporte mal avaliado**
- **QUANDO** o grupo avaliou mal o transporte de um lugar distante
- **ENTÃO** lugares com deslocamento parecido descem no ranking daquela sala

### 4.11 Voz e notificações

#### RF-39 · Entrada por voz (Must)

O sistema DEVE aceitar voz em toda conversa com a IA, mostrando a transcrição para confirmação antes de qualquer ação que envolva datas, valores ou confirmação de presença.

**Cenário: transcrição errada**
- **QUANDO** a transcrição sai errada
- **ENTÃO** a pessoa corrige por texto ou fala de novo, e nada é registrado antes da confirmação

#### RF-40 · Resposta em voz (Should)

O sistema DEVE oferecer leitura em voz alta das mensagens da IA, que cada pessoa liga ou desliga.

**Cenário: leitura ligada**
- **QUANDO** a pessoa ativou a leitura em voz alta
- **ENTÃO** as mensagens da IA para ela são lidas automaticamente, e a mensagem continua visível em texto

#### RF-41 · Notificações agrupadas (Must)

O sistema DEVE notificar (push no app instalado ou e-mail) só quando há algo que exige ação ou um lembrete, agrupando pedidos pendentes em uma única notificação.

**Cenário: duas pendências**
- **QUANDO** há disponibilidade e orçamento pendentes no mesmo rolê
- **ENTÃO** a pessoa recebe uma única notificação, que abre as duas perguntas em sequência

### 4.12 Agrupamento para o documento final

Sugestão de 12 capacidades que resumem os Must no pacote de definição:

| Capacidade | RF |
|---|---|
| Contas, login sem senha e salas de 2 a 20 pessoas | RF-01 a RF-04, RF-42 |
| Pedido de rolê e iniciativa da IA | RF-05, RF-06 |
| Coleta privada com prazos | RF-07, RF-08, RF-12 |
| Orçamento sigiloso | RF-11, RF-18 |
| Escolha de datas | RF-13, RF-14 |
| Planos fundamentados em dados reais | RF-15 a RF-17 |
| Ranqueamento justo e deslocamento | RF-19, RF-21 |
| Decisão do grupo e presença | RF-24 a RF-26 |
| Divisão de custos | RF-30, RF-32 |
| Confirmação de que o encontro aconteceu | RF-36 |
| Voz | RF-39 |
| Notificações | RF-41 |

## 5. Requisitos não funcionais

### Resumo

| ID | Requisito | Prioridade | Riscos | Métrica |
|---|---|---|---|---|
| RNF-01 | Privacidade e LGPD | Must | R-01, R-09 | |
| RNF-02 | Sigilo do orçamento e das conversas privadas | Must | R-01, R-02 | |
| RNF-03 | Dados reais | Must | R-03 | |
| RNF-04 | Cálculos fora do modelo de linguagem | Must | R-02, R-03 | |
| RNF-05 | Explicabilidade e transparência | Must | R-03 | |
| RNF-06 | Mínimo de idas ao app | Must | R-04 | |
| RNF-07 | Acessibilidade | Must | R-09 | |
| RNF-08 | Português do Brasil | Must | R-09 | |
| RNF-09 | Web para celular, instalável | Must | | |
| RNF-10 | Registro para métricas | Must | R-06 | |
| RNF-11 | Segurança da aplicação | Must | R-01 | |
| RNF-12 | Arquitetura compatível com o roadmap | Must | R-07 | |
| RNF-13 | Justiça e viés | Must | R-02 | |
| RNF-14 | Desempenho | Should | R-07 | |
| RNF-15 | Resiliência e dependência de APIs | Should | R-07 | |
| RNF-16 | Álcool e segurança no encontro | Should | R-05, R-08 | |

As metas numéricas abaixo são provisórias, valem como intenção para os testes do MVP e serão fixadas junto com as métricas de sucesso.

#### RNF-01 · Privacidade e LGPD (Must)

O sistema DEVE tratar dados pessoais conforme a LGPD: finalidade explícita, consentimento por finalidade (RF-02), minimização e retenção limitada.

**Como verificar**
- Localização só como região, bairro ou referência; agenda só como livre/ocupado.
- Áudio descartado depois da transcrição; foto da nota descartada depois da extração.
- Conversas privadas e orçamentos de um rolê apagados depois de um prazo do fim do rolê (a definir).
- Dados enviados a provedores de LLM e de APIs limitados ao necessário, sem nome nem contato.
- Aviso de privacidade em linguagem simples antes do cadastro.
- Checklist de LGPD revisado antes dos testes do MVP.

#### RNF-02 · Sigilo do orçamento e das conversas privadas (Must)

O sistema DEVE garantir que nenhum membro veja o orçamento ou o conteúdo da conversa privada de outro, nem consiga deduzi-los pelas explicações da IA. Na arquitetura multiagentes, o agente de cada membro só conhece os dados desse membro e repassa ao planejador apenas restrições sem identificação.

**Como verificar**
- Bateria de testes adversariais: perguntar diretamente, pedir "um resumo do que todos disseram", tentar injeção de instrução pelo chat da sala.
- Meta: nenhum vazamento.

#### RNF-03 · Dados reais (Must)

O sistema DEVE apresentar só lugares, eventos, preços e horários que existem, conforme a base de conhecimento.

**Como verificar**
- 100% dos lugares e eventos dos planos existem na base.
- Em amostra conferida à mão, pelo menos 95% dos preços e horários estão corretos.
- A comparação LLM puro × RAG da semana 3 usa a mesma métrica.

#### RNF-04 · Cálculos fora do modelo de linguagem (Must)

O sistema DEVE fazer por código determinístico o cruzamento de janelas, os filtros de restrição, as estimativas de custo, a divisão, os saldos, os códigos Pix e as caronas (otimizador). O modelo de linguagem conversa, interpreta, orquestra e explica.

**Como verificar**
- Testes automatizados nos módulos de cálculo.
- Nenhum valor em reais nem chave Pix vem de texto gerado pelo modelo.

#### RNF-05 · Explicabilidade e transparência (Must)

O sistema DEVE mostrar, em cada plano, por que ele foi sugerido (restrições atendidas, regra de datas, critério de justiça, prós e contras), marcar estimativas como estimativas e deixar claro que quem conversa é uma IA.

**Como verificar**
- Em teste com usuários, a maioria sabe dizer por que o plano escolhido ficou em primeiro (percentual a definir).

#### RNF-06 · Mínimo de idas ao app (Must)

O sistema DEVE permitir fechar um rolê com poucas interações obrigatórias por participante, com prazo e ação padrão em toda pergunta que trava o rolê (RF-12) e notificações agrupadas (RF-41).

**Como verificar**
- Meta provisória: no máximo 3 interações obrigatórias por participante (respostas na conversa privada, voto, presença), medidas nos registros dos testes do MVP (RNF-10).

#### RNF-07 · Acessibilidade (Must)

O sistema DEVE ser utilizável por adultos de qualquer idade, inclusive pessoas com pouca experiência ou fluência com tecnologia: WCAG 2.1 nível AA, fonte ajustável, alvos de toque grandes, linguagem simples, e tudo que se faz por voz também se faz por texto, e vice-versa.

**Como verificar**
- Verificador automático de acessibilidade sem erros críticos.
- Teste de uso com pelo menos uma pessoa com pouca fluência digital, no perfil da persona Márcio.

#### RNF-08 · Português do Brasil (Must)

O sistema DEVE usar pt-BR em interface, conversa e voz, com datas em dd/mm, horário de 24 horas e valores em R$, e entender expressões comuns ("rolê", "bora", "rachar").

**Como verificar**
- Conjunto de frases de teste de disponibilidade e de gastos interpretadas corretamente em pelo menos 90% dos casos.

#### RNF-09 · Web para celular, instalável (Must)

O sistema DEVE funcionar como app web responsivo e instalável (PWA), nas duas versões mais recentes do Chrome no Android e do Safari no iOS, e continuar utilizável no computador.

**Como verificar**
- Roteiro de teste manual nesses navegadores antes dos testes do MVP.

#### RNF-10 · Registro para métricas (Must)

O sistema DEVE registrar eventos pseudonimizados do ciclo do rolê (pedido, respostas, planos gerados, escolha, confirmações, se aconteceu, avaliação, gastos lançados e quitados), com o tempo entre etapas e o número de interações, sem o conteúdo das conversas privadas nem valores de orçamento.

**Como verificar**
- Todas as métricas de sucesso do pacote podem ser calculadas só a partir desses registros.

#### RNF-11 · Segurança da aplicação (Must)

O sistema DEVE exigir autenticação, usar HTTPS, limitar cada sala aos seus membros, criptografar em repouso a chave Pix e os dados sensíveis, manter segredos fora do git e resistir a injeção de instrução: texto de usuários e de fontes externas não muda as regras da IA.

**Como verificar**
- Checklist básico do OWASP Top 10.
- Testes de acesso a salas de outras pessoas.

#### RNF-12 · Arquitetura compatível com o roadmap (Must)

O sistema DEVE separar a base de conhecimento (RAG, semana 2), os agentes (um por membro, mais planejador, logística, finanças e mediador, semana 4), as entradas multimodais (voz e foto, semana 5) e a interface, com provedores de LLM, voz e mapas trocáveis por configuração.

**Como verificar**
- Cada entrega semanal roda sobre a anterior, sem reescrevê-la.

#### RNF-13 · Justiça e viés (Must)

O sistema DEVE usar uma regra de ranqueamento documentada em ADR que não favoreça sistematicamente quem mora em regiões centrais ou tem mais dinheiro.

**Como verificar**
- Em cenários de teste com membros espalhados pelo DF, comparar a regra adotada com a média simples: diferença entre o maior e o menor tempo de deslocamento e maior custo individual (meta a definir).

#### RNF-14 · Desempenho (Should)

O sistema DEVE responder na conversa em até 5 segundos (p90) e gerar os planos em até 60 segundos depois da última resposta necessária, mostrando o progresso, em salas de até 20 membros.

**Como verificar**
- Tempos medidos nos registros dos testes do MVP, com salas de 20 membros simulados.

#### RNF-15 · Resiliência e dependência de APIs (Should)

O sistema DEVE preservar o estado do rolê quando o LLM, os mapas ou a voz falharem, tentar de novo e avisar com mensagem clara, e guardar em cache as respostas de APIs externas só quando os termos do provedor permitem (da Google Places, por exemplo, só o place ID; ver [ADR 0004](../decisoes/0004-fonte-e-manutencao-da-base.md)). O consumo é registrado, e os testes do MVP devem caber nos créditos gratuitos de API de cada membro; pagar por APIs fica só como possibilidade (premissa P12).

**Como verificar**
- Testes com cada API externa desligada.

#### RNF-16 · Álcool e segurança no encontro (Should)

O sistema DEVE evitar incentivar o consumo de álcool, incluir uma opção sem foco em bebida alcoólica sempre que houver uma viável e, em planos com bebida, lembrar de combinar a volta sem ninguém dirigir depois de beber.

**Como verificar**
- Revisão de uma amostra de planos gerados em cenários de teste.

## 6. Questões em aberto

1. **Prazos de resposta:** valores para disponibilidade, orçamento, voto, presença e lançamento de gastos (RF-12, RF-18, RF-25, RF-30).
2. **Iniciativa da IA:** período padrão sem encontro e limite de frequência (RF-06).
3. **Regra de justiça do ranqueamento:** "menor miséria" é a proposta; precisa de ADR (RF-19, RNF-13).
4. ~~**Fonte de lugares, eventos e preços.**~~ Decidida nos ADRs [0004](../decisoes/0004-fonte-e-manutencao-da-base.md) e [0005](../decisoes/0005-coleta-automatica-e-base-vetorial.md) (proposta): candidatos da Overture, extração automática dos sites oficiais com evidência literal, Google Places só para conferir os finalistas, limites de "aproximado" por tipo de dado e base vetorial em PostgreSQL com pgvector (RF-16, RNF-03).
5. **Visibilidade de votos e dívidas:** sugestão de contagem de votos visível com voto individual secreto, e de cada devedor ver só o próprio valor enquanto quem pagou vê quem já pagou (RF-25, RF-34).
6. **Caronas:** escolhidas para o MVP, mas marcadas como Should porque dependem de um otimizador de rotas. Confirmar a prioridade (RF-23).
7. **Rolê em casa:** como dividir compras feitas antes do encontro por quem é anfitrião (RF-20, RF-32).
8. **Transporte público do DF:** confirmar se os dados abertos (GTFS) estão disponíveis e atualizados (RF-21, RF-22).
9. **Imprevistos:** fontes de previsão do tempo e de alertas de transporte do DF (RF-46).

## 7. Extensões futuras

Fora do MVP ([ADR 0002](../decisoes/0002-recorte-do-mvp.md)). Os requisitos destas extensões podem ser escritos depois dos do MVP.

- **Modo Descoberta:** grupos novos entre desconhecidos compatíveis. Exige verificação de identidade, moderação e regras de segurança.
- **Videogames e plano B online:** jogos que o grupo já tem e Remote Play Together da Steam, sem substituir o encontro presencial.
- **Versão para menores de idade:** responsáveis participam da aprovação dos planos, com filtros como nada de bares, horário limite e deslocamento acompanhado. Exige atender ao art. 14 da LGPD (dados de crianças e adolescentes).
- **Pix com confirmação automática:** Pix Cobrança pela API de um banco ou intermediador de pagamento, no lugar do Pix estático com quitação manual.
- **Outros canais:** bot no WhatsApp ou no Telegram, além do app web.

## 8. Premissas assumidas aqui

A consolidar no item Premissas do pacote de definição.

- Os membros de uma sala já se conhecem.
- Os usuários têm celular com navegador atualizado e internet.
- O canal é um app web próprio ([ADR 0003](../decisoes/0003-canal-app-web.md), proposta).
- Os dados de lugares do DF vêm de uma base curada pelo grupo, conferida por API.
- Os testes do MVP cabem nos créditos gratuitos de API fornecidos a cada membro; pagar por APIs fica só como possibilidade (P12).

## Riscos referenciados

IDs da guia Riscos do documento da equipe, usados nas colunas Riscos acima.

| ID | Risco | P × I |
|---|---|---|
| R-01 | Privacidade e vazamento de dados | Média × Alta |
| R-02 | Exclusão financeira e constrangimento social | Média × Alta |
| R-03 | Dados inventados e alucinação | Alta × Alta |
| R-04 | Inércia do grupo e "amigo gargalo" | Alta × Alta |
| R-05 | Segurança no deslocamento e mobilidade urbana | Média × Alta |
| R-06 | Métricas de vaidade | Média × Média |
| R-07 | Dependência e limites de APIs externas | Alta × Média |
| R-08 | Incentivo ao consumo de álcool e direção | Baixa × Alta |
| R-09 | Tratamento de voz e fotos de notas fiscais | Média × Média |

## Histórico

| Versão | Data | Mudança |
|---|---|---|
| 0.1 | 2026-10-29 | Versão inicial: 41 RF e 16 RNF do MVP |
| 0.2 | 2026-10-29 | RF-42 a RF-45 vindos das personas, coluna Persona preenchida, prazos ajustáveis pelo organizador (RF-12) e recusa discreta (RF-26) |
| 0.3 | 2026-10-29 | RF-46 (imprevistos, Could); coluna Riscos com os IDs R-NN da guia Riscos; consistência com as outras guias: sala de 2 a 20, adultos 18+, créditos gratuitos de API, testes do MVP sem piloto, itens Should marcados no escopo, ajustes no glossário e nos RF-02, 03, 04, 12, 15, 17 e 25. Trazida do documento da equipe para o repositório em 2026-11-03 |
| 0.3.1 | 2026-11-03 | Consequências do ADR 0004: RNF-15 com cache só do que os termos permitem; RF-37 com a pergunta opcional sobre lugar aberto e preço; questão em aberto 4 fechada |
