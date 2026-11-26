"""Os 4 campos secretos da Tela 2 (guia oficial de 10/11) -> perfil estruturado do participante.

| Campo da Tela 2                          | Sai daqui                                   | Quem resolve                 |
|------------------------------------------|---------------------------------------------|------------------------------|
| 1. De onde você vai sair no DF?          | uma das 35 RAs e a macrorregião             | apelidos, quadras e estações |
| 2. Quais dias e horários você pode?      | janelas com data e hora                     | regras + `tempo.py`          |
| 3. Qual seu limite máximo de gasto em R$?| teto em reais                               | `numeros.py` (nunca o LLM)   |
| 4. O que você anima fazer e como vai?    | tipos de rolê, vibes, restrições, transporte| dicionário de termos         |

Tudo por código (RNF-04). O LLM do ADR 0007 só entra como reserva do campo 2, quando as regras não acham
nenhum dia, e só se o chamador passar um cliente. Os campos 1, 3 e 4 nunca saem da máquina: localização e
dinheiro são os dados mais sensíveis da sala (RNF-01, RNF-02).

O resultado é mostrado só ao próprio participante, para ele confirmar em segredo ("Sáb 14/11, 18h–23h,
saindo de Águas Claras, teto de R$ 60,00").
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal

from .lugares import casar, ras_validas
from .numeros import canon, valor_em_reais
from .tempo import DIAS, ErroTempo, JanelaResolvida, _data_dia_mes, resolver_janelas

TETO_MAXIMO = Decimal("1000")  # mesmo limite de ConsultaBusca.teto_pessoa

PERGUNTAS = {
    "local_vazio": "De onde você vai sair? Pode ser a RA, a quadra ou um ponto conhecido (ex.: 'Taguatinga Centro', 'SQN 210').",
    "local_desconhecido": "Não reconheci essa região do DF. Pode dizer a RA ou um ponto conhecido (ex.: 'Águas Claras perto da estação')?",
    "local_ambiguo": "Encontrei mais de uma região ({ras}). De qual delas você vai sair?",
    "falta_dia": "Quais dias você pode? Ex.: 'sexta depois das 19h ou sábado à tarde'.",
    "dia_invalido": "Não entendi o dia. Pode dizer o dia da semana ou a data (dd/mm)?",
    "horario_invalido": "Não entendi o horário. De que horas a que horas?",
    "hora_ambigua": "É de manhã ou de noite? Escreva, por exemplo, '9 da manhã' ou '21h'.",
    "so_negativa": "Entendi quando você não pode. E quando você pode?",
    "janela_passada": "Esses horários já passaram. Quais dias e horários você pode a partir de agora?",
    "teto_vazio": "Qual o máximo que você quer gastar neste rolê, em reais, transporte incluído? Ex.: 60.",
    "teto_invalido": "Não entendi o valor. Escreva um número só, em reais (ex.: 60).",
    "teto_alto": "O limite vai até R$ 1.000 por pessoa. Qual o seu máximo, em reais?",
}


# ---------------------------------------------------------------- campo 1: de onde sai

# Siglas de endereço do DF que já dizem a RA ("SQN 210", "QNM 12", "SHIS QI 5"). Da mais específica para a mais geral.
_QUADRAS: list[tuple[str, str]] = [
    (r"\b(sqsw|clsw|crsw)\b", "Sudoeste/Octogonal"),
    (r"\b(sqnw|clnw)\b", "Plano Piloto"),  # Noroeste
    (r"\bshis\b", "Lago Sul"),
    (r"\bshin\b", "Lago Norte"),
    (r"\bsmpw\b", "Park Way"),
    (r"\b(sqs|sqn|cls|cln|crs|crn|scs|scn|sbs|sbn|sds|sdn|shs|shn|sgas|sgan|scrs|scrn|scls|scln|sclrn|sclrs|w3|l2)\b",
     "Plano Piloto"),
    (r"\b\d{3}\s*(sul|norte)\b", "Plano Piloto"),  # "408 Norte", "estação 102 Sul"
    (r"\bqn[m-r]\b", "Ceilândia"),
    (r"\bqn[a-l]\b", "Taguatinga"),
]


@dataclass
class LocalInterpretado:
    ra: str | None
    regiao: str | None
    pergunta: str | None = None
    motivo: str | None = None


def interpretar_local(texto: str) -> LocalInterpretado:
    """Texto livre ("moro perto da estação Arniqueiras", "SQN 210") -> uma das 35 RAs."""
    if not texto or not texto.strip():
        return LocalInterpretado(None, None, PERGUNTAS["local_vazio"], "local_vazio")
    ras, _regioes, _ = casar([texto])
    t = canon(texto)
    for padrao, ra in _QUADRAS:
        if re.search(padrao, t) and ra not in ras:
            ras.append(ra)
    # "Asa Sul" + "SQS 308" são a mesma RA; "Plano Piloto (Sudoeste)" fica com a mais específica
    if "Sudoeste/Octogonal" in ras and "Plano Piloto" in ras:
        ras.remove("Plano Piloto")
    if not ras:
        return LocalInterpretado(None, None, PERGUNTAS["local_desconhecido"], "local_desconhecido")
    if len(ras) > 1:
        return LocalInterpretado(None, None, PERGUNTAS["local_ambiguo"].format(ras=", ".join(ras)), "local_ambiguo")
    return LocalInterpretado(ras[0], ras_validas()[ras[0]])


# ---------------------------------------------------------------- campo 2: dias e horários

_DIA_PALAVRA = {"segunda": "seg", "terca": "ter", "quarta": "qua", "quinta": "qui", "sexta": "sex",
                "sabado": "sab", "domingo": "dom", "seg": "seg", "qui": "qui", "sex": "sex", "sab": "sab",
                "dom": "dom"}
_RE_DIA = re.compile(r"\b(segunda|terca|quarta|quinta|sexta|sabado|domingo|seg|qui|sex|sab|dom)s?(?:[- ]feiras?)?\b")
_PERIODOS = {"manha": ("08:00", "12:00"), "tarde": ("13:00", "18:00"), "noite": ("19:00", "24:00"),
             "almoco": ("11:00", "15:00"), "dia_todo": ("08:00", "24:00")}
_DIA = r"(?:segunda|terca|quarta|quinta|sexta|sabado|domingo|seg|qui|sex|sab|dom)s?(?:[- ]feiras?)?"
_RE_FAIXA_DIAS = re.compile(rf"\b(?:d[aeo]\s+)?({_DIA})\s+(?:a|ao|ate(?:\s+[ao])?)\s+({_DIA})\b")
_RE_ENTRE_DIAS = re.compile(rf"\bentre\s+({_DIA})\s+e\s+({_DIA})\b")
_NOME_DIA = ["segunda", "terca", "quarta", "quinta", "sexta", "sabado", "domingo"]  # na ordem de tempo.DIAS

# Horas ditas por extenso ("oito e meia", "vinte e duas horas"). As horas são femininas: "um" e "dois" não entram.
_HORA_EXTENSO = {"uma": 1, "duas": 2, "tres": 3, "quatro": 4, "cinco": 5, "seis": 6, "sete": 7, "oito": 8, "nove": 9,
                 "dez": 10, "onze": 11, "doze": 12, "treze": 13, "catorze": 14, "quatorze": 14, "quinze": 15,
                 "dezesseis": 16, "dezessete": 17, "dezoito": 18, "dezenove": 19, "vinte": 20, "vinte e uma": 21,
                 "vinte e duas": 22, "vinte e tres": 23, "vinte e quatro": 24}
_MINUTO_EXTENSO = {"cinco": 5, "dez": 10, "quinze": 15, "vinte": 20, "vinte e cinco": 25, "trinta": 30,
                   "trinta e cinco": 35, "quarenta": 40, "quarenta e cinco": 45, "cinquenta": 50,
                   "cinquenta e cinco": 55, "meia": 30}
# Datas ditas ("6 de novembro", "dia vinte e oito"): o número do dia, por extenso ou não, e o mês
_MESES = {"janeiro": 1, "fevereiro": 2, "marco": 3, "abril": 4, "maio": 5, "junho": 6, "julho": 7, "agosto": 8,
          "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12}
_UNIDADE = {"um": 1, "uma": 1, "dois": 2, "duas": 2, "tres": 3, "quatro": 4, "cinco": 5, "seis": 6, "sete": 7,
            "oito": 8, "nove": 9}
_DIA_EXTENSO = {**_UNIDADE, "primeiro": 1, "dez": 10, "onze": 11, "doze": 12, "treze": 13, "catorze": 14,
                "quatorze": 14, "quinze": 15, "dezesseis": 16, "dezessete": 17, "dezoito": 18, "dezenove": 19,
                "vinte": 20, "trinta": 30, "trinta e um": 31, **{f"vinte e {k}": 20 + v for k, v in _UNIDADE.items()}}
# "sem hora pra voltar" não limita o fim. O Whisper ouviu "100 horas pra voltar" e "cem horas" (voz real, 26/11)
_RE_SEM_HORA = re.compile(r"\b(?:sem|100|cem|cento)\s+horas?\s+(?:pra|para|de)\s+(?:voltar|acabar|ir embora)\b")
_CORRECAO = r"\s*,?\s*\b(?:quer dizer|ou melhor|alias)\b\s*,?\s*"  # "sábado, ou melhor, domingo"
_RE_CORRECAO = re.compile(_CORRECAO)
_RE_FIM_DITO = re.compile(r"\b(?:embora|voltar|vazar|em casa)\b")  # "ir embora às 20h" é o fim


def _ou(palavras) -> str:
    return "|".join(sorted(palavras, key=len, reverse=True))


# O que vem antes de um número solto para ele ser hora ("depois das 8", "lá pelas 8"), e não quantidade ("uns 3 amigos")
_PRE = (r"(?:\b(?:as|das|da|ate|apos|depois|antes|pelas|pras|partir|desde|entre)\b"
        r"(?:\s+(?:de|d[ao]s?|as?))?(?:\s+(?:umas?|uns))?\s+)")
_PARTE_DO_DIA = r"noite|tarde|manha|madrugada"
_RE_EXTENSO = re.compile(
    rf"(?P<pre>{_PRE})?\b(?P<h>{_ou(_HORA_EXTENSO)})\b(?P<horas>\s+horas?\b)?(?:\s+e\s+(?P<m>{_ou(_MINUTO_EXTENSO)})\b)?"
    rf"(?=(?P<pos>\s*(?:horas?\b|h\b|d[ao]\s+(?:{_PARTE_DO_DIA})\b|em diante\b))?)")
_RE_ENTRE_EXTENSO = re.compile(
    rf"\bentre\s+(?:as?\s+)?({_ou(_HORA_EXTENSO)})\s+e\s+(?:as?\s+)?({_ou(_HORA_EXTENSO)})\b")
_RE_DE_A_EXTENSO = re.compile(
    rf"\bde\s+({_ou(_HORA_EXTENSO)})\s+(?:a|as|ate(?:\s+as)?)\s+({_ou(_HORA_EXTENSO)})\b")
_NAO_E_HORA = (r"(?!\s*(?:/|pessoas?\b|reais\b|contos?\b|anos\b|amig|min(?:utos?)?\b"
               r"|de\s+(?:jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez)))")
_RE_MENCAO = re.compile(
    rf"(?P<pre>{_PRE})?(?<![\d/@.,])(?P<h>\d{{1,2}})(?!\d){_NAO_E_HORA}"
    r"(?:\s*(?P<u>horas?|hrs?|hs|h)(?![a-z])(?:\s*(?:e\s+)?(?P<m1>meia\b|\d{2}(?!\d|\s*[h:/]|\s+horas?))(?:\s*min(?:utos?)?\b)?)?"
    r"|:(?P<m2>\d{2})(?!\d)"
    r"|\s+e\s+(?P<m3>meia\b|\d{2}(?!\d|\s*[h:/]|\s+horas?)))?"
    rf"(?:\s*d[ao]\s+(?P<parte>{_PARTE_DO_DIA})\b)?(?![a-z])")
_T = r"@(\d{2})(\d{2})([~!]?)"  # hora já lida: @HHMM; "~" = dita sem "h" nem parte do dia; "!" = "8 da noite"
_RE_SEGUNDA = re.compile(r"(@\d{4}[~!]?\s*(?:-|\ba\b|\bate\b)\s*)(\d{1,2})(?![\dh:/])\b")
_RE_FAIXA = [re.compile(rf"\bentre\s+(?:as?\s+)?{_T}\s+e\s+(?:as?\s+)?{_T}"),
             re.compile(rf"(?:\bd[ae]s?\s+)?{_T}\s*(?:-|\bas?\b|\bate(?:\s+as?)?(?:\s+umas?)?\b)\s*{_T}")]
_RE_APOS = [re.compile(rf"\b(?:depois|apos|a partir|partir|desde)\s+(?:d[ae]s?\s+|as\s+)?(?:umas?\s+|uns\s+)?{_T}"),
            re.compile(rf"(?:\bd[ae]s?\s+)?{_T}\s+(?:em diante|pra frente|pra la)\b")]
_RE_ATE = re.compile(rf"\b(?:ate|antes)\s+(?:d[aeo]s?\s+|[ao]s?\s+)?(?:umas?\s+|uns\s+)?{_T}")
_RE_HORA = re.compile(_T)

_OCUPACAO = (r"trabalh\w*|trampo|aulas?|expediente|servico|faculdade|facul|academia|estagio|plantao|curso|escola"
             r"|reuniao|prova")
_RE_OCUPADO = re.compile(rf"\b(?:{_OCUPACAO}|ocupad[oa]|compromisso)\b")
_RE_SAIDA = re.compile(r"\b(?:saio|sai|sair|largo|termino|terminar|termina|acabo|acaba|acabar|libero|chego)\b")
# "depois do trabalho" sem dizer a hora: o app não sabe a que horas a pessoa sai e precisa perguntar
_RE_VAGO = re.compile(
    r"\b(?:depois|apos|antes|ate|quando|assim que)\s+(?:eu\s+)?(?:sair\s+|acabar\s+|terminar\s+)?"
    rf"(?:d?[oa]s?\s+|de\s+)?(?:meu\s+|minha\s+)?(?:{_OCUPACAO}|jantar|jogo|culto|missa)\b")
_RE_DEPOIS_DISSO = re.compile(
    r"\b(?:depois|apos)\s+(?:disso|desse horario|dessa hora|isso)\b|\bd[ae]i\s+(?:em diante|pra frente|pra la)\b"
    r"|\ba partir d(?:ai|isso)\b|\bdepois\s+(?:eu\s+)?(?:to|fico|estou)\s+(?:livre|de boa|suave)\b")
_RE_PISTA = re.compile(
    r"@\d{4}|\b(?:manha|tarde|noite|almoco|jantar|dia todo|dia inteiro|qualquer hora|qualquer horario)\b")
_RE_TOKEN_DIA = re.compile(
    rf"\b(?:{_DIA}|depois de amanha|amanha|hoje|fim de semana|fds|dias?\s+\d{{1,2}})\b|\b\d{{1,2}}/\d{{1,2}}\b")
_RE_SEPARADOR = re.compile(r"(\s+ou\s+|;|,|\s+mas\s+|\s+porem\s+|\s+so que\s+|\.\s|\n)")
_RE_MENOS = re.compile(rf"\s+(?=(?:menos|exceto|tirando)\s+(?:(?:n?[ao]s?|de)\s+)?{_DIA}\b)")
_RE_DATA_DITA = re.compile(
    rf"\b(?:(?P<sem>{_DIA})\s*,?\s+)?(?:(?:n?o\s+)?dia\s+)?(?P<d>\d{{1,2}}|{_ou(_DIA_EXTENSO)})\s+de\s+"
    rf"(?P<mes>{_ou(_MESES)})\b")
_RE_DIA_EXTENSO = re.compile(rf"\b(dias?)\s+({_ou(_DIA_EXTENSO)})\b")


@dataclass
class HorariosInterpretados:
    janelas: list[JanelaResolvida]
    confirmacao: str | None = None
    pergunta: str | None = None
    motivo: str | None = None
    origem: str = "regras"  # "regras" ou "llm"


@dataclass(frozen=True)
class _Hora:
    h: int
    m: int
    curta: bool = False      # dita sem "h" nem parte do dia ("depois das 8"): pode ser de manhã ou de noite
    explicita: bool = False  # "8 da noite": não se mexe mais

    def mais12(self) -> "_Hora":
        return _Hora(self.h + 12, self.m)

    def txt(self) -> str:
        return f"{self.h:02d}:{self.m:02d}"


@dataclass
class _Clausula:
    fichas: list[str] = field(default_factory=list)
    proxima: bool = False
    periodo: str | None = None
    apos: str | None = None
    ate: str | None = None
    negativa: bool = False
    separador: str = ""                   # o que veio antes ("ou", "mas", ",")
    hora_ini: _Hora | None = None
    hora_fim: _Hora | None = None
    faixa: bool = False                   # "das X às Y"
    partes: frozenset[str] = frozenset()  # manha, tarde, noite citadas na cláusula
    vago: bool = False                    # "depois do trabalho", sem hora
    depois_disso: bool = False            # "depois disso tô livre"
    ocupacao: bool = False                # início veio de "aula até as 22h"

    @property
    def tem_horario(self) -> bool:
        return bool(self.periodo or self.apos or self.ate)


def _ler_hora(g) -> _Hora:
    return _Hora(int(g[0]), int(g[1]), curta=g[2] == "~", explicita=g[2] == "!")


def _marcar_horas(t: str) -> str:
    """Troca cada hora dita no texto (já em `canon`) por @HHMM. Número que não é hora fica como está."""
    t = re.sub(r"meia[- ]noite", "24h", t)
    t = re.sub(r"meio[- ]dia e meia", "12h30", t)
    t = re.sub(r"meio[- ]dia", "12h", t)
    t = re.sub(r"\b(?:depois|apos)\s+d?o\s+almoco\b", "depois das 13h", t)  # início da tarde na tabela de períodos
    t = re.sub(r"\bantes\s+do\s+almoco\b", "ate as 12h", t)
    for rx in (_RE_ENTRE_EXTENSO, _RE_DE_A_EXTENSO):
        t = rx.sub(lambda m: f"das {_HORA_EXTENSO[m[1]]} as {_HORA_EXTENSO[m[2]]}", t)

    def extenso(m: re.Match) -> str:
        # "vinte e uma e trinta", "vinte e trinta"; mas "vinte e cinco" é um número
        com_minuto = m["m"] and not (m["h"] == "vinte" and m["m"] == "cinco")
        if not (m["pre"] or m["horas"] or m["pos"] or com_minuto):
            return m[0]
        minuto = "" if not m["m"] else " e meia" if m["m"] == "meia" else f" e {_MINUTO_EXTENSO[m['m']]:02d}"
        return f"{m['pre'] or ('as ' if com_minuto else '')}{_HORA_EXTENSO[m['h']]}{' horas' if m['horas'] else ''}{minuto}"

    t = _RE_EXTENSO.sub(extenso, t)
    t = re.sub(r"\bentre\s+(?:as?\s+)?(\d{1,2}(?:h\d{0,2})?)\s+e\s+(?:as?\s+)?(\d{1,2})(?=\D|$)", r"das \1 as \2", t)
    t = re.sub(rf"\bde\s+(\d{{1,2}})\s+a\s+(\d{{1,2}})\b{_NAO_E_HORA}", r"das \1 as \2", t)

    def sem_das(m: re.Match) -> str:  # "sábado 18 às 22"; não em "dias 14 e 15 às 19" nem "das 18 horas e 30 às 22"
        antes = m.string[:m.start()]
        nao = re.search(r"\bdias?\b[\s\d,e]*$|\d\s*(?:h|horas?)?\s+e\s+$", antes)
        return m[0] if nao else f"das {m[1]} as "

    t = re.sub(r"(?<![\d/@:])\b(\d{1,2})\s+as\s+(?=\d)", sem_das, t)

    def mencao(m: re.Match) -> str:
        minuto = m["m1"] or m["m2"] or m["m3"]
        if not (m["u"] or m["m2"] or m["parte"] or m["pre"] or m["m3"] == "meia"):
            return m[0]
        h, mm, parte = int(m["h"]), 30 if minuto == "meia" else int(minuto or 0), m["parte"]
        if parte in ("noite", "tarde") and 1 <= h < 12:
            h += 12
        elif parte == "noite" and h == 12:
            h = 24
        if h > 24 or mm > 59 or (h == 24 and mm):
            raise ErroTempo("horario_invalido", m[0])
        falada = not m["m2"] and m["u"] not in ("h", "hs", "hr", "hrs")
        return f"{m['pre'] or ''}@{h:02d}{mm:02d}{'!' if parte else '~' if falada and h < 12 else ''}"

    t = _RE_MENCAO.sub(mencao, t)
    return _RE_SEGUNDA.sub(lambda m: f"{m[1]}@{int(m[2]):02d}00{'~' if int(m[2]) < 12 else ''}", t)


def _expandir_dias(m: re.Match) -> str:
    """'de sexta a domingo' -> 'sexta sabado domingo'."""
    i, f = (DIAS.index(_DIA_PALAVRA[_RE_DIA.match(g)[1]]) for g in m.groups())
    return " ".join(_NOME_DIA[(i + k) % 7] for k in range((f - i) % 7 + 1))


def _inicio(x: _Hora, partes: frozenset[str]) -> _Hora:
    if x.explicita or "manha" in partes:
        return x
    if 1 <= x.h <= 6 or ("noite" in partes and 1 <= x.h < 12) or (x.curta and x.h == 7):
        return x.mais12()  # um rolê "depois das 7" é de noite (ADR 0009)
    if x.curta and 8 <= x.h <= 11:
        raise ErroTempo("hora_ambigua", x.txt())
    return x


def _fim(x: _Hora, partes: frozenset[str], ini: str | None) -> _Hora:
    if x.explicita or x.h >= 12 or x.h == 0 or ("manha" in partes and "noite" not in partes):
        return x
    de_noite = "noite" in partes or (ini is not None and ini >= "18:00")
    if x.h <= 6:
        return x if de_noite else x.mais12()  # "à noite até as 2" passa da meia-noite
    if de_noite or "tarde" in partes or (ini is not None and ini >= "12:00"):
        return x.mais12()
    if x.curta:
        raise ErroTempo("hora_ambigua", x.txt())
    return x


def _das_as(a: _Hora, b: _Hora, partes: frozenset[str]) -> tuple[_Hora, _Hora]:
    if "manha" in partes:
        return a, b
    dita = a.h
    if not a.explicita:
        if b.explicita and b.h >= 12:  # "das 7 às 11 da noite": os dois de noite
            return (a.mais12() if 1 <= dita < 12 and dita + 12 < b.h else a), b
        if "noite" in partes and 1 <= dita < 12:
            a = a.mais12()
        elif 1 <= dita <= 6 or (dita == 7 and a.curta):
            if not (b.h >= 13 and dita + 12 >= b.h):  # "das 7 às 18" começa de manhã
                a = a.mais12()
        elif a.curta and 8 <= dita <= 11 and b.h <= 11 and not b.explicita:
            raise ErroTempo("hora_ambigua", a.txt())
    if not b.explicita:
        deslocada = a.h != dita
        if b.h == 12 and deslocada:
            raise ErroTempo("hora_ambigua", b.txt())
        if b.h < 12 and ((deslocada and b.h > dita) or (a.h >= 12 and b.h > 6)):
            b = b.mais12()
    return a, b


def _clausula(c: str, separador: str = "") -> _Clausula:
    k = _Clausula(separador=separador)
    k.proxima = bool(re.search(r"\bque vem\b|\bproxim[ao]s?\b", c))

    def tirar(padrao) -> bool:
        nonlocal c
        achou = re.search(padrao, c) is not None
        c = re.sub(padrao, " ", c)
        return achou

    k.vago = tirar(r"\b(?:nao\s+)?(?:ate\s+)?(?:muito|mais|bem|tao)\s+(?:tarde|cedo)\b(?:\s+da\s+noite\b)?")  # que horas?
    k.negativa = bool(re.search(r"\bnao\b|\bmenos\b|\bexceto\b|\btirando\b", c))

    if tirar(r"\b(fim|final|finais|fins) de semana\b|\bfds\b"):
        k.fichas.append("fim_de_semana")
    if tirar(r"\bdias? de semana\b|\bdias? uteis\b|\bdurante a semana\b"):
        k.fichas += DIAS[:5]
    if tirar(r"\bqualquer dia\b|\btodos os dias\b|\btodo dia\b|\b(a )?semana (toda|inteira)\b|\btoda a semana\b"):
        k.fichas += DIAS
    if tirar(r"\bdepois de amanha\b"):
        k.fichas.append("depois_de_amanha")
    if tirar(r"\bamanha\b"):
        k.fichas.append("amanha")
    if tirar(r"\bhoje\b"):
        k.fichas.append("hoje")
    if tirar(r"\bn?(?:essa|esta)\s+semana\b"):
        k.fichas.append("esta_semana")
    for m in re.finditer(r"\b(\d{1,2})/(\d{1,2})\b", c):
        k.fichas.append(f"{int(m.group(1))}/{int(m.group(2))}")
    c = re.sub(r"\b(\d{1,2})/(\d{1,2})\b", " ", c)
    for m in re.finditer(r"\bdias?\s+(\d{1,2}(?:\s+e\s+\d{1,2})*)\b", c):
        k.fichas += [str(int(d)) for d in re.findall(r"\d+", m.group(1))]
    c = re.sub(r"\bdias?\s+\d{1,2}(?:\s+e\s+\d{1,2})*\b", " ", c)
    periodo_por_dia = re.search(rf"\b(?:manha|tarde|noite)\s+(?:n[oa]|d[oa]|de)\s+{_DIA}\b", c) is not None
    for m in _RE_DIA.finditer(c):
        k.fichas.append(_DIA_PALAVRA[m.group(1)])
    c = _RE_DIA.sub(" ", c)
    if not k.fichas and k.proxima and re.search(r"\bsemana\b", c):
        k.fichas, k.proxima = ["semana_que_vem"], False

    k.depois_disso = tirar(_RE_DEPOIS_DISSO)
    k.vago = tirar(_RE_VAGO) or tirar(r"\b(?:cedo|cedinho|tardinha|tardezinha|noitinha)\b") or k.vago
    ocupado = _RE_OCUPADO.search(c) is not None
    antes = re.search(r"\bantes\b", c) is not None
    for rx in _RE_FAIXA:
        if m := rx.search(c):
            k.hora_ini, k.hora_fim, k.faixa = _ler_hora(m.groups()[:3]), _ler_hora(m.groups()[3:]), True
            c = c[:m.start()] + " " + c[m.end():]
            break
    for rx in _RE_APOS:
        if not k.hora_ini and (m := rx.search(c)):
            k.hora_ini = _ler_hora(m.groups())
            c = c[:m.start()] + " " + c[m.end():]
    if not k.hora_fim and (m := _RE_ATE.search(c)):
        k.hora_fim = _ler_hora(m.groups())
        c = c[:m.start()] + " " + c[m.end():]
    solta = False
    if not k.hora_ini and not k.hora_fim and (m := _RE_HORA.search(c)):
        k.hora_ini, solta = _ler_hora(m.groups()), True  # "sábado às 20h": começa às 20h
        c = c[:m.start()] + " " + c[m.end():]
        if _RE_FIM_DITO.search(c):  # "preciso ir embora às 8 da noite": é quando acaba
            k.hora_ini, k.hora_fim, solta = None, k.hora_ini, False
    # Trava: hora que sobrou sem uso vira pergunta, em vez de o app supor o dia todo
    if "@" in c or re.search(r"\bmadrugada\b", c):
        raise ErroTempo("horario_invalido", "hora não usada")

    if ocupado and not k.vago:
        if k.faixa:                     # "aula das 14h às 18h": é quando NÃO pode
            k.negativa = True
        elif k.hora_fim and not antes:  # "trabalho até as 18h": livre depois
            k.hora_ini, k.hora_fim, k.ocupacao = k.hora_fim, None, True
        elif solta and not _RE_SAIDA.search(c):  # "tenho aula às 19h": até quando?
            raise ErroTempo("horario_invalido", "compromisso sem fim")
    if k.negativa and antes and k.hora_fim and not k.hora_ini:  # "não posso antes das 19h"
        k.hora_ini, k.hora_fim, k.negativa = k.hora_fim, None, False

    periodos = [p for p, rx in (("manha", r"\bmanha\b"), ("almoco", r"\balmoco\b"), ("tarde", r"\btarde\b"),
                                ("noite", r"\bnoite\b|\bjantar\b"),
                                ("dia_todo", r"\bdia (todo|inteiro)\b|\bqualquer hora(rio)?\b|\bo dia\b"))
                if re.search(rx, c)]
    k.partes = frozenset(p for p in periodos if p in ("manha", "tarde", "noite"))
    if len(k.partes) > 1 and len(k.fichas) > 1 and periodo_por_dia:  # "tarde na sexta e noite no sábado"
        raise ErroTempo("horario_invalido", "períodos por dia")
    if len(periodos) == 1 and periodos[0] in ("manha", "tarde", "noite", "dia_todo"):
        k.periodo = periodos[0]
    elif periodos:  # "tarde e noite", "almoço"
        k.apos = min(_PERIODOS[p][0] for p in periodos)
        k.ate = max(_PERIODOS[p][1] for p in periodos)
    return k


def _fechar_horas(k: _Clausula, anterior: _Clausula | None) -> None:
    """Resolve as horas ditas. Sem dia próprio, vale a parte do dia da cláusula anterior ("à noite, mas depois das 8")."""
    partes = k.partes or (anterior.partes if anterior and not k.fichas else frozenset())
    if k.faixa:
        a, b = _das_as(k.hora_ini, k.hora_fim, partes)
        k.apos, k.ate = a.txt(), b.txt()
        return
    if k.hora_ini:
        k.apos = _inicio(k.hora_ini, partes).txt()
    if k.hora_fim:
        k.ate = _fim(k.hora_fim, partes, k.apos).txt()


def _ordem(hora: str) -> str:
    """Fim até as 6h é do dia seguinte, então vem depois de 23h59."""
    return hora if hora > "06:00" else f"{int(hora[:2]) + 24}{hora[2:]}"


def _datas_ditas(t: str, hoje: date | None) -> str:
    """'sexta, 6 de novembro' -> '6/11'. Dia da semana que não bate com a data vira pergunta."""
    def troca(m: re.Match) -> str:
        n = int(m["d"]) if m["d"].isdigit() else _DIA_EXTENSO[m["d"]]
        mes = _MESES[m["mes"]]
        if m["sem"] and hoje is not None:
            data = _data_dia_mes(n, mes, hoje)
            if DIAS.index(_DIA_PALAVRA[_RE_DIA.match(m["sem"])[1]]) != data.weekday():
                raise ErroTempo("dia_invalido", m[0])
        return f" {n}/{mes} "

    t = _RE_DATA_DITA.sub(troca, t)
    return _RE_DIA_EXTENSO.sub(lambda m: f"{m[1]} {_DIA_EXTENSO[m[2]]}", t)


def _correcoes(t: str) -> str:
    """Fica com o que veio depois de "quer dizer" / "ou melhor": a hora ("das três, quer dizer, das quatro") ou o
    dia com o que foi dito junto ("sábado à noite, ou melhor, domingo à noite")."""
    t = re.sub(rf"(?:\b(?:d[ao]s?|as)\s+)?@\d{{4}}[~!]?{_CORRECAO}(?=(?:\b(?:d[ao]s?|as)\s+)?@)", " ", t)
    while m := _RE_CORRECAO.search(t):
        dias = list(_RE_TOKEN_DIA.finditer(t[:m.start()]))
        t = t[:dias[-1].start() if dias else m.start()] + " " + t[m.end():]
    return t


def _pedacos(texto: str, hoje: date | None = None) -> list[tuple[str, str]]:
    """(separador, cláusula). Além de vírgula, "ou" e "mas", separa "sexta à noite e sábado à tarde" (cada dia com o
    seu horário, mesmo sem vírgula, como sai da fala) e "qualquer dia menos sexta"."""
    t = re.sub(r"\b([2-6])a\b", lambda m: _NOME_DIA[int(m[1]) - 2], canon(texto))  # "6ª feira", "2ª"
    t = _RE_SEM_HORA.sub(" ", _datas_ditas(t, hoje))
    t = _RE_ENTRE_DIAS.sub(_expandir_dias, t)
    t = _correcoes(_marcar_horas(_RE_FAIXA_DIAS.sub(_expandir_dias, t)))
    partes = _RE_SEPARADOR.split(t)
    out: list[tuple[str, str]] = []
    for i in range(0, len(partes), 2):
        sep = partes[i - 1].strip() if i else ""
        for j, pedaco in enumerate(_RE_MENOS.split(partes[i])):
            inicio, cortes = 0, []
            dias = list(_RE_TOKEN_DIA.finditer(pedaco))
            for n, b in enumerate(dias[1:], start=1):
                proximo = dias[n + 1].start() if n + 1 < len(dias) else len(pedaco)
                if _RE_PISTA.search(pedaco[inicio:b.start()]) and _RE_PISTA.search(pedaco[b.start():proximo]):
                    cortes.append(b.start())
                    inicio = b.start()
            limites = [0, *cortes, len(pedaco)]
            for n, (a, b) in enumerate(zip(limites, limites[1:])):
                if pedaco[a:b].strip():
                    out.append((sep if j == 0 and n == 0 else "e", pedaco[a:b]))
    return out


def _clausulas(texto: str, hoje: date | None = None) -> list[_Clausula]:
    cls: list[_Clausula] = []
    antes_do_dia: _Clausula | None = None  # "de noite, sexta ou sábado": o horário veio antes dos dias
    for sep, pedaco in _pedacos(texto, hoje):
        k = _clausula(pedaco, sep)
        anterior = cls[-1] if cls else None
        _fechar_horas(k, anterior)
        if anterior is None and not k.fichas:
            if k.tem_horario:
                if antes_do_dia:
                    raise ErroTempo("falta_dia", "mais de um horário sem dia")
                antes_do_dia = k
            continue
        if k.fichas:
            if antes_do_dia and anterior is None and (k.tem_horario or sep == "ou"):
                raise ErroTempo("falta_dia", "horário sem dia")  # "depois das 19h ou sábado o dia todo"
            cls.append(k)
            continue
        if k.depois_disso and not k.tem_horario:  # "saio às 18h, depois disso tô livre"
            fim = anterior.ate or anterior.apos
            if fim is None:
                raise ErroTempo("horario_invalido", "depois disso")
            if anterior.negativa and anterior.faixa:  # "aula das 14h às 18h, depois disso pode": valem as duas
                cls.append(_Clausula(fichas=list(anterior.fichas), proxima=anterior.proxima, apos=fim, separador=sep))
            else:
                anterior.apos, anterior.ate, anterior.periodo, anterior.negativa = fim, None, None, False
            continue
        if anterior.ocupacao and k.tem_horario and not k.negativa:
            # "aula até as 22h na segunda e terça. Livre à noite": à noite em que dia, e antes das 22h?
            raise ErroTempo("horario_invalido", "compromisso e horário livre sem dia")
        so_um_limite = not k.periodo and bool(k.apos) != bool(k.ate)
        if so_um_limite and sep != "ou" and anterior.tem_horario and not k.negativa:
            # "à noite, mas tenho que voltar até as 23h": restringe o que já foi dito, não abre outra janela
            for p in cls:
                if p.fichas and p.tem_horario and not p.negativa:
                    if k.ate and (p.ate is None or _ordem(k.ate) < _ordem(p.ate)):
                        p.ate = k.ate
                    if k.apos and (p.apos is None or k.apos > p.apos):
                        p.apos = k.apos
            continue
        if k.tem_horario or k.negativa:  # sem dia herda o último dia dito ("sábado de manhã ou de tarde")
            fonte = next((p for p in reversed(cls) if p.fichas), None)
            if fonte is anterior and not anterior.tem_horario and not anterior.negativa:
                # "sábado, 18 horas", "sábado, não pode": completa o dia dito antes, em vez de abrir outra janela
                anterior.periodo, anterior.apos, anterior.ate = k.periodo, k.apos, k.ate
                anterior.negativa, anterior.partes, anterior.faixa = k.negativa, k.partes, k.faixa
                anterior.ocupacao = k.ocupacao
                continue
            k.fichas, k.proxima = (list(fonte.fichas), fonte.proxima) if fonte else ([], False)
        elif k.vago and not anterior.tem_horario:
            anterior.vago = True
        cls.append(k)
    if any(k.tem_horario and not k.fichas for k in cls):
        raise ErroTempo("falta_dia", "horário sem dia")  # a trava: horário que não achou dia não some
    _semana_que_vem(cls)
    # sem horário herda o da seguinte ("sexta, sábado ou domingo à noite") ou o dito antes de todos os dias
    seguinte = antes_do_dia
    for k in reversed(cls):
        if k.fichas and k.tem_horario:
            seguinte = k
        elif k.fichas and not k.tem_horario and seguinte and not k.negativa:
            k.periodo, k.apos, k.ate = seguinte.periodo, seguinte.apos, seguinte.ate
    cls = [k for k in cls if k.fichas]
    if any((k.vago or k.depois_disso) and not k.tem_horario for k in cls):
        raise ErroTempo("horario_invalido", "horário vago")
    return cls


def _semana_que_vem(cls: list[_Clausula]) -> None:
    """'semana que vem, de segunda a quarta': "semana que vem" qualifica os dias seguintes, não é a semana inteira."""
    i = 0
    while i < len(cls):
        k = cls[i]
        seguintes = cls[i + 1:]
        if (k.fichas == ["semana_que_vem"] and not k.tem_horario and not k.negativa and seguintes
                and seguintes[0].fichas and set(seguintes[0].fichas) <= set(DIAS)):
            for p in seguintes:
                if not p.fichas or not set(p.fichas) <= set(DIAS):
                    break
                p.proxima = True
            del cls[i]
            continue
        i += 1


def _por_regras(texto: str, agora: datetime) -> list[JanelaResolvida]:
    janelas: list[JanelaResolvida] = []
    for k in _clausulas(texto, agora.date()):
        for j in resolver_janelas(k.fichas, k.periodo, k.apos, k.ate, agora, k.proxima,
                                  disponivel=not k.negativa, exigir_dia=True):
            if j not in janelas:
                janelas.append(j)
    return janelas


def _por_llm(texto: str, agora: datetime, llm) -> list[JanelaResolvida]:
    from .interpretar import interpretar

    r = interpretar(texto, contexto="privado", agora=agora, llm=llm)
    return [j for i in r.intencoes if i.tipo == "disponibilidade" and not i.pergunta for j in i.janelas]


def interpretar_horarios(texto: str, agora: datetime, llm=None) -> HorariosInterpretados:
    """Texto livre ("sexta depois das 19h ou sábado à tarde") -> janelas com data e hora, pelo `tempo.py`.

    `agora` é a hora local (America/Sao_Paulo) sem fuso. `llm` (opcional) é o cliente do ADR 0007, usado só
    quando as regras não acham nenhum dia.
    """
    if not texto or not texto.strip():
        return HorariosInterpretados([], pergunta=PERGUNTAS["falta_dia"], motivo="falta_dia")
    origem = "regras"
    try:
        janelas = _por_regras(texto, agora)
    except ErroTempo as e:
        return HorariosInterpretados([], pergunta=PERGUNTAS.get(e.motivo, PERGUNTAS["falta_dia"]), motivo=e.motivo)
    if not janelas and llm is not None:
        janelas, origem = _por_llm(texto, agora, llm), "llm"
    if not janelas:
        return HorariosInterpretados([], pergunta=PERGUNTAS["falta_dia"], motivo="falta_dia", origem=origem)
    futuras = [j for j in janelas if j.fim > agora]
    if not futuras:
        return HorariosInterpretados([], pergunta=PERGUNTAS["janela_passada"], motivo="janela_passada", origem=origem)
    negativas = [j for j in futuras if not j.disponivel]
    futuras = [j for j in futuras if not j.disponivel or
               not any(n.inicio <= j.inicio and j.fim <= n.fim for n in negativas)]
    if not any(j.disponivel for j in futuras):
        return HorariosInterpretados([], pergunta=PERGUNTAS["so_negativa"], motivo="so_negativa", origem=origem)
    partes = [j.texto() + ("" if j.disponivel else " (não pode)") for j in futuras]
    return HorariosInterpretados(futuras, confirmacao="; ".join(partes), origem=origem)


# ---------------------------------------------------------------- campo 3: teto de gasto

def interpretar_teto(texto: str) -> tuple[Decimal | None, str | None]:
    """'60', 'R$ 60,00', 'uns 80 conto' -> (valor, motivo da pergunta). O valor nunca passa por LLM."""
    if not texto or not texto.strip():
        return None, "teto_vazio"
    if re.search(r"\bentre\b|\d\s*(?:reais\s+)?(?:e|a|ou|-|ate)\s*(?:r\$\s*)?\d", canon(texto)):
        return None, "teto_invalido"  # "50 a 70", "entre 50 e 70": no campo de teto é faixa, não centavos
    v = valor_em_reais(texto)
    if v is None or v < 0:
        return None, "teto_invalido"
    if v > TETO_MAXIMO:
        return None, "teto_alto"
    return v.quantize(Decimal("0.01")), None


# ---------------------------------------------------------------- campo 4: preferências e transporte

# Rótulos iguais aos da base de 93 lugares (tipo_de_role e vibes de data/banco_aprovado_2fa.json)
TIPOS: dict[str, str] = {
    "Restaurante / Gastronomia": r"restaurantes?|comer|comida|jantar|almocar|almoco|rodizio|pizza(ria)?|hamburguer(ia)?|burger|sushi|japones|churrasco|lanche|petisco",
    "Bar / Boteco / Pub": r"bar(zinho|es)?|boteco|botequim|pub|cerveja|chopp?|drinks?|happy hour|beber",
    "Cafeteria / Doceria": r"cafe(zinho)?|cafeteria|doces?|doceria|sorvete(ria)?|brunch|bolo|confeitaria|padaria",
    "Experiência / Evento": r"shows?|eventos?|festa|festival|feira|teatro|cinema|exposicao|museu|karaoke|balada|musica ao vivo|boliche|jogos?",
    "Ao Ar Livre / Parque": r"parques?|ar livre|piquenique|natureza|trilha|cachoeira|caminhada|por do sol|sunset|praca",
}
VIBES: dict[str, str] = {
    "Calmo / Bom para Conversar": r"calm[oa]|tranquil[oa]|conversar|sossegad[oa]|silencios[oa]|de boa",
    "Animado / Galera": r"animad[oa]|agitad[oa]|galera|musica ao vivo|dancar|balada|festa",
    "Romântico / Date": r"romantic[oa]|date|casal|namorad[oa]",
    "Baratinho": r"barat(o|a|inho|inha)|economic[oa]|em conta|gastar pouco|gratis|de graca",
    "Cultural / Alternativo": r"cultura(l)?|alternativ[oa]|arte|exposicao|teatro|museu",
    "Kid Friendly": r"criancas?|kids?|filh[oa]s?|familia|brinquedoteca|infantil",
    "Intimista / Aconchegante": r"intimista|aconchegante|aconchego|aconchegad[oa]",
}
# Atributos do contrato da busca (src/interpretador/contrato.py)
RESTRICOES: dict[str, str] = {
    "alim_vegano": r"vegan[oa]s?",
    "alim_vegetariano": r"vegetarian[oa]s?|nao como carne",
    "alim_sem_gluten": r"sem gluten|celiac[oa]|intolerante a gluten",
    "alim_sem_lactose": r"sem lactose|intolerante a lactose",
    "acess_entrada_sem_degrau": r"cadeirante|cadeira de rodas|acessibilidade|mobilidade reduzida|muleta",
}
TRANSPORTES: dict[str, str] = {
    "publico": r"metro|onibus|bus[ao]o?|brt|transporte publico|circular",
    "app": r"uber|99|taxi|aplicativo|app",
    "carro": r"carro|dirigindo|de moto|moto",
    "carona": r"carona",
    "a_pe": r"a pe|andando|caminhando",
    "bike": r"bike|bicicleta|patinete",
}
ROTULOS_TRANSPORTE = {"publico": "ônibus/metrô", "app": "Uber/99", "carro": "carro", "carona": "carona",
                      "a_pe": "a pé", "bike": "bike"}
ROTULOS_RESTRICAO = {"alim_vegano": "vegano", "alim_vegetariano": "vegetariano", "alim_sem_gluten": "sem glúten",
                     "alim_sem_lactose": "sem lactose", "acess_entrada_sem_degrau": "acessibilidade"}


@dataclass
class Preferencias:
    tipos: list[str] = field(default_factory=list)
    vibes: list[str] = field(default_factory=list)
    restricoes: list[str] = field(default_factory=list)
    transporte: list[str] = field(default_factory=list)
    pet: bool = False
    texto_busca: str = ""  # o próprio campo 4, para a busca por texto nos 93 lugares


def _achar(t: str, tabela: dict[str, str]) -> list[str]:
    return [rotulo for rotulo, rx in tabela.items() if re.search(rf"\b(?:{rx})\b", t)]


def interpretar_preferencias(texto: str) -> Preferencias:
    """'Barzinho ou café calmo, sou vegetariana, vou de metrô/Uber' -> tags para buscar nos 93 lugares."""
    t = canon(texto or "")
    restricoes = _achar(t, RESTRICOES)
    if "alim_vegano" in restricoes and "alim_vegetariano" not in restricoes:
        restricoes.append("alim_vegetariano")  # quem é vegano também precisa de opção vegetariana
    return Preferencias(tipos=_achar(t, TIPOS), vibes=_achar(t, VIBES), restricoes=restricoes,
                        transporte=_achar(t, TRANSPORTES), pet=bool(re.search(r"\bpet\b|cachorr|\bdog\b", t)),
                        texto_busca=(texto or "").strip()[:300])


# ---------------------------------------------------------------- os 4 campos juntos

@dataclass
class PerfilInterpretado:
    ra: str | None
    regiao: str | None
    janelas: list[JanelaResolvida]
    teto: Decimal | None
    preferencias: Preferencias
    pendencias: dict[str, str] = field(default_factory=dict)  # campo -> pergunta
    resumo: str = ""

    @property
    def completo(self) -> bool:
        return not self.pendencias

    def para_dono(self) -> dict:
        """Visão do próprio participante (Tela 2). Contém o teto: nunca mandar a outro membro."""
        p = self.preferencias
        return {
            "ra": self.ra, "regiao": self.regiao,
            "janelas": [{"inicio": j.inicio.isoformat(), "fim": j.fim.isoformat(), "disponivel": j.disponivel,
                         "texto": j.texto() + ("" if j.disponivel else " (não pode)")} for j in self.janelas],
            "teto": str(self.teto) if self.teto is not None else None,
            "tipos": p.tipos, "vibes": p.vibes, "restricoes": p.restricoes, "transporte": p.transporte,
            "pet": p.pet, "pendencias": self.pendencias, "resumo": self.resumo, "completo": self.completo,
        }


def _reais(v: Decimal) -> str:
    return "R$ " + f"{v:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def _resumo(local: LocalInterpretado, h: HorariosInterpretados, teto: Decimal | None, p: Preferencias) -> str:
    partes = []
    if h.confirmacao:
        partes.append(h.confirmacao)
    if local.ra:
        partes.append(f"saindo de {local.ra}")
    if teto is not None:
        partes.append(f"teto de {_reais(teto)} (só você vê)")
    gosto = [t.split(" / ")[0] for t in p.tipos] + [v.split(" / ")[0] for v in p.vibes]
    if gosto:
        partes.append("quer: " + ", ".join(gosto))
    if p.restricoes:
        partes.append(", ".join(ROTULOS_RESTRICAO[r] for r in p.restricoes))
    partes.append("vai de " + "/".join(ROTULOS_TRANSPORTE[t] for t in p.transporte) if p.transporte
                  else "transporte não informado (contamos ônibus/metrô)")
    return "; ".join(partes) + "."


def interpretar_campos(origem: str, horarios: str, teto: str, preferencias: str, *, agora: datetime,
                       llm=None) -> PerfilInterpretado:
    """Os 4 campos de texto da Tela 2 -> perfil. `agora` é a hora local sem fuso (America/Sao_Paulo)."""
    local = interpretar_local(origem)
    h = interpretar_horarios(horarios, agora, llm=llm)
    valor, motivo_teto = interpretar_teto(teto)
    prefs = interpretar_preferencias(preferencias)
    pend = {}
    if local.pergunta:
        pend["origem"] = local.pergunta
    if h.pergunta:
        pend["horarios"] = h.pergunta
    if motivo_teto:
        pend["teto"] = PERGUNTAS[motivo_teto]
    return PerfilInterpretado(ra=local.ra, regiao=local.regiao, janelas=h.janelas, teto=valor, preferencias=prefs,
                              pendencias=pend, resumo=_resumo(local, h, valor, prefs))
