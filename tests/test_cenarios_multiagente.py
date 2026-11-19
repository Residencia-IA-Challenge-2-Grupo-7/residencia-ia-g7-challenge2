"""
Testes do dataset de cenários do multiagente da Semana 4 (issue #66).

Garante que data/cenarios_teste_multiagente.json segue o contrato combinado e
que o gabarito de cada amigo é o que o Agente 0 realmente entende dos 4 campos:

- estrutura: versão, cenários com id único, cenário padrão com m1 a m4;
- tipos e vocabulário: RAs entre as 35 oficiais, tetos dentro do limite da Tela 2,
  tags de tipo, vibe, restrição e transporte iguais às do interpretador;
- contraste: origens periféricas e central, tetos distintos, restrição alimentar;
- coerência: interpretar_campos() aplicado ao texto devolve o gabarito;
- resultados esperados: janela comum, teto do grupo e o veredito "sem lugar viável",
  com os vetos de cada lugar citado recalculados contra a base 2FA (RNF-03).

Os vetos são recalculados aqui com uma regra própria e simples (a de
`regra_dos_vetos` no JSON), usando só as medidas do repositório: tempo e custo de
`estimar_deslocamento` e situação de horário de `ler_funcionamento`. A decisão de
vetar não reaproveita o código dos agentes, para o gabarito poder pegar erro neles.
"""

import json
import re
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pytest

from src.financas.orcamento import teto_seguro_grupo
from src.interpretador.campos import (RESTRICOES, TETO_MAXIMO, TIPOS, TRANSPORTES, VIBES,
                                      interpretar_campos)
from src.interpretador.numeros import canon
from src.logistica.transporte_df import estimar_deslocamento
from src.salas.horario_lugar import ano_do_lugar, ler_funcionamento
from src.salas.integracoes import ra_do_lugar
from src.salas.janelas import cruzar
from src.salas.sugestoes import TERMOS_RESTRICAO

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

BASE_2FA = {
    registro["id"]: registro
    for registro in json.loads(
        (RAIZ / "data" / "banco_aprovado_2fa.json").read_text(encoding="utf-8")
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


# ------------------------------------------------------------------ resultados esperados (vetos e veredito)

CAMPOS_RESULTADOS = (
    "janela_comum",
    "teto_grupo_rs",
    "restricoes_duras_do_grupo",
    "veredito",
    "lugares_viaveis_esperados",
    "comportamento_esperado",
    "regra_dos_vetos",
    "locais_plausiveis",
    "nunca_sugerir",
)
CAMPOS_LUGAR_CITADO = ("id", "nome", "vetos_esperados")
# Mesmos rótulos de MotivoVeto (src/agentes/contratos.py)
MOTIVOS_VETO = {"horario", "orcamento", "restricao", "encerrado", "deslocamento"}
VEREDITOS = {"com_lugar_viavel", "sem_lugar_viavel"}
# Onde o texto de um lugar pode comprovar uma restrição (o mesmo que a busca lê)
CAMPOS_TEXTO_LUGAR = ("nome", "tipo_de_role", "resumo_sensorial", "legenda_original", "transcricao_audio_whisper")

ESPERADO = CENARIO_PADRAO["resultados_esperados"]
JANELA = ESPERADO["janela_comum"]
INICIO, FIM = datetime.fromisoformat(JANELA["inicio"]), datetime.fromisoformat(JANELA["fim"])
LUGARES_CITADOS = ESPERADO["locais_plausiveis"] + ESPERADO["nunca_sugerir"]


def _vetos(lugar, amigos=CENARIO_PADRAO["amigos"], inicio=INICIO, fim=FIM, motivos=MOTIVOS_VETO):
    """{motivo: marcadores barrados} de um lugar na janela, pela regra de `regra_dos_vetos`."""
    vetos = {}
    funcionamento = ler_funcionamento(lugar.get("horario_funcionamento"), ano_do_lugar(lugar, inicio.year))
    situacao, _ = funcionamento.situacao(inicio, fim)
    if situacao == "fechado":
        vetos["horario"] = []
    if situacao == "encerrado":
        vetos["encerrado"] = []

    consumo = Decimal(str(lugar.get("custo_medio_rs") or 0))
    texto = canon(" ".join(str(lugar.get(campo) or "") for campo in CAMPOS_TEXTO_LUGAR))
    for amigo in amigos:
        esperado = amigo["interpretacao_esperada"]
        marcador = amigo["marcador"]
        trajetos = []
        if lugar.get("lat") is not None and lugar.get("lng") is not None:
            trajetos = [estimar_deslocamento(esperado["ra"], lugar["lat"], lugar["lng"], modo, inicio)
                        for modo in esperado["transporte"]]
            trajetos = [t for t in trajetos if t]
        # sem trajeto estimável, a pessoa não tem como chegar nem como saber quanto gasta
        if not trajetos or min(t["minutos"] for t in trajetos) > amigo["tolerancia_deslocamento_max_min"]:
            vetos.setdefault("deslocamento", []).append(marcador)
        if not trajetos or consumo + min(t["custo_ida_volta"] for t in trajetos) > Decimal(str(esperado["teto_rs"])):
            vetos.setdefault("orcamento", []).append(marcador)
        for restricao in esperado["restricoes"]:
            if not re.search(TERMOS_RESTRICAO[restricao], texto):
                vetos.setdefault("restricao", []).append(marcador)
    return {motivo: barrados for motivo, barrados in vetos.items() if motivo in motivos}


def _perfis():
    agora = datetime.fromisoformat(CENARIO_PADRAO["agora_referencia"])
    return {
        amigo["marcador"]: interpretar_campos(
            *(amigo["campos_tela2"][campo] for campo in CAMPOS_TELA2), agora=agora
        )
        for amigo in CENARIO_PADRAO["amigos"]
    }


def test_resultados_esperados_tem_os_campos_e_o_veredito_coerente():
    """O bloco de resultados tem todos os campos; 'sem lugar viável' vem com a lista de viáveis vazia."""
    assert not [campo for campo in CAMPOS_RESULTADOS if campo not in ESPERADO]
    assert ESPERADO["veredito"] in VEREDITOS
    assert _texto_preenchido(ESPERADO["comportamento_esperado"])
    assert _texto_preenchido(ESPERADO["regra_dos_vetos"])
    assert (ESPERADO["veredito"] == "sem_lugar_viavel") == (ESPERADO["lugares_viaveis_esperados"] == [])


def test_janela_comum_e_a_que_o_cruzamento_de_horarios_acha():
    """A primeira janela de cruzar() é a do gabarito, com os 4 amigos presentes."""
    agora = datetime.fromisoformat(CENARIO_PADRAO["agora_referencia"])
    janelas = cruzar({marcador: perfil.janelas for marcador, perfil in _perfis().items()}, agora)
    assert janelas, "o cenário precisa ter ao menos uma janela comum"
    primeira = janelas[0]
    assert (primeira.inicio, primeira.fim) == (INICIO, FIM)
    assert sorted(primeira.presentes) == JANELA["presentes"] == ["m1", "m2", "m3", "m4"]


def test_teto_do_grupo_e_o_menor_teto_e_bate_com_as_financas():
    """O teto seguro do grupo é o menor teto individual, como calcula src/financas."""
    tetos = [Decimal(str(a["interpretacao_esperada"]["teto_rs"])) for a in CENARIO_PADRAO["amigos"]]
    assert Decimal(str(ESPERADO["teto_grupo_rs"])) == min(tetos) == teto_seguro_grupo(tetos)


def test_restricoes_duras_do_grupo_sao_a_uniao_das_individuais():
    """O grupo herda a restrição de qualquer membro (vegetariano do m1)."""
    unidas = sorted({r for a in CENARIO_PADRAO["amigos"] for r in a["interpretacao_esperada"]["restricoes"]})
    assert ESPERADO["restricoes_duras_do_grupo"] == unidas


def test_lugares_citados_existem_na_base_sem_repetir():
    """Todo lugar citado é um registro real da base 2FA, com o mesmo nome e a mesma RA (RNF-03)."""
    ids = [lugar["id"] for lugar in LUGARES_CITADOS]
    assert len(ids) == len(set(ids))
    for citado in LUGARES_CITADOS:
        assert not [c for c in CAMPOS_LUGAR_CITADO if c not in citado], citado.get("id")
        registro = BASE_2FA.get(citado["id"])
        assert registro is not None, f"{citado['id']} não está na base 2FA"
        assert citado["nome"] == registro["nome"]
        if "ra" in citado:
            assert citado["ra"] == ra_do_lugar(registro)
    assert len(ESPERADO["locais_plausiveis"]) >= 3, "a issue pede locais plausíveis da base"


@pytest.mark.parametrize("citado", LUGARES_CITADOS, ids=lambda c: c["nome"])
def test_vetos_esperados_batem_com_o_calculo(citado):
    """Os vetos anotados de cada lugar são os que a regra recalcula, com motivos e marcadores válidos."""
    anotados = citado["vetos_esperados"]
    marcadores = {amigo["marcador"] for amigo in CENARIO_PADRAO["amigos"]}
    assert anotados, "um lugar citado num cenário sem lugar viável precisa de pelo menos um veto"
    assert set(anotados) <= MOTIVOS_VETO
    assert all(set(barrados) <= marcadores for barrados in anotados.values())
    assert _vetos(BASE_2FA[citado["id"]]) == anotados


def test_plausiveis_cobrem_os_tipos_de_veto_mais_comuns():
    """Os quase-lá mostram vetos diferentes, para testar cada filtro da Validação."""
    motivos = {m for lugar in ESPERADO["locais_plausiveis"] for m in lugar["vetos_esperados"]}
    assert {"deslocamento", "orcamento", "restricao", "horario"} <= motivos


def test_nenhum_lugar_da_base_passa_em_todos_os_filtros():
    """Veredito: na janela comum, todo lugar da base leva pelo menos um veto."""
    viaveis = [registro["nome"] for registro in BASE_2FA.values() if not _vetos(registro)]
    assert viaveis == ESPERADO["lugares_viaveis_esperados"] == [], (
        f"a base passou a ter lugar viável para o cenário: {viaveis}. Atualize o gabarito."
    )


def test_so_o_deslocamento_ja_deixa_o_cenario_sem_resposta():
    """Mesmo sem olhar restrição, orçamento e horário, nenhum lugar fica a até a tolerância de todos."""
    alcancaveis = [registro["nome"] for registro in BASE_2FA.values()
                   if not _vetos(registro, motivos={"deslocamento"})]
    assert alcancaveis == []
