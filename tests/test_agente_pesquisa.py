"""Testes do agente de Pesquisa (issue #70, src/agentes/pesquisa.py e ferramentas.py), sem rede.

Conferem a ferramenta de busca sobre a base oficial, que o LLM só cita ids e trechos dos documentos que a busca
trouxe (RNF-03), a volta da Validação só com contagens, a entrada validada (RNF-02) e a reserva por regras sem LLM.
"""
from __future__ import annotations

import json
import re

import pytest
import requests
from pydantic import ValidationError

from src.agentes import ferramentas
from src.agentes.contratos import Consulta
from src.agentes.llm import MODELO_AGENTES, ClienteLLM
from src.agentes.pesquisa import (CATEGORIAS, MAX_CANDIDATOS, _consultas_por_regras, buscar_lugares_rag,
                                  executar_agente_pesquisa)
from src.salas import integracoes as integ

LUGARES = list(integ.carregar_lugares())
POR_ID = {l["id"]: l for l in LUGARES}
GRUPO = {"tamanho": 4, "tipos": ["Cafeteria / Doceria", "Restaurante / Gastronomia"],
         "tipos_pedidos": {"Cafeteria / Doceria": "2 de 4"}, "vibes": ["Calmo / Bom para Conversar"],
         "evitar": ["lugares barulhentos"], "restricoes": ["alim_vegetariano"],
         "trechos_pedido": ["cafe tranquilo para conversar"], "janela": "sábado, 18h às 21h (4 de 4)"}


class _Resposta:
    status_code = 200

    def __init__(self, corpo: dict):
        self._d = {"model": MODELO_AGENTES, "choices": [{"message": {"content": json.dumps(corpo, ensure_ascii=False)}}],
                   "usage": {"total_tokens": 100, "cost": 0.0001}}

    def json(self):
        return self._d


class _SessaoFalsa:
    """Responde `pesquisa_planejar` e `pesquisa_selecionar`; a seleção recebe os documentos enviados."""

    def __init__(self, selecionar):
        self.selecionar, self.enviados = selecionar, []

    def post(self, url, json=None, timeout=None, headers=None):  # noqa: A002
        self.enviados.append(json)
        etapa = json["response_format"]["json_schema"]["name"]
        if etapa == "pesquisa_planejar":
            return _Resposta({"consultas": [{"texto": "café calmo para conversar", "tipos_role": ["comer_beber"],
                                             "exigir": ["alim_vegetariano"], "ras": ["Atlântida"]}],
                              "raciocinio": "pedido principal"})
        return _Resposta(self.selecionar(_documentos(json)))


def _documentos(corpo: dict) -> list[dict]:
    m = re.search(r'<dados origem="documentos_da_base" marca="(\w+)">\n(.*)\n</dados marca="\1">',
                  corpo["messages"][1]["content"], re.DOTALL)
    return json.loads(m.group(2))


def _honesto(docs):
    return {"candidatos": [{"id": d["id"], "motivo": "Combina com o pedido.", "trecho": d["nome"]} for d in docs[:9]],
            "observacao": ""}


# ------------------------------------------------------------------ ferramenta

def test_ferramenta_busca_na_base_oficial_e_filtra_por_categoria():
    itens = buscar_lugares_rag("café calmo para conversar", ["comer_beber"], k=6)
    assert len(itens) == 6 and all(i["id"] in POR_ID for i in itens)
    assert {i["tipo"] for i in itens} <= ferramentas.TIPOS_DA_BASE["comer_beber"]
    assert [i["pontuacao"] for i in itens] == sorted((i["pontuacao"] for i in itens), reverse=True)


def test_ferramenta_entrega_so_o_que_um_llm_pode_ler():
    item = buscar_lugares_rag("bar animado", k=1)[0]
    assert set(item) == {"id", "nome", "tipo", "regiao_do_lugar", "vibes", "descricao", "pontuacao"}


def test_ferramenta_aceita_tipo_da_base_e_recusa_categoria_desconhecida():
    assert buscar_lugares_rag("parque", ["Ao Ar Livre / Parque"], k=3) == buscar_lugares_rag("parque", ["ar_livre_gratuito"], k=3)
    with pytest.raises(ValueError, match="categoria desconhecida"):
        buscar_lugares_rag("bar", ["balada"])
    assert CATEGORIAS == {"comer_beber", "ar_livre_gratuito", "local_evento"}


def test_conferir_trecho_e_busca_por_tipo():
    l = LUGARES[0]
    assert ferramentas.conferir_trecho(l["nome"], l)
    assert not ferramentas.conferir_trecho("trecho que não existe em lugar nenhum xyz", l)
    itens, meta = ferramentas.buscar(Consulta(texto="café doce bolo", tipos_role=["comer_beber"], exigir=[], ras=[]),
                                     LUGARES, k=5)
    assert len(itens) == 5 and meta["busca"] == "lexica"
    assert all("custo_medio_rs" not in i and "horario_funcionamento" not in i for i in itens)


# ------------------------------------------------------------------ agente

def test_saida_tem_fonte_e_trecho_literal_conferidos():
    sessao = _SessaoFalsa(_honesto)
    cands = executar_agente_pesquisa(GRUPO, cliente=ClienteLLM(sessao=sessao, chave="teste"), lugares=LUGARES)
    assert 8 <= len(cands) <= MAX_CANDIDATOS
    for c in cands:
        assert set(c) == {"fonte_id", "nome", "tipo", "motivo", "trecho_citado"}
        assert ferramentas.conferir_trecho(c["trecho_citado"], POR_ID[c["fonte_id"]])
    assert [b["model"] for b in sessao.enviados] == [MODELO_AGENTES, MODELO_AGENTES]  # DeepSeek V4.1 Flash
    assert all(b["response_format"]["json_schema"]["strict"] for b in sessao.enviados)


def test_descarta_trecho_inventado_id_fora_da_busca_e_repetido():
    def mentiroso(docs):
        bons = [{"id": d["id"], "motivo": "Combina.", "trecho": d["nome"]} for d in docs[:9]]
        return {"observacao": "", "candidatos": bons[:6] + [
            {"id": docs[6]["id"], "motivo": "Tem rodízio vegano.", "trecho": "rodízio vegano liberado a noite toda"},
            {"id": "tiktok_que_nao_existe", "motivo": "Ótimo.", "trecho": "ótimo"},
            {"id": docs[0]["id"], "motivo": "De novo.", "trecho": docs[0]["nome"]},
        ] + bons[7:9]}
    cands = executar_agente_pesquisa(GRUPO, cliente=ClienteLLM(sessao=_SessaoFalsa(mentiroso), chave="t"),
                                     lugares=LUGARES)
    ids = [c["fonte_id"] for c in cands]
    assert len(ids) == len(set(ids)) == 8
    assert "tiktok_que_nao_existe" not in ids
    assert all("rodízio vegano" not in c["trecho_citado"] for c in cands)


def test_volta_da_validacao_leva_so_contagens_e_exclui_os_ja_julgados():
    sessao = _SessaoFalsa(_honesto)
    excluir = {d["id"] for d in buscar_lugares_rag("café calmo para conversar", ["comer_beber"], k=5)}
    feedback = {"faltam": 2, "vetos": {"orcamento": 4, "horario": 3}, "ja_vistos": 10}
    cands = executar_agente_pesquisa(GRUPO, feedback, cliente=ClienteLLM(sessao=sessao, chave="t"),
                                     lugares=LUGARES, excluir=excluir)
    assert not excluir & {c["fonte_id"] for c in cands}
    planejar = sessao.enviados[0]["messages"][1]["content"]
    assert '"vetos": {"orcamento": 4, "horario": 3}' in planejar and '"faltam": 2' in planejar


@pytest.mark.parametrize("feedback", [
    {"faltam": 2, "vetos": {"orcamento": 1}, "ja_vistos": 3, "nota": "o Caio ganha pouco"},  # texto livre
    {"faltam": "dois", "vetos": {}, "ja_vistos": 3},
])
def test_feedback_fora_do_contrato_nao_chega_ao_llm(feedback):
    sessao = _SessaoFalsa(_honesto)
    with pytest.raises(ValidationError):
        executar_agente_pesquisa(GRUPO, feedback, cliente=ClienteLLM(sessao=sessao, chave="t"), lugares=LUGARES)
    assert sessao.enviados == []


def test_perfil_com_dado_privado_nao_chega_ao_llm():
    sessao = _SessaoFalsa(_honesto)
    with pytest.raises(ValidationError):
        executar_agente_pesquisa({**GRUPO, "teto": 80}, cliente=ClienteLLM(sessao=sessao, chave="t"), lugares=LUGARES)
    assert sessao.enviados == []


def test_perfil_parcial_completa_com_vazios():
    cands = executar_agente_pesquisa({"tipos": ["Bar / Boteco / Pub"]}, cliente=ClienteLLM(offline=True),
                                     lugares=LUGARES)
    assert len(cands) >= 3


# ------------------------------------------------------------------ reserva por regras

def test_sem_llm_a_reserva_entrega_candidatos_da_busca():
    cands = executar_agente_pesquisa(GRUPO, cliente=ClienteLLM(offline=True), lugares=LUGARES)
    assert 3 <= len(cands) <= MAX_CANDIDATOS
    assert all(c["trecho_citado"] == POR_ID[c["fonte_id"]]["nome"] for c in cands)
    assert all(not re.search(r"\d", c["motivo"]) for c in cands)


def test_reserva_usa_os_vetos_para_ampliar_a_busca():
    grupo = {**GRUPO, "restricoes": []}
    so_pedido = _consultas_por_regras(grupo, None)
    com_vetos = _consultas_por_regras(grupo, {"faltam": 2, "vetos": {"orcamento": 3, "horario": 2}, "ja_vistos": 9})
    assert len(so_pedido) == 1 and len(com_vetos) == 3
    assert "barato" in com_vetos[1].texto and "aberto" in com_vetos[2].texto


def test_llm_fora_do_ar_cai_na_reserva():
    class Quebrada:
        def post(self, *a, **k):
            raise requests.ConnectionError("sem rede")
    cands = executar_agente_pesquisa(GRUPO, cliente=ClienteLLM(sessao=Quebrada(), chave="t"), lugares=LUGARES)
    assert len(cands) >= 3
