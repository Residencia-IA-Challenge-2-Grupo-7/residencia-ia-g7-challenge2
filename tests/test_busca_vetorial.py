"""Testes da busca vetorial e híbrida do Modo B (embeddings gemini-embedding-001 pela OpenRouter). Sem rede."""
import json
from pathlib import Path

import numpy as np
import pytest
import requests
from fastapi.testclient import TestClient

from src.main import app
from src.rag import busca_vetorial, guardrails as gr, llm_pura
from src.telemetria import logger_metricas as lm
from src.telemetria.telemetria import fundir_rankings, recuperar_com_guardrails

RAIZ = Path(__file__).resolve().parent.parent
VETORES = {d["id"]: d for d in json.loads((RAIZ / "data" / "banco_vetorial_embeddings.json").read_text(encoding="utf-8"))}
DONA_CLEIDE = "tiktok_7612334793040186632"


class _Resposta:
    def __init__(self, status, corpo):
        self.status_code, self._corpo = status, corpo

    def json(self):
        return self._corpo


class EmbeddingsFalsos:
    """Imita /api/v1/embeddings devolvendo um vetor fixo e guarda o corpo enviado."""

    def __init__(self, vetor, status=200):
        self.vetor, self.status, self.corpos = list(vetor), status, []

    def post(self, url, timeout, headers, json):
        self.corpos.append(json)
        return _Resposta(self.status, {"data": [{"embedding": self.vetor}], "provider": "Google",
                                       "usage": {"prompt_tokens": 8, "cost": 1.2e-06}})


@pytest.fixture(autouse=True)
def isolar(monkeypatch, tmp_path):
    monkeypatch.setattr(lm, "ARQUIVO_CACHE_PADRAO", tmp_path / "cache.json")
    monkeypatch.setattr(lm, "ARQUIVO_METRICAS_PADRAO", tmp_path / "metricas.jsonl")
    lm._MEMORIA_CACHE.clear()
    busca_vetorial.limpar_cache()
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
    yield
    busca_vetorial.limpar_cache()


def _com_embedding(monkeypatch, vetor, status=200):
    falso = EmbeddingsFalsos(vetor, status)
    monkeypatch.setattr(busca_vetorial, "segredo", lambda nome: "chave-de-teste")
    monkeypatch.setattr(busca_vetorial, "requests", type("M", (), {"post": falso.post,
                                                                   "RequestException": requests.RequestException}))
    return falso


def test_fusao_por_posicao_premia_quem_vai_bem_nas_duas_ordens():
    assert fundir_rankings([["a", "b", "c"], ["b", "c", "a"]])[0] == "b"
    assert fundir_rankings([["a", "b"], ["a", "b"]]) == ["a", "b"]


def test_vetor_de_um_lugar_como_pergunta_traz_o_proprio_lugar_em_primeiro(monkeypatch):
    falso = _com_embedding(monkeypatch, VETORES[DONA_CLEIDE]["embedding_vector"])
    guard, lugares = recuperar_com_guardrails("rodízio de caldos com brinquedoteca", top_k=3, busca="vetorial")
    assert guard.busca == "vetorial" and guard.permitido
    assert lugares[0]["id"] == DONA_CLEIDE
    assert lugares[0]["score_similaridade"] == pytest.approx(1.0, abs=1e-3)
    assert "score_lexico" in lugares[0]
    corpo = falso.corpos[0]
    assert corpo["model"] == "google/gemini-embedding-001"
    assert corpo["provider"] == {"zdr": True, "data_collection": "deny"}  # sem retenção, como os LLMs


def test_hibrida_usa_as_duas_ordens_e_o_cosseno_no_guardrail(monkeypatch):
    _com_embedding(monkeypatch, VETORES[DONA_CLEIDE]["embedding_vector"])
    guard, lugares = recuperar_com_guardrails("rodízio de caldos com brinquedoteca em Águas Claras", busca="hibrida")
    assert guard.busca == "hibrida" and lugares[0]["id"] == DONA_CLEIDE
    assert guard.score_maximo == pytest.approx(1.0, abs=1e-3)


def test_pergunta_longe_de_todos_os_lugares_e_recusada_pelo_limiar_do_cosseno(monkeypatch):
    _, matriz = busca_vetorial.carregar_vetores()
    longe = -matriz.mean(axis=0)  # direção oposta à média da base: cosseno baixo com todos
    _com_embedding(monkeypatch, longe)
    guard, lugares = recuperar_com_guardrails("bar no DF", busca="vetorial")
    assert guard.busca == "vetorial" and not guard.permitido
    assert guard.motivo == "similaridade_baixa" and lugares == []
    assert guard.score_maximo < gr.LIMIAR_COSSENO


def test_sem_chave_a_busca_volta_para_a_lexica_e_diz_por_que(monkeypatch):
    monkeypatch.setattr(busca_vetorial, "segredo", lambda nome: None)
    guard, lugares = recuperar_com_guardrails("rodízio de caldos com brinquedoteca em Águas Claras", busca="vetorial")
    assert guard.busca == "lexica" and "OPENROUTER_API_KEY" in guard.busca_erro
    assert lugares and "score_lexico" not in lugares[0]


def test_api_fora_do_ar_tambem_volta_para_a_lexica(monkeypatch):
    _com_embedding(monkeypatch, [0.0] * 3072, status=503)
    guard, _ = recuperar_com_guardrails("rodízio de caldos em Águas Claras", busca="vetorial")
    assert guard.busca == "lexica" and "HTTP 503" in guard.busca_erro


def test_pergunta_fora_do_df_e_barrada_antes_do_embedding(monkeypatch):
    falso = _com_embedding(monkeypatch, VETORES[DONA_CLEIDE]["embedding_vector"])
    guard, lugares = recuperar_com_guardrails("bares em Copacabana", busca="vetorial")
    assert not guard.permitido and guard.motivo == "fora_do_df" and lugares == []
    assert falso.corpos == []  # nem chega a gastar o embedding


def test_busca_invalida():
    with pytest.raises(ValueError):
        recuperar_com_guardrails("bar", busca="semantica")


def test_rota_aceita_busca_e_raciocinio_e_recusa_valores_fora_da_lista(monkeypatch):
    monkeypatch.setattr(llm_pura, "segredo", lambda nome: None)  # sem LLM: os modos saem como indisponíveis
    _com_embedding(monkeypatch, VETORES[DONA_CLEIDE]["embedding_vector"])
    cliente = TestClient(app)
    r = cliente.post("/api/comparativo/executar", json={"id_golden": "golden_02", "busca": "vetorial",
                                                         "raciocinio": "high"})
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["configuracao"] == {"raciocinio": "high", "busca": "vetorial"}
    assert corpo["modo_b_rag"]["busca"] == "vetorial"
    assert corpo["modo_b_rag"]["fontes_utilizadas"][0]["id"] == DONA_CLEIDE
    for invalido in ({"id_golden": "golden_02", "busca": "semantica"}, {"id_golden": "golden_02", "raciocinio": "max"}):
        assert cliente.post("/api/comparativo/executar", json=invalido).status_code == 422


def test_tela_tem_os_seletores_de_raciocinio_e_busca():
    html = TestClient(app).get("/comparativo").text
    assert 'id="raciocinioSelect"' in html and 'id="buscaSelect"' in html
    assert "corpoReq.busca" in html and "corpoReq.raciocinio" in html
