# Requisitos do MVP: Orquestrador de Rolês

- **Versão:** 0.1 (rascunho inicial), 2026-10-29
- **Status:** para revisão do grupo. As escolhas de comportamento foram feitas na sessão de requisitos de 29/10 e ainda precisam ser validadas com o grupo, as personas e o resultado do formulário.
- **Base:** [visão do produto](visao.md) · recorte do MVP no [ADR 0002](../decisoes/0002-recorte-do-mvp.md) · canal no [ADR 0003](../decisoes/0003-canal-app-web.md)

## Como ler

- **IDs fixos.** RF-NN são funcionais e RNF-NN são não funcionais. Um ID nunca é reaproveitado: requisito que sai fica marcado como *removido*.
- **Prioridade provisória (MoSCoW):** **Must** (sem isso o MVP não resolve o problema), **Should** (importante, entra se couber nas 7 semanas), **Could** (desejável). O que está fora do MVP fica em [Extensões futuras](#7-extensões-futuras).
- **Notação (estilo OpenSpec):** cada requisito tem um enunciado com **DEVE** e cenários **QUANDO / ENTÃO**, que servem de critério de aceitação e, depois, de casos de teste.
- **Rastreabilidade:** as colunas Persona e Métrica ficam em branco até essas partes do pacote ficarem prontas. A coluna Riscos usa os nomes dos riscos da [visão](visao.md#riscos-conhecidos) até eles ganharem IDs (R-NN).
- **Documento final:** entra só o que é Must, agrupado por capacidade (ver [seção 4.12](#412-agrupamento-para-o-documento-final)). Esta lista completa fica no repositório.

## 1. Escopo do MVP

**Dentro**

- Organização de rolês entre amigos que já se conhecem, em salas de 2 a 20 pessoas.
- App web, pensado primeiro para o celular, com exportação do plano fechado para o WhatsApp e para a agenda.
- Distrito Federal inteiro; adultos (18+) de qualquer idade.
- Quatro tipos de rolê: comer e beber fora, eventos com data marcada, ao ar livre ou gratuitos, em casa de alguém.
- Conversa por texto e por voz.

**Fora** (ver [Extensões futuras](#7-extensões-futuras))

- Modo Descoberta, videogames e plano B online, versão para menores de idade.

## 2. Glossário

| Termo | Significado |
|---|---|
| Sala | Grupo fixo de amigos no app (2 a 20 membros), com um chat do grupo |
| Organizador | Quem criou a sala, com papel transferível. Configura o modo de decisão, a regra de preferência de datas e a iniciativa da IA |
| Rolê | Um encontro em organização dentro de uma sala, do pedido até a avaliação |
| Participante | Membro da sala convidado para um rolê específico |
| Conversa privada | Chat individual entre um participante e a IA. O que é dito ali não aparece para os outros |
| Plano | Proposta completa de rolê: o quê, onde, quando, como cada um chega e volta, e custo estimado por pessoa |
| Restrição dura | Condição que elimina um plano: orçamento, disponibilidade, horário de funcionamento, restrições declaradas |
| Janela | Intervalo de data e hora em que os participantes estão livres |
| Prazo de resposta | Tempo que a IA espera por uma resposta antes de seguir com uma ação padrão (valores em aberto) |
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

| ID | Requisito | Prioridade | Riscos (visão) | Persona | Métrica |
|---|---|---|---|---|---|
| RF-01 | Cadastro e perfil | Must | Privacidade | | |
| RF-02 | Consentimento e controle dos dados | Must | Privacidade | | |
| RF-03 | Sala e convites (2 a 20 membros) | Must | | | |
| RF-04 | Gestão da sala pelo organizador | Must | | | |
| RF-05 | Pedido de rolê por qualquer membro | Must | | | |
| RF-06 | Iniciativa da IA | Must | | | |
| RF-07 | Conversa privada com cada participante | Must | Privacidade | | |
| RF-08 | Disponibilidade por conversa livre | Must | | | |
| RF-09 | Disponibilidade por grade de horários | Should | | | |
| RF-10 | Disponibilidade pelo Google Agenda | Could | Privacidade | | |
| RF-11 | Orçamento sigiloso | Must | Privacidade, Exclusão financeira | | |
| RF-12 | Prazo de resposta e ação padrão | Must | | | |
| RF-13 | Cruzamento de disponibilidades | Must | | | |
| RF-14 | Regra de preferência de datas do organizador | Must | | | |
| RF-15 | Planos completos com custo por pessoa | Must | Dados inventados | | |
| RF-16 | Fundamentação na base de conhecimento | Must | Dados inventados | | |
| RF-17 | Filtro de restrições duras | Must | Exclusão financeira | | |
| RF-18 | Negociação privada de orçamento | Must | Exclusão financeira | | |
| RF-19 | Ranqueamento justo e explicação | Must | Exclusão financeira | | |
| RF-20 | Rolê em casa de alguém | Should | | | |
| RF-21 | Deslocamento por pessoa | Must | | | |
| RF-22 | Aviso de volta para casa | Should | Segurança | | |
| RF-23 | Caronas otimizadas | Should | Segurança | | |
| RF-24 | Modo de decisão da sala | Must | | | |
| RF-25 | Votação | Must | | | |
| RF-26 | Confirmação de presença | Must | | | |
| RF-27 | Compartilhar no WhatsApp | Should | Privacidade | | |
| RF-28 | Adicionar à agenda | Should | | | |
| RF-29 | Lembretes antes do encontro | Should | | | |
| RF-30 | Lançamento de gastos no chat | Must | | | |
| RF-31 | Lançamento por foto da nota fiscal | Should | | | |
| RF-32 | Divisão dos gastos | Must | Exclusão financeira | | |
| RF-33 | Código Pix de quem pagou | Should | Privacidade | | |
| RF-34 | Quitação e lembretes discretos | Should | Exclusão financeira | | |
| RF-35 | Saldo entre rolês | Could | | | |
| RF-36 | Confirmação de que o encontro aconteceu | Must | Métricas de vaidade | | |
| RF-37 | Avaliação opcional por item | Should | | | |
| RF-38 | Aprendizado com as avaliações | Should | | | |
| RF-39 | Entrada por voz | Must | | | |
| RF-40 | Resposta em voz | Should | | | |
| RF-41 | Notificações agrupadas | Must | | | |

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

O sistema DEVE pedir consentimento separado para cada finalidade sensível (localização, agenda, voz, chave Pix) e permitir que a pessoa veja, corrija, exporte e apague os próprios dados e a conta.

**Cenário: revogação**
- **QUANDO** a pessoa desconecta a agenda
- **ENTÃO** a conexão é removida e os horários importados são apagados

**Cenário: exclusão da conta**
- **QUANDO** a pessoa pede para apagar a conta
- **ENTÃO** o app avisa se há saldos em aberto e, depois da confirmação, remove os dados pessoais; nos rolês passados ela aparece como "ex-membro"

#### RF-03 · Sala e convites (Must)

O sistema DEVE permitir que qualquer usuário crie uma sala, da qual passa a ser o organizador, e convide amigos por um link compartilhável. Uma sala tem no mínimo 2 e no máximo 20 membros.

**Cenário: sala cheia**
- **QUANDO** uma 21ª pessoa abre o link de convite
- **ENTÃO** a entrada é recusada com uma explicação, e o organizador é avisado

**Cenário: sala com uma pessoa só**
- **QUANDO** a sala tem só 1 membro
- **ENTÃO** não é possível iniciar um rolê, e o app sugere convidar alguém

#### RF-04 · Gestão da sala (Must)

O sistema DEVE permitir que o organizador transfira o papel para outro membro, remova membros e configure a sala: modo de decisão (RF-24), regra de preferência de datas (RF-14) e iniciativa da IA (RF-06). Qualquer membro pode sair da sala.

**Cenário: organizador sai**
- **QUANDO** o organizador tenta sair sem transferir o papel
- **ENTÃO** o app pede que ele escolha um sucessor; se ele não escolher, o papel passa ao membro mais antigo

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

#### RF-11 · Orçamento sigiloso (Must)

O sistema DEVE coletar em particular quanto cada participante quer gastar no rolê, transporte incluído, e usar esse valor só como restrição. O valor individual nunca é mostrado a outro membro nem atribuído a alguém nas explicações.

**Cenário: plano descartado por custo**
- **QUANDO** um plano é descartado por orçamento
- **ENTÃO** a explicação ao grupo diz "fora do orçamento do grupo", nunca "fora do orçamento da Ana"

**Cenário: sem resposta**
- **QUANDO** o participante não informa o orçamento até o prazo
- **ENTÃO** a IA usa o orçamento padrão do perfil ou, se não houver, o menor orçamento informado no grupo

#### RF-12 · Prazo de resposta e ação padrão (Must)

O sistema DEVE associar a cada pergunta que trava o rolê (disponibilidade, orçamento, voto, presença) um prazo e uma ação padrão, para que o rolê avance sem depender de todos e sem que a pessoa precise voltar ao app várias vezes. Os valores dos prazos estão em aberto.

**Cenário: participante não responde**
- **QUANDO** um participante não informa a disponibilidade até o prazo
- **ENTÃO** a IA segue com quem respondeu e avisa essa pessoa de que ela ainda pode entrar até a votação

**Cenário: lembrete único**
- **QUANDO** o prazo está perto do fim
- **ENTÃO** a IA manda um único lembrete

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

O sistema DEVE propor 2 ou 3 planos para o rolê, cada um com atividade e local (ou evento), data e horário, como cada participante chega e volta, comida, itens para levar quando houver e custo estimado por pessoa (atividade, comida e transporte). Os planos podem ser de qualquer um dos quatro tipos do MVP.

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
- **ENTÃO** ele aparece como "aproximado", com a data da verificação

#### RF-17 · Filtro de restrições duras (Must)

O sistema DEVE descartar planos que violem o orçamento de algum participante, as janelas de disponibilidade, o horário de funcionamento do lugar ou evento, as restrições declaradas (alimentares, de acessibilidade) ou a capacidade das caronas.

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

O sistema DEVE permitir que cada participante vote em um plano até o prazo. Vence a maioria simples; em empate, vence o plano mais bem colocado no ranking de justiça. Quem não vota não trava o resultado.

**Cenário: empate**
- **QUANDO** 3 votam no plano A, 3 no plano B, 1 não vota, e B está acima no ranking
- **ENTÃO** B vence, e o resultado informa que o desempate foi pelo ranking

#### RF-26 · Confirmação de presença (Must)

O sistema DEVE pedir que cada participante confirme presença no plano escolhido. Se menos de 2 confirmarem, o rolê é cancelado e a IA oferece reabrir com outra janela.

**Cenário: desistência depois de confirmar**
- **QUANDO** alguém desconfirma depois da decisão
- **ENTÃO** as caronas e as estimativas de custo são recalculadas, e os afetados são avisados

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

O sistema DEVE oferecer, de forma opcional, notas de 1 a 5 para lugar, custo, transporte e horário, com comentário livre por texto ou voz.

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
| Contas e salas de 2 a 20 pessoas | RF-01 a RF-04 |
| Pedido de rolê e iniciativa da IA | RF-05, RF-06 |
| Coleta privada com prazos | RF-07, RF-08, RF-12 |
| Orçamento sigiloso | RF-11, RF-18 |
| Escolha de datas | RF-13, RF-14 |
| Planos fundamentados em dados reais | RF-15 a RF-17 |
| Decisão justa e deslocamento | RF-19, RF-21 |
| Decisão do grupo e presença | RF-24 a RF-26 |
| Divisão de custos | RF-30, RF-32 |
| Confirmação de que o encontro aconteceu | RF-36 |
| Voz | RF-39 |
| Notificações | RF-41 |

## 5. Requisitos não funcionais

### Resumo

| ID | Requisito | Prioridade | Riscos (visão) | Métrica |
|---|---|---|---|---|
| RNF-01 | Privacidade e LGPD | Must | Privacidade | |
| RNF-02 | Sigilo do orçamento e das conversas privadas | Must | Privacidade, Exclusão financeira | |
| RNF-03 | Dados reais | Must | Dados inventados | |
| RNF-04 | Cálculos fora do modelo de linguagem | Must | Dados inventados, Exclusão financeira | |
| RNF-05 | Explicabilidade e transparência | Must | | |
| RNF-06 | Mínimo de idas ao app | Must | | |
| RNF-07 | Acessibilidade | Must | | |
| RNF-08 | Português do Brasil | Must | | |
| RNF-09 | Web para celular, instalável | Must | | |
| RNF-10 | Registro para métricas | Must | Métricas de vaidade | |
| RNF-11 | Segurança da aplicação | Must | Privacidade, Segurança | |
| RNF-12 | Arquitetura compatível com o roadmap | Must | | |
| RNF-13 | Justiça e viés | Must | Exclusão financeira | |
| RNF-14 | Desempenho | Should | | |
| RNF-15 | Resiliência e dependência de APIs | Should | Dependência de APIs | |
| RNF-16 | Álcool e segurança no encontro | Should | Álcool, Segurança | |

As metas numéricas abaixo são provisórias e serão fixadas junto com as métricas de sucesso.

#### RNF-01 · Privacidade e LGPD (Must)

O sistema DEVE tratar dados pessoais conforme a LGPD: finalidade explícita, consentimento por finalidade (RF-02), minimização e retenção limitada.

**Como verificar**
- Localização só como região, bairro ou referência; agenda só como livre/ocupado.
- Áudio descartado depois da transcrição; foto da nota descartada depois da extração.
- Conversas privadas e orçamentos de um rolê apagados depois de um prazo do fim do rolê (a definir).
- Dados enviados a provedores de LLM e de APIs limitados ao necessário, sem nome nem contato.
- Aviso de privacidade em linguagem simples antes do cadastro.
- Checklist de LGPD revisado antes do piloto.

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
- Meta provisória: no máximo 3 interações obrigatórias por participante (respostas na conversa privada, voto, presença), medidas nos registros do piloto (RNF-10).

#### RNF-07 · Acessibilidade (Must)

O sistema DEVE ser utilizável por adultos de qualquer idade, inclusive pessoas mais velhas e com pouca experiência em apps: WCAG 2.1 nível AA, fonte ajustável, alvos de toque grandes, linguagem simples, e tudo que se faz por voz também se faz por texto, e vice-versa.

**Como verificar**
- Verificador automático de acessibilidade sem erros críticos.
- Teste de uso com pelo menos uma pessoa do perfil da persona mais velha.

#### RNF-08 · Português do Brasil (Must)

O sistema DEVE usar pt-BR em interface, conversa e voz, com datas em dd/mm, horário de 24 horas e valores em R$, e entender expressões comuns ("rolê", "bora", "rachar").

**Como verificar**
- Conjunto de frases de teste de disponibilidade e de gastos interpretadas corretamente em pelo menos 90% dos casos.

#### RNF-09 · Web para celular, instalável (Must)

O sistema DEVE funcionar como app web responsivo e instalável (PWA), nas duas versões mais recentes do Chrome no Android e do Safari no iOS, e continuar utilizável no computador.

**Como verificar**
- Roteiro de teste manual nesses navegadores antes do piloto.

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
- Tempos medidos nos registros do piloto e em testes com salas de 20 membros simulados.

#### RNF-15 · Resiliência e dependência de APIs (Should)

O sistema DEVE preservar o estado do rolê quando o LLM, os mapas ou a voz falharem, tentar de novo e avisar com mensagem clara, e guardar em cache as respostas de APIs externas. O custo das APIs não é restrição por enquanto, mas o consumo é registrado.

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
4. **Fonte de lugares, eventos e preços:** combinado em 29/10 usar uma base curada pelo grupo, indexada no RAG, mais uma API para conferir se o lugar existe e está aberto. Detalhar em ADR na semana 2 (RF-16, RNF-03).
5. **Visibilidade de votos e dívidas:** sugestão de contagem de votos visível com voto individual secreto, e de cada devedor ver só o próprio valor enquanto quem pagou vê quem já pagou (RF-25, RF-34).
6. **Caronas:** escolhidas para o MVP, mas marcadas como Should porque dependem de um otimizador de rotas. Confirmar a prioridade (RF-23).
7. **Rolê em casa:** como dividir compras feitas antes do encontro por quem é anfitrião (RF-20, RF-32).
8. **Transporte público do DF:** confirmar se os dados abertos (GTFS) estão disponíveis e atualizados (RF-21, RF-22).

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
- O orçamento para APIs pagas não restringe o MVP por enquanto.

## Histórico

| Versão | Data | Mudança |
|---|---|---|
| 0.1 | 2026-10-29 | Versão inicial: 41 RF e 16 RNF do MVP |
