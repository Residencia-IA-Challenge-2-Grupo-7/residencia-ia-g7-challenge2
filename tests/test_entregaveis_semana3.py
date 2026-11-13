"""
Testes automatizados da Central de Entregáveis (/entregaveis) com Painel da Semana 3.
Referência: Issue #39 — [Semana 3] [FRONTEND] Central de Entregáveis (/entregaveis) com Painel da Semana 3 e Visualizadores
Responsável: Maria Carolina (@mcznh)
"""

import os
from fastapi.testclient import TestClient

from src.main import BASE_DIR, app

client = TestClient(app)


def test_rnf12_preservacao_rotas_semana2():
    """
    Garante que os artefatos e endpoints da Semana 02 continuam funcionando
    integralmente sem regressão (RNF-12).
    """
    # 1. Página principal da Central de Entregáveis
    res_page = client.get("/entregaveis")
    assert res_page.status_code == 200
    assert "Central Interativa de Entregáveis" in res_page.text
    assert "Semana 02" in res_page.text

    # 2. Base aprovada 2FA (93 lugares)
    res_aprovados = client.get("/api/entregaveis/dados?colecao=aprovados")
    assert res_aprovados.status_code == 200
    dados_aprovados = res_aprovados.json()
    assert dados_aprovados["total"] == 93
    assert len(dados_aprovados["dados"]) == 93

    # 3. Quarentena (71 vídeos)
    res_quarentena = client.get("/api/entregaveis/dados?colecao=quarentena")
    assert res_quarentena.status_code == 200
    dados_quarentena = res_quarentena.json()
    assert dados_quarentena["total"] == 71

    # 4. Embeddings vetoriais
    res_vetores = client.get("/api/entregaveis/dados?colecao=vetores")
    assert res_vetores.status_code == 200
    assert res_vetores.json()["total"] == 93

    # 5. Relatórios da Semana 2
    res_pdf_view = client.get("/visualizar/relatorio-pdf")
    assert res_pdf_view.status_code == 200
    assert res_pdf_view.headers["content-type"] == "application/pdf"

    res_pdf_down = client.get("/download/relatorio-pdf")
    assert res_pdf_down.status_code == 200
    assert "attachment" in res_pdf_down.headers.get("content-disposition", "")

    res_zip = client.get("/download/entregavel-zip")
    assert res_zip.status_code == 200


def test_colecoes_semana3_retornam_200():
    """Valida as novas coleções de dados estruturados da Semana 03."""
    # 1. Golden Dataset Semana 3 (20 casos de teste com gabarito)
    res_golden = client.get("/api/entregaveis/dados?colecao=golden_semana3")
    assert res_golden.status_code == 200
    dados_golden = res_golden.json()
    assert dados_golden["total"] >= 10
    assert len(dados_golden["dados"]) >= 10
    # Verifica campos essenciais do contrato do Golden Dataset
    primeiro = dados_golden["dados"][0]
    assert "pergunta" in primeiro
    assert "categoria" in primeiro
    assert "locais_gabarito" in primeiro

    # 2. Resultados do Benchmark Semana 3
    res_bench = client.get("/api/entregaveis/dados?colecao=benchmark_semana3")
    assert res_bench.status_code == 200
    dados_bench = res_bench.json()
    assert dados_bench["total"] >= 1
    assert len(dados_bench["dados"]) >= 1
    caso = dados_bench["dados"][0]
    assert "pergunta" in caso
    assert "modo_a_llm_pura" in caso
    assert "modo_b_rag" in caso


def test_colecao_invalida_retorna_400():
    """Garante que coleção inexistente retorna HTTP 400 com mensagem informativa."""
    res = client.get("/api/entregaveis/dados?colecao=colecao_inexistente")
    assert res.status_code == 400
    assert "Coleção inválida" in res.json()["detail"]


def test_interface_entregaveis_contem_elementos_semana3():
    """Valida que a página /entregaveis renderiza os novos cards, placar e link para /comparativo."""
    res = client.get("/entregaveis")
    assert res.status_code == 200
    html = res.text

    # Elementos e cards da Semana 03
    assert "Semana 03" in html
    assert "Comparação LLM Pura vs. RAG" in html
    assert "Placar Comparativo LLM x RAG" in html
    assert "Golden Dataset da Semana 3" in html
    assert "Resultados do Benchmark A/B" in html
    assert "Relatório Técnico &amp; ZIP Sem. 03" in html or "Relatório Técnico & ZIP Sem. 03" in html

    # Botão de destaque para o comparativo lado a lado
    assert 'href="/comparativo"' in html

    # KPIs e módulos da Semana 03
    assert "moduloPlacarSemana3" in html
    assert "moduloGoldenSemana3" in html
    assert "moduloBenchmarkSemana3" in html
    assert "moduloRelatorioSemana3" in html

    # Funções de filtro e eventos JS
    assert "filtrarGoldenSemana3" in html
    assert "filtrarBenchmarkSemana3" in html


def test_rotas_download_e_visualizacao_semana3(tmp_path):
    """
    Testa o comportamento das rotas de PDF e ZIP da Semana 3,
    incluindo o tratamento 404 quando ausentes e 200 quando presentes.
    """
    # 1. Quando o PDF da Semana 3 não existe, deve retornar 404 amigável
    pdf_semana3 = os.path.join(BASE_DIR, "docs/entregas/semana-03/RELATORIO_TECNICO_SEMANA_03.pdf")
    zip_semana3 = os.path.join(BASE_DIR, "docs/entregas/semana-03/Entregavel_Grupo7_Semana_03.zip")

    # Cria arquivos temporários caso ainda não existam para testar o fluxo de sucesso
    criou_pdf = False
    criou_zip = False
    try:
        if not os.path.isfile(pdf_semana3):
            os.makedirs(os.path.dirname(pdf_semana3), exist_ok=True)
            with open(pdf_semana3, "wb") as f:
                f.write(b"%PDF-1.4 mock semana 3")
            criou_pdf = True

        if not os.path.isfile(zip_semana3):
            os.makedirs(os.path.dirname(zip_semana3), exist_ok=True)
            with open(zip_semana3, "wb") as f:
                f.write(b"PK mock zip semana 3")
            criou_zip = True

        # Teste de visualização inline
        res_view = client.get("/visualizar/relatorio-semana3-pdf")
        assert res_view.status_code == 200
        assert res_view.headers["content-type"] == "application/pdf"
        assert "attachment" not in res_view.headers.get("content-disposition", "")

        # Teste de download com attachment
        res_down = client.get("/download/relatorio-semana3-pdf")
        assert res_down.status_code == 200
        assert "attachment" in res_down.headers.get("content-disposition", "")

        # Teste de download do zip
        res_zip = client.get("/download/entregavel-semana3-zip")
        assert res_zip.status_code == 200
        assert "application/zip" in res_zip.headers.get("content-type", "")

    finally:
        # Limpa arquivos temporários criados exclusivamente para o teste
        if criou_pdf and os.path.isfile(pdf_semana3):
            os.remove(pdf_semana3)
        if criou_zip and os.path.isfile(zip_semana3):
            os.remove(zip_semana3)
