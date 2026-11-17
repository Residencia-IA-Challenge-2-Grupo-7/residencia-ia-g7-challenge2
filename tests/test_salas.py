"""Testes das salas (src/salas/ e src/state.py): cruzamento de horários, horário dos lugares, cartões,
votação, rotas e sigilo do orçamento. Sem LLM e sem rede; a base de 93 lugares é lida do repositório."""
import json
import re
from datetime import date, datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from src.interpretador.campos import interpretar_campos
from src.interpretador.tempo import JanelaResolvida
from src.main import app
from src.salas.gerenciador_salas import ErroSala, GerenciadorSalas
from src.salas.horario_lugar import ler_funcionamento
from src.salas.janelas import cruzar
from src.salas.modelos import LIMITE_PARTICIPANTES, ORQUESTRADO, VOTACAO
from src.salas.rotas import obter_gerenciador
from src.salas import sugestoes as motor
from src.state import RepositorioMemoria

TER = datetime(2026, 11, 10, 14, 0)  # terça-feira
SAB = datetime(2026, 11, 14)


def J(d, h0, h1, disponivel=True, dia=None):
    base = datetime(2026, 11, d)
    fim = datetime(2026, 11, d + 1) if h1 == 24 else base.replace(hour=h1)
    return JanelaResolvida(base.replace(hour=h0), fim, disponivel)


# ---------- cruzamento de horários (RF-13)

def test_janela_comum_de_todos():
    r = cruzar({"a": [J(14, 18, 24)], "b": [J(14, 19, 23)], "c": [J(13, 19, 24), J(14, 17, 22)]}, TER)
    assert (r[0].inicio, r[0].fim) == (datetime(2026, 11, 14, 19), datetime(2026, 11, 14, 22))
    assert r[0].contagem == "3 de 3 podem"


def test_sem_janela_de_todos_usa_a_com_mais_gente():
    r = cruzar({"a": [J(13, 19, 24)], "b": [J(13, 19, 24)], "c": [J(14, 19, 24)]}, TER)
    assert r[0].inicio.day == 13 and r[0].contagem == "2 de 3 podem"


def test_quem_so_disse_o_que_nao_pode_fica_livre_no_resto():
    r = cruzar({"a": [J(14, 8, 24, disponivel=False)], "b": [J(13, 19, 24), J(14, 19, 24)]}, TER)
    assert [j.inicio.day for j in r] == [13]


def test_menos_de_duas_pessoas_nao_gera_janela():
    assert cruzar({"a": [J(13, 19, 24)], "b": [J(14, 19, 24)]}, TER) == []


# ---------- horário de funcionamento dos lugares (RF-17)

@pytest.mark.parametrize("texto, situacao", [
    ("Terça a domingo: 17h às 23h30", "aberto"),
    ("Segunda a sexta: 18h às 23h", "fechado"),
    ("Segunda a quinta: 11h30 às 00h; Sexta a domingo: 11h30 às 01h30", "aberto"),
    ("Almoço de segunda a sexta", "fechado"),
    ("Noite de quarta a domingo; Almoço de sábado, domingo e feriados", "aberto"),
    ("Consultar no local", "incerto"),
    ("Domingo a quinta e sexta, sábados e feriados", "provavel"),
    ("8 a 10 de maio", "encerrado"),
    ("Somente até o final de julho", "encerrado"),
])
def test_situacao_no_sabado_a_noite(texto, situacao):
    s, _ = ler_funcionamento(texto, 2026).situacao(datetime(2026, 11, 14, 19), datetime(2026, 11, 15, 0))
    assert s == situacao


def test_trecho_aberto_e_o_cruzamento_com_a_janela():
    _, trecho = ler_funcionamento("Todos os dias: 12h às 22h30", 2026).situacao(datetime(2026, 11, 14, 19),
                                                                                 datetime(2026, 11, 15, 0))
    assert trecho == (datetime(2026, 11, 14, 19), datetime(2026, 11, 14, 22, 30))


# ---------- cartões de sugestão

def _perfil(origem, horarios, teto, prefs):
    p = interpretar_campos(origem, horarios, teto, prefs, agora=TER)
    assert p.completo, p.pendencias
    return p


LUGARES = [
    {"id": "perto", "nome": "Bar Perto", "tipo_de_role": "Bar / Boteco / Pub", "vibes": ["Calmo / Bom para Conversar"],
     "regiao_administrativa": "Taguatinga", "endereco": "QNA 1", "lat": -15.8147, "lng": -48.0251,
     "custo_medio_rs": 30, "horario_funcionamento": "Todos os dias: 18h às 01h", "ano_mes": "2026-10",
     "tiktok_url": "https://www.tiktok.com/@x/video/1", "autor_tiktok": "@x", "data_publicacao": "01/10/2026"},
    {"id": "caro", "nome": "Restaurante Caro", "tipo_de_role": "Restaurante / Gastronomia", "vibes": [],
     "regiao_administrativa": "Taguatinga", "endereco": "QNA 2", "lat": -15.8147, "lng": -48.0251,
     "custo_medio_rs": 200, "horario_funcionamento": "Todos os dias: 18h às 23h", "ano_mes": "2026-10"},
    {"id": "fechado", "nome": "Café da Manhã", "tipo_de_role": "Cafeteria / Doceria", "vibes": [],
     "regiao_administrativa": "Taguatinga", "endereco": "QNA 3", "lat": -15.8147, "lng": -48.0251,
     "custo_medio_rs": 20, "horario_funcionamento": "Todos os dias: 7h às 12h", "ano_mes": "2026-10"},
    {"id": "longe", "nome": "Bar Longe", "tipo_de_role": "Bar / Boteco / Pub", "vibes": [],
     "regiao_administrativa": "Santa Maria", "endereco": "QR 1", "lat": -16.0185, "lng": -48.0075,
     "custo_medio_rs": 25, "horario_funcionamento": "Consultar no local", "ano_mes": "2026-10"},
]


def test_cartoes_respeitam_horario_e_orcamento_e_preferem_o_justo():
    perfis = {"a": _perfil("Taguatinga", "sábado à noite", "60", "barzinho calmo, vou de ônibus"),
              "b": _perfil("Águas Claras", "sábado à noite", "45", "bar, vou de metrô")}
    janelas = cruzar({k: p.janelas for k, p in perfis.items()}, TER)
    r = motor.gerar(perfis, janelas, LUGARES, TER)
    nomes = [s.nome for s in r.sugestoes]
    assert nomes[0] == "Bar Perto"
    assert "Restaurante Caro" not in nomes and "Café da Manhã" not in nomes
    assert r.descartes == {"orcamento": 1, "horario": 1}
    perto = r.sugestoes[0]
    assert perto.horario_situacao == "aberto" and perto.inicio == datetime(2026, 11, 14, 19)
    assert perto.nota_justica > r.sugestoes[1].nota_justica
    assert "orçamento de todo o grupo" in perto.explicacao and "R$ 45" not in perto.explicacao


def test_orcamento_conta_o_transporte_de_cada_um():
    # Consumo de 30 + 11 de ônibus = 41: cabe em 45, mas não em 40
    lugar = [LUGARES[0]]
    ok = {"a": _perfil("Águas Claras", "sábado à noite", "45", "vou de ônibus"),
          "b": _perfil("Taguatinga", "sábado à noite", "100", "vou de ônibus")}
    apertado = {**ok, "a": _perfil("Águas Claras", "sábado à noite", "40", "vou de ônibus")}
    for perfis, n in ((ok, 1), (apertado, 0)):
        j = cruzar({k: p.janelas for k, p in perfis.items()}, TER)
        assert len(motor.gerar(perfis, j, lugar, TER).sugestoes) == n


def test_base_real_gera_cartoes_so_com_lugares_da_base():
    base = json.load(open("data/banco_aprovado_2fa.json", encoding="utf-8"))
    ids = {str(x["id"]) for x in base}
    perfis = {"a": _perfil("Asa Norte 408", "sábado à noite", "80", "restaurante animado, vou de carro"),
              "b": _perfil("Ceilândia Centro", "sábado depois das 18h", "60", "barzinho barato, vou de metrô"),
              "c": _perfil("Taguatinga", "sábado à noite", "70", "restaurante tranquilo, vou de ônibus")}
    j = cruzar({k: p.janelas for k, p in perfis.items()}, TER)
    r = motor.gerar(perfis, j, base, TER)
    assert 3 <= len(r.sugestoes) <= 4
    assert all(s.lugar_id in ids for s in r.sugestoes)  # RF-16 / RNF-03
    assert all(s.horario_situacao in ("aberto", "provavel", "incerto") for s in r.sugestoes)


# ---------- gerenciador e votação

@pytest.fixture
def g():
    return GerenciadorSalas(RepositorioMemoria(), relogio=lambda: TER, lugares=LUGARES)


def _sala_com_dois(g):
    sala, tok_org = g.criar_sala("Rolê de sábado", "Rafaela", True)
    a, ta = g.entrar(sala.codigo, "Rafaela", True, "Taguatinga", "sábado à noite", "60", "barzinho calmo, de ônibus")
    b, tb = g.entrar(sala.codigo, "Cadu", True, "Águas Claras", "sábado à noite", "45", "bar, de metrô")
    g.confirmar(sala.codigo, a.id, ta)
    g.confirmar(sala.codigo, b.id, tb)
    return sala.codigo, tok_org, (a.id, ta), (b.id, tb)


def test_menor_de_idade_nao_e_guardado(g):
    with pytest.raises(ErroSala) as e:
        g.criar_sala("Rolê", "Ana", False)
    assert e.value.status == 403
    sala, _ = g.criar_sala("Rolê", "Ana", True)
    with pytest.raises(ErroSala):
        g.entrar(sala.codigo, "Bia", False, "Guará", "sábado", "50", "")
    assert g.painel(sala.codigo)["participantes"] == []


def test_limite_de_20_e_nome_repetido(g):
    sala, _ = g.criar_sala("Rolê", "Ana", True)
    for i in range(LIMITE_PARTICIPANTES):
        g.entrar(sala.codigo, f"Pessoa {i}", True, "Guará", "sábado", "50", "")
    with pytest.raises(ErroSala) as e:
        g.entrar(sala.codigo, "Pessoa 21", True, "Guará", "sábado", "50", "")
    assert e.value.status == 409
    sala2, _ = g.criar_sala("Rolê", "Ana", True)
    g.entrar(sala2.codigo, "Bia", True, "Guará", "sábado", "50", "")
    with pytest.raises(ErroSala):
        g.entrar(sala2.codigo, "bia", True, "Guará", "sábado", "50", "")


def test_nao_confirma_com_pendencia_e_precisa_de_dois(g):
    sala, tok = g.criar_sala("Rolê", "Ana", True)
    p, t = g.entrar(sala.codigo, "Ana", True, "Marte", "sábado", "50", "")
    with pytest.raises(ErroSala) as e:
        g.confirmar(sala.codigo, p.id, t)
    assert e.value.status == 422 and "origem" in e.value.extra["pendencias"]
    g.corrigir(sala.codigo, p.id, t, "Guará", "sábado", "50", "")
    g.confirmar(sala.codigo, p.id, t)
    with pytest.raises(ErroSala) as e:
        g.gerar_sugestoes(sala.codigo, tok)
    assert e.value.status == 409


def test_so_o_organizador_gera_e_so_o_dono_ve_o_perfil(g):
    codigo, tok_org, (aid, ta), (bid, tb) = _sala_com_dois(g)
    with pytest.raises(ErroSala) as e:
        g.gerar_sugestoes(codigo, ta)
    assert e.value.status == 403
    with pytest.raises(ErroSala):
        g.visao_do_participante(codigo, aid, tb)
    assert g.visao_do_participante(codigo, aid, ta)["perfil"]["teto"] == "60.00"


def test_votacao_multipla_fecha_sozinha_e_desempata_pela_justica(g):
    codigo, tok_org, (aid, ta), (bid, tb) = _sala_com_dois(g)
    painel = g.gerar_sugestoes(codigo, tok_org)
    assert painel["status"] == VOTACAO and [s["nome"] for s in painel["sugestoes"]][0] == "Bar Perto"
    ids = [s["id"] for s in painel["sugestoes"]]
    g.votar(codigo, aid, ta, ids)            # vota em todos
    with pytest.raises(ErroSala):
        g.votar(codigo, bid, tb, ["Z"])
    painel = g.votar(codigo, bid, tb, ids)   # empate em tudo -> melhor nota de justiça
    assert painel["status"] == ORQUESTRADO
    r = painel["resultado"]
    melhor = max(painel["sugestoes"], key=lambda s: (s["nota_justica"], -s["posicao"]))
    assert r["sugestao_id"] == melhor["id"] and r["desempate_por_justica"] is (len(ids) > 1)
    assert r["mensagem"] == "🎉 Rolê orquestrado com sucesso!"
    assert "Bar Perto" in r["resumo_whatsapp"] and r["link_agenda"].startswith("https://calendar.google.com/")
    with pytest.raises(ErroSala):
        g.entrar(codigo, "Atrasado", True, "Guará", "sábado", "50", "")


def test_organizador_fecha_sem_esperar_todos(g):
    codigo, tok_org, (aid, ta), _ = _sala_com_dois(g)
    painel = g.gerar_sugestoes(codigo, tok_org)
    ultimo = painel["sugestoes"][-1]["id"]
    g.votar(codigo, aid, ta, [ultimo])
    painel = g.fechar_votacao(codigo, tok_org)
    assert painel["resultado"]["sugestao_id"] == ultimo and painel["resultado"]["votos"] == 1


# ---------- rotas e sigilo (RNF-02)

@pytest.fixture
def cliente(g):
    app.dependency_overrides[obter_gerenciador] = lambda: g
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_fluxo_completo_pela_api_sem_vazar_orcamento(cliente):
    r = cliente.post("/api/salas", json={"nome_role": "Aniversário", "organizador": "Rafaela", "maior_de_idade": True})
    assert r.status_code == 201
    codigo, tok_org = r.json()["codigo"], r.json()["token_organizador"]
    participantes = []
    for nome, origem, teto in (("Rafaela", "Taguatinga", "61"), ("Cadu", "Águas Claras", "47")):
        r = cliente.post(f"/api/salas/{codigo}/participantes", json={
            "nome": nome, "maior_de_idade": True, "origem": origem, "horarios": "sábado à noite", "teto": teto,
            "preferencias": "barzinho, vou de ônibus"})
        assert r.status_code == 201 and r.json()["perfil"]["teto"] == f"{teto}.00"
        pid, tok = r.json()["participante_id"], r.json()["token"]
        assert cliente.post(f"/api/salas/{codigo}/participantes/{pid}/confirmar").status_code == 403
        assert cliente.post(f"/api/salas/{codigo}/participantes/{pid}/confirmar",
                            headers={"X-Token": tok}).status_code == 200
        participantes.append((pid, tok))
    assert cliente.post(f"/api/salas/{codigo}/gerar-sugestoes", headers={"X-Token": participantes[0][1]}).status_code == 403
    r = cliente.post(f"/api/salas/{codigo}/gerar-sugestoes", headers={"X-Token": tok_org})
    assert r.status_code == 200 and r.json()["sugestoes"]
    for pid, tok in participantes:
        r = cliente.post(f"/api/salas/{codigo}/votar", headers={"X-Token": tok},
                         json={"participante_id": pid, "opcoes": ["A"]})
        assert r.status_code == 200
    publico = cliente.get(f"/api/salas/{codigo}").json()
    assert publico["status"] == ORQUESTRADO and publico["placar"]["A"] == 2
    texto = json.dumps(publico, ensure_ascii=False)
    for segredo in ("Águas Claras\"", "teto", "token", "sábado à noite"):
        assert segredo not in texto, segredo
    for teto in ("61", "47"):
        # o teto como número isolado, sem casar com pedaços de ids aleatórios ("47a3f1") nem de URLs ("%E2%80%93")
        assert not re.search(rf'(?<![\w.%]){teto}(?:[.,]00?)?(?![\w.%])', texto), teto
    minha = cliente.get(f"/api/salas/{codigo}/participantes/{participantes[1][0]}",
                        headers={"X-Token": participantes[1][1]}).json()
    assert minha["perfil"]["teto"] == "47.00" and minha["meu_custo_e_tempo"]["A"]["modo"] == "publico"


def test_erros_da_api(cliente):
    assert cliente.get("/api/salas/NAOEXISTE").status_code == 404
    r = cliente.post("/api/salas", json={"nome_role": "x", "organizador": "y", "maior_de_idade": False})
    assert r.status_code == 403
    r = cliente.post("/api/salas", json={"nome_role": "x", "organizador": "y", "maior_de_idade": True, "extra": 1})
    assert r.status_code == 422
