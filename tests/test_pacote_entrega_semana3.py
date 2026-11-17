"""Pacote do entregável da Semana 3 (issue #40): os arquivos existem, não estão vazios e o ZIP está completo."""
import zipfile
from pathlib import Path

import pytest

from scripts.gerar_pacote_semana3 import ARQUIVOS, ZIP

PASTA = Path(__file__).resolve().parents[1] / "docs" / "entregas" / "semana-03"


@pytest.mark.parametrize("nome", [
    "RELATORIO_TECNICO_SEMANA_03.pdf",
    "RELATORIO_TECNICO_SEMANA_03.md",
    "RELATORIO_TECNICO_SEMANA_03.tex",
    "BENCHMARK_LLM_VS_RAG_LOG.txt",
    ZIP.name,
])
def test_arquivo_do_entregavel_existe_e_nao_esta_vazio(nome):
    caminho = PASTA / nome
    assert caminho.is_file(), f"falta {caminho.name}"
    assert caminho.stat().st_size > 0, f"{caminho.name} está vazio"


def test_pdf_e_um_pdf_de_verdade():
    assert (PASTA / "RELATORIO_TECNICO_SEMANA_03.pdf").read_bytes()[:5] == b"%PDF-"


def test_zip_tem_todos_os_arquivos_do_pacote():
    with zipfile.ZipFile(ZIP) as pacote:
        assert pacote.testzip() is None
        assert sorted(pacote.namelist()) == sorted(destino for _, destino in ARQUIVOS)


def test_relatorio_markdown_traz_os_numeros_do_benchmark():
    """O texto cita a tabela oficial; se o benchmark for refeito, o relatório precisa ser atualizado junto."""
    import json

    raiz = Path(__file__).resolve().parents[1]
    dados = json.loads((raiz / "data" / "resultados_benchmark_semana3.json").read_text(encoding="utf-8"))
    acertos = {
        cid: sum(c["resultados_configuracoes"][cid]["scores"].get("acerto_gabarito") == 1.0 for c in dados)
        for cid in dados[0]["resultados_configuracoes"]
    }
    assert acertos["1_llm_pura_sem_raciocinio"] == 2
    assert acertos["4_rag_llm_busca_lexica"] == 12
    assert acertos["6_rag_llm_busca_vetorial"] == 18
    texto = (PASTA / "RELATORIO_TECNICO_SEMANA_03.md").read_text(encoding="utf-8")
    for trecho in ("0 de 18", "10 de 18", "16 de 18", "12 de 20", "18 de 20"):
        assert trecho in texto
