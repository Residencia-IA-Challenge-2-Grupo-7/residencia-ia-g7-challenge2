"""Testes do estado compartilhado do grafo multiagente (issue #64, src/agentes/estado.py), sem rede.

Conferem os campos que a issue pede, os reducers, a ida e volta em JSON e que a serialização recusa dado do cofre
(nome, id de usuário, teto, origem) em qualquer nível (RNF-02). O estado de exemplo tem a forma do que o grafo produz
numa sala de 4 pessoas; o teste de que o grafo de fato o preenche está em test_grafo_multiagente.py.
"""
from __future__ import annotations

import copy
import json
import operator
from datetime import datetime
from typing import get_type_hints

import pytest
from pydantic import ValidationError

from src.agentes.contratos import Cofre, Membro
from src.agentes.estado import (CHAVES_PRIVADAS, EstadoSerializado, MultiAgentState, VazamentoNoEstado,
                                dados_privados_no_estado, desserializar_estado, serializar_estado)

CAMPOS_DA_ISSUE = ("sala_id", "membros_anonimos", "preferencias_grupo", "candidatos_pesquisa", "candidatos_avaliados",
                   "candidatos_validados", "resultado_final_cartoes", "iteracao_pesquisa", "historico_erros")


def _anonimo(tipos, vibes, restricoes=(), transporte=("metro",)):
    return {"tipos": list(tipos), "vibes": list(vibes), "evitar": [], "restricoes": list(restricoes),
            "transporte": list(transporte), "trecho_pedido": "", "itens_do_log_usados": 0}


def _avaliado(i, nome, ra, nota, pior):
    return {"id": i, "nome": nome, "ra_do_lugar": ra, "janela": "sábado, 18h às 21h", "quantos_podem": "4 de 4",
            "horario_situacao": "aberto", "nota_justica": nota, "pior_trajeto_min": pior, "media_trajeto_min": pior - 12,
            "diferenca_min": 20, "estimativa_provisoria": False, "pontuacao": round(nota / 100, 3)}


AVALIADOS = [_avaliado("l1", "Café Calmo", "Taguatinga", 82, 41), _avaliado("l2", "Bar da Praça", "Guará", 77, 45),
             _avaliado("l3", "Doceria Sul", "Águas Claras", 74, 50), _avaliado("l4", "Espetinho", "Gama", 40, 95)]
ESTADO: MultiAgentState = {
    "sala_id": "ROLE-AB12",
    "membros": ["m1", "m2", "m3", "m4"],
    "membros_anonimos": [_anonimo(["comer_beber"], ["Animado / Galera"]), _anonimo(["comer_beber"], []),
                         _anonimo([], [], ["alim_vegetariano"], ["onibus"]),
                         _anonimo(["comer_beber"], ["Calmo / Bom para Conversar"])],
    "preferencias_grupo": {"tamanho": 4, "tipos": ["comer_beber"], "tipos_pedidos": {"comer_beber": "3 de 4"},
                           "vibes": ["Animado / Galera", "Calmo / Bom para Conversar"], "evitar": [],
                           "restricoes": ["alim_vegetariano"], "trechos_pedido": ["restaurante calmo"],
                           "janela": "sábado, 18h às 21h (4 de 4)"},
    "candidatos_pesquisa": [{"id": c["id"], "motivo": "Combina com o pedido.", "trecho": c["nome"]} for c in AVALIADOS],
    "documentos": {"l1": {"id": "l1", "nome": "Café Calmo", "tipo": "Cafeteria / Doceria", "regiao_do_lugar":
                          "Taguatinga", "vibes": ["Calmo / Bom para Conversar"], "descricao": "Café com mesas.",
                          "pontuacao": 0.98}},
    "vistos": ["l1", "l2", "l3", "l4"],
    "pedido_nova_busca": None,
    "iteracao_pesquisa": 1,
    "candidatos_avaliados": AVALIADOS,
    "julgados": [],
    "relatorio_validacao": {"aprovados": ["l1", "l2", "l3"], "vetos": [{"id": "l4", "motivo": "restricao"}],
                            "contagem": {"restricao": 1}, "teto_aplicado": True, "derrubados_pelo_juiz": []},
    "candidatos_validados": AVALIADOS[:3],
    "fatos": [{"id": "A", "nome": "Café Calmo", "sinais": {"chegada_equilibrada": True}}],
    "cartoes": [{"id": "A", "titulo": "Café para conversar", "resumo_acesso": "Todo mundo chega junto.",
                 "por_que_combina": "É calmo, como o grupo pediu."}],
    "cartoes_por_llm": True,
    "reprovados": {},
    "reescritas": 0,
    "resultado_final_cartoes": [{"id": "A", "lugar_id": "l1", "nome": "Café Calmo", "faixa_gasto_rs":
                                 {"min": "45.00", "max": "60.00"}, "titulo": "Café para conversar"}],
    "mensagens": [{"de": "Validação", "para": "Pesquisa", "texto": "Só 2 lugares passaram (vetos: 1 por restricao).",
                   "em": "10:00:01", "vereditos_juiz": {}},
                  {"de": "Pesquisa", "para": "Logística", "texto": "Nova busca: 4 candidatos.", "em": "10:00:02",
                   "usou_llm": True, "consultas": ["café calmo"]}],
    "historico_erros": ["validacao (volta 0): l4 vetado por restricao"],
}


@pytest.fixture
def cofre():
    membros = {f"m{i}": Membro(id=f"m{i}", usuario=f"usuario-{i}", nome=n, perfil=None)
               for i, n in enumerate(("Bia", "Caio", "Duda", "Leo"), 1)}
    return Cofre(membros=membros, janelas=[], agora=datetime(2026, 11, 17, 10), lugares={}, store=None,
                 sala_id="ROLE-AB12")


def test_estado_declara_os_campos_da_issue_com_reducers_nos_acumulativos():
    tipos = get_type_hints(MultiAgentState, include_extras=True)
    assert set(CAMPOS_DA_ISSUE) <= set(tipos)
    for campo in ("membros_anonimos", "mensagens", "historico_erros"):
        assert operator.add in tipos[campo].__metadata__, campo
    assert not hasattr(tipos["iteracao_pesquisa"], "__metadata__")
    assert set(tipos) == set(EstadoSerializado.model_fields)  # o espelho Pydantic cobre todo o estado


def test_reducer_soma_os_perfis_dos_agentes_pessoais_em_paralelo():
    reducer = get_type_hints(MultiAgentState, include_extras=True)["membros_anonimos"].__metadata__[0]
    um, outro = [ESTADO["membros_anonimos"][0]], [ESTADO["membros_anonimos"][1]]
    assert reducer(um, outro) == ESTADO["membros_anonimos"][:2]


def test_ida_e_volta_em_json_preserva_o_estado(cofre):
    texto = serializar_estado(ESTADO, cofre)
    lido = desserializar_estado(texto)
    assert lido == ESTADO
    assert serializar_estado(lido, cofre) == texto


def test_estado_de_exemplo_nao_tem_dado_do_cofre(cofre):
    assert dados_privados_no_estado(ESTADO, cofre) == []
    assert not CHAVES_PRIVADAS & set(json.loads(serializar_estado(ESTADO)))


def test_link_do_trace_faz_parte_do_estado_e_vai_e_volta():
    com_trace = {**ESTADO, "trace_url": "https://cloud.langfuse.com/project/p/traces/1"}
    assert desserializar_estado(serializar_estado(com_trace))["trace_url"] == com_trace["trace_url"]


@pytest.mark.parametrize("estrago", [
    {"teto_rs": 80},
    {"preferencias_grupo": {"origem": "Samambaia"}},
    {"candidatos_avaliados": [{"id": "x", "por_participante": {"m1": 40}}]},
    {"fatos": [{"id": "A", "sinais": {"teto_individual": 60}}]},  # campo dict livre: a varredura pega
])
def test_serializacao_recusa_chave_privada_em_qualquer_nivel(estrago):
    with pytest.raises(VazamentoNoEstado):
        serializar_estado({"sala_id": "ROLE-AB12", **estrago})


@pytest.mark.parametrize("texto, achado", [("Caio não pode no sábado", "nome de m2"),
                                           ("log de usuario-4 lido", "usuario de m4")])
def test_serializacao_recusa_nome_ou_usuario_de_membro_num_texto(cofre, texto, achado):
    vazado = copy.deepcopy(ESTADO)
    vazado["historico_erros"].append(texto)
    with pytest.raises(VazamentoNoEstado, match=achado):
        serializar_estado(vazado, cofre)


def _cofre_com(*nomes, lugares=("Maria Fumaça",)):
    membros = {f"m{i}": Membro(id=f"m{i}", usuario=f"usuario-{i}", nome=n, perfil=None) for i, n in enumerate(nomes, 1)}
    return Cofre(membros=membros, janelas=[], agora=datetime(2026, 11, 17, 10), store=None,
                 lugares={f"l{i}": {"id": f"l{i}", "nome": n} for i, n in enumerate(lugares, 1)})


def _com_texto(texto: str) -> dict:
    return {**ESTADO, "historico_erros": [texto]}


@pytest.mark.parametrize("nome, texto, achado", [
    ("Bia", "o pedido da bia foi aceito", "nome de m1"),                    # minúsculas
    ("Otávio", "OTAVIO não pode no sábado", "nome de m1"),                  # sem acento e em maiúsculas
    ("Maria Eduarda", "Maria não pode no sábado", "nome parcial de m1"),    # parte de nome composto
    ("Maria Eduarda", "a eduarda pediu vegetariano", "nome parcial de m1"),
    ("Ana dos Santos", "falou com a santos", "nome parcial de m1"),
])
def test_varredura_pega_nome_sem_diferenciar_caixa_acento_e_partes(nome, texto, achado):
    assert dados_privados_no_estado(_com_texto(texto), _cofre_com(nome)) == [achado]


@pytest.mark.parametrize("nome, texto", [
    ("Maria Eduarda", "Rolê no Maria Fumaça, com trem e doce"),  # lugar da base com o mesmo primeiro nome
    ("Ana dos Santos", "pedido dos amigos de todos"),             # partículas não contam
    ("Ana dos Santos", "banana e pão"),                           # parte dentro de outra palavra
])
def test_varredura_nao_confunde_lugar_da_base_nem_particula_com_nome(nome, texto):
    assert dados_privados_no_estado(_com_texto(texto), _cofre_com(nome)) == []


def test_texto_copiado_da_base_fica_fora_da_varredura_de_nomes():
    estado = {**ESTADO, "documentos": {"l1": {**ESTADO["documentos"]["l1"], "descricao": "Mesas com vista clara."}}}
    assert dados_privados_no_estado(estado, _cofre_com("Clara")) == []
    assert dados_privados_no_estado(_com_texto("a clara não pode"), _cofre_com("Clara")) == ["nome de m1"]


def test_nome_dentro_de_outra_palavra_nao_e_vazamento(cofre):
    estado = {**ESTADO, "historico_erros": ["Leopoldo's Bar vetado por horario"]}
    assert dados_privados_no_estado(estado, cofre) == []


def test_serializacao_recusa_campo_desconhecido_e_forma_errada():
    with pytest.raises(ValidationError):
        serializar_estado({"sala_id": "ROLE-AB12", "campo_novo": 1})
    with pytest.raises(ValidationError):
        serializar_estado({"relatorio_validacao": {"aprovados": [], "vetos": [{"id": "x", "motivo": "chuva"}],
                                                   "contagem": {}, "teto_aplicado": False}})
    with pytest.raises(ValidationError):
        desserializar_estado('{"membros_anonimos": [{"tipos": [], "nome": "Bia"}]}')
