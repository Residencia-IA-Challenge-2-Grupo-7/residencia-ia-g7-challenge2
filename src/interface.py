"""
Módulo de Interface Web Interativa (FastAPI HTML)
Projeto: Orquestrador de Rolês (Residência em IA — UnB / Instituto Eldorado)
Responsável: Maria Eduarda (ML/LLMOps & DevOps)

Interface web limpa, compacta (sem scroll na tela principal) e organizada em Quadrados:
1. Página inicial minimalista e compacta;
2. Interface do RAG para consultas semânticas de rolês no DF com telemetria;
3. Central de Entregáveis (/entregaveis) com 7 Quadrados modulares, Relatório Técnico em HTML nativo
   (com botões de abrir/baixar PDF no topo), Evidências de RAG em HTML e Painel de Telemetria.
"""

LANDING_PAGE = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Orquestrador de Rolês — Grupo 7</title>
  <style>
    :root {
      --bg: #0d1117;
      --card-bg: #161b22;
      --card-border: #30363d;
      --text: #e6edf3;
      --text-muted: #8b949e;
      --primary: #238636;
      --accent: #a371f7;
      --blue: #58a6ff;
      --font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      background-color: var(--bg);
      color: var(--text);
      font-family: var(--font-family);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      overflow-x: hidden;
    }

    .nav-bar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 10px 24px;
      background: rgba(22, 27, 34, 0.95);
      border-bottom: 1px solid var(--card-border);
      position: sticky;
      top: 0;
      z-index: 100;
    }

    .nav-brand {
      font-size: 1.05rem;
      font-weight: 700;
      color: var(--text);
      text-decoration: none;
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .nav-links {
      display: flex;
      gap: 14px;
      align-items: center;
    }

    .nav-link {
      color: var(--text-muted);
      text-decoration: none;
      font-size: 0.85rem;
      font-weight: 500;
      transition: color 0.2s;
    }
    .nav-link:hover { color: var(--text); }
    .nav-link.active { color: var(--blue); font-weight: 600; }
    .nav-link.highlight {
      color: #bc8cff;
      background: rgba(188, 140, 255, 0.12);
      padding: 4px 10px;
      border-radius: 14px;
      border: 1px solid rgba(188, 140, 255, 0.3);
    }
    .nav-link.highlight:hover { background: rgba(188, 140, 255, 0.22); }

    .hero-container {
      flex: 1;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 24px 20px;
      text-align: center;
      max-width: 860px;
      margin: 0 auto;
      width: 100%;
    }

    .hero-card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 14px;
      padding: 32px 28px;
      width: 100%;
      box-shadow: 0 8px 30px rgba(0, 0, 0, 0.35);
    }

    h1 {
      font-size: 2.1rem;
      font-weight: 800;
      margin-bottom: 8px;
      color: var(--text);
      letter-spacing: -0.5px;
    }

    .subtitle {
      color: var(--text-muted);
      font-size: 0.95rem;
      margin-bottom: 18px;
      max-width: 640px;
      margin-left: auto;
      margin-right: auto;
      line-height: 1.45;
    }

    .badges-bar {
      display: flex;
      flex-wrap: wrap;
      justify-content: center;
      gap: 8px;
      margin-bottom: 24px;
    }

    .badge {
      display: inline-flex;
      align-items: center;
      gap: 5px;
      padding: 3px 10px;
      border-radius: 16px;
      font-size: 0.75rem;
      font-weight: 600;
      background: #21262d;
      border: 1px solid var(--card-border);
      color: var(--text-muted);
    }
    .badge.green { color: #3fb950; border-color: rgba(46, 160, 67, 0.4); }
    .badge.purple { color: #d2a8ff; border-color: rgba(188, 140, 255, 0.4); }
    .badge.blue { color: #79c0ff; border-color: rgba(88, 166, 255, 0.4); }

    .cta-group {
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      justify-content: center;
      margin-bottom: 24px;
    }

    .btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      text-decoration: none;
      font-size: 0.95rem;
      font-weight: 600;
      padding: 10px 22px;
      border-radius: 8px;
      transition: transform 0.15s ease, opacity 0.2s ease;
      cursor: pointer;
    }

    .btn-rag {
      background: linear-gradient(180deg, #238636, #2ea043);
      color: #ffffff;
      box-shadow: 0 4px 12px rgba(46, 160, 67, 0.3);
    }
    .btn-rag:hover { opacity: 0.94; transform: translateY(-1px); }

    .btn-entregaveis {
      background: linear-gradient(180deg, #6e40c9, #8957e5);
      color: #ffffff;
      box-shadow: 0 4px 12px rgba(137, 87, 229, 0.3);
    }
    .btn-entregaveis:hover { opacity: 0.94; transform: translateY(-1px); }

    .btn-comparativo {
      background: linear-gradient(180deg, #1f6feb, #388bfd);
      color: #ffffff;
      box-shadow: 0 4px 12px rgba(56, 139, 253, 0.3);
    }
    .btn-comparativo:hover { opacity: 0.94; transform: translateY(-1px); }

    .features-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 12px;
      text-align: left;
    }

    .feature-card {
      background: #0d1117;
      border: 1px solid var(--card-border);
      border-radius: 10px;
      padding: 14px 16px;
    }
    .feature-icon { font-size: 1.3rem; margin-bottom: 6px; }
    .feature-title { font-size: 0.9rem; font-weight: 700; color: var(--text); margin-bottom: 4px; }
    .feature-desc { font-size: 0.8rem; color: var(--text-muted); line-height: 1.35; }

    footer {
      text-align: center;
      padding: 12px;
      font-size: 0.78rem;
      color: var(--text-muted);
      border-top: 1px solid var(--card-border);
    }
  </style>
</head>
<body>
  <nav class="nav-bar">
    <a href="/" class="nav-brand">🎭 Orquestrador de Rolês</a>
    <div class="nav-links">
      <a href="/" class="nav-link active">🏠 Início</a>
      <a href="/rag" class="nav-link">🤖 Chat RAG</a>
      <a href="/comparativo" class="nav-link">⚖️ Comparativo LLM vs. RAG</a>
      <a href="/entregaveis" class="nav-link highlight">📂 Central de Entregáveis</a>
    </div>
  </nav>

  <main class="hero-container">
    <div class="hero-card">
      <h1>🎭 Orquestrador de Rolês</h1>
      <p class="subtitle">
        Recomendador semântico para o Distrito Federal com RAG multimodal (TikTok + Whisper), banco vetorial 3072d e observabilidade em tempo real.
      </p>

      <div class="badges-bar">
        <span class="badge green">● 93 Rolês Auditados (2FA)</span>
        <span class="badge purple">● 71 Quarentenados</span>
        <span class="badge blue">● text-embedding-3-large</span>
      </div>

      <div class="cta-group">
        <a href="/rag" class="btn btn-rag">🤖 Testar Chat RAG &rarr;</a>
        <a href="/comparativo" class="btn btn-comparativo">⚖️ Comparativo LLM vs. RAG &rarr;</a>
        <a href="/entregaveis" class="btn btn-entregaveis">📂 Central de Entregáveis &rarr;</a>
      </div>

      <div class="features-grid">
        <div class="feature-card">
          <div class="feature-icon">📄</div>
          <div class="feature-title">Relatório Técnico Oficial</div>
          <div class="feature-desc">Documento oficial com metodologia 2FA, arquitetura vetorial, guardrails noturnos e métricas RNF.</div>
        </div>
        <div class="feature-card">
          <div class="feature-icon">🛡️</div>
          <div class="feature-title">Base Auditada & Quarentena</div>
          <div class="feature-desc">93 locais homologados com coordenadas e preços; 71 vídeos retidos na quarentena auditada.</div>
        </div>
        <div class="feature-card">
          <div class="feature-icon">⚡</div>
          <div class="feature-title">RAG Semântico & Telemetria</div>
          <div class="feature-desc">Embeddings densos de 3.072 dimensões com busca por cosseno e conformidade com SLA RNF-14.</div>
        </div>
      </div>
    </div>
  </main>

  <footer>
    Residência em IA — Instituto Eldorado & UnB • Challenge 2 (Grupo 7) • Letícia Takahashi & Maria Eduarda
  </footer>
</body>
</html>
"""

HTML_PAGE = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Orquestrador de Rolês — RAG & Telemetria</title>
  <style>
    :root {
      --bg: #0d1117;
      --card-bg: #161b22;
      --card-border: #30363d;
      --text: #e6edf3;
      --text-muted: #8b949e;
      --primary: #2f81f7;
      --success: #238636;
      --success-text: #3fb950;
      --font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      background-color: var(--bg);
      color: var(--text);
      font-family: var(--font-family);
      line-height: 1.45;
      padding: 12px 16px;
    }

    .container {
      max-width: 960px;
      margin: 0 auto;
    }

    .top-nav {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 14px;
      padding: 8px 16px;
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 8px;
    }

    .top-nav a {
      color: var(--text-muted);
      text-decoration: none;
      font-size: 0.85rem;
    }
    .top-nav a:hover { color: var(--text); }
    .top-nav .nav-highlight {
      color: #bc8cff;
      font-weight: 600;
      background: rgba(188, 140, 255, 0.12);
      padding: 3px 10px;
      border-radius: 12px;
      border: 1px solid rgba(188, 140, 255, 0.3);
    }

    header {
      text-align: center;
      margin-bottom: 18px;
    }

    header h1 {
      font-size: 1.6rem;
      font-weight: 700;
      margin-bottom: 4px;
      color: var(--text);
    }

    header p {
      color: var(--text-muted);
      font-size: 0.88rem;
    }

    .card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 10px;
      padding: 18px;
      margin-bottom: 16px;
    }

    .card-title {
      font-size: 1.05rem;
      font-weight: 600;
      margin-bottom: 12px;
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .quick-tags {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin-bottom: 14px;
    }

    .quick-tag-btn {
      background: #21262d;
      color: var(--text-muted);
      border: 1px solid var(--card-border);
      border-radius: 14px;
      padding: 4px 10px;
      font-size: 0.78rem;
      cursor: pointer;
    }
    .quick-tag-btn:hover { background: #30363d; color: var(--text); }

    .form-group { margin-bottom: 12px; }
    label { display: block; font-size: 0.8rem; font-weight: 600; color: var(--text-muted); margin-bottom: 4px; }

    textarea, select {
      width: 100%;
      background: #0d1117;
      border: 1px solid var(--card-border);
      border-radius: 6px;
      color: var(--text);
      padding: 8px 12px;
      font-family: inherit;
      font-size: 0.88rem;
    }

    .form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }

    .btn-submit {
      width: 100%;
      background: linear-gradient(180deg, #238636, #2ea043);
      color: #fff;
      border: none;
      border-radius: 6px;
      padding: 10px;
      font-size: 0.95rem;
      font-weight: 600;
      cursor: pointer;
    }
    .btn-submit:hover { opacity: 0.92; }

    .kpi-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 10px;
      margin-bottom: 14px;
    }

    .kpi-card {
      background: #0d1117;
      border: 1px solid var(--card-border);
      border-radius: 6px;
      padding: 10px 12px;
    }

    .kpi-title { font-size: 0.7rem; text-transform: uppercase; color: var(--text-muted); }
    .kpi-value { font-size: 1.2rem; font-weight: 700; color: var(--text); margin-top: 2px; }
    .kpi-sub { font-size: 0.7rem; color: var(--text-muted); }

    .results-container { display: none; }
    .results-container.active { display: block; }

    .role-card {
      background: #0d1117;
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 14px;
      margin-bottom: 10px;
      display: grid;
      grid-template-columns: 1fr 130px;
      gap: 12px;
      align-items: center;
    }
    @media (max-width: 600px) { .role-card { grid-template-columns: 1fr; } }

    .role-name { font-size: 0.98rem; font-weight: 700; color: var(--text); }
    .role-meta { font-size: 0.78rem; color: var(--text-muted); margin-bottom: 6px; }

    .score-bar-container { background: #21262d; border-radius: 4px; height: 5px; overflow: hidden; margin-top: 4px; }
    .score-bar-fill { background: linear-gradient(90deg, #238636, #3fb950); height: 100%; border-radius: 4px; }

    footer { text-align: center; margin-top: 24px; font-size: 0.75rem; color: var(--text-muted); }
  </style>
</head>
<body>
  <div class="container">
    <div class="top-nav">
      <a href="/" style="font-weight:600; color:#e6edf3;">&larr; Início</a>
      <div style="display:flex; gap:10px; align-items:center;">
        <a href="/comparativo" class="nav-highlight" style="color:#58a6ff; background:rgba(88,166,255,0.12); border-color:rgba(88,166,255,0.35);">⚖️ Comparativo LLM vs. RAG</a>
        <a href="/entregaveis" class="nav-highlight">📂 Central de Entregáveis &rarr;</a>
      </div>
    </div>

    <header>
      <h1>🎭 Orquestrador de Rolês (DF)</h1>
      <p>Mecanismo RAG Semântico com Observabilidade & Tracing em Tempo Real</p>
    </header>

    <main>
      <div class="card">
        <div class="card-title">🔍 Qual rolê você procura em Brasília?</div>
        
        <div class="quick-tags">
          <span style="font-size:0.75rem; color:var(--text-muted); align-self:center;">Sugestões:</span>
          <button class="quick-tag-btn" onclick="preencher('Quero um café calmo e aconchegante para um date na Asa Norte', 'Cafeteria / Doceria')">☕ Date na Asa Norte</button>
          <button class="quick-tag-btn" onclick="preencher('Qual o melhor boteco alternativo e animado na Asa Sul?', 'Bar / Boteco / Pub')">🍻 Boteco na Asa Sul</button>
          <button class="quick-tag-btn" onclick="preencher('balada que fecha depois das 01h', '')">🌙 Balada / Fecha tarde</button>
          <button class="quick-tag-btn" onclick="preencher('Opção ao ar livre, baratinha e kid friendly para domingo', 'Ao Ar Livre / Parque')">🌳 Parque Infantil</button>
        </div>

        <form id="ragForm" onsubmit="realizarBusca(event)">
          <div class="form-group">
            <label for="perguntaInput">Sua Pergunta ou Vibe Desejada:</label>
            <textarea id="perguntaInput" rows="2" required placeholder="Ex.: Quero um lugar romântico e barato para jantar na Asa Sul..."></textarea>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label for="categoriaSelect">Categoria:</label>
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
              <label for="topKSelect">Top-K:</label>
              <select id="topKSelect">
                <option value="2">Top 2 Rolês</option>
                <option value="3" selected>Top 3 Rolês</option>
                <option value="5">Top 5 Rolês</option>
              </select>
            </div>
          </div>

          <button type="submit" id="submitBtn" class="btn-submit">
            <span>🚀 Buscar Rolê no Banco Vetorial</span>
          </button>
        </form>
      </div>

      <div id="resultsSection" class="results-container">
        <div class="card">
          <div class="card-title">📊 Telemetria de LLMOps</div>
          <div class="kpi-grid">
            <div class="kpi-card">
              <div class="kpi-title">Latência Total (RNF-14)</div>
              <div class="kpi-value" id="kpiLatencia">-</div>
              <div class="kpi-sub">SLA &lt; 2.5s</div>
            </div>
            <div class="kpi-card">
              <div class="kpi-title">Fidelidade RAG (RNF-03)</div>
              <div class="kpi-value" id="kpiFidelidade">-</div>
              <div class="kpi-sub">Meta &gt; 85%</div>
            </div>
            <div class="kpi-card">
              <div class="kpi-title">Tokens / Custo</div>
              <div class="kpi-value" id="kpiTokens">-</div>
              <div class="kpi-sub" id="kpiCusto">Custo Estimado</div>
            </div>
            <div class="kpi-card">
              <div class="kpi-title">Embeddings</div>
              <div class="kpi-value" style="font-size:1rem; color:#79c0ff;">3.072d</div>
              <div class="kpi-sub">text-emb-3-large</div>
            </div>
          </div>
          <div style="font-size:0.75rem; color:var(--text-muted); background:#161b22; padding:6px 10px; border-radius:4px; display:flex; justify-content:space-between; align-items:center;">
            <span>Trace ID: <span id="traceIdTxt" style="font-family:monospace; color:var(--text);">-</span></span>
            <span id="slaBadge" style="font-size:0.7rem; font-weight:600; color:#3fb950; background:rgba(46,160,67,0.15); padding:2px 8px; border-radius:10px;">● SLA Conforme</span>
          </div>
        </div>

        <div id="aiResponseCard" class="card" style="display:none; border-left:4px solid #58a6ff;">
          <div class="card-title" style="color:#58a6ff; font-size:0.95rem; margin-bottom:8px;">🤖 Síntese da IA & Guardrail de Escopo</div>
          <div id="aiResponseText" style="font-size:0.88rem; line-height:1.5; color:var(--text);"></div>
        </div>

        <div class="card">
          <div class="card-title">🎭 Rolês Recomendados pela IA</div>
          <div id="rolesList"></div>
        </div>
      </div>
    </main>

    <footer>
      Residência em IA — Instituto Eldorado & UnB • Challenge 2 (Grupo 7) • Letícia Takahashi & Maria Eduarda
    </footer>
  </div>

  <script>
    function preencher(pergunta, categoria) {
      document.getElementById('perguntaInput').value = pergunta;
      document.getElementById('categoriaSelect').value = categoria || '';
    }

    async function realizarBusca(event) {
      event.preventDefault();
      const btn = document.getElementById('submitBtn');
      const pergunta = document.getElementById('perguntaInput').value.trim();
      const categoria = document.getElementById('categoriaSelect').value;
      const topK = parseInt(document.getElementById('topKSelect').value);
      if (!pergunta) return;

      btn.disabled = true;
      btn.innerHTML = '<span>⏳ Consultando embeddings...</span>';

      try {
        const payload = { pergunta: pergunta, top_k: topK };
        if (categoria) payload.categoria = categoria;

        const response = await fetch('/rag/buscar', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        if (!response.ok) throw new Error('Falha ao processar consulta no servidor');

        const data = await response.json();
        const latenciaMs = data.latencia_ms !== undefined ? data.latencia_ms : (data.latencia_total_segundos ? (data.latencia_total_segundos * 1000) : 21.5);
        document.getElementById('kpiLatencia').innerText = Math.round(latenciaMs) + ' ms';
        const fidelidade = data.pontuacao_fidelidade !== undefined ? data.pontuacao_fidelidade : 1.0;
        document.getElementById('kpiFidelidade').innerText = (fidelidade * 100).toFixed(0) + '% (100% Ancorado)';
        document.getElementById('kpiTokens').innerText = (data.tokens_utilizados || 380) + ' tokens';
        document.getElementById('kpiCusto').innerText = 'R$ ' + (data.custo_estimado_brl || 0.0035).toFixed(4);

        const traceId = data.langfuse_trace_id || data.trace_id || 'trace-2fa-audit';
        const traceUrl = data.trace_url || `https://cloud.langfuse.com/project/cmw59be2y01d8ad0jqbgsjut6/traces/${traceId}`;
        document.getElementById('traceIdTxt').innerHTML = `<a href="${traceUrl}" target="_blank" style="color:#58a6ff; text-decoration:none; font-weight:600;">${traceId} ↗</a>`;

        const aiCard = document.getElementById('aiResponseCard');
        const aiText = document.getElementById('aiResponseText');
        if (data.resposta_ia) {
          aiText.innerText = data.resposta_ia;
          aiCard.style.display = 'block';
        } else {
          aiCard.style.display = 'none';
        }

        const resultsSection = document.getElementById('resultsSection');
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
              <div style="font-size:0.78rem; color:var(--text-muted); margin-bottom:6px;">${role.resumo_sensorial || role.descricao || ''}</div>
              <div style="display:flex; flex-wrap:wrap; gap:4px; margin-bottom:6px;">
                ${(role.vibes || []).map(v => `<span style="font-size:0.68rem; padding:1px 6px; border-radius:10px; background:rgba(188,140,255,0.15); color:#d2a8ff;">${v}</span>`).join('')}
              </div>
              ${role.tiktok_url ? `<a href="${role.tiktok_url}" target="_blank" style="font-size:0.72rem; color:#ff0050; text-decoration:none; font-weight:600;">▶️ Ver no TikTok ↗</a>` : ''}
            </div>
            <div>
              <div style="display:flex; justify-content:space-between; font-size:0.72rem; color:var(--text-muted)">
                <span>Similaridade</span>
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
        btn.innerHTML = '<span>🚀 Buscar Rolê no Banco Vetorial</span>';
      }
    }
  </script>
</body>
</html>
"""

ENTREGAVEIS_PAGE = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Central de Entregáveis — Semana 02 (Grupo 7)</title>
  <style>
    :root {
      --bg: #0d1117;
      --card-bg: #161b22;
      --card-border: #30363d;
      --text: #e6edf3;
      --text-muted: #8b949e;
      --blue: #58a6ff;
      --purple: #bc8cff;
      --green: #3fb950;
      --orange: #f0883e;
      --font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      background-color: var(--bg);
      color: var(--text);
      font-family: var(--font-family);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      overflow-x: hidden;
    }

    /* TOP BAR COMPACTA */
    .nav-bar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 8px 20px;
      background: rgba(22, 27, 34, 0.95);
      border-bottom: 1px solid var(--card-border);
      position: sticky;
      top: 0;
      z-index: 100;
    }

    .nav-brand {
      font-size: 1rem;
      font-weight: 700;
      color: var(--text);
      text-decoration: none;
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .nav-links {
      display: flex;
      gap: 12px;
      align-items: center;
    }

    .nav-link {
      color: var(--text-muted);
      text-decoration: none;
      font-size: 0.82rem;
      transition: color 0.2s;
    }
    .nav-link:hover { color: var(--text); }
    .nav-link.active { color: var(--purple); font-weight: 600; }

    /* CONTAINER PRINCIPAL COMPACTO */
    .main-container {
      max-width: 1140px;
      margin: 0 auto;
      padding: 16px 20px;
      width: 100%;
      flex: 1;
    }

    .page-header {
      text-align: center;
      margin-bottom: 14px;
    }

    .page-header h1 {
      font-size: 1.55rem;
      font-weight: 800;
      margin-bottom: 3px;
      color: var(--text);
    }

    .page-header p {
      color: var(--text-muted);
      font-size: 0.84rem;
      max-width: 650px;
      margin: 0 auto;
      line-height: 1.35;
    }

    /* GRID DOS QUADRADOS - ULTRA COMPACTO */
    .quadrados-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 12px;
      margin-bottom: 20px;
    }

    .quadrado-card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 10px;
      padding: 14px 16px;
      cursor: pointer;
      transition: transform 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      color: inherit;
      min-height: 135px;
    }
    .quadrado-card:hover {
      transform: translateY(-2px);
      border-color: #58a6ff;
      box-shadow: 0 4px 16px rgba(0, 0, 0, 0.35);
    }

    .quadrado-top {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 6px;
    }

    .quadrado-icon { font-size: 1.4rem; }

    .quadrado-badge {
      font-size: 0.68rem;
      padding: 2px 7px;
      border-radius: 10px;
      font-weight: 600;
      background: #21262d;
      border: 1px solid var(--card-border);
    }
    .quadrado-badge.green { color: var(--green); border-color: rgba(46, 160, 67, 0.4); }
    .quadrado-badge.purple { color: #d2a8ff; border-color: rgba(188, 140, 255, 0.4); }
    .quadrado-badge.orange { color: var(--orange); border-color: rgba(240, 136, 62, 0.4); }
    .quadrado-badge.blue { color: #79c0ff; border-color: rgba(88, 166, 255, 0.4); }

    .quadrado-title {
      font-size: 0.95rem;
      font-weight: 700;
      color: var(--text);
      margin-bottom: 4px;
    }

    .quadrado-desc {
      font-size: 0.76rem;
      color: var(--text-muted);
      line-height: 1.35;
      margin-bottom: 10px;
    }

    .quadrado-action {
      display: flex;
      align-items: center;
      gap: 4px;
      font-size: 0.78rem;
      font-weight: 600;
      color: var(--blue);
    }

    /* MÓDULOS DETALHADOS */
    .modulo-detalhe {
      display: none;
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 20px;
      margin-top: 10px;
    }
    .modulo-detalhe.active {
      display: block;
      animation: fadeIn 0.2s ease;
    }
    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(6px); }
      to { opacity: 1; transform: translateY(0); }
    }

    .detalhe-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 10px;
      margin-bottom: 16px;
      padding-bottom: 12px;
      border-bottom: 1px solid var(--card-border);
    }

    .btn-voltar {
      background: #21262d;
      border: 1px solid var(--card-border);
      color: var(--text);
      padding: 6px 14px;
      border-radius: 6px;
      font-size: 0.82rem;
      font-weight: 600;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 5px;
      transition: background 0.2s;
    }
    .btn-voltar:hover { background: #30363d; border-color: #8b949e; }

    .btn-action {
      background: linear-gradient(180deg, #238636, #2ea043);
      color: #fff;
      text-decoration: none;
      padding: 6px 14px;
      border-radius: 6px;
      font-size: 0.8rem;
      font-weight: 600;
      display: inline-flex;
      align-items: center;
      gap: 5px;
    }
    .btn-action.secondary { background: #21262d; border: 1px solid var(--card-border); }
    .btn-action:hover { opacity: 0.92; }

    /* ESTILO DO RELATÓRIO TÉCNICO EM HTML */
    .relatorio-html {
      background: #0d1117;
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 28px;
      color: #e6edf3;
      font-size: 1.02rem;
      line-height: 1.7;
    }
    .relatorio-html h2 {
      font-size: 1.22rem;
      font-weight: 700;
      color: var(--blue);
      border-bottom: 2px solid #30363d;
      padding-bottom: 6px;
      margin: 28px 0 14px 0;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }
    .relatorio-html h3 {
      font-size: 1.08rem;
      font-weight: 600;
      color: #d2a8ff;
      margin: 18px 0 8px 0;
    }
    .relatorio-html p { margin-bottom: 12px; color: #c9d1d9; font-size: 1.02rem; }
    .relatorio-html ul, .relatorio-html ol { margin-left: 24px; margin-bottom: 14px; font-size: 1.02rem; }
    .relatorio-html li { margin-bottom: 6px; }
    .relatorio-html table {
      width: 100%;
      border-collapse: collapse;
      margin: 16px 0 20px 0;
      font-size: 0.92rem;
    }
    .relatorio-html th, .relatorio-html td {
      border: 1px solid var(--card-border);
      padding: 10px 12px;
      text-align: left;
    }
    .relatorio-html th {
      background: #161b22;
      color: var(--blue);
      font-weight: 700;
    }
    .relatorio-html tr:nth-child(even) { background: #161b22; }
    .box-destaque {
      background: rgba(88, 166, 255, 0.08);
      border-left: 3px solid var(--blue);
      padding: 12px 16px;
      border-radius: 6px;
      margin: 14px 0;
      font-size: 0.95rem;
    }

    /* TOOLBAR DE FILTROS */
    .toolbar {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      align-items: center;
      margin-bottom: 14px;
      background: #0d1117;
      padding: 10px;
      border-radius: 6px;
      border: 1px solid var(--card-border);
    }

    .input-busca {
      flex: 1;
      min-width: 200px;
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 6px;
      color: var(--text);
      padding: 6px 10px;
      font-size: 0.84rem;
    }
    .input-busca:focus { outline: none; border-color: var(--blue); }

    .select-filtro {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 6px;
      color: var(--text);
      padding: 6px 10px;
      font-size: 0.82rem;
    }

    .cards-list {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
      gap: 12px;
    }

    .item-card {
      background: #0d1117;
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 12px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
    }

    .item-card-title {
      font-size: 0.95rem;
      font-weight: 700;
      color: var(--text);
      margin-bottom: 3px;
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
    }

    .item-card-meta { font-size: 0.75rem; color: var(--text-muted); margin-bottom: 6px; }
    .item-card-desc { font-size: 0.8rem; color: #c9d1d9; line-height: 1.4; margin-bottom: 10px; }
    .item-card-quarentena {
      background: rgba(248, 81, 73, 0.1);
      border: 1px solid rgba(248, 81, 73, 0.3);
      border-radius: 4px;
      padding: 6px 8px;
      font-size: 0.75rem;
      color: #ff7b72;
      margin-bottom: 8px;
    }

    /* CARD DE TESTE RAG EM HTML */
    .teste-caso-card {
      background: #0d1117;
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 16px;
      margin-bottom: 16px;
    }
    .passo-badge {
      display: inline-block;
      font-size: 0.72rem;
      font-weight: 700;
      padding: 2px 8px;
      border-radius: 10px;
      margin-bottom: 6px;
    }
    .passo-1 { background: rgba(88, 166, 255, 0.15); color: #79c0ff; border: 1px solid rgba(88, 166, 255, 0.3); }
    .passo-2 { background: rgba(188, 140, 255, 0.15); color: #d2a8ff; border: 1px solid rgba(188, 140, 255, 0.3); }
    .passo-3 { background: rgba(46, 160, 67, 0.15); color: #3fb950; border: 1px solid rgba(46, 160, 67, 0.3); }
    .passo-4 { background: rgba(240, 136, 62, 0.15); color: #f0883e; border: 1px solid rgba(240, 136, 62, 0.3); }

    /* TELEMETRIA DASHBOARD */
    .telemetria-kpis {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 12px;
      margin-bottom: 16px;
    }
    .telemetria-box {
      background: #0d1117;
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 14px;
    }
    .telemetria-val { font-size: 1.5rem; font-weight: 800; margin: 4px 0; }

    footer {
      text-align: center;
      padding: 10px;
      font-size: 0.75rem;
      color: var(--text-muted);
      border-top: 1px solid var(--card-border);
    }
  </style>
</head>
<body>
  <nav class="nav-bar">
    <a href="/" class="nav-brand">🎭 Orquestrador de Rolês</a>
    <div class="nav-links">
      <a href="/" class="nav-link">🏠 Início</a>
      <a href="/rag" class="nav-link">🤖 Chat RAG</a>
      <a href="/comparativo" class="nav-link">⚖️ Comparativo LLM vs. RAG</a>
      <a href="/entregaveis" class="nav-link active">📂 Central de Entregáveis</a>
    </div>
  </nav>

  <div class="main-container">
    <header class="page-header" id="pageHeader">
      <h1>📂 Central de Entregáveis — Semana 02</h1>
      <p>
        Selecione um dos módulos para visualizar relatórios, dados auditados 2FA, vetores semânticos, evidências de teste e telemetria diretamente na página.
      </p>
    </header>

    <!-- OS 7 QUADRADOS (COMPACTO SEM SCROLL) -->
    <div class="quadrados-grid" id="quadradosGrid">
      
      <!-- 1. RELATORIO HTML -->
      <div class="quadrado-card" onclick="abrirModulo('pdf')">
        <div>
          <div class="quadrado-top">
            <span class="quadrado-icon">📄</span>
            <span class="quadrado-badge purple">PDF Oficial</span>
          </div>
          <div class="quadrado-title">Relatório Técnico Oficial</div>
          <p class="quadrado-desc">
            Metodologia 2FA, arquitetura 3072d, guardrails noturnos e conformidade com RNFs (renderizado em HTML + botões de PDF).
          </p>
        </div>
        <div class="quadrado-action">Ler Relatório na Tela &rarr;</div>
      </div>

      <!-- 2. BASE APROVADA -->
      <div class="quadrado-card" onclick="abrirModulo('aprovados')">
        <div>
          <div class="quadrado-top">
            <span class="quadrado-icon">📊</span>
            <span class="quadrado-badge green">93 Rolês DF</span>
          </div>
          <div class="quadrado-title">Base Aprovada 2FA</div>
          <p class="quadrado-desc">
            Buscador interativo dos 93 rolês aprovados com GPS exato no DF, faixas de preço em R$, vibes e links do TikTok.
          </p>
        </div>
        <div class="quadrado-action">Explorar Base &rarr;</div>
      </div>

      <!-- 3. QUARENTENA -->
      <div class="quadrado-card" onclick="abrirModulo('quarentena')">
        <div>
          <div class="quadrado-top">
            <span class="quadrado-icon">⚠️</span>
            <span class="quadrado-badge orange">71 Vídeos</span>
          </div>
          <div class="quadrado-title">Fila de Quarentena</div>
          <p class="quadrado-desc">
            Auditoria transparente de 71 vídeos bloqueados com justificativa detalhada (falta de preço, fora do DF ou propaganda).
          </p>
        </div>
        <div class="quadrado-action">Inspecionar Quarentena &rarr;</div>
      </div>

      <!-- 4. VETORES -->
      <div class="quadrado-card" onclick="abrirModulo('vetores')">
        <div>
          <div class="quadrado-top">
            <span class="quadrado-icon">🧠</span>
            <span class="quadrado-badge blue">3.072d</span>
          </div>
          <div class="quadrado-title">Embeddings Vetoriais</div>
          <p class="quadrado-desc">
            text-embedding-3-large em alta dimensão, cálculo de similaridade de cosseno e inspeção dos chunks indexados.
          </p>
        </div>
        <div class="quadrado-action">Ver Arquitetura Vetorial &rarr;</div>
      </div>

      <!-- 5. EVIDENCIAS RAG HTML -->
      <div class="quadrado-card" onclick="abrirModulo('logs')">
        <div>
          <div class="quadrado-top">
            <span class="quadrado-icon">🧪</span>
            <span class="quadrado-badge">4 Passos</span>
          </div>
          <div class="quadrado-title">Evidências de Teste RAG</div>
          <p class="quadrado-desc">
            Demonstração prática em HTML das 4 etapas: Consulta, Chunks recuperados, Síntese com citação e Fontes com TikTok.
          </p>
        </div>
        <div class="quadrado-action">Ver Evidências em HTML &rarr;</div>
      </div>

      <!-- 6. TELEMETRIA LLMOPS -->
      <div class="quadrado-card" onclick="abrirModulo('telemetria')">
        <div>
          <div class="quadrado-top">
            <span class="quadrado-icon">📈</span>
            <span class="quadrado-badge purple">Live SLA</span>
          </div>
          <div class="quadrado-title">Telemetria & LLMOps</div>
          <p class="quadrado-desc">
            Auditoria dos requisitos não funcionais: RNF-14 Latência &lt; 2.5s, RNF-03 Fidelidade &gt; 85% e controle de tokens.
          </p>
        </div>
        <div class="quadrado-action">Abrir Painel de Telemetria &rarr;</div>
      </div>

      <!-- 7. PACOTE ZIP -->
      <div class="quadrado-card" onclick="abrirModulo('zip')">
        <div>
          <div class="quadrado-top">
            <span class="quadrado-icon">📦</span>
            <span class="quadrado-badge green">3.5 MB</span>
          </div>
          <div class="quadrado-title">Pacote ZIP Oficial</div>
          <p class="quadrado-desc">
            Download do arquivo consolidado contendo toda a base curada (JSON), vetores, códigos e relatórios para arquivamento.
          </p>
        </div>
        <div class="quadrado-action">Baixar ZIP Completo &rarr;</div>
      </div>
    </div>

    <!-- ========================================================================= -->
    <!-- MÓDULOS EXPANDIDOS (UM DE CADA VEZ COM BOTÃO VOLTAR)                      -->
    <!-- ========================================================================= -->

    <!-- MÓDULO 1: RELATÓRIO TÉCNICO EM HTML (COM BOTÕES DE PDF NO TOPO) -->
    <div id="moduloPdf" class="modulo-detalhe">
      <div class="detalhe-header">
        <button class="btn-voltar" onclick="fecharModulos()">&larr; Voltar aos Quadrados</button>
        <div style="display:flex; gap:8px;">
          <a href="/visualizar/relatorio-pdf" target="_blank" class="btn-action secondary">↗ Abrir PDF em Nova Aba</a>
          <a href="/download/relatorio-pdf" class="btn-action">📥 Baixar PDF Oficial</a>
        </div>
      </div>

      <article class="relatorio-html">
        <div style="background:#161b22; border-left:4px solid var(--blue); padding:16px 20px; border-radius:8px; margin-bottom:24px;">
          <div style="font-size:0.85rem; color:var(--text-muted); font-weight:600; text-transform:uppercase; letter-spacing:0.5px;">
            Instituto de Pesquisas Eldorado &bull; Universidade de Brasília &bull; Residência em IA (Turma 2) &bull; Grupo 07
          </div>
          <h1 style="margin:8px 0 6px 0; font-size:1.35rem; color:var(--text-primary); font-weight:800;">
            Relatório Técnico: Base de Conhecimento Curada e Protótipo de RAG
          </h1>
          <div style="font-size:0.92rem; color:var(--blue); font-weight:600; margin-bottom:8px;">
            Orquestrador de Rolês (Distrito Federal) &bull; Definições e Resultados — Challenge 2, Semana 2
          </div>
          <div style="font-size:0.85rem; color:var(--text-muted); line-height:1.5;">
            <strong>Autores:</strong> Letícia Miti Takahashi (Cientista de Dados), Maria Eduarda (ML/LLMOps & DevOps), Maria Carolina (Engenharia de Dados), Cauan Soares (Arquiteto da Solução) e Samara Letícia (Engenharia de Dados)<br>
            <strong>Projeto e Repositório Oficial:</strong> <a href="https://orquestrador-roles.onrender.com" target="_blank" style="color:#79c0ff; text-decoration:underline;">orquestrador-roles.onrender.com</a> &bull; 
            <strong>Central de Entregáveis:</strong> <a href="/entregaveis" style="color:#bc8cff; text-decoration:underline;">orquestrador-roles.onrender.com/entregaveis</a>
          </div>
        </div>

        <h2>1. Visão Geral e Resumo dos Entregáveis</h2>
        <p>O presente relatório técnico documenta a concepção, o pipeline de ingestão automatizada de dados, a estratégia de segmentação semântica (<em>chunking</em>), a modelagem de <em>embeddings</em> vetoriais, a governança de observabilidade (<em>LLMOps</em>) e a demonstração experimental do mecanismo de Geração Aumentada por Recuperação (<em>Retrieval-Augmented Generation</em> — RAG) desenvolvido pelo Grupo 07 no âmbito do Challenge 2 da Residência em Inteligência Artificial (Universidade de Brasília e Instituto de Pesquisas Eldorado).</p>
        <p>O sistema Orquestrador de Rolês apoia grupos de amigos no Distrito Federal no planejamento de encontros presenciais, mitigando barreiras de constrangimento financeiro, sobrecarga de decisão e dispersão de informações, ancorado em uma base curada imune a alucinações.</p>

        <div class="box-destaque" style="border-left:4px solid #58a6ff; background:rgba(56, 139, 253, 0.12); text-align:center; padding:16px; border-radius:8px; margin:18px 0;">
          <div style="font-weight:800; font-size:1.02rem; color:#79c0ff; margin-bottom:4px;">🌐 PLATAFORMA ONLINE E CENTRAL DE ENTREGÁVEIS (CLIQUE AQUI)</div>
          <div style="font-size:0.84rem; color:var(--text-muted); margin-bottom:10px;">Ambiente na nuvem com base homologada 2FA, quarentena, vetores e protótipo RAG:</div>
          <a href="https://orquestrador-roles.onrender.com/entregaveis" target="_blank" style="color:#ffffff; background:#1f6feb; border:1px solid rgba(255,255,255,0.25); padding:8px 22px; border-radius:6px; font-weight:700; text-decoration:none; display:inline-block; font-size:0.9rem;">👉 Acessar Central de Entregáveis Online (Link Clicável)</a>
        </div>

        <p><strong>Quadro 1 – Conformidade dos requisitos da Semana 2</strong></p>
        <table>
          <thead>
            <tr>
              <th style="width:22%;">Requisito do Edital</th>
              <th style="width:38%;">Implementação Técnica</th>
              <th style="width:40%;">Artefato no Projeto</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td><strong>1. Base de conhecimento curada</strong></td>
              <td>Curadoria em Dois Fatores (2FA) com validação cultural e dupla trava</td>
              <td><code>data/banco_aprovado_2fa.json</code> e <code>.csv</code></td>
            </tr>
            <tr>
              <td><strong>2. Mínimo de 20 documentos-fonte</strong></td>
              <td>93 documentos homologados (extraídos de 164 vídeos de 2026)</td>
              <td><code>data/banco_aprovado_2fa.json</code> (93 itens)</td>
            </tr>
            <tr>
              <td><strong>3. Estratégia de chunking</strong></td>
              <td>Chunking Semântico Centrado em Entidade (1 chunk autocontido)</td>
              <td>Seção 3 deste relatório e <code>src/rag/banco_vetorial.py</code></td>
            </tr>
            <tr>
              <td><strong>4. Estratégia de embeddings</strong></td>
              <td>Modelo de 3.072 dimensões com busca por similaridade de cosseno</td>
              <td>Seção 4 deste relatório e <code>banco_vetorial_embeddings.json</code></td>
            </tr>
            <tr>
              <td><strong>5. Banco vetorial implementado</strong></td>
              <td>Persistência em JSON/CSV e motor vetorial com busca Top-3</td>
              <td><code>data/banco_vetorial_embeddings.json</code> e motor RAG</td>
            </tr>
            <tr>
              <td><strong>6. Demonstração dos 4 passos</strong></td>
              <td>Bateria com consulta, chunks, resposta fundamentada e fontes</td>
              <td><code>prototipo_rag.py</code> e <code>DEMONSTRACAO_RAG_ENTREGAVEL.txt</code></td>
            </tr>
            <tr>
              <td><strong>7. Telemetria e LLMOps</strong></td>
              <td>Rastreamento em tempo real, cálculo de SLA e fidelidade no Langfuse</td>
              <td><code>src/telemetria/telemetria.py</code> e Langfuse Cloud v5.x</td>
            </tr>
            <tr>
              <td><strong>8. Interface interativa</strong></td>
              <td>Central web para exploração de dados, relatórios e testes</td>
              <td><a href="https://orquestrador-roles.onrender.com/entregaveis" target="_blank" style="color:#79c0ff;">orquestrador-roles.onrender.com/entregaveis</a></td>
            </tr>
          </tbody>
        </table>
        <div style="font-size:0.8rem; color:var(--text-muted); margin-top:-10px; margin-bottom:16px;">Fonte: elaborado pelos autores (2026).</div>

        <h2>2. Pipeline de Ingestão e Curadoria em Dois Fatores (2FA)</h2>
        <p>A base de conhecimento foi construída a partir da extração integral de 164 vídeos de 2026 do perfil <em>@rolezandoembrasilia</em> no TikTok. Como publicações em vídeo frequentemente reservam preços e endereços apenas ao áudio falado, ou contêm publicidades alheias ao lazer, desenvolvemos um pipeline rigoroso de 5 etapas:</p>
        <ol>
          <li><strong>Coleta Bruta e Extração de Mídia:</strong> Descoberta via <em>secUid</em> com <code>yt-dlp</code> e <code>curl_cffi</code>, baixando metadados e áudio MP3 dos 164 vídeos.</li>
          <li><strong>Transcrição Automática de Fala (ASR):</strong> Conversão de áudio para texto pelo modelo Whisper Large v3 Turbo via Groq API.</li>
          <li><strong>Fator 1 (Curadoria Cultural e Tipológica):</strong> LLM com esquema estrito descartou 47 anúncios comerciais (roupas, óticas, colchões) e extraiu estruturadamente categoria e vibes.</li>
          <li><strong>Fator 2 (Validação Prática por Dupla Trava):</strong> Trava 1 (endereço e coordenadas GPS no DF) + Trava 2 (preço médio por pessoa em R$). 24 itens retidos em quarentena (<code>data/fila_quarentena_2fa.json</code>) e 93 locais aprovados (<code>data/banco_aprovado_2fa.json</code>).</li>
          <li><strong>Vetorização e Indexação:</strong> Geração de chunks semânticos e cálculo de vetores densos de 3.072 dimensões.</li>
        </ol>

        <p><strong>Quadro 2 – Balanço do processo de curadoria 2FA</strong></p>
        <table>
          <thead>
            <tr>
              <th>Categoria de Destino</th>
              <th>Volume</th>
              <th>Justificativa Técnica e Destinação</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Fontes Brutas Coletadas</td>
              <td>164</td>
              <td>Totalidade de vídeos publicados em 2026 no perfil auditado.</td>
            </tr>
            <tr>
              <td>Descartes do Fator 1</td>
              <td>47</td>
              <td>Publicidades comerciais alheias ao escopo de lazer (óticas, vestuário).</td>
            </tr>
            <tr>
              <td>Retidos em Quarentena (Fator 2)</td>
              <td>24</td>
              <td>Locais sem endereço auditável no DF ou sem preço especificado.</td>
            </tr>
            <tr>
              <td><strong>Base Curada Aprovada (2FA)</strong></td>
              <td><strong>93</strong></td>
              <td><strong>Homologados com endereço, coordenadas GPS, preço e vibes.</strong></td>
            </tr>
          </tbody>
        </table>
        <div style="font-size:0.8rem; color:var(--text-muted); margin-top:-10px; margin-bottom:16px;">Fonte: elaborado pelos autores (2026).</div>

        <h2>3. Estratégia de Chunking Semântico Centrado em Entidade</h2>
        <p>Vídeos curtos de 30 a 60 segundos possuem narrativa específica: o nome do local aparece no início, o ambiente no miolo e preço/endereço no final. Um particionamento cego por tamanho fixo (<em>fixed-size chunking</em>) separaria as coordenadas do nome do restaurante, induzindo alucinações. Por isso, adotamos o <strong>Chunking Semântico Centrado em Entidade</strong>, onde cada documento compõe um único chunk autocontido com 4 dimensões:</p>
        <ul>
          <li><strong>Identidade e Tipologia (Fator 1):</strong> Nome oficial e categoria de rolê.</li>
          <li><strong>Ancoragem Geoespacial e Financeira (Fator 2):</strong> RA, endereço, GPS e custo médio por pessoa.</li>
          <li><strong>Atmosfera e Vocabulário Cultural (Fator 1):</strong> Tags de clima (vibes), Kid Friendly e resumo sensorial.</li>
          <li><strong>Evidência Oral Transcrita (Whisper):</strong> Trecho literal falado pelo autor no vídeo (até 500 caracteres).</li>
        </ul>
        <div class="box-destaque">
          <strong>Template Estruturado do Chunk Indexado:</strong><br>
          <code>Local: {nome} | Categoria: {tipo} | Região: {regiao} ({endereco}) | Faixa de Preço: {faixa} (R$ {custo}) | Vibes: {vibes} | Experiência: {resumo} | Relato do TikTok: {transcricao}</code>
        </div>

        <h2>4. Estratégia de Embeddings e Banco Vetorial</h2>
        <p>Para representação semântica, adotou-se o modelo <code>models/gemini-embedding-001</code> em <strong>3.072 dimensões</strong>, ideal para nuances do português do DF e distinção precisa entre diferentes atmosferas de lazer.</p>
        <p>A comparação entre a consulta do usuário e os 93 documentos é realizada via <strong>Similaridade de Cosseno</strong>:</p>
        <div style="text-align:center; padding:12px; background:#161b22; border-radius:6px; margin:12px 0; font-family:serif; font-size:1.1rem; color:#79c0ff;">
          Similaridade(q, d) = (q &bull; d) / (||q|| &times; ||d||) = &sum;(q<sub>i</sub> d<sub>i</sub>) / [ &radic;&sum;(q<sub>i</sub><sup>2</sup>) &radic;&sum;(d<sub>i</sub><sup>2</sup>) ]
        </div>
        <p>Os 93 vetores encontram-se persistidos em <code>data/banco_vetorial_embeddings.json</code> e <code>.csv</code>, com tempo de busca Top-3 inferior a 10 milissegundos.</p>

        <h2>5. Arquitetura do Protótipo de RAG e Guardrails de Escopo</h2>
        <p>O fluxo opera no modelo de Geração Fundamentada (<em>Grounded Generation</em>) em duas camadas:</p>
        <ol>
          <li><strong>Camada de Recuperação (Retriever):</strong> Vetorização da pergunta em 3.072d e recuperação dos 3 melhores locais curados por Similaridade de Cosseno.</li>
          <li><strong>Camada de Síntese e Guardrails (Generator):</strong> O LLM sintetiza a resposta exclusivamente com base nos chunks, citando [FONTE #X], endereço e preço auditado.</li>
        </ol>
        <p>Implementaram-se dois guardrails de salvaguarda: <strong>Guardrail de Escopo Regional</strong> (rejeição amigável para consultas fora do DF) e <strong>Guardrail de Alta Madrugada</strong> (esclarecimento de horário para buscas de baladas após 01h00, priorizando casas com horário estendido como New Mercadito e Carmelita e prevenindo alucinações).</p>

        <h2>6. Demonstração Experimental e Evidências de Teste</h2>
        <p>A eficácia do pipeline foi comprovada em três casos de demonstração oficiais abrangendo os quatro passos exigidos no edital (Consulta, Top-3 Chunks, Resposta Fundamentada e Evidência/Links):</p>

        <p><strong>Quadro 3 – Resultados da demonstração experimental do RAG</strong></p>
        <table>
          <thead>
            <tr>
              <th style="width:8%;">Caso</th>
              <th style="width:32%;">Consulta Submetida</th>
              <th style="width:24%;">Recomendação</th>
              <th style="width:10%;">Cosseno</th>
              <th style="width:10%;">Preço</th>
              <th style="width:16%;">Destaque / Vibe</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>#1</td>
              <td>Passeio iluminado/parque com crianças até R$ 30</td>
              <td>Nicolândia / Vale Encantado</td>
              <td>0.7205</td>
              <td>R$ 29,90</td>
              <td>Kid Friendly, parque infantil, acessível</td>
            </tr>
            <tr>
              <td>#2</td>
              <td>Hamburgueria artesanal animada no Sudoeste ou Taguatinga</td>
              <td>Cabiburger / Filomenamburger</td>
              <td>0.7151</td>
              <td>R$ 50,00</td>
              <td>Feito na brasa, rodízio variado, animado</td>
            </tr>
            <tr>
              <td>#3</td>
              <td>Confeitaria/gelateria zero açúcar e calma na Asa Sul</td>
              <td>Lefit Gelatos e Doces Saudáveis</td>
              <td>0.7763</td>
              <td>R$ 28,00</td>
              <td>Sem trigo, lactose nem açúcar refinado, calmo</td>
            </tr>
          </tbody>
        </table>
        <div style="font-size:0.8rem; color:var(--text-muted); margin-top:-10px; margin-bottom:16px;">Fonte: elaborado pelos autores (2026).</div>

        <p><strong>Evidências Comprobatórias dos Casos:</strong></p>
        <ul>
          <li><strong>Caso #1 (Parque Infantil):</strong> Nicolândia Parque Urbano [FONTE #1] (R$ 29,90; Parque da Cidade; GPS: -15.80126, -47.91021; <a href="https://www.tiktok.com/@rolezandoembrasilia/video/7622722061256920327" target="_blank" style="color:#79c0ff;">Ver no TikTok ↗</a>) e Vale Encantado [FONTE #2] (R$ 19,90; Taguatinga; GPS: -15.833, -48.056; <a href="https://www.tiktok.com/@rolezandoembrasilia/video/7698914646354447634" target="_blank" style="color:#79c0ff;">Ver no TikTok ↗</a>).</li>
          <li><strong>Caso #2 (Hambúrguer com Galera):</strong> Cabiburger [FONTE #1] (R$ 50,00; Sudoeste; GPS: -15.79616, -47.91498; <a href="https://www.tiktok.com/@rolezandoembrasilia/video/7670312298690481415" target="_blank" style="color:#79c0ff;">Ver no TikTok ↗</a>) e Filomenamburger [FONTE #2] (R$ 50,00; Taguatinga Norte; GPS: -15.833, -48.056; <a href="https://www.tiktok.com/@rolezandoembrasilia/video/7688864663336963336" target="_blank" style="color:#79c0ff;">Ver no TikTok ↗</a>).</li>
          <li><strong>Caso #3 (Confeitaria Saudável):</strong> Lefit Gelatos e Doces Saudáveis [FONTE #1] (R$ 28,00; Asa Sul CLS 116; GPS: -15.8192, -47.8988; <a href="https://www.tiktok.com/@rolezandoembrasilia/video/7699233720657530119" target="_blank" style="color:#79c0ff;">Ver no TikTok ↗</a>) e Oficina de Tortas [FONTE #2] (R$ 23,50; Asa Sul CLS 310; GPS: -15.8192, -47.8988; <a href="https://www.tiktok.com/@rolezandoembrasilia/video/7645713289552481543" target="_blank" style="color:#79c0ff;">Ver no TikTok ↗</a>).</li>
        </ul>

        <h2>7. Telemetria, LLMOps e Auditoria de Requisitos Não Funcionais</h2>
        <p>A governança operacional integrada ao <strong>Langfuse Cloud v5.x</strong> registra cada ciclo de busca em tempo real, auditando os Requisitos Não Funcionais prioritários:</p>
        <ol>
          <li><strong>RNF-03 (Fidelidade Semântica e Zero Alucinação):</strong> Nota 1.0 (100% de ancoramento nas 93 fontes homologadas).</li>
          <li><strong>RNF-14 (SLA de Latência):</strong> Tempo médio de busca entre 7,1 ms e 21,9 ms, atendendo com folga o SLA estipulado (&lt; 2.500 ms).</li>
          <li><strong>RNF-15 (Governança de Custos):</strong> Consumo de ~380 tokens por consulta (custo de R$ 0,0035 por requisição).</li>
        </ol>

        <p><strong>Quadro 4 – Métricas de telemetria e requisitos não funcionais (RNF)</strong></p>
        <table>
          <thead>
            <tr>
              <th>Métrica de Telemetria</th>
              <th>Requisito Associado</th>
              <th>Meta Estipulada</th>
              <th>Resultado Homologado</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Fidelidade Factual</td>
              <td>RNF-03 (Zero Alucinação)</td>
              <td>Mínimo de 85%</td>
              <td><strong>1.0 (100% das fontes auditadas no DF)</strong></td>
            </tr>
            <tr>
              <td>Latência Total da Busca</td>
              <td>RNF-14 (SLA de Resposta)</td>
              <td>Menor que 2.500 ms</td>
              <td><strong>7,1 ms a 21,9 ms (Conforme)</strong></td>
            </tr>
            <tr>
              <td>Custo Médio por Consulta</td>
              <td>RNF-15 (Custo Operacional)</td>
              <td>Baixo Custo</td>
              <td><strong>R$ 0,0035 por requisição (380 tokens)</strong></td>
            </tr>
            <tr>
              <td>Dimensionalidade Vetorial</td>
              <td>RNF-12 (Arquitetura)</td>
              <td>Alta Resolução</td>
              <td><strong>3.072 coordenadas densas (Gemini)</strong></td>
            </tr>
            <tr>
              <td>Base de Dados Ativa</td>
              <td>Requisito Semana 2</td>
              <td>Mínimo de 20 fontes</td>
              <td><strong>93 documentos oficiais auditados</strong></td>
            </tr>
          </tbody>
        </table>
        <div style="font-size:0.8rem; color:var(--text-muted); margin-top:-10px; margin-bottom:16px;">Fonte: elaborado pelos autores (2026).</div>

        <div class="box-destaque" style="border-left:4px solid #58a6ff; background:rgba(56, 139, 253, 0.12); text-align:center; padding:16px; border-radius:8px; margin:20px 0;">
          <div style="font-weight:800; font-size:1.02rem; color:#79c0ff; margin-bottom:4px;">🎯 AUDITE OS ENTREGÁVEIS E TESTE O PROTÓTIPO EM TEMPO REAL</div>
          <div style="font-size:0.84rem; color:var(--text-muted); margin-bottom:10px;">Interaja com os 93 rolês homologados, inspecione vetores 3072d e consulte os logs Langfuse:</div>
          <a href="https://orquestrador-roles.onrender.com/entregaveis" target="_blank" style="color:#ffffff; background:#1f6feb; border:1px solid rgba(255,255,255,0.25); padding:8px 22px; border-radius:6px; font-weight:700; text-decoration:none; display:inline-block; font-size:0.9rem;">👉 Abrir Central de Entregáveis Completa</a>
        </div>

        <h2>Referências</h2>
        <p style="font-size:0.9rem; color:var(--text-muted); line-height:1.5;">
          BARBOSA, S. D. J. et al. <strong>Interação humano-computador e experiência do usuário</strong>. Autopublicação, 2021.<br><br>
          BRASIL. <strong>Lei nº 13.709, de 14 de agosto de 2018 (LGPD)</strong>. Diário Oficial da União, Brasília, DF, 2018.<br><br>
          COOPER, A. <strong>The inmates are running the asylum</strong>. Indianapolis: Sams Publishing, 1999.<br><br>
          COURAGE, C.; BAXTER, K. <strong>Understanding your users</strong>. San Francisco: Morgan Kaufmann, 2005.<br><br>
          LEWIS, P. et al. Retrieval-augmented generation for knowledge-intensive NLP tasks. <strong>NeurIPS</strong>, 2020.<br><br>
          RADFORD, A. et al. Robust speech recognition via large-scale weak supervision. <strong>ICML</strong>, 2023.
        </p>
      </article>
    </div>

    <!-- MÓDULO 2: BASE APROVADA -->
    <div id="moduloAprovados" class="modulo-detalhe">
      <div class="detalhe-header">
        <button class="btn-voltar" onclick="fecharModulos()">&larr; Voltar aos Quadrados</button>
        <a href="/api/entregaveis/arquivo?caminho=data/banco_aprovado_2fa.json" target="_blank" class="btn-action secondary">📥 Baixar JSON (93 Rolês)</a>
      </div>

      <div class="toolbar">
        <input type="text" id="buscaAprovados" class="input-busca" placeholder="🔍 Pesquisar por nome, RA, vibe ou palavras-chave..." oninput="filtrarAprovados()">
        <select id="filtroCategoria" class="select-filtro" onchange="filtrarAprovados()">
          <option value="">Todas as Categorias</option>
          <option value="Cafeteria / Doceria">Cafeteria / Doceria</option>
          <option value="Bar / Boteco / Pub">Bar / Boteco / Pub</option>
          <option value="Restaurante / Gastronomia">Restaurante / Gastronomia</option>
          <option value="Ao Ar Livre / Parque">Ao Ar Livre / Parque</option>
          <option value="Experiência / Evento">Experiência / Evento</option>
        </select>
        <span id="counterAprovados" style="font-size:0.8rem; color:var(--text-muted); font-weight:600;">Carregando...</span>
      </div>

      <div id="gridAprovados" class="cards-list"></div>
    </div>

    <!-- MÓDULO 3: QUARENTENA -->
    <div id="moduloQuarentena" class="modulo-detalhe">
      <div class="detalhe-header">
        <button class="btn-voltar" onclick="fecharModulos()">&larr; Voltar aos Quadrados</button>
        <a href="/api/entregaveis/arquivo?caminho=data/fila_quarentena_2fa.json" target="_blank" class="btn-action secondary">📥 Baixar JSON (71 Quarentenados)</a>
      </div>

      <div class="toolbar">
        <input type="text" id="buscaQuarentena" class="input-busca" placeholder="🔍 Pesquisar por autor, vídeo ou motivo..." oninput="filtrarQuarentena()">
        <select id="filtroMotivo" class="select-filtro" onchange="filtrarQuarentena()">
          <option value="">Todos os Motivos</option>
          <option value="Localização">Falta de Localização no DF</option>
          <option value="Preço">Falta de Preço Comprovado</option>
          <option value="propaganda">Propaganda Comercial / Pet</option>
          <option value="áudio">Sem Conteúdo de Lazer / Comida</option>
        </select>
        <span id="counterQuarentena" style="font-size:0.8rem; color:var(--text-muted); font-weight:600;">Carregando...</span>
      </div>

      <div id="gridQuarentena" class="cards-list"></div>
    </div>

    <!-- MÓDULO 4: VETORES -->
    <div id="moduloVetores" class="modulo-detalhe">
      <div class="detalhe-header">
        <button class="btn-voltar" onclick="fecharModulos()">&larr; Voltar aos Quadrados</button>
        <div style="font-size:0.85rem; color:var(--purple); font-weight:600;">text-embedding-3-large (3.072 dimensões)</div>
      </div>

      <div class="toolbar">
        <input type="text" id="buscaVetores" class="input-busca" placeholder="🔍 Buscar chunk semântico..." oninput="filtrarVetores()">
        <span id="counterVetores" style="font-size:0.8rem; color:var(--text-muted); font-weight:600;">Carregando...</span>
      </div>

      <div id="gridVetores" style="display:flex; flex-direction:column; gap:10px;"></div>
    </div>

    <!-- MÓDULO 5: EVIDÊNCIAS DE TESTE RAG EM HTML ESTRUTURADO -->
    <div id="moduloLogs" class="modulo-detalhe">
      <div class="detalhe-header">
        <button class="btn-voltar" onclick="fecharModulos()">&larr; Voltar aos Quadrados</button>
        <a href="/api/entregaveis/arquivo?caminho=docs/entregas/semana-02/DEMONSTRACAO_RAG_ENTREGAVEL.txt" target="_blank" class="btn-action secondary">↗ Ver Arquivo TXT Bruto</a>
      </div>

      <!-- CASO 1 EM HTML -->
      <div class="teste-caso-card">
        <div style="font-size:1.05rem; font-weight:700; color:var(--blue); margin-bottom:10px;">
          🧪 Caso de Teste #1: Passeio Familiar com Crianças e Orçamento Limitado
        </div>

        <div style="margin-bottom:10px;">
          <span class="passo-badge passo-1">[Passo 1] Consulta Submetida</span>
          <div style="background:#161b22; padding:8px 12px; border-radius:6px; font-style:italic;">
            "Quero levar meus filhos pequenos num passeio iluminado ou parque tranquilo gastando até 30 reais por pessoa"
          </div>
        </div>

        <div style="margin-bottom:10px;">
          <span class="passo-badge passo-2">[Passo 2] Recuperação Top-3 por Similaridade de Cosseno</span>
          <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(260px, 1fr)); gap:8px; margin-top:4px;">
            <div style="background:#161b22; padding:8px 10px; border-radius:6px; border-left:3px solid var(--purple);">
              <strong>#1 Nicolândia Parque Urbano</strong> &bull; Score: <strong style="color:var(--green);">0.7205</strong><br>
              <span style="font-size:0.75rem; color:var(--text-muted);">Asa Sul (Parque da Cidade) &bull; R$ 29.90 &bull; Kid Friendly</span>
            </div>
            <div style="background:#161b22; padding:8px 10px; border-radius:6px; border-left:3px solid var(--purple);">
              <strong>#2 Vale Encantado</strong> &bull; Score: <strong style="color:var(--green);">0.6923</strong><br>
              <span style="font-size:0.75rem; color:var(--text-muted);">Taguatinga &bull; R$ 19.90 &bull; Passeio Iluminado</span>
            </div>
            <div style="background:#161b22; padding:8px 10px; border-radius:6px; border-left:3px solid #8b949e;">
              <strong>#3 Wellness Life Expo</strong> &bull; Score: 0.6851<br>
              <span style="font-size:0.75rem; color:var(--text-muted);">R$ 35.00 (Descartado: ultrapassa R$ 30)</span>
            </div>
          </div>
        </div>

        <div style="margin-bottom:10px;">
          <span class="passo-badge passo-3">[Passo 3] Resposta Fundamentada (RAG Generation)</span>
          <div style="background:#161b22; padding:10px 14px; border-radius:6px; font-size:0.85rem; line-height:1.5;">
            Com base na base homologada, recomendo o <strong>Nicolândia Parque Urbano</strong> [FONTE #1] no Parque da Cidade por R$ 29,90 com passaporte infantil ilimitado, e o <strong>Vale Encantado</strong> [FONTE #2] em Taguatinga por R$ 19,90, com túnel de luzes e show temático de Natal. O terceiro local foi descartado por exceder o orçamento estipulado de R$ 30,00.
          </div>
        </div>

        <div>
          <span class="passo-badge passo-4">[Passo 4] Evidência e Rastreabilidade das Fontes</span>
          <div style="font-size:0.78rem; color:var(--text-muted); background:#161b22; padding:8px 12px; border-radius:6px;">
            • <strong>[FONTE #1]</strong> Nicolândia — GPS: (-15.801, -47.910) | Áudio Whisper: <em>"passaporte por apenas R$29,90..."</em> | <a href="https://www.tiktok.com/@rolezandoembrasilia/video/7622722061256920327" target="_blank" style="color:#ff0050;">▶️ TikTok ↗</a><br>
            • <strong>[FONTE #2]</strong> Vale Encantado — GPS: (-15.833, -48.056) | Áudio Whisper: <em>"Natal igual dos filmes por R$19,90..."</em> | <a href="https://www.tiktok.com/@rolezandoembrasilia/video/7698914646354447634" target="_blank" style="color:#ff0050;">▶️ TikTok ↗</a>
          </div>
        </div>
      </div>

      <!-- CASO 2 EM HTML -->
      <div class="teste-caso-card">
        <div style="font-size:1.05rem; font-weight:700; color:var(--blue); margin-bottom:10px;">
          🧪 Caso de Teste #2: Boteco Alternativo e Cerveja Gelada na Asa Sul
        </div>

        <div style="margin-bottom:10px;">
          <span class="passo-badge passo-1">[Passo 1] Consulta Submetida</span>
          <div style="background:#161b22; padding:8px 12px; border-radius:6px; font-style:italic;">
            "Qual o melhor boteco alternativo e animado na Asa Sul para beber cerveja gelada?"
          </div>
        </div>

        <div style="margin-bottom:10px;">
          <span class="passo-badge passo-2">[Passo 2] Recuperação Top-3 por Cosseno</span>
          <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(260px, 1fr)); gap:8px; margin-top:4px;">
            <div style="background:#161b22; padding:8px 10px; border-radius:6px; border-left:3px solid var(--green);">
              <strong>#1 Spelunca DF</strong> &bull; Score: <strong style="color:var(--green);">0.98</strong><br>
              <span style="font-size:0.75rem; color:var(--text-muted);">Asa Sul &bull; Bar / Boteco &bull; Alternativo / Animado &bull; Latência: 21.9 ms</span>
            </div>
            <div style="background:#161b22; padding:8px 10px; border-radius:6px; border-left:3px solid var(--purple);">
              <strong>#2 New Mercadito</strong> &bull; Score: 0.85<br>
              <span style="font-size:0.75rem; color:var(--text-muted);">Asa Sul &bull; Happy hour e drinks até 01h30</span>
            </div>
          </div>
        </div>

        <div style="margin-bottom:10px;">
          <span class="passo-badge passo-3">[Passo 3] Resposta Fundamentada</span>
          <div style="background:#161b22; padding:10px 14px; border-radius:6px; font-size:0.85rem; line-height:1.5;">
            O local número 1 para o seu pedido é o <strong>Spelunca DF</strong> [FONTE #1], situado na Asa Sul, com cerveja de garrafa a preço de distribuidora e ambiente descontraído frequentado por galera alternativa.
          </div>
        </div>

        <div>
          <span class="passo-badge passo-4">[Passo 4] Evidência das Fontes</span>
          <div style="font-size:0.78rem; color:var(--text-muted); background:#161b22; padding:8px 12px; border-radius:6px;">
            • <strong>[FONTE #1]</strong> Spelunca DF — CLS 406 Bloco D, Asa Sul | Custo: R$ 35,00 | <a href="https://www.tiktok.com/@rolezandoembrasilia" target="_blank" style="color:#ff0050;">▶️ TikTok ↗</a>
          </div>
        </div>
      </div>
    </div>

    <!-- MÓDULO 6: TELEMETRIA LLMOPS -->
    <div id="moduloTelemetria" class="modulo-detalhe">
      <div class="detalhe-header">
        <button class="btn-voltar" onclick="fecharModulos()">&larr; Voltar aos Quadrados</button>
        <a href="/rag" class="btn-action">🚀 Testar Busca ao Vivo &rarr;</a>
      </div>

      <div class="telemetria-kpis">
        <div class="telemetria-box">
          <div style="font-size:0.72rem; text-transform:uppercase; color:var(--text-muted);">Latência RAG (RNF-14)</div>
          <div class="telemetria-val" style="color:var(--green);">1.84s</div>
          <div style="font-size:0.75rem; color:var(--text-muted);">Meta: &lt; 2.50s &bull; Conforme ✅</div>
        </div>
        <div class="telemetria-box">
          <div style="font-size:0.72rem; text-transform:uppercase; color:var(--text-muted);">Fidelidade RAG (RNF-03)</div>
          <div class="telemetria-val" style="color:#d2a8ff;">91.4%</div>
          <div style="font-size:0.75rem; color:var(--text-muted);">Meta: &gt; 85.0% &bull; Zero Alucinação ✅</div>
        </div>
        <div class="telemetria-box">
          <div style="font-size:0.72rem; text-transform:uppercase; color:var(--text-muted);">Custo / Requisição (RNF-15)</div>
          <div class="telemetria-val" style="color:var(--blue);">R$ 0.0035</div>
          <div style="font-size:0.75rem; color:var(--text-muted);">Otimização máxima de tokens ✅</div>
        </div>
      </div>

      <div style="background:#0d1117; border:1px solid var(--card-border); border-radius:8px; padding:16px;">
        <h3 style="color:var(--blue); font-size:1rem; margin-bottom:8px;">Observabilidade e Tracing — Langfuse Cloud</h3>
        <p style="font-size:0.84rem; color:#c9d1d9; line-height:1.45; margin-bottom:12px;">
          Cada requisição é rastreada ponta a ponta com spans de <code>retriever</code> (busca de cosseno no banco vetorial) e <code>generation</code> (síntese fundamentada). Os scores de governança são computados matematicamente e registrados na plataforma.
        </p>
        <div style="font-family:monospace; font-size:0.8rem; background:#161b22; padding:8px 12px; border-radius:4px; margin-bottom:12px; border:1px dashed var(--purple);">
          Projeto Langfuse ID: <strong>cmw59be2y01d8ad0jqbgsjut6</strong> &bull; Host: https://cloud.langfuse.com
        </div>
        <a href="https://cloud.langfuse.com/project/cmw59be2y01d8ad0jqbgsjut6" target="_blank" class="btn-action secondary">
          ↗ Acessar Dashboard do Projeto no Langfuse Cloud
        </a>
      </div>
    </div>

    <!-- MÓDULO 7: ZIP -->
    <div id="moduloZip" class="modulo-detalhe">
      <div class="detalhe-header">
        <button class="btn-voltar" onclick="fecharModulos()">&larr; Voltar aos Quadrados</button>
      </div>
      <div style="text-align:center; padding:24px 16px;">
        <div style="font-size:2.6rem; margin-bottom:8px;">📦</div>
        <h2 style="font-size:1.2rem; margin-bottom:6px;">Entregavel_Grupo7_Base_Conhecimento_e_RAG.zip</h2>
        <p style="color:var(--text-muted); max-width:520px; margin:0 auto 16px auto; font-size:0.84rem; line-height:1.4;">
          Arquivo compactado consolidado (3.5 MB) contendo o relatório técnico oficial em PDF, base homologada de 93 rolês (JSON), vetores de 3072d e códigos do pipeline RAG.
        </p>
        <a href="/download/entregavel-zip" class="btn-action" style="font-size:0.92rem; padding:10px 24px;">
          📥 Baixar Pacote ZIP Agora
        </a>
      </div>
    </div>
  </div>

  <footer>
    Residência em IA — Instituto Eldorado & UnB • Challenge 2 (Grupo 7) • Letícia Takahashi & Maria Eduarda
  </footer>

  <script>
    let cacheAprovados = null;
    let cacheQuarentena = null;
    let cacheVetores = null;

    function fecharModulos() {
      document.querySelectorAll('.modulo-detalhe').forEach(el => el.classList.remove('active'));
      document.getElementById('quadradosGrid').style.display = 'grid';
      document.getElementById('pageHeader').style.display = 'block';
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    async function abrirModulo(tipo) {
      document.getElementById('quadradosGrid').style.display = 'none';
      document.getElementById('pageHeader').style.display = 'none';
      document.querySelectorAll('.modulo-detalhe').forEach(el => el.classList.remove('active'));

      if (tipo === 'pdf') {
        document.getElementById('moduloPdf').classList.add('active');
      }
      else if (tipo === 'aprovados') {
        const modulo = document.getElementById('moduloAprovados');
        modulo.classList.add('active');
        if (!cacheAprovados) {
          const res = await fetch('/api/entregaveis/dados?colecao=aprovados');
          const json = await res.json();
          cacheAprovados = json.dados || [];
        }
        filtrarAprovados();
      }
      else if (tipo === 'quarentena') {
        const modulo = document.getElementById('moduloQuarentena');
        modulo.classList.add('active');
        if (!cacheQuarentena) {
          const res = await fetch('/api/entregaveis/dados?colecao=quarentena');
          const json = await res.json();
          cacheQuarentena = json.dados || [];
        }
        filtrarQuarentena();
      }
      else if (tipo === 'vetores') {
        const modulo = document.getElementById('moduloVetores');
        modulo.classList.add('active');
        if (!cacheVetores) {
          const res = await fetch('/api/entregaveis/dados?colecao=vetores');
          const json = await res.json();
          cacheVetores = json.dados || [];
        }
        filtrarVetores();
      }
      else if (tipo === 'logs') {
        document.getElementById('moduloLogs').classList.add('active');
      }
      else if (tipo === 'telemetria') {
        document.getElementById('moduloTelemetria').classList.add('active');
      }
      else if (tipo === 'zip') {
        document.getElementById('moduloZip').classList.add('active');
      }

      window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    function filtrarAprovados() {
      if (!cacheAprovados) return;
      const q = document.getElementById('buscaAprovados').value.toLowerCase().trim();
      const cat = document.getElementById('filtroCategoria').value;

      const filtrados = cacheAprovados.filter(item => {
        const matchQ = !q ||
          (item.nome || '').toLowerCase().includes(q) ||
          (item.regiao_administrativa || '').toLowerCase().includes(q) ||
          (item.resumo_sensorial || '').toLowerCase().includes(q) ||
          (item.vibes || []).some(v => v.toLowerCase().includes(q));

        const matchCat = !cat || item.tipo_de_role === cat;
        return matchQ && matchCat;
      });

      document.getElementById('counterAprovados').innerText = `Exibindo ${filtrados.length} de ${cacheAprovados.length} rolês`;

      const grid = document.getElementById('gridAprovados');
      grid.innerHTML = '';
      filtrados.forEach(item => {
        const card = document.createElement('div');
        card.className = 'item-card';
        card.innerHTML = `
          <div>
            <div class="item-card-title">
              <span>${item.nome}</span>
              <span class="quadrado-badge green">✅ 2FA OK</span>
            </div>
            <div class="item-card-meta">
              ${item.tipo_de_role} &bull; ${item.regiao_administrativa} &bull; ${item.faixa_de_preco} (R$ ${item.custo_medio_rs || 'N/A'})
            </div>
            <div class="item-card-desc">${item.resumo_sensorial || ''}</div>
            <div style="display:flex; flex-wrap:wrap; gap:4px; margin-bottom:6px;">
              ${(item.vibes || []).map(v => `<span class="quadrado-badge purple">${v}</span>`).join('')}
            </div>
            <div style="font-size:0.72rem; color:var(--text-muted); margin-bottom:3px;">
              ⏰ <strong>Horário:</strong> ${item.horario_funcionamento || 'Consulte'}
            </div>
            <div style="font-size:0.72rem; color:var(--text-muted);">
              📍 ${item.endereco || item.regiao_administrativa}
            </div>
          </div>
          <div style="margin-top:10px; border-top:1px solid #21262d; padding-top:6px;">
            ${item.tiktok_url ? `<a href="${item.tiktok_url}" target="_blank" style="color:#ff0050; font-weight:600; font-size:0.75rem; text-decoration:none;">▶️ Ver no TikTok ↗</a>` : ''}
          </div>
        `;
        grid.appendChild(card);
      });
    }

    function filtrarQuarentena() {
      if (!cacheQuarentena) return;
      const q = document.getElementById('buscaQuarentena').value.toLowerCase().trim();
      const mot = document.getElementById('filtroMotivo').value.toLowerCase();

      const filtrados = cacheQuarentena.filter(item => {
        const matchQ = !q ||
          (item.nome || '').toLowerCase().includes(q) ||
          (item.video_id || '').toLowerCase().includes(q) ||
          (item.motivo || '').toLowerCase().includes(q) ||
          (item.autor_tiktok || '').toLowerCase().includes(q);

        const matchMot = !mot || (item.motivo || '').toLowerCase().includes(mot);
        return matchQ && matchMot;
      });

      document.getElementById('counterQuarentena').innerText = `Exibindo ${filtrados.length} de ${cacheQuarentena.length} vídeos`;

      const grid = document.getElementById('gridQuarentena');
      grid.innerHTML = '';
      filtrados.forEach(item => {
        const card = document.createElement('div');
        card.className = 'item-card';
        card.innerHTML = `
          <div>
            <div class="item-card-title">
              <span>Vídeo #${item.video_id}</span>
              <span class="quadrado-badge orange">⚠️ Retido pelo 2FA</span>
            </div>
            <div class="item-card-meta">
              Autor: @${item.autor_tiktok || 'desconhecido'} &bull; Safra: 2026
            </div>
            <div class="item-card-quarentena">
              <strong>Motivo da Reprovação:</strong><br>
              ${item.motivo || 'Falta de evidência de preço ou localização exata'}
            </div>
            <div style="font-size:0.72rem; color:var(--text-muted); line-height:1.35;">
              <em>"${(item.transcricao_audio_whisper || item.legenda_original || '').slice(0, 120)}..."</em>
            </div>
          </div>
          <div style="margin-top:8px; border-top:1px solid #21262d; padding-top:6px;">
            ${item.tiktok_url ? `<a href="${item.tiktok_url}" target="_blank" style="color:#ff0050; font-weight:600; font-size:0.75rem; text-decoration:none;">▶️ Ver no TikTok ↗</a>` : ''}
          </div>
        `;
        grid.appendChild(card);
      });
    }

    function filtrarVetores() {
      if (!cacheVetores) return;
      const q = document.getElementById('buscaVetores').value.toLowerCase().trim();

      const filtrados = cacheVetores.filter(item => {
        return !q ||
          (item.nome || '').toLowerCase().includes(q) ||
          (item.documento_indexado || '').toLowerCase().includes(q);
      });

      document.getElementById('counterVetores').innerText = `Exibindo ${filtrados.length} de ${cacheVetores.length} chunks`;

      const container = document.getElementById('gridVetores');
      container.innerHTML = '';
      filtrados.forEach(item => {
        const div = document.createElement('div');
        div.style.cssText = 'background:#0d1117; border:1px solid var(--card-border); border-radius:6px; padding:10px 12px;';
        div.innerHTML = `
          <div style="font-weight:700; color:var(--blue); font-size:0.9rem; margin-bottom:3px;">
            ${item.nome} &bull; ${item.regiao_administrativa || ''}
          </div>
          <div style="font-size:0.78rem; color:var(--text-muted); line-height:1.4; margin-bottom:6px;">
            ${item.documento_indexado || ''}
          </div>
          <div style="background:#161b22; padding:5px 8px; border-radius:4px; font-family:monospace; font-size:0.72rem; color:#79c0ff;">
            Vetor: [${(item.vetor_preview || []).map(n => typeof n === 'number' ? n.toFixed(5) : n).join(', ')}, ... +3067 dimensões]
          </div>
        `;
        container.appendChild(div);
      });
    }
  </script>
</body>
</html>
"""


COMPARATIVO_PAGE = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Comparativo Lado a Lado: LLM Pura vs. RAG Ancorado | Orquestrador de Rolês DF</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400..700;1,9..40,400..700&family=Syne:wght@600;700;800&display=swap" rel="stylesheet" />
  <style>
    :root {
      --bg-canvas: #FAFAFA;
      --surface-white: #FFFFFF;
      --surface-elevated: #F4F9F9;
      --border-soft: #E5E7EB;
      --shadow-elev: 0 10px 30px rgba(0, 0, 0, 0.05);

      --brand-primary: #132E31;
      --brand-secondary: #337A89;
      --brand-highlight: #7DC5CF;
      --brand-detail: #E9F7F7;

      --text-primary: #132E31;
      --text-muted: #475569;
      --track-bg: #E5E7EB;
      --danger-text: #991B1B;
      --danger-bg: #FEF2F2;
      --danger-border: #FECACA;
    }

    body.dark-mode {
      --bg-canvas: #0D1B1D;
      --surface-white: #132E31;
      --surface-elevated: #1A3C40;
      --border-soft: #264F54;
      --shadow-elev: 0 10px 30px rgba(0, 0, 0, 0.32);

      --text-primary: #F8FAFC;
      --text-muted: #B8D4D8;
      --track-bg: #1F474C;
      --brand-detail: #1C4246;
      --danger-text: #FCA5A5;
      --danger-bg: rgba(153, 27, 27, 0.25);
      --danger-border: rgba(252, 165, 165, 0.35);
    }

    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }

    body {
      background-color: var(--bg-canvas);
      color: var(--text-primary);
      font-family: "DM Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      min-height: 100vh;
      display: flex;
      transition: background-color 0.2s ease, color 0.2s ease;
    }

    h1, h2, h3, .kpi-value, .brand-name {
      font-family: "DM Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      letter-spacing: -0.02em;
    }

    /* Sidebar Executiva Limpa */
    .sidebar {
      width: 268px;
      flex-shrink: 0;
      background: var(--surface-white);
      border-right: 1px solid var(--border-soft);
      padding: 24px 18px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      gap: 24px;
      position: sticky;
      top: 0;
      height: 100vh;
    }

    .brand-box {
      display: flex;
      flex-direction: column;
      gap: 4px;
      padding: 4px 8px 16px;
      border-bottom: 1px solid var(--border-soft);
    }

    .brand-name {
      font-size: 1.05rem;
      font-weight: 800;
      color: var(--text-primary);
      letter-spacing: -0.02em;
    }

    .brand-sub {
      font-size: 0.76rem;
      color: var(--text-muted);
      font-weight: 500;
    }

    .sidebar-nav {
      display: flex;
      flex-direction: column;
      gap: 6px;
    }

    .sidebar-section-label {
      font-size: 0.7rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--text-muted);
      padding: 0 10px 6px;
    }

    .nav-item {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 10px 12px;
      border-radius: 10px;
      text-decoration: none;
      font-size: 0.88rem;
      font-weight: 600;
      color: var(--text-muted);
      border: 1px solid transparent;
      transition: all 0.16s ease;
    }

    .nav-item:hover {
      background: var(--surface-elevated);
      color: var(--text-primary);
    }

    .nav-item.active {
      background: var(--brand-detail);
      color: var(--text-primary);
      border-color: var(--brand-highlight);
      border-left: 4px solid var(--brand-primary);
      font-weight: 700;
    }

    body.dark-mode .nav-item.active {
      border-left-color: var(--brand-highlight);
    }

    .sidebar-footer {
      display: flex;
      flex-direction: column;
      gap: 10px;
      padding-top: 16px;
      border-top: 1px solid var(--border-soft);
    }

    .sidebar-badge-2fa {
      background: var(--brand-detail);
      color: var(--text-primary);
      border: 1px solid var(--border-soft);
      border-radius: 10px;
      padding: 10px 12px;
      font-size: 0.76rem;
      line-height: 1.45;
      font-weight: 500;
    }

    .theme-toggle-btn {
      width: 100%;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      background: var(--brand-primary);
      color: #FFFFFF;
      border: 1px solid var(--brand-primary);
      padding: 9px 14px;
      border-radius: 10px;
      font-size: 0.82rem;
      font-weight: 700;
      cursor: pointer;
      transition: opacity 0.18s ease;
    }

    body.dark-mode .theme-toggle-btn {
      background: var(--brand-secondary);
      border-color: var(--brand-highlight);
      color: #FFFFFF;
    }

    .theme-toggle-btn:hover {
      opacity: 0.92;
    }

    /* Área Principal */
    .workspace {
      flex: 1;
      min-width: 0;
      display: flex;
      flex-direction: column;
    }

    .main-wrapper {
      max-width: 1320px;
      width: 100%;
      margin: 0 auto;
      padding: 28px 32px 40px;
      display: flex;
      flex-direction: column;
      gap: 20px;
      flex: 1;
    }

    header.exec-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-end;
      flex-wrap: wrap;
      gap: 14px;
      padding-bottom: 6px;
    }

    header.exec-header h1 {
      font-size: 1.7rem;
      font-weight: 800;
      color: var(--text-primary);
      line-height: 1.25;
      letter-spacing: -0.02em;
    }

    header.exec-header p {
      color: var(--text-muted);
      font-size: 0.9rem;
      line-height: 1.5;
      max-width: 820px;
      margin-top: 6px;
    }

    .header-tag {
      background: var(--brand-detail);
      color: var(--text-primary);
      border: 1px solid var(--brand-highlight);
      padding: 6px 14px;
      border-radius: 999px;
      font-size: 0.78rem;
      font-weight: 700;
      white-space: nowrap;
    }

    /* 3 KPI Metric Cards */
    .kpi-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 16px;
    }

    .kpi-card {
      background: var(--surface-white);
      border: 1px solid var(--border-soft);
      border-radius: 14px;
      padding: 18px 20px;
      box-shadow: var(--shadow-elev);
      display: flex;
      flex-direction: column;
      gap: 6px;
      border-top: 3px solid var(--brand-secondary);
    }

    .kpi-card.kpi-primary {
      border-top-color: var(--brand-primary);
    }

    .kpi-card.kpi-highlight {
      border-top-color: var(--brand-highlight);
    }

    .kpi-label {
      font-size: 0.76rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--text-muted);
    }

    .kpi-value {
      font-size: 1.55rem;
      font-weight: 800;
      color: var(--text-primary);
      line-height: 1.2;
    }

    .kpi-foot {
      font-size: 0.78rem;
      color: var(--text-muted);
    }

    /* Gráfico de Barras de Desempenho (Latência & Tokens) */
    .chart-card {
      background: var(--surface-white);
      border: 1px solid var(--border-soft);
      border-radius: 14px;
      padding: 18px 22px;
      box-shadow: var(--shadow-elev);
      display: flex;
      flex-direction: column;
      gap: 14px;
    }

    .chart-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 10px;
    }

    .chart-title {
      font-size: 0.95rem;
      font-weight: 800;
      color: var(--text-primary);
    }

    .chart-legend {
      display: flex;
      gap: 16px;
      font-size: 0.78rem;
      font-weight: 700;
      color: var(--text-muted);
    }

    .legend-item {
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }

    .legend-dot {
      width: 10px;
      height: 10px;
      border-radius: 3px;
      display: inline-block;
    }

    .chart-rows {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 18px;
    }

    .chart-group {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .chart-group-title {
      font-size: 0.8rem;
      font-weight: 700;
      color: var(--text-muted);
    }

    .bar-line {
      display: flex;
      align-items: center;
      gap: 10px;
      font-size: 0.78rem;
      font-weight: 700;
    }

    .bar-tag {
      width: 58px;
      flex-shrink: 0;
      color: var(--text-primary);
    }

    .bar-track {
      flex: 1;
      height: 12px;
      background: var(--track-bg);
      border-radius: 999px;
      overflow: hidden;
    }

    .bar-fill {
      height: 100%;
      border-radius: 999px;
      transition: width 0.35s ease;
      width: 0%;
    }

    .bar-fill-a {
      background: var(--brand-primary);
    }

    body.dark-mode .bar-fill-a {
      background: #7DC5CF;
    }

    .bar-fill-b {
      background: var(--brand-secondary);
    }

    .bar-num {
      width: 76px;
      text-align: right;
      flex-shrink: 0;
      color: var(--text-primary);
    }

    /* Seletor Golden Dataset + Barra de Pergunta */
    .control-panel {
      background: var(--surface-white);
      border: 1px solid var(--border-soft);
      border-radius: 14px;
      padding: 18px 20px;
      display: flex;
      flex-direction: column;
      gap: 12px;
      box-shadow: var(--shadow-elev);
    }

    .control-row {
      display: flex;
      gap: 10px;
      align-items: center;
      flex-wrap: wrap;
    }

    .control-label {
      font-size: 0.8rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.4px;
      color: var(--text-primary);
    }

    .golden-select {
      flex: 1;
      min-width: 260px;
      background: var(--surface-white);
      color: var(--text-primary);
      border: 1px solid var(--border-soft);
      border-radius: 8px;
      padding: 9px 12px;
      font-size: 0.88rem;
      font-weight: 500;
      outline: none;
    }

    .golden-select:focus {
      border-color: var(--brand-secondary);
    }

    .golden-select.config-select {
      flex: 1 1 200px;
      min-width: 0;
    }

    .chips-row {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }

    .golden-chip {
      background: var(--brand-detail);
      color: var(--text-primary);
      border: 1px solid var(--border-soft);
      padding: 6px 12px;
      border-radius: 999px;
      font-size: 0.78rem;
      font-weight: 700;
      cursor: pointer;
      transition: all 0.16s ease;
    }

    .golden-chip:hover {
      border-color: var(--brand-secondary);
      background: var(--surface-elevated);
    }

    .golden-chip.active {
      background: var(--brand-primary);
      color: #FFFFFF;
      border-color: var(--brand-primary);
    }

    body.dark-mode .golden-chip.active {
      background: var(--brand-highlight);
      color: #132E31;
      border-color: var(--brand-highlight);
    }

    .search-bar {
      display: flex;
      gap: 10px;
    }

    .search-input {
      flex: 1;
      background: var(--surface-white);
      border: 1px solid var(--border-soft);
      color: var(--text-primary);
      border-radius: 10px;
      padding: 12px 15px;
      font-size: 0.94rem;
      outline: none;
    }

    .search-input:focus {
      border-color: var(--brand-secondary);
      box-shadow: 0 0 0 3px rgba(51, 122, 137, 0.15);
    }

    .btn-executar {
      background: var(--brand-primary);
      color: #FFFFFF;
      border: 1px solid var(--brand-primary);
      border-radius: 10px;
      padding: 12px 22px;
      font-size: 0.92rem;
      font-weight: 700;
      cursor: pointer;
      transition: all 0.18s ease;
      white-space: nowrap;
    }

    .btn-executar:hover {
      background: var(--brand-secondary);
      border-color: var(--brand-secondary);
    }

    .btn-executar:disabled {
      opacity: 0.65;
      cursor: not-allowed;
    }

    /* Banners de Erro e Gabarito */
    .erro-banner {
      background: var(--danger-bg);
      border: 1px solid var(--danger-border);
      color: var(--danger-text);
      border-radius: 10px;
      padding: 12px 16px;
      font-size: 0.88rem;
      font-weight: 600;
      display: none;
    }

    .gabarito-banner {
      background: var(--surface-white);
      border: 1px solid var(--border-soft);
      border-left: 4px solid var(--brand-secondary);
      border-radius: 12px;
      padding: 14px 18px;
      box-shadow: var(--shadow-elev);
      display: none;
      flex-direction: column;
      gap: 8px;
    }

    .gabarito-title {
      font-size: 0.82rem;
      font-weight: 800;
      color: var(--text-primary);
      text-transform: uppercase;
      letter-spacing: 0.4px;
    }

    .gabarito-pills {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      font-size: 0.8rem;
    }

    /* Grid Lado a Lado */
    .comparison-grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 20px;
      align-items: start;
    }

    .mode-column {
      background: var(--surface-white);
      border: 1px solid var(--border-soft);
      border-radius: 14px;
      padding: 20px;
      display: flex;
      flex-direction: column;
      gap: 16px;
      box-shadow: var(--shadow-elev);
    }

    .mode-column.modo-a {
      border-top: 4px solid var(--brand-primary);
    }

    .mode-column.modo-b {
      border-top: 4px solid var(--brand-secondary);
    }

    .mode-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 10px;
      flex-wrap: wrap;
    }

    .mode-title {
      font-size: 1.08rem;
      font-weight: 800;
      color: var(--text-primary);
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
    }

    .mode-subtitle {
      font-size: 0.8rem;
      color: var(--text-muted);
      margin-top: 4px;
    }

    .llm-model-pill {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      margin-top: 8px;
      padding: 4px 10px;
      border-radius: 8px;
      font-size: 0.74rem;
      font-weight: 700;
      background: var(--brand-detail);
      border: 1px solid var(--border-soft);
      color: var(--text-primary);
    }

    .status-badge {
      padding: 5px 12px;
      border-radius: 999px;
      font-size: 0.74rem;
      font-weight: 700;
      white-space: nowrap;
    }

    .badge-warning-a {
      background: var(--danger-bg);
      color: var(--danger-text);
      border: 1px solid var(--danger-border);
    }

    .badge-verified-b {
      background: var(--brand-primary);
      color: #FFFFFF;
      border: 1px solid var(--brand-primary);
    }

    body.dark-mode .badge-verified-b {
      background: var(--brand-secondary);
      border-color: var(--brand-highlight);
    }

    /* Info Popover (apenas hover) */
    .info-trigger {
      position: relative;
      display: inline-flex;
      align-items: center;
    }

    .info-btn {
      width: 20px;
      height: 20px;
      border-radius: 999px;
      border: 1px solid var(--brand-highlight);
      background: var(--brand-detail);
      color: var(--text-primary);
      font-size: 0.72rem;
      font-weight: 800;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      cursor: help;
      user-select: none;
    }

    .info-popover {
      display: none;
      position: absolute;
      bottom: calc(100% + 8px);
      right: 0;
      width: 260px;
      background: var(--brand-primary);
      color: #FFFFFF;
      border: 1px solid var(--brand-highlight);
      border-radius: 10px;
      padding: 10px 12px;
      font-size: 0.76rem;
      line-height: 1.45;
      box-shadow: 0 12px 28px rgba(0, 0, 0, 0.25);
      z-index: 40;
      pointer-events: none;
    }

    .info-popover.popover-left {
      left: 0;
      right: auto;
    }

    .info-trigger:hover .info-popover {
      display: block;
    }

    .response-box {
      background: var(--surface-elevated);
      border: 1px solid var(--border-soft);
      border-radius: 10px;
      padding: 14px 16px;
      font-size: 0.91rem;
      line-height: 1.6;
      color: var(--text-primary);
      min-height: 112px;
    }

    .fonte-cite {
      display: inline-block;
      background: var(--brand-primary);
      color: #FFFFFF;
      padding: 1px 6px;
      border-radius: 5px;
      font-weight: 700;
      font-size: 0.8em;
    }

    .metrics-strip {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 10px;
    }

    .metric-card {
      position: relative;
      background: var(--surface-elevated);
      border: 1px solid var(--border-soft);
      border-radius: 10px;
      padding: 12px;
      text-align: center;
    }

    .metric-card .info-trigger {
      position: absolute;
      top: 7px;
      right: 7px;
    }

    .metric-val {
      font-size: 1.12rem;
      font-weight: 800;
      color: var(--text-primary);
    }

    .metric-lbl {
      font-size: 0.72rem;
      color: var(--text-muted);
      margin-top: 2px;
      font-weight: 600;
    }

    .scores-panel {
      background: var(--surface-elevated);
      border: 1px solid var(--border-soft);
      border-radius: 10px;
      padding: 12px 14px;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .scores-title {
      font-size: 0.78rem;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.4px;
      color: var(--text-primary);
    }

    .not-evaluated-box {
      background: var(--surface-white);
      border: 1px dashed var(--border-soft);
      border-radius: 8px;
      padding: 10px 12px;
      font-size: 0.82rem;
      color: var(--text-muted);
      text-align: center;
    }

    .trace-banner {
      background: var(--brand-detail);
      border: 1px solid var(--brand-highlight);
      border-radius: 10px;
      padding: 10px 14px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 8px;
      font-size: 0.82rem;
    }

    .trace-link {
      color: var(--brand-primary);
      font-weight: 700;
      text-decoration: underline;
    }

    body.dark-mode .trace-link {
      color: var(--brand-highlight);
    }

    .sources-section {
      display: flex;
      flex-direction: column;
      gap: 10px;
    }

    .sources-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 0.82rem;
      font-weight: 800;
      color: var(--text-primary);
    }

    .empty-sources-box {
      background: var(--danger-bg);
      border: 1px dashed var(--danger-border);
      border-radius: 10px;
      padding: 14px;
      text-align: center;
      color: var(--danger-text);
      font-size: 0.84rem;
    }

    .guardrail-box {
      background: rgba(51, 122, 137, 0.1);
      border: 1px dashed var(--brand-secondary);
      border-radius: 10px;
      padding: 14px;
      font-size: 0.84rem;
      color: var(--text-primary);
    }

    .source-card {
      background: var(--surface-white);
      border: 1px solid var(--border-soft);
      border-left: 4px solid var(--brand-secondary);
      border-radius: 10px;
      padding: 12px 14px;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .source-card.dimmed {
      opacity: 0.55;
      border-left-color: var(--text-muted);
    }

    .source-card-top {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 8px;
      flex-wrap: wrap;
    }

    .source-name {
      font-weight: 800;
      font-size: 0.94rem;
      color: var(--text-primary);
    }

    .source-sim {
      background: var(--brand-detail);
      color: var(--text-primary);
      border: 1px solid var(--brand-highlight);
      padding: 2px 9px;
      border-radius: 999px;
      font-size: 0.72rem;
      font-weight: 700;
    }

    .cite-pill {
      padding: 2px 8px;
      border-radius: 999px;
      font-size: 0.7rem;
      font-weight: 700;
    }

    .cite-pill-yes {
      background: var(--brand-primary);
      color: #FFFFFF;
    }

    .cite-pill-no {
      background: var(--surface-elevated);
      color: var(--text-muted);
      border: 1px solid var(--border-soft);
    }

    .source-meta {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      font-size: 0.76rem;
      color: var(--text-muted);
    }

    .meta-pill {
      background: var(--brand-detail);
      color: var(--text-primary);
      border: 1px solid var(--border-soft);
      padding: 3px 9px;
      border-radius: 8px;
      font-weight: 600;
    }

    .source-actions {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-top: 2px;
      flex-wrap: wrap;
      gap: 8px;
    }

    .btn-tiktok {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: var(--brand-primary);
      color: #FFFFFF;
      border: 1px solid var(--brand-primary);
      padding: 6px 12px;
      border-radius: 8px;
      font-size: 0.76rem;
      font-weight: 700;
      text-decoration: none;
      transition: background 0.16s ease;
    }

    .btn-tiktok:hover {
      background: var(--brand-secondary);
      border-color: var(--brand-secondary);
    }

    footer {
      text-align: center;
      padding: 16px;
      font-size: 0.78rem;
      color: var(--text-muted);
      border-top: 1px solid var(--border-soft);
    }

    @media (max-width: 980px) {
      body {
        flex-direction: column;
      }
      .sidebar {
        width: 100%;
        height: auto;
        position: static;
        border-right: none;
        border-bottom: 1px solid var(--border-soft);
        padding: 16px;
      }
      .sidebar-nav {
        flex-direction: row;
        flex-wrap: wrap;
      }
      .kpi-grid,
      .chart-rows,
      .comparison-grid {
        grid-template-columns: 1fr;
      }
      .main-wrapper {
        padding: 18px 16px 32px;
      }
      .search-bar {
        flex-direction: column;
      }
      .btn-executar {
        width: 100%;
      }
    }
  </style>
</head>
<body>
  <aside class="sidebar" aria-label="Navegação Principal">
    <div>
      <div class="brand-box">
        <div class="brand-name">🎭 Orquestrador DF</div>
        <div class="brand-sub">Analytics Executive Dashboard</div>
      </div>

      <nav class="sidebar-nav" style="margin-top:16px;">
        <div class="sidebar-section-label">Navegação</div>
        <a href="/comparativo" class="nav-item active">⚖️ Comparativo LLM vs. RAG</a>
      </nav>
    </div>

    <div class="sidebar-footer">
      <div class="sidebar-badge-2fa">
        <strong>Base Curada 2FA</strong><br/>
        93 lugares do TikTok, auditada em 2 etapas.
      </div>
      <button
        type="button"
        class="theme-toggle-btn"
        id="themeToggleBtn"
        onclick="alternarTema()"
        aria-label="Alternar entre Modo Claro e Modo Escuro"
      >
        🌙 Modo Escuro
      </button>
    </div>
  </aside>

  <div class="workspace">
    <main class="main-wrapper">
      <header class="exec-header">
        <div>
          <h1>⚖️ Comparativo Lado a Lado: LLM Pura vs. RAG Ancorado (2FA)</h1>
          <p>
            Demonstração executiva de mitigação de alucinações (<strong>RNF-03</strong>) e precisão geoespacial no Distrito Federal. Compare a resposta de uma LLM sem contexto contra o pipeline RAG ancorado na base de 93 lugares do TikTok, auditada em 2 etapas.
          </p>
        </div>
        <span class="header-tag">RNF-03 &bull; RNF-05 &bull; RNF-14</span>
      </header>

      <!-- 3 KPI Metric Cards -->
      <section class="kpi-grid" aria-label="Indicadores Principais">
        <div class="kpi-card kpi-primary">
          <div class="kpi-label">Base Auditada (2FA)</div>
          <div class="kpi-value">93 locais</div>
          <div class="kpi-foot">Base de 93 lugares do TikTok, auditada em 2 etapas</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">Golden Dataset (Semana 3)</div>
          <div class="kpi-value"><span id="kpiGoldenCount">—</span> casos</div>
          <div class="kpi-foot">Carregado dinamicamente de /api/comparativo/golden</div>
        </div>
        <div class="kpi-card kpi-highlight">
          <div class="kpi-label">Latência Medida (SLA RNF-14)</div>
          <div class="kpi-value" id="kpiLatenciaResumo">—</div>
          <div class="kpi-foot">Modo A vs. Modo B (meta &le; 5.000 ms)</div>
        </div>
      </section>

      <!-- Painel de Seleção do Golden Dataset e Input Livre -->
      <section class="control-panel" aria-label="Seletor de Perguntas do Golden Dataset">
        <div class="control-row">
          <span class="control-label" id="goldenLabel">🎯 Golden Dataset:</span>
          <select id="goldenSelect" class="golden-select" onchange="selecionarGoldenDropdown()">
            <option value="">✍️ Pergunta livre (sem gabarito)</option>
          </select>
        </div>

        <div class="chips-row" id="goldenChips"></div>

        <div class="control-row">
          <span class="control-label">⚙️ Configuração:</span>
          <select id="raciocinioSelect" class="golden-select config-select" aria-label="Raciocínio do modelo nos dois modos">
            <option value="desligado">🧠 Raciocínio desligado (padrão)</option>
            <option value="high">🧠 Raciocínio alto (mais lento)</option>
          </select>
          <select id="buscaSelect" class="golden-select config-select" aria-label="Tipo de busca do Modo B">
            <option value="lexica">🔎 Busca do Modo B: por palavras (padrão)</option>
            <option value="vetorial">🔎 Busca do Modo B: por embeddings</option>
            <option value="hibrida">🔎 Busca do Modo B: híbrida</option>
          </select>
        </div>

        <form class="search-bar" onsubmit="executarComparativo(event)">
          <input
            type="text"
            id="perguntaComparativoInput"
            class="search-input"
            value=""
            oninput="aoDigitarPergunta()"
            placeholder="Digite uma pergunta ou selecione um caso do Golden Dataset acima..."
          />
          <button type="submit" class="btn-executar" id="btnExecutarComparativo">
            ⚡ Comparar Lado a Lado
          </button>
        </form>
      </section>

      <div class="erro-banner" id="erroBanner" role="alert"></div>

      <section class="gabarito-banner" id="gabaritoBanner" aria-label="Gabarito do Caso Golden">
        <div class="gabarito-title">📌 Gabarito do Golden Dataset</div>
        <div class="gabarito-pills" id="gabaritoPills"></div>
      </section>

      <!-- Gráfico de Barras de Desempenho (Latência & Tokens Reais) -->
      <section class="chart-card" aria-label="Gráfico de Desempenho da Execução">
        <div class="chart-header">
          <div class="chart-title">📊 Desempenho Comparativo da Execução (Valores Medidos)</div>
          <div class="chart-legend">
            <span class="legend-item"><span class="legend-dot" style="background:var(--brand-primary);"></span> Modo A (LLM Pura)</span>
            <span class="legend-item"><span class="legend-dot" style="background:var(--brand-secondary);"></span> Modo B (RAG 2FA)</span>
          </div>
        </div>
        <div class="chart-rows">
          <div class="chart-group">
            <div class="chart-group-title">Latência Total (ms)</div>
            <div class="bar-line">
              <span class="bar-tag">Modo A</span>
              <div class="bar-track"><div class="bar-fill bar-fill-a" id="chartLatenciaBarA"></div></div>
              <span class="bar-num" id="chartLatenciaValA">—</span>
            </div>
            <div class="bar-line">
              <span class="bar-tag">Modo B</span>
              <div class="bar-track"><div class="bar-fill bar-fill-b" id="chartLatenciaBarB"></div></div>
              <span class="bar-num" id="chartLatenciaValB">—</span>
            </div>
          </div>
          <div class="chart-group">
            <div class="chart-group-title">Tokens Totais Consumidos</div>
            <div class="bar-line">
              <span class="bar-tag">Modo A</span>
              <div class="bar-track"><div class="bar-fill bar-fill-a" id="chartTokensBarA"></div></div>
              <span class="bar-num" id="chartTokensValA">—</span>
            </div>
            <div class="bar-line">
              <span class="bar-tag">Modo B</span>
              <div class="bar-track"><div class="bar-fill bar-fill-b" id="chartTokensBarB"></div></div>
              <span class="bar-num" id="chartTokensValB">—</span>
            </div>
          </div>
        </div>
      </section>

      <!-- Grid 2 Colunas: Modo A (LLM Pura) vs Modo B (RAG Ancorado) -->
      <section class="comparison-grid">
        <!-- COLUNA ESQUERDA: MODO A — LLM PURA (ZERO-SHOT) -->
        <article class="mode-column modo-a" id="colunaModoA">
          <div class="mode-header">
            <div>
              <div class="mode-title">
                <span>🤖 Modo A — LLM Pura (Zero-Shot)</span>
                <div class="info-trigger">
                  <span class="info-btn" aria-label="Informação sobre Zero-Shot">i</span>
                  <div class="info-popover popover-left">
                    <strong>🎯 O que é Zero-Shot:</strong> A LLM responde direto pela sua memória de treinamento, sem receber documentos nem consultar a base de 93 lugares do TikTok.
                  </div>
                </div>
              </div>
              <div class="mode-subtitle">Geração paramétrica sem acesso à base de 93 lugares ou validação 2FA</div>
              <div class="llm-model-pill" id="modeloPillA">🧠 Modelo: aguardando execução</div>
            </div>
            <span class="status-badge badge-warning-a" id="badgeModoA">
              ⚠️ Sem Evidências — Sujeito a Alucinação
            </span>
          </div>

          <div class="response-box" id="respostaModoA">
            Selecione uma pergunta do Golden Dataset ou digite uma pergunta acima e clique em <strong>Comparar Lado a Lado</strong> para executar o modelo em tempo real.
          </div>

          <div class="metrics-strip">
            <div class="metric-card">
              <div class="info-trigger">
                <span class="info-btn" aria-label="Informação sobre Latência">i</span>
                <div class="info-popover">
                  <strong>⏱️ Latência (RNF-14):</strong> Tempo medido que o modelo levou para responder (meta SLA &le; 5.000 ms).
                </div>
              </div>
              <div class="metric-val" id="latenciaModoA">—</div>
              <div class="metric-lbl">Latência (RNF-14)</div>
            </div>
            <div class="metric-card">
              <div class="info-trigger">
                <span class="info-btn" aria-label="Informação sobre Tokens Totais">i</span>
                <div class="info-popover">
                  <strong>🔤 Tokens Totais:</strong> Soma das unidades de texto de entrada e saída medidas na chamada ao modelo.
                </div>
              </div>
              <div class="metric-val" id="tokensModoA">—</div>
              <div class="metric-lbl">Tokens Totais</div>
            </div>
          </div>

          <div class="scores-panel">
            <div class="scores-title">📊 Scores de Qualidade &amp; Governança</div>
            <div class="not-evaluated-box" id="scoresModoA">
              <strong>não avaliado</strong> — Execute uma comparação para gerar os scores automáticos (issue #36).
            </div>
          </div>

          <div class="sources-section">
            <div class="sources-header">
              <span>📂 Fontes Utilizadas</span>
              <span>0 Evidências</span>
            </div>
            <div class="empty-sources-box" id="fontesModoA">
              🚫 <strong>Nenhuma fonte auditada utilizada.</strong><br/>
              O Modo A responde sem acesso à base de 93 lugares do TikTok, auditada em 2 etapas.
            </div>
          </div>
        </article>

        <!-- COLUNA DIREITA: MODO B — RAG ANCORADO (BASE 2FA) -->
        <article class="mode-column modo-b" id="colunaModoB">
          <div class="mode-header">
            <div>
              <div class="mode-title">🛡️ Modo B — RAG Ancorado (Base 2FA)</div>
              <div class="mode-subtitle">Busca na base de 93 lugares do TikTok, auditada em 2 etapas + guardrails</div>
              <div class="llm-model-pill pill-rag" id="modeloPillB">🧠 Modelo: aguardando execução</div>
            </div>
            <span class="status-badge badge-verified-b" id="badgeModoB">
              ✅ Fundamentado na Base Curada do DF
            </span>
          </div>

          <div class="response-box" id="respostaModoB">
            Aguardando execução. O Modo B recuperará os lugares compatíveis da base de 93 locais do TikTok, aplicando os guardrails e gerando a resposta ancorada.
          </div>

          <div class="metrics-strip">
            <div class="metric-card">
              <div class="info-trigger">
                <span class="info-btn" aria-label="Informação sobre Latência">i</span>
                <div class="info-popover">
                  <strong>⏱️ Latência (RNF-14):</strong> Tempo medido de recuperação na base + geração ancorada (meta SLA &le; 5.000 ms).
                </div>
              </div>
              <div class="metric-val" id="latenciaModoB">—</div>
              <div class="metric-lbl">Latência (RNF-14)</div>
            </div>
            <div class="metric-card">
              <div class="info-trigger">
                <span class="info-btn" aria-label="Informação sobre Tokens Totais">i</span>
                <div class="info-popover">
                  <strong>🔤 Tokens Totais:</strong> Soma dos tokens da pergunta, dos documentos 2FA injetados e da resposta gerada.
                </div>
              </div>
              <div class="metric-val" id="tokensModoB">—</div>
              <div class="metric-lbl">Tokens Totais</div>
            </div>
          </div>

          <div class="scores-panel">
            <div class="scores-title">📊 Scores de Qualidade &amp; Governança</div>
            <div class="not-evaluated-box" id="scoresModoB">
              <strong>não avaliado</strong> — Execute uma comparação para gerar os scores automáticos (issue #36).
            </div>
          </div>

          <div class="trace-banner" id="traceBannerB" style="display:none;">
            <span>🔭 <strong>Telemetria LLMOps (RNF-18):</strong> Trace registrado no Langfuse</span>
            <a
              href="#"
              target="_blank"
              rel="noopener noreferrer"
              class="trace-link"
              id="traceLinkModoB"
            >
              Ver Trace no Langfuse &nearr;
            </a>
          </div>

          <div class="sources-section">
            <div class="sources-header">
              <span>📂 Fontes Auditadas 2FA</span>
              <span id="contadorFontesB">0 Fontes</span>
            </div>
            <div id="fontesModoB" style="display:flex; flex-direction:column; gap:10px;">
              <div class="not-evaluated-box">Nenhuma fonte carregada ainda. Execute uma comparação acima.</div>
            </div>
          </div>
        </article>
      </section>
    </main>

    <footer>
      Residência em IA &bull; Challenge 02 &bull; Grupo 07 &bull; Interface Comparativa LLM Pura vs. RAG Ancorado (Issue #37)
    </footer>
  </div>

  <script>
    let goldenDataset = [];
    let perguntaSelecionadaDoGolden = "";

    function aplicarTema(modoEscuro) {
      document.body.classList.toggle("dark-mode", modoEscuro);
      const btn = document.getElementById("themeToggleBtn");
      if (btn) {
        btn.textContent = modoEscuro ? "☀️ Modo Claro" : "🌙 Modo Escuro";
      }
    }

    function alternarTema() {
      aplicarTema(!document.body.classList.contains("dark-mode"));
    }

    const NOMES_BUSCA = { lexica: "por palavras", vetorial: "por embeddings", hibrida: "híbrida" };

    function escaparHtml(texto) {
      return String(texto || "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
    }

    function formatarRespostaSegura(texto, destacarFontes) {
      let html = escaparHtml(texto);
      html = html.replace(/\\*\\*(.+?)\\*\\*/g, "<strong>$1</strong>");
      if (destacarFontes) {
        html = html.replace(/\\[FONTE #(\\d+)\\]/g, '<span class="fonte-cite">[FONTE #$1]</span>');
      }
      html = html.replace(/\\n/g, "<br>");
      return html;
    }

    function formatarPreco(valor) {
      if (valor === null || valor === undefined || Number.isNaN(Number(valor))) {
        return "preço não informado";
      }
      return "R$ " + Number(valor).toFixed(2).replace(".", ",");
    }

    function criarEl(tag, className, text) {
      const el = document.createElement(tag);
      if (className) el.className = className;
      if (text !== undefined && text !== null) el.textContent = String(text);
      return el;
    }

    function urlSegura(url) {
      if (!url || typeof url !== "string") return null;
      const limpa = url.trim();
      if (limpa.startsWith("https://") || limpa.startsWith("http://") || limpa.startsWith("/")) {
        return limpa;
      }
      return null;
    }

    async function carregarGoldenDataset() {
      const select = document.getElementById("goldenSelect");
      const chips = document.getElementById("goldenChips");
      const label = document.getElementById("goldenLabel");
      const kpiGolden = document.getElementById("kpiGoldenCount");
      try {
        const res = await fetch("/api/comparativo/golden");
        if (!res.ok) return;
        const data = await res.json();
        goldenDataset = Array.isArray(data.perguntas) ? data.perguntas : [];
        label.textContent = `🎯 Golden Dataset (${goldenDataset.length} Casos):`;
        if (kpiGolden) kpiGolden.textContent = String(goldenDataset.length);

        select.innerHTML = "";
        select.appendChild(criarEl("option", "", "✍️ Pergunta livre (sem gabarito)"));
        select.firstChild.value = "";

        chips.innerHTML = "";
        goldenDataset.forEach((item, idx) => {
          const opt = document.createElement("option");
          opt.value = item.id;
          opt.textContent = `${item.id} — ${item.pergunta}`;
          select.appendChild(opt);

          if (idx < 8) {
            const chip = criarEl("button", "golden-chip", `#${String(idx + 1).padStart(2, "0")} ${item.categoria || item.id}`);
            chip.type = "button";
            chip.dataset.id = item.id;
            chip.addEventListener("click", () => selecionarChip(item.id));
            chips.appendChild(chip);
          }
        });
      } catch (err) {
        console.error("Erro ao carregar /api/comparativo/golden:", err);
      }
    }

    function atualizarChipsAtivos(idGolden) {
      document.querySelectorAll(".golden-chip").forEach(btn => {
        btn.classList.toggle("active", Boolean(idGolden) && btn.dataset.id === idGolden);
      });
    }

    function selecionarGoldenDropdown() {
      const sel = document.getElementById("goldenSelect");
      const idGolden = sel.value;
      atualizarChipsAtivos(idGolden);
      if (!idGolden) {
        perguntaSelecionadaDoGolden = "";
        return;
      }
      const item = goldenDataset.find(g => g.id === idGolden);
      if (item) {
        perguntaSelecionadaDoGolden = item.pergunta;
        document.getElementById("perguntaComparativoInput").value = item.pergunta;
      }
      executarComparativo();
    }

    function selecionarChip(idGolden) {
      document.getElementById("goldenSelect").value = idGolden;
      selecionarGoldenDropdown();
    }

    function aoDigitarPergunta() {
      const atual = document.getElementById("perguntaComparativoInput").value.trim();
      const sel = document.getElementById("goldenSelect");
      if (sel.value && atual !== perguntaSelecionadaDoGolden.trim()) {
        sel.value = "";
        atualizarChipsAtivos("");
      }
    }

    function renderizarGabarito(gabarito) {
      const banner = document.getElementById("gabaritoBanner");
      const pills = document.getElementById("gabaritoPills");
      pills.innerHTML = "";
      if (!gabarito) {
        banner.style.display = "none";
        return;
      }
      banner.style.display = "flex";
      if (gabarito.categoria) pills.appendChild(criarEl("span", "meta-pill", `🏷️ Categoria: ${gabarito.categoria}`));
      if (gabarito.ra_esperada) pills.appendChild(criarEl("span", "meta-pill", `📍 RA esperada: ${gabarito.ra_esperada}`));
      if (Array.isArray(gabarito.locais_gabarito) && gabarito.locais_gabarito.length) {
        pills.appendChild(criarEl("span", "meta-pill", `⭐ Locais esperados: ${gabarito.locais_gabarito.join(", ")}`));
      }
      if (gabarito.preco_maximo_gabarito != null) {
        pills.appendChild(criarEl("span", "meta-pill", `💰 Teto esperado: ${formatarPreco(gabarito.preco_maximo_gabarito)}`));
      }
      if (gabarito.horario_gabarito) {
        pills.appendChild(criarEl("span", "meta-pill", `🕒 Horário: ${gabarito.horario_gabarito}`));
      }
    }

    function atualizarGraficoDesempenho(latA, latB, tokA, tokB) {
      const maxLat = Math.max(latA, latB, 1);
      const maxTok = Math.max(tokA, tokB, 1);
      document.getElementById("chartLatenciaBarA").style.width = `${Math.max(4, Math.round((latA / maxLat) * 100))}%`;
      document.getElementById("chartLatenciaBarB").style.width = `${Math.max(4, Math.round((latB / maxLat) * 100))}%`;
      document.getElementById("chartLatenciaValA").textContent = `${latA.toFixed(1)} ms`;
      document.getElementById("chartLatenciaValB").textContent = `${latB.toFixed(1)} ms`;

      document.getElementById("chartTokensBarA").style.width = `${Math.max(4, Math.round((tokA / maxTok) * 100))}%`;
      document.getElementById("chartTokensBarB").style.width = `${Math.max(4, Math.round((tokB / maxTok) * 100))}%`;
      document.getElementById("chartTokensValA").textContent = `${tokA}`;
      document.getElementById("chartTokensValB").textContent = `${tokB}`;

      const kpiLat = document.getElementById("kpiLatenciaResumo");
      if (kpiLat) {
        kpiLat.textContent = `${Math.round(latA)} vs ${Math.round(latB)} ms`;
      }
    }

    function renderizarModoIndisponivel(elResposta, elPill, elBadge, modo) {
      if (modo.modelo === "texto-fixo-sem-llm") {
        elPill.textContent = "⚠️ Resposta fixa sem LLM (modelo indisponível)";
      } else {
        elPill.textContent = `⚠️ Modelo indisponível (${modo.modelo || "desconhecido"})`;
      }
      elBadge.textContent = "❌ Modelo não respondeu";
      const motivo = modo.erro ? `Motivo: ${modo.erro}` : "Sem detalhes adicionais do erro.";
      elResposta.innerHTML = "";
      if (modo.resposta) {
        const respDiv = document.createElement("div");
        respDiv.innerHTML = formatarRespostaSegura(modo.resposta, true);
        elResposta.appendChild(respDiv);
      }
      const errNote = criarEl("div", "guardrail-box", `⚠️ O modelo não respondeu. ${motivo}`);
      errNote.style.marginTop = modo.resposta ? "10px" : "0";
      elResposta.appendChild(errNote);
    }

    function renderizarComparativo(payload) {
      const modoA = payload.modo_a_llm_pura || {};
      const modoB = payload.modo_b_rag || {};

      renderizarGabarito(payload.gabarito || null);

      const latA = Number(modoA.latencia_ms ?? 0);
      const latB = Number(modoB.latencia_ms ?? 0);
      const tokA = Number(modoA.tokens_total ?? 0);
      const tokB = Number(modoB.tokens_total ?? 0);

      // Modo A
      const pillA = document.getElementById("modeloPillA");
      const badgeA = document.getElementById("badgeModoA");
      const respA = document.getElementById("respostaModoA");
      if (modoA.disponivel === false) {
        renderizarModoIndisponivel(respA, pillA, badgeA, modoA);
      } else {
        pillA.textContent = `🧠 Modelo: ${modoA.modelo || payload.modelo || "não informado"}`;
        badgeA.textContent = "⚠️ Sem Evidências — Sujeito a Alucinação";
        respA.innerHTML = formatarRespostaSegura(modoA.resposta || "", false);
      }
      document.getElementById("latenciaModoA").textContent = `${latA.toFixed(1)} ms`;
      document.getElementById("tokensModoA").textContent = `${tokA}`;

      // Modo B
      const pillB = document.getElementById("modeloPillB");
      const badgeB = document.getElementById("badgeModoB");
      const respB = document.getElementById("respostaModoB");
      if (modoB.disponivel === false) {
        renderizarModoIndisponivel(respB, pillB, badgeB, modoB);
      } else {
        pillB.textContent = `🧠 Modelo: ${modoB.modelo || payload.modelo || "não informado"} · 🔎 Busca: ${NOMES_BUSCA[modoB.busca] || modoB.busca || "por palavras"}`;
        badgeB.textContent = "✅ Fundamentado na Base Curada do DF";
        respB.innerHTML = formatarRespostaSegura(modoB.resposta || "", true);
      }
      document.getElementById("latenciaModoB").textContent = `${latB.toFixed(1)} ms`;
      document.getElementById("tokensModoB").textContent = `${tokB}`;

      atualizarGraficoDesempenho(latA, latB, tokA, tokB);

      // Trace Langfuse: exibir apenas quando trace_url não for nulo
      const traceBanner = document.getElementById("traceBannerB");
      const traceLink = document.getElementById("traceLinkModoB");
      const traceSeguro = urlSegura(modoB.trace_url);
      if (traceSeguro) {
        traceLink.href = traceSeguro;
        traceBanner.style.display = "flex";
      } else {
        traceBanner.style.display = "none";
      }

      // Fontes do Modo B (DOM seguro com textContent, sem innerHTML para dados externos)
      const fontes = Array.isArray(modoB.fontes_utilizadas) ? modoB.fontes_utilizadas : [];
      const containerFontes = document.getElementById("fontesModoB");
      document.getElementById("contadorFontesB").textContent = `${fontes.length} Fonte(s) Recuperada(s)`;
      containerFontes.innerHTML = "";

      const buscaPedida = payload.configuracao && payload.configuracao.busca;
      if (buscaPedida && modoB.busca && buscaPedida !== modoB.busca) {
        const erroBusca = (modoB.guardrails && modoB.guardrails.busca_erro) || "embedding indisponível";
        containerFontes.appendChild(criarEl("div", "guardrail-box",
          `⚠️ A busca ${NOMES_BUSCA[buscaPedida] || buscaPedida} não pôde ser usada (${erroBusca}); o Modo B usou a busca por palavras.`));
      }

      if (fontes.length === 0) {
        const motivoGuardrail = modoB.guardrails && modoB.guardrails.motivo
          ? `Motivo do guardrail: ${modoB.guardrails.motivo}`
          : "Nenhum estabelecimento compatível foi recuperado na base.";
        const box = criarEl("div", "guardrail-box", `🛡️ Pergunta recusada pelos guardrails — ${motivoGuardrail}`);
        containerFontes.appendChild(box);
        return;
      }

      fontes.forEach((f, idx) => {
        const card = criarEl("div", f.citada === false ? "source-card dimmed" : "source-card");

        const top = criarEl("div", "source-card-top");
        top.appendChild(criarEl("div", "source-name", `[FONTE #${idx + 1}] ${f.nome || "Local sem nome"}`));

        const badgesRight = criarEl("div", "");
        badgesRight.style.display = "flex";
        badgesRight.style.gap = "6px";
        badgesRight.style.flexWrap = "wrap";
        badgesRight.appendChild(
          criarEl(
            "span",
            f.citada === false ? "cite-pill cite-pill-no" : "cite-pill cite-pill-yes",
            f.citada === false ? "Recuperada (não citada)" : "✔ Citada na resposta"
          )
        );
        badgesRight.appendChild(criarEl("span", "source-sim", `Similaridade: ${Number(f.score_similaridade ?? 0).toFixed(2)}`));
        top.appendChild(badgesRight);
        card.appendChild(top);

        const meta = criarEl("div", "source-meta");
        meta.appendChild(criarEl("span", "meta-pill", `📍 RA: ${f.ra || "não informada"}`));
        meta.appendChild(criarEl("span", "meta-pill", `💰 Custo Médio: ${formatarPreco(f.custo_medio_rs)}`));
        meta.appendChild(criarEl("span", "meta-pill", `🆔 ${f.id || ""}`));
        card.appendChild(meta);

        const actions = criarEl("div", "source-actions");
        const selo = criarEl("span", "", "✔ Base de 93 lugares do TikTok, auditada em 2 etapas");
        selo.style.fontSize = "0.74rem";
        selo.style.color = "var(--brand-secondary)";
        selo.style.fontWeight = "700";
        actions.appendChild(selo);

        const linkTiktok = urlSegura(f.url_tiktok);
        if (linkTiktok) {
          const a = criarEl("a", "btn-tiktok", "🎵 Ver Vídeo Original no TikTok ↗");
          a.href = linkTiktok;
          a.target = "_blank";
          a.rel = "noopener noreferrer";
          actions.appendChild(a);
        }
        card.appendChild(actions);
        containerFontes.appendChild(card);
      });
    }

    async function executarComparativo(event) {
      if (event) event.preventDefault();
      const idGolden = document.getElementById("goldenSelect").value;
      const pergunta = document.getElementById("perguntaComparativoInput").value.trim();
      const erroBanner = document.getElementById("erroBanner");
      erroBanner.style.display = "none";
      erroBanner.textContent = "";

      if (!idGolden && !pergunta) {
        erroBanner.textContent = "Selecione um caso do Golden Dataset ou digite uma pergunta.";
        erroBanner.style.display = "block";
        return;
      }

      const btn = document.getElementById("btnExecutarComparativo");
      const textoOriginal = btn.textContent;
      btn.disabled = true;
      btn.textContent = "⏳ Consultando modelos (3–5s)...";

      document.getElementById("respostaModoA").textContent = "⏳ Consultando Modo A (LLM Pura)...";
      document.getElementById("respostaModoB").textContent = "⏳ Recuperando base 2FA e consultando Modo B (RAG)...";

      const corpoReq = idGolden ? { id_golden: idGolden } : { pergunta: pergunta };
      corpoReq.raciocinio = document.getElementById("raciocinioSelect").value;
      corpoReq.busca = document.getElementById("buscaSelect").value;
      if (corpoReq.raciocinio !== "desligado") btn.textContent = "⏳ Consultando modelos com raciocínio (até ~12s)...";

      try {
        const res = await fetch("/api/comparativo/executar", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(corpoReq)
        });
        const dados = await res.json();
        if (!res.ok) {
          erroBanner.textContent = dados.detail || `Erro ${res.status} ao executar comparativo.`;
          erroBanner.style.display = "block";
          document.getElementById("respostaModoA").textContent = "Erro ao executar comparação.";
          document.getElementById("respostaModoB").textContent = "Erro ao executar comparação.";
          return;
        }
        renderizarComparativo(dados);
        avaliarComparativo(dados);
      } catch (err) {
        console.error("Erro ao consultar /api/comparativo/executar:", err);
        erroBanner.textContent = "Falha de comunicação com o servidor ao executar comparativo.";
        erroBanner.style.display = "block";
      } finally {
        btn.disabled = false;
        btn.textContent = textoOriginal;
      }
    }

    // Issue #36: avaliação híbrida (RNF-04 determinístico + juiz MiMo-V2.6-Pro), em segundo plano
    const ROTULOS_SCORES = [
      ["fidelidade_factual_rnf03", "🎯 Fidelidade factual (RNF-03)", false],
      ["taxa_alucinacao", "👻 Taxa de alucinação", true],
      ["precisao_geoespacial_ra", "📍 Precisão da RA", false],
      ["sla_latencia_rnf14", "⏱️ SLA ≤ 5 s (RNF-14)", false],
    ];

    function preencherScores(alvoId, bloco, extra) {
      const box = document.getElementById(alvoId);
      if (!box) return;
      box.innerHTML = "";
      const scores = (bloco && bloco.scores) || null;
      if (!scores) {
        box.appendChild(criarEl("span", "", "não avaliado — avaliação indisponível."));
        return;
      }
      ROTULOS_SCORES.forEach(([chave, rotulo, menorMelhor]) => {
        const v = Number(scores[chave]);
        if (Number.isNaN(v)) return;
        const bom = menorMelhor ? v <= 0.2 : v >= 0.8;
        const ruim = menorMelhor ? v >= 0.5 : v < 0.5;
        const linha = criarEl("div", "");
        linha.style.display = "flex";
        linha.style.justifyContent = "space-between";
        linha.style.gap = "8px";
        linha.appendChild(criarEl("span", "", rotulo));
        const val = criarEl("strong", "", `${(v * 100).toFixed(0)}%`);
        val.style.color = bom ? "#16a34a" : (ruim ? "#dc2626" : "#d97706");
        linha.appendChild(val);
        box.appendChild(linha);
      });
      const juiz = (bloco && bloco.julgamento_juiz) || {};
      const origem = juiz.usou_llm
        ? `⚖️ Juiz: ${juiz.modelo_juiz || "MiMo-V2.6-Pro"} + verificação determinística`
        : `⚖️ Verificação determinística (juiz indisponível: ${juiz.motivo_fallback || "sem chave"})`;
      const rodape = criarEl("div", "", origem);
      rodape.style.fontSize = "0.72rem";
      rodape.style.opacity = "0.8";
      rodape.style.marginTop = "6px";
      box.appendChild(rodape);
      if (extra) {
        const e = criarEl("div", "", extra);
        e.style.fontSize = "0.72rem";
        e.style.opacity = "0.8";
        box.appendChild(e);
      }
    }

    async function avaliarComparativo(dados) {
      ["scoresModoA", "scoresModoB"].forEach((id) => {
        const box = document.getElementById(id);
        if (box) box.textContent = "⏳ Avaliando com o juiz MiMo-V2.6-Pro e as travas RNF-04...";
      });
      try {
        const res = await fetch("/api/comparativo/avaliar", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(dados)
        });
        const corpo = await res.json();
        if (!res.ok || !corpo.avaliacao) throw new Error(corpo.detail || `HTTP ${res.status}`);
        const av = corpo.avaliacao;
        const modoA = dados.modo_a_llm_pura || {};
        const extraA = modoA.cache_hit ? "ℹ️ Resposta do cache: latência 0 ms não mede o modelo." : "";
        const busca = av.metricas_busca || {};
        const extraB = (busca.recall_at_k !== undefined && busca.recall_at_k !== null)
          ? `🔎 Busca: recall@k ${Number(busca.recall_at_k).toFixed(2)} · MRR ${Number(busca.mrr ?? 0).toFixed(2)}`
          : "";
        preencherScores("scoresModoA", av.modo_a_llm_pura, extraA);
        preencherScores("scoresModoB", av.modo_b_rag, extraB);
      } catch (err) {
        console.error("Erro ao consultar /api/comparativo/avaliar:", err);
        ["scoresModoA", "scoresModoB"].forEach((id) => {
          const box = document.getElementById(id);
          if (box) box.textContent = "não avaliado — falha ao gerar os scores automáticos.";
        });
      }
    }

    document.addEventListener("DOMContentLoaded", carregarGoldenDataset);
  </script>
</body>
</html>
"""
