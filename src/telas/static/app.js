/* Aba 1 (/app): criar sala e gerar o link de convite (RF-03, RF-04). */
'use strict';

(() => {
  const $ = (id) => document.getElementById(id);

  $('formCriar').addEventListener('submit', async (ev) => {
    ev.preventDefault();
    const organizador = $('organizador').value.trim();
    const nomeRole = $('nomeRole').value.trim();
    const maior = $('criarMaiorIdade').checked;
    const aviso = $('avisoCriar');

    for (const [campo, ok] of [[$('organizador'), !!organizador], [$('nomeRole'), !!nomeRole]]) {
      campo.setAttribute('aria-invalid', ok ? 'false' : 'true');
    }
    if (!organizador || !nomeRole) {
      Orq.mostrarAviso(aviso, 'Preencha seu nome e o nome do rolê.', 'erro');
      return;
    }
    if (!maior) {
      Orq.mostrarAviso(aviso, 'O Orquestrador de Rolês é só para maiores de 18 anos.', 'erro');
      return;
    }

    const botao = $('botaoCriar');
    botao.disabled = true;
    botao.textContent = 'Criando…';
    Orq.mostrarAviso(aviso, '', 'info');
    try {
      const r = await Orq.api('POST', '/api/salas', { nome_role: nomeRole, organizador, maior_de_idade: true });
      // O token do organizador volta só agora: fica guardado neste aparelho para gerar sugestões e fechar a votação.
      Orq.salvarCredenciais(r.codigo, { token_organizador: r.token_organizador, nome_sugerido: organizador });
      Orq.definirCodigoAtivo(r.codigo);
      mostrarConvite(r.codigo, nomeRole);
    } catch (e) {
      Orq.mostrarAviso(aviso, e.message, 'erro');
    } finally {
      botao.disabled = false;
      botao.textContent = 'Criar Sala';
    }
  });

  function mostrarConvite(codigo, nomeRole) {
    const link = Orq.linkConvite(codigo);
    const texto = `Bora pro rolê "${nomeRole}"? Entra na sala e conta, em segredo, de onde você sai, quando pode e quanto quer gastar: ${link}`;
    $('codigoSala').textContent = codigo;
    $('linkConvite').textContent = link;
    $('botaoWhatsApp').href = Orq.linkWhatsApp(texto);
    $('botaoMeusDados').onclick = () => Orq.irParaAba('perfil', codigo);
    $('botaoPainel').onclick = () => Orq.irParaAba('sala', codigo);
    $('botaoCopiar').onclick = async () => {
      const ok = await Orq.copiar(link);
      Orq.mostrarAviso($('avisoConvite'), ok ? 'Link copiado! Cole no grupo do WhatsApp.' : 'Não deu para copiar. Selecione o link acima.', ok ? 'ok' : 'erro');
    };
    $('secaoCriar').hidden = true;
    const secao = $('secaoConvite');
    secao.hidden = false;
    secao.focus();
    secao.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  $('formEntrar').addEventListener('submit', (ev) => {
    ev.preventDefault();
    let codigo = $('codigoEntrar').value.trim().toUpperCase().replace(/\s+/g, '');
    if (/^[A-Z0-9]{4}$/.test(codigo)) codigo = 'ROLE-' + codigo; // aceita só as 4 letras finais
    if (!/^[A-Z0-9-]{4,12}$/.test(codigo)) {
      $('codigoEntrar').setAttribute('aria-invalid', 'true');
      Orq.mostrarAviso($('avisoEntrar'), 'Digite o código do convite, por exemplo ROLE-7KQ2.', 'erro');
      return;
    }
    $('codigoEntrar').removeAttribute('aria-invalid');
    Orq.mostrarAviso($('avisoEntrar'), '', 'info');
    Orq.irParaAba('sala', codigo);
  });

  $('botaoVerDemo').addEventListener('click', () => Orq.irParaAba('sala', Orq.CODIGO_DEMO));
})();
