"""Pipeline RAG corporativo construído com Haystack (haystack-ai v3.x).

Atende à recomendação dos mentores para a Semana 3 (demonstração de pipeline RAG
via framework corporativo Haystack), operando sobre a base de 93 rolês auditados
(data/banco_aprovado_2fa.json).

Arquitetura do Pipeline Haystack:
  1. InMemoryDocumentStore (93 documentos da base 2FA)
  2. InMemoryBM25Retriever (recuperação lexical / BM25)
  3. ChatPromptBuilder (montagem do prompt Modo B ancorado)
  4. Gerador LLM (OpenRouter / DeepSeek V4.1 com fallback determinístico)
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

# Desabilita telemetria interna do Haystack para evitar escrita em ~/.haystack
os.environ["HAYSTACK_TELEMETRY_ENABLED"] = "False"

from haystack import Document, Pipeline, component
from haystack.components.builders import ChatPromptBuilder
from haystack.components.retrievers.in_memory import InMemoryBM25Retriever
from haystack.dataclasses import ChatMessage
from haystack.document_stores.in_memory import InMemoryDocumentStore

from src.interpretador.config import segredo
from src.rag import llm_pura, llm_rag

RAIZ = Path(__file__).resolve().parents[2]
ARQUIVO_BASE = RAIZ / "data" / "banco_aprovado_2fa.json"

PROMPT_SISTEMA_HAYSTACK = (
    "Você é o assistente oficial de rolês de Brasília construído sobre a pipeline Haystack. "
    "Responda em português do Brasil em até 150 palavras. Recomende no máximo 3 lugares baseando-se "
    "estritamente nas fontes fornecidas. Cite as fontes no formato [FONTE #n]."
)

TEMPLATE_USUARIO = [
    ChatMessage.from_system(PROMPT_SISTEMA_HAYSTACK),
    ChatMessage.from_user(
        "Documentos recuperados da base de 93 rolês:\n\n"
        "{% for doc in documents %}"
        "[FONTE #{{ loop.index }}]\n"
        "Nome: {{ doc.meta['nome'] }}\n"
        "Região administrativa: {{ doc.meta.get('regiao_administrativa', 'DF') }}\n"
        "Endereço: {{ doc.meta.get('endereco', 'Não informado') }}\n"
        "Preço médio por pessoa: {{ doc.meta.get('preco_medio_texto', 'não informado') }}\n"
        "Horário de funcionamento: {{ doc.meta.get('horario_funcionamento') or 'não informado' }}\n"
        "Descrição: {{ doc.content }}\n\n"
        "{% endfor %}\n"
        "Pergunta do usuário: {{ question }}\n\n"
        "Instruções: use apenas os fatos acima. Se nenhum documento atender, recuse educadamente."
    ),
]


def carregar_documentos_base() -> list[Document]:
    """Lê os 93 rolês auditados e converte em Documentos do Haystack."""
    if not ARQUIVO_BASE.exists():
        return []
    try:
        dados = json.loads(ARQUIVO_BASE.read_text(encoding="utf-8"))
    except Exception:
        return []

    docs = []
    for item in dados:
        if not isinstance(item, dict):
            continue
        vibes = item.get("vibes")
        vibes_txt = ", ".join(vibes) if isinstance(vibes, list) else ""
        custo = item.get("custo_medio_rs")
        preco_txt = llm_rag._reais(float(custo)) if custo not in (None, "") else "não informado"
        # O BM25 só lê o conteúdo: nome, tipo, RA, vibes e descrição precisam estar nele
        partes = [
            f"{item.get('nome', '')}.",
            f"Tipo: {item.get('tipo_de_role', '')}.",
            f"Região administrativa: {item.get('regiao_administrativa', '')}.",
            f"Vibes: {vibes_txt}.",
            f"{item.get('resumo_sensorial') or ''}",
        ]
        doc = Document(
            content=" ".join(p for p in partes if p).strip(),
            meta={
                "id": item.get("id"),
                "nome": item.get("nome"),
                "tipo_de_role": item.get("tipo_de_role"),
                "regiao_administrativa": item.get("regiao_administrativa"),
                "endereco": item.get("endereco"),
                "faixa_de_preco": item.get("faixa_de_preco"),
                "custo_medio_rs": custo,
                "preco_medio_texto": preco_txt,
                "horario_funcionamento": item.get("horario_funcionamento"),
            },
        )
        docs.append(doc)
    return docs


@component
class GeradorOpenRouter:
    """Componente Haystack customizado que chama OpenRouter com guardrails e telemetria."""

    @component.output_types(resposta=str, metadados=dict)
    def run(self, prompt: list[ChatMessage], pergunta: str = ""):
        chave = segredo("OPENROUTER_API_KEY")
        if not chave:
            # Fallback determinístico caso sem chave (CI ou modo offline)
            return {
                "resposta": f"[Haystack RAG - Fallback Offline] Resposta gerada sobre os documentos recuperados para: '{pergunta}'.",
                "metadados": {"modelo": "fallback-offline", "tokens_total": 0, "provedor": "offline"},
            }

        sistema = prompt[0].text if len(prompt) > 0 else PROMPT_SISTEMA_HAYSTACK
        usuario = prompt[1].text if len(prompt) > 1 else pergunta

        import requests
        sessao = requests.Session()
        res = llm_pura._chamar(pergunta, chave, sessao, nivel=None, sistema=sistema, usuario=usuario, modo="haystack_rag")
        return {
            "resposta": res.get("resposta", ""),
            "metadados": {
                "modelo": res.get("modelo"),
                "tokens_total": res.get("tokens_total", 0),
                "custo_estimado_brl": res.get("custo_estimado_brl", 0.0),
                "latencia_ms": res.get("latencia_ms", 0.0),
                "disponivel": res.get("disponivel", False),
            },
        }


def criar_pipeline_haystack() -> tuple[Pipeline, InMemoryDocumentStore]:
    """Monta e conecta o pipeline completo do Haystack."""
    doc_store = InMemoryDocumentStore()
    docs = carregar_documentos_base()
    if docs:
        doc_store.write_documents(docs)

    retriever = InMemoryBM25Retriever(document_store=doc_store)
    prompt_builder = ChatPromptBuilder(template=TEMPLATE_USUARIO)
    gerador = GeradorOpenRouter()

    pipe = Pipeline()
    pipe.add_component("retriever", retriever)
    pipe.add_component("prompt_builder", prompt_builder)
    pipe.add_component("gerador", gerador)

    pipe.connect("retriever.documents", "prompt_builder.documents")
    pipe.connect("prompt_builder.prompt", "gerador.prompt")

    return pipe, doc_store


# Instância singleton para reuso em memória
_PIPELINE, _DOC_STORE = None, None


def obter_pipeline_haystack() -> Pipeline:
    global _PIPELINE, _DOC_STORE
    if _PIPELINE is None:
        _PIPELINE, _DOC_STORE = criar_pipeline_haystack()
    return _PIPELINE


def executar_rag_haystack(pergunta: str, top_k: int = 3) -> dict[str, Any]:
    """Executa a pergunta através do pipeline Haystack retornando resposta e fontes."""
    pipe = obter_pipeline_haystack()
    res = pipe.run(
        {
            "retriever": {"query": pergunta, "top_k": top_k},
            "prompt_builder": {"question": pergunta},
            "gerador": {"pergunta": pergunta},
        },
        include_outputs_from={"retriever"},  # os mesmos documentos do prompt, sem rodar a busca de novo
    )

    saida_gerador = res.get("gerador", {})
    docs_recuperados = res.get("retriever", {}).get("documents", [])

    fontes = []
    for i, doc in enumerate(docs_recuperados, 1):
        m = doc.meta or {}
        fontes.append({
            "fonte_id": f"FONTE #{i}",
            "id": m.get("id"),
            "nome": m.get("nome"),
            "regiao_administrativa": m.get("regiao_administrativa"),
            "preco": m.get("custo_medio_rs"),
        })

    return {
        "framework": "Haystack 3.5.0",
        "pergunta": pergunta,
        "resposta": saida_gerador.get("resposta", ""),
        "fontes_recuperadas": fontes,
        "total_fontes": len(fontes),
        "metadados": saida_gerador.get("metadados", {}),
    }
