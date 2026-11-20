"""Instrumentação de Telemetria e Tracing do Grafo Multiagente no Langfuse Cloud (Issue #73, RNF-10, RNF-14).

Responsabilidades:
1. Spans explícitos padronizados para cada nó do grafo multiagente (`@observar_agente` e `registrar_span_agente`)
   em conformidade estrita com o ADR 0015 (evitando explosão de observações e mantendo entradas/saídas enxutas).
2. Nomes canônicos padronizados para cada nó do grafo (agente_0_pessoal, agente_1_pesquisa, agente_2_logistica,
   agente_3_validacao, agente_4_comunicacao, agente_3_validacao_textos, agente_orquestrador_consolidar,
   agente_orquestrador_finalizar, grafo_sala_multiagente).
3. Registro estruturado de metadados: iterações do loop condicional (iteracao_pesquisa), quantidade e motivos de
   vetos (quantidade_vetos, motivos_vetos), status de convergência, auditorias do juiz (juiz, juiz_llm, exposicoes)
   e métricas de chamadas de LLM (tokens, custo_usd, latencia_llm_s, chamadas_llm, tentativas_sem_resposta).
4. Captura e retorno do link oficial do trace (`trace_url`) no Langfuse Cloud dinamicamente via SDK.
5. Mascaramento preventivo de PII privada (telefones, e-mails, CPFs, origens individuais e nomes de membros).
   A proteção de tetos e orçamentos individuais é garantida primariamente pelo isolamento no cofre (RNF-02),
   preservando valores e faixas de preço públicos dos estabelecimentos para conferência do juiz.
6. Resiliência e fallback offline caso o Langfuse Cloud esteja desconectado ou credenciais ausentes.
"""
from __future__ import annotations

import logging
import os
import re
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional

logger = logging.getLogger(__name__)

PROJETO_LANGFUSE_ID = "cmw59be2y01d8ad0jqbgsjut6"

# Mapeamento canônico dos nós do grafo para os nomes oficiais de spans exigidos pela Issue #73 e RNF-10
SPANS_AGENTES: Mapping[str, str] = {
    "no_pessoal": "agente_0_pessoal",
    "pessoal": "agente_0_pessoal",
    "agente_pessoal": "agente_0_pessoal",
    "agente_0_pessoal": "agente_0_pessoal",
    "no_consolidar_grupo": "agente_orquestrador_consolidar",
    "consolidar_grupo": "agente_orquestrador_consolidar",
    "agente_orquestrador_consolidar": "agente_orquestrador_consolidar",
    "no_pesquisa": "agente_1_pesquisa",
    "pesquisa": "agente_1_pesquisa",
    "agente_1_pesquisa": "agente_1_pesquisa",
    "pesquisa.buscar": "agente_1_pesquisa_buscar",
    "no_logistica": "agente_2_logistica",
    "logistica": "agente_2_logistica",
    "agente_2_logistica": "agente_2_logistica",
    "no_validacao": "agente_3_validacao",
    "validacao": "agente_3_validacao",
    "agente_3_validacao": "agente_3_validacao",
    "validacao.vetos": "agente_3_validacao_vetos",
    "no_comunicacao": "agente_4_comunicacao",
    "comunicacao": "agente_4_comunicacao",
    "agente_4_comunicacao": "agente_4_comunicacao",
    "no_validacao_textos": "agente_3_validacao_textos",
    "validacao_textos": "agente_3_validacao_textos",
    "agente_3_validacao_textos": "agente_3_validacao_textos",
    "no_finalizar": "agente_orquestrador_finalizar",
    "finalizar": "agente_orquestrador_finalizar",
    "agente_orquestrador_finalizar": "agente_orquestrador_finalizar",
    "sala_multiagente": "grafo_sala_multiagente",
    "grafo_sala_multiagente": "grafo_sala_multiagente",
}

# Regexes de detecção e mascaramento de PII privada (RNF-02, RNF-10)
# NOTA: Valores públicos de cardápio e preços dos lugares NÃO são mascarados para permitir auditoria factual pelo juiz.
# O teto de gastos individual dos participantes fica isolado com segurança no cofre (fora do estado).
RE_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
RE_TELEFONE = re.compile(r"(?<!\w)(?:\+?55\s?)?(?:\(?\d{2}\)?\s?)?(?:9?\d{4}[-\s]?\d{4})\b")
RE_CPF = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")
RE_ORIGEM_EXPLICITA = re.compile(
    r"\b(?:quem\s+vem\s+de|quem\s+sai\s+de|saindo\s+de|vindo\s+de|mora\s+em|pra\s+quem\s+sai\s+de|"
    r"saindo\s+do|vindo\s+do|partindo\s+de)\s+([A-Za-zÀ-ÖØ-öø-ÿ0-9\s]+)",
    re.IGNORECASE,
)


def mascarar_pii(dados: Any, nomes_proibidos: Iterable[str] | None = None) -> Any:
    """Varre recursivamente estruturas de dados e mascara PII privada (RNF-02, RNF-10).
    
    Substitui:
    - E-mails -> [EMAIL_REMOVIDO]
    - Telefones -> [TELEFONE_REMOVIDO]
    - CPFs -> [CPF_REMOVIDO]
    - Menções explícitas de origem individual -> [ORIGEM_REMOVIDA]
    - Nomes de participantes fornecidos -> [NOME_REMOVIDO]
    - Chaves estritamente privadas (teto, origem...) -> [DADO_PRIVADO_REMOVIDO]
    """
    if dados is None:
        return None

    if isinstance(dados, str):
        t = dados
        t = RE_EMAIL.sub("[EMAIL_REMOVIDO]", t)
        t = RE_CPF.sub("[CPF_REMOVIDO]", t)
        t = RE_TELEFONE.sub("[TELEFONE_REMOVIDO]", t)
        t = RE_ORIGEM_EXPLICITA.sub("[ORIGEM_REMOVIDA]", t)

        if nomes_proibidos:
            for nome in nomes_proibidos:
                n = str(nome).strip()
                if len(n) >= 3:
                    padrao = rf"\b{re.escape(n)}\b"
                    t = re.sub(padrao, "[NOME_REMOVIDO]", t, flags=re.IGNORECASE)
        return t

    if isinstance(dados, Mapping):
        mascarado: dict[str, Any] = {}
        for k, v in dados.items():
            # Chaves estritamente privadas nunca são repassadas
            if k in {"teto", "teto_rs", "teto_individual", "origem", "origem_ra", "ra_origem", "usuario"}:
                mascarado[k] = "[DADO_PRIVADO_REMOVIDO]"
            else:
                mascarado[k] = mascarar_pii(v, nomes_proibidos)
        return mascarado

    if isinstance(dados, (list, tuple, set)):
        tipo = type(dados)
        itens = [mascarar_pii(item, nomes_proibidos) for item in dados]
        return tipo(itens)

    return dados


def obter_trace_url(trace_id: str | None = None) -> str | None:
    """Retorna a URL pública canônica do trace no Langfuse Cloud (ou None caso indisponível)."""
    try:
        from langfuse import get_client

        c = get_client()
        tid = trace_id or c.get_current_trace_id()
        if tid:
            url = c.get_trace_url(trace_id=tid)
            if url:
                return url
    except Exception:
        pass

    env_host = os.environ.get("LANGFUSE_BASE_URL") or os.environ.get("LANGFUSE_HOST") or "https://cloud.langfuse.com"
    tid_fallback = trace_id
    if not tid_fallback:
        try:
            from langfuse import get_client
            tid_fallback = get_client().get_current_trace_id()
        except Exception:
            pass

    if tid_fallback:
        proj = os.environ.get("LANGFUSE_PROJECT_ID", PROJETO_LANGFUSE_ID)
        return f"{env_host.rstrip('/')}/project/{proj}/traces/{tid_fallback}"
    return None


def registrar_span_agente(
    nome_agente: str = "",
    entrada: Any = None,
    saida: Any = None,
    *,
    nomes_proibidos: Iterable[str] | None = None,
    **metadados: Any,
) -> None:
    """Atualiza o span do agente atual no Langfuse Cloud aplicando máscara estrita de PII (RNF-02, RNF-10).
    
    Registra:
    - Nome canônico do agente (ex: agente_1_pesquisa);
    - Entrada e saída selecionadas à mão e sanitizadas;
    - Metadados de iteração, vetos, convergência, tokens, custo e latência.
    """
    try:
        from opentelemetry import trace
        if not trace.get_current_span().is_recording():
            return

        from langfuse import get_client
        c = get_client()

        nome_canonico = SPANS_AGENTES.get(nome_agente, nome_agente) if nome_agente else None
        entrada_limpa = mascarar_pii(entrada, nomes_proibidos) if entrada is not None else None
        saida_limpa = mascarar_pii(saida, nomes_proibidos) if saida is not None else None
        meta_limpa = mascarar_pii(metadados, nomes_proibidos) if metadados else None

        kw: dict[str, Any] = {
            "input": entrada_limpa,
            "output": saida_limpa,
            "metadata": meta_limpa or None,
        }
        if nome_canonico:
            kw["name"] = nome_canonico

        c.update_current_span(**kw)
    except Exception as e:
        logger.debug("Não foi possível atualizar o span no Langfuse (%s: %s)", type(e).__name__, e)


def observar_agente(nome: str, tipo: str = "agent"):
    """Decorador de nó do grafo para rastreamento no Langfuse Cloud.
    
    Desabilita captura automática de input/output bruto do LangGraph (capture_input=False,
    capture_output=False) para evitar vazamento acidental de estado privado (RNF-02).
    """
    nome_canonico = SPANS_AGENTES.get(nome, nome)
    try:
        from langfuse import observe
        return observe(name=nome_canonico, as_type=tipo, capture_input=False, capture_output=False)
    except Exception:
        # Fallback sem Langfuse instalado
        return lambda f: f
