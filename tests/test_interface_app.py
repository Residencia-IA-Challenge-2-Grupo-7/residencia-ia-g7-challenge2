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
    # Modo Dev deve vir escondido por padrão no HTML cru inicial (item 3 da revisão)
    assert 'data-dev-controle="true" hidden' in r.text
    # Sem manipuladores inline (CSP compliance, item 6 da revisão)
    assert 'onclick=' not in r.text


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


def test_rnf_02_servidor_nao_injeta_dados_no_html():
    """Garante que o servidor entrega HTML puramente estático/SPA (RNF-02).

    Nenhum dado sensível de sala, participante, orçamento ou origem é injetado
    no HTML servido em /sala/{codigo} ou /sala/{codigo}/perfil.
    """
    # 1. Cria uma sala real via API com dados privados
    resp_criar = cliente.post(
        "/api/salas",
        json={
            "organizador": "OrganizadorSecretoRNF02",
            "nome_role": "RoleUltraSecretoXYZ123",
            "maior_de_idade": True,
        },
    )
    assert resp_criar.status_code == 201
    dados_sala = resp_criar.json()
    cod_sala = dados_sala["codigo"]

    # 2. Adiciona participante com dados privados de perfil
    resp_part = cliente.post(
        f"/api/salas/{cod_sala}/participantes",
        json={
            "nome": "ParticipanteMisterioso99",
            "maior_de_idade": True,
            "origem": "Taguatinga Sul QSD 15 Casa Secreta",
            "horarios": "sexta 20h",
            "teto": "85.50",
            "preferencias": "barzinho sem glúten",
        },
    )
    assert resp_part.status_code == 201

    # 3. Faz requisição nas rotas HTML do app
    r_app = cliente.get("/app")
    r_sala = cliente.get(f"/sala/{cod_sala}")
    r_perfil = cliente.get(f"/sala/{cod_sala}/perfil")

    assert r_app.status_code == 200
    assert r_sala.status_code == 200
    assert r_perfil.status_code == 200

    # 4. O HTML servido em /sala/{codigo} e /sala/{codigo}/perfil é idêntico a /app
    assert r_sala.text == r_app.text
    assert r_perfil.text == r_app.text

    # 5. Nenhum dado sensível vaza no corpo do HTML (segurança e RNF-02)
    for dado_privado in (
        "OrganizadorSecretoRNF02",
        "RoleUltraSecretoXYZ123",
        "ParticipanteMisterioso99",
        "Taguatinga Sul QSD 15 Casa Secreta",
        "85.50",
    ):
        assert dado_privado not in r_sala.text
        assert dado_privado not in r_perfil.text
