from unittest.mock import MagicMock, patch
import pytest

from src.rag.pipeline_haystack import (
    carregar_documentos_base,
    criar_pipeline_haystack,
    executar_rag_haystack,
)


def test_carregar_documentos_base():
    docs = carregar_documentos_base()
    assert len(docs) == 93, f"Esperava 93 documentos carregados, obteve {len(docs)}"
    primeiro = docs[0]
    assert primeiro.content
    assert "nome" in primeiro.meta
    assert "regiao_administrativa" in primeiro.meta


def test_pipeline_haystack_offline():
    with patch("src.rag.pipeline_haystack.segredo", return_value=""):
        res = executar_rag_haystack("Onde comer pizza em Taguatinga?")
        assert res["framework"] == "Haystack 3.5.0"
        assert len(res["fontes_recuperadas"]) > 0
        assert "Offline" in res["resposta"] or "Fallback" in res["resposta"]


def test_pipeline_haystack_com_mock_openrouter():
    with patch("src.rag.pipeline_haystack.segredo", return_value="fake-key"), \
         patch("src.rag.llm_pura._chamar") as mock_chamar:
        mock_chamar.return_value = {
            "resposta": "Recomendo o Café do Lago [FONTE #1] no Parque da Cidade.",
            "modelo": "deepseek/deepseek-v4.1-flash-1017",
            "tokens_total": 45,
            "custo_estimado_brl": 0.001,
            "latencia_ms": 320.0,
            "disponivel": True,
        }
        res = executar_rag_haystack("café no parque")
        assert "Café do Lago" in res["resposta"]
        assert len(res["fontes_recuperadas"]) > 0
        assert res["metadados"]["tokens_total"] == 45


def test_documentos_usam_os_campos_reais_da_base():
    """Revisão PR #60 item 6: RA, descrição e preço precisam estar no conteúdo/metadados."""
    docs = {d.meta["nome"]: d for d in carregar_documentos_base()}
    d = docs["Restaurante Dona Cleide"]
    assert "Águas Claras" in d.content
    assert d.meta["custo_medio_rs"] is not None
    assert d.meta["preco_medio_texto"].startswith("R$")
    assert all(x.meta["preco_medio_texto"] != "R$ N/A" for x in docs.values())


def test_recall_at_3_do_haystack_no_golden():
    from scripts.medir_recall_haystack import medir

    r = medir()
    assert r["casos"] == 18
    assert r["acertos"] >= 14  # 14 de 18 (77,8%); era 2 de 18 com os campos errados
