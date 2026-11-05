"""Etapa 8: embeddings das fichas, só quando o texto mudou (ADR 0005, Modelo de embeddings).

Modelo aberto rodando localmente: nenhum texto sai da máquina. O modelo fica na configuração (RNF-12).
"""
import hashlib
import json

import numpy as np

from .config import CFG, PROC

PASTA = PROC / "vetores"
_CARREGADOS = {}


def _slug(modelo: str) -> str:
    return modelo.replace("/", "__")


def carregar(modelo: str):
    if modelo not in _CARREGADOS:
        from sentence_transformers import SentenceTransformer
        _CARREGADOS[modelo] = SentenceTransformer(modelo, device="cpu")
    return _CARREGADOS[modelo]


def _prefixo(modelo: str, papel: str) -> str:
    # A família e5 foi treinada com prefixos; o BGE-M3 não usa.
    return f"{papel}: " if "e5" in modelo.lower() else ""


def embutir(textos: list[str], modelo: str, papel: str = "passage") -> np.ndarray:
    m = carregar(modelo)
    return m.encode([_prefixo(modelo, papel) + t for t in textos], batch_size=16,
                    normalize_embeddings=True, show_progress_bar=False)


def _hash(t: str) -> str:
    return hashlib.sha256(t.encode()).hexdigest()[:16]


def executar(modelo: str | None = None):
    modelo = modelo or CFG["embeddings"]["modelo"]
    fichas = json.loads((PROC / "fichas.json").read_text(encoding="utf-8"))
    PASTA.mkdir(parents=True, exist_ok=True)
    arq = PASTA / f"{_slug(modelo)}.npz"
    antigo = {}
    if arq.exists():
        z = np.load(arq, allow_pickle=False)
        antigo = {(c, d): (h, v) for c, d, h, v in zip(z["colecao"], z["doc_id"], z["hash"], z["vetor"])}
    docs = [(col, d.get("id") or d["ra"], d["ficha"]) for col in ("lugares", "eventos", "regioes")
            for d in fichas[col]]
    novos = [(c, i, t) for c, i, t in docs if antigo.get((c, i), ("",))[0] != _hash(t)]
    vet_novos = embutir([t for _, _, t in novos], modelo) if novos else np.zeros((0, CFG["embeddings"]["dimensao"]))
    mapa = {(c, i): v for (c, i, _), v in zip(novos, vet_novos)}
    linhas = [(c, i, _hash(t), mapa[(c, i)] if (c, i) in mapa else antigo[(c, i)][1]) for c, i, t in docs]
    np.savez(arq, colecao=np.array([l[0] for l in linhas]), doc_id=np.array([l[1] for l in linhas]),
             hash=np.array([l[2] for l in linhas]), vetor=np.stack([l[3] for l in linhas]).astype(np.float32),
             modelo=np.array(modelo))
    return {"modelo": modelo, "documentos": len(docs), "vetorizados_agora": len(novos),
            "dimensao": int(linhas[0][3].shape[0]) if linhas else 0}
