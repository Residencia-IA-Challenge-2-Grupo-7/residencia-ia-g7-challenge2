/* Voz no campo de horários da Tela 2 (RF-47, ADR 0017).

   Componente isolado: só precisa que a página tenha <textarea id="horarios">. Ele monta o botão logo abaixo do campo
   e não aparece se o servidor não tiver voz, se o navegador não gravar, sem HTTPS ou na sala DEMO. O texto transcrito
   entra no campo, editável, e nada é enviado sozinho. A gravação fica só na memória desta página até o envio. */
'use strict';

(() => {
  const campo = document.getElementById('horarios');
  const formulario = document.getElementById('formPerfil');
  if (!campo) return;

  const CHAVE_CONSENTIMENTO = 'orquestrador:voz-consentimento';
  const TIPOS = ['audio/webm;codecs=opus', 'audio/mp4', 'audio/ogg;codecs=opus'];
  const VOLUME_DE_FALA = 0.012;   // RMS acima disto conta como fala
  const QUADROS_DE_FALA = 4;      // de 100 ms cada; menos que isto é gravação muda
  const ESPERA_RESPOSTA_MS = 30000;
  const ROTULO = '🎤 Falar meus horários';

  let limites = null;      // resposta de GET /api/voz
  let sessao = null;       // gravação em andamento
  let envio = null;        // AbortController da transcrição em andamento
  let textoAnterior = null;

  // ------------------------------------------------------------ consentimento (RF-02): por aparelho, com volta atrás

  function consentiu() {
    try { return localStorage.getItem(CHAVE_CONSENTIMENTO) === '1'; } catch (_) { return false; }
  }

  function guardarConsentimento(sim) {
    try {
      if (sim) localStorage.setItem(CHAVE_CONSENTIMENTO, '1'); else localStorage.removeItem(CHAVE_CONSENTIMENTO);
    } catch (_) { /* modo privado: vale só para esta gravação */ }
  }

  // ------------------------------------------------------------ elementos

  const botao = Orq.el('button', { type: 'button', class: 'botao botao-secundario voz-botao', id: 'botaoVoz',
    'aria-describedby': 'vozDica', onclick: () => (sessao ? parar() : pedir()) });
  const cancelar = Orq.el('button', { type: 'button', class: 'botao botao-secundario', text: 'Cancelar', hidden: true,
    onclick: () => { descartar(); avisar('Gravação cancelada. Nada foi enviado.', 'info'); botao.focus(); } });
  const desfazer = Orq.el('button', { type: 'button', class: 'botao botao-secundario', text: '↩️ Desfazer', hidden: true,
    onclick: () => { trocarTexto(textoAnterior || ''); desfazer.hidden = true; avisar('Voltei ao texto anterior.', 'info'); } });
  const retirar = Orq.el('button', { type: 'button', class: 'voz-link', text: 'Não usar mais minha voz', hidden: true,
    onclick: () => { descartar(); guardarConsentimento(false); retirar.hidden = true; avisar('Pronto. Vou perguntar de novo antes de gravar.', 'info'); } });
  const dica = Orq.el('span', { class: 'dica', id: 'vozDica', text: 'Fale só dias e horários. Não diga endereço nem valores.' });
  const status = Orq.el('div', { class: 'aviso', id: 'vozStatus', role: 'status', 'aria-live': 'polite' });
  const permitir = Orq.el('button', { type: 'button', class: 'botao botao-primario', text: 'Permitir e falar',
    onclick: () => { guardarConsentimento(true); fecharPedido(); gravar(); } });
  const recusar = Orq.el('button', { type: 'button', class: 'botao botao-secundario', text: 'Prefiro digitar',
    onclick: () => { fecharPedido(); campo.focus(); } });
  const pedido = Orq.el('div', { class: 'voz-pedido', id: 'vozPedido', role: 'group', 'aria-labelledby': 'vozPedidoTitulo', hidden: true },
    Orq.el('strong', { id: 'vozPedidoTitulo', text: 'Posso ouvir você?' }),
    Orq.el('p', { text: 'Sua gravação vai para um serviço de transcrição fora do Brasil (Groq ou DeepInfra, pela OpenRouter), em modo sem retenção, e é descartada em seguida. O texto só aparece para você, e você confere antes de enviar. Tudo também pode ser digitado.' }),
    Orq.el('div', { class: 'grupo-botoes' }, permitir, recusar));
  const caixa = Orq.el('div', { class: 'voz', id: 'vozHorarios', hidden: true },
    Orq.el('div', { class: 'voz-acoes' }, botao, cancelar, desfazer), dica, pedido, status, retirar);
  campo.insertAdjacentElement('afterend', caixa);
  rotular(false);

  function avisar(texto, tipo) { Orq.mostrarAviso(status, texto, tipo); }

  function rotular(gravando, segundos) {
    botao.classList.toggle('voz-gravando', gravando);
    botao.setAttribute('aria-pressed', gravando ? 'true' : 'false');
    if (!gravando) { botao.replaceChildren(ROTULO); return; }
    // o cronômetro muda a cada segundo, então fica fora do leitor de tela
    botao.replaceChildren('⏹ Parar ', Orq.el('span', { 'aria-hidden': 'true', text: `(${segundos}s de ${limites.max_s}s)` }));
  }

  function trocarTexto(texto) {
    campo.value = texto;
    campo.dispatchEvent(new Event('input', { bubbles: true }));
  }

  // ------------------------------------------------------------ gravação

  function pedir() {
    if (envio) return;
    if (consentiu()) { gravar(); return; }
    pedido.hidden = false;
    botao.hidden = true;
    permitir.focus();
  }

  function fecharPedido() { pedido.hidden = true; botao.hidden = false; }

  async function gravar() {
    if (sessao || envio) return;
    avisar('', 'info');
    desfazer.hidden = true;
    const s = { pedacos: [], quadros: 0, medido: false, descartada: false };
    sessao = s;
    try {
      s.fluxo = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } });
    } catch (e) {
      sessao = null;
      avisar(e && (e.name === 'NotAllowedError' || e.name === 'SecurityError')
        ? 'O navegador não deixou usar o microfone. Libere nas permissões do site ou digite seus horários.'
        : 'Não achei um microfone. Digite seus horários.', 'erro');
      return;
    }
    if (s.descartada) { soltarMicrofone(s); return; }
    const tipo = TIPOS.find((t) => MediaRecorder.isTypeSupported(t));
    try {
      s.gravador = new MediaRecorder(s.fluxo, Object.assign({ audioBitsPerSecond: 32000 }, tipo ? { mimeType: tipo } : {}));
    } catch (_) {
      soltarMicrofone(s);
      sessao = null;
      avisar('Este navegador não consegue gravar. Digite seus horários.', 'erro');
      return;
    }
    s.gravador.ondataavailable = (ev) => { if (ev.data && ev.data.size) s.pedacos.push(ev.data); };
    s.gravador.onstop = () => terminar(s);
    medirVolume(s);
    s.gravador.start();
    s.inicio = Date.now();
    s.relogio = setInterval(() => {
      const seg = Math.floor((Date.now() - s.inicio) / 1000);
      if (seg >= limites.max_s) parar(); else rotular(true, seg);
    }, 250);
    rotular(true, 0);
    cancelar.hidden = false;
    avisar('Gravando. Toque em Parar quando terminar.', 'info');
  }

  /** Conta quantos décimos de segundo tiveram som de fala: silêncio vira palavra inventada no transcritor. */
  function medirVolume(s) {
    const Contexto = window.AudioContext || window.webkitAudioContext;
    if (!Contexto) return;
    try {
      s.contexto = new Contexto();
      const analisador = s.contexto.createAnalyser();
      analisador.fftSize = 2048;
      s.contexto.createMediaStreamSource(s.fluxo).connect(analisador);
      const amostras = new Float32Array(analisador.fftSize);
      s.volume = setInterval(() => {
        if (s.contexto.state !== 'running') return;
        analisador.getFloatTimeDomainData(amostras);
        let soma = 0;
        for (const x of amostras) soma += x * x;
        s.medido = true;
        if (Math.sqrt(soma / amostras.length) > VOLUME_DE_FALA) s.quadros += 1;
      }, 100);
    } catch (_) { s.medido = false; }
  }

  function soltarMicrofone(s) {
    clearInterval(s.relogio);
    clearInterval(s.volume);
    if (s.fluxo) s.fluxo.getTracks().forEach((t) => t.stop());
    if (s.contexto) s.contexto.close().catch(() => {});
  }

  function parar() {
    if (sessao && sessao.gravador && sessao.gravador.state !== 'inactive') sessao.gravador.stop();
  }

  /** Larga a gravação e o pedido em andamento, sem usar nada deles. */
  function descartar() {
    if (sessao) {
      const s = sessao;
      s.descartada = true;
      if (s.gravador && s.gravador.state !== 'inactive') s.gravador.stop(); else { soltarMicrofone(s); sessao = null; }
    }
    if (envio) envio.abort();
    cancelar.hidden = true;
    rotular(false);
  }

  async function terminar(s) {
    soltarMicrofone(s);
    if (sessao === s) sessao = null;
    cancelar.hidden = true;
    rotular(false);
    const pedacos = s.pedacos;
    s.pedacos = [];
    if (s.descartada) return;
    const audio = new Blob(pedacos, { type: (s.gravador.mimeType || 'audio/webm').split(';')[0] });
    if (!audio.size || (s.medido && s.quadros < QUADROS_DE_FALA)) {
      avisar('Não ouvi nada. Fale mais perto do microfone ou digite seus horários.', 'erro');
      botao.focus();
      return;
    }
    await transcrever(audio);
  }

  // ------------------------------------------------------------ transcrição

  async function transcrever(audio) {
    const meu = new AbortController();
    envio = meu;
    botao.disabled = true;
    avisar('Transcrevendo sua fala…', 'info');
    const prazo = setTimeout(() => { meu.demorou = true; meu.abort(); }, ESPERA_RESPOSTA_MS);
    try {
      const resp = await fetch(`/api/salas/${encodeURIComponent(Orq.codigoAtivo())}/voz/horarios`, {
        method: 'POST', body: audio, signal: meu.signal, cache: 'no-store',
        headers: { Accept: 'application/json', 'Content-Type': audio.type, 'X-Consentimento-Voz': '1' },
      });
      let dados = null;
      try { dados = await resp.json(); } catch (_) { /* resposta sem JSON */ }
      if (!resp.ok) {
        const d = dados && dados.detail;
        throw new Error((d && d.mensagem) || 'Não consegui transcrever agora. Digite seus horários.');
      }
      textoAnterior = campo.value;
      trocarTexto(dados.texto);
      desfazer.hidden = !textoAnterior;
      retirar.hidden = !consentiu();
      avisar(dados.aviso || 'Escrevi no campo o que ouvi. Confira e corrija antes de enviar.', dados.aviso ? 'erro' : 'ok');
      campo.focus();
    } catch (e) {
      if (meu.signal.aborted && !meu.demorou) return;
      avisar(meu.demorou ? 'A transcrição demorou demais. Digite seus horários ou tente de novo.'
        : e instanceof TypeError ? 'Sem conexão com o servidor. Digite seus horários ou tente de novo.' : e.message, 'erro');
      botao.disabled = false;
      botao.focus();
    } finally {
      clearTimeout(prazo);
      if (envio === meu) envio = null;
      botao.disabled = false;
    }
  }

  // ------------------------------------------------------------ quando aparece e quando larga o microfone

  function navegadorGrava() {
    return window.isSecureContext && typeof MediaRecorder === 'function' && typeof fetch === 'function'
      && navigator.mediaDevices && typeof navigator.mediaDevices.getUserMedia === 'function';
  }

  async function atualizar() {
    const codigo = Orq.codigoAtivo();
    if (!codigo || Orq.ehDemo(codigo) || !navegadorGrava()) { caixa.hidden = true; return; }
    if (!limites) {
      try { limites = await Orq.api('GET', '/api/voz'); } catch (_) { limites = null; }
    }
    caixa.hidden = !(limites && limites.disponivel);
    retirar.hidden = !consentiu();
  }

  Orq.aoMudarAba((aba) => {
    if (aba === 'perfil') atualizar(); else descartar();
  });
  if (formulario) formulario.addEventListener('submit', descartar);
  document.addEventListener('visibilitychange', () => {
    if (document.hidden && sessao) { descartar(); avisar('Parei a gravação porque você saiu da página. Nada foi enviado.', 'info'); }
  });
  window.addEventListener('pagehide', descartar);
})();
