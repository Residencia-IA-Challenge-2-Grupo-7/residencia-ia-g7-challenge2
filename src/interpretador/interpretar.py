"""Interpretador de mensagens (ADR 0007): texto digitado ou transcrito -> intenções estruturadas e destino.

Fluxo: pseudonimizar -> LLM preenche o esquema -> validação Pydantic -> código resolve datas, converte valores,
casa lugares, monta a ConsultaBusca, decide confirmação, pergunta e destino. O LLM nunca vê a data de hoje
nem escreve SQL; nenhum valor em reais sai de texto gerado (RNF-04).
"""
import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from pydantic import ValidationError

from base.contrato import ConsultaBusca, Janela

from .config import CFG, PROMPTS
from .esquema import IntencaoLLM, Intencao, Interpretacao, SaidaLLM
from .lugares import casar
from .numeros import trecho_na_mensagem, valor_em_reais
from .pseudonimo import Pseudonimos
from .tempo import ErroTempo, resolver_dias, resolver_janelas

SISTEMA = (PROMPTS / "interpretar.md").read_text(encoding="utf-8")
FUSO = timezone(timedelta(hours=-3))  # America/Sao_Paulo, sem horário de verão desde 2019
V = CFG["valores"]

PERGUNTAS = {
    "falta_dia": "De qual dia você está falando?",
    "dia_invalido": "Não entendi o dia. Pode dizer a data (dd/mm) ou o dia da semana?",
    "horario_invalido": "Não entendi o horário. De que horas a que horas?",
    "falta_valor_gasto": "Quanto foi, em reais?",
    "falta_valor_orcamento": "Até quanto você quer gastar neste rolê, em reais, transporte incluído?",
    "valor_invalido": "Não entendi o valor. Quanto é, em reais?",
}
TIPOS_BASE = {"comer_beber", "ar_livre_gratuito", "local_evento"}


def reais(v: Decimal) -> str:
    s = f"{v:,.2f}"
    return "R$ " + s.replace(",", "_").replace(".", ",").replace("_", ".")


def _hora_local(agora: datetime | None) -> datetime:
    agora = agora or datetime.now(FUSO)
    if agora.tzinfo is not None:
        agora = agora.astimezone(FUSO)
    return agora.replace(tzinfo=None)


def _valor(it: IntencaoLLM, texto_llm: str) -> tuple[Decimal | None, str | None]:
    """(valor, motivo da pergunta). O trecho precisa estar na mensagem; quem converte é o código."""
    if not it.valor:
        return None, "falta_valor"
    if not trecho_na_mensagem(it.valor, texto_llm):
        return None, "valor_invalido"
    v = valor_em_reais(it.valor)
    if v is None or not (V["minimo"] <= v <= V["maximo"]):
        return None, "valor_invalido"
    return v, None


def _perguntar(i: Intencao, motivo: str, chave: str | None = None):
    i.motivo_pergunta = motivo
    i.pergunta = PERGUNTAS[chave or motivo]
    i.requer_confirmacao = False
    i.confirmacao = None


def resolver(it: IntencaoLLM, *, texto_llm: str, ps: Pseudonimos, contexto: str, origem: str,
             agora: datetime) -> Intencao:
    i = Intencao(tipo=it.tipo, destino="nenhum", trecho=ps.revelar_texto(it.trecho))
    try:
        if it.tipo == "disponibilidade":
            i.destino = "agente_membro"
            if not it.janelas:
                raise ErroTempo("falta_dia")
            for j in it.janelas:
                i.janelas += resolver_janelas(j.dias, j.periodo, j.apos, j.ate, agora, j.proxima_semana,
                                              j.disponivel, exigir_dia=True)
            i.requer_confirmacao = True
            partes = [j.texto() + ("" if j.disponivel else " (não pode)") for j in i.janelas]
            i.confirmacao = "; ".join(partes) + ". Está certo?"

        elif it.tipo == "orcamento":
            v, motivo = _valor(it, texto_llm)
            i.valor = v
            if contexto == "grupo":
                # ADR 0007: orçamento dito no grupo não vira restrição nem é repetido; a coleta é no privado (RF-11).
                i.destino = "ignorado"
                return i
            i.destino = "agente_membro"
            if motivo:
                _perguntar(i, motivo, "falta_valor_orcamento" if motivo == "falta_valor" else None)
                return i
            i.requer_confirmacao = True
            i.confirmacao = f"Seu teto para este rolê: {reais(v)}, transporte incluído. Está certo?"

        elif it.tipo == "gasto":
            i.destino = "financas"
            i.pagador = ps.revelar(it.pagador) or ps.autor
            i.descricao = ps.revelar_texto(it.descricao) if it.descricao else None
            v, motivo = _valor(it, texto_llm)
            i.valor = v
            if motivo:
                _perguntar(i, motivo, "falta_valor_gasto" if motivo == "falta_valor" else None)
                return i
            i.requer_confirmacao = True
            do = f" de {i.descricao}" if i.descricao else ""
            i.confirmacao = f"{reais(v)}{do}, pago por {'você' if i.pagador == ps.autor else i.pagador}. Confirma?"
            if i.pagador and i.pagador != ps.autor:
                i.confirmar_com = i.pagador  # RF-30: quem pagou confirma antes de dividir

        elif it.tipo == "pedido_role":
            i.destino = "mediador"
            i.tipo_role = it.tipo_role
            i.convidados = sorted({ps.revelar(c) for c in it.convidados if c.startswith("@m")})
            fichas = [d for j in it.janelas for d in j.dias]
            proxima = any(j.proxima_semana for j in it.janelas)
            if fichas:
                datas = resolver_dias(fichas, agora.date(), proxima)
                i.periodo_de, i.periodo_ate = datas[0], datas[-1]
                if origem == "voz":  # RF-39: ação com data dita por voz passa por confirmação
                    i.requer_confirmacao = True
                    i.confirmacao = f"Abrir um rolê entre {i.periodo_de:%d/%m} e {i.periodo_ate:%d/%m}?"

        elif it.tipo == "busca_lugar":
            i.destino = "base"
            i.tipo_role = it.tipo_role
            ras, regioes, sobra = casar(it.lugares)
            teto = None
            if it.valor:
                teto, _ = _valor(it, texto_llm)
            janela = None
            if it.janelas:
                j = it.janelas[0]
                if j.dias or j.periodo or j.apos or j.ate:
                    r = resolver_janelas(j.dias, j.periodo, j.apos, j.ate, agora, j.proxima_semana, exigir_dia=False)[0]
                    janela = Janela(inicio=r.inicio, fim=r.fim)
                    i.janelas = [r]
            texto = " ".join(filter(None, [it.texto_busca, *sobra])) or ps.revelar_texto(it.trecho) or texto_llm
            i.consulta = ConsultaBusca(
                texto=texto[:300], tipos_role=[it.tipo_role] if it.tipo_role in TIPOS_BASE else [],
                colecoes=["eventos"] if it.tipo_role == "local_evento" else ["lugares"],
                ras=ras, regioes=regioes, teto_pessoa=teto, exigir=list(dict.fromkeys(it.exigir)), janela=janela)

        else:
            i.destino = "conversa" if contexto == "privado" else "nenhum"

    except ErroTempo as e:
        _perguntar(i, e.motivo)
    except ValidationError:
        _perguntar(i, "valor_invalido")
    return i


def juntar_disponibilidade(intencoes: list[IntencaoLLM]) -> list[IntencaoLLM]:
    """Várias intenções de disponibilidade na mesma mensagem viram uma só, com uma confirmação para todas
    ("sábado não posso, domingo tô livre"). Medido em 05/11: o LLM às vezes as separa."""
    disp = [i for i in intencoes if i.tipo == "disponibilidade"]
    if len(disp) < 2:
        return intencoes
    unica = disp[0].model_copy(update={"janelas": [j for i in disp for j in i.janelas],
                                       "trecho": "; ".join(i.trecho for i in disp if i.trecho)})
    saida, pos = [], False
    for i in intencoes:
        if i.tipo != "disponibilidade":
            saida.append(i)
        elif not pos:
            saida.append(unica)
            pos = True
    return saida


def interpretar(mensagem: str, *, contexto: str = "privado", autor: str | None = None,
                membros: list[str] | tuple = (), agora: datetime | None = None, origem: str = "texto",
                llm=None) -> Interpretacao:
    """contexto: 'privado' (conversa do membro com a IA) ou 'grupo'. origem: 'texto' ou 'voz'."""
    from .llm import ErroLLM, OpenRouter

    agora = _hora_local(agora)
    ps = Pseudonimos(list(membros), autor)
    texto_llm = ps.ocultar(mensagem)
    t0 = time.perf_counter()
    res = Interpretacao(mensagem=mensagem, contexto=contexto, origem=origem, intencoes=[])
    try:
        llm = llm or OpenRouter()
        bruto, meta = llm.interpretar(SISTEMA, f"<mensagem>{texto_llm}</mensagem>")
        saida = SaidaLLM.model_validate(bruto)
        res.modelo, res.tokens_entrada, res.tokens_saida, res.custo_usd = (
            meta.modelo, meta.tokens_entrada, meta.tokens_saida, meta.custo_usd)
    except (ErroLLM, ValidationError) as e:
        # RNF-15: nada é registrado; a IA pede para repetir.
        res.erro = f"{type(e).__name__}: {str(e)[:500]}"
        res.intencoes = [Intencao(tipo="outra", destino="nenhum", motivo_pergunta="falha_llm",
                                  pergunta="Não consegui entender agora. Pode repetir?")]
        res.latencia_s = time.perf_counter() - t0
        return res
    res.intencoes = [resolver(it, texto_llm=texto_llm, ps=ps, contexto=contexto, origem=origem, agora=agora)
                     for it in juntar_disponibilidade(saida.intencoes)]
    res.latencia_s = time.perf_counter() - t0
    return res
