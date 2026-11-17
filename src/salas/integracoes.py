"""Pontos de encaixe com os módulos das colegas (guia oficial, semana 3), com uma reserva simples enquanto eles não chegam.

| Peça                         | Dona     | O que este arquivo espera encontrar                                              | Reserva usada até lá                          |
|------------------------------|----------|----------------------------------------------------------------------------------|-----------------------------------------------|
| Teto seguro do grupo         | Eduarda  | `src.financas` com `teto_seguro_grupo(tetos: list[Decimal]) -> Decimal`          | o menor teto                                  |
| Deslocamento no DF           | Samara   | `src.logistica.transporte_df.estimar_deslocamento(ra_origem, lat, lng, modo) -> dict` com `km`, `minutos`, `custo_ida_volta` | linha reta entre centroides × 1,3, velocidades e tarifa fixas |
| Nota de justiça (Menor Miséria) | Samara | `src.logistica.transporte_df.nota_menor_miseria(deslocamentos: list[dict]) -> float` (0 a 100) | 100 menos o pior tempo e a diferença entre o pior e o melhor; 30 quando não há como medir |
| Aderência ao pedido          | Letícia  | `src.telemetria.telemetria.calcular_similaridade_leticia(pergunta, lugar)`       | contagem de tags iguais                        |

Se a assinatura das colegas mudar, só este arquivo muda. Nada aqui recebe o teto de uma pessoa identificada:
só a lista de tetos, sem nomes (RNF-02).
"""
from __future__ import annotations

import importlib
import inspect
import json
import math
import re
from decimal import Decimal
from functools import lru_cache
from pathlib import Path

from src.interpretador.lugares import casar

RAIZ = Path(__file__).resolve().parents[2]
TARIFA_PUBLICO = Decimal("5.50")  # passagem de ônibus/metrô no DF (guia oficial)
VELOCIDADE_KMH = {"publico": 18, "app": 30, "carro": 30, "carona": 30, "a_pe": 4.5, "bike": 12}
ESPERA_MIN = {"publico": 15, "app": 5, "carro": 5, "carona": 5, "a_pe": 0, "bike": 0}
FATOR_ROTA = 1.3  # a rua não é linha reta


def _funcao(modulos: list[str], nome: str):
    for m in modulos:
        try:
            f = getattr(importlib.import_module(m), nome, None)
        except ImportError:
            continue
        if callable(f):
            return f
    return None


# ---------------------------------------------------------------- teto do grupo (Eduarda)

def teto_do_grupo(tetos: list[Decimal]) -> Decimal | None:
    if not tetos:
        return None
    f = _funcao(["src.financas", "src.financas.teto", "src.financas.financas"], "teto_seguro_grupo")
    if f:
        return Decimal(str(f(list(tetos))))
    return min(tetos)


# ---------------------------------------------------------------- deslocamento (Samara)

def ra_do_lugar(lugar: dict) -> str | None:
    """'Plano Piloto (Asa Sul)' -> 'Plano Piloto'; 'Plano Piloto (Sudoeste)' -> 'Sudoeste/Octogonal'.

    O que vem entre parênteses é o mais específico: se ele corresponde a uma RA só, é ela. Senão, fica com a
    primeira RA citada no texto."""
    texto = str(lugar.get("regiao_administrativa") or "")
    dentro = re.search(r"\(([^)]*)\)", texto)
    if dentro:
        ras, _, _ = casar([dentro.group(1)])
        if len(ras) == 1:
            return ras[0]
    ras, _, _ = casar([texto])
    return ras[0] if ras else None


@lru_cache(maxsize=1)
def _centroides() -> dict[str, tuple[float, float]]:
    """Centroides das RAs: o arquivo da Samara, se existir; senão, a média das coordenadas da base (que já são
    centroides de RA, conforme `fonte_validacao_fator2`)."""
    arq = RAIZ / "data" / "regioes_df_gps.json"
    if arq.exists():
        try:
            dados = json.loads(arq.read_text(encoding="utf-8"))
            itens = dados.items() if isinstance(dados, dict) else (
                (d.get("ra") or d.get("nome") or d.get("regiao_administrativa"), d) for d in dados)
            out = {}
            for nome, d in itens:
                ras, _, _ = casar([str(nome)])
                if ras and d.get("lat") is not None and d.get("lng", d.get("lon")) is not None:
                    out.setdefault(ras[0], (float(d["lat"]), float(d.get("lng", d.get("lon")))))
            if out:
                return out
        except (ValueError, AttributeError, TypeError):
            pass
    soma: dict[str, list[float]] = {}
    for lugar in carregar_lugares():
        ra = ra_do_lugar(lugar)
        if ra and lugar.get("lat") is not None and lugar.get("lng") is not None:
            s = soma.setdefault(ra, [0.0, 0.0, 0])
            s[0] += float(lugar["lat"])
            s[1] += float(lugar["lng"])
            s[2] += 1
    return {ra: (s[0] / s[2], s[1] / s[2]) for ra, s in soma.items()}


def _km(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))


def _tarifa_zero(quando) -> bool:
    """Domingo ou feriado (Vai de Graça): a regra da Samara, se existir; senão, só os domingos."""
    if quando is None:
        return False
    f = _funcao(["src.logistica.transporte_df", "src.logistica"], "tarifa_zero")
    return bool(f(quando)) if f else quando.weekday() == 6


def _custo_ida_volta(modo: str, km: float, quando=None) -> Decimal:
    k = Decimal(str(round(km, 1)))
    custo = {"publico": Decimal("0") if _tarifa_zero(quando) else TARIFA_PUBLICO * 2, "app": (Decimal("5") + Decimal("2.20") * k) * 2,
             "carro": Decimal("0.90") * k * 2}.get(modo, Decimal("0"))
    return custo.quantize(Decimal("0.01"))


def deslocamento(ra_origem: str | None, lugar: dict, modo: str, quando=None) -> dict | None:
    """{'km', 'minutos', 'custo_ida_volta', 'modo', 'estimado_por'} ou None se não houver como estimar.

    `quando`: início do rolê (datetime). Num domingo ou feriado, ônibus e metrô saem de graça (Vai de Graça)."""
    lat, lng = lugar.get("lat"), lugar.get("lng")
    if ra_origem is None or lat is None or lng is None:
        return None
    f = _funcao(["src.logistica.transporte_df", "src.logistica"], "estimar_deslocamento")
    if f:
        aceita_data = "quando" in inspect.signature(f).parameters
        r = f(ra_origem, float(lat), float(lng), modo, quando=quando) if aceita_data else \
            f(ra_origem, float(lat), float(lng), modo)
        if r:
            return {"km": float(r["km"]), "minutos": float(r["minutos"]),
                    "custo_ida_volta": Decimal(str(r["custo_ida_volta"])), "modo": modo, "estimado_por": "logistica"}
    c = _centroides().get(ra_origem)
    if c is None:
        return None
    km = _km(c, (float(lat), float(lng))) * FATOR_ROTA
    minutos = ESPERA_MIN.get(modo, 10) + km / VELOCIDADE_KMH.get(modo, 18) * 60
    return {"km": round(km, 1), "minutos": round(minutos), "custo_ida_volta": _custo_ida_volta(modo, km, quando),
            "modo": modo, "estimado_por": "reserva"}


def nota_justica(deslocamentos: list[dict]) -> float:
    """0 a 100. Menor Miséria: protege quem fica pior (o maior tempo pesa mais que a média)."""
    if not deslocamentos:
        return 30.0  # sem como medir o deslocamento: a incerteza pesa contra o lugar
    f = _funcao(["src.logistica.transporte_df", "src.logistica"], "nota_menor_miseria")
    if f:
        return float(f(deslocamentos))
    tempos = [d["minutos"] for d in deslocamentos]
    pior, melhor = max(tempos), min(tempos)
    penalidade = 0.8 * max(0.0, pior - 20) + 0.3 * (pior - melhor)
    return round(100 * 100 / (100 + penalidade), 1)  # mesma curva da Samara: nunca zera


# ---------------------------------------------------------------- aderência ao pedido (Letícia)

def aderencia(texto: str, lugar: dict) -> float | None:
    """0 a 1 pela busca da Letícia, ou None se ela não estiver disponível."""
    if not texto.strip():
        return None
    f = _funcao(["src.telemetria.telemetria"], "calcular_similaridade_leticia")
    if not f:
        return None
    try:
        return max(0.0, min(1.0, float(f(texto, lugar))))
    except Exception:  # a busca não pode derrubar a sala (RNF-15)
        return None


# ---------------------------------------------------------------- base de 93 lugares (Letícia)

@lru_cache(maxsize=1)
def carregar_lugares() -> tuple[dict, ...]:
    arq = RAIZ / "data" / "banco_aprovado_2fa.json"
    return tuple(json.loads(arq.read_text(encoding="utf-8"))) if arq.exists() else ()
