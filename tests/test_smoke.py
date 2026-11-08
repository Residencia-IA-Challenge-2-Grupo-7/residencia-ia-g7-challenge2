def test_ambiente_container_ok():
    """
    Smoke test: garante que o ambiente Python e as dependencias essenciais
    carregam com sucesso dentro do container.
    """
    import numpy
    import langfuse
    import pydantic
    import torch

    assert not torch.cuda.is_available()


def test_api_rotas_carregadas():
    """Garante que a aplicacao FastAPI inicializa perfeitamente com todas as rotas."""
    from src.main import app

    assert app.title == "Orquestrador de Roles - RAG API"
    rotas = [route.path for route in app.routes]
    assert "/" in rotas
    assert "/rag" in rotas
    assert "/demo" in rotas
    assert "/status" in rotas
    assert "/health" in rotas
    assert "/telemetria/status" in rotas
    assert "/rag/buscar" in rotas
    assert "/entregaveis" in rotas
    assert "/download/relatorio-pdf" in rotas
    assert "/download/entregavel-zip" in rotas
    assert "/api/entregaveis/arquivo" in rotas
    assert "/api/entregaveis/dados" in rotas


def test_entregaveis_endpoints():
    """Valida as rotas de entrega interativa e integridade dos dados."""
    from fastapi.testclient import TestClient
    from src.main import app

    client = TestClient(app)

    # 1. Pagina HTML de entregaveis
    res_page = client.get("/entregaveis")
    assert res_page.status_code == 200
    assert "Central Interativa de Entregáveis" in res_page.text

    # 2. Dados aprovados 2FA (93 roles)
    res_dados = client.get("/api/entregaveis/dados?colecao=aprovados")
    assert res_dados.status_code == 200
    dados = res_dados.json()
    assert dados["total"] == 93
    assert len(dados["dados"]) == 93

    # 3. Quarentena (71 videos)
    res_quarentena = client.get("/api/entregaveis/dados?colecao=quarentena")
    assert res_quarentena.status_code == 200
    assert res_quarentena.json()["total"] == 71

    # 4. Vetores resumo (93 chunks com 3072 dims)
    res_vetores = client.get("/api/entregaveis/dados?colecao=vetores")
    assert res_vetores.status_code == 200
    assert res_vetores.json()["total"] == 93
    assert len(res_vetores.json()["dados"][0]["vetor_preview"]) == 5

    # 5. Seguranca: tentar path traversal
    res_traversal = client.get("/api/entregaveis/arquivo?caminho=../etc/passwd")
    assert res_traversal.status_code == 403



def test_simulacao_rag_telemetria():
    """Valida a execucao da funcao de busca do RAG com observabilidade."""
    from src.telemetria.telemetria import simular_recuperacao_rag

    resultado = simular_recuperacao_rag("date calmo na Asa Sul", top_k=2)
    assert "resultados" in resultado
    assert len(resultado["resultados"]) == 2
    assert resultado["status_sla"] == "conforme_rnf_14"
