import os
from typing import Optional
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from src.interface import HTML_PAGE, LANDING_PAGE
from src.telemetria.telemetria import (
    checar_conexao_langfuse,
    disparar_primeiro_trace,
    simular_recuperacao_rag,
    flush_telemetria,
)

app = FastAPI(
    title="Orquestrador de Roles - RAG API",
    description="API do Orquestrador de Roles com Telemetria Langfuse (Grupo 7 - Challenge 2)",
    version="0.2.0",
)


class ConsultaRAGRequest(BaseModel):
    pergunta: str = "Quero um café calmo e aconchegante para um date na Asa Norte"
    top_k: int = 3
    categoria: Optional[str] = None


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    """
    Entrega a pagina inicial do Orquestrador de Roles com botao para /rag.
    Se o cliente pedir explicitamente application/json (ex: curl/testes), retorna JSON.
    """
    accept = request.headers.get("accept", "")
    if "application/json" in accept and "text/html" not in accept:
        langfuse_ok = checar_conexao_langfuse()
        return {
            "projeto": "Orquestrador de Roles",
            "status": "online",
            "ambiente": os.environ.get("ENVIRONMENT", "desenvolvimento"),
            "responsavel_devops": "Maria Eduarda",
            "telemetria_langfuse": "conectado" if langfuse_ok else "desconectado",
            "doc": "/docs",
        }
    return HTMLResponse(content=LANDING_PAGE)


@app.get("/rag", response_class=HTMLResponse)
@app.get("/demo", response_class=HTMLResponse)
def demo_interface():
    """Rota direta para a interface web do RAG."""
    return HTMLResponse(content=HTML_PAGE)


@app.get("/status")
def status_api():
    """Status estruturado em JSON para automações e monitoramento."""
    langfuse_ok = checar_conexao_langfuse()
    return {
        "projeto": "Orquestrador de Roles",
        "status": "online",
        "ambiente": os.environ.get("ENVIRONMENT", "desenvolvimento"),
        "responsavel_devops": "Maria Eduarda",
        "telemetria_langfuse": "conectado" if langfuse_ok else "desconectado",
        "doc": "/docs",
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/telemetria/status")
def status_telemetria():
    """Verifica se as chaves e a conexao com o Langfuse Cloud estao operacionais."""
    conectado = checar_conexao_langfuse()
    return {
        "langfuse_conectado": conectado,
        "host": os.environ.get("LANGFUSE_BASE_URL", os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com")),
        "public_key_configurada": bool(os.environ.get("LANGFUSE_PUBLIC_KEY")),
        "modulo": "ML/LLMOps - Observabilidade",
    }


@app.post("/telemetria/disparar-trace")
def acionar_primeiro_trace():
    """Gera um trace inicial completo no Langfuse Cloud para validar o dashboard."""
    resultado = disparar_primeiro_trace()
    return resultado


@app.post("/rag/buscar")
def buscar_roles(requisicao: ConsultaRAGRequest):
    """
    Executa a busca de roles com telemetria e tracing automatico no Langfuse.
    """
    resultado = simular_recuperacao_rag(
        pergunta_usuario=requisicao.pergunta,
        top_k=requisicao.top_k,
        categoria=requisicao.categoria,
    )
    flush_telemetria()
    return resultado
