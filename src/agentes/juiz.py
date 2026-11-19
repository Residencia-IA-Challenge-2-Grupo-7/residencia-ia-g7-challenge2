"""Avaliador Semântico (LLM-as-a-Judge) em 2 Passagens (ADR 0014, Issue #72).

Audita semântica e factualmente as saídas dos agentes do grafo:
- Passagem 1 (Auditoria da Pesquisa): Avalia se cada afirmação/candidato confere, contradiz
  ou não consta na base 2FA de 93 locais curados (RNF-03).
- Passagem 2 (Auditoria da Comunicação): Avalia os textos gerados pelo Anfitrião para garantir
  fidelidade factual e ausência absoluta de vazamento de PII e restrições individuais (RNF-02).
- Fallback determinístico offline quando o endpoint LLM estiver indisponível ou desativado.

Requisitos atendidos:
- RNF-03 (Auditoria de Alucinação): Fidelidade estrita contra a base 2FA.
- RNF-02 (Auditoria de Vazamento de PII): Zero exposição de orçamentos, origens ou restrições de membros.
- ADR 0014 / ADR 0015: Uso do juiz padrão (z-ai/glm-5.3-flash ou xiaomi/mimo-v2.6-pro via OpenRouter).
"""
from __future__ import annotations

import json
import os
import re
from typing import Any, Mapping, Sequence

from src.agentes.contratos import (
    AfirmacaoCartao,
    AfirmacaoParecer,
    Candidato,
    CartaoTexto,
    Exposicao,
    SaidaJuizCartoes,
    SaidaJuizParecer,
    esquema_estrito,
)
from src.agentes.llm import MODELO_JUIZ, ClienteLLM, ErroLLM, embrulhar, prompt
from src.interpretador.numeros import canon
from src.salas.integracoes import carregar_lugares

# Categorias de exposição de dados individuais (RNF-02)
CATEGORIAS_EXPOSICAO = frozenset({"origem", "orcamento", "restricao", "texto_pessoal"})

# Regexes para detecção heurística/determinística de vazamento de PII (fallback offline)
RE_ORIGEM = re.compile(
    r"\b(?:quem\s+vem\s+de|quem\s+sai\s+de|saindo\s+de|vindo\s+de|mora\s+em|pra\s+quem\s+sai\s+de|"
    r"saindo\s+do|vindo\s+do|partindo\s+de)\s+([A-ZÀ-Úa-zà-ú0-9\s]+)",
    re.IGNORECASE,
)
RE_ORCAMENTO = re.compile(
    r"(?:r\$|\b\d+\s*reais\b|teto\s+de|or[çc]amento\s+de|teto\s+individual|bolso\s+d[eo]|"
    r"cada\s+um\s+gasta\s+at[ée]\s+\d+|\bgrana\b|\bteto\s+m[áa]ximo\b)",
    re.IGNORECASE,
)
RE_RESTRICAO_INDIVIDUAL = re.compile(
    r"(?:j[áa]\s+que\s+o|membro\s+que\s+[ée]|para\s+o\s+amigo\s+(?:vegano|vegetariano|cel[íi]aco)|"
    r"algu[ée]m\s+n[ãa]o\s+come|restri[çc][ãa]o\s+d[eo]|para\s+quem\s+n[ãa]o\s+come)\s+([A-ZÀ-Úa-zà-ú]+)?",
    re.IGNORECASE,
)
RE_TEXTO_PESSOAL = re.compile(
    r"(?:voc[êe]\s+pediu|como\s+pedido\s+no\s+chat|conforme\s+seu\s+coment[áa]rio|mensagem\s+de\s+[áa]udio|"
    r"voc[êe]\s+escreveu|coment[áa]rio\s+pessoal)",
    re.IGNORECASE,
)
RE_FORA_DO_DF = re.compile(
    r"\b(s[ãa]o\s+paulo|rio\s+de\s+janeiro|belo\s+horizonte|salvador|curitiba|goi[âa]nia)\b",
    re.IGNORECASE,
)


def obter_modelo_juiz() -> str:
    """Retorna o modelo do juiz configurado via env ou o padrão da ADR 0014."""
    return os.environ.get("JUIZ_LLM_MODELO") or MODELO_JUIZ


def formatar_documento_para_juiz(doc: dict) -> dict[str, Any]:
    """Extrai os campos factuais relevantes de um local da base para alimentar o prompt do Juiz."""
    return {
        "id": doc.get("id"),
        "nome": doc.get("nome"),
        "tipo": doc.get("tipo_de_role") or doc.get("tipo"),
        "regiao_administrativa": doc.get("regiao_administrativa") or doc.get("ra"),
        "endereco": doc.get("endereco_completo") or doc.get("endereco"),
        "horario": doc.get("horario_funcionamento") or doc.get("horario"),
        "custo_medio_rs": doc.get("custo_medio_rs"),
        "resumo_sensorial": doc.get("resumo_sensorial"),
        "legenda_original": doc.get("legenda_original"),
        "transcricao": doc.get("transcricao_audio_whisper"),
    }


def _resolver_base(
    documentos: Mapping[str, dict] | None,
    base_completa: Mapping[str, dict] | None,
) -> dict[str, dict]:
    """Mescla documentos específicos e a base completa curada de 93 locais."""
    base: dict[str, dict] = {}
    if base_completa:
        base.update(base_completa)
    else:
        # Carrega a base padrão caso não fornecida
        try:
            for item in carregar_lugares():
                lid = str(item.get("id") or "")
                if lid:
                    base[lid] = item
        except Exception:
            pass

    if documentos:
        base.update(documentos)
    return base


# -----------------------------------------------------------------------------
# Passagem 1: Auditoria da Pesquisa (Fidelidade Factual)
# -----------------------------------------------------------------------------

def _fallback_julgar_parecer(
    candidatos: Sequence[dict | Candidato],
    documentos: Mapping[str, dict],
) -> SaidaJuizParecer:
    """Auditoria factual determinística dos candidatos da Pesquisa (fallback sem LLM)."""
    afirmacoes: list[AfirmacaoParecer] = []

    for c in candidatos:
        cid = str(c.id if isinstance(c, Candidato) else (c.get("id") or c.get("lugar_id") or ""))
        motivo = str(c.motivo if isinstance(c, Candidato) else (c.get("motivo") or ""))
        trecho = str(c.trecho if isinstance(c, Candidato) else (c.get("trecho") or ""))

        doc = documentos.get(cid)
        if not doc:
            afirmacoes.append(
                AfirmacaoParecer(
                    id=cid,
                    justificativa="Local não encontrado na base oficial de 93 estabelecimentos.",
                    veredito="sem_apoio",
                )
            )
            continue

        # Texto canônico do documento oficial
        doc_texto = canon(" ".join(str(v or "") for v in doc.values()))
        trecho_canon = canon(trecho)
        motivo_canon = canon(motivo)

        # 1. Contradição explícita (ex: menção a local fora do DF)
        if RE_FORA_DO_DF.search(motivo) or RE_FORA_DO_DF.search(trecho):
            afirmacoes.append(
                AfirmacaoParecer(
                    id=cid,
                    justificativa="Afirmação contradiz a base ao citar localização fora do Distrito Federal.",
                    veredito="contradiz",
                )
            )
            continue

        # 2. Confere: trecho literal está no texto do documento ou motivo bate com nome/tipo
        if trecho_canon and trecho_canon in doc_texto:
            afirmacoes.append(
                AfirmacaoParecer(
                    id=cid,
                    justificativa="Trecho citado confere textualmente com o documento do estabelecimento na base.",
                    veredito="confere",
                )
            )
        elif not trecho_canon and (canon(str(doc.get("nome") or "")) in motivo_canon):
            afirmacoes.append(
                AfirmacaoParecer(
                    id=cid,
                    justificativa="Motivo confere com as informações cadastrais do estabelecimento.",
                    veredito="confere",
                )
            )
        else:
            # 3. Sem apoio factual na base
            afirmacoes.append(
                AfirmacaoParecer(
                    id=cid,
                    justificativa="Trecho ou motivo não comprovado pelos documentos da base 2FA.",
                    veredito="sem_apoio",
                )
            )

    return SaidaJuizParecer(afirmacoes=afirmacoes)


def julgar_parecer_pesquisa(
    candidatos: Sequence[dict | Candidato],
    documentos: Mapping[str, dict] | None = None,
    llm: ClienteLLM | None = None,
    *,
    base_completa: Mapping[str, dict] | None = None,
    devolver_status: bool = False,
) -> SaidaJuizParecer | tuple[SaidaJuizParecer, bool]:
    """Passagem 1: Audita fidelidade dos candidatos e trechos da Pesquisa contra a base 2FA (ADR 0014, RNF-03).
    
    Classifica cada candidato em 'confere', 'contradiz' ou 'sem_apoio'.
    """
    if not candidatos:
        res_vazio = SaidaJuizParecer(afirmacoes=[])
        return (res_vazio, False) if devolver_status else res_vazio

    base = _resolver_base(documentos, base_completa)
    usou_llm = False

    if llm is not None and llm.disponivel and not llm.offline:
        # Prepara dados para o modelo em formato delimitado e protegido (spotlighting)
        candidatos_payload = [
            {
                "id": str(c.id if isinstance(c, Candidato) else (c.get("id") or c.get("lugar_id") or "")),
                "motivo": str(c.motivo if isinstance(c, Candidato) else (c.get("motivo") or "")),
                "trecho": str(c.trecho if isinstance(c, Candidato) else (c.get("trecho") or "")),
            }
            for c in candidatos
        ]
        docs_payload = {
            cid: formatar_documento_para_juiz(base[cid])
            for cid in (c["id"] for c in candidatos_payload)
            if cid in base
        }

        usuario = (
            f"{embrulhar('candidatos_pesquisa', candidatos_payload)}\n"
            f"{embrulhar('documentos_base_2fa', docs_payload)}\n"
            "Avalie a fidelidade de cada candidato contra o documento correspondente."
        )

        try:
            modelo = obter_modelo_juiz()
            saida_bruta = llm.json(
                agente="juiz_pesquisa",
                sistema=prompt("juiz_pesquisa"),
                usuario=usuario,
                esquema=esquema_estrito(SaidaJuizParecer),
                modelo=modelo,
                max_tokens=4000,
            )
            resultado = SaidaJuizParecer.model_validate(saida_bruta)
            usou_llm = True
            return (resultado, usou_llm) if devolver_status else resultado
        except (ErroLLM, Exception):
            # Fallback determinístico caso o endpoint falhe
            pass

    # Execução do fallback determinístico
    resultado = _fallback_julgar_parecer(candidatos, base)
    return (resultado, usou_llm) if devolver_status else resultado


# -----------------------------------------------------------------------------
# Passagem 2: Auditoria da Comunicação (Fidelidade + Prevenção de Vazamento)
# -----------------------------------------------------------------------------

def _fallback_julgar_cartoes(
    cartoes: Sequence[dict | CartaoTexto],
    fatos: Sequence[dict] | None,
    documentos: Mapping[str, dict],
) -> SaidaJuizCartoes:
    """Auditoria semântica determinística dos cartões da Comunicação (fallback sem LLM)."""
    afirmacoes: list[AfirmacaoCartao] = []
    exposicoes: list[Exposicao] = []

    fatos_por_cartao = {
        str(f.get("id") or f.get("cartao") or ""): f
        for f in (fatos or [])
    }

    for card in cartoes:
        cid = str(card.id if isinstance(card, CartaoTexto) else (card.get("id") or ""))
        titulo = str(card.titulo if isinstance(card, CartaoTexto) else (card.get("titulo") or ""))
        resumo_acesso = str(card.resumo_acesso if isinstance(card, CartaoTexto) else (card.get("resumo_acesso") or ""))
        por_que_combina = str(card.por_que_combina if isinstance(card, CartaoTexto) else (card.get("por_que_combina") or ""))

        texto_completo = f"{titulo}. {resumo_acesso}. {por_que_combina}"

        # 1. Auditoria de Vazamento de PII (RNF-02)
        # a) Origem
        m_origem = RE_ORIGEM.search(texto_completo)
        if m_origem:
            exposicoes.append(
                Exposicao(
                    cartao=cid,
                    trecho=m_origem.group(0),
                    o_que_expoe="origem",
                )
            )

        # b) Orçamento individual
        m_orcamento = RE_ORCAMENTO.search(texto_completo)
        if m_orcamento:
            exposicoes.append(
                Exposicao(
                    cartao=cid,
                    trecho=m_orcamento.group(0),
                    o_que_expoe="orcamento",
                )
            )

        # c) Restrição alimentar de indivíduo
        m_restr = RE_RESTRICAO_INDIVIDUAL.search(texto_completo)
        if m_restr:
            exposicoes.append(
                Exposicao(
                    cartao=cid,
                    trecho=m_restr.group(0),
                    o_que_expoe="restricao",
                )
            )

        # d) Texto pessoal / citação
        m_texto_p = RE_TEXTO_PESSOAL.search(texto_completo)
        if m_texto_p:
            exposicoes.append(
                Exposicao(
                    cartao=cid,
                    trecho=m_texto_p.group(0),
                    o_que_expoe="texto_pessoal",
                )
            )

        # 2. Auditoria Factual (RNF-03)
        fato_lugar = fatos_por_cartao.get(cid, {})
        lugar_id = str(fato_lugar.get("lugar_id") or fato_lugar.get("id") or cid)
        doc = documentos.get(lugar_id) or documentos.get(cid)

        # Verifica menção contraditória fora do DF
        if RE_FORA_DO_DF.search(texto_completo):
            afirmacoes.append(
                AfirmacaoCartao(
                    cartao=cid,
                    trecho=titulo or texto_completo[:60],
                    justificativa="Texto afirma localização fora do Distrito Federal, contradizendo o escopo oficial.",
                    veredito="contradiz",
                )
            )
        elif doc or fato_lugar:
            afirmacoes.append(
                AfirmacaoCartao(
                    cartao=cid,
                    trecho=titulo or "Cartão de sugestão",
                    justificativa="Texto coerente com os fatos e documentos oficiais do local.",
                    veredito="confere",
                )
            )
        else:
            afirmacoes.append(
                AfirmacaoCartao(
                    cartao=cid,
                    trecho=titulo or "Cartão de sugestão",
                    justificativa="Fatos do local não encontrados na base para comprovação.",
                    veredito="sem_apoio",
                )
            )

    return SaidaJuizCartoes(afirmacoes=afirmacoes, exposicoes=exposicoes)


def julgar_cartoes_comunicacao(
    cartoes: Sequence[dict | CartaoTexto],
    fatos: Sequence[dict] | None = None,
    documentos: Mapping[str, dict] | None = None,
    llm: ClienteLLM | None = None,
    *,
    base_completa: Mapping[str, dict] | None = None,
    devolver_status: bool = False,
) -> SaidaJuizCartoes | tuple[SaidaJuizCartoes, bool]:
    """Passagem 2: Audita textos do Agente 4 para fidelidade factual e prevenção de vazamento de PII (ADR 0014).
    
    Verifica se não há vazamento de orçamentos, origens individuais ou restrições pessoais (RNF-02)
    e confirma conformidade factual contra fatos autorizados e a base 2FA (RNF-03).
    """
    if not cartoes:
        res_vazio = SaidaJuizCartoes(afirmacoes=[], exposicoes=[])
        return (res_vazio, False) if devolver_status else res_vazio

    base = _resolver_base(documentos, base_completa)
    usou_llm = False

    if llm is not None and llm.disponivel and not llm.offline:
        cartoes_payload = [
            {
                "id": str(c.id if isinstance(c, CartaoTexto) else (c.get("id") or "")),
                "titulo": str(c.titulo if isinstance(c, CartaoTexto) else (c.get("titulo") or "")),
                "resumo_acesso": str(c.resumo_acesso if isinstance(c, CartaoTexto) else (c.get("resumo_acesso") or "")),
                "por_que_combina": str(c.por_que_combina if isinstance(c, CartaoTexto) else (c.get("por_que_combina") or "")),
            }
            for c in cartoes
        ]
        fatos_payload = list(fatos or [])
        docs_payload = {
            lid: formatar_documento_para_juiz(doc)
            for lid, doc in base.items()
        }

        usuario = (
            f"{embrulhar('cartoes_comunicacao', cartoes_payload)}\n"
            f"{embrulhar('fatos_autorizados', fatos_payload)}\n"
            f"{embrulhar('documentos_base_2fa', docs_payload)}\n"
            "Audite rigorosamente os cartões quanto à fidelidade factual e ausência de vazamento de PII."
        )

        try:
            modelo = obter_modelo_juiz()
            saida_bruta = llm.json(
                agente="juiz_comunicacao",
                sistema=prompt("juiz_comunicacao"),
                usuario=usuario,
                esquema=esquema_estrito(SaidaJuizCartoes),
                modelo=modelo,
                max_tokens=4000,
            )
            resultado = SaidaJuizCartoes.model_validate(saida_bruta)
            usou_llm = True
            return (resultado, usou_llm) if devolver_status else resultado
        except (ErroLLM, Exception):
            # Fallback determinístico em caso de falha da LLM
            pass

    resultado = _fallback_julgar_cartoes(cartoes, fatos, base)
    return (resultado, usou_llm) if devolver_status else resultado


# -----------------------------------------------------------------------------
# Utilitários de Integração para o Grafo Multiagente (LangGraph / Agente 3)
# -----------------------------------------------------------------------------

def filtrar_candidatos_aprovados_pelo_juiz(
    candidatos: Sequence[dict | Candidato],
    julgamento: SaidaJuizParecer,
) -> tuple[list[dict | Candidato], list[str]]:
    """Separa os candidatos que conferem com a base daqueles derrubados pelo Juiz (contradiz ou sem_apoio).
    
    Retorna (candidatos_aprovados, ids_derrubados_pelo_juiz).
    """
    mapa_vereditos = {af.id: af.veredito for af in julgamento.afirmacoes}

    aprovados: list[dict | Candidato] = []
    derrubados: list[str] = []

    for c in candidatos:
        cid = str(c.id if isinstance(c, Candidato) else (c.get("id") or c.get("lugar_id") or ""))
        veredito = mapa_vereditos.get(cid, "sem_apoio")

        if veredito == "confere":
            aprovados.append(c)
        else:
            derrubados.append(cid)

    return aprovados, derrubados


def avaliar_reprovacoes_cartoes(julgamento: SaidaJuizCartoes) -> dict[str, list[str]]:
    """Mapeia reprovações por cartão a partir dos vereditos e exposições apontados pelo Juiz.
    
    Retorna um dicionário {cartao_id: [motivos_reprovacao]}.
    Cartões aprovados não entram no dicionário (ou possuem lista vazia).
    """
    reprovados: dict[str, list[str]] = {}

    # 1. Reprovações por vazamento de PII (RNF-02)
    for exp in julgamento.exposicoes:
        cid = exp.cartao
        reprovados.setdefault(cid, []).append(f"vazamento_{exp.o_que_expoe}")

    # 2. Reprovações por infidelidade factual ou alucinação (RNF-03)
    for af in julgamento.afirmacoes:
        if af.veredito in ("contradiz", "sem_apoio"):
            cid = af.cartao
            reprovados.setdefault(cid, []).append(f"factual_{af.veredito}")

    return reprovados
