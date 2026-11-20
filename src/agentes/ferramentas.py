"""Ferramentas que os agentes chamam: a busca da Pesquisa, o documento que um LLM pode ler e a conferência do
trecho literal. Tudo em código, sem LLM (RNF-04).

`buscar` recebe a `Consulta` que o agente de Pesquisa escreveu (subconjunto da `ConsultaBusca` do ADR 0007, sem
teto em reais) e devolve os lugares da base de 93 com a pontuação. Não aplica o limiar de aderência do guardrail
1b: numa sala o grupo sempre precisa de candidatos (caso golden_06 da semana 3).
"""
from __future__ import annotations

import re

from src.agentes.contratos import Consulta
from src.interpretador.numeros import canon
from src.salas import integracoes as integ
from src.salas.sugestoes import TERMOS_RESTRICAO
from src.telemetria.telemetria import calcular_similaridade_leticia

TIPOS_DA_BASE = {
    "comer_beber": {"Bar / Boteco / Pub", "Restaurante / Gastronomia", "Cafeteria / Doceria"},
    "ar_livre_gratuito": {"Ao Ar Livre / Parque"},
    "local_evento": {"Experiência / Evento"},
}
CAMPOS_LEGIVEIS = ("nome", "tipo_de_role", "regiao_administrativa", "vibes", "resumo_sensorial")


def documento(lugar: dict) -> dict:
    """O que um agente LLM pode ler de um lugar: sem preço, horário e endereço (esses vão por código) e sem a
    legenda e a transcrição originais do vídeo, que são texto de terceiros e longas."""
    return {"id": lugar["id"], "nome": lugar.get("nome", ""), "tipo": lugar.get("tipo_de_role", ""),
            "regiao_do_lugar": lugar.get("regiao_administrativa", ""), "vibes": list(lugar.get("vibes") or []),
            "descricao": lugar.get("resumo_sensorial") or ""}


def _texto_legivel(lugar: dict) -> str:
    return canon(" ".join(str(lugar.get(k) or "") if k != "vibes" else " ".join(lugar.get("vibes") or [])
                          for k in CAMPOS_LEGIVEIS))


def conferir_trecho(trecho: str, lugar: dict) -> bool:
    """O trecho citado está, literalmente (sem acento e caixa), no documento que o agente recebeu?"""
    t = canon(trecho or "").strip(" .\"'")
    return len(t) >= 4 and t in _texto_legivel(lugar)


def _cumpre(lugar: dict, restricao: str) -> bool:
    rx = TERMOS_RESTRICAO.get(restricao)
    return bool(rx and re.search(rx, canon(" ".join(str(lugar.get(k) or "") for k in
                                                    ("nome", "resumo_sensorial", "legenda_original")))))


def buscar(consulta: Consulta, lugares: list[dict], *, busca: str = "lexica", k: int = 12) -> tuple[list[dict], dict]:
    """(lugares ordenados, metadados da busca). `busca`: "lexica" ou "vetorial" (cai para a léxica sem chave ou
    sem rede, ADR 0012)."""
    meta = {"busca": "lexica", "embedding_ms": 0.0, "custo_usd": 0.0, "erro": None}
    base = list(lugares)
    if consulta.tipos_role:
        tipos = set().union(*(TIPOS_DA_BASE[t] for t in consulta.tipos_role))
        filtrados = [l for l in base if l.get("tipo_de_role") in tipos]
        base = filtrados if len(filtrados) >= 3 else base  # filtro que esvazia a busca vira preferência
    if consulta.ras:
        na_ra = [l for l in base if integ.ra_do_lugar(l) in set(consulta.ras)]
        base = na_ra if na_ra else base

    cos = None
    if busca == "vetorial":
        from src.rag.busca_vetorial import similaridades
        cos, m = similaridades(consulta.texto)
        meta.update(embedding_ms=m.get("latencia_ms", 0.0), custo_usd=m.get("custo_usd", 0.0), erro=m.get("erro"))
        if cos is not None:
            meta["busca"] = "vetorial"

    def nota(l: dict) -> float:
        n = cos.get(l["id"], 0.0) if cos is not None else calcular_similaridade_leticia(consulta.texto, l)
        return n + 0.1 * sum(_cumpre(l, r) for r in consulta.exigir)

    ordem = sorted(base, key=lambda l: -nota(l))[:k]
    return [{**documento(l), "pontuacao": round(nota(l), 4)} for l in ordem], meta
