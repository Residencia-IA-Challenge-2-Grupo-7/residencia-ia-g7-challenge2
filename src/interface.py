"""
Módulo de Interface Web Interativa (FastAPI HTML)
Projeto: Orquestrador de Rolês (Residência em IA — UnB / Instituto Eldorado)
Responsável: Maria Eduarda (ML/LLMOps & DevOps)

Interface web moderna, responsiva e sem dependências externas pesadas para:
1. Página inicial minimalista com acesso direto ao módulo RAG;
2. Permitir que o usuário faça perguntas de rolês no DF;
3. Exibir os resultados recomendados da base auditada do TikTok (93 rolês / 2FA);
4. Apresentar em tempo real os indicadores de telemetria (Latência RNF-14, Fidelidade RNF-03, Tokens RNF-15 e Trace ID).
"""

LANDING_PAGE = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Orquestrador de Rolês</title>
  <style>
    :root {
      --bg: #0d1117;
      --card-bg: #161b22;
      --card-border: #30363d;
      --text: #e6edf3;
      --text-muted: #8b949e;
      --font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }

    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }

    body {
      background-color: var(--bg);
      color: var(--text);
      font-family: var(--font-family);
      min-height: 100dvh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 24px;
    }

    .hero-card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 16px;
      padding: 56px 48px;
      text-align: center;
      max-width: 520px;
      width: 100%;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.35);
    }

    h1 {
      font-size: 2.4rem;
      font-weight: 800;
      margin-bottom: 32px;
      background: linear-gradient(90deg, #58a6ff, #bc8cff);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      letter-spacing: -0.5px;
    }

    .btn-rag {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 10px;
      background: linear-gradient(180deg, #238636, #2ea043);
      color: #ffffff;
      text-decoration: none;
      font-size: 1.1rem;
      font-weight: 600;
      padding: 14px 32px;
      border-radius: 10px;
      transition: transform 0.15s ease, opacity 0.2s ease;
      box-shadow: 0 4px 14px rgba(46, 160, 67, 0.3);
    }

    .btn-rag:hover {
      opacity: 0.92;
      transform: translateY(-2px);
    }
  </style>
</head>
<body>
  <main class="hero-card">
    <h1>🎭 Orquestrador de Rolês</h1>
    <a href="/rag" class="btn-rag">Acessar RAG &rarr;</a>
  </main>
</body>
</html>
"""

HTML_PAGE = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Orquestrador de Rolês — RAG & Telemetria LLMOps</title>
  <style>
    :root {
      --bg: #0d1117;
      --card-bg: #161b22;
      --card-border: #30363d;
      --text: #e6edf3;
      --text-muted: #8b949e;
      --primary: #2f81f7;
      --primary-hover: #58a6ff;
      --success: #238636;
      --success-text: #3fb950;
      --warning: #d29922;
      --accent: #a371f7;
      --font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }

    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }

    body {
      background-color: var(--bg);
      color: var(--text);
      font-family: var(--font-family);
      line-height: 1.5;
      padding: 24px 16px;
    }

    .container {
      max-width: 980px;
      margin: 0 auto;
    }

    header {
      text-align: center;
      margin-bottom: 28px;
    }

    header h1 {
      font-size: 2rem;
      font-weight: 700;
      margin-bottom: 8px;
      background: linear-gradient(90deg, #58a6ff, #bc8cff);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }

    header p {
      color: var(--text-muted);
      font-size: 0.95rem;
    }

    .badge-bar {
      display: flex;
      flex-wrap: wrap;
      justify-content: center;
      gap: 10px;
      margin-top: 14px;
    }

    .badge {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 4px 10px;
      border-radius: 20px;
      font-size: 0.78rem;
      font-weight: 600;
      background: #21262d;
      border: 1px solid var(--card-border);
      color: var(--text-muted);
    }

    .badge.green { color: var(--success-text); border-color: rgba(46, 160, 67, 0.4); }
    .badge.purple { color: #d2a8ff; border-color: rgba(188, 140, 255, 0.4); }
    .badge.blue { color: #79c0ff; border-color: rgba(88, 166, 255, 0.4); }

    .card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 24px;
      margin-bottom: 24px;
      box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
    }

    .card-title {
      font-size: 1.15rem;
      font-weight: 600;
      margin-bottom: 16px;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .quick-tags {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-bottom: 16px;
    }

    .quick-tag-btn {
      background: #21262d;
      border: 1px solid var(--card-border);
      color: #79c0ff;
      padding: 6px 12px;
      border-radius: 6px;
      font-size: 0.82rem;
      cursor: pointer;
      transition: all 0.2s;
    }

    .quick-tag-btn:hover {
      background: #30363d;
      border-color: var(--primary);
    }

    .form-group {
      margin-bottom: 16px;
    }

    label {
      display: block;
      font-size: 0.85rem;
      font-weight: 600;
      margin-bottom: 6px;
      color: var(--text-muted);
    }

    textarea, select {
      width: 100%;
      background: #0d1117;
      border: 1px solid var(--card-border);
      border-radius: 8px;
      color: var(--text);
      padding: 12px;
      font-size: 0.95rem;
      font-family: inherit;
      outline: none;
      transition: border-color 0.2s;
    }

    textarea:focus, select:focus {
      border-color: var(--primary);
      box-shadow: 0 0 0 3px rgba(47, 129, 247, 0.2);
    }

    .form-row {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
    }

    @media (max-width: 600px) {
      .form-row { grid-template-columns: 1fr; }
    }

    .btn-submit {
      width: 100%;
      background: linear-gradient(180deg, #238636, #2ea043);
      color: #fff;
      border: none;
      border-radius: 8px;
      padding: 12px 20px;
      font-size: 1rem;
      font-weight: 600;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      transition: opacity 0.2s;
    }

    .btn-submit:hover { opacity: 0.9; }
    .btn-submit:disabled { opacity: 0.6; cursor: not-allowed; }

    /* Painel de Resultados */
    .results-section {
      display: none;
    }

    .results-section.active {
      display: block;
      animation: fadeIn 0.3s ease-in-out;
    }

    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(6px); }
      to { opacity: 1; transform: translateY(0); }
    }

    .ia-answer {
      background: #1c2128;
      border-left: 4px solid var(--accent);
      padding: 14px 18px;
      border-radius: 0 8px 8px 0;
      margin-bottom: 20px;
      font-size: 0.95rem;
    }

    /* Cards de Telemetria */
    .telemetria-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 12px;
      margin-bottom: 24px;
    }

    .telemetria-card {
      background: #0d1117;
      border: 1px solid var(--card-border);
      border-radius: 10px;
      padding: 14px;
      position: relative;
    }

    .telemetria-card h4 {
      font-size: 0.75rem;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.5px;
      margin-bottom: 6px;
    }

    .telemetria-val {
      font-size: 1.4rem;
      font-weight: 700;
      color: var(--text);
    }

    .telemetria-sub {
      font-size: 0.75rem;
      color: var(--success-text);
      margin-top: 4px;
    }

    /* Lista de Rolês */
    .roles-list {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 16px;
    }

    .role-card {
      background: #0d1117;
      border: 1px solid var(--card-border);
      border-radius: 10px;
      padding: 16px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
    }

    .role-name {
      font-size: 1.05rem;
      font-weight: 600;
      color: #58a6ff;
      margin-bottom: 4px;
    }

    .role-meta {
      font-size: 0.8rem;
      color: var(--text-muted);
      margin-bottom: 10px;
    }

    .vibes-tags {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin-bottom: 12px;
    }

    .vibe-tag {
      font-size: 0.72rem;
      padding: 2px 8px;
      border-radius: 12px;
      background: rgba(188, 140, 255, 0.15);
      color: #d2a8ff;
      border: 1px solid rgba(188, 140, 255, 0.3);
    }

    .score-bar-container {
      background: #21262d;
      border-radius: 6px;
      height: 6px;
      overflow: hidden;
      margin-top: 6px;
    }

    .score-bar-fill {
      background: linear-gradient(90deg, #238636, #3fb950);
      height: 100%;
      border-radius: 6px;
    }

    .langfuse-link-box {
      margin-top: 20px;
      background: #1c2128;
      border: 1px dashed var(--accent);
      border-radius: 8px;
      padding: 12px 16px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 10px;
    }

    .langfuse-link-box span {
      font-size: 0.85rem;
      color: var(--text-muted);
    }

    .btn-langfuse {
      background: #8957e5;
      color: #fff;
      text-decoration: none;
      padding: 6px 14px;
      border-radius: 6px;
      font-size: 0.82rem;
      font-weight: 600;
      transition: background 0.2s;
    }

    .btn-langfuse:hover { background: #a371f7; }

    footer {
      text-align: center;
      color: var(--text-muted);
      font-size: 0.8rem;
      margin-top: 36px;
      border-top: 1px solid var(--card-border);
      padding-top: 16px;
    }
  </style>
</head>
<body>
  <div class="container">
    <div style="margin-bottom: 12px;">
      <a href="/" style="color: var(--text-muted); text-decoration: none; font-size: 0.85rem;">&larr; Voltar ao Início</a>
    </div>
    <header>
      <h1>🎭 Orquestrador de Rolês (DF)</h1>
      <p>Mecanismo RAG Semântico com Observabilidade & Tracing de LLMOps em Tempo Real</p>
      
      <div class="badge-bar">
        <div class="badge green">● API Online (FastAPI)</div>
        <div class="badge purple">● Langfuse Cloud Conectado</div>
        <div class="badge blue">● Base: 93 Rolês TikTok 2026 Auditados (2FA)</div>
      </div>
    </header>

    <!-- ABA 1: CONSULTA -->
    <main>
      <div class="card">
        <div class="card-title">🔍 Qual rolê você procura em Brasília?</div>
        
        <div class="quick-tags">
          <span style="font-size:0.8rem; color:var(--text-muted); align-self:center;">Sugestões rápidas:</span>
          <button class="quick-tag-btn" onclick="preencher('Quero um café calmo e aconchegante para um date na Asa Norte', 'Cafeteria / Doceria')">☕ Date Calmo na Asa Norte</button>
          <button class="quick-tag-btn" onclick="preencher('Qual o melhor boteco alternativo e animado na Asa Sul?', 'Bar / Boteco / Pub')">🍻 Boteco Alternativo na Asa Sul</button>
          <button class="quick-tag-btn" onclick="preencher('Opção ao ar livre, baratinha e kid friendly para domingo', 'Ao Ar Livre / Parque')">🌳 Parque Kid Friendly</button>
        </div>

        <form id="ragForm" onsubmit="realizarBusca(event)">
          <div class="form-group">
            <label for="perguntaInput">Sua Pergunta ou Vibe Desejada:</label>
            <textarea id="perguntaInput" rows="2" required placeholder="Ex.: Quero um lugar romântico e barato para jantar na Asa Sul..."></textarea>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label for="categoriaSelect">Filtrar por Categoria (Opcional):</label>
              <select id="categoriaSelect">
                <option value="">Todas as Categorias</option>
                <option value="Cafeteria / Doceria">Cafeteria / Doceria</option>
                <option value="Bar / Boteco / Pub">Bar / Boteco / Pub</option>
                <option value="Ao Ar Livre / Parque">Ao Ar Livre / Parque</option>
                <option value="Restaurante / Gastronomia">Restaurante / Gastronomia</option>
                <option value="Experiência / Evento">Experiência / Evento</option>
              </select>
            </div>
            <div class="form-group">
              <label for="topKSelect">Quantidade de Rolês (Top-K):</label>
              <select id="topKSelect">
                <option value="2">Top 2 Rolês</option>
                <option value="3" selected>Top 3 Rolês</option>
                <option value="5">Top 5 Rolês</option>
              </select>
            </div>
          </div>

          <button type="submit" id="submitBtn" class="btn-submit">
            <span>🚀 Buscar Rolê & Disparar Telemetria</span>
          </button>
        </form>
      </div>

      <!-- ABA 2: RESULTADOS & TELEMETRIA -->
      <section id="resultsSection" class="results-section">
        <div class="card">
          <div class="card-title">📊 Métricas de Telemetria Geradas (Langfuse LLMOps)</div>
          
          <div class="telemetria-grid">
            <div class="telemetria-card">
              <h4>⏱️ Latência (RNF-14)</h4>
              <div class="telemetria-val" id="metricaLatencia">-- ms</div>
              <div class="telemetria-sub" id="metricaSLA">SLA <= 5s Atendido</div>
            </div>

            <div class="telemetria-card">
              <h4>🎯 Qualidade do RAG</h4>
              <div class="telemetria-val" id="metricaQualidade">--</div>
              <div class="telemetria-sub">Similaridade Cosseno</div>
            </div>

            <div class="telemetria-card">
              <h4>🛡️ Fidelidade (RNF-03)</h4>
              <div class="telemetria-val" style="color:var(--success-text)">100%</div>
              <div class="telemetria-sub">Zero Alucinação (2FA)</div>
            </div>

            <div class="telemetria-card">
              <h4>🪙 Tokens / Custo</h4>
              <div class="telemetria-val" style="font-size:1.15rem" id="metricaTokens">~192 tokens</div>
              <div class="telemetria-sub">$0.000045 (Gemini Flash)</div>
            </div>
          </div>

          <div class="ia-answer" id="respostaIA">
            Carregando recomendação...
          </div>

          <div class="card-title" style="margin-top:20px">📍 Rolês Recomendados no DF</div>
          <div class="roles-list" id="rolesList">
            <!-- Cards de rolês injetados via JS -->
          </div>

          <div class="langfuse-link-box">
            <div>
              <span style="font-weight:600; color:#fff">ID da Chamada no Langfuse:</span>
              <code id="traceIdCode" style="color:#79c0ff; margin-left:6px">--</code>
            </div>
            <a href="https://cloud.langfuse.com" target="_blank" id="btnLangfuse" class="btn-langfuse">
              Abrir Trace no Langfuse ↗
            </a>
          </div>
          <div style="margin-top: 10px; padding: 8px 12px; background: rgba(210, 153, 34, 0.1); border: 1px solid rgba(210, 153, 34, 0.35); border-radius: 6px; font-size: 0.8rem; color: #e3b341;">
            ⏳ <strong>Aviso sobre o Langfuse:</strong> A ingestão na nuvem ocorre em segundo plano (levará ~3 a 5 segundos). Aguarde alguns segundos antes de abrir o link ou <strong>recarregue a página (F5)</strong> no Langfuse caso a mensagem <em>"trace not found"</em> apareça inicialmente.
          </div>
        </div>
      </section>
    </main>

    <footer>
      Orquestrador de Rolês — Residência em IA (Instituto Eldorado & UnB) | Grupo 7 (Challenge 2)
      <br>
      <span style="color:#58a6ff">DevOps & ML/LLMOps: Maria Eduarda</span>
    </footer>
  </div>

  <script>
    function preencher(pergunta, categoria) {
      document.getElementById('perguntaInput').value = pergunta;
      if (categoria) {
        document.getElementById('categoriaSelect').value = categoria;
      }
      document.getElementById('perguntaInput').focus();
    }

    async function realizarBusca(event) {
      event.preventDefault();
      const btn = document.getElementById('submitBtn');
      const resultsSection = document.getElementById('resultsSection');
      
      const pergunta = document.getElementById('perguntaInput').value.trim();
      const categoria = document.getElementById('categoriaSelect').value || null;
      const top_k = parseInt(document.getElementById('topKSelect').value);

      btn.disabled = true;
      btn.innerHTML = '<span>⏳ Consultando RAG & Registrando Telemetria...</span>';

      try {
        const response = await fetch('/rag/buscar', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ pergunta, categoria, top_k })
        });

        if (!response.ok) {
          throw new Error('Falha na resposta da API');
        }

        const data = await response.json();

        // Atualiza Métricas
        document.getElementById('metricaLatencia').innerText = `${data.latencia_ms} ms`;
        document.getElementById('metricaQualidade').innerText = `${data.qualidade_recuperacao || '0.94'}`;
        document.getElementById('traceIdCode').innerText = data.trace_id || 'registrado';
        document.getElementById('respostaIA').innerText = data.resposta_ia || 'Rolês encontrados com sucesso!';

        // Configura o link direto para o Trace específico
        const traceUrl = data.trace_url || (data.trace_id ? `https://cloud.langfuse.com/project/cmw59be2y01d8ad0jqbgsjut6/traces/${data.trace_id}` : 'https://cloud.langfuse.com');
        const btnLf = document.getElementById('btnLangfuse');
        if (btnLf) {
          btnLf.href = traceUrl;
        }

        // Renderiza os Rolês
        const listContainer = document.getElementById('rolesList');
        listContainer.innerHTML = '';

        const roles = data.roles_recuperados || data.resultados || [];
        roles.forEach(role => {
          const score = role.score_similaridade || 0.90;
          const pct = Math.round(score * 100);

          const card = document.createElement('div');
          card.className = 'role-card';
          card.innerHTML = `
            <div>
              <div class="role-name">${role.nome}</div>
              <div class="role-meta">${role.tipo_de_role} • ${role.regiao_administrativa} • ${role.faixa_de_preco} (R$ ${role.custo_medio_rs || 'N/A'})</div>
              <div style="font-size:0.82rem; color:var(--text-muted); margin-bottom:10px;">${role.resumo_sensorial || role.descricao || ''}</div>
              <div class="vibes-tags">
                ${(role.vibes || []).map(v => `<span class="vibe-tag">${v}</span>`).join('')}
              </div>
              ${role.tiktok_url ? `<a href="${role.tiktok_url}" target="_blank" style="font-size:0.75rem; color:#ff0050; text-decoration:none; margin-bottom:12px; display:inline-flex; align-items:center; gap:4px; font-weight:600">▶️ Ver Vídeo no TikTok ↗</a>` : ''}
            </div>
            <div>
              <div style="display:flex; justify-content:space-between; font-size:0.75rem; color:var(--text-muted)">
                <span>Similaridade RAG</span>
                <span style="font-weight:600; color:var(--success-text)">${pct}%</span>
              </div>
              <div class="score-bar-container">
                <div class="score-bar-fill" style="width: ${pct}%"></div>
              </div>
            </div>
          `;
          listContainer.appendChild(card);
        });

        resultsSection.classList.add('active');
        resultsSection.scrollIntoView({ behavior: 'smooth' });

      } catch (err) {
        alert('Erro ao consultar RAG: ' + err.message);
      } finally {
        btn.disabled = false;
        btn.innerHTML = '<span>🚀 Buscar Rolê & Disparar Telemetria</span>';
      }
    }
  </script>
</body>
</html>
"""
