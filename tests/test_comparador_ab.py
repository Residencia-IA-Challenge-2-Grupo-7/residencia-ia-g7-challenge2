"""Testes do motor da comparação A/B e das rotas /api/comparativo (issue #34). Sem rede: a OpenRouter é imitada."""
import json
from pathlib import Path

import pytest
import requests
from fastapi.testclient import TestClient

from src.main import app
from src.rag import comparador_ab, llm_pura, llm_rag
from src.telemetria import logger_metricas as lm

RAIZ = Path(__file__).resolve().parent.parent
IDS_BASE = {r["id"] for r in json.loads((RAIZ / "data" / "banco_aprovado_2fa.json").read_text(encoding="utf-8"))}
CAMPOS_TOPO = {"id_golden", "pergunta", "gabarito", "modo_a_llm_pura", "modo_b_rag"}
CAMPOS_MODO = {"resposta", "fontes_utilizadas", "latencia_ms", "tokens_total", "custo_estimado_brl"}
CAMPOS_FONTE = {"id", "nome", "ra", "custo_medio_rs", "score_similaridade", "url_tiktok"}
CAMPOS_GABARITO = {"ra_esperada", "locais_gabarito", "preco_maximo_gabarito"}


class _Resposta:
    def __init__(self, status, corpo):
        self.status_code, self._corpo = status, corpo

    def json(self):
        return self._corpo


class OpenRouterFalsa:
    """Imita a OpenRouter: responde conforme o prompt de sistema (Modo A ou Modo B) e guarda o que recebeu."""

    def __init__(self):
        self.chamadas = []

    def post(self, url, json, timeout, headers):
        self.chamadas.append(json)
        modo_b = json["messages"][0]["content"] == llm_rag.PROMPT_SISTEMA
        texto = ("Recomendo o lugar da [FONTE #1], na região indicada no documento." if modo_b
                 else "Sugiro o Bar Inventado, na Asa Sul, por cerca de R$ 40.")
        return _Resposta(200, {
            "model": json["model"], "provider": "ProvedorFalso",
            "choices": [{"message": {"content": texto}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 150, "completion_tokens": 50, "total_tokens": 200, "cost": 0.0001},
        })

    def de_modo(self, prompt):
        return [c for c in self.chamadas if c["messages"][0]["content"] == prompt]


@pytest.fixture(autouse=True)
def telemetria_isolada(monkeypatch, tmp_path):
    """Cache e métricas num diretório temporário, sem Langfuse: os testes não sujam data/telemetria/."""
    monkeypatch.setattr(lm, "ARQUIVO_CACHE_PADRAO", tmp_path / "cache.json")
    monkeypatch.setattr(lm, "ARQUIVO_METRICAS_PADRAO", tmp_path / "metricas.jsonl")
    lm._MEMORIA_CACHE.clear()
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
    yield
    lm._MEMORIA_CACHE.clear()


@pytest.fixture
def openrouter(monkeypatch):
    falsa = OpenRouterFalsa()
    monkeypatch.setattr(llm_pura, "segredo", lambda nome: "chave-de-teste")
    monkeypatch.setattr(requests, "Session", lambda: falsa)
    return falsa


@pytest.fixture
def sem_chave(monkeypatch):
    monkeypatch.setattr(llm_pura, "segredo", lambda nome: None)


@pytest.fixture
def cliente():
    return TestClient(app)


def _confere_contrato(corpo):
    assert CAMPOS_TOPO <= set(corpo)
    for modo in ("modo_a_llm_pura", "modo_b_rag"):
        assert CAMPOS_MODO <= set(corpo[modo]), modo
        assert isinstance(corpo[modo]["resposta"], str) and corpo[modo]["resposta"]
        assert corpo[modo]["latencia_ms"] >= 0 and corpo[modo]["tokens_total"] >= 0
    assert "trace_url" in corpo["modo_b_rag"]
    assert corpo["modo_a_llm_pura"]["fontes_utilizadas"] == []
    for fonte in corpo["modo_b_rag"]["fontes_utilizadas"]:
        assert CAMPOS_FONTE <= set(fonte)
        assert fonte["id"] in IDS_BASE  # RNF-03: toda fonte do Modo B é da base de 93


# ---------------------------------------------------------------------------------------------------- GET golden


def test_golden_lista_as_perguntas_sem_o_gabarito(cliente):
    r = cliente.get("/api/comparativo/golden")
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["total"] == len(corpo["perguntas"]) >= 10
    for item in corpo["perguntas"]:
        assert set(item) == {"id", "pergunta", "categoria"}
        assert item["id"].startswith("golden_") and item["pergunta"]


def test_golden_ausente_devolve_lista_vazia(tmp_path):
    assert comparador_ab.listar_golden(tmp_path / "nao_existe.json") == []


# ------------------------------------------------------------------------------------------------ POST executar


def test_executar_caso_golden_devolve_o_contrato_e_o_gabarito(cliente, openrouter):
    r = cliente.post("/api/comparativo/executar", json={"id_golden": "golden_02"})
    assert r.status_code == 200
    corpo = r.json()
    _confere_contrato(corpo)
    assert corpo["id_golden"] == "golden_02"
    assert corpo["pergunta"].startswith("Onde tem rodízio de caldos")
    assert CAMPOS_GABARITO <= set(corpo["gabarito"])
    assert corpo["gabarito"]["locais_gabarito"] == ["Restaurante Dona Cleide"]

    b = corpo["modo_b_rag"]
    assert b["disponivel"] is True and b["guardrails"]["permitido"] is True
    assert 1 <= len(b["fontes_utilizadas"]) <= comparador_ab.TOP_K
    assert b["fontes_utilizadas"][0]["citada"] is True  # a resposta falsa cita a [FONTE #1]
    assert b["latencia_ms"] >= 0


def test_os_dois_modos_usam_o_mesmo_modelo_e_so_o_b_recebe_documentos(cliente, openrouter):
    corpo = cliente.post("/api/comparativo/executar", json={"id_golden": "golden_02"}).json()
    [a] = openrouter.de_modo(llm_pura.PROMPT_SISTEMA)
    [b] = openrouter.de_modo(llm_rag.PROMPT_SISTEMA)
    for chave in ("model", "temperature", "provider", "reasoning", "max_tokens"):
        assert a[chave] == b[chave], chave
    assert a["messages"][1]["content"] == corpo["pergunta"]  # Modo A: só a pergunta
    mensagem_b = b["messages"][1]["content"]
    assert "[FONTE #1]" in mensagem_b and corpo["pergunta"] in mensagem_b
    assert corpo["modo_b_rag"]["fontes_utilizadas"][0]["nome"] in mensagem_b


def test_pergunta_livre_sem_golden_tem_gabarito_nulo(cliente, openrouter):
    r = cliente.post("/api/comparativo/executar", json={"pergunta": "café calmo na Asa Norte"})
    assert r.status_code == 200
    corpo = r.json()
    _confere_contrato(corpo)
    assert corpo["id_golden"] is None and corpo["gabarito"] is None


def test_pergunta_fora_do_df_nao_chama_o_llm_no_modo_b(cliente, openrouter):
    corpo = cliente.post("/api/comparativo/executar", json={"id_golden": "golden_09"}).json()
    _confere_contrato(corpo)
    b = corpo["modo_b_rag"]
    assert b["fontes_utilizadas"] == [] and b["guardrails"]["permitido"] is False
    assert b["guardrails"]["motivo"] == "fora_do_df"
    assert b["tokens_total"] == 0 and b["custo_estimado_brl"] == 0.0
    assert openrouter.de_modo(llm_rag.PROMPT_SISTEMA) == []  # guardrail recusou antes do LLM
    assert len(openrouter.de_modo(llm_pura.PROMPT_SISTEMA)) == 1  # o Modo A responde mesmo assim


def test_sem_chave_os_dois_modos_ficam_marcados_como_indisponiveis(cliente, sem_chave):
    r = cliente.post("/api/comparativo/executar", json={"id_golden": "golden_01"})
    assert r.status_code == 200
    corpo = r.json()
    _confere_contrato(corpo)
    a, b = corpo["modo_a_llm_pura"], corpo["modo_b_rag"]
    assert a["disponivel"] is False and "OPENROUTER_API_KEY" in a["erro"]
    assert b["disponivel"] is False and b["modelo"] == llm_rag.MODELO_RESERVA  # texto fixo, não um LLM
    assert b["fontes_utilizadas"]  # a recuperação continua funcionando sem chave


def test_segunda_execucao_vem_do_cache_sem_nova_chamada(cliente, openrouter):
    cliente.post("/api/comparativo/executar", json={"id_golden": "golden_03"})
    chamadas = len(openrouter.chamadas)
    corpo = cliente.post("/api/comparativo/executar", json={"id_golden": "golden_03"}).json()
    assert len(openrouter.chamadas) == chamadas == 2
    assert corpo["modo_a_llm_pura"]["cache_hit"] is True and corpo["modo_b_rag"]["cache_hit"] is True


@pytest.mark.parametrize("corpo, status", [
    ({}, 422),                                                      # nem pergunta nem id
    ({"pergunta": "   "}, 422),                                     # pergunta em branco
    ({"id_golden": "golden_99"}, 404),                              # caso inexistente
    ({"id_golden": "golden_01", "pergunta": "outra pergunta"}, 422),  # gabarito não bate com a pergunta
    ({"pergunta": "x" * 501}, 422),                                 # pergunta longa demais
    ({"pergunta": "bar na Asa Sul", "top_k": 50}, 422),             # campo fora do contrato
])
def test_entradas_invalidas(cliente, sem_chave, corpo, status):
    assert cliente.post("/api/comparativo/executar", json=corpo).status_code == status


# ------------------------------------------------------------------------------------------- partes do Modo B


def test_raciocinio_ligado_vale_para_os_dois_modos(cliente, openrouter):
    corpo = comparador_ab.executar_comparacao_ab("", "golden_02", usar_cache=False, registrar=False,
                                                 raciocinio="high")
    for chamada in openrouter.chamadas:
        assert chamada["reasoning"] == {"effort": "high", "exclude": True}
        assert chamada["max_tokens"] == llm_pura.MAX_TOKENS_COM_RACIOCINIO
    assert len(openrouter.chamadas) == 2
    assert corpo["modo_a_llm_pura"]["raciocinio"] == corpo["modo_b_rag"]["raciocinio"] == "high"


def test_citacoes_em_grupo_tambem_contam():
    lugares = [{"id": f"x{n}", "nome": f"L{n}"} for n in range(1, 5)]
    fontes = llm_rag.formatar_fontes(lugares, "Ver [FONTE #1]. As outras [FONTES #2 e #3] ficam longe.")
    assert [f["citada"] for f in fontes] == [True, True, True, False]


def test_fonte_sem_custo_fica_nula_em_vez_de_inventar_um_valor():
    [fonte] = llm_rag.formatar_fontes([{"id": "x", "nome": "Lugar", "regiao_administrativa": "Guará"}])
    assert fonte["custo_medio_rs"] is None and fonte["citada"] is False


def test_documentos_do_modo_b_trazem_os_dados_da_base():
    lugar = {"nome": "Restaurante Dona Cleide", "regiao_administrativa": "Águas Claras", "endereco": "Av. das Araucárias",
             "horario_funcionamento": "Terça a domingo", "custo_medio_rs": "54.9"}
    doc = llm_rag.montar_documentos([lugar])
    assert doc.startswith("[FONTE #1]")
    for trecho in ("Restaurante Dona Cleide", "Águas Claras", "Av. das Araucárias", "Terça a domingo", "R$ 54,90"):
        assert trecho in doc
