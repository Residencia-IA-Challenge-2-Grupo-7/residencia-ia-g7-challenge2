/* Aba 3 (/sala/{codigo}): painel da sala, 3 a 4 cartões de sugestão, votação múltipla
   e banner oficial "🎉 Rolê orquestrado com sucesso!" (RF-04, RF-15, RF-25). */
'use strict';

(() => {
  const $ = (id) => document.getElementById(id);
  const TRANSPORTE = { publico: 'ônibus/metrô', app: 'Uber/99', carro: 'carro', carona: 'carona', a_pe: 'a pé', bike: 'bike' };
  const SITUACAO_HORARIO = { aberto: 'Aberto no horário', provavel: 'Horário provável (confirme antes)', incerto: 'Consultar horário no local' };

  let codigo = Orq.codigoAtivo();
  let demo = Orq.ehDemo(codigo);
  let creds = demo ? {} : Orq.credenciais(codigo);
  let salaAtual = null;
  let minhaVisaoAtual = null;

  $('linkMeuPerfil').addEventListener('click', () => Orq.irParaAba('perfil'));

  // ------------------------------------------------------------ carregar painel e visão pessoal

  async function carregar() {
    codigo = Orq.codigoAtivo();
    demo = Orq.ehDemo(codigo);
    creds = demo ? {} : Orq.credenciais(codigo);
    $('botaoReiniciarDemo').hidden = !demo;
    Orq.mostrarAviso($('salaAvisoGeral'), '', 'info');

    let sala;
    try {
      sala = demo ? Demo.painel() : await Orq.api('GET', '/api/salas/' + encodeURIComponent(codigo));
    } catch (e) {
      // Se a sala ainda não existe no servidor (ou servidor foi reiniciado), entra no modo demonstração para permitir testar
      codigo = Orq.definirCodigoAtivo(Orq.CODIGO_DEMO);
      demo = true;
      creds = {};
      sala = Demo.painel();
      $('botaoReiniciarDemo').hidden = false;
      Orq.mostrarAviso(
        $('salaAvisoGeral'),
        'Você está visualizando a sala de exemplo (DEMO). Crie sua sala na aba "1. Criar Sala" ou vote abaixo para testar a orquestração.',
        'info'
      );
    }
    salaAtual = sala;

    minhaVisaoAtual = null;
    if (demo && Demo.temMeuPerfil()) {
      minhaVisaoAtual = Demo.minhaVisao();
    } else if (!demo && creds.participante_id && creds.token) {
      try {
        minhaVisaoAtual = await Orq.api(
          'GET',
          `/api/salas/${encodeURIComponent(codigo)}/participantes/${encodeURIComponent(creds.participante_id)}`,
          undefined,
          creds.token
        );
      } catch (e) {
        if (e.status === 403 || e.status === 404) {
          Orq.esquecerParticipante(codigo);
          creds = Orq.credenciais(codigo);
        }
      }
    }

    renderizar(sala, minhaVisaoAtual);
  }

  // ------------------------------------------------------------ renderização segura (sem innerHTML)

  function renderizar(sala, visao) {
    $('salaTituloRole').textContent = sala.nome_role;
    $('salaSubtituloRole').textContent = `Sala ${sala.codigo} · organizada por ${sala.organizador}`;

    const avisosTexto = (sala.avisos || []).join(' ');
    Orq.mostrarAviso($('avisosSala'), avisosTexto, 'info');

    // Participantes
    $('contagemPreencheram').textContent = sala.preencheram;
    const lista = $('listaParticipantes');
    lista.replaceChildren(
      ...sala.participantes.map((p) => {
        const eu = visao && visao.participante_id === p.id;
        const rotuloNome = eu ? `${p.nome} (você)` : p.nome;
        const selo = p.preencheu
          ? Orq.el('span', { class: 'selo selo-ok', text: 'Já preencheu ✅' })
          : Orq.el('span', { class: 'selo selo-espera', text: 'Falta preencher ⏳' });
        return Orq.el('li', {}, Orq.el('strong', { text: rotuloNome }), selo);
      })
    );

    // Botão de perfil
    const linkPerfil = $('linkMeuPerfil');
    if (sala.status === 'orquestrado') {
      linkPerfil.hidden = true;
    } else {
      linkPerfil.hidden = false;
      linkPerfil.textContent = visao ? '✏️ Editar meus dados' : '🔒 Preencher meus dados';
    }

    // Bloco do organizador para gerar sugestões
    const souOrganizador = demo || Boolean(creds.token_organizador);
    const blocoOrg = $('blocoOrganizadorColeta');
    if (souOrganizador && sala.status !== 'orquestrado') {
      blocoOrg.hidden = false;
      const btnGerar = $('botaoGerarSugestoes');
      btnGerar.disabled = !sala.pode_gerar_sugestoes;
      btnGerar.textContent = sala.status === 'votacao' ? '🔄 Gerar novas sugestões' : '✨ Gerar Sugestões de Rolê';
      $('dicaGerar').textContent = sala.pode_gerar_sugestoes
        ? 'Tudo pronto para cruzar horários, orçamento e distância do grupo.'
        : 'É preciso pelo menos 2 pessoas com os dados confirmados para gerar sugestões.';
    } else {
      blocoOrg.hidden = true;
    }

    // Resultado oficial
    renderizarResultado(sala);

    // Cartões de sugestão
    renderizarSugestoes(sala, visao, souOrganizador);
  }

  function renderizarResultado(sala) {
    const secao = $('secaoResultado');
    const r = sala.resultado;
    if (!r) {
      secao.hidden = true;
      return;
    }
    const venc = (sala.sugestoes || []).find((s) => s.id === r.sugestao_id);
    $('tituloResultado').textContent = r.mensagem || '🎉 Rolê orquestrado com sucesso!';
    $('textoVencedor').textContent = venc
      ? `Opção ${venc.id}: ${venc.nome} (${venc.regiao_administrativa}) — ${venc.horario}`
      : `Opção ${r.sugestao_id}`;

    const resumo = r.resumo_whatsapp || '';
    $('botaoWhatsAppResumo').href = Orq.linkWhatsApp(resumo);
    $('botaoCopiarResumo').onclick = async () => {
      const ok = await Orq.copiar(resumo);
      Orq.mostrarAviso(
        $('avisoResumoCopiado'),
        ok ? 'Resumo copiado! Cole no grupo do WhatsApp.' : 'Não deu para copiar automaticamente.',
        ok ? 'ok' : 'erro'
      );
    };

    const btnAgenda = $('botaoAgenda');
    const agendaUrl = Orq.urlSegura(r.link_agenda);
    if (agendaUrl) {
      btnAgenda.href = agendaUrl;
      btnAgenda.hidden = false;
    } else {
      btnAgenda.hidden = true;
    }
    secao.hidden = false;
  }

  function renderizarSugestoes(sala, visao, souOrganizador) {
    const secao = $('secaoSugestoes');
    const sugestoes = sala.sugestoes || [];
    if (!sugestoes.length) {
      secao.hidden = true;
      return;
    }
    secao.hidden = false;

    const janela = sala.janela_escolhida;
    $('subtituloSugestoes').textContent = janela
      ? `Melhor janela para o grupo: ${janela.horario} (${janela.quantos_podem})`
      : 'Sugestões ordenadas por aderência, justiça espacial e horário';
    $('seloVotaram').textContent = `${sala.votaram} votaram`;

    const placar = sala.placar || {};
    const totalConfirmados = Math.max(1, sala.participantes.filter((p) => p.preencheu).length);
    const meusVotos = new Set((visao && visao.meus_votos) || []);
    const podeVotar = sala.status === 'votacao' && Boolean(visao && visao.confirmado);
    const vencedorId = sala.resultado ? sala.resultado.sugestao_id : null;

    const grade = $('gradeCartoes');
    grade.replaceChildren(
      ...sugestoes.map((s) => {
        const marcado = meusVotos.has(s.id);
        const ehVencedor = vencedorId === s.id;
        const votos = placar[s.id] || 0;
        const pct = Math.min(100, Math.round((votos / totalConfirmados) * 100));

        const classes = ['cartao-role'];
        if (marcado && sala.status === 'votacao') classes.push('marcado');
        if (ehVencedor) classes.push('vencedor');

        const linkVideo = Orq.urlSegura(s.tiktok_url);
        const meuInfo = visao && visao.meu_custo_e_tempo ? visao.meu_custo_e_tempo[s.id] : null;
        const tempoTexto = s.tempo_medio_chegada_min != null
          ? `~${s.tempo_medio_chegada_min} min (máx. ${s.tempo_maximo_chegada_min} min)`
          : 'não calculado';

        const filhos = [
          Orq.el('div', { class: 'topo-cartao' },
            Orq.el('span', { class: 'letra', text: s.id }),
            Orq.el('div', {},
              Orq.el('h3', { class: 'nome-lugar', text: s.nome }),
              Orq.el('div', { style: 'display:flex; flex-wrap:wrap; gap:6px' },
                Orq.el('span', { class: 'selo', text: s.regiao_administrativa || s.ra || 'DF' }),
                s.tipo ? Orq.el('span', { class: 'selo selo-espera', text: s.tipo }) : null,
                ehVencedor ? Orq.el('span', { class: 'selo selo-ok', text: '🏆 Escolhido' }) : null
              )
            )
          ),
          Orq.el('dl', {},
            Orq.el('dt', { text: 'Endereço' }),
            Orq.el('dd', { text: s.endereco || '—' }),
            Orq.el('dt', { text: 'Quando' }),
            Orq.el('dd', { text: `${s.horario} · ${SITUACAO_HORARIO[s.horario_situacao] || s.horario_situacao}` }),
            Orq.el('dt', { text: 'Gasto' }),
            Orq.el('dd', { text: `${Orq.faixaReais(s.faixa_gasto_rs)} por pessoa (consumo + transporte)` }),
            Orq.el('dt', { text: 'Chegada' }),
            Orq.el('dd', { text: tempoTexto })
          ),
          s.explicacao ? Orq.el('p', { class: 'explicacao', text: s.explicacao }) : null,
          meuInfo ? Orq.el('p', {
            class: 'meu-custo',
            text: `🔒 Para você: ~${meuInfo.minutos} min (${TRANSPORTE[meuInfo.modo] || meuInfo.modo}), total estimado ${Orq.reais(meuInfo.gasto_total_rs)}.`,
          }) : null,
          linkVideo ? Orq.el('p', { style: 'margin:2px 0' },
            Orq.el('a', { href: linkVideo, target: '_blank', rel: 'noopener', text: '▶️ Ver vídeo no TikTok ↗' })
          ) : null,
          Orq.el('div', { class: 'placar' },
            Orq.el('span', { text: `${votos} ${votos === 1 ? 'voto' : 'votos'}` }),
            Orq.el('div', { class: 'barra', 'aria-hidden': 'true' }, Orq.el('span', { style: `width:${pct}%` }))
          ),
        ];

        if (sala.status === 'votacao') {
          const check = Orq.el('input', {
            type: 'checkbox',
            name: 'opcoes',
            value: s.id,
            checked: marcado,
            disabled: !podeVotar,
          });
          check.addEventListener('change', (ev) => {
            ev.currentTarget.closest('.cartao-role').classList.toggle('marcado', ev.currentTarget.checked);
          });
          filhos.push(
            Orq.el('div', { class: 'votar' },
              Orq.el('label', { class: 'caixa-marcar' },
                check,
                Orq.el('span', { text: podeVotar ? `Votar na opção ${s.id}` : 'Confirme seus dados acima para votar' })
              )
            )
          );
        }

        return Orq.el('article', { class: classes.join(' '), 'data-sugestao': s.id }, ...filhos);
      })
    );

    const barra = $('barraVotacao');
    if (sala.status === 'votacao' && (podeVotar || souOrganizador)) {
      barra.hidden = false;
      $('botaoVotar').hidden = !podeVotar;
      $('botaoFecharVotacao').hidden = !souOrganizador;
    } else {
      barra.hidden = true;
    }
  }

  // ------------------------------------------------------------ ações

  $('botaoAtualizar').addEventListener('click', carregar);

  $('botaoCopiarConvite').addEventListener('click', async () => {
    const link = Orq.linkConvite(codigo);
    const ok = await Orq.copiar(link);
    Orq.mostrarAviso(
      $('salaAvisoGeral'),
      ok ? 'Link de convite copiado! Cole no grupo do WhatsApp.' : `Copie o link: ${link}`,
      ok ? 'ok' : 'erro'
    );
  });

  $('botaoReiniciarDemo').addEventListener('click', () => {
    Demo.reiniciar();
    Orq.mostrarAviso($('salaAvisoGeral'), 'Sala de exemplo reiniciada.', 'info');
    carregar();
  });

  $('botaoGerarSugestoes').addEventListener('click', async () => {
    const botao = $('botaoGerarSugestoes');
    botao.disabled = true;
    botao.textContent = 'Buscando melhores lugares…';
    Orq.mostrarAviso($('salaAvisoGeral'), '', 'info');
    try {
      const painel = demo
        ? Demo.gerarSugestoes()
        : await Orq.api('POST', `/api/salas/${encodeURIComponent(codigo)}/gerar-sugestoes`, undefined, creds.token_organizador);
      renderizar(painel, demo && Demo.temMeuPerfil() ? Demo.minhaVisao() : minhaVisaoAtual);
      if (demo && Demo.temMeuPerfil()) await carregar();
      $('secaoSugestoes').scrollIntoView({ behavior: 'smooth', block: 'start' });
    } catch (e) {
      Orq.mostrarAviso($('salaAvisoGeral'), e.message, 'erro');
      botao.disabled = false;
      botao.textContent = '✨ Gerar Sugestões de Rolê';
    }
  });

  $('formVotacao').addEventListener('submit', async (ev) => {
    ev.preventDefault();
    const escolhidas = Array.from(document.querySelectorAll('input[name="opcoes"]:checked')).map((c) => c.value);
    const aviso = $('avisoVoto');
    if (!escolhidas.length) {
      Orq.mostrarAviso(aviso, 'Marque pelo menos uma opção antes de confirmar seu voto.', 'erro');
      return;
    }
    const botao = $('botaoVotar');
    botao.disabled = true;
    botao.textContent = 'Enviando voto…';
    try {
      if (demo) {
        Demo.votar(escolhidas);
      } else {
        await Orq.api(
          'POST',
          `/api/salas/${encodeURIComponent(codigo)}/votar`,
          { participante_id: creds.participante_id, opcoes: escolhidas },
          creds.token
        );
      }
      Orq.mostrarAviso(aviso, 'Voto registrado!', 'ok');
      await carregar();
      if (salaAtual && salaAtual.status === 'orquestrado') {
        $('secaoResultado').focus();
        $('secaoResultado').scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    } catch (e) {
      Orq.mostrarAviso(aviso, e.message, 'erro');
    } finally {
      botao.disabled = false;
      botao.textContent = '🗳️ Confirmar meu voto';
    }
  });

  $('botaoFecharVotacao').addEventListener('click', async () => {
    const botao = $('botaoFecharVotacao');
    botao.disabled = true;
    try {
      if (demo) {
        Demo.fecharVotacao();
      } else {
        await Orq.api('POST', `/api/salas/${encodeURIComponent(codigo)}/fechar-votacao`, undefined, creds.token_organizador);
      }
      await carregar();
      $('secaoResultado').focus();
      $('secaoResultado').scrollIntoView({ behavior: 'smooth', block: 'start' });
    } catch (e) {
      Orq.mostrarAviso($('avisoVoto'), e.message, 'erro');
      botao.disabled = false;
    }
  });

  Orq.aoMudarAba((aba) => { if (aba === 'sala') carregar(); });
})();
