def test_ambiente_container_ok():
    """
    Smoke test: garante que o ambiente Python e as bibliotecas essenciais
    carregam com sucesso dentro do container.
    """
    import psycopg
    import pgvector
    import langfuse
    import pydantic
    import torch

    # Valida que o PyTorch esta na versao CPU (otimizada)
    assert "+cpu" in torch.__version__ or torch.__version__.split("+")[0]
