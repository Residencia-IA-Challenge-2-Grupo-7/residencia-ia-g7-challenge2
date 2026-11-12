"""Deslocamento até os lugares do rolê no DF, calculado por código (RNF-04).

Nada aqui chama LLM nem rede: as mesmas entradas dão sempre a mesma saída, o que
deixa os números testáveis e defensáveis no relatório.

Peças, na ordem em que uma depende da outra:

1. `haversine_km`: distância em linha reta entre dois pontos (lat, lng).
2. `resolver_ra` e `ponto_da_ra`: nome da RA -> ponto de referência em
   data/regioes_df_gps.json.
3. `calcular_distancia_km`: da RA de origem até um lugar (coordenadas ou um
   registro da base de 93).

Tempo, custo e a nota de justiça (Menor Miséria) se apoiam nelas.
"""
from __future__ import annotations

import json
import math
from collections.abc import Mapping
from functools import lru_cache
from pathlib import Path

from src.interpretador.lugares import casar

Ponto = tuple[float, float]
"""(latitude, longitude) em graus decimais. No DF, as duas são negativas."""

RAIO_TERRA_KM = 6371.0
"""Raio médio da Terra. É o mesmo valor da reserva de src/salas/integracoes.py,
para as duas contas darem o mesmo número."""

ARQUIVO_REGIOES = Path(__file__).resolve().parents[2] / "data" / "regioes_df_gps.json"


def _validar(ponto: Ponto) -> tuple[float, float]:
    """Falha cedo com uma mensagem clara, em vez de devolver uma distância sem sentido."""
    lat, lng = float(ponto[0]), float(ponto[1])
    if not (math.isfinite(lat) and math.isfinite(lng)) or abs(lat) > 90 or abs(lng) > 180:
        raise ValueError(f"coordenada inválida (lat, lng): {ponto!r}")
    return lat, lng


def haversine_km(origem: Ponto, destino: Ponto) -> float:
    """Distância em km entre dois pontos (lat, lng), em linha reta sobre a superfície da Terra.

    É a distância "em voo de pássaro": a rua de verdade é mais longa, e o fator de rota
    entra depois, no cálculo do tempo. Tratar a Terra como esfera erra menos de 0,5%.
    """
    lat1, lng1 = map(math.radians, _validar(origem))
    lat2, lng2 = map(math.radians, _validar(destino))
    a = (math.sin((lat2 - lat1) / 2) ** 2
         + math.cos(lat1) * math.cos(lat2) * math.sin((lng2 - lng1) / 2) ** 2)
    # min(1.0, ...): em pontos quase opostos do globo o arredondamento pode passar de 1,
    # e asin de um número maior que 1 levanta ValueError.
    return 2 * RAIO_TERRA_KM * math.asin(min(1.0, math.sqrt(a)))


# ---------------------------------------------------------------- RA de origem


@lru_cache(maxsize=1)
def _regioes() -> dict[str, Ponto]:
    """Os 35 pontos de referência, lidos do disco uma vez só por processo."""
    dados = json.loads(ARQUIVO_REGIOES.read_text(encoding="utf-8"))
    return {r["nome"]: (float(r["lat"]), float(r["lng"])) for r in dados}


def resolver_ra(nome: str) -> str:
    """Nome de RA como vier ("aguas claras", "Asa Sul", "Plano Piloto (Asa Sul)") -> nome oficial.

    Usa o mesmo casamento do interpretador (src/interpretador/lugares.py): aceita sem acento,
    em maiúsculas e os apelidos do config.toml. Não é o interpretador: quadra ("SQN 210") e
    texto livre são trabalho do campos.py, que já entrega uma das 35 RAs.

    A mensagem de erro não repete o que foi digitado: a origem é um dos 4 campos secretos
    e não deve parar em log.
    """
    ras, _, _ = casar([str(nome or "")])
    if not ras:
        raise ValueError("o nome não corresponde a nenhuma das 35 RAs do DF")
    if len(ras) > 1:
        raise ValueError(f"o nome corresponde a {len(ras)} RAs; informe uma só")
    return ras[0]


def ponto_da_ra(nome: str) -> Ponto:
    """Ponto de referência (centro urbano) da RA, aceitando o nome como `resolver_ra` aceita."""
    return _regioes()[resolver_ra(nome)]


# ---------------------------------------------------------------- distância até o lugar


def _ponto_do_local(local: Ponto | Mapping) -> Ponto:
    """(lat, lng) ou um registro da base com as chaves 'lat' e 'lng'."""
    if isinstance(local, Mapping):
        lat, lng = local.get("lat"), local.get("lng")
        if lat is None or lng is None:
            nome = local.get("nome") or local.get("id") or "sem nome"
            raise ValueError(f"lugar sem coordenadas: {nome}")
        return (lat, lng)
    return local


def calcular_distancia_km(origem_ra: str, local_gps: Ponto | Mapping) -> float:
    """Distância em km, em linha reta, do ponto de referência da RA de origem até o lugar.

    `local_gps` pode ser (lat, lng) ou um registro de data/banco_aprovado_2fa.json. O valor é
    o da Haversine, sem ajuste: dentro da mesma RA pode dar 0 km, porque muitos lugares da
    base estão no centro da RA. O mínimo realista entra no cálculo do tempo.
    """
    return haversine_km(ponto_da_ra(origem_ra), _ponto_do_local(local_gps))
