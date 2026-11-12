"""Modo B da comparação da semana 3: o mesmo LLM do Modo A, agora com os lugares recuperados como contexto (issue #34).

O que muda entre os modos é só a base. Modelo (DeepSeek V4.1 Flash), temperatura 0, roteamento sem retenção,
limite de palavras e regra de não inventar são os mesmos do Modo A (`src/rag/llm_pura.py`, ADR 0010). Aqui o
prompt entrega os lugares recuperados da base de 93 (com os guardrails da issue #33) como `[FONTE #n]`
e pede que a resposta use só esses documentos.

    from src.rag.llm_rag import gerar_resposta_rag
    r = gerar_resposta_rag("Onde comer hambúrguer em Taguatinga?", lugares)   # lugares da recuperação
    r["resposta"], r["fontes_utilizadas"], r["latencia_ms"], r["custo_estimado_brl"]

Sem chave da OpenRouter (no CI, por exemplo) ou com a API fora do ar, a resposta é o texto fixo da rota
/rag/buscar da semana 2, com `disponivel: False` e `modelo: "texto-fixo-sem-llm"`, para o contrato continuar
igual e ninguém confundir o texto fixo com a geração do LLM.
"""
from __future__ import annotations

import re
from typing import Any, Iterable

import requests

from src.rag import llm_pura

MODO = "modo_b_rag"
VERSAO_PROMPT = "2026-11-12"
MODELO_RESERVA = "texto-fixo-sem-llm"

PROMPT_SISTEMA = (
    "Você é um assistente que recomenda rolês (bares, restaurantes, cafés, eventos e passeios) no Distrito "
    "Federal: Brasília e as regiões administrativas. Responda em português do Brasil, em até 150 palavras. "
    "Recomende no máximo 3 lugares e, para cada um, informe: nome, região administrativa, endereço, preço médio "
    "por pessoa em R$ e horário de funcionamento. Use apenas os documentos [FONTE #n] enviados junto com a "
    "pergunta, que vêm de uma base auditada de lugares do DF, e cite a fonte de cada lugar como [FONTE #n]. "
    "Não use conhecimento de fora dos documentos. Se nenhum documento atender ao pedido, diga que a base não tem "
    "um lugar que atenda. Não invente informações: se um dado não estiver nos documentos, diga que não sabe."
)

CAMPOS_DOCUMENTO = (
    ("Nome", "nome"),
    ("Tipo", "tipo_de_role"),
    ("Região administrativa", "regiao_administrativa"),
    ("Endereço", "endereco"),
    ("Horário de funcionamento", "horario_funcionamento"),
    ("Faixa de preço", "faixa_de_preco"),
    ("Descrição", "resumo_sensorial"),
)


def _custo(lugar: dict) -> float | None:
    """Custo médio por pessoa como número, ou None se a base não tiver o valor (nunca um padrão inventado)."""
    try:
        valor = lugar.get("custo_medio_rs")
        return None if valor in (None, "") else round(float(valor), 2)
    except (TypeError, ValueError):
        return None


def _reais(valor: float) -> str:
    return f"R$ {valor:.2f}".replace(".", ",")


def montar_documentos(lugares: list[dict]) -> str:
    """Os lugares recuperados no formato que o modelo recebe: um bloco `[FONTE #n]` por lugar."""
    blocos = []
    for n, lugar in enumerate(lugares, start=1):
        linhas = [f"[FONTE #{n}]"]
        for rotulo, campo in CAMPOS_DOCUMENTO:
            valor = str(lugar.get(campo) or "").strip()
            if valor:
                linhas.append(f"{rotulo}: {valor}")
        custo = _custo(lugar)
        if custo is not None:
            linhas.append(f"Preço médio por pessoa: {_reais(custo)}")
        blocos.append("\n".join(linhas))
    return "\n\n".join(blocos)


def montar_mensagem(pergunta: str, lugares: list[dict]) -> str:
    return f"Documentos da base:\n\n{montar_documentos(lugares)}\n\nPergunta: {pergunta}"


def _citadas(resposta: str) -> set[int]:
    """Números citados em [FONTE #1], e também nas formas que o modelo às vezes usa: [FONTES #2 e #3], [FONTE #1, #2]."""
    numeros = set()
    for grupo in re.findall(r"\[\s*FONTES?\s*(#[^\]]*)\]", resposta or "", flags=re.IGNORECASE):
        numeros.update(int(n) for n in re.findall(r"#\s*(\d+)", grupo))
    return numeros


def formatar_fontes(lugares: list[dict], resposta: str = "") -> list[dict]:
    """Fontes no formato do contrato da issue #34. `citada` diz se a resposta usou o marcador [FONTE #n]."""
    citadas = _citadas(resposta)
    return [
        {
            "id": lugar.get("id"),
            "nome": lugar.get("nome"),
            "ra": lugar.get("regiao_administrativa"),
            "custo_medio_rs": _custo(lugar),
            "score_similaridade": lugar.get("score_similaridade"),
            "url_tiktok": lugar.get("tiktok_url") or lugar.get("url_tiktok") or lugar.get("link_tiktok"),
            "citada": n in citadas,
        }
        for n, lugar in enumerate(lugares, start=1)
    ]


def _texto_fixo(pergunta: str, lugares: list[dict]) -> str:
    from src.telemetria.telemetria import _etapa_generation

    return _etapa_generation(pergunta, lugares)


def _reserva(pergunta: str, lugares: list[dict], motivo: str) -> dict:
    resposta = _texto_fixo(pergunta, lugares)
    return llm_pura._resultado(pergunta, modo=MODO, modelo=MODELO_RESERVA, disponivel=False, erro=motivo,
                               resposta=resposta, fontes_utilizadas=formatar_fontes(lugares, resposta))


def _registrar_langfuse(r: dict) -> None:
    try:
        from src.telemetria.telemetria import obter_cliente

        obter_cliente().update_current_generation(
            model=r["modelo"],
            usage_details={"input": r["tokens_entrada"], "output": r["tokens_saida"], "total": r["tokens_total"]},
            cost_details={"total": r["custo_estimado_usd"]},
            metadata={"modo": MODO, "provedor": "OpenRouter", "fontes": len(r["fontes_utilizadas"]),
                      "disponivel": r["disponivel"]},
        )
    except Exception:
        pass


def gerar_resposta_rag(pergunta: str, lugares: list[dict], *, avisos: Iterable[str] = (), usar_cache: bool = True,
                       registrar: bool = True, sessao=None, raciocinio: str | None = None) -> dict:
    """Pergunta + lugares recuperados -> resposta do LLM ancorada nesses lugares.

    `lugares`: saída de `recuperar_com_guardrails` (vazia quando um guardrail bloqueou; aí não há chamada ao LLM).
    `avisos`: avisos dos guardrails (ex.: conflito entre "luxo" e teto baixo), postos antes da resposta.
    `usar_cache`, `registrar`, `sessao` e `raciocinio`: como em `gerar_resposta_llm_pura`. A chave do cache
    inclui os ids dos lugares e o raciocínio, então a mesma pergunta com outra recuperação gera outra chamada.
    """
    pergunta = (pergunta or "").strip()
    avisos = [a for a in avisos if a]
    if not pergunta:
        return llm_pura._resultado(pergunta, modo=MODO, modelo=None, disponivel=False, erro="pergunta vazia",
                                   resposta="Nenhuma pergunta foi enviada.")
    if not lugares:  # guardrail bloqueou: a recusa é a resposta certa, e o LLM não é chamado
        return llm_pura._resultado(pergunta, modo=MODO, modelo=None,
                                   resposta=" ".join(avisos) or "Nenhum lugar da base atende ao pedido.")
    from src.telemetria import logger_metricas as lm

    nivel = llm_pura._nivel(raciocinio)
    parametros = {"modelo": llm_pura._modelo(), "prompt": VERSAO_PROMPT, "lugares": [l.get("id") for l in lugares],
                  "raciocinio": nivel}
    if usar_cache:
        item = lm.obter_cache_avaliacao(pergunta, MODO, parametros)
        if item and isinstance(item.get("resposta"), dict):
            return {**item["resposta"], "cache_hit": True, "latencia_ms": 0.0}

    chave = llm_pura.segredo(llm_pura.CHAVE_ENV)
    if not chave:
        r = _reserva(pergunta, lugares, f"sem {llm_pura.CHAVE_ENV}")
    else:
        r = llm_pura._chamar(pergunta, chave, sessao or requests.Session(), nivel, sistema=PROMPT_SISTEMA,
                             usuario=montar_mensagem(pergunta, lugares), modo=MODO)
        if r["disponivel"]:
            r["fontes_utilizadas"] = formatar_fontes(lugares, r["resposta"])
        else:
            r = _reserva(pergunta, lugares, r["erro"])
    if avisos:
        r["resposta"] = " ".join(avisos) + " " + r["resposta"]
    _registrar_langfuse(r)
    if r["disponivel"]:
        if usar_cache:
            lm.salvar_cache_avaliacao(pergunta, r, MODO, r["tokens_total"], r["latencia_ms"], parametros)
        if registrar:
            lm.registrar_evento_metrica(MODO, r["latencia_ms"], r["tokens_total"], r["custo_estimado_brl"],
                                        cache_hit=False, consulta=pergunta,
                                        metadados={"modelo": r["modelo"], "provedor": r["provedor"],
                                                   "fontes": len(lugares)})
    return r


try:  # trace no Langfuse quando houver chaves; sem elas, a função roda igual
    from langfuse import observe

    gerar_resposta_rag = observe(name="modo_b_rag_geracao", as_type="generation")(gerar_resposta_rag)
except Exception:  # pragma: no cover
    pass
