# Questionário de validação: encontros entre amigos

- **Status:** rascunho v0.3 (2026-10-27): a maioria das perguntas em escala de 5 pontos; ainda não pilotado
- **Geração automática:** [gerar_formulario.gs](gerar_formulario.gs) cria este questionário no Google Forms. Ao mudar uma pergunta aqui, mude lá também.
- **Objetivo:** validar a dor por trás da proposta (dificuldade de combinar encontros entre amigos) com dados do nosso próprio público, antes de falar da solução
- **Público:** estudantes e residentes, 18 anos ou mais
- **Duração estimada:** 10 a 12 minutos (medir no piloto)
- **Formato:** Google Forms, anônimo, sem coleta de e-mail

## Escalas

| Código | Uso | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|---|
| **C** | Concordância (percepções e atitudes) | Discordo totalmente | Discordo | Neutro | Concordo | Concordo totalmente |
| **F** | Frequência nos últimos 3 meses (comportamentos) | Nunca | Raramente | Às vezes | Frequentemente | Muito frequentemente |
| **T** | Trabalho que uma tarefa dá | Nenhum | Pouco | Moderado | Bastante | Muito |
| **U** | Utilidade de uma funcionalidade | Nada útil | Pouco útil | Moderadamente útil | Muito útil | Extremamente útil |

Nas grades de concordância, incluir também a coluna **"Não se aplica"**, para que o "Neutro" não seja usado por quem não tem como responder.

## Princípios de redação

1. **Uma ideia por afirmação.** Nada de "gosto e me sinto mais feliz" na mesma frase, nem intensificadores ("muito", "sempre") dentro da afirmação: a intensidade fica na escala.
2. **Afirmações invertidas.** Em cada grade, parte das afirmações aponta no sentido contrário da dor investigada. Elas estão marcadas com **(R)** aqui (a marca não aparece no formulário). Isso reduz a tendência de concordar com tudo e permite detectar respostas automáticas.
3. **Comportamento usa a escala F, percepção usa a escala C.** O que aconteceu é perguntado como frequência nos últimos 3 meses. Opiniões e sentimentos, como concordância.
4. **Temas sensíveis normalizados.** Dinheiro e vergonha são sub-relatados, então as perguntas descrevem comportamentos e trazem frases de normalização.
5. **A ideia só aparece no fim.** O bloco 10 é o único que descreve a solução.
6. **Dois lados do convite.** Pares de afirmações comparam quem convida e quem é convidado: **P1** (4.2f ↔ 5.2a) e **P2** (5.2e ↔ 5.2f).

## O que não está em escala de 5 pontos, e por quê

- **Perfil (bloco 1):** são categorias, não intensidades.
- **2.1 e 2.2 (frequência real e desejada):** a diferença entre as duas é a própria definição de solidão da OMS, e faixas concretas ("2 a 3 vezes por mês") são mais precisas que "às vezes".
- **Listas de motivos e de canais (1.2, 3.3, 3.5, 7.2, 8.2):** a pessoa precisa escolher entre opções diferentes, não graduar uma.
- **Gasto (5.4), tempo de deslocamento (6.1) e número de amigos novos (8.1):** valores concretos rendem frases mais fortes no relatório ("a média de gasto por encontro foi...").
- **Escala de solidão (bloco 9):** é um instrumento validado com 3 pontos de resposta. Alterá-la invalida a comparação com outros estudos.
- **Perguntas abertas (10.1, 10.3).**

## Configuração no Google Forms

- Afirmações agrupadas usam **"Grade de múltipla escolha"**: linhas = afirmações, colunas = os 5 pontos com rótulo em todos. A "Escala linear" do Forms só rotula as pontas, então fica reservada às perguntas isoladas de 1 a 5 (5.3 e 9.4).
- Nas grades (exceto no bloco 9), ativar **"Embaralhar ordem das linhas"** e não exigir resposta em todas as linhas. O script não consegue ativar o embaralhamento, porque o Apps Script não oferece essa opção: é preciso ligar à mão em cada grade e na pergunta 3.3 ("Embaralhar ordem das opções").
- Perguntas usadas para desvio de seção (3.1, 4.0, 7.1, 8.1) precisam ser do tipo **"Múltipla escolha"** com os rótulos da escala, porque o desvio por resposta só funciona nesse tipo.
- Uma seção por bloco. Não ativar "Coletar e-mails".
- Pilotar com 5 pessoas antes de divulgar: cronometrar, perguntar o que ficou confuso e ajustar.

---

## Texto de abertura

> Esta pesquisa faz parte de um projeto acadêmico e busca entender como grupos de amigos combinam encontros e o que atrapalha. Leva cerca de 10 minutos.
>
> As respostas são anônimas: não pedimos nome, e-mail nem dados que identifiquem você, e os resultados serão apresentados apenas de forma agregada. Você pode pular perguntas ou parar a qualquer momento.
>
> Ao continuar, você declara ter 18 anos ou mais e concorda em participar.

> **Definições usadas no questionário**
> - **Amigos:** pessoas que você considera amigas. Não conte familiares nem parceiro(a).
> - **Encontro:** qualquer momento combinado para estar com amigos fora de aula ou trabalho (bar, churrasco, cinema, ir à casa de alguém, etc.). Quando a pergunta tratar de encontros online, isso estará escrito.

---

## Bloco 1: Perfil

**1.1** Qual a sua idade?
18–21 · 22–25 · 26–30 · 31–40 · 41 ou mais

**1.2** Como você costuma se deslocar para encontros com amigos? (marque todas que se aplicam)
Carro próprio · Carona · Transporte por aplicativo · Ônibus ou metrô · A pé ou bicicleta · Outro

**1.3** Quantas pessoas você considera amigos próximos?
Nenhuma · 1 · 2 a 3 · 4 a 5 · 6 a 9 · 10 ou mais

## Bloco 2: Frequência e bem-estar

**2.1** Nos últimos 3 meses, com que frequência você se encontrou **pessoalmente** com amigos?
Nenhuma vez · Menos de uma vez por mês · Cerca de uma vez por mês · 2 a 3 vezes por mês · Cerca de uma vez por semana · Mais de uma vez por semana

**2.2** Com que frequência você **gostaria** de se encontrar pessoalmente com amigos?
(mesmas opções da 2.1)

**2.3** Nos últimos 3 meses, com que frequência você fez atividades **online** com amigos (jogar, assistir algo junto, chamada de vídeo em grupo)? (F)

**2.4** Indique o quanto você concorda com cada afirmação. (C)
- a. Encontro meus amigos pessoalmente com a frequência que eu gostaria. (R)
- b. Tenho amigos de quem gosto, mas com quem quase não me encontro mais.
- c. Depois de um encontro com amigos, costumo me sentir melhor do que antes.
- d. Passar tempo com amigos faz pouca diferença no meu humor. (R)
- e. Minhas amizades continuam próximas mesmo quando passamos meses sem nos ver. (R)

## Bloco 3: Encontros que não aconteceram

**3.1** Nos últimos 3 meses, com que frequência um encontro sugerido no seu grupo de amigos (por você ou por outra pessoa) acabou não acontecendo? (F, como múltipla escolha)
Nunca → [ir para a 3.4] · Raramente · Às vezes · Frequentemente · Muito frequentemente

**3.2** Nos últimos 3 meses, com que frequência um encontro deixou de acontecer... (F)
- a. porque não achamos um dia e horário em que todos pudessem
- b. porque ninguém tomou a frente para organizar
- c. porque não chegamos a um acordo sobre o que fazer ou aonde ir
- d. por causa do custo para alguém
- e. por causa de distância ou transporte
- f. porque pessoas desistiram em cima da hora
- g. porque a conversa esfriou e as pessoas pararam de responder

**3.3** Entre esses motivos, qual mais atrapalha os encontros do seu grupo? (escolha um; mesmas opções da 3.2, mais "Outro: ___")

**3.4** Indique o quanto você concorda com cada afirmação. (C)
- a. No meu grupo, quase sempre as mesmas pessoas propõem os encontros.
- b. Combinar um encontro no grupo de mensagens costuma ser rápido e fácil. (R)
- c. Quando surgem muitas sugestões diferentes, o grupo tem dificuldade para decidir.

**3.5** Como o seu grupo costuma combinar encontros? (marque todas que se aplicam)
Grupo de WhatsApp ou Telegram · Mensagens individuais · Enquete · Aplicativo de agenda ou de eventos · Pessoalmente · Outro

## Bloco 4: Quando você propõe ou organiza

**4.0** Nos últimos 3 meses, você propôs ou organizou algum encontro com amigos?
Sim · Não, mas pensei em propor · Não, nem pensei nisso → [ir para o bloco 5]

**4.1** Nos últimos 3 meses, com que frequência você pensou em propor um encontro e acabou não propondo? (F)

**4.2** Indique o quanto você concorda com cada afirmação. (C)
- a. Quando penso em propor um encontro, fico em dúvida se os outros vão ter interesse.
- b. Evito perguntar a disponibilidade dos meus amigos para não incomodar.
- c. Fico à vontade para chamar amigos para um encontro. (R)
- d. Evito sugerir programas que tenham custo para os outros.
- e. Organizar um encontro me dá mais trabalho do que eu gostaria.
- f. Se eu convidasse um amigo com quem não falo há alguns meses, ele ficaria feliz com o convite. **[P1]**

**4.3** Organizar um encontro envolve várias tarefas. Quanto trabalho cada uma costuma dar a você? (T, mais a coluna "Não faço essa tarefa")
- a. Descobrir quando as pessoas estão livres
- b. Escolher o que fazer ou o lugar
- c. Pesquisar preços, horários e avaliações
- d. Resolver transporte e caronas
- e. Dividir os custos e cobrar as pessoas
- f. Lembrar as pessoas e confirmar presença

## Bloco 5: Quando você recebe um convite

**5.1** Muitas pessoas preferem não comentar sobre dinheiro com amigos. Nos últimos 3 meses, com que frequência você... (F; se não recebeu convites no período, deixe em branco)
- a. recusou um convite principalmente por causa do custo da atividade
- b. recusou um convite principalmente por causa do custo ou do tempo de deslocamento (ônibus, aplicativo, volta para casa)
- c. recusou um convite por causa de dinheiro sem dizer que esse era o motivo

**5.2** Indique o quanto você concorda com cada afirmação. (C)
- a. Quando um amigo com quem não falo há alguns meses me convida para um encontro, fico feliz com o convite. **[P1]**
- b. Gostaria de receber convites dos meus amigos com mais frequência.
- c. Fico desconfortável quando um convite envolve gastos que eu não tinha planejado.
- d. Prefiro saber quanto um encontro vai custar antes de aceitar.
- e. Eu me sentiria à vontade para dizer ao grupo quanto posso gastar num encontro. **[P2]**
- f. Eu informaria quanto posso gastar se ninguém do grupo visse o meu valor. **[P2]**
- g. Raramente me preocupo com o custo de um encontro com amigos. (R)

**5.3** Comparado com você, quanto interesse seus amigos têm em se encontrar com mais frequência? (escala linear)
1 = Bem menos que eu · 2 · 3 = O mesmo que eu · 4 · 5 = Bem mais que eu

**5.4** Em média, quanto você costuma gastar num encontro presencial com amigos, incluindo transporte?
Até R$ 20 · R$ 21 a 50 · R$ 51 a 100 · R$ 101 a 200 · Mais de R$ 200 · Prefiro não responder

## Bloco 6: Distância e transporte

**6.1** Em média, quanto tempo você leva para chegar aos encontros com amigos?
Até 15 min · 15 a 30 min · 30 a 60 min · Mais de 60 min

**6.2** Nos últimos 3 meses, com que frequência você deixou de ir a um encontro por falta de transporte ou por não ter como voltar para casa? (F)

**6.3** Indique o quanto você concorda com cada afirmação. (C)
- a. A distância até os lugares de encontro faz com que eu vá a menos encontros do que gostaria.
- b. Voltar para casa depois de um encontro à noite é uma preocupação para mim.
- c. Chegar aos lugares onde meus amigos se encontram é fácil para mim. (R)

## Bloco 7: Jogos e encontros online

**7.1** Nos últimos 3 meses, com que frequência você jogou videogame online com amigos? (F, como múltipla escolha)
Nunca → [ir para o bloco 8] · Raramente · Às vezes · Frequentemente · Muito frequentemente

**7.2** Em quais plataformas? (marque todas que se aplicam)
PC (Steam, Epic etc.) · PlayStation · Xbox · Nintendo · Celular · Navegador

**7.3** Nos últimos 3 meses, com que frequência você e seus amigos deixaram de jogar juntos porque nem todos tinham o mesmo jogo ou não queriam pagar por ele? (F)

**7.4** Indique o quanto você concorda com cada afirmação. (C)
- a. Jogar online com amigos substitui bem um encontro presencial.
- b. Jogar online me ajuda a manter contato com amigos que moram longe.

## Bloco 8: Novas amizades

**8.1** Nos últimos 12 meses, quantas pessoas novas passaram a ser suas amigas?
Nenhuma → [ir para a 8.3] · 1 · 2 a 3 · 4 ou mais

**8.2** [se 1 ou mais] Como você conheceu essas pessoas? (marque todas que se aplicam)
Por meio de amigos em comum · Faculdade ou trabalho · Atividade regular (esporte, curso, religião, voluntariado) · Evento ou festa · Aplicativo ou internet · Outro

**8.3** Indique o quanto você concorda com cada afirmação. (C)
- a. Gostaria de conhecer pessoas novas com interesses parecidos com os meus.
- b. Estou satisfeito(a) com o número de amigos que tenho. (R)
- c. Eu me sentiria à vontade para conhecer pessoas novas num encontro com amigos de amigos.
- d. Eu me sentiria à vontade para conhecer pessoas novas num grupo pequeno de desconhecidos com um interesse em comum.
- e. Eu me sentiria à vontade para conhecer pessoas novas num evento grande.
- f. Eu me sentiria à vontade para conhecer uma pessoa nova num encontro a dois.

## Bloco 9: Como você tem se sentido

> As próximas perguntas são sobre como você tem se sentido. Não há respostas certas ou erradas.

**9.1** Com que frequência você sente falta de companhia?
Quase nunca · Às vezes · Frequentemente

**9.2** Com que frequência você se sente deixado(a) de lado?
Quase nunca · Às vezes · Frequentemente

**9.3** Com que frequência você se sente isolado(a) das outras pessoas?
Quase nunca · Às vezes · Frequentemente

**9.4** De 0 a 10, quão satisfeito(a) você está com a sua vida social hoje? (escala linear)
0 = Nada satisfeito(a) · 10 = Totalmente satisfeito(a)

> Os itens 9.1 a 9.3 são a escala curta de solidão de 3 itens (Hughes et al., 2004), derivada da UCLA e usada no ELSI-Brasil. **Antes de aplicar, conferir a redação oficial em português no questionário do ELSI-Brasil.** Pontuação de 3 a 9 (1 a 3 por item).

## Bloco 10: Como vocês combinam hoje e a ideia

**10.1** Pense na última vez que o seu grupo combinou um encontro. O que mais atrapalhou ou deu trabalho? (resposta aberta, opcional)

**10.2** Estamos estudando um assistente com IA que conversa em particular com cada pessoa do grupo (disponibilidade, preferências e quanto pode gastar) e propõe planos de encontro com lugar, transporte e divisão de custos. Quão útil seria para você um assistente que... (U)
- a. encontra um horário em que todos possam
- b. sugere o que fazer e onde
- c. planeja transporte e caronas
- d. respeita o quanto cada um pode gastar, sem expor ninguém
- e. divide os custos entre as pessoas
- f. toma a iniciativa de chamar o grupo
- g. sugere jogos online baratos quando não der para sair
- h. ajuda a conhecer pessoas novas com interesses parecidos

**10.3** O que faria você **não** usar algo assim? (resposta aberta, opcional)

## Encerramento

> Obrigado por participar!

---

## Plano de análise

**Preparação dos dados**

1. Inverter os itens (R) antes de calcular qualquer média: nota invertida = 6 − nota.
2. "Não se aplica" e respostas em branco ficam fora do cálculo, sem virar "Neutro".
3. Marcar como suspeitas as respostas que concordam com uma afirmação e com a invertida dela ao mesmo tempo (por exemplo, 4 ou 5 em 2.4c e em 2.4d). Reportar quantas foram e testar se os resultados mudam sem elas.
4. Para cada afirmação, reportar a **% que concorda** (notas 4 e 5) e a distribuição completa. Médias de escalas de 5 pontos são uma aproximação útil para ordenar itens, mas não devem ser o único número apresentado.

**Hipóteses e indicadores**

| Hipótese | Perguntas | Indicador para o relatório e o pitch |
|---|---|---|
| H1. Muita gente se encontra menos do que gostaria | 2.1 × 2.2; 2.4a (R) | % com frequência desejada maior que a real; % que discorda de 2.4a |
| H2. Encontros sugeridos morrem na coordenação | 3.1, 3.2, 3.3 | % que respondeu "às vezes" ou mais na 3.1; motivos ordenados pela média na 3.2; motivo mais citado na 3.3 |
| H3. Dinheiro é uma barreira escondida | 5.1a–c, 4.2d, 5.2c, 5.2g (R) | % que recusou convites por custo; entre essas pessoas, % que já escondeu o motivo (comparar com os 56% do CFP Board, 2026) |
| H4. Quem convida subestima a reação de quem é convidado (P1) | 4.2f × 5.2a | Entre quem respondeu as duas, diferença média entre a reação prevista (4.2f) e a própria reação (5.2a). Replica Liu et al. (2022) |
| H5. As pessoas acham que os amigos têm menos interesse do que elas | 5.3 | % com nota 1 ou 2 |
| H6. Organizar dá trabalho e fica nas mãos de poucos | 3.4a, 4.1, 4.2e, 4.3 | % que concorda com 3.4a; tarefas mais trabalhosas na 4.3 |
| H7. Existe demanda por novas conexões, de preferência via amigos de amigos | 8.3a, 8.3b (R), 8.3c–f | % que concorda com 8.3a; situação com maior concordância entre 8.3c–f |
| H8. Quem se encontra menos do que gostaria se sente mais só | 2.1 × 2.2 × 9.1–9.3 | Pontuação média de solidão por faixa de diferença entre frequência real e desejada |
| H9. O orçamento privado tem valor (P2) | 5.2e × 5.2f | % que concorda com 5.2f mas não com 5.2e (só informaria o valor em sigilo) |
| H10. Quais funcionalidades importam mais | 10.2 | Funcionalidades ordenadas pela % de "muito útil" ou "extremamente útil" |

**Cuidados na interpretação**

- A amostra é de conveniência (pessoas próximas de nós), então não representa a população. O relatório deve dizer isso.
- As análises são descritivas e de associação. Nenhuma pergunta permite concluir causa e efeito.
- Sempre reportar o tamanho da amostra (n) junto com as porcentagens. A meta é de 50 a 100 respostas.
- Se o questionário ficar longo demais no piloto, cortar primeiro os blocos 6 e 7.
