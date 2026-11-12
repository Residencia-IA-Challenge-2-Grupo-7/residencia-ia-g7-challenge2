"""
Testes do deslocamento no DF (issue #44).

Esta primeira parte valida o catálogo de pontos das 35 RAs
(data/regioes_df_gps.json). Os testes de src/logistica/transporte_df.py
entram nos próximos commits.
"""

import json
from pathlib import Path

import pytest

from src.interpretador.lugares import ras_validas
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
