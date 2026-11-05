def test_ambiente_container_ok():
    """
    Smoke test: garante que o ambiente Python e as dependencias essenciais
    carregam com sucesso dentro do container.
    """
    import numpy
    import langfuse
    import pydantic
    import torch

    assert "+cpu" in torch.__version__ or torch.__version__.split("+")[0]

def test_api_rotas_carregadas():
    """Garante que a aplicacao FastAPI inicializa perfeitamente."""
    from src.main import app
    assert app.title == "Orquestrador de Roles - RAG API"
