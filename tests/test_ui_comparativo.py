"""
Testes automatizados da Interface Web de Comparação Lado a Lado: LLM Pura vs. RAG (/comparativo)
Referência: Issue #37 — [Semana 3] [FRONTEND] Interface Web de Comparação Lado a Lado: LLM Pura vs. RAG (/comparativo)
Responsável: Maria Carolina (@mcznh)
"""

import re
import shutil
import subprocess
import requests
from fastapi.testclient import TestClient

from src.main import app
from src.rag import llm_pura, llm_rag
from src.telemetria import logger_metricas as lm

client = TestClient(app)


class _RespostaFalsa:
    def __init__(self, status, corpo):
        self.status_code = status
        self._corpo = corpo

    def json(self):
        return self._corpo


class _OpenRouterFalsa:
    def post(self, url, json, timeout, headers):
        modo_b = json["messages"][0]["content"] == llm_rag.PROMPT_SISTEMA
        texto = (
            "Recomendo o local **[FONTE #1]** na região indicada."
            if modo_b
            else "Sugiro um restaurante qualquer <script>alert(1)</script>."
        )
        return _RespostaFalsa(
            200,
            {
                "model": json["model"],
                "provider": "ProvedorFalso",
                "choices": [{"message": {"content": texto}, "finish_reason": "stop"}],
                "usage": {
                    "prompt_tokens": 120,
                    "completion_tokens": 40,
                    "total_tokens": 160,
                    "cost": 0.0001,
                },
            },
        )


def test_rota_comparativo_retorna_200_e_estrutura_lado_a_lado():
    """Valida que GET /comparativo retorna HTTP 200 com layout limpo, sem dados fixos nem rótulos incorretos."""
    response = client.get("/comparativo")
    assert response.status_code == 200
    html = response.text

    # 1. Colunas Lado a Lado (Modo A vs Modo B)
    assert "Modo A — LLM Pura (Zero-Shot)" in html
    assert "Modo B — RAG Ancorado (Base 2FA)" in html

    # 2. Estado inicial vazio e scores marcados como não avaliado (aguardando issue #36)
    assert "não avaliado" in html
    assert "aguardando execução" in html
    assert "Burger House" not in html
    assert "Filomenamburger" not in html
    assert "Smash &amp; Co" not in html

    # 3. Informações técnicas fiéis aos ADRs (sem Google Maps/Instagram, ChromaDB ou Gemini 1.5)
    assert "base de 93 lugares do TikTok, auditada em 2 etapas" in html
    assert "Google Maps" not in html
    assert "ChromaDB" not in html
    assert "Gemini 1.5" not in html
    assert "/telemetria/trace" not in html

    # 4. Sem gradiente no texto dos títulos
    assert "-webkit-text-fill-color" not in html

    # 5. Seletor dinâmico do Golden Dataset, input livre, paleta Analytics Executive Dashboard e proteção XSS
    assert 'id="goldenSelect"' in html
    assert 'id="perguntaComparativoInput"' in html
    assert 'id="themeToggleBtn"' in html
    assert "body.dark-mode" in html
    assert "#FAFAFA" in html
    assert "#132E31" in html
    assert "#337A89" in html
    assert "#7DC5CF" in html
    assert "#E9F7F7" in html
    assert "#E5E7EB" in html
    assert "0 10px 30px rgba(0, 0, 0, 0.05)" in html
    assert "DM Sans" in html
    assert 'class="sidebar"' in html
    assert 'class="kpi-grid"' in html
    assert 'class="chart-card"' in html
    assert "/api/comparativo/golden" in html
    assert "/api/comparativo/executar" in html
    assert "escaparHtml" in html
    assert "formatarRespostaSegura" in html
    assert "preço não informado" in html
    assert "texto-fixo-sem-llm" in html


def test_navegacao_para_comparativo_na_home_e_rag_e_trace_removido():
    """Valida que / mantém a LANDING_PAGE com link para /comparativo, /rag aponta para /comparativo e /telemetria/trace não existe."""
    res_home = client.get("/", headers={"Accept": "text/html"})
    assert res_home.status_code == 200
    assert "Orquestrador de Rolês" in res_home.text
    assert 'href="/comparativo"' in res_home.text

    res_rag = client.get("/rag")
    assert res_rag.status_code == 200
    assert 'href="/comparativo"' in res_rag.text

    res_trace = client.get("/telemetria/trace")
    assert res_trace.status_code == 404


def test_integracao_comparativo_com_rotas_reais_e_escape_xss(monkeypatch, tmp_path):
    """Valida consumo das rotas reais da #34 (golden + executar) e escape de <script> na interface."""
    monkeypatch.setattr(lm, "ARQUIVO_CACHE_PADRAO", tmp_path / "cache.json")
    monkeypatch.setattr(lm, "ARQUIVO_METRICAS_PADRAO", tmp_path / "metricas.jsonl")
    lm._MEMORIA_CACHE.clear()
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
    monkeypatch.setattr(llm_pura, "segredo", lambda nome: "chave-de-teste")
    monkeypatch.setattr(requests, "Session", lambda: _OpenRouterFalsa())

    res_golden = client.get("/api/comparativo/golden")
    assert res_golden.status_code == 200
    assert res_golden.json()["total"] >= 10

    res_exec = client.post("/api/comparativo/executar", json={"id_golden": "golden_02"})
    assert res_exec.status_code == 200
    data = res_exec.json()
    assert data["gabarito"]["locais_gabarito"] == ["Restaurante Dona Cleide"]
    assert data["modo_b_rag"]["trace_url"] is None
    assert "<script>alert(1)</script>" in data["modo_a_llm_pura"]["resposta"]

    # Valida que a função JS formatarRespostaSegura escapa tags <script>
    html = client.get("/comparativo").text
    m = re.search(
        r"(function escaparHtml\(texto\).*?function formatarRespostaSegura\(texto, destacarFontes\).*?\n    \})",
        html,
        re.DOTALL,
    )
    assert m is not None
    if shutil.which("node"):
        script_js = (
            m.group(1)
            + '\nconsole.log(formatarRespostaSegura("Teste **ok** <script>alert(1)</script> [FONTE #1]", true));'
        )
        out = subprocess.check_output(["node", "-e", script_js], text=True).strip()
        assert "<script>" not in out
        assert "&lt;script&gt;alert(1)&lt;/script&gt;" in out
        assert "<strong>ok</strong>" in out
        assert '<span class="fonte-cite">[FONTE #1]</span>' in out
