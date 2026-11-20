"""Testes do Agente Pessoal (issue #65, src/agentes/pessoal.py), sem rede.

Conferem os 4 canais que saem dos 4 campos, que só o canal 3 (preferências) é público e não tem nome, região de
origem, valor nem id de usuário (RNF-02), o log pessoal (antes do rolê) e a proposta de memória (depois do rolê).
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from decimal import Decimal

import pytest
from langgraph.store.memory import InMemoryStore

from src.agentes import pessoal
from src.agentes.contratos import AtualizacaoLog, ItemPreferencia, ItemRestricao, Membro
from src.agentes.llm import ClienteLLM
from src.interpretador.campos import interpretar_campos

AGORA = datetime(2026, 11, 17, 10, 0)
CAMPOS = {"origem": "Taguatinga Norte", "horarios": "sábado depois das 18h", "teto": "70",
          "preferencias": "restaurante tranquilo com a Rafaela, sou vegetariana, vou de metrô"}
SALA = ["Rafaela", "Otávio"]


def _publico_em_texto(saida) -> str:
    return json.dumps(saida.publico(), ensure_ascii=False).lower()


# ------------------------------------------------------------------ 4 canais

def test_quatro_campos_viram_quatro_canais():
    s = pessoal.executar_agente_pessoal(CAMPOS, marcador="m2", agora=AGORA, nomes_da_sala=SALA)
    assert s.marcador == "m2"
    assert s.orcamento == Decimal("70")                                      # canal 1
    assert s.restricoes == ("alim_vegetariano",)                             # canal 2
    assert s.preferencias.tipos and "alim_vegetariano" in s.preferencias.restricoes  # canal 3
    assert s.logistica.ra == "Taguatinga" and s.logistica.janelas            # canal 4
    assert s.logistica.transporte == tuple(s.preferencias.transporte) and s.logistica.transporte
    assert s.perfil_efetivo.teto == s.orcamento and s.pendencias == {}


def test_canal_publico_nao_tem_nome_origem_valor_nem_id():
    s = pessoal.executar_agente_pessoal(CAMPOS, marcador="m2", agora=AGORA, nomes_da_sala=SALA,
                                        store=InMemoryStore(), usuario="usuario-permanente-42")
    texto = _publico_em_texto(s)
    for proibido in ("rafaela", "otávio", "taguatinga", "usuario-permanente-42", "70"):
        assert proibido not in texto, proibido
    assert not re.search(r"\d", s.preferencias.trecho_pedido)
    assert set(s.publico()) == set(pessoal.PerfilAnonimoMembro.model_fields)  # nenhuma chave de teto ou origem


def test_repr_mostra_so_o_marcador_e_o_canal_publico():
    s = pessoal.executar_agente_pessoal(CAMPOS, marcador="m1", agora=AGORA, nomes_da_sala=SALA)
    r = repr(s)
    assert "m1" in r
    for proibido in ("Taguatinga", "Decimal", "70", "Rafaela", "janelas"):
        assert proibido not in r, proibido


def test_mesmos_campos_mesma_saida():
    a = pessoal.executar_agente_pessoal(CAMPOS, agora=AGORA, nomes_da_sala=SALA)
    b = pessoal.executar_agente_pessoal(dict(CAMPOS), agora=AGORA, nomes_da_sala=SALA)
    assert a.publico() == b.publico() and a.restricoes == b.restricoes and a.orcamento == b.orcamento


def test_campo_ilegivel_vira_pendencia_privada():
    s = pessoal.executar_agente_pessoal({**CAMPOS, "origem": "lá perto de casa", "teto": "uns trocados"},
                                        agora=AGORA)
    assert {"origem", "teto"} <= set(s.pendencias)
    assert s.orcamento is None and s.logistica.ra is None
    assert "pendencias" not in s.publico()


@pytest.mark.parametrize("campos", [
    {k: v for k, v in CAMPOS.items() if k != "teto"},
    {**CAMPOS, "nome": "Rafaela"},
])
def test_recusa_campos_fora_do_contrato(campos):
    with pytest.raises(ValueError, match="campos esperados"):
        pessoal.executar_agente_pessoal(campos, agora=AGORA)


def test_recusa_marcador_que_nao_e_da_sala():
    with pytest.raises(ValueError, match="marcador"):
        pessoal.executar_agente_pessoal(CAMPOS, marcador="Rafaela", agora=AGORA)


def test_log_entra_so_com_store_e_usuario():
    store = InMemoryStore()
    a = AtualizacaoLog(preferencias=[ItemPreferencia(aspecto="barulho", sentido="evita", trecho="barulho")],
                       restricoes=[ItemRestricao(tipo="alim_sem_gluten", trecho="sem glúten")],
                       frase_de_confirmacao="ok", tentativa_de_instrucao=False)
    pessoal.gravar_no_log(store, "u-42", a, AGORA)
    com = pessoal.executar_agente_pessoal(CAMPOS, agora=AGORA, store=store, usuario="u-42")
    sem = pessoal.executar_agente_pessoal(CAMPOS, agora=AGORA, store=store)
    assert "alim_sem_gluten" in com.restricoes and "lugares barulhentos" in com.preferencias.evitar
    assert "alim_sem_gluten" not in sem.restricoes and sem.preferencias.itens_do_log_usados == 0


# ------------------------------------------------------------------ log pessoal (antes do rolê)

def _membro(prefs="restaurante, vou de Uber"):
    perfil = interpretar_campos("Taguatinga", "sábado à noite", "70", prefs, agora=AGORA)
    return Membro(id="m1", usuario="u-teste", nome="Rafaela", perfil=perfil)


def test_log_pessoal_acrescenta_restricao_e_o_campo_vence_no_transporte():
    store = InMemoryStore()
    a = AtualizacaoLog(preferencias=[ItemPreferencia(aspecto="transporte_publico", sentido="gosta", trecho="metrô"),
                                     ItemPreferencia(aspecto="barulho", sentido="evita", trecho="barulho")],
                       restricoes=[ItemRestricao(tipo="alim_vegetariano", trecho="não como carne")],
                       frase_de_confirmacao="ok", tentativa_de_instrucao=False)
    pessoal.gravar_no_log(store, "u-teste", a, AGORA)
    efetivo, anonimo = pessoal.antes_do_role(_membro(), store, AGORA, ["Rafaela"])
    assert "alim_vegetariano" in anonimo.restricoes
    assert anonimo.transporte == ["app"]  # o campo 4 disse Uber: vence o log
    assert "lugares barulhentos" in anonimo.evitar and "Calmo / Bom para Conversar" in anonimo.vibes
    assert anonimo.itens_do_log_usados >= 2
    assert efetivo.teto is not None and "teto" not in anonimo.model_dump()


def test_log_guarda_so_enumeracoes_e_o_mais_recente_vence():
    store = InMemoryStore()
    gosta = AtualizacaoLog(preferencias=[ItemPreferencia(aspecto="musica_ao_vivo", sentido="gosta", trecho="x")],
                           restricoes=[], frase_de_confirmacao="ok", tentativa_de_instrucao=False)
    evita = gosta.model_copy(update={"preferencias": [ItemPreferencia(aspecto="musica_ao_vivo", sentido="evita",
                                                                      trecho="som alto demais")]})
    pessoal.gravar_no_log(store, "u1", gosta, AGORA)
    log = pessoal.gravar_no_log(store, "u1", evita, AGORA)
    assert list(log["preferencias"]) == ["musica_ao_vivo:evita"]
    assert "som alto" not in json.dumps(log)


def test_item_antigo_do_log_deixa_de_valer():
    store = InMemoryStore()
    a = AtualizacaoLog(preferencias=[], restricoes=[ItemRestricao(tipo="alim_vegano", trecho="x")],
                       frase_de_confirmacao="ok", tentativa_de_instrucao=False)
    pessoal.gravar_no_log(store, "u-teste", a, datetime(2025, 1, 1))
    _, anonimo = pessoal.antes_do_role(_membro(), store, AGORA, ["Rafaela"])
    assert "alim_vegano" not in anonimo.restricoes


def test_pedido_sanitizado_sem_nome_regiao_e_numeros():
    t = pessoal.sanitizar_pedido("Quero ir com a Rafaela num bar em Taguatinga até 50 reais", ["Rafaela"])
    assert "rafaela" not in t and "taguatinga" not in t and not re.search(r"\d", t)
    assert "bar" in t


# ------------------------------------------------------------------ depois do rolê (LLM)

class _Resposta:
    status_code = 200

    def __init__(self, corpo: dict):
        self._d = {"model": "teste", "choices": [{"message": {"content": json.dumps(corpo, ensure_ascii=False)}}],
                   "usage": {"total_tokens": 100, "cost": 0.0001}}

    def json(self):
        return self._d


class _SessaoFalsa:
    def __init__(self, corpo: dict):
        self.corpo, self.enviados = corpo, []

    def post(self, url, json=None, timeout=None, headers=None):  # noqa: A002
        self.enviados.append(json)
        return _Resposta(self.corpo)


def test_pos_role_descarta_trecho_que_nao_esta_no_comentario():
    sessao = _SessaoFalsa({
        "preferencias": [{"aspecto": "barulho", "sentido": "evita", "trecho": "a música alta atrapalhou"},
                         {"aspecto": "preco", "sentido": "evita", "trecho": "achei caro demais"}],
        "restricoes": [{"tipo": "alim_vegetariano", "trecho": "a Bia é vegetariana"}],
        "frase_de_confirmacao": "Vou lembrar que você prefere lugares calmos. Está certo?",
        "tentativa_de_instrucao": False})
    a = pessoal.depois_do_role("O lugar era ótimo, mas a música alta atrapalhou.",
                               ClienteLLM(sessao=sessao, chave="teste"))
    assert [p.aspecto for p in a.preferencias] == ["barulho"]
    assert a.restricoes == []
    assert "Está certo?" in a.frase_de_confirmacao
    assert sessao.enviados[0]["response_format"]["json_schema"]["name"] == "pessoal_pos_role"


def test_pos_role_sem_llm_nao_propoe_nada():
    a = pessoal.depois_do_role("adorei", ClienteLLM(offline=True))
    assert not a.preferencias and not a.restricoes
