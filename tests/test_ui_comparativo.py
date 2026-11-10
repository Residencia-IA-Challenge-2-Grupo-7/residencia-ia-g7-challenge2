"""
Testes automatizados da Interface Web de Comparação Lado a Lado: LLM Pura vs. RAG (/comparativo)
Referência: Issue #37 — [Semana 3] [FRONTEND] Interface Web de Comparação Lado a Lado: LLM Pura vs. RAG (/comparativo)
Responsável: Maria Carolina (@mcznh)
"""

from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)


def test_rota_comparativo_retorna_200_e_estrutura_lado_a_lado():
    """Valida que GET /comparativo retorna HTTP 200 e contém os elementos estruturais dos dois modos."""
    response = client.get("/comparativo")
    assert response.status_code == 200
    html = response.text

    # 1. Colunas Lado a Lado (Modo A vs Modo B)
    assert "Modo A — LLM Pura (Zero-Shot)" in html
    assert "Modo B — RAG Ancorado" in html

    # 2. Badges de Status (RNF-03 / RNF-07)
    assert "⚠️ Sem Evidências — Sujeito a Alucinação" in html
    assert "✅ 100% Fundamentado na Base Curada do DF" in html

    # 3. Seletor de Perguntas do Golden Dataset e Input de Pergunta Livre
    assert 'id="goldenSelect"' in html
    assert "golden_01" in html
    assert "golden_10" in html
    assert 'id="perguntaComparativoInput"' in html

    # 4. Métricas de Score, Botões de Informação, Dark Mode, Paleta e Evidências (Fontes #1 e #2, TikTok e Langfuse Trace)
    assert "Google Gemini 1.5 Flash (gemini-1.5-flash)" in html
    assert "Informação sobre Zero-Shot" in html
    assert "O que é Zero-Shot:" in html
    assert 'id="themeToggleBtn"' in html
    assert "body.dark-mode" in html
    assert "Como calculamos as porcentagens:" in html
    assert "Informação sobre Latência" in html
    assert "Informação sobre Tokens Totais" in html
    assert "Custo Estimado" not in html
    assert "(taxa_alucinacao)" not in html
    assert "(fidelidade_factual_rnf03)" not in html
    assert "(precisao_geoespacial_ra)" not in html
    assert "(fontes_utilizadas)" not in html
    assert "100% (1.00)" not in html
    assert "0% (0.00)" not in html
    assert "#0C0A14" in html
    assert "#FF2E9A" in html
    assert "#00E5FF" in html
    assert "#C6FF00" in html
    assert "taxa_alucinacao" in html
    assert "fidelidade_factual_rnf03" in html
    assert "precisao_geoespacial_ra" in html
    assert "[FONTE #1]" in html
    assert "[FONTE #2]" in html
    assert "tiktok.com" in html
    assert "cloud.langfuse.com" in html


def test_navegacao_para_comparativo_na_home_e_rag():
    """Valida que a Landing Page (/) e a tela de RAG (/rag) possuem botão/link para /comparativo."""
    res_home = client.get("/", headers={"Accept": "text/html"})
    assert res_home.status_code == 200
    assert 'href="/comparativo"' in res_home.text

    res_rag = client.get("/rag")
    assert res_rag.status_code == 200
    assert 'href="/comparativo"' in res_rag.text


def test_contrato_json_api_comparativo_executar():
    """Valida que POST /api/comparativo/executar cumpre rigorosamente o Contrato JSON da Issue #37."""
    payload = {
        "id_golden": "golden_01",
        "pergunta": "Onde comer hambúrguer artesanal ou rodízio de mini hambúrgueres em Taguatinga com amigos?",
    }
    response = client.post("/api/comparativo/executar", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["id_golden"] == "golden_01"
    assert data["pergunta"] == payload["pergunta"]

    # Validação Modo A (LLM Pura)
    modo_a = data["modo_a_llm_pura"]
    assert isinstance(modo_a["resposta"], str) and len(modo_a["resposta"]) > 0
    assert modo_a["fontes_utilizadas"] == []
    assert "latencia_ms" in modo_a
    assert "tokens_total" in modo_a
    assert "custo_estimado_brl" in modo_a
    scores_a = modo_a["scores"]
    assert scores_a["fidelidade_factual_rnf03"] == 0.0
    assert scores_a["taxa_alucinacao"] == 1.0
    assert "precisao_geoespacial_ra" in scores_a
    assert "sla_latencia_rnf14" in scores_a

    # Validação Modo B (RAG Ancorado com no mínimo 2 alternativas)
    modo_b = data["modo_b_rag"]
    assert "[FONTE #1]" in modo_b["resposta"]
    assert "[FONTE #2]" in modo_b["resposta"]
    assert isinstance(modo_b["fontes_utilizadas"], list) and len(modo_b["fontes_utilizadas"]) >= 2
    fonte_1 = modo_b["fontes_utilizadas"][0]
    for campo in ("id", "nome", "ra", "custo_medio_rs", "score_similaridade", "url_tiktok"):
        assert campo in fonte_1
    assert "trace_url" in modo_b
    scores_b = modo_b["scores"]
    assert scores_b["fidelidade_factual_rnf03"] == 1.0
    assert scores_b["taxa_alucinacao"] == 0.0
    assert scores_b["precisao_geoespacial_ra"] == 1.0
    assert scores_b["sla_latencia_rnf14"] == 1.0

    # Valida que o link do Trace abre o Painel de Inspeção completo (HTTP 200) e não uma página vazia
    res_trace = client.get(modo_b["trace_url"])
    assert res_trace.status_code == 200
    assert "Langfuse Observability" in res_trace.text
    assert "pipeline_orquestrador_rag" in res_trace.text
    assert "recuperacao_vetorial_tiktok" in res_trace.text
    assert "sintese_resposta_llm" in res_trace.text
