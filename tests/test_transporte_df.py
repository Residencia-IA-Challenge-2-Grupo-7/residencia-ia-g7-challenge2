"""
Testes do deslocamento no DF (issue #44).

Validam o catálogo de pontos das 35 RAs (data/regioes_df_gps.json) e o
módulo src/logistica/transporte_df.py, com os casos da issue entre
Samambaia, Águas Claras e Plano Piloto.
"""

import json
import math
from decimal import Decimal
from pathlib import Path

import pytest

from src.interpretador.campos import ROTULOS_TRANSPORTE
from src.interpretador.lugares import ras_validas
from src.logistica.transporte_df import (
    DISTANCIA_MINIMA_KM,
    ESPERA_MIN,
    FATOR_ROTA,
    MODOS,
    RAIO_TERRA_KM,
    TARIFA_PUBLICO,
    VELOCIDADE_KMH,
    calcular_distancia_km,
    calcular_score_justica_espacial,
    distancia_por_rua_km,
    estimar_custo_ida_volta,
    estimar_deslocamento,
    estimar_tempo_ida_min,
    haversine_km,
    nota_menor_miseria,
    ponto_da_ra,
    resolver_ra,
    tempos_de_ida_min,
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


# ---------------------------------------------------------------- tempo de ida

RAS_DA_ISSUE = ["Samambaia", "Águas Claras", "Plano Piloto"]


def test_modos_sao_os_do_campo_4_da_tela_2():
    assert set(MODOS) == set(ROTULOS_TRANSPORTE) == set(VELOCIDADE_KMH) == set(ESPERA_MIN)


def test_usa_os_mesmos_numeros_da_reserva_das_salas():
    """Se alguém mudar um lado e não o outro, os cartões mudam sem ninguém decidir."""
    assert FATOR_ROTA == integracoes.FATOR_ROTA
    assert VELOCIDADE_KMH == integracoes.VELOCIDADE_KMH
    assert ESPERA_MIN == integracoes.ESPERA_MIN


def test_rua_e_30_por_cento_mais_longa_que_a_linha_reta():
    assert distancia_por_rua_km(10) == pytest.approx(13)


@pytest.mark.parametrize("reta", [0, 0.5, 1.5])
def test_trajeto_curto_respeita_o_piso(reta):
    assert distancia_por_rua_km(reta) == DISTANCIA_MINIMA_KM


@pytest.mark.parametrize("reta", [-1, float("nan")])
def test_distancia_invalida_levanta_erro(reta):
    with pytest.raises(ValueError):
        distancia_por_rua_km(reta)


def test_tempo_soma_a_espera_e_o_trajeto():
    # 18 km de ônibus a 18 km/h = 60 min, mais 15 min de espera
    assert estimar_tempo_ida_min(18, "publico") == pytest.approx(75)
    # 15 km de carro a 30 km/h = 30 min, mais 5 min para estacionar
    assert estimar_tempo_ida_min(15, "carro") == pytest.approx(35)


def test_meio_desconhecido_levanta_erro_dizendo_os_validos():
    with pytest.raises(ValueError, match="publico"):
        estimar_tempo_ida_min(5, "uber")


def test_samambaia_ao_plano_de_carro_e_de_onibus():
    tempos = tempos_de_ida_min("Samambaia", PLANO)
    assert tempos["carro"] == pytest.approx(66.1, abs=0.1)
    assert tempos["publico"] == pytest.approx(116.8, abs=0.1)


@pytest.mark.parametrize("origem", RAS_DA_ISSUE)
@pytest.mark.parametrize("destino", RAS_DA_ISSUE)
def test_carro_e_app_chegam_antes_do_onibus(origem, destino):
    tempos = tempos_de_ida_min(origem, _ponto(destino))
    assert tempos["carro"] == tempos["app"] < tempos["publico"]


def test_mesma_ra_nao_da_zero_minuto():
    tempos = tempos_de_ida_min("Águas Claras", DONA_CLEIDE)
    assert tempos["publico"] == pytest.approx(15 + DISTANCIA_MINIMA_KM / 18 * 60)
    assert tempos["a_pe"] == pytest.approx(DISTANCIA_MINIMA_KM / 4.5 * 60)
    assert all(minutos > 0 for minutos in tempos.values())


# ---------------------------------------------------------------- custo de ida e volta


def test_tarifa_e_a_mesma_da_reserva_das_salas():
    assert TARIFA_PUBLICO == integracoes.TARIFA_PUBLICO == Decimal("5.50")


@pytest.mark.parametrize("km", [2.0, 7.7, 13.0, 30.54])
@pytest.mark.parametrize("modo", MODOS)
def test_custo_da_o_mesmo_que_a_reserva_das_salas(km, modo):
    assert estimar_custo_ida_volta(km, modo) == integracoes._custo_ida_volta(modo, km)


@pytest.mark.parametrize("km", [2.0, 30.54])
def test_onibus_e_metro_custam_duas_passagens_qualquer_que_seja_a_distancia(km):
    assert estimar_custo_ida_volta(km, "publico") == Decimal("11.00")


@pytest.mark.parametrize("modo", ["carona", "a_pe", "bike"])
def test_carona_a_pe_e_bike_nao_custam_nada(modo):
    assert estimar_custo_ida_volta(30.54, modo) == Decimal("0.00")


def test_samambaia_ao_plano_de_app_e_de_carro():
    km = distancia_por_rua_km(calcular_distancia_km("Samambaia", PLANO))  # ~30,5 km
    assert estimar_custo_ida_volta(km, "app") == Decimal("144.20")  # (5 + 2,20 x 30,5) x 2
    assert estimar_custo_ida_volta(km, "carro") == Decimal("54.90")  # 0,90 x 30,5 x 2


def test_custo_e_decimal_com_duas_casas():
    custo = estimar_custo_ida_volta(7.7, "app")
    assert isinstance(custo, Decimal)
    assert custo.as_tuple().exponent == -2


# ---------------------------------------------------------------- encaixe com as salas


def test_estimar_deslocamento_segue_o_contrato_das_salas():
    r = estimar_deslocamento("Samambaia", PLANO[0], PLANO[1], "publico")
    assert set(r) == {"km", "minutos", "custo_ida_volta"}
    assert r == {"km": 30.5, "minutos": 117, "custo_ida_volta": Decimal("11.00")}


@pytest.mark.parametrize(
    "ra, lat, lng, modo",
    [
        ("Goiânia", -15.79, -47.88, "publico"),
        ("Samambaia", None, -47.88, "publico"),
        ("Samambaia", -15.79, -47.88, "uber"),
    ],
)
def test_estimar_deslocamento_devolve_none_quando_nao_da_para_estimar(ra, lat, lng, modo):
    assert estimar_deslocamento(ra, lat, lng, modo) is None


def test_salas_passam_a_usar_este_modulo():
    r = integracoes.deslocamento("Samambaia", DONA_CLEIDE, "publico")
    assert r["estimado_por"] == "logistica"


def test_so_muda_a_reserva_nos_trajetos_curtos(monkeypatch):
    """Ligar o módulo não muda nenhum cartão, exceto onde entra o piso de 2 km."""
    lugares = [lugar for lugar in BASE_2FA.values() if lugar.get("lat") is not None]
    pares = [(ra, lugar, modo) for ra in ras_validas() for lugar in lugares for modo in MODOS]
    nossos = [integracoes.deslocamento(ra, lugar, modo) for ra, lugar, modo in pares]
    # Sem a nossa função, integracoes.py cai na reserva dele.
    monkeypatch.setattr(integracoes, "_funcao", lambda modulos, nome: None)
    reservas = [integracoes.deslocamento(ra, lugar, modo) for ra, lugar, modo in pares]

    curtos = 0
    for (ra, lugar, _), nosso, reserva in zip(pares, nossos, reservas):
        assert (nosso["estimado_por"], reserva["estimado_por"]) == ("logistica", "reserva")
        if calcular_distancia_km(ra, lugar) * FATOR_ROTA >= DISTANCIA_MINIMA_KM:
            for chave in ("km", "minutos", "custo_ida_volta"):
                assert nosso[chave] == reserva[chave], (ra, lugar["nome"], chave)
        else:
            curtos += 1
            assert nosso["km"] == DISTANCIA_MINIMA_KM
    assert curtos > 0


# ---------------------------------------------------------------- Menor Miséria por tempo (salas)


def _desl(*minutos):
    return [{"minutos": m} for m in minutos]


GRUPOS_DE_TEMPO = [
    (10,),
    (20, 20),
    (20, 100),
    (60, 60),
    (30, 45, 90),
    (117, 22),
    (5, 200),
    (66, 66, 66, 66),
]


def test_salas_passam_a_usar_esta_nota():
    achada = integracoes._funcao(
        ["src.logistica.transporte_df", "src.logistica"], "nota_menor_miseria"
    )
    assert achada is nota_menor_miseria


@pytest.mark.parametrize("minutos", GRUPOS_DE_TEMPO, ids=str)
def test_nota_por_tempo_da_o_mesmo_que_a_reserva_das_salas(minutos, monkeypatch):
    nossa = integracoes.nota_justica(_desl(*minutos))
    monkeypatch.setattr(integracoes, "_funcao", lambda modulos, nome: None)
    assert nossa == integracoes.nota_justica(_desl(*minutos))


def test_mesma_media_mas_quem_fica_pior_derruba_a_nota():
    """Os dois grupos têm média de 60 min; o primeiro deixa alguém com 100 min."""
    assert nota_menor_miseria(_desl(20, 100)) < nota_menor_miseria(_desl(60, 60))


def test_dentro_da_folga_so_a_desigualdade_tira_pontos():
    assert nota_menor_miseria(_desl(15, 15, 20)) == pytest.approx(98.5)
    assert nota_menor_miseria(_desl(20, 20)) == 100.0


def test_ordem_das_pessoas_nao_muda_a_nota():
    assert nota_menor_miseria(_desl(30, 45, 90)) == nota_menor_miseria(_desl(90, 30, 45))


def test_sem_trajeto_para_medir_a_nota_e_30():
    assert nota_menor_miseria([]) == 30.0


# ---------------------------------------------------------------- Menor Miséria por distância (issue)

DUPLA_DA_ISSUE = ["Samambaia", "Plano Piloto"]


def test_issue_samambaia_e_plano_preferem_aguas_claras_a_um_dos_extremos():
    no_plano = calcular_score_justica_espacial(DUPLA_DA_ISSUE, PLANO)
    em_samambaia = calcular_score_justica_espacial(DUPLA_DA_ISSUE, SAMAMBAIA)
    em_aguas_claras = calcular_score_justica_espacial(DUPLA_DA_ISSUE, AGUAS_CLARAS)
    assert em_aguas_claras > no_plano == em_samambaia


def test_media_quase_igual_mas_a_nota_separa_os_lugares():
    """Em Plano, Águas Claras e Guará a média de km da dupla fica entre 11,7 e 11,9."""
    lugares = [PLANO, AGUAS_CLARAS, _ponto("Guará")]
    medias = [
        sum(calcular_distancia_km(ra, lugar) for ra in DUPLA_DA_ISSUE) / 2
        for lugar in lugares
    ]
    notas = [calcular_score_justica_espacial(DUPLA_DA_ISSUE, lugar) for lugar in lugares]
    assert max(medias) - min(medias) < 0.3
    assert notas[0] < notas[1] < notas[2]


def test_grupo_espalhado_ainda_separa_os_lugares():
    """Planaltina + Santa Maria + Plano: a nota por tempo zera em quase todo lugar; esta não."""
    grupo = ["Planaltina", "Santa Maria", "Plano Piloto"]
    notas = [
        calcular_score_justica_espacial(grupo, _ponto(ra))
        for ra in ["Plano Piloto", "Guará", "Samambaia"]  # pior trajeto: 31,5 / 41,9 / 54,5 km
    ]
    assert notas[0] > notas[1] > notas[2] > 0


def test_protege_quem_mora_na_periferia():
    """Ceilândia + Samambaia + Plano: o melhor lugar não é o Plano, onde só um mora (RNF-13)."""
    grupo = ["Ceilândia", "Samambaia", "Plano Piloto"]
    candidatos = ["Plano Piloto", "Águas Claras", "Taguatinga", "Guará"]
    melhor = max(candidatos, key=lambda ra: calcular_score_justica_espacial(grupo, _ponto(ra)))
    assert melhor != "Plano Piloto"


def test_todo_mundo_saindo_do_proprio_lugar_tira_100():
    assert calcular_score_justica_espacial(["Águas Claras", "Águas Claras"], DONA_CLEIDE) == 100.0


def test_nota_espacial_fica_entre_0_e_100_em_toda_a_base():
    grupo = ["Ceilândia", "Samambaia", "Plano Piloto", "Planaltina"]
    for lugar in BASE_2FA.values():
        if lugar.get("lat") is not None:
            assert 0 < calcular_score_justica_espacial(grupo, lugar) <= 100


def test_nota_espacial_e_so_um_numero():
    """Nada no resultado diz quem é o mais prejudicado nem de onde cada um sai."""
    assert isinstance(calcular_score_justica_espacial(DUPLA_DA_ISSUE, PLANO), float)


def test_grupo_vazio_ou_ra_desconhecida_levanta_erro():
    with pytest.raises(ValueError):
        calcular_score_justica_espacial([], PLANO)
    with pytest.raises(ValueError):
        calcular_score_justica_espacial(["Goiânia"], PLANO)
