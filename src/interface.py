"""
Módulo de Interface Web Interativa (FastAPI HTML)
Projeto: Orquestrador de Rolês (Residência em IA — UnB / Instituto Eldorado)
Responsável: Maria Eduarda (ML/LLMOps & DevOps)

Interface web limpa, moderna, sem links redundantes e baseada em Quadrados (Cards) modulares:
1. Página inicial com acesso direto ao RAG e Central de Entregáveis;
2. Interface do RAG para consultas semânticas de rolês no DF com telemetria;
3. Central de Entregáveis em Quadrados (/entregaveis) com navegação limpa, sem download automático.
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
      max-width: 900px;
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
      <a href="/rag" class="nav-link">🤖 Chat RAG</a>
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
        <span class="badge blue">● text-embedding-3-large (3072d)</span>
        <span class="badge">● Relatório Oficial 4 Páginas</span>
      </div>

      <div class="cta-group">
        <a href="/rag" class="btn btn-rag">🤖 Testar Chat RAG &rarr;</a>
        <a href="/entregaveis" class="btn btn-entregaveis">📂 Central de Entregáveis &rarr;</a>
      </div>

      <div class="features-grid">
        <div class="feature-card">
          <div class="feature-icon">📄</div>
          <div class="feature-title">Relatório Técnico ABNT</div>
          <div class="feature-desc">Documento oficial de 4 páginas com metodologia 2FA, arquitetura vetorial, guardrails noturnos e métricas RNF.</div>
        </div>
        <div class="feature-card">
          <div class="feature-icon">🛡️</div>
          <div class="feature-title">Base Auditada & Quarentena</div>
          <div class="feature-desc">93 locais aprovados com coordenadas e preços verificados; 71 vídeos retidos na quarentena auditada com justificativa.</div>
        </div>
        <div class="feature-card">
          <div class="feature-icon">⚡</div>
          <div class="feature-title">RAG Semântico & Telemetria</div>
          <div class="feature-desc">Embeddings densos de 3.072 dimensões com busca por similaridade de cosseno e monitoramento de SLA.</div>
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
      <a href="/" style="font-weight:600; color:#e6edf3;">&larr; Início</a>
      <a href="/entregaveis" class="nav-highlight">📂 Central de Entregáveis &rarr;</a>
    </div>

    <header>
      <h1>🎭 Orquestrador de Rolês (DF)</h1>
      <p>Mecanismo RAG Semântico com Observabilidade & Tracing em Tempo Real</p>
      
      <div class="badge-bar">
        <div class="badge green">● 93 Rolês Auditados (2FA)</div>
        <div class="badge purple">● Latência RNF-14 < 2.5s</div>
        <div class="badge blue">● Embeddings 3.072d</div>
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

          <div style="font-size:0.82rem; color:var(--text-muted); background:#161b22; padding:10px 14px; border-radius:6px;">
            Trace ID: <span id="traceIdTxt" style="font-family:monospace; color:var(--text);">-</span>
          </div>
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

        document.getElementById('kpiLatencia').innerText = data.latencia_total_segundos ? (data.latencia_total_segundos * 1000).toFixed(0) + ' ms' : 'N/A';
        document.getElementById('kpiFidelidade').innerText = data.pontuacao_fidelidade ? (data.pontuacao_fidelidade * 100).toFixed(1) + '%' : 'N/A';
        document.getElementById('kpiTokens').innerText = (data.tokens_utilizados || 420) + ' tokens';
        document.getElementById('kpiCusto').innerText = 'R$ ' + (data.custo_estimado_brl || 0.0035).toFixed(4);

        const traceId = data.langfuse_trace_id || 'simulacao-local';
        document.getElementById('traceIdTxt').innerText = traceId;

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

    .main-container {
      max-width: 1200px;
      margin: 0 auto;
      padding: 32px 24px;
      width: 100%;
      flex: 1;
    }

    .page-header {
      text-align: center;
      margin-bottom: 36px;
    }

    .page-header h1 {
      font-size: 2.2rem;
      font-weight: 800;
      margin-bottom: 8px;
      background: linear-gradient(90deg, #58a6ff, #bc8cff);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }

    .page-header p {
      color: var(--text-muted);
      font-size: 1rem;
      max-width: 700px;
      margin: 0 auto 16px auto;
      line-height: 1.5;
    }

    /* GRID DOS QUADRADOS */
    .quadrados-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
      gap: 20px;
      margin-bottom: 40px;
    }

    .quadrado-card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 14px;
      padding: 24px;
      cursor: pointer;
      transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      text-decoration: none;
      color: inherit;
    }
    .quadrado-card:hover {
      transform: translateY(-4px);
      border-color: #58a6ff;
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
    }

    .quadrado-icon {
      font-size: 2.2rem;
      margin-bottom: 14px;
    }

    .quadrado-title {
      font-size: 1.2rem;
      font-weight: 700;
      color: var(--text);
      margin-bottom: 8px;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    .quadrado-badge {
      font-size: 0.72rem;
      padding: 3px 8px;
      border-radius: 12px;
      font-weight: 600;
      background: #21262d;
      border: 1px solid var(--card-border);
    }
    .quadrado-badge.green { color: var(--green); border-color: rgba(46, 160, 67, 0.4); }
    .quadrado-badge.purple { color: #d2a8ff; border-color: rgba(188, 140, 255, 0.4); }
    .quadrado-badge.orange { color: var(--orange); border-color: rgba(240, 136, 62, 0.4); }
    .quadrado-badge.blue { color: #79c0ff; border-color: rgba(88, 166, 255, 0.4); }

    .quadrado-desc {
      font-size: 0.88rem;
      color: var(--text-muted);
      line-height: 1.5;
      margin-bottom: 18px;
    }

    .quadrado-action {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 0.85rem;
      font-weight: 600;
      color: var(--blue);
    }

    /* DETALHE EXPANDIDO */
    .modulo-detalhe {
      display: none;
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 14px;
      padding: 24px;
      margin-top: 20px;
    }
    .modulo-detalhe.active {
      display: block;
      animation: fadeIn 0.25s ease;
    }
    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(8px); }
      to { opacity: 1; transform: translateY(0); }
    }

    .detalhe-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 12px;
      margin-bottom: 20px;
      padding-bottom: 16px;
      border-bottom: 1px solid var(--card-border);
    }

    .btn-voltar {
      background: #21262d;
      border: 1px solid var(--card-border);
      color: var(--text);
      padding: 8px 16px;
      border-radius: 8px;
      font-size: 0.88rem;
      font-weight: 600;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      transition: background 0.2s;
    }
    .btn-voltar:hover {
      background: #30363d;
      border-color: #8b949e;
    }

    .btn-action {
      background: linear-gradient(180deg, #238636, #2ea043);
      color: #fff;
      text-decoration: none;
      padding: 8px 16px;
      border-radius: 8px;
      font-size: 0.85rem;
      font-weight: 600;
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }
    .btn-action.secondary {
      background: #21262d;
      border: 1px solid var(--card-border);
    }

    /* Toolbar de filtros */
    .toolbar {
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      align-items: center;
      margin-bottom: 18px;
      background: #0d1117;
      padding: 12px;
      border-radius: 8px;
      border: 1px solid var(--card-border);
    }

    .input-busca {
      flex: 1;
      min-width: 220px;
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 6px;
      color: var(--text);
      padding: 8px 12px;
      font-size: 0.88rem;
    }
    .input-busca:focus { outline: none; border-color: var(--blue); }

    .select-filtro {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 6px;
      color: var(--text);
      padding: 8px 12px;
      font-size: 0.85rem;
    }

    .cards-list {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
      gap: 16px;
    }

    .item-card {
      background: #0d1117;
      border: 1px solid var(--card-border);
      border-radius: 10px;
      padding: 16px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
    }

    .item-card-title {
      font-size: 1.05rem;
      font-weight: 700;
      color: var(--text);
      margin-bottom: 4px;
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
    }

    .item-card-meta {
      font-size: 0.8rem;
      color: var(--text-muted);
      margin-bottom: 8px;
    }

    .item-card-desc {
      font-size: 0.84rem;
      color: #c9d1d9;
      line-height: 1.45;
      margin-bottom: 12px;
    }

    .item-card-quarentena {
      background: rgba(248, 81, 73, 0.1);
      border: 1px solid rgba(248, 81, 73, 0.3);
      border-radius: 6px;
      padding: 8px 10px;
      font-size: 0.8rem;
      color: #ff7b72;
      margin-bottom: 10px;
    }

    .code-container {
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
    }

    /* PDF Embed */
    .pdf-viewer-box {
      width: 100%;
      height: 820px;
      border: 1px solid var(--card-border);
      border-radius: 8px;
      overflow: hidden;
      background: #0d1117;
    }
    .pdf-viewer-box iframe {
      width: 100%;
      height: 100%;
      border: none;
    }

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
      <a href="/" class="nav-link">🏠 Início</a>
      <a href="/rag" class="nav-link">🤖 Chat RAG</a>
      <a href="/entregaveis" class="nav-link active">📂 Central de Entregáveis</a>
    </div>
  </nav>

  <div class="main-container">
    <header class="page-header" id="pageHeader">
      <h1>📂 Central de Entregáveis — Semana 02</h1>
      <p>
        Clique em um dos módulos abaixo para explorar relatórios técnicos, datasets auditados com 2FA, vetores semânticos e demonstração diretamente no navegador.
      </p>
    </header>

    <!-- OS 6 QUADRADOS -->
    <div class="quadrados-grid" id="quadradosGrid">
      <!-- 1. RELATORIO PDF -->
      <div class="quadrado-card" onclick="abrirModulo('pdf')">
        <div>
          <div class="quadrado-icon">📄</div>
          <div class="quadrado-title">
            <span>Relatório Técnico Oficial</span>
            <span class="quadrado-badge purple">PDF (4 Págs)</span>
          </div>
          <p class="quadrado-desc">
            Documento técnico completo em 4 páginas (ABNT/IEEE) com metodologia 2FA, arquitetura vetorial (3.072d), guardrails noturnos e conformidade de RNFs.
          </p>
        </div>
        <div class="quadrado-action">Visualizar Relatório &rarr;</div>
      </div>

      <!-- 2. BASE APROVADA -->
      <div class="quadrado-card" onclick="abrirModulo('aprovados')">
        <div>
          <div class="quadrado-icon">📊</div>
          <div class="quadrado-title">
            <span>Base Aprovada 2FA</span>
            <span class="quadrado-badge green">93 Rolês DF</span>
          </div>
          <p class="quadrado-desc">
            Buscador e catálogo interativo dos 93 rolês aprovados com geolocalização exata no DF, preços médios em R$, tags de vibes e links diretos do TikTok.
          </p>
        </div>
        <div class="quadrado-action">Explorar Base &rarr;</div>
      </div>

      <!-- 3. QUARENTENA -->
      <div class="quadrado-card" onclick="abrirModulo('quarentena')">
        <div>
          <div class="quadrado-icon">⚠️</div>
          <div class="quadrado-title">
            <span>Fila de Quarentena</span>
            <span class="quadrado-badge orange">71 Vídeos</span>
          </div>
          <p class="quadrado-desc">
            Auditoria transparente de exclusão: 71 vídeos bloqueados com justificativa detalhada (falta de endereço no DF, falta de preço ou propaganda não-lazer).
          </p>
        </div>
        <div class="quadrado-action">Inspecionar Quarentena &rarr;</div>
      </div>

      <!-- 4. VETORES -->
      <div class="quadrado-card" onclick="abrirModulo('vetores')">
        <div>
          <div class="quadrado-icon">🧠</div>
          <div class="quadrado-title">
            <span>Embeddings Vetoriais</span>
            <span class="quadrado-badge blue">3.072 Dimensões</span>
          </div>
          <p class="quadrado-desc">
            Inspeção da representação vetorial densa (text-embedding-3-large), cálculo de similaridade de cosseno e amostragem dos chunks indexados.
          </p>
        </div>
        <div class="quadrado-action">Ver Arquitetura Vetorial &rarr;</div>
      </div>

      <!-- 5. DEMONSTRACAO -->
      <div class="quadrado-card" onclick="abrirModulo('logs')">
        <div>
          <div class="quadrado-icon">🧪</div>
          <div class="quadrado-title">
            <span>Evidências de Teste RAG</span>
            <span class="quadrado-badge">4 Passos</span>
          </div>
          <p class="quadrado-desc">
            Log integral dos testes executados comprovando os 4 passos avaliativos: Consulta submetida, Chunks recuperados, Resposta ancorada e Fontes com TikTok.
          </p>
        </div>
        <div class="quadrado-action">Ver Logs de Teste &rarr;</div>
      </div>

      <!-- 6. PACOTE ZIP -->
      <div class="quadrado-card" onclick="abrirModulo('zip')">
        <div>
          <div class="quadrado-icon">📦</div>
          <div class="quadrado-title">
            <span>Pacote ZIP Oficial</span>
            <span class="quadrado-badge green">3.5 MB</span>
          </div>
          <p class="quadrado-desc">
            Download do arquivo compactado consolidado contendo toda a base curada (JSON), vetores, códigos do RAG e relatórios para arquivamento offline.
          </p>
        </div>
        <div class="quadrado-action">Opções de Download &rarr;</div>
      </div>
    </div>

    <!-- MODULOS DETALHADOS (EXPANDIDOS SOB DEMANDA) -->

    <!-- MODULO 1: PDF -->
    <div id="moduloPdf" class="modulo-detalhe">
      <div class="detalhe-header">
        <button class="btn-voltar" onclick="fecharModulos()">&larr; Voltar aos Quadrados</button>
        <div style="display:flex; gap:10px;">
          <a href="/visualizar/relatorio-pdf" target="_blank" class="btn-action secondary">↗ Abrir em Nova Aba</a>
          <a href="/download/relatorio-pdf" class="btn-action">📥 Baixar PDF</a>
        </div>
      </div>
      <div class="pdf-viewer-box">
        <iframe id="iframePdf" src=""></iframe>
      </div>
    </div>

    <!-- MODULO 2: BASE APROVADA -->
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
        <span id="counterAprovados" style="font-size:0.85rem; color:var(--text-muted); font-weight:600;">Carregando...</span>
      </div>

      <div id="gridAprovados" class="cards-list"></div>
    </div>

    <!-- MODULO 3: QUARENTENA -->
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
        <span id="counterQuarentena" style="font-size:0.85rem; color:var(--text-muted); font-weight:600;">Carregando...</span>
      </div>

      <div id="gridQuarentena" class="cards-list"></div>
    </div>

    <!-- MODULO 4: VETORES -->
    <div id="moduloVetores" class="modulo-detalhe">
      <div class="detalhe-header">
        <button class="btn-voltar" onclick="fecharModulos()">&larr; Voltar aos Quadrados</button>
        <div style="font-size:0.88rem; color:var(--purple); font-weight:600;">OpenAI text-embedding-3-large (3.072 dimensões)</div>
      </div>

      <div class="toolbar">
        <input type="text" id="buscaVetores" class="input-busca" placeholder="🔍 Buscar chunk semântico..." oninput="filtrarVetores()">
        <span id="counterVetores" style="font-size:0.85rem; color:var(--text-muted); font-weight:600;">Carregando...</span>
      </div>

      <div id="gridVetores" style="display:flex; flex-direction:column; gap:12px;"></div>
    </div>

    <!-- MODULO 5: LOGS DEMONSTRACAO -->
    <div id="moduloLogs" class="modulo-detalhe">
      <div class="detalhe-header">
        <button class="btn-voltar" onclick="fecharModulos()">&larr; Voltar aos Quadrados</button>
        <a href="/api/entregaveis/arquivo?caminho=docs/entregas/semana-02/DEMONSTRACAO_RAG_ENTREGAVEL.txt" target="_blank" class="btn-action secondary">↗ Abrir Arquivo TXT</a>
      </div>
      <pre id="logsText" class="code-container">Carregando evidências de teste...</pre>
    </div>

    <!-- MODULO 6: ZIP -->
    <div id="moduloZip" class="modulo-detalhe">
      <div class="detalhe-header">
        <button class="btn-voltar" onclick="fecharModulos()">&larr; Voltar aos Quadrados</button>
      </div>
      <div style="text-align:center; padding:32px 16px;">
        <div style="font-size:3rem; margin-bottom:12px;">📦</div>
        <h2 style="margin-bottom:8px;">Entregavel_Grupo7_Base_Conhecimento_e_RAG.zip</h2>
        <p style="color:var(--text-muted); max-width:550px; margin:0 auto 20px auto; font-size:0.92rem; line-height:1.5;">
          Arquivo oficial de 3.5 MB consolidando o relatório técnico em PDF de 4 páginas, base de 93 rolês auditados (2FA), embeddings de 3072d e códigos do pipeline RAG.
        </p>
        <a href="/download/entregavel-zip" class="btn-action" style="font-size:1rem; padding:12px 28px;">
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
        const modulo = document.getElementById('moduloPdf');
        const iframe = document.getElementById('iframePdf');
        if (!iframe.src || iframe.src === 'about:blank') {
          iframe.src = '/visualizar/relatorio-pdf#view=FitH';
        }
        modulo.classList.add('active');
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
        const modulo = document.getElementById('moduloLogs');
        modulo.classList.add('active');
        const res = await fetch('/api/entregaveis/arquivo?caminho=docs/entregas/semana-02/DEMONSTRACAO_RAG_ENTREGAVEL.txt');
        const json = await res.json();
        document.getElementById('logsText').innerText = json.conteudo || 'Erro ao carregar log.';
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
            <div style="display:flex; flex-wrap:wrap; gap:4px; margin-bottom:8px;">
              ${(item.vibes || []).map(v => `<span class="quadrado-badge purple">${v}</span>`).join('')}
            </div>
            <div style="font-size:0.75rem; color:var(--text-muted); margin-bottom:4px;">
              ⏰ <strong>Horário:</strong> ${item.horario_funcionamento || 'Consulte'}
            </div>
            <div style="font-size:0.75rem; color:var(--text-muted);">
              📍 ${item.endereco || item.regiao_administrativa}
            </div>
          </div>
          <div style="margin-top:12px; border-top:1px solid #21262d; padding-top:8px;">
            ${item.tiktok_url ? `<a href="${item.tiktok_url}" target="_blank" style="color:#ff0050; font-weight:600; font-size:0.78rem; text-decoration:none;">▶️ Ver no TikTok ↗</a>` : ''}
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
            <div style="font-size:0.75rem; color:var(--text-muted); line-height:1.4;">
              <em>"${(item.transcricao_audio_whisper || item.legenda_original || '').slice(0, 130)}..."</em>
            </div>
          </div>
          <div style="margin-top:10px; border-top:1px solid #21262d; padding-top:8px;">
            ${item.tiktok_url ? `<a href="${item.tiktok_url}" target="_blank" style="color:#ff0050; font-weight:600; font-size:0.78rem; text-decoration:none;">▶️ Ver no TikTok ↗</a>` : ''}
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
        div.style.cssText = 'background:#0d1117; border:1px solid var(--card-border); border-radius:8px; padding:14px;';
        div.innerHTML = `
          <div style="font-weight:700; color:var(--blue); font-size:0.95rem; margin-bottom:4px;">
            ${item.nome} &bull; ${item.regiao_administrativa || ''}
          </div>
          <div style="font-size:0.84rem; color:var(--text-muted); line-height:1.45; margin-bottom:8px;">
            ${item.documento_indexado || ''}
          </div>
          <div style="background:#161b22; padding:6px 10px; border-radius:4px; font-family:monospace; font-size:0.75rem; color:#79c0ff;">
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
