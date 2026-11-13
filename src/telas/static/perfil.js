/* Aba 2 (/sala/{codigo}/perfil): os 4 campos secretos (RF-07, RF-11, ADR 0009).
   O texto vai para POST/PUT /api/salas/{codigo}/participantes; a API devolve o resumo interpretado
   e as pendências (campo -> pergunta). Só depois de "Confirmar em Segredo" o grupo vê "Já preencheu ✅". */
'use strict';

(() => {
  const $ = (id) => document.getElementById(id);
  const CAMPOS = { origem: 'pendOrigem', horarios: 'pendHorarios', teto: 'pendTeto', preferencias: 'pendPreferencias' };
  const TRANSPORTE = { publico: 'ônibus/metrô', app: 'Uber/99', carro: 'carro', carona: 'carona', a_pe: 'a pé', bike: 'bike' };
  const RESTRICAO = {
    alim_vegano: 'vegano', alim_vegetariano: 'vegetariano', alim_sem_gluten: 'sem glúten',
    alim_sem_lactose: 'sem lactose', acess_entrada_sem_degrau: 'acessibilidade (entrada sem degrau)',
  };

  let codigo = Orq.codigoAtivo();
  let demo = Orq.ehDemo(codigo);
  let creds = demo ? {} : Orq.credenciais(codigo);
  let jaParticipa = false;

  $('linkPainel').addEventListener('click', () => Orq.irParaAba('sala'));

  // ------------------------------------------------------------ carregar sala e participante

  async function iniciar() {
    codigo = Orq.codigoAtivo();
    demo = Orq.ehDemo(codigo);
    creds = demo ? {} : Orq.credenciais(codigo);
    jaParticipa = false;

    $('secaoFormulario').hidden = false;
    $('secaoResumo').hidden = true;
    Orq.mostrarAviso($('perfilAvisoGeral'), '', 'info');

    let sala;
    try {
      sala = demo ? Demo.painel() : await Orq.api('GET', '/api/salas/' + encodeURIComponent(codigo));
    } catch (e) {
      // Se a sala ainda não existe no servidor, entra no modo demonstração para permitir testar
      codigo = Orq.definirCodigoAtivo(Orq.CODIGO_DEMO);
      demo = true;
      creds = {};
      sala = Demo.painel();
      Orq.mostrarAviso($('perfilAvisoGeral'), 'Você está visualizando a sala de exemplo (DEMO). Preencha seus 4 campos abaixo para testar.', 'info');
    }
    $('perfilTituloRole').textContent = sala.nome_role;
    $('perfilSubtituloRole').textContent = `Sala ${sala.codigo} · organizada por ${sala.organizador}`;

    if (sala.status === 'orquestrado') {
      Orq.mostrarAviso($('perfilAvisoGeral'), 'Este rolê já foi orquestrado. Veja o resultado no painel da sala.', 'info');
      bloquearFormulario();
      return;
    }

    if (creds.nome_sugerido && !$('nome').value) $('nome').value = creds.nome_sugerido;

    if (demo && !$('nome').value) {
      $('nome').value = 'Bia';
      $('perfilMaiorIdade').checked = true;
      if (!$('origem').value) $('origem').value = 'Águas Claras perto da estação';
      if (!$('horarios').value) $('horarios').value = 'Sexta depois das 19h ou sábado à tarde';
      if (!$('teto').value) $('teto').value = '60';
      if (!$('preferencias').value) $('preferencias').value = 'Barzinho ou café calmo, sou vegetariana, vou de metrô/Uber';
    }

    if (demo && Demo.temMeuPerfil()) {
      jaParticipa = true;
    } else if (!demo && creds.participante_id && creds.token) {
      try {
        const eu = await Orq.api('GET', `/api/salas/${encodeURIComponent(codigo)}/participantes/${encodeURIComponent(creds.participante_id)}`, undefined, creds.token);
        jaParticipa = true;
        if (eu.confirmado) {
          Orq.mostrarAviso($('perfilAvisoGeral'), `Oi, ${eu.nome}! Você já confirmou seus dados. Se mudar alguma coisa, envie de novo e confirme outra vez.`, 'ok');
        } else if (eu.perfil) {
          mostrarResumo(eu.perfil);
        }
      } catch (e) {
        if (e.status === 403 || e.status === 404) { Orq.esquecerParticipante(codigo); creds = Orq.credenciais(codigo); }
      }
    }
    $('blocoIdentificacao').hidden = jaParticipa;
  }

  function bloquearFormulario() {
    $('secaoFormulario').hidden = true;
    $('secaoResumo').hidden = true;
  }

  // ------------------------------------------------------------ enviar os 4 campos

  function lerCampos() {
    return {
      origem: $('origem').value.trim(),
      horarios: $('horarios').value.trim(),
      teto: $('teto').value.trim(),
      preferencias: $('preferencias').value.trim(),
    };
  }

  $('formPerfil').addEventListener('submit', async (ev) => {
    ev.preventDefault();
    const aviso = $('perfilAvisoGeral');
    const campos = lerCampos();
    const nome = $('nome').value.trim();

    if (!jaParticipa) {
      $('nome').setAttribute('aria-invalid', nome ? 'false' : 'true');
      if (!nome) { Orq.mostrarAviso(aviso, 'Escreva seu nome ou apelido.', 'erro'); $('nome').focus(); return; }
      if (!$('perfilMaiorIdade').checked) { Orq.mostrarAviso(aviso, 'O Orquestrador de Rolês é só para maiores de 18 anos.', 'erro'); return; }
    }
    if (!campos.origem && !campos.horarios && !campos.teto && !campos.preferencias) {
      Orq.mostrarAviso(aviso, 'Preencha os 4 campos do seu jeito. Pode escrever como falaria no grupo.', 'erro');
      $('origem').focus();
      return;
    }

    const botao = $('botaoEnviar');
    botao.disabled = true;
    botao.textContent = 'Lendo o que você escreveu…';
    Orq.mostrarAviso(aviso, '', 'info');
    try {
      let r;
      if (demo) {
        r = Demo.entrar(nome || 'Você', campos);
      } else if (jaParticipa) {
        r = await Orq.api('PUT', `/api/salas/${encodeURIComponent(codigo)}/participantes/${encodeURIComponent(creds.participante_id)}`, campos, creds.token);
      } else {
        r = await Orq.api('POST', `/api/salas/${encodeURIComponent(codigo)}/participantes`,
          Object.assign({ nome, maior_de_idade: true }, campos));
        Orq.salvarCredenciais(codigo, { participante_id: r.participante_id, token: r.token });
        creds = Orq.credenciais(codigo);
      }
      jaParticipa = true;
      $('blocoIdentificacao').hidden = true;
      mostrarResumo(r.perfil);
    } catch (e) {
      Orq.mostrarAviso(aviso, e.message, 'erro');
    } finally {
      botao.disabled = false;
      botao.textContent = 'Ver o que o app entendeu';
    }
  });

  // ------------------------------------------------------------ resumo para confirmar

  function rotulo(t) { return String(t).split(' / ')[0]; }

  function mostrarResumo(perfil) {
    const pend = perfil.pendencias || {};
    const temPendencia = Object.keys(pend).length > 0;

    for (const [campo, idPend] of Object.entries(CAMPOS)) {
      const caixa = $(idPend);
      const entrada = $(campo);
      if (pend[campo]) {
        caixa.textContent = '❓ ' + pend[campo];
        caixa.hidden = false;
        entrada.setAttribute('aria-invalid', 'true');
      } else {
        caixa.hidden = true;
        caixa.textContent = '';
        entrada.removeAttribute('aria-invalid');
      }
    }

    $('resumoTexto').textContent = perfil.resumo || 'Ainda faltam algumas informações.';
    const gostos = [...(perfil.tipos || []), ...(perfil.vibes || [])].map(rotulo);
    const itens = [
      ['Saindo de', perfil.regiao || perfil.ra || '—'],
      ['Quando pode', (perfil.janelas || []).map((j) => j.texto).filter(Boolean).join('; ') || '—'],
      ['Limite de gasto', perfil.teto ? Orq.reais(perfil.teto) + ' 🔒 só você vê' : '—'],
      ['Quer fazer', gostos.length ? gostos.join(', ') : 'qualquer coisa'],
      ['Restrições', (perfil.restricoes || []).map((r) => RESTRICAO[r] || r).join(', ') + (perfil.pet ? (perfil.restricoes && perfil.restricoes.length ? ', ' : '') + 'vai com pet' : '') || 'nenhuma'],
      ['Vai de', (perfil.transporte || []).map((t) => TRANSPORTE[t] || t).join(', ') || 'não informado (contamos ônibus/metrô)'],
    ];
    const lista = $('resumoLista');
    lista.replaceChildren(...itens.map(([k, v]) => Orq.el('li', {}, Orq.el('strong', { text: k }), Orq.el('span', { text: v }))));

    const confirmar = $('botaoConfirmar');
    confirmar.disabled = temPendencia;
    Orq.mostrarAviso($('avisoResumo'), temPendencia
      ? 'Responda as perguntas marcadas em vermelho no formulário e envie de novo.'
      : 'Está certo? Confirme para o grupo ver que você já preencheu. Seus dados continuam em segredo.',
      temPendencia ? 'erro' : 'info');

    $('secaoFormulario').hidden = !temPendencia;
    const secao = $('secaoResumo');
    secao.hidden = false;
    if (temPendencia) {
      const primeiro = Object.keys(CAMPOS).find((c) => pend[c]);
      if (primeiro) $(primeiro).focus();
    } else {
      secao.focus();
      secao.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }

  $('botaoCorrigir').addEventListener('click', () => {
    $('secaoFormulario').hidden = false;
    $('secaoResumo').hidden = true;
    $('origem').focus();
  });

  $('botaoConfirmar').addEventListener('click', async () => {
    const botao = $('botaoConfirmar');
    botao.disabled = true;
    try {
      if (demo) {
        Demo.confirmar();
      } else {
        await Orq.api('POST', `/api/salas/${encodeURIComponent(codigo)}/participantes/${encodeURIComponent(creds.participante_id)}/confirmar`, undefined, creds.token);
      }
      Orq.irParaAba('sala');
    } catch (e) {
      if (e.detalhe && e.detalhe.pendencias) {
        mostrarResumo({ pendencias: e.detalhe.pendencias, resumo: '' });
      } else {
        Orq.mostrarAviso($('avisoResumo'), e.message, 'erro');
      }
      botao.disabled = false;
    }
  });

  Orq.aoMudarAba((aba) => { if (aba === 'perfil') iniciar(); });
})();
