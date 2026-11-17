"""Ajustes das salas sobre a logística da Samara (PR #55): nota que não zera, Vai de Graça e RA do lugar."""
from datetime import date, datetime
from decimal import Decimal

import pytest

from src.logistica.transporte_df import _pascoa, feriados, nota_menor_miseria, tarifa_zero
from src.salas import integracoes

PLANO = {"lat": -15.79, "lng": -47.88}


# --------------------------------------------------------------------------- Vai de Graça

@pytest.mark.parametrize("ano, pascoa", [(2024, date(2024, 3, 31)), (2025, date(2025, 4, 20)),
                                         (2026, date(2026, 4, 5))])
def test_pascoa(ano, pascoa):
    assert _pascoa(ano) == pascoa


@pytest.mark.parametrize("dia, gratis", [
    (date(2026, 11, 15), True),   # domingo
    (date(2026, 11, 14), False),  # sábado
    (date(2026, 11, 20), True),   # Consciência Negra (sexta)
    (date(2026, 11, 30), True),   # Dia do Evangélico (feriado do DF)
    (date(2026, 4, 3), True),     # Sexta-feira Santa
    (date(2026, 4, 21), True),    # Tiradentes e aniversário de Brasília
    (date(2026, 2, 17), False),   # Carnaval é ponto facultativo, não feriado
    (None, False),                # sem data, cobra (a estimativa mais cara não estoura o teto de ninguém)
])
def test_tarifa_zero_em_domingos_e_feriados(dia, gratis):
    assert tarifa_zero(dia) is gratis


def test_feriados_do_ano_incluem_os_do_df():
    assert date(2026, 11, 30) in feriados(2026) and date(2026, 4, 21) in feriados(2026)


def test_salas_repassam_a_data_e_o_onibus_sai_de_graca_no_domingo():
    sabado = integracoes.deslocamento("Samambaia", PLANO, "publico", datetime(2026, 11, 14, 19))
    domingo = integracoes.deslocamento("Samambaia", PLANO, "publico", datetime(2026, 11, 15, 19))
    assert sabado["estimado_por"] == domingo["estimado_por"] == "logistica"
    assert sabado["custo_ida_volta"] == Decimal("11.00") and domingo["custo_ida_volta"] == Decimal("0.00")
    assert sabado["minutos"] == domingo["minutos"]
    app = integracoes.deslocamento("Samambaia", PLANO, "app", datetime(2026, 11, 15, 19))
    assert app["custo_ida_volta"] > 0  # o Vai de Graça é só para ônibus e metrô


def test_reserva_das_salas_tambem_zera_no_domingo(monkeypatch):
    monkeypatch.setattr(integracoes, "_funcao", lambda modulos, nome: None)  # sem o módulo da Samara
    r = integracoes.deslocamento("Samambaia", PLANO, "publico", datetime(2026, 11, 15, 19))
    assert r["estimado_por"] == "reserva" and r["custo_ida_volta"] == Decimal("0.00")


def test_cartoes_de_domingo_cobram_zero_de_quem_vai_de_onibus():
    from src.salas import sugestoes

    class Perfil:
        ra = "Ceilândia"

        class preferencias:
            transporte = ["publico"]

    d = sugestoes._deslocamento(Perfil, PLANO, datetime(2026, 11, 15, 18))
    assert d["custo_ida_volta"] == Decimal("0.00")


# ------------------------------------------------------------------- Menor Miséria que não zera

def _desl(*minutos):
    return [{"minutos": m} for m in minutos]


def test_nota_por_tempo_nunca_zera_e_segue_o_pior_trajeto():
    espalhado_a = nota_menor_miseria(_desl(60, 150))
    espalhado_b = nota_menor_miseria(_desl(60, 200))
    assert 0 < espalhado_b < espalhado_a < 100  # antes, os dois empatavam em 0


def test_reserva_das_salas_usa_a_mesma_curva(monkeypatch):
    for minutos in [(20, 20), (15, 15, 20), (60, 150), (30, 45, 90)]:
        com_modulo = integracoes.nota_justica(_desl(*minutos))
        monkeypatch.setattr(integracoes, "_funcao", lambda modulos, nome: None)
        assert integracoes.nota_justica(_desl(*minutos)) == com_modulo
        monkeypatch.undo()


# ---------------------------------------------------------------------------------- RA do lugar

@pytest.mark.parametrize("texto, ra", [
    ("Plano Piloto (Sudoeste)", "Sudoeste/Octogonal"),
    ("Plano Piloto (Asa Sul)", "Plano Piloto"),
    ("Guará", "Guará"),
    ("Águas Claras", "Águas Claras"),
    ("", None),
])
def test_ra_do_lugar_prefere_o_que_esta_entre_parenteses(texto, ra):
    assert integracoes.ra_do_lugar({"regiao_administrativa": texto}) == ra
