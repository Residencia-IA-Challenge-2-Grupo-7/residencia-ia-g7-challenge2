"""Cruzamento das disponibilidades da sala (RF-13), por código (RNF-04).

Cada participante tem janelas em que pode (`disponivel=True`) e em que não pode ("sexta não posso").
A disponibilidade dele é a união das primeiras menos as segundas; quem só disse o que não pode fica livre
nos próximos 7 dias, das 8h à meia-noite, menos isso.

O cruzamento varre os instantes em que alguém entra ou sai e devolve os trechos com mais gente, de pelo
menos 2 horas (ou 1 hora, se não houver nenhum de 2). Ordem: mais participantes, depois a mais próxima
de agora (regra padrão do RF-14). Para o grupo, só sai a contagem ("5 de 7 podem"), nunca quem não pode.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta

from src.interpretador.tempo import JanelaResolvida

Intervalo = tuple[datetime, datetime]
DIAS_SEMANA = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]


@dataclass(frozen=True)
class JanelaComum:
    inicio: datetime
    fim: datetime
    presentes: frozenset[str]  # ids dos participantes; fica no servidor
    total: int

    @property
    def contagem(self) -> str:
        return f"{len(self.presentes)} de {self.total} podem"

    def texto(self) -> str:
        return texto_intervalo(self.inicio, self.fim)


def _h(t: datetime, fim: bool = False) -> str:
    if fim and t.time() == time(0, 0):
        return "24h"
    return f"{t.hour}h" if t.minute == 0 else f"{t.hour}h{t.minute:02d}"


def texto_intervalo(inicio: datetime, fim: datetime) -> str:
    return f"{DIAS_SEMANA[inicio.weekday()]} {inicio:%d/%m}, {_h(inicio)}–{_h(fim, fim=True)}"


def _juntar(iv: list[Intervalo]) -> list[Intervalo]:
    saida: list[Intervalo] = []
    for a, b in sorted(iv):
        if saida and a <= saida[-1][1]:
            saida[-1] = (saida[-1][0], max(saida[-1][1], b))
        else:
            saida.append((a, b))
    return saida


def _menos(pos: list[Intervalo], neg: list[Intervalo]) -> list[Intervalo]:
    for n0, n1 in neg:
        novo = []
        for a, b in pos:
            if n1 <= a or n0 >= b:
                novo.append((a, b))
                continue
            if a < n0:
                novo.append((a, n0))
            if n1 < b:
                novo.append((n1, b))
        pos = novo
    return pos


def disponibilidade(janelas: list[JanelaResolvida], agora: datetime, horizonte: timedelta) -> list[Intervalo]:
    pos = [(j.inicio, j.fim) for j in janelas if j.disponivel]
    neg = [(j.inicio, j.fim) for j in janelas if not j.disponivel]
    if not pos and neg:
        d0 = agora.date()
        pos = [(datetime.combine(d0 + timedelta(days=k), time(8)), datetime.combine(d0 + timedelta(days=k + 1), time(0)))
               for k in range(7)]
    limite = agora + horizonte
    pos = [(max(a, agora), min(b, limite)) for a, b in pos if b > agora and a < limite]
    return _juntar(_menos(_juntar(pos), neg))


def cruzar(disponiveis: dict[str, list[JanelaResolvida]], agora: datetime, *, minimo_pessoas: int = 2,
           duracao: timedelta = timedelta(hours=2), horizonte: timedelta = timedelta(days=21),
           maximo: int = 5) -> list[JanelaComum]:
    """{participante: janelas} -> as melhores janelas comuns."""
    total = len(disponiveis)
    disp = {p: disponibilidade(j, agora, horizonte) for p, j in disponiveis.items()}
    pontos = sorted({t for iv in disp.values() for a, b in iv for t in (a, b)})
    trechos: list[tuple[datetime, datetime, frozenset[str]]] = []
    for a, b in zip(pontos, pontos[1:]):
        quem = frozenset(p for p, iv in disp.items() if any(x <= a and b <= y for x, y in iv))
        if len(quem) < minimo_pessoas:
            continue
        if trechos and trechos[-1][1] == a and trechos[-1][2] == quem:
            trechos[-1] = (trechos[-1][0], b, quem)
        else:
            trechos.append((a, b, quem))
    for minimo in (duracao, timedelta(hours=1)):
        candidatas = [JanelaComum(a, b, q, total) for a, b, q in trechos if b - a >= minimo]
        if candidatas:
            candidatas.sort(key=lambda j: (-len(j.presentes), j.inicio))
            return candidatas[:maximo]
    return []
