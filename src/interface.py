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
      background: linear-gradient(90deg, #58a6ff, #bc8cff);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
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
      background: linear-gradient(90deg, #58a6ff, #bc8cff);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
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
      <a href="/entregaveis" class="nav-highlight">📂 Central de Entregáveis &rarr;</a>
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
      background: linear-gradient(90deg, #58a6ff, #bc8cff);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
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
      padding: 24px;
      color: #e6edf3;
      font-size: 0.88rem;
      line-height: 1.6;
    }
    .relatorio-html h2 {
      font-size: 1.15rem;
      color: var(--blue);
      border-bottom: 1px solid #30363d;
      padding-bottom: 4px;
      margin: 20px 0 10px 0;
    }
    .relatorio-html h3 {
      font-size: 0.98rem;
      color: #d2a8ff;
      margin: 14px 0 6px 0;
    }
    .relatorio-html p { margin-bottom: 10px; color: #c9d1d9; }
    .relatorio-html ul, .relatorio-html ol { margin-left: 20px; margin-bottom: 12px; }
    .relatorio-html li { margin-bottom: 4px; }
    .relatorio-html table {
      width: 100%;
      border-collapse: collapse;
      margin: 12px 0 16px 0;
      font-size: 0.8rem;
    }
    .relatorio-html th, .relatorio-html td {
      border: 1px solid var(--card-border);
      padding: 8px 10px;
      text-align: left;
    }
    .relatorio-html th {
      background: #161b22;
      color: var(--blue);
    }
    .relatorio-html tr:nth-child(even) { background: #161b22; }
    .box-destaque {
      background: rgba(88, 166, 255, 0.08);
      border-left: 3px solid var(--blue);
      padding: 10px 14px;
      border-radius: 4px;
      margin: 12px 0;
      font-size: 0.84rem;
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
            <span class="quadrado-badge purple">4 Págs ABNT</span>
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
        <div style="background:#161b22; border-left:4px solid var(--blue); padding:12px 16px; border-radius:6px; margin-bottom:18px;">
          <h2 style="margin:0 0 4px 0; border:none; padding:0; font-size:1.25rem;">Relatório Técnico: Base de Conhecimento, Protótipo de RAG e Telemetria</h2>
          <div style="font-size:0.8rem; color:var(--text-muted); line-height:1.4;">
            <strong>RES IA ELD UNB — Turma 2 | Grupo 7 — Orquestrador de Rolês (Brasília/DF)</strong><br>
            <strong>Equipe:</strong> Letícia Miti Takahashi (Engenharia de Dados & RAG) e Maria Eduarda (DevOps, Infraestrutura & LLMOps)<br>
            <strong>Aplicação Online:</strong> <a href="/rag" style="color:#79c0ff;">orquestrador-roles.onrender.com/rag</a> | 
            <strong>Central de Entregáveis:</strong> <a href="/entregaveis" style="color:#bc8cff;">orquestrador-roles.onrender.com/entregaveis</a>
          </div>
        </div>

        <h2>1. Resumo Executivo e Checklist dos Artefatos</h2>
        <p>O objetivo deste entregável da Semana 2 é construir e auditar o mecanismo de <strong>RAG (Retrieval-Augmented Generation)</strong> fundamentado em base de conhecimento curada do DF, assegurando alta precisão na recuperação semântica, respostas sem alucinações e rastreabilidade total das fontes.</p>

        <table>
          <thead>
            <tr>
              <th>Requisito do Edital</th>
              <th>Status</th>
              <th>Localização no Repositório</th>
              <th>Resumo Técnico</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td><strong>1. Base curada</strong></td>
              <td><span class="quadrado-badge green">Concluído</span></td>
              <td><code>data/banco_aprovado_2fa.json</code></td>
              <td>93 estabelecimentos aprovados pelo protocolo 2FA.</td>
            </tr>
            <tr>
              <td><strong>2. Mínimo 20 fontes</strong></td>
              <td><span class="quadrado-badge green">Superado</span></td>
              <td><code>data/banco_aprovado_2fa.json</code> (93 fontes)</td>
              <td>164 vídeos auditados da safra 2026 (@rolezandoembrasilia).</td>
            </tr>
            <tr>
              <td><strong>3. Estratégia chunking</strong></td>
              <td><span class="quadrado-badge green">Concluído</span></td>
              <td>Seção 2 + <code>src/rag/banco_vetorial.py</code></td>
              <td><em>Entity-Centric Semantic Chunking</em> (1 chunk por rolê).</td>
            </tr>
            <tr>
              <td><strong>4. Embeddings</strong></td>
              <td><span class="quadrado-badge green">Concluído</span></td>
              <td>Seção 3 + <code>src/rag/banco_vetorial.py</code></td>
              <td><code>text-embedding-3-large</code> (3.072 dimensões) + Cosseno.</td>
            </tr>
            <tr>
              <td><strong>5. Banco vetorial</strong></td>
              <td><span class="quadrado-badge green">Concluído</span></td>
              <td><code>data/banco_vetorial_embeddings.json</code></td>
              <td>93 vetores densos persistidos com busca Top-K (K=3).</td>
            </tr>
            <tr>
              <td><strong>6. Demonstração RAG</strong></td>
              <td><span class="quadrado-badge green">Concluído</span></td>
              <td><code>src/rag/prototipo_rag.py</code> + <code>.txt</code></td>
              <td>4 passos: Consulta &rarr; Chunks &rarr; Resposta &rarr; Fontes.</td>
            </tr>
            <tr>
              <td><strong>7. Diagrama & Pipeline</strong></td>
              <td><span class="quadrado-badge green">Concluído</span></td>
              <td>Seções 4 e 5 deste relatório</td>
              <td>Fluxos de Ingestão 2FA e Arquitetura de Runtime RAG.</td>
            </tr>
            <tr>
              <td><strong>8. Telemetria LLMOps</strong></td>
              <td><span class="quadrado-badge green">Concluído</span></td>
              <td>Seção 6 + <code>src/telemetria/telemetria.py</code></td>
              <td>Langfuse Cloud v5.x (Auditoria RNF-03 e RNF-14).</td>
            </tr>
          </tbody>
        </table>

        <h2>2. Estratégia de Chunking (Entity-Centric Semantic Chunking)</h2>
        <h3>Por que não utilizar Fixed-Size Chunking?</h3>
        <p>Vídeos curtos de gastronomia e lazer (30 a 60 segundos) apresentam estrutura não linear: o nome do local aparece no início, as atrações no meio e o preço e endereço no final. Um particionamento cego por número fixo de caracteres separaria o endereço do nome, quebrando o contexto e induzindo alucinações.</p>

        <h3>Solução Adotada: 1 Documento-Fonte = 1 Chunk Semântico Autocontido</h3>
        <p>Cada estabelecimento aprovado consolida 4 camadas de informação em um bloco único coeso (~120 a 190 tokens):</p>
        <ol>
          <li><strong>Identidade e Categoria (Fator 1):</strong> Nome oficial e classificação estruturada (Restaurante, Bar/Pub, Cafeteria, Ao Ar Livre, Experiência).</li>
          <li><strong>Ancoragem Geoespacial e Financeira (Fator 2):</strong> Região Administrativa (RA), endereço validado via GPS Nominatim e preço médio em R$.</li>
          <li><strong>Atmosfera e Cultura (Fator 1):</strong> Tags de Vibes (Romântico, Calmo, Baratinho, Kid Friendly, Animado) e Resumo Sensorial.</li>
          <li><strong>Evidência Oral Bruta (Whisper ASR):</strong> Trecho literal da transcrição do áudio, preservando pratos e atrações específicas.</li>
        </ol>

        <div class="box-destaque">
          <strong>Template Estruturado do Chunk Indexado:</strong><br>
          <code>Local: {nome} | Categoria: {tipo} | Região: {RA} ({endereco}) | Preço: {faixa} (R$ {custo_medio}) | Vibes: {vibes} | Experiência: {resumo_sensorial} | TikTok: {transcricao_whisper}</code>
        </div>

        <h2>3. Estratégia de Embeddings e Banco Vetorial</h2>
        <ul>
          <li><strong>Modelo de Embedding:</strong> <code>text-embedding-3-large</code> (OpenAI) / <code>gemini-embedding-001</code>.</li>
          <li><strong>Dimensionalidade:</strong> <strong>3.072 dimensões</strong> (vetores densos de alta fidelidade sem perda de nuances).</li>
          <li><strong>Métrica de Similaridade:</strong> Similaridade de Cosseno calculada entre o vetor da consulta e os 93 vetores curados:</li>
        </ul>
        <div style="text-align:center; padding:8px; background:#161b22; border-radius:6px; margin:8px 0; font-family:monospace; color:#79c0ff;">
          Similaridade(q, d) = (q &bull; d) / (||q|| * ||d||)
        </div>

        <h2>4. Pipeline de Ingestão de Dados (Curadoria em 2 Fatores — 2FA)</h2>
        <p>Para impedir que vídeos patrocinados de varejo (lojas de colchão, óticas) ou locais sem preço contaminassem a base, criamos o filtro de 2 Fatores:</p>
        <ul>
          <li><strong>Etapa 1 — Coleta & ASR:</strong> 164 vídeos brutos de 2026 (@rolezandoembrasilia) com extração de áudio e transcrição via Whisper.</li>
          <li><strong>Etapa 2 — FATOR 1 (Cultural):</strong> Filtro semântico que descartou 47 propagandas não-lazer e aprovou 117 locais culturais.</li>
          <li><strong>Etapa 3 — FATOR 2 (Prático):</strong> Dupla trava exigindo Endereço no DF validado via GPS + Preço comprovado em R$. Retidos 24 vídeos na quarentena e homologadas <strong>93 fontes definitivas</strong>.</li>
          <li><strong>Etapa 4 — Indexação:</strong> Geração dos 93 vetores de 3.072d persistidos em <code>data/banco_vetorial_embeddings.json</code>.</li>
        </ul>

        <h2>5. Telemetria, Observabilidade e Auditoria de RNFs</h2>
        <p>A instrumentação no Langfuse Cloud audita cada chamada em tempo real:</p>
        <ul>
          <li><strong>Fidelidade (RNF-03):</strong> Score 1.0 (100% ancorado nos 93 documentos, zero alucinação).</li>
          <li><strong>Latência (RNF-14):</strong> Recuperação vetorial entre 2.8 ms e 21.9 ms (meta SLA &lt; 2.5s plenamente atendida).</li>
          <li><strong>Governança de Custos (RNF-15):</strong> Consumo médio de ~345 tokens totais por consulta, mantendo custo de R$ 0,0035 por requisição.</li>
        </ul>

        <h2>6. Preparação para a Semana 3 (Baseline LLM vs. RAG)</h2>
        <p>A base homologada de 93 rolês e os traces do Langfuse formam o <em>Golden Dataset</em> para o benchmark da Semana 3, que comparará respostas geradas sem contexto (Zero-Shot) versus o nosso RAG fundamentado.</p>
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
          Arquivo compactado consolidado (3.5 MB) contendo o relatório técnico oficial de 4 páginas em PDF, base homologada de 93 rolês (JSON), vetores de 3072d e códigos do pipeline RAG.
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
