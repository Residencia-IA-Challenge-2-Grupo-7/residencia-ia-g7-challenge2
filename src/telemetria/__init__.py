"""Módulo de telemetria e observabilidade estruturada (RNF-10, Issue #73)."""
from src.telemetria.langfuse_agentes import (
    PROJETO_LANGFUSE_ID,
    SPANS_AGENTES,
    LangfuseAgentesCallbackHandler,
    criar_callback_handler_agentes,
    mascarar_pii,
    obter_trace_url,
    observar_agente,
    registrar_span_agente,
)

__all__ = [
    "PROJETO_LANGFUSE_ID",
    "SPANS_AGENTES",
    "LangfuseAgentesCallbackHandler",
    "criar_callback_handler_agentes",
    "mascarar_pii",
    "obter_trace_url",
    "observar_agente",
    "registrar_span_agente",
]
