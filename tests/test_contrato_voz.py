"""Contrato da busca (ADR 0007) e transcrição (ADR 0006), sem banco, sem rede e sem modelo."""
from datetime import datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from base.buscar import montar_sql
from base.contrato import ConsultaBusca, Janela
from voz import transcrever as tr
from voz.wer import criticos_faltando, normalizar, wer


def test_consulta_valida_ras_e_campos():
    c = ConsultaBusca(texto="bar tranquilo", ras=["Taguatinga"], teto_pessoa=50)
    assert c.k == 10 and c.colecoes == ["lugares"]
    with pytest.raises(ValidationError):
        ConsultaBusca(texto="x", ras=["Pirenópolis"])
    with pytest.raises(ValidationError):
        ConsultaBusca(texto="x", sql="DROP TABLE lugares")
    with pytest.raises(ValidationError):
        ConsultaBusca(texto="x", exigir=["foco_alcool"])
    with pytest.raises(ValidationError):
        Janela(inicio=datetime(2026, 11, 7, 21), fim=datetime(2026, 11, 7, 20))


def test_sql_so_com_parametros():
    malicioso = "bar'; DROP TABLE lugares; --"
    c = ConsultaBusca(texto=malicioso, ras=["Taguatinga"], tipos_role=["comer_beber"], teto_pessoa=50,
                      exigir=["alim_vegano"], janela=Janela(inicio=datetime(2026, 11, 7, 21)))
    sql, args = montar_sql(c, "lugares", "BAAI/bge-m3")
    assert malicioso not in sql and "DROP" not in sql
    assert args["pedido"] == malicioso and args["ras"] == ["Taguatinga"] and args["dia"] == "sab"
    assert args["hora"] == "21:00" and args["at0"] == "alim_vegano"
    sql, args = montar_sql(ConsultaBusca(texto="show", colecoes=["eventos"],
                                         janela=Janela(inicio=datetime(2026, 11, 14, 18))), "eventos", "m")
    assert "e.inicio < %(fim)s" in sql and args["fim"] == datetime(2026, 11, 15, 18)


def test_normalizacao_wer():
    assert normalizar("Sábado às 19h, R$ 1.200,50!") == "sabado as 19 1200 50"
    assert normalizar("dezenove horas e trinta e cinco conto") == "19 e 35 conto"
    assert wer("paguei 180 do bar", "paguei cento e oitenta do bar") == (0, 4)
    assert wer("sexta depois das 19h", "sesta depois das 19h") == (1, 4)
    assert criticos_faltando(["sexta", "19"], "sesta depois das 7 da noite") == ["sexta", "19"]


def test_audio_em_bytes_e_apagado_mesmo_com_erro(monkeypatch):
    vistos = []

    def falha(caminho, modelo, prompt):
        vistos.append(Path(caminho))
        assert Path(caminho).exists()
        raise RuntimeError("provedor fora do ar")

    monkeypatch.setitem(tr.PROVEDORES, "faster_whisper", falha)
    with pytest.raises(RuntimeError):
        tr.transcrever(b"RIFF....", "faster_whisper", "small")
    assert vistos and not vistos[0].exists()  # RNF-01

    def ok(caminho, modelo, prompt):
        vistos.append(Path(caminho))
        return "paguei 180 do bar", 1.5

    monkeypatch.setitem(tr.PROVEDORES, "faster_whisper", ok)
    t = tr.transcrever(b"RIFF....", "faster_whisper", "small")
    assert t.texto == "paguei 180 do bar" and not vistos[-1].exists()


def test_decodificar_reamostra_para_16k_mono(tmp_path):
    import wave
    import numpy as np
    a = tmp_path / "x.wav"
    with wave.open(str(a), "wb") as w:  # 1 s estéreo a 44,1 kHz
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(44100)
        w.writeframes((np.sin(np.arange(44100) / 20) * 8000).astype(np.int16).repeat(2).tobytes())
    x = tr.decodificar(a)
    assert x.dtype == np.float32 and abs(len(x) - 16000) < 400 and 0.1 < np.abs(x).max() <= 1


def test_arquivo_so_e_apagado_quando_pedido(tmp_path, monkeypatch):
    monkeypatch.setitem(tr.PROVEDORES, "faster_whisper", lambda c, m, p: ("ok", 1.0))
    a = tmp_path / "D01.wav"
    a.write_bytes(b"x")
    tr.transcrever(a, "faster_whisper", "small")
    assert a.exists()
    tr.transcrever(a, "faster_whisper", "small", descartar=True)
    assert not a.exists()
