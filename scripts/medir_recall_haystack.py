"""Mede o recall@3 do retriever BM25 do pipeline Haystack nos casos do golden dataset que têm lugar no gabarito.

Uso: PYTHONPATH=. python scripts/medir_recall_haystack.py
Sem LLM e sem rede: só a recuperação (documentos de `carregar_documentos_base`).
"""
from __future__ import annotations

import json
import sys

from src.rag.comparador_ab import carregar_golden
from src.rag.pipeline_haystack import obter_pipeline_haystack

TOP_K = 3


def medir() -> dict:
    retriever = obter_pipeline_haystack().get_component("retriever")
    casos = [c for c in carregar_golden() if c.get("locais_gabarito")]
    detalhes = []
    for c in casos:
        docs = retriever.run(query=c["pergunta"], top_k=TOP_K)["documents"]
        nomes = [d.meta["nome"] for d in docs]
        detalhes.append({"id": c["id"], "gabarito": c["locais_gabarito"], "recuperados": nomes,
                         "acertou": any(g in nomes for g in c["locais_gabarito"])})
    acertos = sum(d["acertou"] for d in detalhes)
    return {"top_k": TOP_K, "casos": len(detalhes), "acertos": acertos,
            "recall_at_k": round(acertos / len(detalhes), 4) if detalhes else None, "detalhes": detalhes}


if __name__ == "__main__":
    r = medir()
    json.dump(r, sys.stdout, ensure_ascii=False, indent=2)
    print(f"\nrecall@{TOP_K}: {r['acertos']}/{r['casos']}", file=sys.stderr)
