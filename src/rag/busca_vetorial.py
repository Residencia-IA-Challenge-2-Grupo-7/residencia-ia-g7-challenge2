"""Busca vetorial na base de 93 lugares, com o mesmo modelo de embedding que gerou os vetores da base.

Os vetores de `data/banco_vetorial_embeddings.json` foram gerados com o `gemini-embedding-001` (3.072 dimensões,
semana 2). A pergunta é convertida em vetor pelo mesmo modelo, pela OpenRouter, com a mesma chave do resto do
projeto (`OPENROUTER_API_KEY`). Em 12/11, os vetores gerados de novo pela OpenRouter para 2 lugares da base
deram cosseno 1,0 com os guardados: o espaço é o mesmo.

    from src.rag.busca_vetorial import similaridades
    s = similaridades("rodízio de caldos com brinquedoteca em Águas Claras")   # {id do lugar: cosseno}

Com 93 lugares, a matriz cabe na memória (cerca de 1 MB em float32) e a busca é um produto de matrizes, sem
banco vetorial. Sem chave ou com a API fora do ar, `similaridades` devolve None, e quem chama volta para a busca
por palavras.
"""
from __future__ import annotations

import json
import os
import threading
import time
from functools import lru_cache
from pathlib import Path

import numpy as np
import requests

from src.interpretador.config import segredo

RAIZ = Path(__file__).resolve().parents[2]
CAMINHO_VETORES = RAIZ / "data" / "banco_vetorial_embeddings.json"
MODELO_PADRAO = "google/gemini-embedding-001"     # o mesmo que gerou os vetores da base
URL = "https://openrouter.ai/api/v1/embeddings"
CHAVE_ENV = "OPENROUTER_API_KEY"
# Sem retenção e sem coleta para treino, como no resto do projeto. O filtro de quantização do roteamento dos
# LLMs não vale para embeddings (a OpenRouter recusa a chamada com ele), por isso fica de fora aqui.
ROTEAMENTO = {"zdr": True, "data_collection": "deny"}
TIMEOUT_S = 15
TENTATIVAS = 2
MAXIMO_CACHE = 512

_cache: dict[str, np.ndarray] = {}
_trava = threading.Lock()


def _modelo() -> str:
    return os.environ.get("BUSCA_EMBEDDING_MODELO") or MODELO_PADRAO


@lru_cache(maxsize=1)
def carregar_vetores(caminho: str | None = None) -> tuple[tuple[str, ...], np.ndarray]:
    """Ids dos lugares e a matriz de vetores normalizados (uma linha por lugar)."""
    dados = json.loads(Path(caminho or CAMINHO_VETORES).read_text(encoding="utf-8"))
    ids = tuple(d["id"] for d in dados)
    matriz = np.array([d["embedding_vector"] for d in dados], dtype=np.float32)
    matriz /= np.linalg.norm(matriz, axis=1, keepdims=True)
    return ids, matriz


def _normalizar(texto: str) -> str:
    return " ".join((texto or "").lower().split())


def vetor_da_pergunta(pergunta: str, sessao=None) -> tuple[np.ndarray | None, dict]:
    """Vetor normalizado da pergunta e metadados da chamada (latência, custo, erro). None se não houver chave
    ou se a API falhar. Perguntas repetidas vêm de um cache em memória (não vão de novo à API)."""
    chave_cache = _normalizar(pergunta)
    with _trava:
        if chave_cache in _cache:
            return _cache[chave_cache], {"latencia_ms": 0.0, "custo_usd": 0.0, "cache_hit": True, "erro": None}
    chave = segredo(CHAVE_ENV)
    if not chave:
        return None, {"latencia_ms": 0.0, "custo_usd": 0.0, "cache_hit": False, "erro": f"sem {CHAVE_ENV}"}
    sessao = sessao or requests
    erros = []
    for _ in range(TENTATIVAS):
        t0 = time.perf_counter()
        try:
            r = sessao.post(URL, timeout=TIMEOUT_S, headers={"Authorization": f"Bearer {chave}"},
                            json={"model": _modelo(), "input": pergunta, "provider": ROTEAMENTO})
            ms = round((time.perf_counter() - t0) * 1000, 1)
            if r.status_code >= 400:
                erros.append(f"HTTP {r.status_code}")
                if r.status_code in (400, 401, 402, 403, 404):
                    break
                continue
            d = r.json()
            vetor = np.array(d["data"][0]["embedding"], dtype=np.float32)
            vetor /= np.linalg.norm(vetor)
            with _trava:
                if len(_cache) >= MAXIMO_CACHE:
                    _cache.pop(next(iter(_cache)))
                _cache[chave_cache] = vetor
            custo = float((d.get("usage") or {}).get("cost") or 0.0)
            return vetor, {"latencia_ms": ms, "custo_usd": custo, "cache_hit": False, "erro": None}
        except (requests.RequestException, ValueError, KeyError, IndexError, TypeError) as e:
            erros.append(type(e).__name__)
    return None, {"latencia_ms": 0.0, "custo_usd": 0.0, "cache_hit": False,
                  "erro": "falha nos embeddings: " + "; ".join(erros[-2:])}


def similaridades(pergunta: str, sessao=None) -> tuple[dict[str, float] | None, dict]:
    """Cosseno entre a pergunta e cada lugar da base ({id: cosseno}), e os metadados da chamada."""
    vetor, meta = vetor_da_pergunta(pergunta, sessao)
    if vetor is None:
        return None, meta
    ids, matriz = carregar_vetores()
    if matriz.shape[1] != vetor.shape[0]:
        return None, {**meta, "erro": f"dimensão {vetor.shape[0]} diferente da base ({matriz.shape[1]})"}
    cos = matriz @ vetor
    return {i: round(float(c), 4) for i, c in zip(ids, cos)}, meta


def limpar_cache() -> None:
    with _trava:
        _cache.clear()
