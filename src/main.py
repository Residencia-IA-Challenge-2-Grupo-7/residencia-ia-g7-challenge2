import json
import logging
import os
import secrets
import threading
import time
from typing import Literal, Optional
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from src.interface import COMPARATIVO_PAGE, ENTREGAVEIS_PAGE, HTML_PAGE, LANDING_PAGE
from src.rag.comparador_ab import ErroComparativo, executar_comparacao_ab, listar_golden
from src.salas.rotas import router as salas_router
from src.telemetria.telemetria import (
    checar_conexao_langfuse,
    disparar_primeiro_trace,
    flush_telemetria,
    simular_recuperacao_rag,
)

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app = FastAPI(
    title="Orquestrador de Roles - RAG API",
    description="API do Orquestrador de Roles com Telemetria Langfuse (Grupo 7 - Challenge 2)",
    version="0.2.0",
)
app.include_router(salas_router)


class ConsultaRAGRequest(BaseModel):
    pergunta: str = "Quero um café calmo e aconchegante para um date na Asa Norte"
    top_k: int = 3
    categoria: Optional[str] = None


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    """
    Entrega a pagina inicial do Orquestrador de Roles com botao para /rag e /comparativo.
    Se o cliente pedir explicitamente application/json (ex: curl/testes), retorna JSON.
    """
    accept = request.headers.get("accept", "")
    if "application/json" in accept and "text/html" not in accept:
        return status_api()
    return HTMLResponse(content=LANDING_PAGE)


@app.get("/rag", response_class=HTMLResponse)
@app.get("/demo", response_class=HTMLResponse)
def demo_interface():
    """Rota direta para a interface web do RAG."""
    return HTMLResponse(content=HTML_PAGE)


@app.get("/comparativo", response_class=HTMLResponse)
@app.get("/comparacao", response_class=HTMLResponse)
def comparativo_interface():
    """Rota da Interface Web de Comparação Lado a Lado: LLM Pura vs. RAG Ancorado (Issue #37)."""
    return HTMLResponse(content=COMPARATIVO_PAGE)


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


class ComparativoRequest(BaseModel):
    """Pergunta livre ou id de um caso do golden dataset (com o id, a pergunta pode ficar vazia)."""

    model_config = ConfigDict(extra="forbid")
    pergunta: Optional[str] = None
    id_golden: Optional[str] = None
    raciocinio: Literal["desligado", "low", "medium", "high"] = "desligado"  # vale para os dois modos
    busca: Literal["lexica", "vetorial", "hibrida"] = "lexica"  # só o Modo B


@app.get("/api/comparativo/golden")
def comparativo_golden():
    """Perguntas do golden dataset da semana 3 disponíveis para o comparativo (issue #34)."""
    perguntas = listar_golden()
    return {"total": len(perguntas), "perguntas": perguntas}


@app.post("/api/comparativo/executar")
def comparativo_executar(requisicao: ComparativoRequest):
    """
    Roda a mesma pergunta no Modo A (LLM pura, sem documentos) e no Modo B (RAG sobre a base de 93 lugares,
    com guardrails), lado a lado (issue #34). Com `id_golden`, devolve também o gabarito do caso.
    `raciocinio` liga o raciocínio do modelo nos dois modos; `busca` escolhe a busca do Modo B (por palavras,
    por embeddings `gemini-embedding-001` ou as duas juntas).
    """
    try:
        resultado = executar_comparacao_ab(requisicao.pergunta, requisicao.id_golden,
                                           raciocinio=requisicao.raciocinio, busca=requisicao.busca)
    except ErroComparativo as e:
        raise HTTPException(status_code=e.status, detail=str(e))
    flush_telemetria()
    # O resultado fica guardado no servidor: /avaliar só recebe este id, nunca texto, gabarito ou trace do navegador
    resultado["id_comparativo"] = _guardar_comparativo(resultado)
    return resultado


class AvaliarRequest(BaseModel):
    """Só o id devolvido por `POST /api/comparativo/executar` (o resultado avaliado é o guardado no servidor)."""

    model_config = ConfigDict(extra="forbid")
    id_comparativo: str = Field(min_length=8, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")


TTL_COMPARATIVO_S = 900
MAX_COMPARATIVOS = 200
_COMPARATIVOS: dict[str, dict] = {}
_COMPARATIVOS_LOCK = threading.Lock()


def _guardar_comparativo(resultado: dict) -> str:
    """Guarda o resultado em memória com id aleatório e validade curta; descarta vencidos e excedentes."""
    agora = time.monotonic()
    id_comparativo = secrets.token_urlsafe(16)
    with _COMPARATIVOS_LOCK:
        for chave in [k for k, v in _COMPARATIVOS.items() if v["expira"] <= agora]:
            del _COMPARATIVOS[chave]
        while len(_COMPARATIVOS) >= MAX_COMPARATIVOS:
            del _COMPARATIVOS[next(iter(_COMPARATIVOS))]
        _COMPARATIVOS[id_comparativo] = {
            "dados": dict(resultado),
            "expira": agora + TTL_COMPARATIVO_S,
            "avaliacao": None,
            "trava": threading.Lock(),
        }
    return id_comparativo


@app.post("/api/comparativo/avaliar")
def comparativo_avaliar(requisicao: AvaliarRequest):
    """
    Motor de Avaliação Híbrida da Semana 3 (Issue #36): avalia um comparativo já executado pelo servidor
    (RNF-04 determinístico + LLM-as-a-Judge MiMo-V2.6-Pro) e grava as notas no trace dele no Langfuse.
    A avaliação é feita uma única vez por id: repetir a chamada devolve o mesmo resultado, sem novo custo.
    """
    with _COMPARATIVOS_LOCK:
        entrada = _COMPARATIVOS.get(requisicao.id_comparativo)
        if entrada and entrada["expira"] <= time.monotonic():
            del _COMPARATIVOS[requisicao.id_comparativo]
            entrada = None
    if entrada is None:
        raise HTTPException(status_code=404, detail="Comparativo não encontrado ou expirado. Execute-o de novo.")

    with entrada["trava"]:
        if entrada["avaliacao"] is None:
            dados = entrada["dados"]
            try:
                from src.telemetria.evals_semana3 import avaliar_par_comparativo

                # O trace vem do resultado gerado pelo servidor, não do navegador
                trace_url = ((dados.get("modo_b_rag") or {}).get("trace_url") or "").rstrip("/")
                trace_id = trace_url.rsplit("/", 1)[-1] if "/traces/" in trace_url else None
                entrada["avaliacao"] = avaliar_par_comparativo(
                    dados, registrar_langfuse=bool(trace_id), trace_id=trace_id)
                flush_telemetria()
            except ErroComparativo as e:
                raise HTTPException(status_code=e.status, detail=str(e))
            except Exception:
                logger.exception("Falha ao avaliar o comparativo %s", requisicao.id_comparativo)
                raise HTTPException(status_code=500, detail="Falha ao avaliar o comparativo.")
        return {"comparativo": entrada["dados"], "avaliacao": entrada["avaliacao"]}


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

