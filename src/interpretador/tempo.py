"""Resolve dias e horários normalizados pelo LLM em janelas com data e hora (ADR 0007, seção 2).

O LLM devolve fichas de um vocabulário fechado ("sex", "amanha", "semana_que_vem", "14/11") e o período
("tarde"); a data absoluta e o intervalo saem daqui, com a tabela de convenções da configuração.
Horários são locais de America/Sao_Paulo, sem fuso no objeto (o Brasil não tem horário de verão desde 2019).
"""
import re
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from .config import CFG

T = CFG["tempo"]
DIAS = ["seg", "ter", "qua", "qui", "sex", "sab", "dom"]
DIAS_EXIBICAO = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]
FICHAS_DIA = DIAS + ["hoje", "amanha", "depois_de_amanha", "fim_de_semana", "esta_semana", "semana_que_vem"]


class ErroTempo(ValueError):
    """Expressão que vira pergunta. `motivo` é um código estável (falta_dia, dia_invalido, horario_invalido)."""

    def __init__(self, motivo: str, detalhe: str = ""):
        super().__init__(f"{motivo}: {detalhe}")
        self.motivo = motivo


@dataclass(frozen=True)
class JanelaResolvida:
    inicio: datetime
    fim: datetime
    disponivel: bool = True

    def texto(self) -> str:
        d = self.inicio
        return f"{DIAS_EXIBICAO[d.weekday()]} {d:%d/%m}, {_h(self.inicio.time())}–{_h(self.fim.time(), fim=True)}"


def _h(t: time, fim: bool = False) -> str:
    if fim and t == time(0, 0):
        return "24h"
    return f"{t.hour}h" if t.minute == 0 else f"{t.hour}h{t.minute:02d}"


def _hora(s: str) -> tuple[time, bool]:
    """'19:00' -> (19:00, False); '24:00' -> (00:00, True = dia seguinte)."""
    m = re.fullmatch(r"(\d{1,2}):(\d{2})", s.strip())
    if not m or int(m.group(1)) > 24 or int(m.group(2)) > 59 or (int(m.group(1)) == 24 and int(m.group(2)) > 0):
        raise ErroTempo("horario_invalido", s)
    h = int(m.group(1))
    return (time(0, 0), True) if h == 24 else (time(h, int(m.group(2))), False)


def resolver_dias(fichas: list[str], hoje: date, proxima_semana: bool = False) -> list[date]:
    """Fichas de dia -> datas, em ordem e sem repetição."""
    seg_que_vem = hoje - timedelta(days=hoje.weekday()) + timedelta(days=7)
    datas = []
    for f in fichas:
        f = f.strip().lower()
        if f in DIAS:
            i = DIAS.index(f)
            datas.append(seg_que_vem + timedelta(days=i) if proxima_semana
                         else hoje + timedelta(days=(i - hoje.weekday()) % 7))
        elif f == "hoje":
            datas.append(hoje)
        elif f == "amanha":
            datas.append(hoje + timedelta(days=1))
        elif f == "depois_de_amanha":
            datas.append(hoje + timedelta(days=2))
        elif f == "fim_de_semana":
            if proxima_semana:
                datas += [seg_que_vem + timedelta(days=5), seg_que_vem + timedelta(days=6)]
            elif hoje.weekday() == 6:
                datas.append(hoje)
            else:
                sab = hoje + timedelta(days=(5 - hoje.weekday()) % 7)
                datas += [sab, sab + timedelta(days=1)]
        elif f == "esta_semana":
            datas += [hoje + timedelta(days=k) for k in range(7 - hoje.weekday())]
        elif f == "semana_que_vem":
            datas += [seg_que_vem + timedelta(days=k) for k in range(7)]
        elif m := re.fullmatch(r"(\d{1,2})(?:/(\d{1,2}))?", f):
            datas.append(_data_dia_mes(int(m.group(1)), int(m.group(2)) if m.group(2) else None, hoje))
        else:
            raise ErroTempo("dia_invalido", f)
    vistos = []
    for d in datas:
        if d not in vistos:
            vistos.append(d)
    return sorted(vistos)


def _data_dia_mes(dia: int, mes: int | None, hoje: date) -> date:
    try:
        if mes is None:  # "dia 14": a próxima data com esse dia, a partir de hoje
            d = date(hoje.year, hoje.month, dia)
            if d < hoje:
                d = date(hoje.year + (hoje.month == 12), hoje.month % 12 + 1, dia)
            return d
        d = date(hoje.year, mes, dia)
        return d if d >= hoje else date(hoje.year + 1, mes, dia)
    except ValueError:
        raise ErroTempo("dia_invalido", f"{dia}/{mes}")


def resolver_horario(periodo: str | None, apos: str | None, ate: str | None) -> tuple[time, time, bool]:
    """(início, fim, fim no dia seguinte) a partir do período e dos limites, pela tabela de convenções."""
    ini = fim = None
    if periodo:
        if periodo not in T["periodos"]:
            raise ErroTempo("horario_invalido", periodo)
        ini, fim = T["periodos"][periodo]
    if apos:
        ini = apos
        fim = fim or T["fim_padrao"]
    if ate:
        fim = ate
        ini = ini or T["inicio_padrao"]
    if ini is None:
        ini, fim = T["periodos"]["dia_todo"]
    t_ini, _ = _hora(ini)
    t_fim, seguinte = _hora(fim)
    if not seguinte and t_fim <= t_ini:
        if t_fim <= time(6, 0):  # "de noite até as 2h": passa da meia-noite
            seguinte = True
        else:
            raise ErroTempo("horario_invalido", f"{ini}–{fim}")
    return t_ini, t_fim, seguinte


def resolver_janelas(fichas: list[str], periodo: str | None, apos: str | None, ate: str | None,
                     agora: datetime, proxima_semana: bool = False, disponivel: bool = True,
                     exigir_dia: bool = True) -> list[JanelaResolvida]:
    if not fichas:
        if exigir_dia:
            raise ErroTempo("falta_dia")
        fichas = ["hoje"]
    datas = resolver_dias(fichas, agora.date(), proxima_semana)
    t_ini, t_fim, seguinte = resolver_horario(periodo, apos, ate)
    return [JanelaResolvida(datetime.combine(d, t_ini), datetime.combine(d + timedelta(days=seguinte), t_fim),
                            disponivel) for d in datas]
