"""Lê o campo livre `horario_funcionamento` da base de 93 lugares e diz se o lugar abre numa janela (RF-17).

O campo vem da legenda e do áudio dos vídeos e não tem formato fixo: "Terça a domingo: 17h às 23h30",
"Almoço de segunda a sexta", "8 a 10 de maio", "Consultar no local". Por isso a resposta tem cinco níveis:

| Situação    | Quando                                                        | Na sugestão            |
|-------------|---------------------------------------------------------------|------------------------|
| `aberto`    | dia e horário batem com a janela por pelo menos 1h30           | entra                  |
| `provavel`  | o dia bate, mas o texto não diz o horário                      | entra, "confirme"      |
| `incerto`   | o texto não diz nada que dê para ler ("Consultar no local")    | entra, "confirme"      |
| `fechado`   | o texto diz os dias ou horários e a janela fica fora           | descartado             |
| `encerrado` | evento ou promoção com datas que já passaram                   | descartado (RNF-03)    |
"""
from __future__ import annotations

import calendar
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from src.interpretador.numeros import canon

_DIAS = {"segunda": 0, "terca": 1, "quarta": 2, "quinta": 3, "sexta": 4, "sabado": 5, "domingo": 6}
_RE_DIA = r"(segunda|terca|quarta|quinta|sexta|sabado|domingo)s?(?:[- ]feiras?)?"
_MESES = {m: i for i, m in enumerate(["janeiro", "fevereiro", "marco", "abril", "maio", "junho", "julho", "agosto",
                                       "setembro", "outubro", "novembro", "dezembro"], start=1)}
_PERIODOS = {r"\balmoco\b": (11 * 60, 15 * 60), r"\bjantar\b": (18 * 60, 23 * 60), r"\bnoites?\b": (18 * 60, 24 * 60),
             r"\bhappy hour\b": (17 * 60, 20 * 60), r"\bsunset\b": (16 * 60, 19 * 60), r"\bmanha\b": (8 * 60, 12 * 60)}
_H = r"(\d{1,2})(?:h|:)(\d{2})?"
_RE_FAIXA = re.compile(rf"\b{_H}\s*(?:as|a|-|ate)\s*(\d{{1,2}})(?:h|:)?(\d{{2}})?")
_RE_A_PARTIR = re.compile(rf"\b(?:a partir d[ae]s?|depois d[ae]s?)\s*{_H}")
SOBREPOSICAO_MINIMA = 90  # minutos: menos que isso não dá um rolê
_RE_ATE = re.compile(rf"\bate\s+(?:as\s+)?{_H}|\bate meio[- ]dia\b")


@dataclass
class Regra:
    dias: set[int] | None          # None = todos os dias
    inicio: int | None = None      # minutos desde 00:00; fim pode passar de 1440 (fecha depois da meia-noite)
    fim: int | None = None
    fechado: bool = False


@dataclass
class Funcionamento:
    regras: list[Regra] = field(default_factory=list)
    datas: set[date] = field(default_factory=set)
    valido_ate: date | None = None

    def situacao(self, inicio: datetime, fim: datetime) -> tuple[str, tuple[datetime, datetime] | None]:
        """(situação, trecho da janela em que o lugar está aberto, quando se sabe)."""
        dia = inicio.date()
        if self.valido_ate and dia > self.valido_ate:
            return "encerrado", None
        if self.datas:
            if max(self.datas) < dia:
                return "encerrado", None
            if dia not in self.datas:
                return "fechado", None
        if not self.regras:
            return ("provavel", None) if self.datas else ("incerto", None)
        wd = inicio.weekday()
        if any(r.fechado and r.dias and wd in r.dias for r in self.regras):
            return "fechado", None
        do_dia = [r for r in self.regras if not r.fechado and (r.dias is None or wd in r.dias)]
        if not do_dia:
            return "fechado", None
        com_hora = [r for r in do_dia if r.inicio is not None]
        if not com_hora:
            return "provavel", None
        base = datetime.combine(dia, datetime.min.time())
        j_ini = (inicio - base).total_seconds() / 60
        j_fim = (fim - base).total_seconds() / 60
        melhor = None
        for r in com_hora:
            ini, fi = max(j_ini, r.inicio), min(j_fim, r.fim)
            if fi - ini >= SOBREPOSICAO_MINIMA and (melhor is None or fi - ini > melhor[1] - melhor[0]):
                melhor = (ini, fi)
        if melhor is None:
            return "fechado", None
        return "aberto", (base + timedelta(minutes=melhor[0]), base + timedelta(minutes=melhor[1]))


def _min(h: str, m: str | None) -> int:
    return int(h) * 60 + int(m or 0)


def _dias(seg: str) -> tuple[set[int] | None, str]:
    """Dias citados no trecho (com intervalos "terça a domingo", que podem dar a volta) e o resto do texto."""
    if re.search(r"todos os dias|todas as noites|diariamente|todo dia|segunda a domingo|segunda a segunda", seg):
        return set(range(7)), seg
    dias: set[int] = set()
    for m in re.finditer(rf"{_RE_DIA}\s+(?:a|ate)\s+{_RE_DIA}", seg):
        a, b = _DIAS[m.group(1)], _DIAS[m.group(2)]
        dias |= {(a + k) % 7 for k in range((b - a) % 7 + 1)}
    seg_sem = re.sub(rf"{_RE_DIA}\s+(?:a|ate)\s+{_RE_DIA}", " ", seg)
    dias |= {_DIAS[m.group(1)] for m in re.finditer(rf"\b{_RE_DIA}\b", seg_sem)}
    if re.search(r"\bfins? de semana|finais de semana", seg):
        dias |= {5, 6}
    return (dias or None), seg


def _datas(texto: str, ano: int) -> tuple[set[date], date | None]:
    datas: set[date] = set()
    for m in re.finditer(r"\b(\d{1,2})/(\d{1,2})\b", texto):
        try:
            datas.add(date(ano, int(m.group(2)), int(m.group(1))))
        except ValueError:
            pass
    valido_ate = None
    if m := re.search(r"ate o (?:final|fim) de (" + "|".join(_MESES) + ")", texto):
        mes = _MESES[m.group(1)]
        valido_ate = date(ano, mes, calendar.monthrange(ano, mes)[1])
    for m in re.finditer(r"([\d\s,ae°º]+?)\s*de\s+(" + "|".join(_MESES) + r")\b", texto):
        mes = _MESES[m.group(2)]
        nums = [int(n) for n in re.findall(r"\d{1,2}", m.group(1))]
        if re.search(r"\d\s+a\s+\d", m.group(1)) and len(nums) == 2:
            nums = list(range(nums[0], nums[1] + 1))
        for n in nums:
            try:
                datas.add(date(ano, mes, n))
            except ValueError:
                pass
    return datas, valido_ate


def ler_funcionamento(texto: str | None, ano: int) -> Funcionamento:
    """`ano`: o do vídeo (campo `ano_mes`), porque as datas da legenda não trazem o ano."""
    t = canon(texto or "")
    t = re.sub(r"\(.*?\)", lambda m: " " + m.group(0)[1:-1] + " ", t)
    datas, valido_ate = _datas(t, ano)
    f = Funcionamento(datas=datas, valido_ate=valido_ate)
    for seg in re.split(r"[;,/]|\.\s|\.$", t):
        seg = seg.strip()
        if not seg:
            continue
        dias, _ = _dias(seg)
        if dias and re.search(r"\bfechad[oa]\b", seg):
            f.regras.append(Regra(dias, fechado=True))
            continue
        faixas = []
        for m in _RE_FAIXA.finditer(seg):
            ini, fim = _min(m.group(1), m.group(2)), _min(m.group(3), m.group(4))
            faixas.append((ini, fim + 1440 if fim <= ini else fim))
        if not faixas and (m := _RE_A_PARTIR.search(seg)):
            faixas.append((_min(m.group(1), m.group(2)), 24 * 60))
        if not faixas and (m := _RE_ATE.search(seg)):
            faixas.append((8 * 60, 12 * 60 if "meio" in m.group(0) else _min(m.group(1), m.group(2))))
        if not faixas:
            faixas = [v for rx, v in _PERIODOS.items() if re.search(rx, seg)]
        if faixas:
            f.regras += [Regra(dias, ini, fim) for ini, fim in faixas]
        elif dias:
            f.regras.append(Regra(dias))
    return f


def ano_do_lugar(lugar: dict, padrao: int) -> int:
    m = re.match(r"(\d{4})", str(lugar.get("ano_mes") or ""))
    return int(m.group(1)) if m else padrao
