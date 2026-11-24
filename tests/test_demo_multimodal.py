"""A demonstração da semana 5 roda sem rede e fecha sozinha (ADR 0017)."""
import sys

import pytest

from scripts import demo_multimodal as demo


@pytest.fixture
def log(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(demo, "ARQUIVO_METRICAS_PADRAO", tmp_path / "metricas.jsonl")
    monkeypatch.setattr(demo.voz_rotas, "registrar_evento_metrica", lambda *a, **kw: {})
    monkeypatch.setattr(sys, "argv", ["demo", "--offline", "--saida", str(tmp_path / "log.txt")])
    demo.main()
    capsys.readouterr()
    return (tmp_path / "log.txt").read_text(encoding="utf-8")


def test_demo_sem_rede_mostra_as_duas_modalidades_e_o_efeito_do_audio(log):
    assert "MODO SEM REDE" in log and log.count("[ÁUDIO]") == 2 and log.count("[TEXTO]") == 8
    assert "sáb 28/11, 14h–18h (4 de 4)" in log and "dom 29/11, 13h–24h (4 de 4)" in log
    assert "A janela comum mudou" in log and "VAZOU" not in log


def test_demo_mostra_as_falhas(log):
    for trecho in ("Silêncio: ouviu", "Hora ambígua", "HTTP 403", "HTTP 415", "HTTP 413", "HTTP 503"):
        assert trecho in log


def test_demo_devolve_o_app_como_estava(log):
    assert not demo.app.dependency_overrides
