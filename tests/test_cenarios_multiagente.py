"""
Testes do dataset de cenários do multiagente da Semana 4 (issue #66).

Garante que data/cenarios_teste_multiagente.json segue o contrato combinado e
que o gabarito de cada amigo é o que o Agente 0 realmente entende dos 4 campos:

- estrutura: versão, cenários com id único, cenário padrão com m1 a m4;
- tipos e vocabulário: RAs entre as 35 oficiais, tetos dentro do limite da Tela 2,
  tags de tipo, vibe, restrição e transporte iguais às do interpretador;
- contraste: origens periféricas e central, tetos distintos, restrição alimentar;
- coerência: interpretar_campos() aplicado ao texto devolve o gabarito.
"""

import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pytest

from src.interpretador.campos import (RESTRICOES, TETO_MAXIMO, TIPOS, TRANSPORTES, VIBES,
                                      interpretar_campos)

RAIZ = Path(__file__).resolve().parent.parent
DATASET = json.loads(
    (RAIZ / "data" / "cenarios_teste_multiagente.json").read_text(encoding="utf-8")
)
REGIOES = {
    regiao["nome"]: regiao["macrorregiao"]
    for regiao in json.loads(
        (RAIZ / "data" / "regioes_df_gps.json").read_text(encoding="utf-8")
    )
}

ID_CENARIO_PADRAO = "cenario_padrao_4_amigos"
CAMPOS_CENARIO = ("id", "descricao", "agora_referencia", "amigos")
CAMPOS_AMIGO = (
    "marcador",
    "nome_ficticio",
    "papel_no_cenario",
    "tolerancia_deslocamento_max_min",
    "campos_tela2",
    "interpretacao_esperada",
)
CAMPOS_TELA2 = ("origem", "horarios", "teto", "preferencias")
CAMPOS_INTERPRETACAO = (
    "ra",
    "macrorregiao",
    "teto_rs",
    "janelas",
    "tipos",
    "vibes",
    "restricoes",
    "transporte",
)
# Teto de deslocamento usado pelo Agente 2 (docs/semanas/semana-04.md, seção 3)
TETO_DESLOCAMENTO_MIN = 75

CENARIOS = DATASET["cenarios"]
CENARIO_PADRAO = next(c for c in CENARIOS if c["id"] == ID_CENARIO_PADRAO)
TODOS_AMIGOS = [(c["id"], amigo) for c in CENARIOS for amigo in c["amigos"]]


def _id_amigo(par):
    cenario_id, amigo = par
    return f"{cenario_id}:{amigo.get('marcador', 'sem_marcador')}"


def _texto_preenchido(valor):
    return isinstance(valor, str) and valor.strip() != ""


def _numero(valor):
    return isinstance(valor, (int, float)) and not isinstance(valor, bool)


# ------------------------------------------------------------------ estrutura

def test_dataset_tem_versao_fontes_e_cenarios():
    """O arquivo declara versão, de onde vêm lugares e regiões e ao menos um cenário."""
    assert DATASET["versao"] == 1
    assert DATASET["fonte_lugares"] == "data/banco_aprovado_2fa.json"
    assert DATASET["fonte_regioes"] == "data/regioes_df_gps.json"
    assert isinstance(CENARIOS, list) and CENARIOS


def test_ids_de_cenario_sao_unicos_e_completos():
    """Cada cenário tem os campos obrigatórios e um id que não se repete."""
    ids = [cenario.get("id") for cenario in CENARIOS]
    assert len(ids) == len(set(ids))
    for cenario in CENARIOS:
        faltando = [campo for campo in CAMPOS_CENARIO if campo not in cenario]
        assert not faltando, f"{cenario.get('id')}: faltam {faltando}"
        datetime.fromisoformat(cenario["agora_referencia"])


def test_cenario_padrao_tem_4_amigos_m1_a_m4():
    """O cenário padrão da issue tem exatamente 4 amigos, marcados m1 a m4 em ordem."""
    marcadores = [amigo["marcador"] for amigo in CENARIO_PADRAO["amigos"]]
    assert marcadores == ["m1", "m2", "m3", "m4"]


@pytest.mark.parametrize("par", TODOS_AMIGOS, ids=_id_amigo)
def test_amigo_tem_campos_obrigatorios_e_tipos(par):
    """Todo amigo traz os 4 campos da Tela 2 em texto e a interpretação com os tipos certos."""
    _, amigo = par
    assert not [c for c in CAMPOS_AMIGO if c not in amigo]
    assert all(_texto_preenchido(amigo["campos_tela2"].get(c)) for c in CAMPOS_TELA2)

    esperado = amigo["interpretacao_esperada"]
    assert not [c for c in CAMPOS_INTERPRETACAO if c not in esperado]
    assert _numero(esperado["teto_rs"])
    for lista in ("tipos", "vibes", "restricoes", "transporte"):
        assert isinstance(esperado[lista], list)
    assert esperado["janelas"], "sem janela não há como cruzar horários"
    for janela in esperado["janelas"]:
        assert datetime.fromisoformat(janela["inicio"]) < datetime.fromisoformat(janela["fim"])


# ------------------------------------------------------------------ vocabulário oficial

@pytest.mark.parametrize("par", TODOS_AMIGOS, ids=_id_amigo)
def test_ra_e_macrorregiao_sao_oficiais(par):
    """A RA é uma das 35 de regioes_df_gps.json e a macrorregião é a dela."""
    _, amigo = par
    esperado = amigo["interpretacao_esperada"]
    assert esperado["ra"] in REGIOES
    assert esperado["macrorregiao"] == REGIOES[esperado["ra"]]


@pytest.mark.parametrize("par", TODOS_AMIGOS, ids=_id_amigo)
def test_teto_e_tolerancia_dentro_dos_limites(par):
    """Teto positivo até o limite da Tela 2; tolerância de deslocamento até o teto da Logística."""
    _, amigo = par
    teto = Decimal(str(amigo["interpretacao_esperada"]["teto_rs"]))
    assert Decimal("0") < teto <= TETO_MAXIMO
    tolerancia = amigo["tolerancia_deslocamento_max_min"]
    assert isinstance(tolerancia, int) and 0 < tolerancia <= TETO_DESLOCAMENTO_MIN


@pytest.mark.parametrize("par", TODOS_AMIGOS, ids=_id_amigo)
def test_tags_usam_o_vocabulario_do_interpretador(par):
    """Tipos, vibes, restrições e transportes são rótulos que o interpretador conhece."""
    _, amigo = par
    esperado = amigo["interpretacao_esperada"]
    assert set(esperado["tipos"]) <= set(TIPOS)
    assert set(esperado["vibes"]) <= set(VIBES)
    assert set(esperado["restricoes"]) <= set(RESTRICOES)
    assert set(esperado["transporte"]) <= set(TRANSPORTES)


# ------------------------------------------------------------------ contraste pedido na issue

def test_cenario_padrao_tem_perfis_contrastantes():
    """Periferia e centro, tetos todos diferentes, alguém com restrição e modos de transporte variados."""
    interpretacoes = [amigo["interpretacao_esperada"] for amigo in CENARIO_PADRAO["amigos"]]
    macrorregioes = [i["macrorregiao"] for i in interpretacoes]
    tetos = [i["teto_rs"] for i in interpretacoes]
    transportes = {modo for i in interpretacoes for modo in i["transporte"]}

    assert "centro" in macrorregioes
    assert sum(m != "centro" for m in macrorregioes) >= 2
    assert len(set(tetos)) == len(tetos)
    assert any(i["restricoes"] for i in interpretacoes)
    assert {"publico", "app"} <= transportes


def test_cenario_padrao_bate_com_a_issue_66():
    """Origem, teto e transporte de cada amigo são os da issue #66."""
    pedido = {
        "m1": ("Ceilândia", 40, {"publico"}, {"alim_vegetariano"}),
        "m2": ("Águas Claras", 70, {"publico"}, set()),
        "m3": ("Plano Piloto", 120, {"app", "carro"}, set()),
        "m4": ("Sobradinho", 50, {"publico"}, set()),
    }
    for amigo in CENARIO_PADRAO["amigos"]:
        ra, teto, transporte, restricoes = pedido[amigo["marcador"]]
        esperado = amigo["interpretacao_esperada"]
        assert esperado["ra"] == ra
        assert esperado["teto_rs"] == teto
        assert set(esperado["transporte"]) == transporte
        assert set(esperado["restricoes"]) == restricoes
    m2, m3 = CENARIO_PADRAO["amigos"][1], CENARIO_PADRAO["amigos"][2]
    assert "Ao Ar Livre / Parque" in m2["interpretacao_esperada"]["tipos"]
    assert "Restaurante / Gastronomia" in m3["interpretacao_esperada"]["tipos"]
    assert CENARIO_PADRAO["amigos"][3]["tolerancia_deslocamento_max_min"] < TETO_DESLOCAMENTO_MIN


# ------------------------------------------------------------------ coerência com o Agente 0

@pytest.mark.parametrize("par", TODOS_AMIGOS, ids=_id_amigo)
def test_interpretador_reproduz_o_gabarito(par):
    """O texto da Tela 2 passado por interpretar_campos() devolve exatamente a interpretação esperada."""
    cenario_id, amigo = par
    cenario = next(c for c in CENARIOS if c["id"] == cenario_id)
    campos = amigo["campos_tela2"]
    perfil = interpretar_campos(
        campos["origem"],
        campos["horarios"],
        campos["teto"],
        campos["preferencias"],
        agora=datetime.fromisoformat(cenario["agora_referencia"]),
    )
    esperado = amigo["interpretacao_esperada"]

    assert perfil.completo, perfil.pendencias
    assert perfil.ra == esperado["ra"]
    assert perfil.regiao == esperado["macrorregiao"]
    assert perfil.teto == Decimal(str(esperado["teto_rs"]))
    assert [(j.inicio.isoformat(), j.fim.isoformat()) for j in perfil.janelas] == [
        (j["inicio"], j["fim"]) for j in esperado["janelas"]
    ]
    assert perfil.preferencias.tipos == esperado["tipos"]
    assert perfil.preferencias.vibes == esperado["vibes"]
    assert perfil.preferencias.restricoes == esperado["restricoes"]
    assert perfil.preferencias.transporte == esperado["transporte"]
