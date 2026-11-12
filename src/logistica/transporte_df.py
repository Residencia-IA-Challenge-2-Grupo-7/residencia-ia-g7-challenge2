"""Deslocamento até os lugares do rolê no DF, calculado por código (RNF-04).

Nada aqui chama LLM nem rede: as mesmas entradas dão sempre a mesma saída, o que
deixa os números testáveis e defensáveis no relatório.

Esta primeira peça é a distância em linha reta entre dois pontos (fórmula de
Haversine). Tempo, custo e a nota de justiça (Menor Miséria) se apoiam nela.
"""
from __future__ import annotations

import math

Ponto = tuple[float, float]
"""(latitude, longitude) em graus decimais. No DF, as duas são negativas."""

RAIO_TERRA_KM = 6371.0
"""Raio médio da Terra. É o mesmo valor da reserva de src/salas/integracoes.py,
para as duas contas darem o mesmo número."""


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
