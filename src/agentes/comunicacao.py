"""Agente 4: Síntese e Comunicação (Issue #69, ADR 0015, docs/semanas/semana-04.md).

Persona: 'Anfitrião de Brasília'.
Responsabilidades:
1. Recebe os candidatos aprovados da Validação (candidatos_validados);
2. Invoca o LLM com o prompt do Anfitrião e saída estrita em JSON (SaidaComunicacao: titulo, resumo_acesso, por_que_combina);
3. Preenche deterministicamente todos os dados financeiros (consumo_estimado_rs, faixa_gasto_rs), tempos de chegada,
   endereço oficial e links do TikTok no esquema Sugestao (RF-06, RNF-04);
4. Garante zero citação de orçamentos individuais, origens de participantes ou restrições de pessoas (RNF-02);
5. Valida os cartões finais via Pydantic / JSON Schema antes da devolução para a sala pública.
"""
from __future__ import annotations

import copy
import re
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from src.agentes.contratos import CartaoTexto, SaidaComunicacao, esquema_estrito
from src.agentes.llm import ClienteLLM, ErroLLM, embrulhar, prompt
from src.interpretador.numeros import canon
from src.salas.integracoes import carregar_lugares
from src.salas.modelos import Sugestao

LETRAS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


# ------------------------------------------------------------------ Pydantic Card Schema
class FaixaGasto(BaseModel):
    model_config = ConfigDict(extra="forbid")
    min: str
    max: str


class CartaoSugestaoValidado(BaseModel):
    """Esquema Pydantic para validação estrita dos cartões finais (RF-06, RNF-03, RNF-04)."""
    model_config = ConfigDict(extra="allow")

    id: str = Field(..., description="Letra do cartão (A, B, C, D)")
    posicao: int = Field(..., ge=1, description="Posição no ranking (1 a 4)")
    lugar_id: str = Field(..., description="ID oficial do local na base 2FA")
    nome: str = Field(..., description="Nome oficial do estabelecimento")
    tipo: str = Field(..., description="Tipo de rolê (ex: Bar, Gastronomia, Café)")
    ra: str | None = Field(default=None, description="Região Administrativa oficial")
    regiao_administrativa: str = Field(..., description="Nome da RA formatado")
    endereco: str = Field(..., description="Endereço oficial completo")
    inicio: str = Field(..., description="Data/hora de início em ISO-8601")
    fim: str = Field(..., description="Data/hora de fim em ISO-8601")
    horario: str = Field(..., description="Texto legível do horário")
    horario_situacao: str = Field(..., description="Situação factual: aberto, provável ou incerto")
    quantos_podem: str = Field(..., description="Contagem pública de confirmação")
    consumo_estimado_rs: str = Field(..., description="Consumo médio estimado por pessoa em R$")
    faixa_gasto_rs: FaixaGasto | dict[str, str] = Field(..., description="Faixa estimada incluindo transporte")
    tempo_medio_chegada_min: int | None = Field(default=None, description="Média de trajeto em minutos")
    tempo_maximo_chegada_min: int | None = Field(default=None, description="Pior trajeto em minutos")
    nota_justica: float = Field(..., description="Nota da Menor Miséria (0 a 100)")
    explicacao: str = Field(..., description="Explicação consolidada para a votação")
    tiktok_url: str | None = Field(default=None, description="Link original do vídeo 2FA")
    fonte: str = Field(..., description="Crédito e data da fonte 2FA")
    vibes: list[str] = Field(default_factory=list, description="Lista de vibes e etiquetas")
    titulo: str = Field(..., description="Título acolhedor gerado pelo Anfitrião")
    resumo_acesso: str = Field(..., description="Resumo de acesso gerado pelo Anfitrião")
    por_que_combina: str = Field(..., description="Motivo de afinidade gerado pelo Anfitrião")


# ------------------------------------------------------------------ Auxiliares de Base
def _mapas_base() -> tuple[dict[str, dict], dict[str, dict]]:
    lugares = carregar_lugares()
    por_id: dict[str, dict] = {}
    por_nome: dict[str, dict] = {}
    for l in lugares:
        lid = str(l.get("id") or "")
        if lid:
            por_id[lid] = l
        vid = str(l.get("video_id") or "")
        if vid:
            por_id[vid] = l
        nome_c = canon(str(l.get("nome") or ""))
        if nome_c:
            por_nome[nome_c] = l
    return por_id, por_nome


def _buscar_lugar(cand: dict | Sugestao, por_id: dict[str, dict], por_nome: dict[str, dict]) -> dict:
    if isinstance(cand, Sugestao):
        return por_id.get(cand.lugar_id) or por_nome.get(canon(cand.nome)) or {}
    cand_id = str(cand.get("lugar_id") or cand.get("id") or "")
    if cand_id in por_id:
        return por_id[cand_id]
    nome_c = canon(str(cand.get("nome") or ""))
    if nome_c in por_nome:
        return por_nome[nome_c]
    return {}


# ------------------------------------------------------------------ Geração do Anfitrião
def _payload_para_llm(candidatos_preparados: list[dict], preferencias_grupo: dict | None = None) -> dict:
    fatos = []
    for c in candidatos_preparados:
        fatos.append({
            "id": c["id"],
            "nome": c["nome"],
            "tipo": c["tipo"],
            "ra": c["regiao_administrativa"],
            "vibes": c["vibes"],
            "resumo_sensorial": c.get("resumo_sensorial", ""),
            "horario_situacao": c["horario_situacao"],
        })
    resultado = {"candidatos": fatos}
    if preferencias_grupo:
        resultado["preferencias_grupo"] = {
            "tipos": preferencias_grupo.get("tipos", []),
            "vibes": preferencias_grupo.get("vibes", []),
            "evitar": preferencias_grupo.get("evitar", []),
        }
    return resultado


def _fallback_textos(cand: dict) -> CartaoTexto:
    nome = cand.get("nome", "Lugar")
    tipo = cand.get("tipo", "Rolê").split(" / ")[0]
    ra = cand.get("regiao_administrativa") or "Brasília"
    vibes = cand.get("vibes") or []
    vibe_txt = ", ".join(vibes[:2]) if vibes else "descontraída"

    titulo = f"{nome} — {tipo} em {ra}"
    resumo_acesso = "Localização bem posicionada no DF com trajeto equilibrado para todo o grupo."
    por_que_combina = f"Ambiente com atmosfera {vibe_txt}, ideal para reunir os amigos com conforto e boas opções."
    return CartaoTexto(id=cand["id"], titulo=titulo, resumo_acesso=resumo_acesso, por_que_combina=por_que_combina)


# ------------------------------------------------------------------ Função Principal
def executar_agente_comunicacao(
    candidatos_validados: list[dict | Any],
    *,
    llm: ClienteLLM | None = None,
    preferencias_grupo: dict | None = None,
    lugares_base: tuple[dict, ...] | None = None,
) -> list[dict]:
    """Agente de Comunicação: redige títulos e justificativas calorosas e monta cartões estritos (RF-06, RNF-02, RNF-04).

    Args:
        candidatos_validados: Lista de candidatos viáveis (instâncias de Sugestao ou dicts avaliados).
        llm: Cliente LLM opcional (usa DeepSeek V4.1 Flash via OpenRouter ou fallback offline).
        preferencias_grupo: Preferências agregadas do grupo (opcional, sem PII).
        lugares_base: Base de lugares alternativa (para testes isolados sem arquivo físico).

    Returns:
        list[dict]: Lista de cartões completos no esquema Sugestao validados por CartaoSugestaoValidado.
    """
    if not candidatos_validados:
        return []

    por_id, por_nome = _mapas_base()
    if lugares_base:
        for l in lugares_base:
            lid = str(l.get("id") or "")
            if lid:
                por_id[lid] = l
            nome_c = canon(str(l.get("nome") or ""))
            if nome_c:
                por_nome[nome_c] = l

    agora = datetime.now()
    preparados = []

    for i, c in enumerate(candidatos_validados):
        letra_id = LETRAS[i] if i < len(LETRAS) else f"C{i+1}"
        if isinstance(c, Sugestao):
            card_dict = copy.deepcopy(c.publico())
            card_dict["id"] = letra_id
            card_dict["posicao"] = i + 1
            lugar_ref = _buscar_lugar(c, por_id, por_nome)
            card_dict["resumo_sensorial"] = lugar_ref.get("resumo_sensorial", "")
            preparados.append(card_dict)
            continue

        c_dict = c if isinstance(c, dict) else (c.model_dump() if hasattr(c, "model_dump") else dict(c))
        lugar = _buscar_lugar(c_dict, por_id, por_nome)

        lugar_id = str(c_dict.get("lugar_id") or lugar.get("id") or c_dict.get("id") or f"cand_{i+1}")
        nome = str(c_dict.get("nome") or lugar.get("nome") or f"Lugar {letra_id}")
        tipo = str(c_dict.get("tipo") or lugar.get("tipo_de_role") or "Rolê")
        ra = c_dict.get("ra") or c_dict.get("ra_do_lugar") or lugar.get("regiao_administrativa")
        regiao_texto = str(c_dict.get("regiao_administrativa") or lugar.get("regiao_administrativa") or ra or "Distrito Federal")
        endereco = str(c_dict.get("endereco") or lugar.get("endereco") or f"{regiao_texto}, Brasília - DF")

        inicio_val = c_dict.get("inicio") or agora
        fim_val = c_dict.get("fim") or (inicio_val + timedelta(hours=3) if isinstance(inicio_val, datetime) else agora + timedelta(hours=3))
        inicio_str = inicio_val.isoformat() if isinstance(inicio_val, datetime) else str(inicio_val)
        fim_str = fim_val.isoformat() if isinstance(fim_val, datetime) else str(fim_val)

        horario = str(c_dict.get("horario") or c_dict.get("horario_texto") or c_dict.get("janela") or "Horário a combinar")
        horario_situacao = str(c_dict.get("horario_situacao") or "aberto")
        quantos_podem = str(c_dict.get("quantos_podem") or c_dict.get("contagem") or "todos podem")

        consumo_num = c_dict.get("consumo_rs") or c_dict.get("consumo_estimado_rs") or lugar.get("custo_medio_rs") or "0.00"
        consumo_rs = Decimal(str(consumo_num)).quantize(Decimal("0.01"))

        fg = c_dict.get("faixa_gasto_rs")
        if isinstance(fg, dict) and "min" in fg and "max" in fg:
            gasto_min = Decimal(str(fg["min"])).quantize(Decimal("0.01"))
            gasto_max = Decimal(str(fg["max"])).quantize(Decimal("0.01"))
        else:
            gasto_min = Decimal(str(c_dict.get("gasto_min", consumo_rs))).quantize(Decimal("0.01"))
            gasto_max = Decimal(str(c_dict.get("gasto_max", consumo_rs))).quantize(Decimal("0.01"))

        tempo_medio = c_dict.get("tempo_medio_chegada_min") or c_dict.get("media_trajeto_min") or c_dict.get("tempo_medio_min")
        tempo_max = c_dict.get("tempo_maximo_chegada_min") or c_dict.get("pior_trajeto_min") or c_dict.get("tempo_max_min")
        tempo_medio_min = int(tempo_medio) if tempo_medio is not None else None
        tempo_max_min = int(tempo_max) if tempo_max is not None else None

        nota_justica = float(c_dict.get("nota_justica", 0.0))
        pontuacao = float(c_dict.get("pontuacao", 0.0))
        tiktok_url = c_dict.get("tiktok_url") or lugar.get("tiktok_url")

        autor = lugar.get("autor_tiktok", "autor desconhecido")
        data_pub = lugar.get("data_publicacao", "s/d")
        fonte = str(c_dict.get("fonte") or f"Vídeo de {autor} publicado em {data_pub}")

        vibes = list(c_dict.get("vibes") or lugar.get("vibes") or [])
        resumo_sensorial = str(lugar.get("resumo_sensorial", ""))

        preparados.append({
            "id": letra_id,
            "posicao": i + 1,
            "lugar_id": lugar_id,
            "nome": nome,
            "tipo": tipo,
            "ra": ra,
            "regiao_administrativa": regiao_texto,
            "endereco": endereco,
            "inicio": inicio_str,
            "fim": fim_str,
            "horario": horario,
            "horario_situacao": horario_situacao,
            "quantos_podem": quantos_podem,
            "consumo_estimado_rs": str(consumo_rs),
            "faixa_gasto_rs": {"min": str(gasto_min), "max": str(gasto_max)},
            "tempo_medio_chegada_min": tempo_medio_min,
            "tempo_maximo_chegada_min": tempo_max_min,
            "nota_justica": nota_justica,
            "pontuacao": pontuacao,
            "explicacao": str(c_dict.get("explicacao") or ""),
            "tiktok_url": tiktok_url,
            "fonte": fonte,
            "vibes": vibes,
            "resumo_sensorial": resumo_sensorial,
        })

    # Chamada ao LLM do Anfitrião com JSON Schema estrito
    textos_cartoes: dict[str, CartaoTexto] = {}
    cliente = llm if llm is not None else ClienteLLM()

    if cliente.disponivel:
        try:
            prompt_sis = prompt("comunicacao")
            dados_usuario = _payload_para_llm(preparados, preferencias_grupo)
            prompt_usr = embrulhar("candidatos_validados", dados_usuario)
            esquema = esquema_estrito(SaidaComunicacao)

            resp_json = cliente.json("comunicacao", prompt_sis, prompt_usr, esquema)
            saida = SaidaComunicacao.model_validate(resp_json)
            for item in saida.cartoes:
                textos_cartoes[item.id] = item
        except (ErroLLM, Exception):
            textos_cartoes.clear()

    # Preenchimento determinístico final e validação Pydantic
    cartoes_finais = []
    for cand in preparados:
        cid = cand["id"]
        texto = textos_cartoes.get(cid) or _fallback_textos(cand)

        card_pronto = {
            "id": cid,
            "posicao": cand["posicao"],
            "lugar_id": cand["lugar_id"],
            "nome": cand["nome"],
            "tipo": cand["tipo"],
            "ra": cand["ra"],
            "regiao_administrativa": cand["regiao_administrativa"],
            "endereco": cand["endereco"],
            "inicio": cand["inicio"],
            "fim": cand["fim"],
            "horario": cand["horario"],
            "horario_situacao": cand["horario_situacao"],
            "quantos_podem": cand["quantos_podem"],
            "consumo_estimado_rs": cand["consumo_estimado_rs"],
            "faixa_gasto_rs": cand["faixa_gasto_rs"],
            "tempo_medio_chegada_min": cand["tempo_medio_chegada_min"],
            "tempo_maximo_chegada_min": cand["tempo_maximo_chegada_min"],
            "nota_justica": cand["nota_justica"],
            "pontuacao": cand.get("pontuacao", 0.0),
            "explicacao": cand["explicacao"] or f"{texto.por_que_combina} {texto.resumo_acesso}".strip(),
            "tiktok_url": cand["tiktok_url"],
            "fonte": cand["fonte"],
            "vibes": cand["vibes"],
            "titulo": texto.titulo,
            "resumo_acesso": texto.resumo_acesso,
            "por_que_combina": texto.por_que_combina,
        }

        # Validação estrita por Pydantic
        validado = CartaoSugestaoValidado.model_validate(card_pronto)
        cartoes_finais.append(validado.model_dump(mode="json"))

    return cartoes_finais


# ------------------------------------------------------------------ Nó para o LangGraph (Issue #71)
def no_comunicacao(estado: dict[str, Any], *, llm: ClienteLLM | None = None) -> dict[str, Any]:
    """Nó do LangGraph para o Agente 4 (Comunicação), consumindo e alimentando MultiAgentState."""
    candidatos = estado.get("candidatos_validados") or estado.get("candidatos_avaliados") or []
    preferencias = estado.get("preferencias_grupo")

    cartoes_finais = executar_agente_comunicacao(candidatos, llm=llm, preferencias_grupo=preferencias)

    textos = [
        {"id": c["id"], "titulo": c["titulo"], "resumo_acesso": c["resumo_acesso"], "por_que_combina": c["por_que_combina"]}
        for c in cartoes_finais
    ]

    return {
        "cartoes": textos,
        "cartoes_por_llm": bool(llm and llm.disponivel),
        "resultado_final_cartoes": cartoes_finais,
    }
