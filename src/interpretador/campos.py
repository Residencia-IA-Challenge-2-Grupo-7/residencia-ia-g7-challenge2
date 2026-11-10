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
from datetime import datetime
from decimal import Decimal

from .lugares import casar, ras_validas
from .numeros import canon, valor_em_reais
from .tempo import DIAS, ErroTempo, JanelaResolvida, resolver_janelas

TETO_MAXIMO = Decimal("1000")  # mesmo limite de ConsultaBusca.teto_pessoa

PERGUNTAS = {
    "local_vazio": "De onde você vai sair? Pode ser a RA, a quadra ou um ponto conhecido (ex.: 'Taguatinga Centro', 'SQN 210').",
    "local_desconhecido": "Não reconheci essa região do DF. Pode dizer a RA ou um ponto conhecido (ex.: 'Águas Claras perto da estação')?",
    "local_ambiguo": "Encontrei mais de uma região ({ras}). De qual delas você vai sair?",
    "falta_dia": "Quais dias você pode? Ex.: 'sexta depois das 19h ou sábado à tarde'.",
    "dia_invalido": "Não entendi o dia. Pode dizer o dia da semana ou a data (dd/mm)?",
    "horario_invalido": "Não entendi o horário. De que horas a que horas?",
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
_H = r"(\d{1,2})(?:\s*(?:h|:|horas?)\s*(\d{2})?)?"
_RE_FAIXA = [re.compile(rf"\bd[ae]s?\s+{_H}\s*(?:as|a|ate|-)\s*{_H}"),
             re.compile(rf"\b(\d{{1,2}})\s*(?:h|:)\s*(\d{{2}})?\s*(?:as|ate|a|-)\s*{_H}")]
_RE_APOS = re.compile(rf"\b(?:depois|apos|a partir|partir|desde)\s+(?:d[ae]s?\s+|as\s+)?{_H}")
_RE_ATE = re.compile(rf"\b(?:ate|antes)\s+(?:d[ae]s?\s+|as\s+)?{_H}")
_RE_HORA = re.compile(r"\b(?:as\s+)?(\d{1,2})\s*(?:h|:)\s*(\d{2})?\b")


@dataclass
class HorariosInterpretados:
    janelas: list[JanelaResolvida]
    confirmacao: str | None = None
    pergunta: str | None = None
    motivo: str | None = None
    origem: str = "regras"  # "regras" ou "llm"


@dataclass
class _Clausula:
    fichas: list[str] = field(default_factory=list)
    proxima: bool = False
    periodo: str | None = None
    apos: str | None = None
    ate: str | None = None
    negativa: bool = False

    @property
    def tem_horario(self) -> bool:
        return bool(self.periodo or self.apos or self.ate)


def _hm(h: str | int, m: str | None) -> str:
    h = int(h)
    if h > 24:
        raise ErroTempo("horario_invalido", str(h))
    return f"{h:02d}:{int(m or 0):02d}"


def _tarde_se_curta(h: str, clausula: str) -> int:
    """'depois das 7' sem 'manhã' é de noite: horas de 1 a 6 no início de um rolê viram 13 a 18."""
    h = int(h)
    return h + 12 if 1 <= h <= 6 and not re.search(r"\bmanha\b|madrugada", clausula) else h


def _normalizar_horas(t: str) -> str:
    t = re.sub(r"meia[- ]noite", "24h", t)
    t = re.sub(r"meio[- ]dia", "12h", t)
    t = re.sub(r"\b(\d{1,2})\s*(?:h|horas?)?\s*da (noite|tarde)\b",
               lambda m: f"{int(m.group(1)) + 12 if int(m.group(1)) < 12 else int(m.group(1))}h", t)
    t = re.sub(r"\b(\d{1,2})\s*(?:h|horas?)?\s*da manha\b", lambda m: f"{int(m.group(1))}h", t)
    return t


def _clausula(c: str) -> _Clausula:
    k = _Clausula()
    k.proxima = bool(re.search(r"\bque vem\b|\bproxim[ao]s?\b", c))
    k.negativa = bool(re.search(r"\bnao\b|\bmenos\b|\bexceto\b|\btirando\b", c))

    def tirar(padrao: str) -> bool:
        nonlocal c
        achou = re.search(padrao, c) is not None
        c = re.sub(padrao, " ", c)
        return achou

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
    for m in re.finditer(r"\b(\d{1,2})/(\d{1,2})\b", c):
        k.fichas.append(f"{int(m.group(1))}/{int(m.group(2))}")
    c = re.sub(r"\b(\d{1,2})/(\d{1,2})\b", " ", c)
    for m in re.finditer(r"\bdia\s+(\d{1,2})\b", c):
        k.fichas.append(str(int(m.group(1))))
    c = re.sub(r"\bdia\s+(\d{1,2})\b", " ", c)
    for m in _RE_DIA.finditer(c):
        k.fichas.append(_DIA_PALAVRA[m.group(1)])
    c = _RE_DIA.sub(" ", c)
    if not k.fichas and k.proxima and re.search(r"\bsemana\b", c):
        k.fichas, k.proxima = ["semana_que_vem"], False

    for rx in _RE_FAIXA:
        if m := rx.search(c):
            k.apos = _hm(_tarde_se_curta(m.group(1), c), m.group(2))
            fim = int(m.group(3))
            if int(k.apos[:2]) >= 12 and fim < 12 and fim > 6:  # "das 19 às 11" não existe: "às 11 da noite"
                fim += 12
            k.ate = _hm(fim, m.group(4))
            c = c[:m.start()] + " " + c[m.end():]
            break
    if not k.apos and (m := _RE_APOS.search(c)):
        k.apos = _hm(_tarde_se_curta(m.group(1), c), m.group(2))
        c = c[:m.start()] + " " + c[m.end():]
    if not k.ate and (m := _RE_ATE.search(c)):
        k.ate = _hm(m.group(1), m.group(2))
        c = c[:m.start()] + " " + c[m.end():]
    if not k.apos and not k.ate and (m := _RE_HORA.search(c)):
        k.apos = _hm(_tarde_se_curta(m.group(1), c), m.group(2))  # "sábado às 20h": começa às 20h

    periodos = [p for p, rx in (("manha", r"\bmanha\b"), ("almoco", r"\balmoco\b"), ("tarde", r"\btarde\b"),
                                ("noite", r"\bnoite\b|\bjantar\b"),
                                ("dia_todo", r"\bdia (todo|inteiro)\b|\bqualquer hora(rio)?\b|\bo dia\b"))
                if re.search(rx, c)]
    if periodos:
        ini = min(_PERIODOS[p][0] for p in periodos)
        fim = max(_PERIODOS[p][1] for p in periodos)
        if len(periodos) == 1 and periodos[0] in ("manha", "tarde", "noite", "dia_todo"):
            k.periodo = periodos[0]
        else:  # "tarde e noite", "almoço"
            k.apos = k.apos or ini
            k.ate = k.ate or fim
    return k


def _clausulas(texto: str) -> list[_Clausula]:
    t = _normalizar_horas(canon(texto))
    partes = [p for p in re.split(r"\s+ou\s+|;|,|\s+mas\s+|\.\s|\n", t) if p.strip()]
    cls = [_clausula(p) for p in partes]
    # sem dia herda o dia da anterior ("sábado de manhã ou de tarde")
    for i, k in enumerate(cls):
        if not k.fichas and i > 0 and (k.tem_horario or k.negativa):
            k.fichas, k.proxima = list(cls[i - 1].fichas), cls[i - 1].proxima
    # sem horário herda o da seguinte ("sexta, sábado ou domingo à noite")
    seguinte = None
    for k in reversed(cls):
        if k.fichas and k.tem_horario:
            seguinte = k
        elif k.fichas and not k.tem_horario and seguinte and not k.negativa:
            k.periodo, k.apos, k.ate = seguinte.periodo, seguinte.apos, seguinte.ate
    return [k for k in cls if k.fichas]


def _por_regras(texto: str, agora: datetime) -> list[JanelaResolvida]:
    janelas: list[JanelaResolvida] = []
    for k in _clausulas(texto):
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
                         "texto": j.texto()} for j in self.janelas],
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
