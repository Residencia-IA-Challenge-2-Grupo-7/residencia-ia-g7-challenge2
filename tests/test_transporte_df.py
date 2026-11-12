"""
Testes do deslocamento no DF (issue #44).

Validam o catálogo de pontos das 35 RAs (data/regioes_df_gps.json) e o
módulo src/logistica/transporte_df.py, com os casos da issue entre
Samambaia, Águas Claras e Plano Piloto.
"""

import json
import math
from pathlib import Path

import pytest

from src.interpretador.lugares import ras_validas
from src.logistica.transporte_df import RAIO_TERRA_KM, haversine_km
from src.rag.coletor_tiktok_2fa import COORDENADAS_RAS_DF
from src.salas import integracoes

RAIZ = Path(__file__).resolve().parent.parent
REGIOES = json.loads(
    (RAIZ / "data" / "regioes_df_gps.json").read_text(encoding="utf-8")
)
POR_NOME = {regiao["nome"]: regiao for regiao in REGIOES}

CAMPOS = {"numero_ra", "nome", "macrorregiao", "lat", "lng", "fonte"}
FONTES = {"coletor_2fa", "wikipedia", "openstreetmap"}

# Retângulo que contém o DF inteiro, com cerca de 1 km de folga.
LAT_MIN, LAT_MAX = -16.06, -15.49
LNG_MIN, LNG_MAX = -48.29, -47.30


def _nome(regiao):
    return regiao["nome"]


# ---------------------------------------------------------------- catálogo das 35 RAs


def test_catalogo_tem_as_35_ras_oficiais_sem_repetir():
    nomes = [regiao["nome"] for regiao in REGIOES]
    assert len(nomes) == 35
    assert len(set(nomes)) == 35
    assert set(nomes) == set(ras_validas())


def test_ordem_segue_a_numeracao_oficial_ra_i_a_ra_xxxv():
    assert [regiao["numero_ra"] for regiao in REGIOES] == list(range(1, 36))
    assert POR_NOME["Plano Piloto"]["numero_ra"] == 1
    assert POR_NOME["Água Quente"]["numero_ra"] == 35


@pytest.mark.parametrize("regiao", REGIOES, ids=_nome)
def test_campos_macrorregiao_e_fonte_de_cada_ra(regiao):
    assert set(regiao) == CAMPOS
    assert regiao["macrorregiao"] == ras_validas()[regiao["nome"]]
    assert regiao["fonte"] in FONTES


@pytest.mark.parametrize("regiao", REGIOES, ids=_nome)
def test_ponto_de_cada_ra_fica_dentro_do_df(regiao):
    assert LAT_MIN <= regiao["lat"] <= LAT_MAX
    assert LNG_MIN <= regiao["lng"] <= LNG_MAX


def test_nenhuma_ra_repete_o_ponto_de_outra():
    pontos = [(regiao["lat"], regiao["lng"]) for regiao in REGIOES]
    assert len(set(pontos)) == len(pontos)


def test_reaproveita_os_pontos_que_a_base_2fa_ja_usa():
    """
    Os lugares "Centróide Oficial" da base usam os pontos do coletor da Miti.
    Se os nossos fossem outros, quem sai da mesma RA do lugar ganharia uma
    viagem falsa de alguns quilômetros.
    """
    em_comum = [nome for nome in COORDENADAS_RAS_DF if nome in POR_NOME]
    assert len(em_comum) == 17
    for nome in em_comum:
        ponto = COORDENADAS_RAS_DF[nome]
        assert (POR_NOME[nome]["lat"], POR_NOME[nome]["lng"]) == (
            ponto["lat"],
            ponto["lng"],
        ), nome


def test_leitor_das_salas_aceita_o_formato_do_arquivo():
    """
    src/salas/integracoes.py lê este arquivo. Se o formato não servir, ele
    volta para a média da base sem avisar; este teste avisa.
    """
    integracoes._centroides.cache_clear()
    centroides = integracoes._centroides()
    assert set(centroides) == set(ras_validas())
    assert centroides["Samambaia"] == (
        POR_NOME["Samambaia"]["lat"],
        POR_NOME["Samambaia"]["lng"],
    )


# ---------------------------------------------------------------- distância de Haversine


def _ponto(nome):
    return (POR_NOME[nome]["lat"], POR_NOME[nome]["lng"])


PLANO = _ponto("Plano Piloto")
AGUAS_CLARAS = _ponto("Águas Claras")
SAMAMBAIA = _ponto("Samambaia")

# Distância geodésica no elipsoide WGS84, calculada uma vez com a biblioteca
# geographiclib (fora do teste). Serve de referência independente da fórmula.
GEODESICA_KM = [
    ("Samambaia", "Plano Piloto", 23.505),
    ("Águas Claras", "Plano Piloto", 16.054),
    ("Samambaia", "Águas Claras", 7.715),
]


def test_mesmo_ponto_da_distancia_zero():
    assert haversine_km(PLANO, PLANO) == 0.0


def test_distancia_e_a_mesma_nos_dois_sentidos():
    assert haversine_km(SAMAMBAIA, PLANO) == pytest.approx(
        haversine_km(PLANO, SAMAMBAIA)
    )


def test_um_grau_de_latitude_mede_pi_r_sobre_180():
    assert haversine_km((0, 0), (1, 0)) == pytest.approx(math.pi * RAIO_TERRA_KM / 180)


def test_pontos_opostos_do_globo_nao_quebram_a_conta():
    assert haversine_km((0, 0), (0, 180)) == pytest.approx(math.pi * RAIO_TERRA_KM)


@pytest.mark.parametrize("origem, destino, esperado", GEODESICA_KM)
def test_ras_da_issue_ficam_a_menos_de_meio_por_cento_da_geodesica(
    origem, destino, esperado
):
    assert haversine_km(_ponto(origem), _ponto(destino)) == pytest.approx(
        esperado, rel=0.005
    )


def test_aguas_claras_fica_no_caminho_entre_samambaia_e_plano():
    """Passar por Águas Claras alonga o trajeto Samambaia → Plano em menos de 2% (dá ~1,1%)."""
    direto = haversine_km(SAMAMBAIA, PLANO)
    pelo_meio = haversine_km(SAMAMBAIA, AGUAS_CLARAS) + haversine_km(AGUAS_CLARAS, PLANO)
    assert direto <= pelo_meio <= direto * 1.02


def test_da_o_mesmo_numero_que_a_reserva_das_salas():
    for origem, destino, _ in GEODESICA_KM:
        a, b = _ponto(origem), _ponto(destino)
        assert haversine_km(a, b) == pytest.approx(integracoes._km(a, b))


@pytest.mark.parametrize(
    "ponto", [(95.0, -47.9), (-15.8, 200.0), (float("nan"), -47.9)]
)
def test_coordenada_invalida_levanta_erro(ponto):
    with pytest.raises(ValueError):
        haversine_km(ponto, PLANO)
