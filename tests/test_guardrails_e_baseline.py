"""Issue #33: contrato da LLM pura (Modo A) e guardrails determinísticos do RAG (Modo B). Sem rede e sem chave.

    PYTHONPATH=. pytest -v tests/test_guardrails_e_baseline.py
"""
from decimal import Decimal

import pytest

from src.rag import guardrails as gr
from src.rag import llm_pura
from src.rag.llm_pura import gerar_resposta_llm_pura
from src.telemetria.telemetria import carregar_base_oficial_leticia, simular_recuperacao_rag

CAMPOS_MODO_A = {"resposta", "modelo", "modo", "fontes_utilizadas", "latencia_ms", "tokens_total",
                 "custo_estimado_brl", "disponivel"}


# ---------- 1. contrato da LLM pura (Modo A)

class _Resposta:
    def __init__(self, status, corpo):
        self.status_code, self._corpo = status, corpo

    def json(self):
        return self._corpo


class SessaoFalsa:
    """Imita a OpenRouter e guarda o corpo enviado."""

    def __init__(self, status=200, texto="Sugiro o Bar Inventado, na Asa Sul, por cerca de R$ 40."):
        self.status, self.texto, self.enviado = status, texto, None

    def post(self, url, json, timeout, headers):
        self.enviado = json
        return _Resposta(self.status, {
            "model": json["model"], "provider": "ProvedorFalso",
            "choices": [{"message": {"content": self.texto}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 150, "completion_tokens": 50, "total_tokens": 200, "cost": 0.0001},
        })


@pytest.fixture
def com_chave(monkeypatch):
    monkeypatch.setattr(llm_pura, "segredo", lambda nome: "chave-de-teste")


def test_contrato_da_llm_pura_sem_fontes(com_chave):
    sessao = SessaoFalsa()
    r = gerar_resposta_llm_pura("Onde comer hambúrguer em Taguatinga?", usar_cache=False, registrar=False,
                                sessao=sessao)
    assert CAMPOS_MODO_A <= set(r)
    assert r["fontes_utilizadas"] == [] and r["modo"] == "modo_a_llm_pura" and r["disponivel"] is True
    assert r["modelo"] == "deepseek/deepseek-v4.1-flash-1017"
    assert r["tokens_total"] == 200 and r["custo_estimado_brl"] == pytest.approx(0.0001 * 5.80)
    assert r["resposta"].startswith("Sugiro")


def test_llm_pura_nao_recebe_nada_da_base_e_usa_roteamento_sem_retencao(com_chave):
    sessao = SessaoFalsa()
    gerar_resposta_llm_pura("Onde tem rodízio de caldos em Águas Claras?", usar_cache=False, registrar=False,
                            sessao=sessao)
    corpo = sessao.enviado
    assert [m["role"] for m in corpo["messages"]] == ["system", "user"]  # zero-shot: sem chunks da base
    texto = " ".join(m["content"] for m in corpo["messages"])
    nomes_da_base = [x["nome"] for x in carregar_base_oficial_leticia()]
    assert not any(nome in texto for nome in nomes_da_base) and "FONTE" not in texto
    assert corpo["provider"]["zdr"] is True and corpo["provider"]["data_collection"] == "deny"
    assert corpo["reasoning"] == {"enabled": False} and corpo["temperature"] == 0


def test_llm_pura_sem_chave_devolve_reserva_deterministica(monkeypatch):
    monkeypatch.setattr(llm_pura, "segredo", lambda nome: None)
    r = gerar_resposta_llm_pura("Onde jantar na Asa Norte?", usar_cache=False, registrar=False)
    assert r["disponivel"] is False and r["fontes_utilizadas"] == [] and "OPENROUTER_API_KEY" in r["erro"]
    assert CAMPOS_MODO_A <= set(r)


def test_llm_pura_com_api_fora_do_ar_nao_quebra(com_chave):
    r = gerar_resposta_llm_pura("Onde jantar na Asa Norte?", usar_cache=False, registrar=False,
                                sessao=SessaoFalsa(status=503))
    assert r["disponivel"] is False and "HTTP 503" in r["erro"]


# ---------- 2. guardrail 1: fora do DF e similaridade baixa

@pytest.mark.parametrize("pergunta", ["Onde jantar em Copacabana?", "Bares em Pinheiros, São Paulo",
                                      "Restaurante bom no Rio de Janeiro", "Tem bar em Valparaíso?"])
def test_bloqueia_pergunta_fora_do_df(pergunta):
    r = simular_recuperacao_rag(pergunta, top_k=3)
    assert r["resultados"] == [] and r["guardrails"]["motivo"] == "fora_do_df"
    assert "Distrito Federal" in r["resposta_ia"]


@pytest.mark.parametrize("pergunta", ["Estou em Goiânia, onde comer em Taguatinga?", "rolê em Planaltina",
                                      "date calmo na Asa Sul"])
def test_nao_bloqueia_pergunta_do_df(pergunta):
    assert gr.avaliar_pergunta(pergunta).permitido


def test_bloqueia_quando_nada_atinge_o_limiar():
    r = simular_recuperacao_rag("oficina mecânica perto de mim", top_k=3)
    assert r["resultados"] == [] and r["guardrails"]["motivo"] == "similaridade_baixa"
    assert r["guardrails"]["score_maximo"] < gr.LIMIAR_SIMILARIDADE


def test_pergunta_boa_continua_recomendando():
    r = simular_recuperacao_rag("date calmo na Asa Sul", top_k=2)
    assert len(r["resultados"]) == 2 and r["guardrails"]["permitido"] is True
    assert r["resultados"][0]["score_similaridade"] >= gr.LIMIAR_SIMILARIDADE


# ---------- 3. guardrail 2: teto em reais (RNF-04)

@pytest.mark.parametrize("pergunta, teto, gratis", [
    ("sushi barato até 30 reais na Asa Norte", Decimal("30"), False),
    ("no máximo R$ 45,50 por pessoa", Decimal("45.50"), False),
    ("gastando até cinquenta reais", Decimal("50"), False),
    ("com 50 conto", Decimal("50"), False),
    ("programa gratuito no domingo", Decimal("0"), True),
    ("bar aberto até as 22h", None, False),
    ("mesa para até 5 pessoas", None, False),
    ("um bar de R$ 50", None, False),
])
def test_extrai_teto(pergunta, teto, gratis):
    assert gr.extrair_teto(pergunta) == (teto, gratis)


def test_filtro_de_teto_e_duro():
    r = simular_recuperacao_rag("sushi barato até 30 reais na Asa Norte", top_k=5)
    assert r["resultados"] and all(x["custo_medio_rs"] <= 30 for x in r["resultados"])
    assert r["guardrails"]["teto"] == 30.0 and r["guardrails"]["filtrados_por_teto"] > 0


def test_conflito_luxo_gratis():
    r = simular_recuperacao_rag("restaurante de luxo grátis", top_k=3)
    g = r["guardrails"]
    assert g["conflito"] and g["gratis"] and g["motivo"] == "sem_lugar_no_teto" and r["resultados"] == []
    assert "incompatível" in r["resposta_ia"] and "Nenhum lugar da base é grátis" in r["resposta_ia"]


def test_conflito_com_teto_baixo_mantem_o_filtro():
    r = simular_recuperacao_rag("jantar sofisticado até 40 reais", top_k=3)
    assert r["guardrails"]["conflito"] and all(x["custo_medio_rs"] <= 40 for x in r["resultados"])


def test_filtrar_por_teto_puro():
    lugares = [{"nome": "a", "custo_medio_rs": 20}, {"nome": "b", "custo_medio_rs": 31}, {"nome": "c"}]
    assert [x["nome"] for x in gr.filtrar_por_teto(lugares, Decimal("30"))] == ["a"]
    assert len(gr.filtrar_por_teto(lugares, None)) == 3
