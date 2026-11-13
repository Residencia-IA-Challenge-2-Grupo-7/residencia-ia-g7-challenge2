"""Testes das Telas 1 a 3 do aplicativo web (issue #42).

    PYTHONPATH=. pytest -v tests/test_interface_app.py
"""
import json

from fastapi.testclient import TestClient

from src.main import app

cliente = TestClient(app)


def test_tela_1_criar_sala_responde_200():
    r = cliente.get("/app")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "Criar Sala" in r.text
    assert 'id="organizador"' in r.text
    assert 'id="nomeRole"' in r.text
    assert 'role="tablist"' in r.text
    assert 'id="abaCriar"' in r.text
    assert 'id="abaPerfil"' in r.text
    assert 'id="abaSala"' in r.text
    assert 'btnDevProxima' in r.text
    assert 'btnDevAnterior' in r.text
    assert 'avancarTelaDev()' in r.text


def test_tela_2_perfil_4_campos_responde_200():
    for rota in ("/sala/demo/perfil", "/sala/ROLE-7KQ2/perfil"):
        r = cliente.get(rota)
        assert r.status_code == 200
        assert "text/html" in r.headers["content-type"]
        assert "De onde você sai no DF?" in r.text
        assert "Quais dias e horários você pode?" in r.text
        assert "Qual seu limite de gasto em R$?" in r.text
        assert "O que você anima fazer e como vai?" in r.text
        assert "Confirmar em Segredo" in r.text
        assert "Secreto" in r.text


def test_tela_3_painel_e_votacao_responde_200():
    for rota in ("/sala/demo", "/sala/ROLE-7KQ2"):
        r = cliente.get(rota)
        assert r.status_code == 200
        assert "text/html" in r.headers["content-type"]
        assert "Quem está na sala" in r.text
        assert "Sugestões para o grupo" in r.text
        assert "🎉 Rolê orquestrado com sucesso!" in r.text
        assert "Confirmar meu voto" in r.text


def test_pwa_e_arquivos_estaticos_respondem_200():
    manifest = cliente.get("/manifest.webmanifest")
    assert manifest.status_code == 200
    dados = json.loads(manifest.text)
    assert dados["start_url"] == "/app"
    assert dados["display"] == "standalone"

    sw = cliente.get("/sw.js")
    assert sw.status_code == 200
    assert "/static/telas/" in sw.text

    for arq in ("app.css", "comum.js", "app.js", "perfil.js", "sala.js", "demo.js", "icone.svg"):
        resp = cliente.get(f"/static/telas/{arq}")
        assert resp.status_code == 200, f"Falha ao carregar /static/telas/{arq}"
