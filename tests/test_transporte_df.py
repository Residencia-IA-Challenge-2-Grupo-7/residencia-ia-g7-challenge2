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
from src.logistica.transporte_df import (
    RAIO_TERRA_KM,
    calcular_distancia_km,
    haversine_km,
    ponto_da_ra,
    resolver_ra,
)
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


# ---------------------------------------------------------------- nome da RA de origem


@pytest.mark.parametrize("nome", sorted(ras_validas()))
def test_cada_ra_oficial_se_resolve_nela_mesma(nome):
    assert resolver_ra(nome) == nome


@pytest.mark.parametrize(
    "texto, esperado",
    [
        ("aguas claras", "Águas Claras"),
        ("ÁGUAS CLARAS", "Águas Claras"),
        ("ceilandia", "Ceilândia"),
        ("Asa Sul", "Plano Piloto"),
        ("Plano Piloto (Asa Sul)", "Plano Piloto"),
        ("Taguá", "Taguatinga"),
        ("estação Arniqueiras", "Arniqueira"),
        ("sol nascente", "Sol Nascente/Pôr do Sol"),
    ],
)
def test_resolve_sem_acento_em_maiusculas_e_por_apelido(texto, esperado):
    assert resolver_ra(texto) == esperado


@pytest.mark.parametrize("texto", ["Goiânia", "zona oeste", "", None])
def test_nome_que_nao_e_ra_levanta_erro(texto):
    with pytest.raises(ValueError, match="nenhuma"):
        resolver_ra(texto)


def test_nome_com_duas_ras_levanta_erro():
    with pytest.raises(ValueError, match="2 RAs"):
        resolver_ra("Sudoeste / Cruzeiro")


def test_erro_nao_repete_o_que_a_pessoa_digitou():
    """A origem é um campo secreto: o texto não pode vazar para log pela mensagem de erro."""
    with pytest.raises(ValueError) as erro:
        resolver_ra("Rua das Flores 123, Goiânia")
    assert "Flores" not in str(erro.value)


# ---------------------------------------------------------------- distância da RA até o lugar

BASE_2FA = {
    registro["id"]: registro
    for registro in json.loads(
        (RAIZ / "data" / "banco_aprovado_2fa.json").read_text(encoding="utf-8")
    )
}
DONA_CLEIDE = BASE_2FA["tiktok_7612334793040186632"]  # no centro de Águas Claras
TRADICIONAL = BASE_2FA["tiktok_7688862229533445383"]  # Planaltina, sem coordenadas


def test_ponto_da_ra_vem_do_catalogo():
    assert ponto_da_ra("samambaia") == SAMAMBAIA


@pytest.mark.parametrize(
    "origem, destino, esperado",
    [
        ("Samambaia", "Plano Piloto", 23.495),
        ("Águas Claras", "Plano Piloto", 16.041),
        ("Samambaia", "Águas Claras", 7.721),
    ],
)
def test_distancia_entre_as_ras_da_issue(origem, destino, esperado):
    assert calcular_distancia_km(origem, _ponto(destino)) == pytest.approx(
        esperado, abs=0.001
    )


def test_aceita_um_registro_da_base():
    assert calcular_distancia_km("Samambaia", DONA_CLEIDE) == pytest.approx(
        7.721, abs=0.001
    )


def test_lugar_no_centro_da_propria_ra_da_zero_km():
    """O valor honesto é 0; o mínimo realista dentro da RA entra no cálculo do tempo."""
    assert calcular_distancia_km("Águas Claras", DONA_CLEIDE) == 0.0


def test_lugar_sem_coordenadas_levanta_erro_com_o_nome_do_lugar():
    with pytest.raises(ValueError, match="Tradicional Restaurante"):
        calcular_distancia_km("Planaltina", TRADICIONAL)


def test_toda_ra_chega_a_todo_lugar_da_base_com_coordenadas():
    lugares = [
        lugar
        for lugar in BASE_2FA.values()
        if lugar.get("lat") is not None and lugar.get("lng") is not None
    ]
    assert lugares
    for ra in ras_validas():
        for lugar in lugares:
            km = calcular_distancia_km(ra, lugar)
            assert 0 <= km < 100, (ra, lugar["nome"])
