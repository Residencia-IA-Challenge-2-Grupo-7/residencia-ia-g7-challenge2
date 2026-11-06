"""Leitores de horário da comparação, com dados fictícios (nada da Google é usado nos testes)."""
from base.comparar_google import horario_google, horario_osm


def test_horario_osm_formatos_comuns():
    h = horario_osm("Mo-Fr 11:00-15:00,18:00-23:00; Sa 12:00-24:00; Su off")
    assert h["seg"] == {("11:00", "15:00"), ("18:00", "23:00")}
    assert h["sab"] == {("12:00", "00:00")}
    assert h["dom"] == set()
    assert horario_osm("Mo-Su 10:00-22:00; PH off")["qua"] == {("10:00", "22:00")}
    assert horario_osm("sunrise-sunset") is None


def test_horario_google_no_formato_da_api():
    p = {"regularOpeningHours": {"periods": [
        {"open": {"day": 0, "hour": 11, "minute": 0}, "close": {"day": 0, "hour": 23, "minute": 0}},
        {"open": {"day": 5, "hour": 18, "minute": 0}, "close": {"day": 6, "hour": 2, "minute": 0}},
    ]}}
    h = horario_google(p)
    assert h["dom"] == {("11:00", "23:00")}
    assert h["sex"] == {("18:00", "02:00")}
    assert h["seg"] == set()
