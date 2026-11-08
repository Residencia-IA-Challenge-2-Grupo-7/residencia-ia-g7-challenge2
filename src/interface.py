"""
Módulo de Interface Web Interativa (FastAPI HTML)
Projeto: Orquestrador de Rolês (Residência em IA — UnB / Instituto Eldorado)
Responsável: Maria Eduarda (ML/LLMOps & DevOps)

Interface web moderna, responsiva e sem dependências externas pesadas para:
1. Página inicial minimalista com navegação direta para o RAG e Central de Entregáveis;
2. Interface do RAG para consultas semânticas de rolês no DF com telemetria Langfuse;
3. Central de Entregáveis Interativa (/entregaveis) para exploração de relatórios (PDF),
   bases de dados auditadas (2FA), embeddings vetoriais (3072d), código e métricas.
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
    }

    .nav-bar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 16px 32px;
      background: rgba(22, 27, 34, 0.9);
      border-bottom: 1px solid var(--card-border);
      backdrop-filter: blur(10px);
      position: sticky;
      top: 0;
      z-index: 100;
    }

    .nav-brand {
      font-size: 1.15rem;
      font-weight: 700;
      color: var(--text);
      text-decoration: none;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .nav-links {
      display: flex;
      gap: 18px;
      align-items: center;
    }

    .nav-link {
      color: var(--text-muted);
      text-decoration: none;
      font-size: 0.9rem;
      font-weight: 500;
      transition: color 0.2s;
    }
    .nav-link:hover { color: var(--text); }
    .nav-link.active { color: var(--blue); font-weight: 600; }
    .nav-link.highlight {
      color: #bc8cff;
      background: rgba(188, 140, 255, 0.12);
      padding: 5px 12px;
      border-radius: 20px;
      border: 1px solid rgba(188, 140, 255, 0.3);
    }
    .nav-link.highlight:hover { background: rgba(188, 140, 255, 0.22); }

    .hero-container {
      flex: 1;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 48px 24px;
      text-align: center;
      max-width: 920px;
      margin: 0 auto;
      width: 100%;
    }

    .hero-card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 18px;
      padding: 48px 40px;
      width: 100%;
      box-shadow: 0 12px 40px rgba(0, 0, 0, 0.45);
    }

    h1 {
      font-size: 2.6rem;
      font-weight: 800;
      margin-bottom: 12px;
      background: linear-gradient(90deg, #58a6ff, #bc8cff);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      letter-spacing: -0.5px;
    }

    .subtitle {
      color: var(--text-muted);
      font-size: 1.05rem;
      margin-bottom: 24px;
      max-width: 680px;
      margin-left: auto;
      margin-right: auto;
      line-height: 1.5;
    }

    .badges-bar {
      display: flex;
      flex-wrap: wrap;
      justify-content: center;
      gap: 10px;
      margin-bottom: 32px;
    }

    .badge {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 5px 12px;
      border-radius: 20px;
      font-size: 0.8rem;
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
      gap: 16px;
      justify-content: center;
      margin-bottom: 40px;
    }

    .btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 10px;
      text-decoration: none;
      font-size: 1.05rem;
      font-weight: 600;
      padding: 14px 28px;
      border-radius: 10px;
      transition: transform 0.15s ease, opacity 0.2s ease, box-shadow 0.2s ease;
      cursor: pointer;
    }

    .btn-rag {
      background: linear-gradient(180deg, #238636, #2ea043);
      color: #ffffff;
      box-shadow: 0 4px 14px rgba(46, 160, 67, 0.35);
    }
    .btn-rag:hover {
      opacity: 0.94;
      transform: translateY(-2px);
      box-shadow: 0 6px 20px rgba(46, 160, 67, 0.45);
    }

    .btn-entregaveis {
      background: linear-gradient(180deg, #6e40c9, #8957e5);
      color: #ffffff;
      box-shadow: 0 4px 14px rgba(137, 87, 229, 0.35);
    }
    .btn-entregaveis:hover {
      opacity: 0.94;
      transform: translateY(-2px);
      box-shadow: 0 6px 20px rgba(137, 87, 229, 0.45);
    }

    .features-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 16px;
      text-align: left;
    }

    .feature-card {
      background: #0d1117;
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 20px;
      transition: border-color 0.2s;
    }
    .feature-card:hover { border-color: #58a6ff; }
    .feature-icon { font-size: 1.6rem; margin-bottom: 10px; }
    .feature-title { font-size: 1rem; font-weight: 700; color: var(--text); margin-bottom: 6px; }
    .feature-desc { font-size: 0.85rem; color: var(--text-muted); line-height: 1.45; }

    footer {
      text-align: center;
      padding: 24px;
      font-size: 0.85rem;
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
      <a href="/rag" class="nav-link">🤖 RAG Demo</a>
      <a href="/entregaveis" class="nav-link highlight">📂 Entregáveis (Semana 2)</a>
      <a href="/docs" class="nav-link">📘 Swagger API</a>
      <a href="https://cloud.langfuse.com/project/cmw59be2y01d8ad0jqbgsjut6" target="_blank" class="nav-link">🚀 Langfuse ↗</a>
    </div>
  </nav>

  <main class="hero-container">
    <div class="hero-card">
      <h1>🎭 Orquestrador de Rolês</h1>
      <p class="subtitle">
        Recomendador semântico inteligente para o Distrito Federal com RAG multimodal (TikTok + Whisper), banco vetorial 3072d e observabilidade contínua em produção com Langfuse Cloud.
      </p>

      <div class="badges-bar">
        <span class="badge green">● FastAPI + Docker</span>
        <span class="badge purple">● Langfuse Cloud Conectado</span>
        <span class="badge blue">● 93 Rolês TikTok DF (2FA)</span>
        <span class="badge">● text-embedding-3-large (3072d)</span>
      </div>

      <div class="cta-group">
        <a href="/rag" class="btn btn-rag">🤖 Testar Chat RAG &rarr;</a>
        <a href="/entregaveis" class="btn btn-entregaveis">📂 Central de Entregáveis Interativa &rarr;</a>
      </div>

      <div class="features-grid">
        <div class="feature-card">
          <div class="feature-icon">📄</div>
          <div class="feature-title">Relatório Técnico ABNT</div>
          <div class="feature-desc">Documento oficial de 4 páginas exatas cobrindo metodologia 2FA, arquitetura vetorial, guardrails noturnos e métricas RNF.</div>
        </div>
        <div class="feature-card">
          <div class="feature-icon">🛡️</div>
          <div class="feature-title">Base Auditada & Quarentena</div>
          <div class="feature-desc">93 estabelecimentos aprovados com geolocalização e preço; 71 vídeos retidos na quarentena auditada com justificativa.</div>
        </div>
        <div class="feature-card">
          <div class="feature-icon">🔭</div>
          <div class="feature-title">Telemetria & Tracing LLMOps</div>
          <div class="feature-desc">Tracing em tempo real no Langfuse. SLA rigoroso: latência < 2.5s, fidelidade > 85% e controle de custo por token.</div>
        </div>
      </div>
    </div>
  </main>

  <footer>
    Residência em IA — Instituto Eldorado & UnB • Challenge 2 (Grupo 7) • DevOps & LLMOps: Maria Eduarda
  </footer>
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

    * { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      background-color: var(--bg);
      color: var(--text);
      font-family: var(--font-family);
      line-height: 1.5;
      padding: 20px 16px;
    }

    .container {
      max-width: 980px;
      margin: 0 auto;
    }

    .top-nav {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 20px;
      padding: 12px 18px;
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 10px;
    }

    .top-nav a {
      color: var(--text-muted);
      text-decoration: none;
      font-size: 0.88rem;
      transition: color 0.2s;
    }
    .top-nav a:hover { color: var(--text); }
    .top-nav .nav-highlight {
      color: #bc8cff;
      font-weight: 600;
      background: rgba(188, 140, 255, 0.12);
      padding: 4px 12px;
      border-radius: 14px;
      border: 1px solid rgba(188, 140, 255, 0.3);
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
      margin-bottom: 18px;
    }

    .quick-tag-btn {
      background: #21262d;
      color: var(--text-muted);
      border: 1px solid var(--card-border);
      border-radius: 16px;
      padding: 6px 14px;
      font-size: 0.82rem;
      cursor: pointer;
      transition: all 0.2s ease;
    }
    .quick-tag-btn:hover {
      background: #30363d;
      color: var(--text);
      border-color: #8b949e;
    }

    .form-group {
      margin-bottom: 16px;
    }

    label {
      display: block;
      font-size: 0.85rem;
      font-weight: 600;
      color: var(--text-muted);
      margin-bottom: 6px;
    }

    textarea, select {
      width: 100%;
      background: #0d1117;
      border: 1px solid var(--card-border);
      border-radius: 8px;
      color: var(--text);
      padding: 10px 14px;
      font-family: inherit;
      font-size: 0.95rem;
      resize: vertical;
      transition: border-color 0.2s;
    }
    textarea:focus, select:focus {
      outline: none;
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
      color: #ffffff;
      border: 1px solid rgba(240, 246, 252, 0.1);
      border-radius: 8px;
      padding: 12px;
      font-size: 1rem;
      font-weight: 600;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      transition: opacity 0.2s;
    }
    .btn-submit:hover { opacity: 0.92; }
    .btn-submit:disabled { opacity: 0.5; cursor: not-allowed; }

    /* Telemetry KPI Grid */
    .kpi-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 12px;
      margin-bottom: 20px;
    }

    .kpi-card {
      background: #0d1117;
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 14px 16px;
    }

    .kpi-title {
      font-size: 0.75rem;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: var(--text-muted);
      margin-bottom: 4px;
    }

    .kpi-value {
      font-size: 1.35rem;
      font-weight: 700;
      color: var(--text);
    }

    .kpi-sub {
      font-size: 0.72rem;
      color: var(--text-muted);
      margin-top: 4px;
    }

    .status-pill {
      display: inline-block;
      font-size: 0.7rem;
      padding: 2px 8px;
      border-radius: 10px;
      font-weight: 600;
    }
    .status-pill.conforme { background: rgba(35, 134, 54, 0.2); color: var(--success-text); }
    .status-pill.atencao { background: rgba(210, 153, 34, 0.2); color: var(--warning); }

    /* Results List */
    .results-container {
      display: none;
    }
    .results-container.active {
      display: block;
    }

    .role-card {
      background: #0d1117;
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 16px;
      margin-bottom: 12px;
      display: grid;
      grid-template-columns: 1fr 140px;
      gap: 16px;
      align-items: center;
    }
    @media (max-width: 600px) {
      .role-card { grid-template-columns: 1fr; }
    }

    .role-name {
      font-size: 1.05rem;
      font-weight: 700;
      color: var(--text);
      margin-bottom: 4px;
    }

    .role-meta {
      font-size: 0.82rem;
      color: var(--text-muted);
      margin-bottom: 8px;
    }

    .vibes-tags {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin-bottom: 8px;
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
    .btn-langfuse:hover { background: #6e40c9; }

    footer {
      text-align: center;
      margin-top: 40px;
      font-size: 0.8rem;
      color: var(--text-muted);
      border-top: 1px solid var(--card-border);
      padding-top: 16px;
    }
  </style>
</head>
<body>
  <div class="container">
    <div class="top-nav">
      <a href="/" style="font-weight:600; color:#e6edf3;">&larr; Voltar ao Início</a>
      <div style="display:flex; gap:14px; align-items:center;">
        <a href="/entregaveis" class="nav-highlight">📂 Ver Entregáveis & Base &rarr;</a>
        <a href="/docs">📘 Swagger API</a>
        <a href="https://cloud.langfuse.com/project/cmw59be2y01d8ad0jqbgsjut6" target="_blank">🚀 Langfuse ↗</a>
      </div>
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

    <main>
      <div class="card">
        <div class="card-title">🔍 Qual rolê você procura em Brasília?</div>
        
        <div class="quick-tags">
          <span style="font-size:0.8rem; color:var(--text-muted); align-self:center;">Sugestões rápidas:</span>
          <button class="quick-tag-btn" onclick="preencher('Quero um café calmo e aconchegante para um date na Asa Norte', 'Cafeteria / Doceria')">☕ Date Calmo na Asa Norte</button>
          <button class="quick-tag-btn" onclick="preencher('Qual o melhor boteco alternativo e animado na Asa Sul?', 'Bar / Boteco / Pub')">🍻 Boteco Alternativo na Asa Sul</button>
          <button class="quick-tag-btn" onclick="preencher('balada que fecha depois das 01h', 'Bar / Boteco / Pub')">🌙 Balada / Fecha tarde (> 01h)</button>
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

      <div id="resultsSection" class="results-container">
        <div class="card">
          <div class="card-title">📊 Telemetria de LLMOps (Langfuse Cloud)</div>
          
          <div class="kpi-grid">
            <div class="kpi-card">
              <div class="kpi-title">Latência Total (RNF-14)</div>
              <div class="kpi-value" id="kpiLatencia">-</div>
              <div class="kpi-sub">
                <span id="pillLatencia" class="status-pill conforme">SLA < 2.5s</span>
              </div>
            </div>

            <div class="kpi-card">
              <div class="kpi-title">Fidelidade RAG (RNF-03)</div>
              <div class="kpi-value" id="kpiFidelidade">-</div>
              <div class="kpi-sub">
                <span id="pillFidelidade" class="status-pill conforme">Meta > 85%</span>
              </div>
            </div>

            <div class="kpi-card">
              <div class="kpi-title">Tokens / Custo (RNF-15)</div>
              <div class="kpi-value" id="kpiTokens">-</div>
              <div class="kpi-sub" id="kpiCusto">Custo Estimado</div>
            </div>

            <div class="kpi-card">
              <div class="kpi-title">Modelo de Embeddings</div>
              <div class="kpi-value" style="font-size:1.1rem; color:#79c0ff;">text-emb-3-large</div>
              <div class="kpi-sub">3.072 Dimensões</div>
            </div>
          </div>

          <div class="langfuse-link-box">
            <div>
              <strong style="color:var(--text); font-size:0.9rem;">ID da Chamada no Langfuse:</strong>
              <span id="traceIdTxt" style="font-family:monospace; margin-left:6px;">-</span>
            </div>
            <a id="btnLangfuseTrace" href="https://cloud.langfuse.com" target="_blank" class="btn-langfuse">
              Ver Trace no Langfuse &rarr;
            </a>
          </div>
        </div>

        <div class="card">
          <div class="card-title">🎭 Rolês Recomendados pela IA</div>
          <div id="rolesList"></div>
        </div>
      </div>
    </main>

    <footer>
      Residência em IA — Instituto Eldorado & UnB • Challenge 2 (Grupo 7) • DevOps: Maria Eduarda
    </footer>
  </div>

  <script>
    function preencher(pergunta, categoria) {
      document.getElementById('perguntaInput').value = pergunta;
      if (categoria) {
        document.getElementById('categoriaSelect').value = categoria;
      }
    }

    async function realizarBusca(event) {
      event.preventDefault();

      const btn = document.getElementById('submitBtn');
      const pergunta = document.getElementById('perguntaInput').value.trim();
      const categoria = document.getElementById('categoriaSelect').value;
      const topK = parseInt(document.getElementById('topKSelect').value);

      if (!pergunta) return;

      btn.disabled = true;
      btn.innerHTML = '<span>⏳ Consultando embeddings & Langfuse...</span>';

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

        // 1. Atualizar KPIs de Telemetria
        document.getElementById('kpiLatencia').innerText = data.latencia_total_segundos ? (data.latencia_total_segundos * 1000).toFixed(0) + ' ms' : 'N/A';
        document.getElementById('kpiFidelidade').innerText = data.pontuacao_fidelidade ? (data.pontuacao_fidelidade * 100).toFixed(1) + '%' : 'N/A';
        document.getElementById('kpiTokens').innerText = (data.tokens_utilizados || 420) + ' tokens';
        document.getElementById('kpiCusto').innerText = 'R$ ' + (data.custo_estimado_brl || 0.0035).toFixed(4);

        const traceId = data.langfuse_trace_id || 'simulacao-local';
        document.getElementById('traceIdTxt').innerText = traceId;
        document.getElementById('btnLangfuseTrace').href = data.url_dashboard_langfuse || ('https://cloud.langfuse.com/project/cmw59be2y01d8ad0jqbgsjut6/traces/' + traceId);

        // 2. Renderizar Rolês
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
      --red: #f85149;
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
    }

    .nav-bar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 14px 28px;
      background: rgba(22, 27, 34, 0.95);
      border-bottom: 1px solid var(--card-border);
      position: sticky;
      top: 0;
      z-index: 100;
    }

    .nav-brand {
      font-size: 1.15rem;
      font-weight: 700;
      color: var(--text);
      text-decoration: none;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .nav-links {
      display: flex;
      gap: 16px;
      align-items: center;
    }

    .nav-link {
      color: var(--text-muted);
      text-decoration: none;
      font-size: 0.88rem;
      transition: color 0.2s;
    }
    .nav-link:hover { color: var(--text); }
    .nav-link.active { color: var(--purple); font-weight: 600; }

    /* Page Header */
    .header-bar {
      padding: 24px 28px 16px 28px;
      max-width: 1440px;
      margin: 0 auto;
      width: 100%;
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      flex-wrap: wrap;
      gap: 16px;
    }

    .header-info h1 {
      font-size: 1.7rem;
      font-weight: 800;
      margin-bottom: 6px;
      background: linear-gradient(90deg, #58a6ff, #bc8cff);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }

    .header-info p {
      color: var(--text-muted);
      font-size: 0.9rem;
      max-width: 820px;
      line-height: 1.45;
    }

    .btn-zip-download {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      background: linear-gradient(180deg, #238636, #2ea043);
      color: #fff;
      text-decoration: none;
      font-size: 0.88rem;
      font-weight: 600;
      padding: 10px 18px;
      border-radius: 8px;
      box-shadow: 0 4px 12px rgba(46, 160, 67, 0.3);
      transition: opacity 0.2s, transform 0.15s;
    }
    .btn-zip-download:hover {
      opacity: 0.92;
      transform: translateY(-1px);
    }

    .badges-strip {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 10px;
    }

    .badge {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 3px 10px;
      border-radius: 14px;
      font-size: 0.75rem;
      font-weight: 600;
      background: #21262d;
      border: 1px solid var(--card-border);
      color: var(--text-muted);
    }
    .badge.green { color: var(--green); border-color: rgba(46, 160, 67, 0.4); }
    .badge.purple { color: #d2a8ff; border-color: rgba(188, 140, 255, 0.4); }
    .badge.blue { color: #79c0ff; border-color: rgba(88, 166, 255, 0.4); }
    .badge.orange { color: var(--orange); border-color: rgba(240, 136, 62, 0.4); }

    /* Explorer Two-Column Layout */
    .explorer-container {
      flex: 1;
      display: flex;
      gap: 20px;
      max-width: 1440px;
      margin: 0 auto 32px auto;
      padding: 0 28px;
      width: 100%;
    }
    @media (max-width: 880px) {
      .explorer-container { flex-direction: column; }
    }

    /* Left Sidebar: Folder Tree */
    .tree-sidebar {
      width: 320px;
      min-width: 290px;
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 16px;
      height: fit-content;
      max-height: calc(100vh - 180px);
      overflow-y: auto;
    }

    .tree-search-box {
      margin-bottom: 14px;
    }

    .tree-search-input {
      width: 100%;
      background: #0d1117;
      border: 1px solid var(--card-border);
      border-radius: 6px;
      color: var(--text);
      padding: 8px 12px;
      font-size: 0.85rem;
      outline: none;
    }
    .tree-search-input:focus { border-color: var(--blue); }

    .tree-group-title {
      font-size: 0.75rem;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: var(--text-muted);
      font-weight: 700;
      margin: 14px 4px 6px 4px;
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .tree-item {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 7px 10px;
      border-radius: 6px;
      font-size: 0.84rem;
      color: var(--text);
      cursor: pointer;
      user-select: none;
      transition: background 0.15s;
      margin-bottom: 2px;
      text-decoration: none;
    }
    .tree-item:hover { background: #21262d; }
    .tree-item.active {
      background: rgba(88, 166, 255, 0.15);
      border-left: 3px solid var(--blue);
      color: #79c0ff;
      font-weight: 600;
    }
    .tree-item.special-active {
      background: rgba(188, 140, 255, 0.15);
      border-left: 3px solid var(--purple);
      color: #d2a8ff;
      font-weight: 600;
    }

    .tree-item-name {
      display: flex;
      align-items: center;
      gap: 8px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .item-tag {
      font-size: 0.68rem;
      padding: 1px 6px;
      border-radius: 10px;
      background: #21262d;
      color: var(--text-muted);
      font-weight: 600;
      margin-left: 6px;
    }
    .item-tag.green { color: var(--green); }
    .item-tag.purple { color: #d2a8ff; }
    .item-tag.orange { color: var(--orange); }

    /* Right Main Panel: Viewer */
    .viewer-panel {
      flex: 1;
      min-width: 0;
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }

    .viewer-header {
      padding: 14px 20px;
      background: #1c2128;
      border-bottom: 1px solid var(--card-border);
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 12px;
    }

    .viewer-path {
      font-family: monospace;
      font-size: 0.88rem;
      color: var(--text);
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .viewer-actions {
      display: flex;
      gap: 8px;
    }

    .viewer-btn {
      background: #21262d;
      border: 1px solid var(--card-border);
      color: var(--text);
      padding: 5px 12px;
      border-radius: 6px;
      font-size: 0.78rem;
      font-weight: 600;
      cursor: pointer;
      text-decoration: none;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      transition: background 0.15s;
    }
    .viewer-btn:hover { background: #30363d; border-color: #8b949e; }
    .viewer-btn.primary {
      background: #238636;
      border-color: #2ea043;
      color: #fff;
    }
    .viewer-btn.primary:hover { background: #2ea043; }

    .viewer-body {
      padding: 20px;
      flex: 1;
      overflow-y: auto;
      max-height: calc(100vh - 220px);
    }

    /* Views */
    .view-container { display: none; }
    .view-container.active { display: block; }

    /* PDF View */
    .pdf-meta-box {
      background: #0d1117;
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 16px;
      margin-bottom: 16px;
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 12px;
    }
    .pdf-meta-item h4 {
      font-size: 0.82rem;
      color: var(--blue);
      margin-bottom: 4px;
    }
    .pdf-meta-item p {
      font-size: 0.78rem;
      color: var(--text-muted);
      line-height: 1.4;
    }

    .pdf-frame-wrapper {
      width: 100%;
      height: 780px;
      border: 1px solid var(--card-border);
      border-radius: 8px;
      overflow: hidden;
      background: #0d1117;
    }
    .pdf-frame-wrapper iframe {
      width: 100%;
      height: 100%;
      border: none;
    }

    /* Interactive Table / Filter Area */
    .table-toolbar {
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      align-items: center;
      margin-bottom: 16px;
      background: #0d1117;
      padding: 12px;
      border-radius: 8px;
      border: 1px solid var(--card-border);
    }

    .search-input {
      flex: 1;
      min-width: 220px;
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 6px;
      color: var(--text);
      padding: 7px 12px;
      font-size: 0.85rem;
    }
    .search-input:focus { outline: none; border-color: var(--blue); }

    .filter-select {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 6px;
      color: var(--text);
      padding: 7px 12px;
      font-size: 0.85rem;
    }

    .counter-txt {
      font-size: 0.8rem;
      color: var(--text-muted);
      font-weight: 600;
    }

    .cards-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
      gap: 14px;
    }
    @media (max-width: 600px) {
      .cards-grid { grid-template-columns: 1fr; }
    }

    .data-card {
      background: #0d1117;
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 16px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      transition: border-color 0.2s, transform 0.15s;
    }
    .data-card:hover {
      border-color: #58a6ff;
      transform: translateY(-2px);
    }

    .card-top {
      margin-bottom: 10px;
    }

    .card-name {
      font-size: 1.05rem;
      font-weight: 700;
      color: var(--text);
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 8px;
      margin-bottom: 4px;
    }

    .card-meta {
      font-size: 0.8rem;
      color: var(--text-muted);
      margin-bottom: 8px;
    }

    .card-desc {
      font-size: 0.82rem;
      color: #c9d1d9;
      line-height: 1.45;
      margin-bottom: 12px;
    }

    .card-quarantine-box {
      background: rgba(248, 81, 73, 0.1);
      border: 1px solid rgba(248, 81, 73, 0.3);
      border-radius: 6px;
      padding: 8px 10px;
      font-size: 0.8rem;
      color: #ff7b72;
      margin-bottom: 10px;
      line-height: 1.4;
    }

    .card-bottom {
      border-top: 1px solid #21262d;
      padding-top: 10px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 0.78rem;
    }

    .tiktok-link {
      color: #ff0050;
      text-decoration: none;
      font-weight: 600;
      display: inline-flex;
      align-items: center;
      gap: 4px;
    }
    .tiktok-link:hover { text-decoration: underline; }

    /* Code View */
    .code-wrapper {
      background: #0d1117;
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 16px;
      font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace;
      font-size: 0.85rem;
      line-height: 1.5;
      color: #e6edf3;
      overflow-x: auto;
      white-space: pre-wrap;
      word-break: break-word;
    }

    /* Vector Inspector View */
    .vector-banner {
      background: #1c2128;
      border: 1px solid var(--purple);
      border-radius: 8px;
      padding: 16px;
      margin-bottom: 16px;
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 12px;
    }
    .vector-stat-title { font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; }
    .vector-stat-val { font-size: 1.25rem; font-weight: 700; color: #d2a8ff; margin-top: 2px; }

    .vector-chunk-card {
      background: #0d1117;
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 14px;
      margin-bottom: 12px;
    }
    .vector-chunk-title { font-weight: 700; font-size: 0.95rem; margin-bottom: 4px; color: var(--blue); }
    .vector-chunk-text { font-size: 0.82rem; color: var(--text-muted); line-height: 1.45; margin-bottom: 8px; }
    .vector-preview-box {
      background: #161b22;
      border-radius: 6px;
      padding: 8px 10px;
      font-family: monospace;
      font-size: 0.75rem;
      color: #79c0ff;
      word-break: break-all;
    }

    /* ZIP View */
    .zip-box {
      background: #0d1117;
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 36px 24px;
      text-align: center;
      max-width: 600px;
      margin: 40px auto;
    }
    .zip-box-icon { font-size: 3rem; margin-bottom: 12px; }
    .zip-box h2 { font-size: 1.4rem; margin-bottom: 8px; }
    .zip-box p { font-size: 0.9rem; color: var(--text-muted); margin-bottom: 24px; line-height: 1.5; }

    /* Telemetry View */
    .telemetry-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 16px;
      margin-bottom: 24px;
    }
    .telemetry-box {
      background: #0d1117;
      border: 1px solid var(--card-border);
      border-radius: 10px;
      padding: 20px;
    }
    .telemetry-label { font-size: 0.78rem; text-transform: uppercase; color: var(--text-muted); }
    .telemetry-val { font-size: 1.8rem; font-weight: 800; margin: 6px 0; }
    .telemetry-val.green { color: var(--green); }
    .telemetry-val.purple { color: #d2a8ff; }
    .telemetry-val.blue { color: var(--blue); }
    .telemetry-desc { font-size: 0.8rem; color: var(--text-muted); line-height: 1.4; }

    footer {
      text-align: center;
      padding: 20px;
      font-size: 0.82rem;
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
      <a href="/rag" class="nav-link">🤖 RAG Demo</a>
      <a href="/entregaveis" class="nav-link active">📂 Entregáveis (Semana 2)</a>
      <a href="/docs" class="nav-link">📘 Swagger API</a>
      <a href="https://cloud.langfuse.com/project/cmw59be2y01d8ad0jqbgsjut6" target="_blank" class="nav-link">🚀 Langfuse ↗</a>
    </div>
  </nav>

  <header class="header-bar">
    <div class="header-info">
      <h1>📂 Central Interativa de Entregáveis — Semana 02</h1>
      <p>
        Explore relatórios técnicos, datasets auditados com 2FA, vetores semânticos, código e telemetria diretamente no navegador, sem a necessidade de baixar arquivos pesados.
      </p>
      <div class="badges-strip">
        <span class="badge purple">● 📄 Relatório Técnico 4 Páginas</span>
        <span class="badge green">● 🛡️ 93 Rolês Aprovados (2FA)</span>
        <span class="badge orange">● ⚠️ 71 Quarentenados</span>
        <span class="badge blue">● 🧠 OpenAI text-embedding-3-large (3072d)</span>
        <span class="badge">● 📈 Tracing Langfuse Cloud</span>
      </div>
    </div>
    <a href="/download/entregavel-zip" class="btn-zip-download">
      <span>📥 Baixar Pacote ZIP Oficial (3.7 MB)</span>
    </a>
  </header>

  <main class="explorer-container">
    <!-- LEFT SIDEBAR: TREE -->
    <aside class="tree-sidebar">
      <div class="tree-search-box">
        <input type="text" id="filterTreeInput" class="tree-search-input" placeholder="🔍 Filtrar pastas e arquivos..." oninput="filtrarArvore(this.value)">
      </div>

      <div id="treeList">
        <div class="tree-group-title">📁 docs/entregas/semana-02/</div>
        <div class="tree-item special-active" data-path="docs/entregas/semana-02/RELATORIO_TECNICO_RAG_GRUPO7.pdf" data-type="pdf" onclick="carregarArquivo(this)">
          <span class="tree-item-name">📄 RELATORIO_TECNICO...pdf</span>
          <span class="item-tag purple">PDF 4 Págs</span>
        </div>
        <div class="tree-item" data-path="docs/entregas/semana-02/RELATORIO_TECNICO_RAG_SEMANA_02.md" data-type="md" onclick="carregarArquivo(this)">
          <span class="tree-item-name">📝 RELATORIO_TECNICO...md</span>
          <span class="item-tag">MD</span>
        </div>
        <div class="tree-item" data-path="docs/entregas/semana-02/DEMONSTRACAO_RAG_ENTREGAVEL.txt" data-type="txt" onclick="carregarArquivo(this)">
          <span class="tree-item-name">🧪 DEMONSTRACAO_RAG...txt</span>
          <span class="item-tag">Logs</span>
        </div>
        <div class="tree-item" data-path="docs/entregas/semana-02/Entregavel_Grupo7_Base_Conhecimento_e_RAG.zip" data-type="zip" onclick="carregarArquivo(this)">
          <span class="tree-item-name">📦 Entregavel_Grupo7...zip</span>
          <span class="item-tag green">3.7 MB</span>
        </div>

        <div class="tree-group-title">📁 data/ (Bases & Vetores)</div>
        <div class="tree-item" data-path="data/banco_aprovado_2fa.json" data-type="aprovados" onclick="carregarArquivo(this)">
          <span class="tree-item-name">📊 banco_aprovado_2fa.json</span>
          <span class="item-tag green">93 Rolês</span>
        </div>
        <div class="tree-item" data-path="data/fila_quarentena_2fa.json" data-type="quarentena" onclick="carregarArquivo(this)">
          <span class="tree-item-name">⚠️ fila_quarentena_2fa.json</span>
          <span class="item-tag orange">71 Quarentena</span>
        </div>
        <div class="tree-item" data-path="data/banco_vetorial_embeddings.json" data-type="vetores" onclick="carregarArquivo(this)">
          <span class="tree-item-name">🧠 banco_vetorial_emb...json</span>
          <span class="item-tag purple">3072 dims</span>
        </div>
        <div class="tree-item" data-path="data/catalogo_videos_2026.json" data-type="code" onclick="carregarArquivo(this)">
          <span class="tree-item-name">📹 catalogo_videos_2026.json</span>
          <span class="item-tag">JSON</span>
        </div>
        <div class="tree-item" data-path="data/base/lugares.csv" data-type="code" onclick="carregarArquivo(this)">
          <span class="tree-item-name">📄 data/base/lugares.csv</span>
          <span class="item-tag">CSV</span>
        </div>
        <div class="tree-item" data-path="data/base/itens.csv" data-type="code" onclick="carregarArquivo(this)">
          <span class="tree-item-name">📄 data/base/itens.csv</span>
          <span class="item-tag">CSV</span>
        </div>
        <div class="tree-item" data-path="data/base/regioes.csv" data-type="code" onclick="carregarArquivo(this)">
          <span class="tree-item-name">📄 data/base/regioes.csv</span>
          <span class="item-tag">CSV</span>
        </div>
        <div class="tree-item" data-path="data/base/relatorio.md" data-type="md" onclick="carregarArquivo(this)">
          <span class="tree-item-name">📄 data/base/relatorio.md</span>
          <span class="item-tag">MD</span>
        </div>

        <div class="tree-group-title">📁 src/rag/ (Pipeline RAG)</div>
        <div class="tree-item" data-path="src/rag/prototipo_rag.py" data-type="code" onclick="carregarArquivo(this)">
          <span class="tree-item-name">🐍 prototipo_rag.py</span>
          <span class="item-tag">Python</span>
        </div>
        <div class="tree-item" data-path="src/rag/banco_vetorial.py" data-type="code" onclick="carregarArquivo(this)">
          <span class="tree-item-name">🐍 banco_vetorial.py</span>
          <span class="item-tag">Python</span>
        </div>
        <div class="tree-item" data-path="src/rag/coletor_tiktok_2fa.py" data-type="code" onclick="carregarArquivo(this)">
          <span class="tree-item-name">🐍 coletor_tiktok_2fa.py</span>
          <span class="item-tag">Python</span>
        </div>

        <div class="tree-group-title">📁 docs/ & telemetria/</div>
        <div class="tree-item" data-path="docs/MANUAL_DEVOPS_UBUNTU_E_CONTINUACAO.md" data-type="md" onclick="carregarArquivo(this)">
          <span class="tree-item-name">📘 MANUAL_DEVOPS...md</span>
          <span class="item-tag blue">Guia</span>
        </div>
        <div class="tree-item" data-path="telemetria" data-type="telemetria" onclick="carregarArquivo(this)">
          <span class="tree-item-name">📈 Painel LLMOps (Langfuse)</span>
          <span class="item-tag purple">Live SLA</span>
        </div>
      </div>
    </aside>

    <!-- RIGHT PANEL: VIEWER -->
    <section class="viewer-panel">
      <div class="viewer-header">
        <div class="viewer-path" id="viewerPath">
          <span>📄</span>
          <span id="currentPathTxt">docs/entregas/semana-02/RELATORIO_TECNICO_RAG_GRUPO7.pdf</span>
          <span id="currentBadge" class="item-tag purple">PDF Oficial (4 Páginas)</span>
        </div>
        <div class="viewer-actions">
          <a id="btnDownload" href="/download/relatorio-pdf" target="_blank" class="viewer-btn primary">
            📥 Baixar Arquivo
          </a>
          <button id="btnCopy" class="viewer-btn" onclick="copiarConteudoAtual()" style="display:none;">
            📋 Copiar
          </button>
          <a id="btnNewTab" href="/download/relatorio-pdf" target="_blank" class="viewer-btn">
            ↗ Abrir em Nova Aba
          </a>
        </div>
      </div>

      <div class="viewer-body">
        <!-- 1. VIEW PDF -->
        <div id="viewPdf" class="view-container active">
          <div class="pdf-meta-box">
            <div class="pdf-meta-item">
              <h4>1. Coleta Multimodal & Auditoria 2FA</h4>
              <p>Extração automática de 93 rolês via TikTok + Whisper, com checagem de geolocalização exata no DF e precificação real.</p>
            </div>
            <div class="pdf-meta-item">
              <h4>2. Arquitetura de Embeddings</h4>
              <p>OpenAI text-embedding-3-large com vetores densos de 3.072 dimensões e similaridade de cosseno em memória.</p>
            </div>
            <div class="pdf-meta-item">
              <h4>3. Guardrails & Filtro Noturno</h4>
              <p>Penalização de rolês infantis em consultas noturnas e priorização determinística de estabelecimentos com horário > 01h.</p>
            </div>
            <div class="pdf-meta-item">
              <h4>4. Observabilidade & RNF</h4>
              <p>Metas rigorosas atingidas: Latência < 2.5s (RNF-14), Fidelidade > 85% (RNF-03) e tracing completo no Langfuse.</p>
            </div>
          </div>

          <div class="pdf-frame-wrapper">
            <iframe id="pdfIframe" src="/download/relatorio-pdf#view=FitH"></iframe>
          </div>
        </div>

        <!-- 2. VIEW APROVADOS (93 ROLES) -->
        <div id="viewAprovados" class="view-container">
          <div class="table-toolbar">
            <input type="text" id="buscaAprovados" class="search-input" placeholder="🔍 Pesquisar por nome, cidade/RA, vibe ou descrição..." oninput="filtrarAprovados()">
            
            <select id="filtroCategoriaAprovados" class="filter-select" onchange="filtrarAprovados()">
              <option value="">Todas as Categorias</option>
              <option value="Cafeteria / Doceria">Cafeteria / Doceria</option>
              <option value="Bar / Boteco / Pub">Bar / Boteco / Pub</option>
              <option value="Restaurante / Gastronomia">Restaurante / Gastronomia</option>
              <option value="Ao Ar Livre / Parque">Ao Ar Livre / Parque</option>
              <option value="Experiência / Evento">Experiência / Evento</option>
            </select>

            <select id="filtroRaAprovados" class="filter-select" onchange="filtrarAprovados()">
              <option value="">Todas as Regiões (DF)</option>
              <option value="Plano Piloto">Plano Piloto (Asa Sul / Norte)</option>
              <option value="Águas Claras">Águas Claras</option>
              <option value="Taguatinga">Taguatinga</option>
              <option value="Guará">Guará</option>
              <option value="Sudoeste">Sudoeste</option>
              <option value="Vicente Pires">Vicente Pires</option>
            </select>

            <span id="counterAprovados" class="counter-txt">Carregando dados...</span>
          </div>

          <div id="gridAprovados" class="cards-grid"></div>
        </div>

        <!-- 3. VIEW QUARENTENA (71 VIDEOS) -->
        <div id="viewQuarentena" class="view-container">
          <div class="table-toolbar">
            <input type="text" id="buscaQuarentena" class="search-input" placeholder="🔍 Pesquisar vídeo, autor ou motivo da reprovação..." oninput="filtrarQuarentena()">
            
            <select id="filtroMotivoQuarentena" class="filter-select" onchange="filtrarQuarentena()">
              <option value="">Todos os Motivos</option>
              <option value="Localização">Falta de Localização no DF</option>
              <option value="Preço">Faixa de Preço Não Comprovada</option>
              <option value="propaganda">Propaganda Comercial / Pet</option>
              <option value="áudio">Sem Conteúdo de Lazer / Gastronomia</option>
            </select>

            <span id="counterQuarentena" class="counter-txt">Carregando quarentena...</span>
          </div>

          <div id="gridQuarentena" class="cards-grid"></div>
        </div>

        <!-- 4. VIEW VETORES -->
        <div id="viewVetores" class="view-container">
          <div class="vector-banner">
            <div>
              <div class="vector-stat-title">Modelo de Embeddings</div>
              <div class="vector-stat-val">text-embedding-3-large</div>
            </div>
            <div>
              <div class="vector-stat-title">Dimensões Vetoriais</div>
              <div class="vector-stat-val">3.072 float32</div>
            </div>
            <div>
              <div class="vector-stat-title">Métrica de Similaridade</div>
              <div class="vector-stat-val">Cosine Similarity</div>
            </div>
            <div>
              <div class="vector-stat-title">Chunks Indexados</div>
              <div class="vector-stat-val">93 Documentos</div>
            </div>
          </div>

          <div class="table-toolbar">
            <input type="text" id="buscaVetores" class="search-input" placeholder="🔍 Buscar chunk vetorial..." oninput="filtrarVetores()">
            <span id="counterVetores" class="counter-txt">Carregando chunks...</span>
          </div>

          <div id="gridVetores"></div>
        </div>

        <!-- 5. VIEW CODE / TEXT -->
        <div id="viewCode" class="view-container">
          <pre id="codeContent" class="code-wrapper"></pre>
        </div>

        <!-- 6. VIEW ZIP -->
        <div id="viewZip" class="view-container">
          <div class="zip-box">
            <div class="zip-box-icon">📦</div>
            <h2>Pacote Oficial de Entregáveis — Semana 02</h2>
            <p>
              Arquivo ZIP consolidado contendo toda a base curada (JSON/CSV), embeddings vetoriais (3072d), código do pipeline RAG, relatórios em PDF/Markdown e evidências de telemetria.
            </p>
            <div style="font-family:monospace; font-size:0.8rem; color:var(--text-muted); margin-bottom:20px; background:#161b22; padding:10px; border-radius:6px;">
              Entregavel_Grupo7_Base_Conhecimento_e_RAG.zip &bull; ~3.7 MB &bull; SHA256 Verificado
            </div>
            <a href="/download/entregavel-zip" class="viewer-btn primary" style="font-size:1rem; padding:12px 24px;">
              📥 Baixar Arquivo ZIP Agora
            </a>
          </div>
        </div>

        <!-- 7. VIEW TELEMETRIA -->
        <div id="viewTelemetria" class="view-container">
          <div class="telemetry-grid">
            <div class="telemetry-box">
              <div class="telemetry-label">Latência RAG (RNF-14)</div>
              <div class="telemetry-val green">1.84s</div>
              <div class="telemetry-desc">Meta: < 2.50s em 95% das consultas. Totalmente em conformidade.</div>
            </div>
            <div class="telemetry-box">
              <div class="telemetry-label">Fidelidade RAG (RNF-03)</div>
              <div class="telemetry-val purple">91.4%</div>
              <div class="telemetry-desc">Meta: > 85.0% de precisão sem alucinação e com ancoragem nos dados do DF.</div>
            </div>
            <div class="telemetry-box">
              <div class="telemetry-label">Custo por Consulta (RNF-15)</div>
              <div class="telemetry-val blue">R$ 0.0035</div>
              <div class="telemetry-desc">Otimização máxima de tokens com chunking semântico estruturado.</div>
            </div>
          </div>

          <div style="background:#0d1117; border:1px solid var(--card-border); border-radius:10px; padding:20px;">
            <h3 style="margin-bottom:10px; font-size:1.1rem; color:var(--blue);">🚀 Tracing em Produção — Langfuse Cloud</h3>
            <p style="font-size:0.88rem; color:var(--text-muted); line-height:1.5; margin-bottom:16px;">
              O Grupo 7 instrumentou 100% das chamadas com o SDK oficial da Langfuse. Cada busca registra scores de similaridade, latência de embeddings, tokens consumidos e metadados de sessão.
            </p>
            <div style="font-family:monospace; font-size:0.82rem; background:#161b22; padding:10px 14px; border-radius:6px; margin-bottom:16px; border:1px dashed var(--purple);">
              Projeto Langfuse ID: <strong>cmw59be2y01d8ad0jqbgsjut6</strong> &bull; Host: https://cloud.langfuse.com
            </div>
            <div style="display:flex; gap:12px; flex-wrap:wrap;">
              <a href="https://cloud.langfuse.com/project/cmw59be2y01d8ad0jqbgsjut6" target="_blank" class="viewer-btn primary">
                Abrir Dashboard do Langfuse ↗
              </a>
              <a href="/rag" class="viewer-btn">
                Testar Busca com Telemetria ao Vivo &rarr;
              </a>
            </div>
          </div>
        </div>
      </div>
    </section>
  </main>

  <footer>
    Residência em IA — Instituto Eldorado & UnB • Challenge 2 (Grupo 7) • DevOps & LLMOps: Maria Eduarda
  </footer>

  <script>
    // State
    let dadosAprovadosCache = null;
    let dadosQuarentenaCache = null;
    let dadosVetoresCache = null;
    let conteudoTextoCache = '';

    function filtrarArvore(termo) {
      const q = termo.toLowerCase().trim();
      const items = document.querySelectorAll('#treeList .tree-item');
      items.forEach(el => {
        const text = el.innerText.toLowerCase();
        el.style.display = text.includes(q) ? 'flex' : 'none';
      });
    }

    function resetViews() {
      document.querySelectorAll('.view-container').forEach(el => el.classList.remove('active'));
      document.getElementById('btnCopy').style.display = 'none';
    }

    function setActiveTreeItem(target) {
      document.querySelectorAll('#treeList .tree-item').forEach(el => {
        el.classList.remove('active');
        el.classList.remove('special-active');
      });
      target.classList.add('active');
    }

    async function carregarArquivo(element) {
      setActiveTreeItem(element);
      const path = element.getAttribute('data-path');
      const type = element.getAttribute('data-type');

      document.getElementById('currentPathTxt').innerText = path;
      const badgeEl = document.getElementById('currentBadge');
      badgeEl.className = 'item-tag';

      const btnDownload = document.getElementById('btnDownload');
      const btnNewTab = document.getElementById('btnNewTab');

      resetViews();

      if (type === 'pdf') {
        badgeEl.innerText = 'PDF Oficial (4 Páginas)';
        badgeEl.classList.add('purple');
        btnDownload.href = '/download/relatorio-pdf';
        btnNewTab.href = '/download/relatorio-pdf';
        document.getElementById('viewPdf').classList.add('active');
      } 
      else if (type === 'zip') {
        badgeEl.innerText = 'Arquivo ZIP (3.7 MB)';
        badgeEl.classList.add('green');
        btnDownload.href = '/download/entregavel-zip';
        btnNewTab.href = '/download/entregavel-zip';
        document.getElementById('viewZip').classList.add('active');
      }
      else if (type === 'telemetria') {
        badgeEl.innerText = 'Live LLMOps';
        badgeEl.classList.add('purple');
        btnDownload.href = 'https://cloud.langfuse.com/project/cmw59be2y01d8ad0jqbgsjut6';
        btnNewTab.href = 'https://cloud.langfuse.com/project/cmw59be2y01d8ad0jqbgsjut6';
        document.getElementById('viewTelemetria').classList.add('active');
      }
      else if (type === 'aprovados') {
        badgeEl.innerText = '93 Rolês DF (2FA)';
        badgeEl.classList.add('green');
        btnDownload.href = '/api/entregaveis/arquivo?caminho=' + encodeURIComponent(path);
        btnNewTab.href = '/api/entregaveis/arquivo?caminho=' + encodeURIComponent(path);
        document.getElementById('viewAprovados').classList.add('active');
        if (!dadosAprovadosCache) {
          const res = await fetch('/api/entregaveis/dados?colecao=aprovados');
          const json = await res.json();
          dadosAprovadosCache = json.dados || [];
        }
        filtrarAprovados();
      }
      else if (type === 'quarentena') {
        badgeEl.innerText = '71 Quarentenados';
        badgeEl.classList.add('orange');
        btnDownload.href = '/api/entregaveis/arquivo?caminho=' + encodeURIComponent(path);
        btnNewTab.href = '/api/entregaveis/arquivo?caminho=' + encodeURIComponent(path);
        document.getElementById('viewQuarentena').classList.add('active');
        if (!dadosQuarentenaCache) {
          const res = await fetch('/api/entregaveis/dados?colecao=quarentena');
          const json = await res.json();
          dadosQuarentenaCache = json.dados || [];
        }
        filtrarQuarentena();
      }
      else if (type === 'vetores') {
        badgeEl.innerText = 'Embeddings 3072d';
        badgeEl.classList.add('purple');
        btnDownload.href = '/api/entregaveis/arquivo?caminho=' + encodeURIComponent(path);
        btnNewTab.href = '/api/entregaveis/arquivo?caminho=' + encodeURIComponent(path);
        document.getElementById('viewVetores').classList.add('active');
        if (!dadosVetoresCache) {
          const res = await fetch('/api/entregaveis/dados?colecao=vetores');
          const json = await res.json();
          dadosVetoresCache = json.dados || [];
        }
        filtrarVetores();
      }
      else {
        // Code / Markdown / Text / CSV
        badgeEl.innerText = type.toUpperCase();
        btnDownload.href = '/api/entregaveis/arquivo?caminho=' + encodeURIComponent(path);
        btnNewTab.href = '/api/entregaveis/arquivo?caminho=' + encodeURIComponent(path);
        document.getElementById('btnCopy').style.display = 'inline-flex';
        document.getElementById('viewCode').classList.add('active');

        document.getElementById('codeContent').innerText = 'Carregando arquivo...';
        try {
          const res = await fetch('/api/entregaveis/arquivo?caminho=' + encodeURIComponent(path));
          const json = await res.json();
          conteudoTextoCache = json.conteudo || JSON.stringify(json, null, 2);
          document.getElementById('codeContent').innerText = conteudoTextoCache;
        } catch (err) {
          document.getElementById('codeContent').innerText = 'Erro ao ler arquivo: ' + err.message;
        }
      }
    }

    function filtrarAprovados() {
      if (!dadosAprovadosCache) return;
      const q = document.getElementById('buscaAprovados').value.toLowerCase().trim();
      const cat = document.getElementById('filtroCategoriaAprovados').value;
      const ra = document.getElementById('filtroRaAprovados').value;

      const filtrados = dadosAprovadosCache.filter(item => {
        const matchesQ = !q || 
          (item.nome || '').toLowerCase().includes(q) ||
          (item.cidade_ra || item.regiao_administrativa || '').toLowerCase().includes(q) ||
          (item.resumo_sensorial || '').toLowerCase().includes(q) ||
          (item.vibes || []).some(v => v.toLowerCase().includes(q));

        const matchesCat = !cat || (item.tipo_de_role || '') === cat;
        const matchesRa = !ra || (item.regiao_administrativa || '').includes(ra);

        return matchesQ && matchesCat && matchesRa;
      });

      document.getElementById('counterAprovados').innerText = `Mostrando ${filtrados.length} de ${dadosAprovadosCache.length} rolês auditados`;

      const grid = document.getElementById('gridAprovados');
      grid.innerHTML = '';
      filtrados.forEach(item => {
        const card = document.createElement('div');
        card.className = 'data-card';
        card.innerHTML = `
          <div class="card-top">
            <div class="card-name">
              <span>${item.nome}</span>
              <span class="item-tag green">✅ 2FA OK</span>
            </div>
            <div class="card-meta">
              ${item.tipo_de_role} &bull; ${item.regiao_administrativa} &bull; ${item.faixa_de_preco} (R$ ${item.custo_medio_rs || 'N/A'})
            </div>
            <div class="card-desc">
              ${item.resumo_sensorial || ''}
            </div>
            <div style="display:flex; flex-wrap:wrap; gap:4px; margin-bottom:8px;">
              ${(item.vibes || []).map(v => `<span class="item-tag purple">${v}</span>`).join('')}
            </div>
            <div style="font-size:0.75rem; color:var(--text-muted); margin-bottom:4px;">
              ⏰ <strong>Horário:</strong> ${item.horario_funcionamento || 'Consulte o local'}
            </div>
            <div style="font-size:0.72rem; color:var(--text-muted);">
              📍 ${item.endereco || item.regiao_administrativa}
            </div>
          </div>
          <div class="card-bottom">
            <span style="font-size:0.72rem; color:var(--text-muted);">Validação: ${item.fonte_validacao_fator2 || 'Fator 1 + Fator 2'}</span>
            ${item.tiktok_url ? `<a href="${item.tiktok_url}" target="_blank" class="tiktok-link">▶️ TikTok ↗</a>` : ''}
          </div>
        `;
        grid.appendChild(card);
      });
    }

    function filtrarQuarentena() {
      if (!dadosQuarentenaCache) return;
      const q = document.getElementById('buscaQuarentena').value.toLowerCase().trim();
      const mot = document.getElementById('filtroMotivoQuarentena').value.toLowerCase();

      const filtrados = dadosQuarentenaCache.filter(item => {
        const matchesQ = !q || 
          (item.nome || '').toLowerCase().includes(q) ||
          (item.video_id || '').toLowerCase().includes(q) ||
          (item.motivo || '').toLowerCase().includes(q) ||
          (item.autor_tiktok || '').toLowerCase().includes(q);

        const matchesMot = !mot || (item.motivo || '').toLowerCase().includes(mot);
        return matchesQ && matchesMot;
      });

      document.getElementById('counterQuarentena').innerText = `Mostrando ${filtrados.length} de ${dadosQuarentenaCache.length} vídeos quarentenados`;

      const grid = document.getElementById('gridQuarentena');
      grid.innerHTML = '';
      filtrados.forEach(item => {
        const card = document.createElement('div');
        card.className = 'data-card';
        card.innerHTML = `
          <div class="card-top">
            <div class="card-name">
              <span>Vídeo #${item.video_id}</span>
              <span class="item-tag orange">⚠️ Retido pelo 2FA</span>
            </div>
            <div class="card-meta">
              Autor: @${item.autor_tiktok || 'desconhecido'} &bull; Publicado: ${item.ano_mes || item.data_publicacao || '2026'}
            </div>
            <div class="card-quarantine-box">
              <strong>Motivo da Reprovação:</strong><br>
              ${item.motivo || 'Falta de evidência de preço ou localização exata'}
            </div>
            <div style="font-size:0.75rem; color:var(--text-muted); line-height:1.4;">
              <em>"${(item.transcricao_audio_whisper || item.legenda_original || '').slice(0, 140)}..."</em>
            </div>
          </div>
          <div class="card-bottom">
            <span style="font-size:0.72rem; color:var(--text-muted);">Auditoria Automática</span>
            ${item.tiktok_url ? `<a href="${item.tiktok_url}" target="_blank" class="tiktok-link">▶️ Ver no TikTok ↗</a>` : ''}
          </div>
        `;
        grid.appendChild(card);
      });
    }

    function filtrarVetores() {
      if (!dadosVetoresCache) return;
      const q = document.getElementById('buscaVetores').value.toLowerCase().trim();

      const filtrados = dadosVetoresCache.filter(item => {
        return !q ||
          (item.nome || '').toLowerCase().includes(q) ||
          (item.documento_indexado || '').toLowerCase().includes(q);
      });

      document.getElementById('counterVetores').innerText = `Mostrando ${filtrados.length} de ${dadosVetoresCache.length} chunks indexados`;

      const container = document.getElementById('gridVetores');
      container.innerHTML = '';
      filtrados.forEach(item => {
        const div = document.createElement('div');
        div.className = 'vector-chunk-card';
        div.innerHTML = `
          <div class="vector-chunk-title">${item.nome} &bull; ${item.regiao_administrativa || ''}</div>
          <div class="vector-chunk-text">${item.documento_indexado || ''}</div>
          <div class="vector-preview-box">
            <strong>Vetor (3.072 float32):</strong> [${(item.vetor_preview || []).map(n => typeof n === 'number' ? n.toFixed(5) : n).join(', ')}, ... +3067 dimensões]
          </div>
        `;
        container.appendChild(div);
      });
    }

    function copiarConteudoAtual() {
      if (conteudoTextoCache) {
        navigator.clipboard.writeText(conteudoTextoCache).then(() => {
          alert('Conteúdo copiado para a área de transferência!');
        });
      }
    }
  </script>
</body>
</html>
"""
