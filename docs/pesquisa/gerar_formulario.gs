/**
 * Gera no Google Forms o questionário de validação descrito em
 * docs/pesquisa/questionario-validacao.md (v0.3).
 *
 * Como usar:
 *   1. Acesse https://script.google.com e crie um projeto novo.
 *   2. Cole este arquivo inteiro no editor, substituindo o conteúdo.
 *   3. Selecione a função criarFormulario e clique em Executar.
 *   4. Autorize o acesso ao Google Forms quando for pedido.
 *   5. Os links de edição e de resposta aparecem no registro de execução.
 *
 * Cada execução cria um formulário novo no seu Google Drive.
 * Ao mudar uma pergunta no questionário em Markdown, mude aqui também.
 */

const TITULO = 'Pesquisa: encontros entre amigos';

// Põe o número da pergunta (ex.: "2.1") no início do título. Facilita ligar as
// colunas da planilha de respostas ao plano de análise.
const NUMERAR = true;

const DESCRICAO = [
  'Esta pesquisa faz parte de um projeto acadêmico e busca entender como grupos de amigos ' +
    'combinam encontros e o que atrapalha. Leva cerca de 10 minutos.',
  '',
  'As respostas são anônimas: não pedimos nome, e-mail nem dados que identifiquem você, e os ' +
    'resultados serão apresentados apenas de forma agregada. Você pode pular perguntas ou parar ' +
    'a qualquer momento.',
  '',
  'Ao continuar, você declara ter 18 anos ou mais e concorda em participar.',
  '',
  'Definições usadas no questionário',
  '• Amigos: pessoas que você considera amigas. Não conte familiares nem parceiro(a).',
  '• Encontro: qualquer momento combinado para estar com amigos fora de aula ou trabalho ' +
    '(bar, churrasco, cinema, ir à casa de alguém etc.). Quando a pergunta tratar de encontros ' +
    'online, isso estará escrito.',
].join('\n');

const AGRADECIMENTO = 'Obrigado por participar!';

const ESCALA_C = ['Discordo totalmente', 'Discordo', 'Neutro', 'Concordo', 'Concordo totalmente'];
const ESCALA_F = ['Nunca', 'Raramente', 'Às vezes', 'Frequentemente', 'Muito frequentemente'];
const ESCALA_T = ['Nenhum', 'Pouco', 'Moderado', 'Bastante', 'Muito'];
const ESCALA_U = ['Nada útil', 'Pouco útil', 'Moderadamente útil', 'Muito útil', 'Extremamente útil'];
const ESCALA_SOLIDAO = ['Quase nunca', 'Às vezes', 'Frequentemente'];

// Grades de concordância ganham "Não se aplica" para que o "Neutro" não seja usado
// por quem não tem como responder.
const COLUNAS_C = ESCALA_C.concat(['Não se aplica']);

const FREQ_ENCONTROS = [
  'Nenhuma vez',
  'Menos de uma vez por mês',
  'Cerca de uma vez por mês',
  '2 a 3 vezes por mês',
  'Cerca de uma vez por semana',
  'Mais de uma vez por semana',
];

const MOTIVOS = [
  'Não achamos um dia e horário em que todos pudessem',
  'Ninguém tomou a frente para organizar',
  'Não chegamos a um acordo sobre o que fazer ou aonde ir',
  'O custo era alto para alguém',
  'Distância ou transporte',
  'Pessoas desistiram em cima da hora',
  'A conversa esfriou e as pessoas pararam de responder',
];

const CONCORDA = 'Indique o quanto você concorda com cada afirmação.';

function criarFormulario() {
  const form = FormApp.create(TITULO);
  form
    .setDescription(DESCRICAO)
    .setCollectEmail(false)
    .setProgressBar(true)
    .setAllowResponseEdits(false)
    .setLimitOneResponsePerUser(false)
    .setConfirmationMessage(AGRADECIMENTO);
  try {
    // Só existe em contas Google Workspace (ex.: e-mail institucional), onde o padrão
    // pode ser exigir login do mesmo domínio.
    form.setRequireLogin(false);
  } catch (e) {
    // Conta pessoal: não há restrição de domínio para desligar.
  }

  // Bloco 1: Perfil (primeira página, junto com a descrição)
  escolhaUnica(form, '1.1', 'Qual a sua idade?', ['18–21', '22–25', '26–30', '31–40', '41 ou mais']);
  variasEscolhas(form, '1.2', 'Como você costuma se deslocar para encontros com amigos?', [
    'Carro próprio',
    'Carona',
    'Transporte por aplicativo',
    'Ônibus ou metrô',
    'A pé ou bicicleta',
  ], true, 'Marque todas que se aplicam.');
  escolhaUnica(form, '1.3', 'Quantas pessoas você considera amigos próximos?', [
    'Nenhuma', '1', '2 a 3', '4 a 5', '6 a 9', '10 ou mais',
  ]);

  // Bloco 2: Frequência e bem-estar
  secao(form, 'Frequência e bem-estar');
  escolhaUnica(form, '2.1',
    'Nos últimos 3 meses, com que frequência você se encontrou pessoalmente com amigos?',
    FREQ_ENCONTROS);
  escolhaUnica(form, '2.2',
    'Com que frequência você gostaria de se encontrar pessoalmente com amigos?',
    FREQ_ENCONTROS);
  escolhaUnica(form, '2.3',
    'Nos últimos 3 meses, com que frequência você fez atividades online com amigos ' +
      '(jogar, assistir algo junto, chamada de vídeo em grupo)?',
    ESCALA_F);
  grade(form, '2.4', CONCORDA, [
    'Encontro meus amigos pessoalmente com a frequência que eu gostaria.',
    'Tenho amigos de quem gosto, mas com quem quase não me encontro mais.',
    'Depois de um encontro com amigos, costumo me sentir melhor do que antes.',
    'Passar tempo com amigos faz pouca diferença no meu humor.',
    'Minhas amizades continuam próximas mesmo quando passamos meses sem nos ver.',
  ], COLUNAS_C);

  // Bloco 3: Encontros que não aconteceram
  secao(form, 'Encontros que não aconteceram');
  const p31 = form.addMultipleChoiceItem().setTitle(titulo('3.1',
    'Nos últimos 3 meses, com que frequência um encontro sugerido no seu grupo de amigos ' +
      '(por você ou por outra pessoa) acabou não acontecendo?'));

  secao(form, 'Por que os encontros não aconteceram');
  grade(form, '3.2',
    'Nos últimos 3 meses, com que frequência um encontro deixou de acontecer...',
    [
      'porque não achamos um dia e horário em que todos pudessem',
      'porque ninguém tomou a frente para organizar',
      'porque não chegamos a um acordo sobre o que fazer ou aonde ir',
      'por causa do custo para alguém',
      'por causa de distância ou transporte',
      'porque pessoas desistiram em cima da hora',
      'porque a conversa esfriou e as pessoas pararam de responder',
    ], ESCALA_F);
  escolhaUnica(form, '3.3', 'Entre esses motivos, qual mais atrapalha os encontros do seu grupo?',
    MOTIVOS, 'Escolha um.').showOtherOption(true);

  const secao3c = secao(form, 'Como o seu grupo combina');
  grade(form, '3.4', CONCORDA, [
    'No meu grupo, quase sempre as mesmas pessoas propõem os encontros.',
    'Combinar um encontro no grupo de mensagens costuma ser rápido e fácil.',
    'Quando surgem muitas sugestões diferentes, o grupo tem dificuldade para decidir.',
  ], COLUNAS_C);
  variasEscolhas(form, '3.5', 'Como o seu grupo costuma combinar encontros?', [
    'Grupo de WhatsApp ou Telegram',
    'Mensagens individuais',
    'Enquete',
    'Aplicativo de agenda ou de eventos',
    'Pessoalmente',
  ], true, 'Marque todas que se aplicam.');

  // Bloco 4: Quando você propõe ou organiza
  secao(form, 'Quando você propõe ou organiza');
  const p40 = form.addMultipleChoiceItem().setTitle(titulo('4.0',
    'Nos últimos 3 meses, você propôs ou organizou algum encontro com amigos?'));

  secao(form, 'Propor e organizar encontros');
  escolhaUnica(form, '4.1',
    'Nos últimos 3 meses, com que frequência você pensou em propor um encontro e acabou não propondo?',
    ESCALA_F);
  grade(form, '4.2', CONCORDA, [
    'Quando penso em propor um encontro, fico em dúvida se os outros vão ter interesse.',
    'Evito perguntar a disponibilidade dos meus amigos para não incomodar.',
    'Fico à vontade para chamar amigos para um encontro.',
    'Evito sugerir programas que tenham custo para os outros.',
    'Organizar um encontro me dá mais trabalho do que eu gostaria.',
    'Se eu convidasse um amigo com quem não falo há alguns meses, ele ficaria feliz com o convite.',
  ], COLUNAS_C);
  grade(form, '4.3',
    'Organizar um encontro envolve várias tarefas. Quanto trabalho cada uma costuma dar a você?',
    [
      'Descobrir quando as pessoas estão livres',
      'Escolher o que fazer ou o lugar',
      'Pesquisar preços, horários e avaliações',
      'Resolver transporte e caronas',
      'Dividir os custos e cobrar as pessoas',
      'Lembrar as pessoas e confirmar presença',
    ], ESCALA_T.concat(['Não faço essa tarefa']));

  // Bloco 5: Quando você recebe um convite
  const secao5 = secao(form, 'Quando você recebe um convite');
  grade(form, '5.1', 'Nos últimos 3 meses, com que frequência você...', [
    'recusou um convite principalmente por causa do custo da atividade',
    'recusou um convite principalmente por causa do custo ou do tempo de deslocamento ' +
      '(ônibus, aplicativo, volta para casa)',
    'recusou um convite por causa de dinheiro sem dizer que esse era o motivo',
  ], ESCALA_F,
  'Muitas pessoas preferem não comentar sobre dinheiro com amigos. ' +
    'Se você não recebeu convites no período, deixe em branco.');
  grade(form, '5.2', CONCORDA, [
    'Quando um amigo com quem não falo há alguns meses me convida para um encontro, ' +
      'fico feliz com o convite.',
    'Gostaria de receber convites dos meus amigos com mais frequência.',
    'Fico desconfortável quando um convite envolve gastos que eu não tinha planejado.',
    'Prefiro saber quanto um encontro vai custar antes de aceitar.',
    'Eu me sentiria à vontade para dizer ao grupo quanto posso gastar num encontro.',
    'Eu informaria quanto posso gastar se ninguém do grupo visse o meu valor.',
    'Raramente me preocupo com o custo de um encontro com amigos.',
  ], COLUNAS_C);
  form.addScaleItem()
    .setTitle(titulo('5.3',
      'Comparado com você, quanto interesse seus amigos têm em se encontrar com mais frequência?'))
    .setHelpText('3 = o mesmo que eu')
    .setBounds(1, 5)
    .setLabels('Bem menos que eu', 'Bem mais que eu');
  escolhaUnica(form, '5.4',
    'Em média, quanto você costuma gastar num encontro presencial com amigos, incluindo transporte?',
    ['Até R$ 20', 'R$ 21 a 50', 'R$ 51 a 100', 'R$ 101 a 200', 'Mais de R$ 200', 'Prefiro não responder']);

  // Bloco 6: Distância e transporte
  secao(form, 'Distância e transporte');
  escolhaUnica(form, '6.1', 'Em média, quanto tempo você leva para chegar aos encontros com amigos?',
    ['Até 15 min', '15 a 30 min', '30 a 60 min', 'Mais de 60 min']);
  escolhaUnica(form, '6.2',
    'Nos últimos 3 meses, com que frequência você deixou de ir a um encontro por falta de ' +
      'transporte ou por não ter como voltar para casa?',
    ESCALA_F);
  grade(form, '6.3', CONCORDA, [
    'A distância até os lugares de encontro faz com que eu vá a menos encontros do que gostaria.',
    'Voltar para casa depois de um encontro à noite é uma preocupação para mim.',
    'Chegar aos lugares onde meus amigos se encontram é fácil para mim.',
  ], COLUNAS_C);

  // Bloco 7: Jogos e encontros online
  secao(form, 'Jogos e encontros online');
  const p71 = form.addMultipleChoiceItem().setTitle(titulo('7.1',
    'Nos últimos 3 meses, com que frequência você jogou videogame online com amigos?'));

  secao(form, 'Jogar com amigos');
  variasEscolhas(form, '7.2', 'Em quais plataformas?', [
    'PC (Steam, Epic etc.)', 'PlayStation', 'Xbox', 'Nintendo', 'Celular', 'Navegador',
  ], false, 'Marque todas que se aplicam.');
  escolhaUnica(form, '7.3',
    'Nos últimos 3 meses, com que frequência você e seus amigos deixaram de jogar juntos porque ' +
      'nem todos tinham o mesmo jogo ou não queriam pagar por ele?',
    ESCALA_F);
  grade(form, '7.4', CONCORDA, [
    'Jogar online com amigos substitui bem um encontro presencial.',
    'Jogar online me ajuda a manter contato com amigos que moram longe.',
  ], COLUNAS_C);

  // Bloco 8: Novas amizades
  const secao8 = secao(form, 'Novas amizades');
  const p81 = form.addMultipleChoiceItem().setTitle(titulo('8.1',
    'Nos últimos 12 meses, quantas pessoas novas passaram a ser suas amigas?'));

  secao(form, 'Como você conheceu novos amigos');
  variasEscolhas(form, '8.2', 'Como você conheceu essas pessoas?', [
    'Por meio de amigos em comum',
    'Faculdade ou trabalho',
    'Atividade regular (esporte, curso, religião, voluntariado)',
    'Evento ou festa',
    'Aplicativo ou internet',
  ], true, 'Marque todas que se aplicam.');

  const secao8c = secao(form, 'Conhecer pessoas novas');
  grade(form, '8.3', CONCORDA, [
    'Gostaria de conhecer pessoas novas com interesses parecidos com os meus.',
    'Estou satisfeito(a) com o número de amigos que tenho.',
    'Eu me sentiria à vontade para conhecer pessoas novas num encontro com amigos de amigos.',
    'Eu me sentiria à vontade para conhecer pessoas novas num grupo pequeno de desconhecidos ' +
      'com um interesse em comum.',
    'Eu me sentiria à vontade para conhecer pessoas novas num evento grande.',
    'Eu me sentiria à vontade para conhecer uma pessoa nova num encontro a dois.',
  ], COLUNAS_C);

  // Bloco 9: escala de solidão de 3 itens (Hughes et al., 2004). Não mudar a redação
  // nem as opções sem conferir a versão em português do ELSI-Brasil.
  secao(form, 'Como você tem se sentido',
    'As próximas perguntas são sobre como você tem se sentido. Não há respostas certas ou erradas.');
  escolhaUnica(form, '9.1', 'Com que frequência você sente falta de companhia?', ESCALA_SOLIDAO);
  escolhaUnica(form, '9.2', 'Com que frequência você se sente deixado(a) de lado?', ESCALA_SOLIDAO);
  escolhaUnica(form, '9.3', 'Com que frequência você se sente isolado(a) das outras pessoas?',
    ESCALA_SOLIDAO);
  form.addScaleItem()
    .setTitle(titulo('9.4', 'De 0 a 10, quão satisfeito(a) você está com a sua vida social hoje?'))
    .setBounds(0, 10)
    .setLabels('Nada satisfeito(a)', 'Totalmente satisfeito(a)');

  // Bloco 10: Como vocês combinam hoje e a ideia (a solução só aparece aqui)
  secao(form, 'Para terminar');
  form.addParagraphTextItem()
    .setTitle(titulo('10.1',
      'Pense na última vez que o seu grupo combinou um encontro. O que mais atrapalhou ou deu trabalho?'))
    .setHelpText('Opcional.');
  grade(form, '10.2', 'Quão útil seria para você um assistente que...', [
    'encontra um horário em que todos possam',
    'sugere o que fazer e onde',
    'planeja transporte e caronas',
    'respeita o quanto cada um pode gastar, sem expor ninguém',
    'divide os custos entre as pessoas',
    'toma a iniciativa de chamar o grupo',
    'sugere jogos online baratos quando não der para sair',
    'ajuda a conhecer pessoas novas com interesses parecidos',
  ], ESCALA_U,
  'Estamos estudando um assistente com IA que conversa em particular com cada pessoa do grupo ' +
    '(disponibilidade, preferências e quanto pode gastar) e propõe planos de encontro com lugar, ' +
    'transporte e divisão de custos.');
  form.addParagraphTextItem()
    .setTitle(titulo('10.3', 'O que faria você não usar algo assim?'))
    .setHelpText('Opcional.');

  // Desvios: só podem ser definidos depois que as seções de destino existem.
  definirDesvios(p31, ESCALA_F, { 'Nunca': secao3c });
  definirDesvios(p40, ['Sim', 'Não, mas pensei em propor', 'Não, nem pensei nisso'],
    { 'Não, nem pensei nisso': secao5 });
  definirDesvios(p71, ESCALA_F, { 'Nunca': secao8 });
  definirDesvios(p81, ['Nenhuma', '1', '2 a 3', '4 ou mais'], { 'Nenhuma': secao8c });

  Logger.log('Formulário criado.');
  Logger.log('Editar: ' + form.getEditUrl());
  Logger.log('Responder: ' + form.getPublishedUrl());
}

function titulo(codigo, texto) {
  return NUMERAR ? codigo + ' ' + texto : texto;
}

function secao(form, tituloSecao, ajuda) {
  const item = form.addPageBreakItem().setTitle(tituloSecao);
  if (ajuda) item.setHelpText(ajuda);
  return item;
}

function escolhaUnica(form, codigo, texto, opcoes, ajuda) {
  const item = form.addMultipleChoiceItem().setTitle(titulo(codigo, texto)).setChoiceValues(opcoes);
  if (ajuda) item.setHelpText(ajuda);
  return item;
}

function variasEscolhas(form, codigo, texto, opcoes, comOutro, ajuda) {
  const item = form.addCheckboxItem().setTitle(titulo(codigo, texto)).setChoiceValues(opcoes);
  if (comOutro) item.showOtherOption(true);
  if (ajuda) item.setHelpText(ajuda);
  return item;
}

function grade(form, codigo, texto, linhas, colunas, ajuda) {
  const item = form.addGridItem().setTitle(titulo(codigo, texto)).setRows(linhas).setColumns(colunas);
  if (ajuda) item.setHelpText(ajuda);
  return item;
}

// As opções listadas em `desvios` levam à seção indicada; as demais seguem para a próxima seção.
function definirDesvios(item, opcoes, desvios) {
  item.setChoices(opcoes.map(function (opcao) {
    return desvios[opcao]
      ? item.createChoice(opcao, desvios[opcao])
      : item.createChoice(opcao, FormApp.PageNavigationType.CONTINUE);
  }));
}
