"""Fluxo completo pedido na issue #43, pela API e com a base real de 93 lugares: criar a sala, 3 participantes
preenchem os 4 campos da Tela 2, confirmam, o organizador gera os cartões e todos votam (votação múltipla).

    PYTHONPATH=. pytest -v tests/test_salas_backend.py
"""
import json
import re
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.salas.gerenciador_salas import MENSAGEM_SUCESSO, GerenciadorSalas
from src.salas.integracoes import carregar_lugares
from src.salas.rotas import obter_gerenciador
from src.state import RepositorioMemoria

TER = datetime(2026, 11, 10, 14, 0)  # terça-feira, 14h

# Os exemplos do guia oficial (seção 1, item 3), um por pessoa
PARTICIPANTES = [
    {"nome": "Rafaela", "origem": "Asa Norte 408", "horarios": "Sexta depois das 19h ou sábado à noite",
     "teto": "80", "preferencias": "Restaurante ou bar animado, vou de carro"},
    {"nome": "Bia", "origem": "Águas Claras perto da estação", "horarios": "sexta e sábado à noite",
     "teto": "60", "preferencias": "Barzinho ou café calmo, sou vegetariana, vou de metrô/Uber"},
    {"nome": "Cadu", "origem": "Ceilândia Centro", "horarios": "sábado depois das 18h",
     "teto": "55", "preferencias": "barzinho barato, vou de metrô"},
]
RA_ESPERADA = {"Rafaela": "Plano Piloto", "Bia": "Águas Claras", "Cadu": "Ceilândia"}


@pytest.fixture
def cliente():
    g = GerenciadorSalas(RepositorioMemoria(), relogio=lambda: TER)  # base real: data/banco_aprovado_2fa.json
    app.dependency_overrides[obter_gerenciador] = lambda: g
    yield TestClient(app)
    app.dependency_overrides.clear()


def _sala_com_tres(cliente):
    r = cliente.post("/api/salas", json={"nome_role": "Aniversário da Galera", "organizador": "Rafaela",
                                         "maior_de_idade": True})
    assert r.status_code == 201
    sala = r.json()
    assert re.fullmatch(r"ROLE-[A-HJ-NP-Z2-9]{4}", sala["codigo"])
    assert sala["link_convite"] == f"/sala/{sala['codigo']}"
    codigo = sala["codigo"]

    pessoas = {}
    for p in PARTICIPANTES:
        r = cliente.post(f"/api/salas/{codigo}/participantes", json={**p, "maior_de_idade": True})
        assert r.status_code == 201, r.text
        corpo = r.json()
        perfil = corpo["perfil"]
        assert perfil["completo"] and perfil["ra"] == RA_ESPERADA[p["nome"]]
        assert perfil["teto"] == f"{p['teto']}.00" and perfil["janelas"]
        assert corpo["confirmado"] is False
        r = cliente.post(f"/api/salas/{codigo}/participantes/{corpo['participante_id']}/confirmar",
                         headers={"X-Token": corpo["token"]})
        assert r.status_code == 200
        pessoas[p["nome"]] = (corpo["participante_id"], corpo["token"])
    return codigo, sala["token_organizador"], pessoas


def test_fluxo_completo_com_tres_participantes(cliente):
    codigo, tok_org, pessoas = _sala_com_tres(cliente)
    painel = cliente.get(f"/api/salas/{codigo}").json()
    assert painel["preencheram"] == "3 de 3" and painel["pode_gerar_sugestoes"]

    # Gerar sugestões: só o organizador
    r = cliente.post(f"/api/salas/{codigo}/gerar-sugestoes", headers={"X-Token": tok_org})
    assert r.status_code == 200
    painel = r.json()
    assert painel["status"] == "votacao"
    assert painel["janela_escolhida"] == {"horario": "sáb 14/11, 19h–24h", "quantos_podem": "3 de 3 podem"}
    cartoes = painel["sugestoes"]
    assert 3 <= len(cartoes) <= 4

    # Cada cartão sai da base de 93, cabe no teto de todos e traz os campos do guia
    base = {str(x["id"]): x for x in carregar_lugares()}
    menor_teto = min(float(p["teto"]) for p in PARTICIPANTES)
    for c in cartoes:
        assert c["lugar_id"] in base and c["nome"] == base[c["lugar_id"]]["nome"]
        assert float(c["consumo_estimado_rs"]) <= menor_teto
        assert c["inicio"].startswith("2026-11-14T")
        for campo in ("ra", "regiao_administrativa", "endereco", "horario", "faixa_gasto_rs",
                      "tempo_medio_chegada_min", "tiktok_url", "explicacao", "nota_justica"):
            assert campo in c
    for nome, (pid, tok) in pessoas.items():
        meu = cliente.get(f"/api/salas/{codigo}/participantes/{pid}", headers={"X-Token": tok}).json()
        teto = float(next(p["teto"] for p in PARTICIPANTES if p["nome"] == nome))
        for custo in meu["meu_custo_e_tempo"].values():
            assert custo is None or float(custo["gasto_total_rs"]) <= teto  # RF-17: transporte incluído

    # Votação múltipla: A e B empatam com 2 votos; vence a melhor nota de justiça entre elas
    ids = [c["id"] for c in cartoes]
    votos = {"Rafaela": [ids[0], ids[1]], "Bia": [ids[0]], "Cadu": [ids[1]]}
    for i, (nome, opcoes) in enumerate(votos.items()):
        pid, tok = pessoas[nome]
        r = cliente.post(f"/api/salas/{codigo}/votar", headers={"X-Token": tok},
                         json={"participante_id": pid, "opcoes": opcoes})
        assert r.status_code == 200
        painel = r.json()
        assert painel["status"] == ("orquestrado" if i == 2 else "votacao")  # fecha sozinha no último voto

    assert painel["placar"][ids[0]] == 2 and painel["placar"][ids[1]] == 2
    res = painel["resultado"]
    a, b = cartoes[0], cartoes[1]
    esperado = a if (a["nota_justica"], -a["posicao"]) >= (b["nota_justica"], -b["posicao"]) else b
    assert res["sugestao_id"] == esperado["id"] and res["desempate_por_justica"] is True
    assert res["mensagem"] == MENSAGEM_SUCESSO == "🎉 Rolê orquestrado com sucesso!"
    assert esperado["nome"] in res["resumo_whatsapp"]
    assert res["link_agenda"].startswith("https://calendar.google.com/calendar/render?")

    # Sigilo (RNF-02): nada dos 4 campos de ninguém aparece no painel público
    texto = json.dumps(cliente.get(f"/api/salas/{codigo}").json(), ensure_ascii=False)
    for p in PARTICIPANTES:
        assert f'"{p["teto"]}' not in texto and f'{p["teto"]}.00' not in texto and f'{p["teto"]},00' not in texto
        assert p["origem"] not in texto and p["horarios"] not in texto and p["preferencias"] not in texto
    assert "token" not in texto and "teto" not in texto


def test_regras_de_entrada_e_permissoes(cliente):
    codigo, tok_org, pessoas = _sala_com_tres(cliente)
    pid, tok = pessoas["Bia"]

    # Menor de idade: recusado, nada guardado
    r = cliente.post(f"/api/salas/{codigo}/participantes", json={**PARTICIPANTES[0], "nome": "Júnior",
                                                                 "maior_de_idade": False})
    assert r.status_code == 403
    assert len(cliente.get(f"/api/salas/{codigo}").json()["participantes"]) == 3

    # Participante não gera sugestões nem vota com o token de outro
    assert cliente.post(f"/api/salas/{codigo}/gerar-sugestoes", headers={"X-Token": tok}).status_code == 403
    cliente.post(f"/api/salas/{codigo}/gerar-sugestoes", headers={"X-Token": tok_org})
    outro = pessoas["Cadu"][1]
    r = cliente.post(f"/api/salas/{codigo}/votar", headers={"X-Token": outro},
                     json={"participante_id": pid, "opcoes": ["A"]})
    assert r.status_code == 403

    # Opção que não existe
    r = cliente.post(f"/api/salas/{codigo}/votar", headers={"X-Token": tok},
                     json={"participante_id": pid, "opcoes": ["Z"]})
    assert r.status_code == 422

    # Código digitado em minúsculas também acha a sala
    assert cliente.get(f"/api/salas/{codigo.lower()}").status_code == 200
