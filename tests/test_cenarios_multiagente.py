"""
Testes do dataset de cenários do multiagente da Semana 4 (issue #66).

Garante que data/cenarios_teste_multiagente.json segue o contrato combinado e
que o gabarito de cada amigo é o que o Agente 0 realmente entende dos 4 campos:

- estrutura: versão, cenários com id único, cenário padrão com m1 a m4;
- tipos e vocabulário: RAs entre as 35 oficiais, tetos dentro do limite da Tela 2,
  tags de tipo, vibe, restrição e transporte iguais às do interpretador;
- contraste: origens periféricas e central, tetos distintos, restrição alimentar;
- coerência: interpretar_campos() aplicado ao texto devolve o gabarito;
- resultados esperados de cada cenário: janela comum, teto do grupo, veredito e os vetos
  de cada lugar citado, recalculados contra a base 2FA (RNF-03). O cenário padrão não tem
  lugar viável; o de controle tem, para cobrir o caminho feliz.

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
from typing import get_args

import pytest

from src.agentes.cenarios import carregar_cenario, carregar_cenarios, para_entrada_do_grafo
from src.agentes.contratos import MotivoVeto
from src.financas.orcamento import teto_seguro_grupo
from src.interpretador.campos import (RESTRICOES, TETO_MAXIMO, TIPOS, TRANSPORTES, VIBES,
                                      interpretar_campos)
from src.interpretador.numeros import canon
from src.logistica.transporte_df import estimar_deslocamento
from src.salas.gerenciador_salas import ALFABETO_CODIGO, PREFIXO_CODIGO
from src.salas.horario_lugar import ano_do_lugar, ler_funcionamento
from src.salas.integracoes import ra_do_lugar
from src.salas.janelas import cruzar
from src.salas.sugestoes import TEMPO_ACEITAVEL_MIN, TERMOS_RESTRICAO

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
ID_CENARIO_CONTROLE = "cenario_controle_viavel"
CAMPOS_CENARIO = ("id", "codigo_sala", "descricao", "agora_referencia", "amigos")
CAMPOS_AMIGO = (
    "marcador",
    "nome_ficticio",
    "papel_no_cenario",
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
# Teto de deslocamento da Logística, o mesmo para todos (docs/semanas/semana-04.md, seção 3).
# Vem do código das salas para o gabarito seguir a mesma regra que os agentes vão aplicar.
TETO_DESLOCAMENTO_MIN = TEMPO_ACEITAVEL_MIN

CENARIOS = DATASET["cenarios"]
CENARIO_PADRAO = next(c for c in CENARIOS if c["id"] == ID_CENARIO_PADRAO)
CENARIO_CONTROLE = next(c for c in CENARIOS if c["id"] == ID_CENARIO_CONTROLE)
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
def test_teto_dentro_do_limite_da_tela_2(par):
    """Teto positivo e até o limite que a Tela 2 aceita."""
    _, amigo = par
    teto = Decimal(str(amigo["interpretacao_esperada"]["teto_rs"]))
    assert Decimal("0") < teto <= TETO_MAXIMO


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
    # A "tolerância moderada" do m4 fica só no texto: o sistema não lê minutos da Tela 2
    assert "muito longe" in CENARIO_PADRAO["amigos"][3]["campos_tela2"]["preferencias"]


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
CAMPOS_LUGAR_CITADO = ("id", "nome", "vetos_do_lugar", "vetos_por_membro")
CAMPOS_LUGAR_VIAVEL = ("id", "nome", "ra")
# Os rótulos são os de MotivoVeto (src/agentes/contratos.py), divididos pelo que cada um barra:
# a situação do lugar vale para todos; os demais barram membros específicos.
MOTIVOS_VETO = frozenset(get_args(MotivoVeto))
MOTIVOS_DO_LUGAR = frozenset({"horario", "encerrado"})
MOTIVOS_POR_MEMBRO = MOTIVOS_VETO - MOTIVOS_DO_LUGAR
VEREDITOS = {"com_lugar_viavel", "sem_lugar_viavel"}
# Onde o texto de um lugar pode comprovar uma restrição (o mesmo que a busca lê)
CAMPOS_TEXTO_LUGAR = ("nome", "tipo_de_role", "resumo_sensorial", "legenda_original", "transcricao_audio_whisper")


def _janela(cenario):
    janela = cenario["resultados_esperados"]["janela_comum"]
    return datetime.fromisoformat(janela["inicio"]), datetime.fromisoformat(janela["fim"])


def _citados(cenario):
    esperado = cenario["resultados_esperados"]
    return esperado["locais_plausiveis"] + esperado["nunca_sugerir"]


def _marcadores(cenario):
    return {amigo["marcador"] for amigo in cenario["amigos"]}


CITADOS = [(c["id"], citado) for c in CENARIOS for citado in _citados(c)]
POR_ID = {c["id"]: c for c in CENARIOS}


def _id_citado(par):
    cenario_id, citado = par
    return f"{cenario_id}:{citado['nome']}"


def _vetos(lugar, cenario=CENARIO_PADRAO, motivos=MOTIVOS_VETO):
    """(vetos do lugar, {motivo: marcadores barrados}) na janela comum, pela regra de `regra_dos_vetos`."""
    inicio, fim = _janela(cenario)
    do_lugar = []
    funcionamento = ler_funcionamento(lugar.get("horario_funcionamento"), ano_do_lugar(lugar, inicio.year))
    situacao, _ = funcionamento.situacao(inicio, fim)
    if situacao == "fechado":
        do_lugar.append("horario")
    if situacao == "encerrado":
        do_lugar.append("encerrado")

    por_membro = {}
    consumo = Decimal(str(lugar.get("custo_medio_rs") or 0))
    texto = canon(" ".join(str(lugar.get(campo) or "") for campo in CAMPOS_TEXTO_LUGAR))
    for amigo in cenario["amigos"]:
        esperado = amigo["interpretacao_esperada"]
        marcador = amigo["marcador"]
        trajetos = []
        if lugar.get("lat") is not None and lugar.get("lng") is not None:
            trajetos = [estimar_deslocamento(esperado["ra"], lugar["lat"], lugar["lng"], modo, inicio)
                        for modo in esperado["transporte"]]
            trajetos = [t for t in trajetos if t]
        # sem trajeto estimável, a pessoa não tem como chegar nem como saber quanto gasta
        if not trajetos or min(t["minutos"] for t in trajetos) > TETO_DESLOCAMENTO_MIN:
            por_membro.setdefault("deslocamento", []).append(marcador)
        if not trajetos or consumo + min(t["custo_ida_volta"] for t in trajetos) > Decimal(str(esperado["teto_rs"])):
            por_membro.setdefault("orcamento", []).append(marcador)
        for restricao in esperado["restricoes"]:
            if not re.search(TERMOS_RESTRICAO[restricao], texto):
                por_membro.setdefault("restricao", []).append(marcador)
    return ([m for m in do_lugar if m in motivos],
            {m: barrados for m, barrados in por_membro.items() if m in motivos})


def _viavel(lugar, cenario=CENARIO_PADRAO, motivos=MOTIVOS_VETO):
    do_lugar, por_membro = _vetos(lugar, cenario, motivos)
    return not do_lugar and not por_membro


def _motivos(citado):
    """O que a Validação deve dizer de um lugar: só o conjunto de motivos, sem quem foi barrado."""
    return set(citado["vetos_do_lugar"]) | set(citado["vetos_por_membro"])


def _perfis(cenario):
    agora = datetime.fromisoformat(cenario["agora_referencia"])
    return {
        amigo["marcador"]: interpretar_campos(
            *(amigo["campos_tela2"][campo] for campo in CAMPOS_TELA2), agora=agora
        )
        for amigo in cenario["amigos"]
    }


@pytest.mark.parametrize("cenario", CENARIOS, ids=lambda c: c["id"])
def test_resultados_esperados_tem_os_campos_e_o_veredito_coerente(cenario):
    """Todo cenário tem o bloco de resultados; o veredito bate com a lista de viáveis estar vazia ou não."""
    esperado = cenario["resultados_esperados"]
    assert not [campo for campo in CAMPOS_RESULTADOS if campo not in esperado]
    assert esperado["veredito"] in VEREDITOS
    assert _texto_preenchido(esperado["comportamento_esperado"])
    assert _texto_preenchido(esperado["regra_dos_vetos"])
    assert (esperado["veredito"] == "sem_lugar_viavel") == (esperado["lugares_viaveis_esperados"] == [])


def test_dataset_tem_um_cenario_sem_e_um_com_lugar_viavel():
    """O padrão é o teste de estresse; o de controle cobre o caminho feliz até os cartões."""
    assert CENARIO_PADRAO["resultados_esperados"]["veredito"] == "sem_lugar_viavel"
    assert CENARIO_CONTROLE["resultados_esperados"]["veredito"] == "com_lugar_viavel"


@pytest.mark.parametrize("cenario", CENARIOS, ids=lambda c: c["id"])
def test_janela_comum_e_a_que_o_cruzamento_de_horarios_acha(cenario):
    """A primeira janela de cruzar() é a do gabarito, com os presentes anotados."""
    agora = datetime.fromisoformat(cenario["agora_referencia"])
    janelas = cruzar({marcador: perfil.janelas for marcador, perfil in _perfis(cenario).items()}, agora)
    assert janelas, "o cenário precisa ter ao menos uma janela comum"
    primeira = janelas[0]
    assert (primeira.inicio, primeira.fim) == _janela(cenario)
    assert sorted(primeira.presentes) == cenario["resultados_esperados"]["janela_comum"]["presentes"]


@pytest.mark.parametrize("cenario", CENARIOS, ids=lambda c: c["id"])
def test_teto_do_grupo_e_o_menor_teto_e_bate_com_as_financas(cenario):
    """O teto seguro do grupo é o menor teto individual, como calcula src/financas."""
    tetos = [Decimal(str(a["interpretacao_esperada"]["teto_rs"])) for a in cenario["amigos"]]
    teto = Decimal(str(cenario["resultados_esperados"]["teto_grupo_rs"]))
    assert teto == min(tetos) == teto_seguro_grupo(tetos)


@pytest.mark.parametrize("cenario", CENARIOS, ids=lambda c: c["id"])
def test_restricoes_duras_do_grupo_sao_a_uniao_das_individuais(cenario):
    """O grupo herda a restrição de qualquer membro."""
    unidas = sorted({r for a in cenario["amigos"] for r in a["interpretacao_esperada"]["restricoes"]})
    assert cenario["resultados_esperados"]["restricoes_duras_do_grupo"] == unidas


@pytest.mark.parametrize("cenario", CENARIOS, ids=lambda c: c["id"])
def test_lugares_citados_existem_na_base_sem_repetir(cenario):
    """Todo lugar citado ou viável é um registro real da base 2FA, com o mesmo nome e a mesma RA (RNF-03)."""
    esperado = cenario["resultados_esperados"]
    citados = _citados(cenario)
    ids = [lugar["id"] for lugar in citados]
    assert len(ids) == len(set(ids))
    for citado in citados:
        assert not [c for c in CAMPOS_LUGAR_CITADO if c not in citado], citado.get("id")
    for viavel in esperado["lugares_viaveis_esperados"]:
        assert not [c for c in CAMPOS_LUGAR_VIAVEL if c not in viavel], viavel.get("id")
        assert viavel["id"] not in ids, f"{viavel['nome']} não pode ser viável e vetado ao mesmo tempo"
    for lugar in citados + esperado["lugares_viaveis_esperados"]:
        registro = BASE_2FA.get(lugar["id"])
        assert registro is not None, f"{lugar['id']} não está na base 2FA"
        assert lugar["nome"] == registro["nome"]
        if "ra" in lugar:
            assert lugar["ra"] == ra_do_lugar(registro)


def test_cenario_padrao_tem_ao_menos_3_locais_plausiveis():
    """A issue pede locais plausíveis da base para o cenário dos 4 amigos."""
    assert len(CENARIO_PADRAO["resultados_esperados"]["locais_plausiveis"]) >= 3


@pytest.mark.parametrize("par", CITADOS, ids=_id_citado)
def test_vetos_do_lugar_e_por_membro_ficam_cada_um_no_seu_campo(par):
    """Horário e encerrado só em vetos_do_lugar; os outros só em vetos_por_membro, sempre com alguém barrado."""
    cenario_id, citado = par
    assert set(citado["vetos_do_lugar"]) <= MOTIVOS_DO_LUGAR
    assert set(citado["vetos_por_membro"]) <= MOTIVOS_POR_MEMBRO
    for motivo, barrados in citado["vetos_por_membro"].items():
        assert barrados, f"{motivo} sem ninguém barrado: tire o motivo em vez de deixar a lista vazia"
        assert set(barrados) <= _marcadores(POR_ID[cenario_id])
    assert _motivos(citado), "um lugar citado como vetado precisa de pelo menos um veto"


@pytest.mark.parametrize("par", CITADOS, ids=_id_citado)
def test_vetos_esperados_batem_com_o_calculo(par):
    """Os vetos anotados de cada lugar são os que a regra recalcula no cenário dele."""
    cenario_id, citado = par
    do_lugar, por_membro = _vetos(BASE_2FA[citado["id"]], POR_ID[cenario_id])
    assert do_lugar == citado["vetos_do_lugar"]
    assert por_membro == citado["vetos_por_membro"]


@pytest.mark.parametrize("cenario", CENARIOS, ids=lambda c: c["id"])
def test_comparacao_com_a_validacao_e_so_pelos_motivos_do_lugar(cenario):
    """A projeção para a Validação ({id: motivos}) usa só rótulos de MotivoVeto e não carrega marcadores."""
    projecao = {citado["id"]: _motivos(citado) for citado in _citados(cenario)}
    for motivos in projecao.values():
        assert motivos <= MOTIVOS_VETO
        assert not motivos & _marcadores(cenario)


def test_plausiveis_cobrem_os_tipos_de_veto_mais_comuns():
    """Os quase-lá do cenário padrão mostram vetos diferentes, para testar cada filtro da Validação."""
    plausiveis = CENARIO_PADRAO["resultados_esperados"]["locais_plausiveis"]
    motivos = set().union(*(_motivos(lugar) for lugar in plausiveis))
    assert {"deslocamento", "orcamento", "restricao", "horario"} <= motivos


@pytest.mark.parametrize("cenario", CENARIOS, ids=lambda c: c["id"])
def test_viaveis_esperados_sao_exatamente_os_que_passam_em_todos_os_filtros(cenario):
    """Veredito: na janela comum, passam em todos os filtros exatamente os lugares listados como viáveis."""
    calculados = sorted(r["id"] for r in BASE_2FA.values() if _viavel(r, cenario))
    anotados = sorted(lugar["id"] for lugar in cenario["resultados_esperados"]["lugares_viaveis_esperados"])
    nomes = {r["id"]: r["nome"] for r in BASE_2FA.values()}
    assert calculados == anotados, (
        f"viáveis calculados: {[nomes[i] for i in calculados]}; anotados: {[nomes[i] for i in anotados]}. "
        "A base ou o estimador mudou: atualize o gabarito."
    )


def test_cenario_de_controle_tem_lugares_para_3_a_4_cartoes():
    """Com pelo menos 3 viáveis, a Comunicação consegue montar os 3 a 4 cartões da Tela 3."""
    assert len(CENARIO_CONTROLE["resultados_esperados"]["lugares_viaveis_esperados"]) >= 3


def test_cenario_de_controle_muda_so_a_restricao_do_m1_e_a_origem_do_m4():
    """O controle é o padrão com a menor mudança que deixa lugar viável; o resto é idêntico."""
    assert CENARIO_CONTROLE["agora_referencia"] == CENARIO_PADRAO["agora_referencia"]
    diferencas = {
        (padrao["marcador"], campo)
        for padrao, controle in zip(CENARIO_PADRAO["amigos"], CENARIO_CONTROLE["amigos"], strict=True)
        for campo in CAMPOS_TELA2
        if padrao["campos_tela2"][campo] != controle["campos_tela2"][campo]
    }
    assert diferencas == {("m1", "preferencias"), ("m4", "origem")}
    assert CENARIO_PADRAO["amigos"][0]["interpretacao_esperada"]["restricoes"] == ["alim_vegetariano"]
    assert CENARIO_CONTROLE["amigos"][0]["interpretacao_esperada"]["restricoes"] == []
    assert CENARIO_CONTROLE["amigos"][3]["interpretacao_esperada"]["ra"] == "Taguatinga"


# O veredito do cenário padrão se apoia no que não depende da calibração do estimador de
# deslocamento (#67): o texto da base (quem comprova opção vegetariana) e o dinheiro. Com o
# estimador atual o deslocamento também veta tudo, mas isso pode mudar sem mudar o veredito.
LUGARES_COM_OPCAO_VEGETARIANA = ["Pizzaria Natureto", "Yaki Nikuya", "The Plenty"]


def test_so_3_lugares_da_base_comprovam_opcao_vegetariana():
    """Pela restrição sozinha, sobram só os 3 lugares cujo texto cita opção vegetariana ou vegana."""
    sem_veto_de_restricao = [registro["nome"] for registro in BASE_2FA.values()
                             if _viavel(registro, CENARIO_PADRAO, motivos={"restricao"})]
    assert sorted(sem_veto_de_restricao) == sorted(LUGARES_COM_OPCAO_VEGETARIANA)


def test_restricao_e_orcamento_sozinhos_ja_deixam_o_cenario_sem_resposta():
    """Sem olhar deslocamento nem horário, nenhum dos 3 vegetarianos cabe no teto de R$ 40 do m1."""
    viaveis = [registro["nome"] for registro in BASE_2FA.values()
               if _viavel(registro, CENARIO_PADRAO, motivos={"restricao", "orcamento"})]
    assert viaveis == []


# ------------------------------------------------------------------ entrada do grafo (src/agentes/cenarios.py)

CODIGO_SALA = re.compile(rf"{re.escape(PREFIXO_CODIGO)}[{ALFABETO_CODIGO}]{{4}}")
CAMPOS_MEMBRO_GRAFO = {"nome", *CAMPOS_TELA2}


def test_codigo_de_sala_de_cada_cenario_e_valido_e_unico():
    """O código fixo de cada cenário segue o formato das salas (ROLE- + 4 do alfabeto) e não se repete."""
    codigos = [cenario["codigo_sala"] for cenario in CENARIOS]
    assert len(codigos) == len(set(codigos))
    assert all(CODIGO_SALA.fullmatch(codigo) for codigo in codigos), codigos


def test_carregar_cenarios_le_o_mesmo_arquivo_dos_testes():
    """O módulo e os testes leem o mesmo dataset, na mesma ordem."""
    assert [c["id"] for c in carregar_cenarios()] == [c["id"] for c in CENARIOS]
    assert carregar_cenario(ID_CENARIO_CONTROLE)["id"] == ID_CENARIO_CONTROLE


def test_cenario_inexistente_diz_quais_existem():
    with pytest.raises(KeyError, match=ID_CENARIO_PADRAO):
        carregar_cenario("cenario_que_nao_existe")


@pytest.mark.parametrize("cenario", CENARIOS, ids=lambda c: c["id"])
def test_entrada_do_grafo_tem_o_formato_e_a_data_do_cenario(cenario):
    """codigo, agora (sempre o agora_referencia) e um membro por amigo, com nome e os 4 campos da Tela 2."""
    entrada = para_entrada_do_grafo(cenario)
    assert set(entrada) == {"codigo", "agora", "membros"}
    assert entrada["codigo"] == cenario["codigo_sala"]
    assert entrada["agora"] == cenario["agora_referencia"]
    assert len(entrada["membros"]) == len(cenario["amigos"])
    for membro, amigo in zip(entrada["membros"], cenario["amigos"], strict=True):
        assert set(membro) == CAMPOS_MEMBRO_GRAFO
        assert membro["nome"] == amigo["nome_ficticio"]
        assert all(membro[campo] == amigo["campos_tela2"][campo] for campo in CAMPOS_TELA2)


@pytest.mark.parametrize("cenario", CENARIOS, ids=lambda c: c["id"])
def test_entrada_do_grafo_nao_leva_o_gabarito(cenario):
    """Nem a interpretação esperada, nem os resultados, nem os marcadores chegam ao sistema testado."""
    texto = json.dumps(para_entrada_do_grafo(cenario), ensure_ascii=False)
    for proibido in ("interpretacao_esperada", "resultados_esperados", "vetos", "veredito", "marcador",
                     "papel_no_cenario", '"m1"', '"m4"'):
        assert proibido not in texto
