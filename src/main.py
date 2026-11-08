import json
import os
from typing import Optional
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from pydantic import BaseModel

from src.interface import ENTREGAVEIS_PAGE, HTML_PAGE, LANDING_PAGE
from src.telemetria.telemetria import (
    checar_conexao_langfuse,
    disparar_primeiro_trace,
    flush_telemetria,
    simular_recuperacao_rag,
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

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


@app.get("/entregaveis", response_class=HTMLResponse)
def entregaveis_hub():
    """
    Central Interativa de Entregáveis (Semana 02):
    Permite aos monitores/avaliadores explorar relatórios, dados auditados 2FA,
    embeddings 3072d e código diretamente no navegador.
    """
    return HTMLResponse(content=ENTREGAVEIS_PAGE)


@app.get("/visualizar/relatorio-pdf")
def visualizar_relatorio_pdf():
    """Visualização inline do Relatório Técnico diretamente no navegador (sem forçar download)."""
    pdf_path = os.path.join(BASE_DIR, "docs/entregas/semana-02/RELATORIO_TECNICO_RAG_GRUPO7.pdf")
    if not os.path.isfile(pdf_path):
        raise HTTPException(status_code=404, detail="Relatório PDF não encontrado.")
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        content_disposition_type="inline",
    )


@app.get("/download/relatorio-pdf")
def download_relatorio_pdf():
    """Download do Relatório Técnico Oficial de RAG (PDF)."""
    pdf_path = os.path.join(BASE_DIR, "docs/entregas/semana-02/RELATORIO_TECNICO_RAG_GRUPO7.pdf")
    if not os.path.isfile(pdf_path):
        raise HTTPException(status_code=404, detail="Relatório PDF não encontrado.")
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename="RELATORIO_TECNICO_RAG_GRUPO7.pdf",
    )


@app.get("/download/entregavel-zip")
def download_entregavel_zip():
    """Download do Pacote ZIP Completo de Entregáveis da Semana 02."""
    zip_path = os.path.join(BASE_DIR, "docs/entregas/semana-02/Entregavel_Grupo7_Base_Conhecimento_e_RAG.zip")
    if not os.path.isfile(zip_path):
        raise HTTPException(status_code=404, detail="Pacote ZIP não encontrado.")
    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename="Entregavel_Grupo7_Base_Conhecimento_e_RAG.zip",
    )


@app.get("/api/entregaveis/arquivo")
def api_entregavel_arquivo(caminho: str = Query(..., description="Caminho relativo do arquivo")):
    """
    Entrega o conteúdo de arquivos de entrega de forma segura (somente leitura
    em diretórios permitidos: docs, data, src/rag).
    """
    caminho_limpo = os.path.normpath(caminho).replace("\\", "/")
    if caminho_limpo.startswith("/"):
        caminho_limpo = caminho_limpo.lstrip("/")

    permitidos = ("docs/", "data/", "src/rag/")
    if not any(caminho_limpo.startswith(p) for p in permitidos) or ".." in caminho_limpo:
        raise HTTPException(status_code=403, detail="Acesso não autorizado a este caminho.")

    caminho_absoluto = os.path.join(BASE_DIR, caminho_limpo)
    if not os.path.isfile(caminho_absoluto):
        raise HTTPException(status_code=404, detail=f"Arquivo {caminho_limpo} não encontrado.")

    tamanho = os.path.getsize(caminho_absoluto)
    ext = os.path.splitext(caminho_absoluto)[1].lower()

    try:
        with open(caminho_absoluto, "r", encoding="utf-8", errors="replace") as f:
            conteudo = f.read()
        return JSONResponse({
            "caminho": caminho_limpo,
            "tipo": ext.lstrip("."),
            "tamanho": tamanho,
            "conteudo": conteudo,
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/entregaveis/dados")
def api_entregavel_dados(colecao: str = Query("aprovados", description="aprovados, quarentena ou vetores")):
    """
    Retorna coleções estruturadas para tabelas interativas na Central de Entregáveis.
    """
    if colecao == "aprovados":
        path = os.path.join(BASE_DIR, "data/banco_aprovado_2fa.json")
    elif colecao == "quarentena":
        path = os.path.join(BASE_DIR, "data/fila_quarentena_2fa.json")
    elif colecao == "vetores":
        path = os.path.join(BASE_DIR, "data/banco_vetorial_embeddings.json")
    else:
        raise HTTPException(status_code=400, detail="Coleção inválida. Use: aprovados, quarentena ou vetores.")

    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Arquivo de dados não encontrado.")

    try:
        with open(path, "r", encoding="utf-8") as f:
            dados = json.load(f)

        if colecao == "vetores":
            # Retorna resumo leve dos vetores (preview dos primeiros 5 floats de cada vetor de 3072)
            amostra = []
            for d in dados:
                vetor = d.get("embedding_vector") or []
                amostra.append({
                    "id": d.get("id"),
                    "nome": d.get("nome"),
                    "regiao_administrativa": d.get("regiao_administrativa"),
                    "tipo_de_role": d.get("tipo_de_role"),
                    "documento_indexado": d.get("documento_indexado"),
                    "modelo_embedding": d.get("modelo_embedding", "text-embedding-3-large"),
                    "dimensoes_vetor": d.get("dimensoes_vetor", 3072),
                    "vetor_preview": vetor[:5],
                })
            return JSONResponse({"total": len(amostra), "dados": amostra})

        return JSONResponse({"total": len(dados), "dados": dados})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

