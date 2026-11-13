/* Funções comuns às Telas 1 a 3 (issue #42).
   - Os tokens da sala ficam só no localStorage deste aparelho e vão no cabeçalho X-Token (nunca na URL).
   - Todo texto vindo do usuário ou da API entra na página por textContent (sem innerHTML), contra XSS. */
'use strict';

const Orq = (() => {
  const CHAVE_SALAS = 'orquestrador:salas';
  const CHAVE_FONTE = 'orquestrador:fonte';
  const CODIGO_DEMO = 'DEMO';

  // ------------------------------------------------------------ credenciais por sala

  function lerSalas() {
    try { return JSON.parse(localStorage.getItem(CHAVE_SALAS)) || {}; } catch (_) { return {}; }
  }

  function credenciais(codigo) {
    return lerSalas()[codigo] || {};
  }

  function salvarCredenciais(codigo, dados) {
    const todas = lerSalas();
    todas[codigo] = Object.assign({}, todas[codigo], dados);
    try { localStorage.setItem(CHAVE_SALAS, JSON.stringify(todas)); } catch (_) { /* modo privado */ }
  }

  function esquecerParticipante(codigo) {
    const todas = lerSalas();
    if (todas[codigo]) {
      delete todas[codigo].participante_id;
      delete todas[codigo].token;
      try { localStorage.setItem(CHAVE_SALAS, JSON.stringify(todas)); } catch (_) { /* modo privado */ }
    }
  }

  // ------------------------------------------------------------ API

  class ErroApi extends Error {
    constructor(mensagem, status, detalhe) {
      super(mensagem);
      this.status = status;
      this.detalhe = detalhe;
    }
  }

  async function api(metodo, caminho, corpo, token) {
    const cabecalhos = { Accept: 'application/json' };
    if (corpo !== undefined) cabecalhos['Content-Type'] = 'application/json';
    if (token) cabecalhos['X-Token'] = token;
    let resp;
    try {
      resp = await fetch(caminho, {
        method: metodo,
        headers: cabecalhos,
        body: corpo !== undefined ? JSON.stringify(corpo) : undefined,
      });
    } catch (_) {
      throw new ErroApi('Sem conexão com o servidor. Confira sua internet e tente de novo.', 0, null);
    }
    let dados = null;
    try { dados = await resp.json(); } catch (_) { /* resposta sem JSON */ }
    if (!resp.ok) {
      const d = dados && dados.detail;
      let msg = 'Algo deu errado (erro ' + resp.status + '). Tente de novo.';
      if (d && typeof d === 'object' && !Array.isArray(d) && d.mensagem) msg = d.mensagem;
      else if (Array.isArray(d)) msg = 'Confira os campos: algum ficou vazio ou longo demais.';
      else if (typeof d === 'string') msg = d;
      throw new ErroApi(msg, resp.status, d);
    }
    return dados;
  }

  // ------------------------------------------------------------ DOM

  /** Cria um elemento. Filhos string viram nós de texto (nunca HTML). */
  function el(tag, attrs, ...filhos) {
    const no = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v === null || v === undefined || v === false) continue;
      if (k === 'class') no.className = v;
      else if (k === 'text') no.textContent = v;
      else if (k.startsWith('on') && typeof v === 'function') no.addEventListener(k.slice(2), v);
      else if (v === true) no.setAttribute(k, '');
      else no.setAttribute(k, String(v));
    }
    for (const f of filhos.flat()) {
      if (f === null || f === undefined || f === false) continue;
      no.append(f instanceof Node ? f : document.createTextNode(String(f)));
    }
    return no;
  }

  function mostrarAviso(alvo, mensagem, tipo) {
    if (!alvo) return;
    alvo.className = 'aviso aviso-' + (tipo || 'info');
    alvo.setAttribute('role', tipo === 'erro' ? 'alert' : 'status'); // leitor de tela anuncia sem tirar o foco
    alvo.textContent = mensagem || '';
  }

  // ------------------------------------------------------------ formatos (RNF-08: pt-BR, R$, 24 h)

  function reais(valor) {
    const n = Number(valor);
    return Number.isFinite(n) ? n.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' }) : '—';
  }

  function faixaReais(faixa) {
    if (!faixa) return '—';
    return faixa.min === faixa.max ? reais(faixa.min) : reais(faixa.min) + ' a ' + reais(faixa.max);
  }

  /** Só deixa passar links http(s), para não abrir javascript: vindo da base. */
  function urlSegura(url) {
    if (!url) return null;
    try {
      const u = new URL(url, location.origin);
      return u.protocol === 'https:' || u.protocol === 'http:' ? u.href : null;
    } catch (_) { return null; }
  }

  function codigoDaUrl() {
    const partes = location.pathname.split('/').filter(Boolean); // ["sala", "ROLE-XXXX", "perfil"?]
    return decodeURIComponent(partes[1] || '').trim().toUpperCase();
  }

  function ehDemo(codigo) { return codigo === CODIGO_DEMO; }

  function linkConvite(codigo) { return location.origin + '/sala/' + encodeURIComponent(codigo); }

  function linkWhatsApp(texto) { return 'https://wa.me/?text=' + encodeURIComponent(texto); }

  async function copiar(texto) {
    try {
      await navigator.clipboard.writeText(texto);
      return true;
    } catch (_) {
      const area = el('textarea', { 'aria-hidden': 'true', style: 'position:fixed;opacity:0' });
      area.value = texto;
      document.body.append(area);
      area.select();
      let ok = false;
      try { ok = document.execCommand('copy'); } catch (_) { ok = false; }
      area.remove();
      return ok;
    }
  }

  // ------------------------------------------------------------ fonte ajustável (RNF-07)

  const TAMANHOS = [87.5, 100, 112.5, 125, 137.5, 150];

  function aplicarFonte(indice) {
    const i = Math.max(0, Math.min(TAMANHOS.length - 1, indice));
    document.documentElement.style.fontSize = TAMANHOS[i] + '%';
    try { localStorage.setItem(CHAVE_FONTE, String(i)); } catch (_) { /* modo privado */ }
    return i;
  }

  function iniciarFonte() {
    let i = Number(localStorage.getItem(CHAVE_FONTE));
    if (!Number.isInteger(i)) i = 1;
    i = aplicarFonte(i);
    const menor = document.getElementById('fonteMenor');
    const maior = document.getElementById('fonteMaior');
    if (menor) menor.addEventListener('click', () => { i = aplicarFonte(i - 1); });
    if (maior) maior.addEventListener('click', () => { i = aplicarFonte(i + 1); });
  }

  // ------------------------------------------------------------ guia com 3 abas (tela única)

  const CHAVE_CODIGO = 'orquestrador:codigo_ativo';
  const ouvintesAba = [];
  let abaAtual = 'criar';
  let codigoEmUso = (() => {
    const daUrl = codigoDaUrl();
    if (daUrl) return daUrl;
    try { return (sessionStorage.getItem(CHAVE_CODIGO) || CODIGO_DEMO).toUpperCase(); } catch (_) { return CODIGO_DEMO; }
  })();

  function codigoAtivo() {
    return codigoEmUso || CODIGO_DEMO;
  }

  function definirCodigoAtivo(codigo) {
    codigoEmUso = (codigo || CODIGO_DEMO).trim().toUpperCase();
    try { sessionStorage.setItem(CHAVE_CODIGO, codigoEmUso); } catch (_) { /* modo privado */ }
    return codigoEmUso;
  }

  function aoMudarAba(fn) {
    ouvintesAba.push(fn);
  }

  function irParaAba(nome, novoCodigo) {
    if (novoCodigo) definirCodigoAtivo(novoCodigo);
    abaAtual = nome;
    const mapa = {
      criar: ['abaCriar', 'painelCriar'],
      perfil: ['abaPerfil', 'painelPerfil'],
      sala: ['abaSala', 'painelSala'],
    };
    for (const [chave, [idAba, idPainel]] of Object.entries(mapa)) {
      const ativa = chave === nome;
      const btn = document.getElementById(idAba);
      const painel = document.getElementById(idPainel);
      if (btn) btn.setAttribute('aria-selected', ativa ? 'true' : 'false');
      if (painel) painel.hidden = !ativa;
    }
    const main = document.getElementById('conteudo');
    if (main) main.classList.toggle('largo', nome === 'sala');
    for (const fn of ouvintesAba) fn(nome, codigoAtivo());
  }

  function iniciarAbas() {
    const abas = { abaCriar: 'criar', abaPerfil: 'perfil', abaSala: 'sala' };
    for (const [id, nome] of Object.entries(abas)) {
      const btn = document.getElementById(id);
      if (btn) btn.addEventListener('click', () => irParaAba(nome));
    }
    const partes = location.pathname.split('/').filter(Boolean);
    if (partes[0] === 'sala' && partes[2] === 'perfil') irParaAba('perfil', partes[1]);
    else if (partes[0] === 'sala' && partes[1]) irParaAba('sala', partes[1]);
    else irParaAba('criar');
  }

  // ------------------------------------------------------------ PWA (RNF-09)

  function registrarServiceWorker() {
    if ('serviceWorker' in navigator && location.protocol !== 'file:') {
      navigator.serviceWorker.register('/sw.js').catch(() => { /* app funciona sem ele */ });
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    iniciarFonte();
    iniciarAbas();
    registrarServiceWorker();
  });

  return {
    CODIGO_DEMO, ErroApi, api, credenciais, salvarCredenciais, esquecerParticipante, el, mostrarAviso,
    reais, faixaReais, urlSegura, codigoDaUrl, ehDemo, linkConvite, linkWhatsApp, copiar,
    codigoAtivo, definirCodigoAtivo, irParaAba, aoMudarAba,
  };
})();
