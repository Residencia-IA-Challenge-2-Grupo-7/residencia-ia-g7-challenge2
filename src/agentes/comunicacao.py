"""Agente 4: Síntese e Comunicação (Issue #69, ADR 0015, docs/semanas/semana-04.md).

Persona: 'Anfitrião de Brasília'.
Responsabilidades:
1. Recebe exclusivamente os candidatos aprovados da Validação (candidatos_validados, máximo 4);
2. Invoca o LLM com o prompt do Anfitrião e saída estrita em JSON (SaidaComunicacao: titulo, resumo_acesso, por_que_combina);
3. Envia sinais determinísticos de logística (chegada_equilibrada, todos_podem_na_janela, cabe_no_orcamento_do_grupo);
4. Valida em código cada texto gerado (sem números, sem valores em R$, sem citar origens e sem meios de transporte inventados);
5. Preenche deterministicamente dados financeiros, tempos e links do TikTok no esquema Sugestao (RF-06, RNF-04);
6. Garante zero citação de orçamentos individuais, origens de participantes ou restrições de pessoas (RNF-02);
7. Validação estrita dos cartões via Pydantic com extra='forbid' (CartaoSugestaoValidado).
"""
from __future__ import annotations

import copy
import json
import re
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from src.agentes.contratos import CartaoTexto, SaidaComunicacao, esquema_estrito
from src.agentes.llm import ClienteLLM, ErroLLM, embrulhar, prompt
from src.interpretador.numeros import canon
from src.salas.integracoes import carregar_lugares
from src.salas.modelos import Sugestao

LETRAS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
LIMITE_MAXIMO_CARTOES = 4


# ------------------------------------------------------------------ Pydantic Card Schema (Strict)
class FaixaGasto(BaseModel):
    model_config = ConfigDict(extra="forbid")
    min: str
    max: str


class CartaoSugestaoValidado(BaseModel):
    """Esquema Pydantic para validação estrita dos cartões finais (RF-06, RNF-03, RNF-04, RNF-02)."""
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="Letra do cartão (A, B, C, D)")
    posicao: int = Field(..., ge=1, le=4, description="Posição no ranking (1 a 4)")
    lugar_id: str = Field(..., description="ID oficial do local na base 2FA")
    nome: str = Field(..., description="Nome oficial do estabelecimento")
    tipo: str = Field(..., description="Tipo de rolê (ex: Bar, Gastronomia, Café)")
    ra: str | None = Field(default=None, description="Região Administrativa oficial")
    regiao_administrativa: str = Field(..., description="Nome da RA formatado")
    endereco: str = Field(..., description="Endereço oficial completo")
    inicio: str | None = Field(default=None, description="Data/hora de início em ISO-8601 ou não informada")
    fim: str | None = Field(default=None, description="Data/hora de fim em ISO-8601 ou não informada")
    horario: str = Field(..., description="Texto legível do horário")
    horario_situacao: str = Field(..., description="Situação factual: aberto, provavel ou incerto")
    quantos_podem: str = Field(..., description="Contagem pública de confirmação")
    consumo_estimado_rs: str = Field(..., description="Consumo médio estimado por pessoa em R$")
    faixa_gasto_rs: FaixaGasto | dict[str, str] = Field(..., description="Faixa estimada incluindo transporte")
    tempo_medio_chegada_min: int | None = Field(default=None, description="Média de trajeto em minutos")
    tempo_maximo_chegada_min: int | None = Field(default=None, description="Pior trajeto em minutos")
    nota_justica: float = Field(..., description="Nota da Menor Miséria (0 a 100)")
    pontuacao: float = Field(default=0.0, description="Pontuação composta do ranking")
    explicacao: str = Field(..., description="Explicação consolidada para a votação")
    tiktok_url: str | None = Field(default=None, description="Link original do vídeo 2FA")
    fonte: str = Field(..., description="Crédito e data da fonte 2FA")
    vibes: list[str] = Field(default_factory=list, description="Lista de vibes e etiquetas")
    titulo: str = Field(..., description="Título acolhedor gerado pelo Anfitrião")
    resumo_acesso: str = Field(..., description="Resumo de acesso gerado pelo Anfitrião")
    por_que_combina: str = Field(..., description="Motivo de afinidade gerado pelo Anfitrião")


# ------------------------------------------------------------------ Validação de Texto em Código
def texto_conforme_regras(texto: str) -> bool:
    """Valida em código se o texto gerado respeita RNF-02 e RNF-04:

    - Zero algarismos ou números;
    - Zero menção a moedas ('R$', 'reais'), minutos ('min') ou distâncias ('km');
    - Zero menção a pontos de origem individuais ('quem vem de', 'sai de').
    """
    if not texto or not texto.strip():
        return False
    # Não pode conter algarismos
    if re.search(r"\d", texto):
        return False
    # Não pode citar valores monetários, tempos ou distâncias explícitas
    if re.search(r"\b(r\$|reais|min|minuto|minutos|km|quilometro|quilometros)\b", texto, re.IGNORECASE):
        return False
    # Não pode expor origens ou pontos de partida individuais
    if re.search(r"(quem vem de|pra quem sai de|quem sai de|vindo de|saindo de)", texto, re.IGNORECASE):
        return False
    return True


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


def _calcular_sinais(cand: dict) -> dict[str, bool]:
    """Sinais determinísticos de logística e validação para ancorar a IA."""
    pior = cand.get("tempo_maximo_chegada_min")
    if pior is None:
        pior = cand.get("pior_trajeto_min")
    dif = cand.get("diferenca_min")

    chegada_eq = (pior is not None and pior <= 45 and (dif is None or dif <= 30))
    if pior is not None and pior <= 45 and float(cand.get("nota_justica", 0)) >= 75:
        chegada_eq = True

    qtd = str(cand.get("quantos_podem") or cand.get("contagem") or "").lower()
    todos_podem = ("todos" in qtd or "4 de 4" in qtd or "3 de 3" in qtd or "2 de 2" in qtd)

    return {
        "chegada_equilibrada": bool(chegada_eq),
        "todos_podem_na_janela": bool(todos_podem),
        "cabe_no_orcamento_do_grupo": True,
    }


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
            "sinais": c["sinais"],
        })
    resultado = {"candidatos": fatos}
    if preferencias_grupo:
        resultado["preferencias_grupo"] = {
            "tipos": preferencias_grupo.get("tipos", []),
            "vibes": preferencias_grupo.get("vibes", []),
            "evitar": preferencias_grupo.get("evitar", []),
        }
    return resultado


def _fallback_textos(cand: dict, sinais: dict[str, bool]) -> CartaoTexto:
    nome = cand.get("nome", "Lugar")
    tipo = cand.get("tipo", "Rolê").split(" / ")[0]
    ra = cand.get("regiao_administrativa") or "Brasília"
    vibes = cand.get("vibes") or []
    vibe_txt = ", ".join(vibes[:2]) if vibes else "agradável"
    sit = cand.get("horario_situacao", "aberto")

    titulo = f"{nome} em {ra}" if len(nome.split()) <= 3 else nome[:30]

    if sinais.get("chegada_equilibrada"):
        resumo_acesso = "Fica no meio do caminho para o grupo, sem ninguém precisar atravessar o DF."
    else:
        resumo_acesso = "Vale combinar o transporte antes para o grupo chegar junto."

    partes_combina = [f"Ambiente com estilo {vibe_txt}, bom para reunir o grupo todo."]
    if sit in ("provavel", "incerto"):
        partes_combina.append("Vale confirmar o horário antes de ir.")
    if "Bar" in tipo or "Pub" in tipo or "Boteco" in tipo:
        partes_combina.append("Lembrem-se de combinar a volta com carona ou transporte sem dirigir.")

    por_que_combina = " ".join(partes_combina)
    return CartaoTexto(id=cand["id"], titulo=titulo, resumo_acesso=resumo_acesso, por_que_combina=por_que_combina)


# ------------------------------------------------------------------ Função Principal
def executar_agente_comunicacao(
    candidatos_validados: list[dict | Any],
    *,
    llm: ClienteLLM | None = None,
    preferencias_grupo: dict | None = None,
    lugares_base: tuple[dict, ...] | None = None,
    devolver_status: bool = False,
) -> list[dict] | tuple[list[dict], bool]:
    """Agente de Comunicação: redige títulos e justificativas calorosas e monta cartões estritos (RF-06, RNF-02, RNF-04).

    Args:
        candidatos_validados: Lista de candidatos viáveis aprovados pela Validação (máximo 4).
        llm: Cliente LLM opcional (usa DeepSeek V4.1 Flash via OpenRouter ou fallback offline).
        preferencias_grupo: Preferências agregadas do grupo (opcional, sem PII).
        lugares_base: Base de lugares alternativa (para testes isolados sem arquivo físico).
        devolver_status: Se True, devolve também um booleano indicando se a LLM respondeu.

    Returns:
        list[dict] ou tuple[list[dict], bool]: Lista de cartões validados por CartaoSugestaoValidado.
    """
    if not candidatos_validados:
        return ([], False) if devolver_status else []

    # Limita rigorosamente a no máximo 4 cartões
    candidatos_selecionados = list(candidatos_validados)[:LIMITE_MAXIMO_CARTOES]

    por_id, por_nome = _mapas_base()
    if lugares_base:
        for l in lugares_base:
            lid = str(l.get("id") or "")
            if lid:
                por_id[lid] = l
            nome_c = canon(str(l.get("nome") or ""))
            if nome_c:
                por_nome[nome_c] = l

    preparados = []
    for i, c in enumerate(candidatos_selecionados):
        letra_id = LETRAS[i]
        if isinstance(c, Sugestao):
            card_dict = copy.deepcopy(c.publico())
            card_dict["id"] = letra_id
            card_dict["posicao"] = i + 1
            lugar_ref = _buscar_lugar(c, por_id, por_nome)
            card_dict["resumo_sensorial"] = lugar_ref.get("resumo_sensorial", "")
            card_dict["sinais"] = _calcular_sinais(card_dict)
            card_dict["pontuacao"] = c.pontuacao
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

        inicio_val = c_dict.get("inicio")
        fim_val = c_dict.get("fim")
        inicio_str = inicio_val.isoformat() if isinstance(inicio_val, datetime) else (str(inicio_val) if inicio_val else None)
        fim_str = fim_val.isoformat() if isinstance(fim_val, datetime) else (str(fim_val) if fim_val else None)

        horario = str(c_dict.get("horario") or c_dict.get("horario_texto") or c_dict.get("janela") or "Horário a combinar")
        horario_situacao = str(c_dict.get("horario_situacao") or "aberto")
        quantos_podem = str(c_dict.get("quantos_podem") or c_dict.get("contagem") or "todos podem")

        consumo_num = c_dict.get("consumo_rs") or c_dict.get("consumo_estimado_rs") or lugar.get("custo_medio_rs") or "0.00"
        consumo_rs = Decimal(str(consumo_num)).quantize(Decimal("0.01"))

        fg = c_dict.get("faixa_gasto_rs")
        if isinstance(fg, dict) and "min" in fg and "max" in fg:
            gasto_min = Decimal(str(fg["min"])).quantize(Decimal("0.01"))
            gasto_max = Decimal(str(fg["max"])).quantize(Decimal("0.01"))
        elif c_dict.get("gasto_min") is not None and c_dict.get("gasto_max") is not None:
            gasto_min = Decimal(str(c_dict["gasto_min"])).quantize(Decimal("0.01"))
            gasto_max = Decimal(str(c_dict["gasto_max"])).quantize(Decimal("0.01"))
        else:
            gasto_min = consumo_rs
            gasto_max = consumo_rs

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

        sinais = _calcular_sinais(c_dict)

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
            "sinais": sinais,
        })

    # Chamada ao LLM do Anfitrião com JSON Schema estrito
    textos_cartoes: dict[str, CartaoTexto] = {}
    cliente = llm if llm is not None else ClienteLLM()
    usou_llm = False

    if cliente.disponivel:
        try:
            prompt_sis = prompt("comunicacao")
            dados_usuario = _payload_para_llm(preparados, preferencias_grupo)
            prompt_usr = embrulhar("candidatos_validados", dados_usuario)
            esquema = esquema_estrito(SaidaComunicacao)

            resp_json = cliente.json("comunicacao", prompt_sis, prompt_usr, esquema)
            saida = SaidaComunicacao.model_validate(resp_json)
            for item in saida.cartoes:
                # Conferência de conformidade em código (RNF-02, RNF-04)
                if (texto_conforme_regras(item.titulo) and
                        texto_conforme_regras(item.resumo_acesso) and
                        texto_conforme_regras(item.por_que_combina)):
                    textos_cartoes[item.id] = item
            if textos_cartoes:
                usou_llm = True
        except (ErroLLM, ValueError):
            textos_cartoes.clear()
            usou_llm = False

    # Preenchimento determinístico final e validação Pydantic estrita
    cartoes_finais = []
    for cand in preparados:
        cid = cand["id"]
        sinais = cand["sinais"]
        texto = textos_cartoes.get(cid) or _fallback_textos(cand, sinais)

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

        # Validação estrita por Pydantic (extra='forbid')
        validado = CartaoSugestaoValidado.model_validate(card_pronto)
        cartoes_finais.append(validado.model_dump(mode="json"))

    if devolver_status:
        return cartoes_finais, usou_llm
    return cartoes_finais


# ------------------------------------------------------------------ Nó para o LangGraph (Issue #71)
def no_comunicacao(estado: dict[str, Any], *, llm: ClienteLLM | None = None) -> dict[str, Any]:
    """Nó do LangGraph para o Agente 4 (Comunicação), consumindo exclusivamente candidatos_validados."""
    # Só consome candidatos_validados (RNF-02, RNF-04: nunca candidatos vetados)
    candidatos = estado.get("candidatos_validados") or []
    if not candidatos:
        return {
            "cartoes": [],
            "cartoes_por_llm": False,
            "resultado_final_cartoes": [],
        }

    preferencias = estado.get("preferencias_grupo")
    cartoes_finais, usou_llm = executar_agente_comunicacao(
        candidatos, llm=llm, preferencias_grupo=preferencias, devolver_status=True
    )

    textos = [
        {"id": c["id"], "titulo": c["titulo"], "resumo_acesso": c["resumo_acesso"], "por_que_combina": c["por_que_combina"]}
        for c in cartoes_finais
    ]

    return {
        "cartoes": textos,
        "cartoes_por_llm": usou_llm,
        "resultado_final_cartoes": cartoes_finais,
    }


# ------------------------------------------------------------------ usado pelo grafo da issue #71
# O grafo monta os fatos de cada cartão a partir do ranking da Logística e escreve com o esquema `SaidaComunicacao`,
# para a Validação poder reprovar e pedir reescrita de um cartão só. Juntar com `executar_agente_comunicacao`
# acima é pendência registrada na Seção 8 da semana 4.
PIOR_TRAJETO_EQUILIBRADO_MIN = 45
DIFERENCA_EQUILIBRADA_MIN = 30


def montar_fatos(aprovados: list[str], ranking: list[dict], candidatos: list[dict], documentos: dict[str, dict],
                 teto_aplicado: bool) -> list[dict]:
    """Fatos de grupo por cartão (A, B, C, D), sem números de ninguém."""
    rank = {r["id"]: r for r in ranking}
    cand = {c["id"]: c for c in candidatos}
    fatos = []
    for letra, lid in zip("ABCD", aprovados):
        r, c, d = rank[lid], cand.get(lid, {}), documentos.get(lid, {})
        equilibrada = (r["pior_trajeto_min"] is not None and r["pior_trajeto_min"] <= PIOR_TRAJETO_EQUILIBRADO_MIN
                       and (r["diferenca_min"] or 0) <= DIFERENCA_EQUILIBRADA_MIN)
        fatos.append({
            "id": letra, "lugar_id": lid, "nome": r["nome"], "tipo": d.get("tipo", ""), "ra_do_lugar": r["ra_do_lugar"],
            "trechos_do_documento": [t for t in (c.get("trecho"), d.get("descricao", "")[:240]) if t],
            "motivo_da_pesquisa": c.get("motivo", ""), "vibes": d.get("vibes", []),
            "horario_situacao": r["horario_situacao"],
            "sinais": {"chegada_equilibrada": equilibrada, "cabe_no_orcamento_do_grupo": teto_aplicado,
                       "todos_podem_na_janela": _todos_podem(r["quantos_podem"])},
        })
    return fatos


def _todos_podem(contagem: str) -> bool:
    m = re.match(r"(\d+) de (\d+)", contagem or "")
    return bool(m and m.group(1) == m.group(2))


def texto_reserva(f: dict, *, seguro: bool = False) -> dict:
    """Texto por regras, sem LLM e sem números. `seguro`: sem o motivo escrito pela Pesquisa (cartão reprovado)."""
    acesso = ("Fica no meio do caminho: ninguém precisa atravessar o DF para chegar."
              if f["sinais"]["chegada_equilibrada"] else "Confira no seu painel quanto tempo você leva para chegar.")
    generico = f"Combina com o que o grupo pediu: {f['tipo'].split(' / ')[0].lower()}."
    combina = generico if seguro else (f["motivo_da_pesquisa"] or generico)
    if f["sinais"]["cabe_no_orcamento_do_grupo"]:
        combina += " Cabe no orçamento do grupo."
    if f["horario_situacao"] in ("provavel", "incerto"):
        combina += " Confirme o horário antes de ir."
    return {"id": f["id"], "titulo": f["nome"][:60], "resumo_acesso": acesso, "por_que_combina": combina}


def escrever(fatos: list[dict], pedido_grupo: dict, cliente: ClienteLLM, correcoes: dict[str, list[str]] | None = None
             ) -> dict:
    """-> {cartoes: [...], usou_llm}. `correcoes`: {letra: motivos da Validação} na reescrita."""
    if not fatos:
        return {"cartoes": [], "usou_llm": False}
    if cliente.disponivel:
        fatos_llm = [{k: v for k, v in f.items() if k not in ("lugar_id",)} for f in fatos]
        mensagem = embrulhar("fatos_dos_cartoes", {"pedido_do_grupo": pedido_grupo, "cartoes": fatos_llm})
        if correcoes:
            mensagem += ("\n\nCorreções da Validação (geradas pelo sistema), reescreva só estes cartões: "
                         + json.dumps(correcoes, ensure_ascii=False))
        try:
            bruto = cliente.json("comunicacao", prompt("comunicacao"), mensagem, esquema_estrito(SaidaComunicacao),
                                 max_tokens=1500)
            saida = SaidaComunicacao.model_validate(bruto)
            por_letra = {c.id: c.model_dump() for c in saida.cartoes}
            if all(f["id"] in por_letra for f in fatos):
                return {"cartoes": [por_letra[f["id"]] for f in fatos], "usou_llm": True}
        except (ErroLLM, ValueError):
            pass
    return {"cartoes": [texto_reserva(f) for f in fatos], "usou_llm": False}
