"""Modo A da comparação da semana 3: LLM pura, zero-shot, sem nenhum documento da base (issue #33, ADR 0010).

O modelo é o DeepSeek V4.1 Flash pela OpenRouter, o mesmo do interpretador (ADR 0007), com o mesmo roteamento:
só provedores sem retenção de dados, sem coleta para treino e sem quantização fp4. A chave fica em
`OPENROUTER_API_KEY` no `.env` (fora do git). Sem chave (no CI, por exemplo), a função devolve uma resposta de
reserva determinística, marcada com `disponivel: False`, em vez de quebrar.

    from src.rag.llm_pura import gerar_resposta_llm_pura
    r = gerar_resposta_llm_pura("Onde comer hambúrguer artesanal em Taguatinga?")
    r["resposta"], r["fontes_utilizadas"] == [], r["latencia_ms"], r["custo_estimado_brl"]

Para a comparação ser justa, o prompt pede o mesmo formato do Modo B (nome, RA, endereço, preço em R$ e
horário) e a mesma regra de não inventar; só falta a base. O que se mede é quanto o modelo inventa sozinho.
"""
from __future__ import annotations

import os
import time
from typing import Any

import requests

from src.interpretador.config import CFG, segredo

MODELO_PADRAO = "deepseek/deepseek-v4.1-flash-1017"
URL = CFG["llm"]["url"]
CHAVE_ENV = CFG["llm"]["chave_env"]
ROTEAMENTO = dict(CFG["llm"]["roteamento"])   # ZDR, sem coleta para treino, sem fp4 (RNF-01)
MODO = "modo_a_llm_pura"
VERSAO_PROMPT = "2026-11-10"                  # entra na chave do cache: prompt novo, cache novo
COTACAO_USD_BRL = 5.80                        # mesma cotação usada em src/telemetria/telemetria.py
TIMEOUT_S = 20
TENTATIVAS = 2
MAX_TOKENS = 700

PROMPT_SISTEMA = (
    "Você é um assistente que recomenda rolês (bares, restaurantes, cafés, eventos e passeios) no Distrito "
    "Federal: Brasília e as regiões administrativas. Responda em português do Brasil, em até 150 palavras. "
    "Recomende no máximo 3 lugares e, para cada um, informe: nome, região administrativa, endereço, preço médio "
    "por pessoa em R$ e horário de funcionamento. Use apenas o que você sabe; não há documentos de apoio. "
    "Não invente informações: se não tiver certeza de um dado, diga que não sabe."
)


def _modelo() -> str:
    return os.environ.get("LLM_PURA_MODELO") or MODELO_PADRAO


def _resultado(pergunta: str, **campos: Any) -> dict:
    base = {
        "pergunta": pergunta, "resposta": "", "modelo": _modelo(), "provedor": None, "modo": MODO,
        "fontes_utilizadas": [], "latencia_ms": 0.0, "tokens_entrada": 0, "tokens_saida": 0, "tokens_total": 0,
        "custo_estimado_usd": 0.0, "custo_estimado_brl": 0.0, "disponivel": True, "cache_hit": False, "erro": None,
    }
    base.update(campos)
    return base


def _reserva(pergunta: str, motivo: str) -> dict:
    """Sem chave ou com a API fora do ar: resposta determinística, sem lugar nenhum (nada inventado)."""
    return _resultado(pergunta, disponivel=False, erro=motivo,
                      resposta=("[LLM pura indisponível] Não foi possível consultar o modelo de linguagem "
                                f"({motivo}). Nenhum lugar foi recomendado."))


def _chamar(pergunta: str, chave: str, sessao) -> dict:
    corpo = {
        "model": _modelo(),
        "messages": [{"role": "system", "content": PROMPT_SISTEMA}, {"role": "user", "content": pergunta}],
        "temperature": 0,
        "max_tokens": MAX_TOKENS,
        "provider": ROTEAMENTO,
        "reasoning": {"enabled": False},  # medido em 05/11: com raciocínio, p90 de 6,4 s e respostas vazias
        "usage": {"include": True},
    }
    erros = []
    for _ in range(TENTATIVAS):
        t0 = time.perf_counter()
        try:
            r = sessao.post(URL, json=corpo, timeout=TIMEOUT_S,
                            headers={"Authorization": f"Bearer {chave}",
                                     "X-Title": "Orquestrador de Roles (Residencia IA UnB)"})
            ms = (time.perf_counter() - t0) * 1000
            if r.status_code >= 400:
                erros.append(f"HTTP {r.status_code}")
                if r.status_code in (400, 401, 402, 403, 404):
                    break
                continue
            d = r.json()
            texto = (d["choices"][0]["message"].get("content") or "").strip()
            if not texto:
                erros.append(f"resposta vazia ({d['choices'][0].get('finish_reason')})")
                continue
            u = d.get("usage") or {}
            custo_usd = float(u.get("cost") or 0.0)
            return _resultado(pergunta, resposta=texto, modelo=d.get("model", _modelo()), provedor=d.get("provider"),
                              latencia_ms=round(ms, 1), tokens_entrada=u.get("prompt_tokens") or 0,
                              tokens_saida=u.get("completion_tokens") or 0, tokens_total=u.get("total_tokens") or 0,
                              custo_estimado_usd=round(custo_usd, 8),
                              custo_estimado_brl=round(custo_usd * COTACAO_USD_BRL, 6))
        except (requests.RequestException, ValueError, KeyError, IndexError, TypeError) as e:
            erros.append(type(e).__name__)
    return _reserva(pergunta, "falha na OpenRouter: " + "; ".join(erros[-2:]))


def _registrar_langfuse(r: dict) -> None:
    try:
        from src.telemetria.telemetria import obter_cliente

        obter_cliente().update_current_generation(
            model=r["modelo"],
            usage_details={"input": r["tokens_entrada"], "output": r["tokens_saida"], "total": r["tokens_total"]},
            cost_details={"total": r["custo_estimado_usd"]},
            metadata={"modo": MODO, "provedor": "OpenRouter", "fontes": 0, "disponivel": r["disponivel"]},
        )
    except Exception:
        pass


def gerar_resposta_llm_pura(pergunta: str, *, usar_cache: bool = True, registrar: bool = True,
                            sessao=None) -> dict:
    """Pergunta -> resposta do LLM sem nenhum documento da base (`fontes_utilizadas` é sempre `[]`).

    `usar_cache`: reaproveita a resposta de uma pergunta idêntica (cache da telemetria, RNF-15), para o
    benchmark não pagar duas vezes. `registrar`: grava a métrica sem PII em data/telemetria/ (RNF-10).
    `sessao`: objeto com `.post` (para testes); por padrão, `requests`.
    """
    pergunta = (pergunta or "").strip()
    if not pergunta:
        return _reserva(pergunta, "pergunta vazia")
    from src.telemetria import logger_metricas as lm

    parametros = {"modelo": _modelo(), "prompt": VERSAO_PROMPT}
    if usar_cache:
        item = lm.obter_cache_avaliacao(pergunta, MODO, parametros)
        if item and isinstance(item.get("resposta"), dict):
            return {**item["resposta"], "cache_hit": True, "latencia_ms": 0.0}

    chave = segredo(CHAVE_ENV)
    r = _chamar(pergunta, chave, sessao or requests.Session()) if chave else _reserva(pergunta, f"sem {CHAVE_ENV}")
    _registrar_langfuse(r)
    if r["disponivel"]:
        if usar_cache:
            lm.salvar_cache_avaliacao(pergunta, r, MODO, r["tokens_total"], r["latencia_ms"], parametros)
        if registrar:
            lm.registrar_evento_metrica(MODO, r["latencia_ms"], r["tokens_total"], r["custo_estimado_brl"],
                                        cache_hit=False, consulta=pergunta,
                                        metadados={"modelo": r["modelo"], "provedor": r["provedor"]})
    return r


try:  # trace no Langfuse quando houver chaves; sem elas, a função roda igual
    from langfuse import observe

    gerar_resposta_llm_pura = observe(name="modo_a_llm_pura", as_type="generation")(gerar_resposta_llm_pura)
except Exception:  # pragma: no cover
    pass
