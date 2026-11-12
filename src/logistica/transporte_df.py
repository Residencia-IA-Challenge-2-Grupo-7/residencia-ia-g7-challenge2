"""Deslocamento até os lugares do rolê no DF, calculado por código (RNF-04).

Nada aqui chama LLM nem rede: as mesmas entradas dão sempre a mesma saída, o que
deixa os números testáveis e defensáveis no relatório.

Peças, na ordem em que uma depende da outra:

1. `haversine_km`: distância em linha reta entre dois pontos (lat, lng).
2. `resolver_ra` e `ponto_da_ra`: nome da RA -> ponto de referência em
   data/regioes_df_gps.json.
3. `calcular_distancia_km`: da RA de origem até um lugar (coordenadas ou um
   registro da base de 93).
4. `distancia_por_rua_km`, `estimar_tempo_ida_min` e `tempos_de_ida_min`: o
   caminho por rua e o tempo de ida em cada meio de transporte.
5. `estimar_custo_ida_volta`: quanto a pessoa gasta para ir e voltar.
6. `estimar_deslocamento`: o encaixe com as salas (src/salas/integracoes.py),
   que junta distância, tempo e custo de uma pessoa num dicionário só.

A nota de justiça (Menor Miséria) se apoia nelas.
"""
from __future__ import annotations

import json
import math
from collections.abc import Mapping
from decimal import Decimal
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


@lru_cache(maxsize=64)
def resolver_ra(nome: str) -> str:
    """Nome de RA como vier ("aguas claras", "Asa Sul", "Plano Piloto (Asa Sul)") -> nome oficial.

    Usa o mesmo casamento do interpretador (src/interpretador/lugares.py): aceita sem acento,
    em maiúsculas e os apelidos do config.toml. Não é o interpretador: quadra ("SQN 210") e
    texto livre são trabalho do campos.py, que já entrega uma das 35 RAs.

    A mensagem de erro não repete o que foi digitado: a origem é um dos 4 campos secretos
    e não deve parar em log.

    Fica em cache porque as salas chamam esta função milhares de vezes por sala (cada pessoa
    x cada lugar x cada meio), sempre com os mesmos poucos nomes. Erros não entram no cache.
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


# ---------------------------------------------------------------- tempo de ida

MODOS = ("publico", "app", "carro", "carona", "a_pe", "bike")
"""Os meios que o campo 4 da Tela 2 reconhece (src/interpretador/campos.py)."""

# Os três números abaixo são os mesmos da reserva de src/salas/integracoes.py, para os
# cartões não mudarem quando este módulo entrar no lugar dela. São estimativas, não medições.

FATOR_ROTA = 1.3
"""A rua não é linha reta: o caminho de verdade fica cerca de 30% mais longo."""

VELOCIDADE_KMH = {"publico": 18, "app": 30, "carro": 30, "carona": 30, "a_pe": 4.5, "bike": 12}
"""Velocidade média no trajeto, já contando trânsito, semáforos e paradas."""

ESPERA_MIN = {"publico": 15, "app": 5, "carro": 5, "carona": 5, "a_pe": 0, "bike": 0}
"""Tempo fixo além do trajeto: andar até a parada e esperar, chamar o app, estacionar."""

DISTANCIA_MINIMA_KM = 2.0
"""Piso do caminho por rua. Origem e lugar no mesmo ponto (o centro da RA) dariam 0 km e
0 min, mas ninguém mora em cima do lugar: 2 km é uma volta dentro da própria RA."""


def _checar_modo(modo: str) -> str:
    if modo not in VELOCIDADE_KMH:
        raise ValueError(f"meio de transporte desconhecido: {modo!r}; use um de: {', '.join(MODOS)}")
    return modo


def distancia_por_rua_km(distancia_reta_km: float) -> float:
    """Linha reta -> estimativa do caminho por rua, nunca abaixo de DISTANCIA_MINIMA_KM."""
    km = float(distancia_reta_km)
    if not math.isfinite(km) or km < 0:
        raise ValueError("distância inválida: precisa ser um número maior ou igual a zero")
    return max(DISTANCIA_MINIMA_KM, km * FATOR_ROTA)


def estimar_tempo_ida_min(km_por_rua: float, modo: str) -> float:
    """Minutos de ida pelo meio escolhido: tempo fixo + trajeto na velocidade média.

    Recebe o caminho por rua (`distancia_por_rua_km`), não a linha reta.
    """
    _checar_modo(modo)
    return ESPERA_MIN[modo] + km_por_rua / VELOCIDADE_KMH[modo] * 60


def tempos_de_ida_min(origem_ra: str, local_gps: Ponto | Mapping) -> dict[str, float]:
    """Tempo de ida da RA até o lugar em cada meio, para comparar carro/app com ônibus/metrô."""
    km = distancia_por_rua_km(calcular_distancia_km(origem_ra, local_gps))
    return {modo: estimar_tempo_ida_min(km, modo) for modo in MODOS}


# ---------------------------------------------------------------- custo de ida e volta

# Mesmos valores da reserva de src/salas/integracoes.py. São estimativas por pessoa.

TARIFA_PUBLICO = Decimal("5.50")
"""Passagem de ônibus/metrô por trecho. É a tarifa do metrô e o teto da integração (até 3
embarques em 3 h); trechos curtos custam R$ 2,70 ou R$ 3,80, então é um teto, não a média.
Congelada até 31/12/2026. Aos domingos e feriados o programa Vai de Graça zera a tarifa,
o que este cálculo não sabe: o contrato com as salas não recebe a data."""

APP_BANDEIRADA = Decimal("5")
APP_POR_KM = Decimal("2.20")
"""Corrida de app (Uber/99): bandeirada mais preço por km."""

CARRO_POR_KM = Decimal("0.90")
"""Gasto do carro próprio por km rodado (combustível e desgaste)."""

# Carona, a pé e bike não têm custo para a pessoa.


def estimar_custo_ida_volta(km_por_rua: float, modo: str) -> Decimal:
    """Reais para ir e voltar pelo meio escolhido, com 2 casas decimais.

    Recebe o caminho por rua (`distancia_por_rua_km`). Dinheiro em Decimal, nunca float:
    0.1 + 0.2 em float dá 0.30000000000000004, e conta de dinheiro não pode ter isso.
    """
    _checar_modo(modo)
    km = Decimal(str(round(km_por_rua, 1)))
    por_trecho = {
        "publico": TARIFA_PUBLICO,
        "app": APP_BANDEIRADA + APP_POR_KM * km,
        "carro": CARRO_POR_KM * km,
    }.get(modo, Decimal("0"))
    return (por_trecho * 2).quantize(Decimal("0.01"))


# ---------------------------------------------------------------- encaixe com as salas


def estimar_deslocamento(ra_origem: str, lat: float, lng: float, modo: str) -> dict | None:
    """Distância, tempo e custo de uma pessoa até um lugar, no formato que as salas esperam.

    É a função que src/salas/integracoes.py procura pelo nome (contrato no README das salas):
    devolve {'km', 'minutos', 'custo_ida_volta'}, com o caminho por rua arredondado a 1 casa
    e os minutos inteiros, como a reserva de lá.

    Devolve None quando não dá para estimar (RA, coordenada ou meio inválidos). Aí as salas
    usam a reserva delas em vez de cair (RNF-15). As funções de baixo continuam levantando
    ValueError para quem as chama direto.
    """
    try:
        km = distancia_por_rua_km(calcular_distancia_km(ra_origem, (lat, lng)))
        minutos = estimar_tempo_ida_min(km, modo)
        custo = estimar_custo_ida_volta(km, modo)
    except (ValueError, TypeError):
        return None
    return {"km": round(km, 1), "minutos": round(minutos), "custo_ida_volta": custo}
