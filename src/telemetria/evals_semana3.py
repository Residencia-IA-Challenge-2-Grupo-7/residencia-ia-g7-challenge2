"""Motor de Avaliação Automatizada Híbrida da Semana 3 (issue #36).

Combina:
1. **Etapa 1 — Verificação Determinística em Código (RNF-04):**
   Confere se os locais citados existem nos 93 registros de `data/banco_aprovado_2fa.json`,
   se a Região Administrativa corresponde à `ra_esperada` e se os preços citados respeitam
   `preco_maximo_gabarito` e os valores oficiais da base.
2. **Etapa 2 — Avaliação Semântica LLM-as-a-Judge (RNF-03):**
   Usa o modelo `xiaomi/mimo-v2.6-pro` pela OpenRouter (família diferente do DeepSeek V4.1 Flash
   avaliado nos Modos A e B) com temperatura 0, roteamento sem retenção de dados e saída em JSON
   para julgar cada afirmação de lugar, preço, endereço e horário como:
   - `"confere com a base"`
   - `"contradiz a base"`
   - `"não está na base"`
   Quando sem chave ou offline, opera com fallback determinístico completo.
3. **4 Scores Padronizados (0.0 a 1.0):**
   - `fidelidade_factual_rnf03`
   - `taxa_alucinacao`
   - `precisao_geoespacial_ra`
   - `sla_latencia_rnf14`
4. **Métricas da Busca (Sem LLM):**
   - `recall_at_k`, `mrr`, `recusa_correta` e `recusa_indevida`.
5. **Integração Langfuse Cloud v5.x:**
   Registra os scores automaticamente no trace ativo via `client.create_score()`.
"""
from __future__ import annotations

import json
import os
import re
import time
import unicodedata
from pathlib import Path
from typing import Any

import requests

from src.interpretador.config import CFG, segredo
from src.telemetria.telemetria import carregar_base_oficial_leticia, obter_cliente

MODELO_JUIZ_PADRAO = "xiaomi/mimo-v2.6-pro"
URL_OPENROUTER = CFG["llm"]["url"]
CHAVE_ENV = CFG["llm"]["chave_env"]
ROTEAMENTO = dict(CFG["llm"]["roteamento"])
SLA_LATENCIA_MAX_MS = 5000.0
TIMEOUT_JUIZ_S = 40  # o MiMo raciocina antes do JSON

VEREDITOS_VALIDOS = ("confere com a base", "contradiz a base", "não está na base")

PROMPT_SISTEMA_JUIZ = (
    "Você é um auditor factual rigoroso (LLM-as-a-Judge) avaliando respostas sobre estabelecimentos "
    "e rolês no Distrito Federal (Brasília e regiões administrativas).\n"
    "Compare a resposta avaliada exclusivamente contra o GABARITO e os DOCUMENTOS DA BASE 2FA fornecidos.\n"
    "Para cada afirmação sobre lugar, preço, endereço ou horário feita na resposta, classifique o campo "
    "`veredito` estritamente com um destes três valores exatos:\n"
    '- "confere com a base"\n'
    '- "contradiz a base"\n'
    '- "não está na base"\n\n'
    "Regras de julgamento:\n"
    "1. Se a resposta inventar nome de estabelecimento, quadra, rua, endereço, preço ou horário que não "
    'conste nos documentos da base 2FA, classifique como "não está na base" ou "contradiz a base".\n'
    "2. Se a pergunta for sobre cidade fora do DF (ex.: Rio de Janeiro, São Paulo) e a resposta recomendar "
    'locais fora do DF sem recusar o escopo, classifique como "não está na base".\n'
    "3. Se a pergunta for fora do DF e a resposta recusar educadamente informando que o app cobre apenas o DF, "
    'classifique como "confere com a base".\n'
    "4. Responda APENAS com um objeto JSON válido no formato:\n"
    '{"afirmacoes": [{"tipo": "lugar|preco|endereco|horario", "trecho": "...", '
    '"veredito": "confere com a base|contradiz a base|não está na base", "justificativa": "..."}], '
    '"resumo_juiz": "..."}'
)

# Palavras genéricas ou nomes de regiões que não devem ser confundidos com nomes de estabelecimentos inventados
_TERMOS_IGNORADOS_NOMES = {
    "brasilia", "distrito federal", "df", "plano piloto", "asa sul", "asa norte",
    "taguatinga", "taguatinga norte", "taguatinga sul", "aguas claras", "guara",
    "riacho fundo", "riacho fundo 1", "riacho fundo i", "samambaia", "ceilandia",
    "gama", "sobradinho", "planaltina", "lago sul", "lago norte", "sudoeste",
    "noroeste", "octogonal", "cruzeiro", "setor comercial sul", "setor hoteleiro",
    "copacabana", "rio de janeiro", "pinheiros", "sao paulo", "goiania",
    "google maps", "instagram", "tiktok", "whatsapp", "uber", "metro", "ifood",
    "segunda", "terca", "quarta", "quinta", "sexta", "sabado", "domingo",
    "fonte", "observacao", "sugestao", "sugestoes", "endereco", "preco", "horario",
    "descricao", "funcionamento", "preco medio", "preco medio por pessoa",
    "regiao administrativa", "opcoes", "opcao", "resumo", "detalhes", "ambiente",
    "faixa de preco", "tipo de role", "vibe", "vibes", "localizacao", "contato",
}


def _modelo_juiz() -> str:
    return (os.environ.get("JUIZ_LLM_MODELO") or MODELO_JUIZ_PADRAO).strip()


def _normalizar(texto: str | None) -> str:
    """Remove acentos, converte para minúsculas e normaliza espaços."""
    if not texto:
        return ""
    sem_acento = "".join(
        c for c in unicodedata.normalize("NFD", str(texto))
        if unicodedata.category(c) != "Mn"
    )
    sem_acento = re.sub(r"[^\w\s]", " ", sem_acento.lower())
    return re.sub(r"\s+", " ", sem_acento).strip()


def _extrair_precos_reais(texto: str) -> list[float]:
    """Extrai valores monetários no formato R$ XX,XX ou R$ XX do texto."""
    if not texto:
        return []
    padrao = re.findall(r"r\$\s*(\d{1,4}(?:[.,]\d{1,2})?)", texto.lower())
    valores: list[float] = []
    for p in padrao:
        try:
            valores.append(float(p.replace(",", ".")))
        except ValueError:
            pass
    return valores


def _eh_recusa_ou_abstencao(resposta: str) -> bool:
    """Identifica se o texto é uma recusa de guardrail ou abstenção explícita sem recomendação."""
    norm = _normalizar(resposta)
    if not norm:
        return True
    sinais_recusa = (
        "fora da cobertura",
        "cobre apenas o distrito federal",
        "cobre somente o distrito federal",
        "so cobre o distrito federal",
        "apenas no distrito federal",
        "nenhum lugar foi recomendado",
        "nao encontrei na base",
        "nao ha opcao na base",
        "nao temos lugares",
        "nao consigo ajudar com",
        "meu foco e o distrito federal",
        "nao tenho certeza de",
        "prefiro nao inventar",
        "llm pura indisponivel",
        "nao foi possivel consultar",
    )
    return any(s in norm for s in sinais_recusa)


def _tokens_ra(ra_esperada: str | None) -> list[str]:
    """Extrai variantes normalizadas da RA esperada (ex.: 'Plano Piloto (Asa Sul)' -> ['plano piloto', 'asa sul'])."""
    if not ra_esperada:
        return []
    partes = re.split(r"[()/,-]", ra_esperada)
    tokens = [_normalizar(p) for p in partes if _normalizar(p)]
    full = _normalizar(ra_esperada)
    if full and full not in tokens:
        tokens.append(full)
    return tokens


def _extrair_candidatos_locais_texto(resposta: str, nomes_base_norm: dict[str, dict]) -> tuple[list[dict], list[str]]:
    """Identifica estabelecimentos da base oficial citados no texto e possíveis estabelecimentos inventados."""
    norm_resp = _normalizar(resposta)
    encontrados_base: list[dict] = []
    vistos_nomes: set[str] = set()

    for nome_norm, item in nomes_base_norm.items():
        if not nome_norm or len(nome_norm) < 3:
            continue
        if re.search(rf"\b{re.escape(nome_norm)}\b", norm_resp):
            if item["nome"] not in vistos_nomes:
                encontrados_base.append(item)
                vistos_nomes.add(item["nome"])

    # Procura candidatos destacados em negrito **Nome** ou listas numeradas "1. Nome —"
    candidatos_brutos: list[str] = []
    for m in re.finditer(r"\*\*([^*]{3,55})\*\*", resposta):
        candidatos_brutos.append(m.group(1).strip())
    for m in re.finditer(
        r"(?:^|\n)\s*\d+[.)]\s*\*?\*?([A-ZÀ-Ú][A-Za-zÀ-ú0-9\s'&.-]{2,45}?)(?:\*?\*?\s*(?:—|–|-|:|\(|\[|\n))",
        resposta,
    ):
        candidatos_brutos.append(m.group(1).strip())
    for m in re.finditer(r"'([^']{3,45})'", resposta):
        cand = m.group(1).strip()
        if cand and cand[0].isupper():
            candidatos_brutos.append(cand)

    inventados: list[str] = []
    for cand in candidatos_brutos:
        cand_limpo = re.sub(r"\s*\([^)]*\)\s*$", "", cand).strip(" :-—–•*")
        cand_norm = _normalizar(cand_limpo)
        if not cand_norm or len(cand_norm) < 3:
            continue
        # Nome de lugar: começa com maiúscula/dígito, uma linha só, sem fim de frase e com poucas palavras.
        # Pares de ** desalinhados capturam trechos como "sushi, à noite, em Samambaia). Veja o que existe:".
        if (not (cand_limpo[0].isupper() or cand_limpo[0].isdigit()) or "\n" in cand_limpo
                or re.search(r"[.!?;)]\s", cand_limpo) or len(cand_limpo.split()) > 7):
            continue
        if cand_norm in _TERMOS_IGNORADOS_NOMES:
            continue
        if any(cand_norm.startswith(prefixo) for prefixo in (
            "onde ", "para ", "como ", "busque ", "veja ", "confira ", "considere ",
            "observacao", "nota", "aviso", "dica", "sugestao", "horario", "preco", "endereco",
            "descricao", "regiao ", "rodizio de ", "opcoes em ", "comercio da ", "bares em ",
            "restaurantes ", "hamburguerias ", "pizzarias ",
        )):
            continue
        # Verifica se coincide com algum nome da base (parcial ou exato)
        bate_base = False
        for nome_norm in nomes_base_norm:
            if cand_norm == nome_norm or cand_norm in nome_norm or nome_norm in cand_norm:
                bate_base = True
                break
        if not bate_base and cand_limpo not in inventados:
            inventados.append(cand_limpo)

    return encontrados_base, inventados


def _detectar_endereco_inventado_ou_contraditorio(
    resposta: str,
    locais_base_citados: list[dict],
    locais_inventados: list[str],
) -> bool:
    """Detecta se a resposta afirma um endereço específico que não pertence aos locais da base."""
    norm_resp = _normalizar(resposta)
    # Padrões típicos de endereços/quadras em Brasília ou outras cidades
    padrao_endereco = re.search(
        r"\b(sqn|sqs|scln|scls|cln|cls|shcgn|shces|eqnl|qnm|qnn|qna|qnb|qnc|qnd|qne|qnf|qng|qnh|"
        r"qi\s*\d+|ql\s*\d+|quadra\s+\d+|bloco\s+[a-z0-9]|lote\s+\d+|loja\s+\d+|"
        r"rua\s+[a-z]+|av\.\s+[a-z]+|avenida\s+[a-z]+)\b",
        norm_resp,
    )
    if not padrao_endereco:
        return False

    if locais_inventados and not locais_base_citados:
        return True

    if not locais_base_citados:
        return True

    # Verifica se os elementos de quadra/lote citados conferem com algum endereço real dos locais citados
    enderecos_reais_norm = " ".join(_normalizar(loc.get("endereco", "")) for loc in locais_base_citados)
    quadras_citadas = re.findall(
        r"\b(?:sqn|sqs|scln|scls|cln|cls|eqnl|qnm|qnn|qna|qnb|qnc|qnd|qne|qnf|quadra)\s*\d+\b",
        norm_resp,
    )
    for q in quadras_citadas:
        if q not in enderecos_reais_norm:
            return True

    return False


def verificar_deterministico_rnf04(
    pergunta: str,
    gabarito: dict | None,
    resultado_modo: dict,
    base_2fa: list[dict] | None = None,
) -> dict[str, Any]:
    """Etapa 1 (RNF-04): Verificação determinística em Python contra os 93 locais da base 2FA e o gabarito."""
    base = base_2fa if base_2fa is not None else carregar_base_oficial_leticia()
    nomes_base_norm: dict[str, dict] = {}
    for item in base:
        nome = item.get("nome")
        if nome:
            nomes_base_norm[_normalizar(nome)] = item

    resposta = str(resultado_modo.get("resposta") or "")
    fontes = resultado_modo.get("fontes_utilizadas") or []
    guardrails = resultado_modo.get("guardrails") or {}
    bloqueado_guardrail = (guardrails.get("permitido") is False)

    gabarito = gabarito or {}
    categoria = gabarito.get("categoria") or ""
    ra_esperada = gabarito.get("ra_esperada")
    locais_gabarito = gabarito.get("locais_gabarito") or []
    preco_maximo_gab = gabarito.get("preco_maximo_gabarito")
    fora_de_escopo = (categoria == "fora_de_escopo_df") or (ra_esperada is None and len(locais_gabarito) == 0 and bool(categoria))

    locais_base_citados, locais_inventados = _extrair_candidatos_locais_texto(resposta, nomes_base_norm)
    nomes_citados_base = [loc["nome"] for loc in locais_base_citados]

    # Também considera fontes marcadas com citada=True que pertençam à base
    for f in fontes:
        if f.get("citada") and f.get("nome"):
            f_norm = _normalizar(f["nome"])
            if f_norm in nomes_base_norm and f["nome"] not in nomes_citados_base:
                locais_base_citados.append(nomes_base_norm[f_norm])
                nomes_citados_base.append(f["nome"])

    norm_resp = _normalizar(resposta)
    locais_gab_norm = [_normalizar(n) for n in locais_gabarito if n]
    acertou_local_gabarito = any(
        re.search(rf"\b{re.escape(g_norm)}\b", norm_resp)
        for g_norm in locais_gab_norm
    )

    # Checagem de RA
    tokens_ra_esp = _tokens_ra(ra_esperada)
    if fora_de_escopo:
        recusou = bloqueado_guardrail or (
            len(locais_inventados) == 0
            and (_eh_recusa_ou_abstencao(resposta) or "distrito federal" in norm_resp or "brasilia" in norm_resp)
        )
        ra_correta = recusou
    elif tokens_ra_esp:
        mencionou_ra = any(t in norm_resp for t in tokens_ra_esp)
        local_na_ra = any(
            any(t in _normalizar(loc.get("regiao_administrativa", "")) for t in tokens_ra_esp)
            for loc in locais_base_citados
        )
        ra_correta = bool((mencionou_ra or local_na_ra) and len(locais_base_citados) > 0)
    else:
        ra_correta = len(locais_base_citados) > 0 and len(locais_inventados) == 0

    # Checagem de Preços
    precos_citados = _extrair_precos_reais(resposta)
    precos_base_citados = [
        float(loc["custo_medio_rs"])
        for loc in locais_base_citados
        if loc.get("custo_medio_rs") is not None
    ]

    preco_contradiz = False
    preco_confere = False
    if precos_citados:
        if locais_base_citados:
            alvos_preco = list(precos_base_citados)
            if preco_maximo_gab is not None:
                alvos_preco.append(float(preco_maximo_gab))
            bate_algum = any(
                any(abs(p - alvo) <= 1.5 for alvo in alvos_preco)
                for p in precos_citados
            )
            if bate_algum:
                preco_confere = True
            else:
                preco_contradiz = True
        elif not _eh_recusa_ou_abstencao(resposta):
            # Citou preços afirmando recomendação sem citar nenhum local real da base
            preco_contradiz = True

    endereco_inventado = _detectar_endereco_inventado_ou_contraditorio(
        resposta, locais_base_citados, locais_inventados
    )
    omissao_pura = (
        not fora_de_escopo
        and len(locais_base_citados) == 0
        and len(locais_inventados) == 0
        and not endereco_inventado
        and not preco_contradiz
        and (bloqueado_guardrail or _eh_recusa_ou_abstencao(resposta))
    )

    # Construção determinística das afirmações auditadas
    afirmacoes_det: list[dict[str, str]] = []

    if fora_de_escopo:
        if ra_correta and len(locais_inventados) == 0:
            afirmacoes_det.append({
                "tipo": "lugar",
                "trecho": resposta[:120],
                "veredito": "confere com a base",
                "justificativa": "Recusou corretamente pergunta fora do escopo geográfico do DF.",
            })
        else:
            afirmacoes_det.append({
                "tipo": "lugar",
                "trecho": (locais_inventados[0] if locais_inventados else resposta[:120]),
                "veredito": "não está na base",
                "justificativa": "Citou estabelecimentos fora da base 2FA ou não recusou escopo fora do DF.",
            })
    elif omissao_pura:
        afirmacoes_det.append({
            "tipo": "lugar",
            "trecho": resposta[:120] or "(abstenção)",
            "veredito": "confere com a base" if bloqueado_guardrail else "não está na base",
            "justificativa": "Abstenção sem inventar estabelecimentos (omissão sem alucinação).",
        })
    else:
        for loc in locais_base_citados:
            afirmacoes_det.append({
                "tipo": "lugar",
                "trecho": loc["nome"],
                "veredito": "confere com a base",
                "justificativa": f"Estabelecimento '{loc['nome']}' existe nos 93 locais auditados 2FA.",
            })
        for inv in locais_inventados:
            afirmacoes_det.append({
                "tipo": "lugar",
                "trecho": inv,
                "veredito": "não está na base",
                "justificativa": f"Local '{inv}' não consta nos 93 registros de data/banco_aprovado_2fa.json.",
            })
        if endereco_inventado:
            afirmacoes_det.append({
                "tipo": "endereco",
                "trecho": "Endereço citado na resposta",
                "veredito": "contradiz a base" if locais_base_citados else "não está na base",
                "justificativa": "Endereço ou quadra não confere com o registro oficial da base 2FA.",
            })
        elif locais_base_citados:
            afirmacoes_det.append({
                "tipo": "endereco",
                "trecho": locais_base_citados[0].get("regiao_administrativa", ""),
                "veredito": "confere com a base" if ra_correta else "contradiz a base",
                "justificativa": "Localização conferida contra a RA oficial da base 2FA.",
            })

        if precos_citados and (locais_base_citados or preco_contradiz):
            afirmacoes_det.append({
                "tipo": "preco",
                "trecho": f"R$ {precos_citados[0]:.2f}",
                "veredito": "confere com a base" if preco_confere and not preco_contradiz else "contradiz a base",
                "justificativa": (
                    "Preço compatível com o cadastro 2FA."
                    if preco_confere and not preco_contradiz
                    else "Preço diverge do valor auditado na base 2FA ou pertence a local não cadastrado."
                ),
            })

        if not afirmacoes_det:
            afirmacoes_det.append({
                "tipo": "lugar",
                "trecho": resposta[:120] or "(resposta vazia)",
                "veredito": "não está na base",
                "justificativa": "Nenhum estabelecimento da base 2FA foi recomendado.",
            })

    return {
        "locais_base_citados": nomes_citados_base,
        "locais_inventados": locais_inventados,
        "acertou_local_gabarito": acertou_local_gabarito,
        "ra_correta": ra_correta,
        "preco_confere": preco_confere,
        "preco_contradiz": preco_contradiz,
        "endereco_inventado": endereco_inventado,
        "omissao_pura": omissao_pura,
        "precos_extraidos": precos_citados,
        "fora_de_escopo": fora_de_escopo,
        "bloqueado_guardrail": bloqueado_guardrail,
        "afirmacoes_deterministicas": afirmacoes_det,
    }


def julgar_com_llm_judge(
    pergunta: str,
    gabarito: dict | None,
    resultado_modo: dict,
    verificacao_det: dict,
    base_2fa: list[dict] | None = None,
    *,
    sessao=None,
) -> dict[str, Any]:
    """Etapa 2: Avalia coerência factual via LLM-as-a-Judge (MiMo-V2.6-Pro) com fallback determinístico."""
    chave = segredo(CHAVE_ENV)
    modelo = _modelo_juiz()

    # Monta resumo enxuto dos documentos relevantes da base (fontes recuperadas + gabarito)
    base = base_2fa if base_2fa is not None else carregar_base_oficial_leticia()
    nomes_relevantes = set(verificacao_det.get("locais_base_citados") or [])
    if gabarito and gabarito.get("locais_gabarito"):
        nomes_relevantes.update(gabarito["locais_gabarito"])
    for f in resultado_modo.get("fontes_utilizadas") or []:
        if f.get("nome"):
            nomes_relevantes.add(f["nome"])

    docs_contexto = [
        {
            "nome": item.get("nome"),
            "regiao_administrativa": item.get("regiao_administrativa"),
            "endereco": item.get("endereco"),
            "custo_medio_rs": item.get("custo_medio_rs"),
            "horario_funcionamento": item.get("horario_funcionamento"),
        }
        for item in base
        if item.get("nome") in nomes_relevantes
    ]

    if not chave:
        return {
            "modelo_juiz": modelo,
            "usou_llm": False,
            "motivo_fallback": f"sem {CHAVE_ENV}",
            "afirmacoes": verificacao_det["afirmacoes_deterministicas"],
            "latencia_juiz_ms": 0.0,
        }

    prompt_usuario = json.dumps(
        {
            "pergunta": pergunta,
            "gabarito": gabarito or {},
            "documentos_base_2fa": docs_contexto,
            "resposta_avaliada": resultado_modo.get("resposta") or "",
            "verificacao_deterministica_previa": {
                "locais_base_citados": verificacao_det["locais_base_citados"],
                "locais_inventados": verificacao_det["locais_inventados"],
                "ra_correta": verificacao_det["ra_correta"],
                "preco_contradiz": verificacao_det["preco_contradiz"],
                "endereco_inventado": verificacao_det["endereco_inventado"],
            },
        },
        ensure_ascii=False,
    )

    corpo = {
        "model": modelo,
        "messages": [
            {"role": "system", "content": PROMPT_SISTEMA_JUIZ},
            {"role": "user", "content": prompt_usuario},
        ],
        "temperature": 0,
        "max_tokens": 4000,  # os tokens de raciocínio do MiMo contam no limite; com 900 o JSON vinha cortado
        "response_format": {"type": "json_object"},
        "provider": ROTEAMENTO,
    }

    http = sessao or requests.Session()
    t0 = time.perf_counter()
    try:
        r = http.post(
            URL_OPENROUTER,
            json=corpo,
            timeout=TIMEOUT_JUIZ_S,
            headers={
                "Authorization": f"Bearer {chave}",
                "X-Title": "Orquestrador de Roles - LLM Judge (Residencia IA UnB)",
            },
        )
        ms = round((time.perf_counter() - t0) * 1000, 1)
        if r.status_code >= 400:
            return {
                "modelo_juiz": modelo,
                "usou_llm": False,
                "motivo_fallback": f"HTTP {r.status_code}",
                "afirmacoes": verificacao_det["afirmacoes_deterministicas"],
                "latencia_juiz_ms": ms,
            }
        dados = r.json()
        conteudo = (dados["choices"][0]["message"].get("content") or "").strip()
        # Remove cercas markdown se houver
        if conteudo.startswith("```"):
            conteudo = re.sub(r"^```(?:json)?\s*|\s*```$", "", conteudo, flags=re.DOTALL).strip()
        julgamento = json.loads(conteudo)
        afirmacoes_brutas = julgamento.get("afirmacoes")
        if not isinstance(afirmacoes_brutas, list) or not afirmacoes_brutas:
            raise ValueError("lista de afirmacoes ausente")

        afirmacoes_limpas: list[dict[str, str]] = []
        for af in afirmacoes_brutas:
            if not isinstance(af, dict):
                continue
            veredito = str(af.get("veredito") or "").strip().lower()
            if veredito not in VEREDITOS_VALIDOS:
                if "confere" in veredito:
                    veredito = "confere com a base"
                elif "contradiz" in veredito:
                    veredito = "contradiz a base"
                else:
                    veredito = "não está na base"
            afirmacoes_limpas.append({
                "tipo": str(af.get("tipo") or "geral"),
                "trecho": str(af.get("trecho") or ""),
                "veredito": veredito,
                "justificativa": str(af.get("justificativa") or ""),
            })

        if not afirmacoes_limpas:
            raise ValueError("nenhuma afirmacao valida")

        return {
            "modelo_juiz": dados.get("model") or modelo,
            "usou_llm": True,
            "motivo_fallback": None,
            "afirmacoes": afirmacoes_limpas,
            "resumo_juiz": julgamento.get("resumo_juiz") or "",
            "latencia_juiz_ms": ms,
        }
    except Exception as exc:
        ms = round((time.perf_counter() - t0) * 1000, 1)
        return {
            "modelo_juiz": modelo,
            "usou_llm": False,
            "motivo_fallback": type(exc).__name__,
            "afirmacoes": verificacao_det["afirmacoes_deterministicas"],
            "latencia_juiz_ms": ms,
        }


def _calcular_scores_modo(
    resultado_modo: dict,
    verificacao_det: dict,
    julgamento_juiz: dict,
) -> dict[str, float]:
    """Calcula os 4 scores padronizados (0.0 a 1.0) combinando RNF-04 (determinístico) e o juiz."""
    latencia_ms = float(resultado_modo.get("latencia_ms") or 0.0)
    sla_latencia = 1.0 if latencia_ms <= SLA_LATENCIA_MAX_MS else 0.0
    precisao_ra = 1.0 if verificacao_det["ra_correta"] else 0.0

    afirmacoes = julgamento_juiz.get("afirmacoes") or verificacao_det["afirmacoes_deterministicas"]
    total_af = max(len(afirmacoes), 1)
    conferem = sum(1 for a in afirmacoes if a.get("veredito") == "confere com a base")
    alucinadas = sum(
        1 for a in afirmacoes
        if a.get("veredito") in ("contradiz a base", "não está na base")
    )

    fidelidade_juiz = conferem / total_af
    alucinacao_juiz = alucinadas / total_af

    # Travas determinísticas RNF-04 (código prevalece sobre suavizações indevidas):
    tem_alucinacao_det = bool(
        verificacao_det["locais_inventados"]
        or verificacao_det["preco_contradiz"]
        or verificacao_det["endereco_inventado"]
        or (verificacao_det["fora_de_escopo"] and not verificacao_det["ra_correta"])
    )
    ancorado_2fa_perfeito = bool(
        not tem_alucinacao_det
        and verificacao_det["ra_correta"]
        and (
            verificacao_det["fora_de_escopo"]
            or (
                len(verificacao_det["locais_base_citados"]) > 0
                and (verificacao_det["acertou_local_gabarito"] or verificacao_det["preco_confere"])
            )
        )
    )

    if ancorado_2fa_perfeito and alucinacao_juiz == 0.0:
        fidelidade_final = 1.0
        taxa_alucinacao_final = 0.0
    elif tem_alucinacao_det:
        # Penalidade determinística garantida para respostas que inventam local, endereço ou preço
        penalidade_det = 0.75 if (
            verificacao_det["locais_inventados"]
            and (verificacao_det["preco_contradiz"] or verificacao_det["endereco_inventado"])
        ) else 0.6
        taxa_alucinacao_final = round(max(alucinacao_juiz, penalidade_det), 4)
        fidelidade_final = round(min(fidelidade_juiz, 1.0 - taxa_alucinacao_final), 4)
    else:
        taxa_alucinacao_final = round(alucinacao_juiz, 4)
        fidelidade_final = round(fidelidade_juiz, 4)

    return {
        "fidelidade_factual_rnf03": round(max(0.0, min(1.0, fidelidade_final)), 4),
        "taxa_alucinacao": round(max(0.0, min(1.0, taxa_alucinacao_final)), 4),
        "precisao_geoespacial_ra": round(precisao_ra, 4),
        "sla_latencia_rnf14": round(sla_latencia, 4),
    }


def calcular_metricas_busca(
    gabarito: dict | None,
    resultado_modo_b: dict,
) -> dict[str, Any]:
    """Calcula métricas determinísticas da busca do Modo B (sem LLM):
    `recall_at_k`, `mrr`, `recusa_correta` e `recusa_indevida`.
    """
    gabarito = gabarito or {}
    categoria = gabarito.get("categoria") or ""
    ra_esperada = gabarito.get("ra_esperada")
    locais_gabarito = gabarito.get("locais_gabarito") or []
    evidencia_id = gabarito.get("evidencia_id_tiktok")
    fora_de_escopo = (categoria == "fora_de_escopo_df") or (
        ra_esperada is None and len(locais_gabarito) == 0 and bool(categoria)
    )

    fontes = resultado_modo_b.get("fontes_utilizadas") or []
    guardrails = resultado_modo_b.get("guardrails") or {}
    recusou_busca = (guardrails.get("permitido") is False) or (len(fontes) == 0)

    if fora_de_escopo:
        return {
            "recall_at_k": None,
            "mrr": None,
            "posicao_gabarito": None,
            "recusa_correta": 1.0 if recusou_busca else 0.0,
            "recusa_indevida": 0.0,
        }

    gabarito_norms = {_normalizar(nome) for nome in locais_gabarito if nome}
    posicao_encontrada: int | None = None

    for idx, f in enumerate(fontes, start=1):
        nome_f_norm = _normalizar(f.get("nome"))
        id_f = f.get("id")
        if (evidencia_id and id_f == evidencia_id) or (nome_f_norm and nome_f_norm in gabarito_norms):
            posicao_encontrada = idx
            break

    recall_at_k = 1.0 if posicao_encontrada is not None else 0.0
    mrr = round(1.0 / posicao_encontrada, 4) if posicao_encontrada is not None else 0.0

    return {
        "recall_at_k": recall_at_k,
        "mrr": mrr,
        "posicao_gabarito": posicao_encontrada,
        "recusa_correta": None,
        "recusa_indevida": 1.0 if recusou_busca else 0.0,
    }


def _registrar_scores_langfuse(
    avaliacao: dict[str, Any],
    trace_id: str | None = None,
) -> bool:
    """Registra todos os scores padronizados e métricas de busca no trace ativo do Langfuse Cloud."""
    try:
        client = obter_cliente()
        tid = trace_id or client.get_current_trace_id()
        if not tid:
            return False

        for sufixo, chave_modo in (("modo_a", "modo_a_llm_pura"), ("modo_b", "modo_b_rag")):
            bloco = avaliacao.get(chave_modo) or {}
            scores = bloco.get("scores") or {}
            for nome_score, valor in scores.items():
                if valor is not None:
                    client.create_score(
                        trace_id=tid,
                        name=f"{nome_score}_{sufixo}",
                        value=float(valor),
                        comment=f"Avaliação híbrida Semana 3 ({sufixo})",
                    )
                    if sufixo == "modo_b":
                        # Registra também com o nome canônico principal do RNF no trace
                        client.create_score(
                            trace_id=tid,
                            name=nome_score,
                            value=float(valor),
                            comment="Score oficial do Modo B (RAG Ancorado 2FA)",
                        )

        busca = avaliacao.get("metricas_busca") or {}
        for nome_m in ("recall_at_k", "mrr", "recusa_correta", "recusa_indevida"):
            val = busca.get(nome_m)
            if val is not None:
                client.create_score(
                    trace_id=tid,
                    name=f"busca_{nome_m}",
                    value=float(val),
                    comment="Métrica determinística de recuperação (Modo B)",
                )
        return True
    except Exception:
        return False


def avaliar_par_comparativo(
    pergunta: str | dict[str, Any],
    gabarito: dict[str, Any] | None = None,
    resultado_modo_a: dict[str, Any] | None = None,
    resultado_modo_b: dict[str, Any] | None = None,
    *,
    sessao=None,
    registrar_langfuse: bool = True,
    trace_id: str | None = None,
    base_2fa: list[dict] | None = None,
) -> dict[str, Any]:
    """Avalia um par comparativo Modo A (LLM Pura) vs. Modo B (RAG Ancorado).

    Aceita tanto os 4 argumentos posicionais `(pergunta, gabarito, resultado_modo_a, resultado_modo_b)`
    quanto o dicionário completo retornado por `executar_comparacao_ab()` / `POST /api/comparativo/executar`.
    """
    id_golden = None
    if isinstance(pergunta, dict):
        payload = pergunta
        id_golden = payload.get("id_golden")
        gabarito = payload.get("gabarito") if gabarito is None else gabarito
        resultado_modo_a = payload.get("modo_a_llm_pura") if resultado_modo_a is None else resultado_modo_a
        resultado_modo_b = payload.get("modo_b_rag") if resultado_modo_b is None else resultado_modo_b
        pergunta_str = str(payload.get("pergunta") or "")
    else:
        pergunta_str = str(pergunta or "")

    resultado_modo_a = resultado_modo_a or {}
    resultado_modo_b = resultado_modo_b or {}
    base = base_2fa if base_2fa is not None else carregar_base_oficial_leticia()

    # Etapa 1: Verificação Determinística (RNF-04)
    det_a = verificar_deterministico_rnf04(pergunta_str, gabarito, resultado_modo_a, base)
    det_b = verificar_deterministico_rnf04(pergunta_str, gabarito, resultado_modo_b, base)

    # Etapa 2: LLM-as-a-Judge (MiMo-V2.6-Pro via OpenRouter) com fallback determinístico
    juiz_a = julgar_com_llm_judge(pergunta_str, gabarito, resultado_modo_a, det_a, base, sessao=sessao)
    juiz_b = julgar_com_llm_judge(pergunta_str, gabarito, resultado_modo_b, det_b, base, sessao=sessao)

    # Cálculo dos 4 Scores Padronizados
    scores_a = _calcular_scores_modo(resultado_modo_a, det_a, juiz_a)
    scores_b = _calcular_scores_modo(resultado_modo_b, det_b, juiz_b)

    # Métricas da Busca (sem LLM)
    metricas_busca = calcular_metricas_busca(gabarito, resultado_modo_b)

    avaliacao = {
        "id_golden": id_golden,
        "pergunta": pergunta_str,
        "modelo_juiz": juiz_b.get("modelo_juiz") or _modelo_juiz(),
        "modo_a_llm_pura": {
            "scores": scores_a,
            "verificacao_deterministica": det_a,
            "julgamento_juiz": juiz_a,
        },
        "modo_b_rag": {
            "scores": scores_b,
            "verificacao_deterministica": det_b,
            "julgamento_juiz": juiz_b,
        },
        "metricas_busca": metricas_busca,
        "delta_rag_vs_llm": {
            "ganho_fidelidade": round(scores_b["fidelidade_factual_rnf03"] - scores_a["fidelidade_factual_rnf03"], 4),
            "reducao_alucinacao": round(scores_a["taxa_alucinacao"] - scores_b["taxa_alucinacao"], 4),
            "ganho_precisao_ra": round(scores_b["precisao_geoespacial_ra"] - scores_a["precisao_geoespacial_ra"], 4),
        },
    }

    if registrar_langfuse:
        avaliacao["registrado_langfuse"] = _registrar_scores_langfuse(avaliacao, trace_id=trace_id)
    else:
        avaliacao["registrado_langfuse"] = False

    return avaliacao
