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
    """Garante que a aplicacao FastAPI inicializa perfeitamente."""
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


def test_simulacao_rag_telemetria():
    """Valida a execucao da funcao de busca do RAG com observabilidade."""
    from src.telemetria.telemetria import simular_recuperacao_rag

    resultado = simular_recuperacao_rag("date calmo na Asa Sul", top_k=2)
    assert "resultados" in resultado
    assert len(resultado["resultados"]) == 2
    assert resultado["status_sla"] == "conforme_rnf_14"
