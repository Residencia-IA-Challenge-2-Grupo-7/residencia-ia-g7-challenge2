/* Sala de demonstração (/sala/demo): funciona sem back-end, para prints, testes de uso e apresentação.
   Lugares reais da base (data/banco_aprovado_2fa.json); pessoas, horários e gastos são fictícios.
   O estado fica no sessionStorage desta aba e some ao fechá-la. */
'use strict';

const Demo = (() => {
  const CHAVE = 'orquestrador:demo';
  const SUCESSO = '🎉 Rolê orquestrado com sucesso!';

  const CARTOES = [
    {
      id: 'A', posicao: 1, nome: 'Crioula Café', tipo: 'Cafeteria / Doceria', ra: 'Guará',
      regiao_administrativa: 'Guará', endereco: 'QE 19 do Guará, Brasília - DF',
      inicio: '2026-11-14T16:00:00', fim: '2026-11-14T19:00:00', horario: 'sáb 14/11, 16h às 19h',
      horario_situacao: 'aberto', quantos_podem: '4 de 4 podem', consumo_estimado_rs: '50.00',
      faixa_gasto_rs: { min: '50.00', max: '61.00' }, tempo_medio_chegada_min: 24, tempo_maximo_chegada_min: 38,
      nota_justica: 86.5,
      explicacao: 'Fica no meio do caminho entre Ceilândia, Águas Claras e a Asa Norte: ninguém passa de 40 min de viagem. Cabe no orçamento de todos e tem opção vegetariana.',
      tiktok_url: 'https://www.tiktok.com/@rolezandoembrasilia/video/7626406997541309704',
      fonte: 'Vídeo de @rolezandoembrasilia', vibes: ['Calmo / Bom para Conversar', 'Intimista / Aconchegante'],
    },
    {
      id: 'B', posicao: 2, nome: 'Rossoni', tipo: 'Restaurante / Gastronomia', ra: 'Plano Piloto',
      regiao_administrativa: 'Plano Piloto (Asa Sul)', endereco: 'CLS 306/307, Asa Sul, Brasília - DF',
      inicio: '2026-11-13T19:30:00', fim: '2026-11-13T22:30:00', horario: 'sex 13/11, 19h30 às 22h30',
      horario_situacao: 'aberto', quantos_podem: '3 de 4 podem', consumo_estimado_rs: '35.00',
      faixa_gasto_rs: { min: '35.00', max: '46.00' }, tempo_medio_chegada_min: 29, tempo_maximo_chegada_min: 52,
      nota_justica: 71.2,
      explicacao: 'O mais barato das opções e animado, mas quem sai de Ceilândia leva cerca de 50 min de metrô.',
      tiktok_url: 'https://www.tiktok.com/@rolezandoembrasilia/video/7626407184108129543',
      fonte: 'Vídeo de @rolezandoembrasilia', vibes: ['Baratinho', 'Animado / Galera'],
    },
    {
      id: 'C', posicao: 3, nome: 'Omura Sushi', tipo: 'Restaurante / Gastronomia', ra: 'Samambaia',
      regiao_administrativa: 'Samambaia', endereco: 'QN 122, Conjunto 05, Lote 04, Samambaia - DF',
      inicio: '2026-11-14T19:00:00', fim: '2026-11-14T22:00:00', horario: 'sáb 14/11, 19h às 22h',
      horario_situacao: 'provavel', quantos_podem: '4 de 4 podem', consumo_estimado_rs: '70.00',
      faixa_gasto_rs: { min: '70.00', max: '81.00' }, tempo_medio_chegada_min: 33, tempo_maximo_chegada_min: 47,
      nota_justica: 68.0,
      explicacao: 'Perto de quem mora mais longe do Plano Piloto. O horário de sábado à noite não foi confirmado pelo lugar.',
      tiktok_url: 'https://www.tiktok.com/@rolezandoembrasilia/video/7626870903460203784',
      fonte: 'Vídeo de @rolezandoembrasilia', vibes: ['Calmo / Bom para Conversar', 'Intimista / Aconchegante'],
    },
    {
      id: 'D', posicao: 4, nome: 'Spelunca DF', tipo: 'Bar / Boteco / Pub', ra: 'Plano Piloto',
      regiao_administrativa: 'Plano Piloto (Asa Sul)', endereco: 'SCS, Ed. Maristela, Brasília - DF',
      inicio: '2026-11-14T20:00:00', fim: '2026-11-14T23:00:00', horario: 'sáb 14/11, 20h às 23h',
      horario_situacao: 'aberto', quantos_podem: '4 de 4 podem', consumo_estimado_rs: '65.50',
      faixa_gasto_rs: { min: '65.50', max: '76.50' }, tempo_medio_chegada_min: 30, tempo_maximo_chegada_min: 50,
      nota_justica: 64.4,
      explicacao: 'Bar alternativo no Setor Comercial Sul, perto do metrô. Fica no limite do orçamento de uma pessoa.',
      tiktok_url: 'https://www.tiktok.com/@rolezandoembrasilia/video/7628371621136452882',
      fonte: 'Vídeo de @rolezandoembrasilia', vibes: ['Animado / Galera', 'Cultural / Alternativo'],
    },
  ];

  const PESSOAS = [
    { id: 'p-rafa', nome: 'Rafaela', preencheu: true },
    { id: 'p-cadu', nome: 'Cadu', preencheu: true },
    { id: 'p-marcio', nome: 'Márcio', preencheu: true },
  ];
  const VOTOS_DOS_OUTROS = { 'p-rafa': ['A', 'B'], 'p-cadu': ['A'], 'p-marcio': ['C', 'A'] };

  function estadoInicial() {
    return { status: 'coletando', participantes: PESSOAS.slice(), eu: null, votos: {}, resultado: null };
  }

  function ler() {
    try { return JSON.parse(sessionStorage.getItem(CHAVE)) || estadoInicial(); } catch (_) { return estadoInicial(); }
  }

  function gravar(e) {
    try { sessionStorage.setItem(CHAVE, JSON.stringify(e)); } catch (_) { /* modo privado */ }
  }

  function painel() {
    const e = ler();
    const confirmados = e.participantes.filter((p) => p.preencheu).length;
    const placar = {};
    if (e.status !== 'coletando') {
      for (const c of CARTOES) placar[c.id] = 0;
      for (const ops of Object.values(e.votos)) for (const o of ops) placar[o] += 1;
    }
    const venc = e.resultado && CARTOES.find((c) => c.id === e.resultado.sugestao_id);
    return {
      codigo: 'DEMO', nome_role: 'Aniversário da Galera (exemplo)', organizador: 'Rafaela', status: e.status,
      link_convite: '/sala/DEMO', limite_participantes: 20, participantes: e.participantes,
      preencheram: `${confirmados} de ${e.participantes.length}`,
      pode_gerar_sugestoes: confirmados >= 2 && e.status !== 'orquestrado',
      janela_escolhida: e.status === 'coletando' ? null : { horario: 'sáb 14/11, 16h às 23h', quantos_podem: '4 de 4 podem' },
      sugestoes: e.status === 'coletando' ? [] : CARTOES,
      placar, votaram: `${Object.keys(e.votos).length} de ${confirmados}`,
      resultado: e.resultado && Object.assign({}, e.resultado, {
        resumo_whatsapp: [SUCESSO, '*Aniversário da Galera (exemplo)*', `📍 ${venc.nome} (${venc.regiao_administrativa})`,
          `🏠 ${venc.endereco}`, `🗓️ ${venc.horario}`, `🎬 ${venc.tiktok_url}`].join('\n'),
        link_agenda: null,
      }),
      avisos: ['Sala de demonstração: lugares reais da base, pessoas e valores fictícios. Nada é enviado ao servidor.'],
    };
  }

  /** Imita o interpretador dos 4 campos só para a demonstração (o real fica em src/interpretador/campos.py). */
  function entrar(nome, campos) {
    const e = ler();
    const pend = {};
    if (!campos.origem.trim()) pend.origem = 'De onde você vai sair? Pode ser a região ou a quadra.';
    if (!campos.horarios.trim()) pend.horarios = 'Quais dias e horários você pode?';
    const teto = Number(String(campos.teto).replace(/[^\d,.]/g, '').replace(',', '.'));
    if (!Number.isFinite(teto) || teto <= 0) pend.teto = 'Qual o máximo que você topa gastar, em reais?';
    const perfil = {
      ra: null, regiao: campos.origem.trim() || null,
      janelas: campos.horarios.trim() ? [{ texto: campos.horarios.trim() }] : [],
      teto: Number.isFinite(teto) && teto > 0 ? teto.toFixed(2) : null,
      tipos: [], vibes: [], restricoes: [], transporte: [], pet: false, pendencias: pend,
      completo: Object.keys(pend).length === 0,
      resumo: Object.keys(pend).length ? '' : `${campos.horarios.trim()}; saindo de ${campos.origem.trim()}; teto de ${Orq.reais(teto)} (só você vê); ${campos.preferencias.trim() || 'sem preferência'}.`,
    };
    if (!e.eu) {
      e.eu = { id: 'p-voce', nome };
      e.participantes.push({ id: 'p-voce', nome, preencheu: false });
    }
    gravar(e);
    return { participante_id: 'p-voce', token: 'demo', perfil };
  }

  function confirmar() {
    const e = ler();
    const eu = e.participantes.find((p) => p.id === 'p-voce');
    if (eu) eu.preencheu = true;
    gravar(e);
  }

  function gerarSugestoes() {
    const e = ler();
    e.status = 'votacao';
    e.votos = {};
    e.resultado = null;
    gravar(e);
    return painel();
  }

  function fechar(e) {
    const placar = {};
    for (const c of CARTOES) placar[c.id] = 0;
    for (const ops of Object.values(e.votos)) for (const o of ops) placar[o] += 1;
    const maior = Math.max(...Object.values(placar));
    const empatados = CARTOES.filter((c) => placar[c.id] === maior);
    empatados.sort((a, b) => b.nota_justica - a.nota_justica || a.posicao - b.posicao);
    e.resultado = { sugestao_id: empatados[0].id, votos: maior, desempate_por_justica: empatados.length > 1, mensagem: SUCESSO };
    e.status = 'orquestrado';
  }

  function votar(opcoes) {
    const e = ler();
    if (e.status !== 'votacao') throw new Orq.ErroApi('A votação não está aberta.', 409, null);
    e.votos = Object.assign({}, VOTOS_DOS_OUTROS, { 'p-voce': opcoes });
    const confirmados = e.participantes.filter((p) => p.preencheu).length;
    if (Object.keys(e.votos).length >= confirmados) fechar(e);
    gravar(e);
    return painel();
  }

  function fecharVotacao() {
    const e = ler();
    if (e.status !== 'votacao') throw new Orq.ErroApi('A votação não está aberta.', 409, null);
    fechar(e);
    gravar(e);
    return painel();
  }

  function minhaVisao() {
    const e = ler();
    return {
      participante_id: 'p-voce', nome: e.eu ? e.eu.nome : 'Você', confirmado: true, perfil: null,
      meus_votos: e.votos['p-voce'] || [],
      meu_custo_e_tempo: Object.fromEntries(CARTOES.map((c, i) => [c.id, {
        modo: 'publico', minutos: [26, 41, 35, 33][i], gasto_total_rs: (Number(c.consumo_estimado_rs) + 11).toFixed(2),
      }])),
    };
  }

  function reiniciar() {
    sessionStorage.removeItem(CHAVE);
  }

  return { painel, entrar, confirmar, gerarSugestoes, votar, fecharVotacao, minhaVisao, reiniciar, temMeuPerfil: () => !!ler().eu };
})();
