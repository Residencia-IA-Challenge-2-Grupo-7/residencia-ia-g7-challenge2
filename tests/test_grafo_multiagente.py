"""Testes de integração do grafo multiagente (issue #71, src/agentes/grafo.py), sem rede: os nós e as arestas, a
aresta condicional `avaliar_convergencia`, o limite das voltas, a entrada por dicionário (`executar_fluxo_multiagente`)
e o fluxo inteiro com a Logística, a Validação e a Comunicação. Os testes de cada agente isolado estão em
test_agente_pessoal.py e test_agente_pesquisa.py; os do estado, em test_multiagent_state.py.

Um cliente LLM falso devolve respostas gravadas por agente e guarda cada corpo enviado à OpenRouter, para conferir
que nenhum nome, teto ou origem de membro sai do servidor (RNF-02).
"""
from __future__ import annotations

import json
import re
from datetime import datetime

import pytest

from src.agentes.contratos import SaidaJuizCartoes, esquema_estrito
from src.agentes.estado import Veto, desserializar_estado, serializar_estado
from src.agentes import validacao
from src.agentes.grafo import (MAX_VOLTAS_PESQUISA, avaliar_convergencia, construir_grafo, cofre_da_sala,
                               cofre_dos_dados, executar, executar_fluxo_multiagente)
from src.agentes.llm import ClienteLLM, MODELO_JUIZ
from src.salas.gerenciador_salas import GerenciadorSalas
from src.state import RepositorioMemoria

AGORA = datetime(2026, 11, 17, 10, 0)
MEMBROS = [
    ("Bia", "Ceilândia Centro", "sábado depois das 18h", "80", "barzinho ou restaurante animado, vou de metrô"),
    ("Caio", "Asa Norte 408", "sábado à noite", "150", "restaurante, vou de Uber"),
    ("Duda", "Samambaia", "sábado depois das 17h", "60", "qualquer coisa, ônibus"),
    ("Leo", "Águas Claras perto da estação", "sábado das 18h às 23h", "100", "café ou restaurante calmo, metrô"),
]
ORIGENS = ("Ceilândia", "Ceilandia", "Samambaia", "Águas Claras", "Aguas Claras", "Asa Norte")


def _dados(conteudo: str, origem: str):
    m = re.search(rf'<dados origem="{origem}" marca="(\w+)">\n(.*)\n</dados marca="\1">', conteudo, re.DOTALL)
    return json.loads(m.group(2)) if m else None


class _Resposta:
    def __init__(self, corpo: dict, modelo: str):
        self.status_code = 200
        self._d = {"model": modelo, "choices": [{"message": {"content": json.dumps(corpo, ensure_ascii=False)}}],
                   "usage": {"total_tokens": 100, "cost": 0.0001}}

    def json(self):
        return self._d


class SessaoFalsa:
    """`respostas[agente]`: dict fixo ou função (corpo da requisição, número da chamada) -> dict."""

    def __init__(self, respostas: dict):
        self.respostas = respostas
        self.corpos: list[dict] = []
        self.contagem: dict[str, int] = {}

    def post(self, url, json=None, timeout=None, headers=None):  # noqa: A002
        self.corpos.append(json)
        agente = json["response_format"]["json_schema"]["name"]
        n = self.contagem[agente] = self.contagem.get(agente, 0) + 1
        r = self.respostas[agente]
        return _Resposta(r(json, n) if callable(r) else r, json["model"])


def _selecionar(corpo, n):
    docs = _dados(corpo["messages"][1]["content"], "documentos_da_base")
    return {"candidatos": [{"id": d["id"], "motivo": f"{d['tipo']} da base.", "trecho": d["nome"]} for d in docs[:10]],
            "observacao": ""}


def _comunicar(primeira_expoe: bool):
    def f(corpo, n):
        fatos = _dados(corpo["messages"][1]["content"], "fatos_dos_cartoes")["cartoes"]
        cartoes = [{"id": c["id"], "titulo": f"Rolê em {c['ra_do_lugar']}", "resumo_acesso": "Todo mundo chega junto.",
                    "por_que_combina": "Combina com o pedido do grupo."} for c in fatos]
        if primeira_expoe and n == 1:
            cartoes[0]["resumo_acesso"] = "Pertinho pra quem vem de Samambaia!"
        return {"cartoes": cartoes}
    return f


def _respostas(primeira_expoe=False):
    return {
        "pesquisa_planejar": {"consultas": [{"texto": "restaurante animado", "tipos_role": ["comer_beber"],
                                             "exigir": [], "ras": []}], "raciocinio": "pedido principal"},
        "pesquisa_selecionar": _selecionar,
        "juiz_pesquisa": {"afirmacoes": []},
        "comunicacao": _comunicar(primeira_expoe),
        "juiz_comunicacao": {"afirmacoes": [], "exposicoes": []},
        "pessoal_pos_role": {"preferencias": [], "restricoes": [], "frase_de_confirmacao": "ok",
                             "tentativa_de_instrucao": False},
    }


@pytest.fixture
def sala_e_lugares():
    g = GerenciadorSalas(RepositorioMemoria(), relogio=lambda: AGORA)
    sala, _ = g.criar_sala("Aniversário da Bia", "Bia", True)
    for nome, origem, horarios, teto, prefs in MEMBROS:
        p, token = g.entrar(sala.codigo, nome, True, origem, horarios, teto, prefs)
        g.confirmar(sala.codigo, p.id, token)
    return g.repo.obter(sala.codigo), list(g.lugares)


def _mensagens_de(final, agente):
    return [m for m in final["mensagens"] if m["de"] == agente]


# ------------------------------------------------------------------ grafo

def test_grafo_sem_llm_chega_aos_cartoes_com_todos_os_agentes(sala_e_lugares):
    sala, lugares = sala_e_lugares
    final = executar(cofre_da_sala(sala, lugares, AGORA), ClienteLLM(offline=True))
    cartoes = final["resultado_final_cartoes"]
    assert 3 <= len(cartoes) <= 4
    assert len({c["lugar_id"] for c in cartoes}) == len(cartoes)
    for agente in ("Agentes Pessoais", "Pesquisa", "Logística", "Validação", "Comunicação", "Orquestrador"):
        assert _mensagens_de(final, agente), agente
    assert all(c["texto_por"] == "reserva_por_regras" for c in cartoes)
    assert all(not re.search(r"\d", c["titulo"] + c["resumo_acesso"]) for c in cartoes)


def test_volta_da_validacao_para_a_pesquisa_tem_limite(sala_e_lugares):
    sala, lugares = sala_e_lugares
    final = executar(cofre_da_sala(sala, lugares, AGORA), ClienteLLM(offline=True))
    pedidos = [m for m in _mensagens_de(final, "Validação") if m["para"] == "Pesquisa"]
    assert 1 <= len(_mensagens_de(final, "Pesquisa")) == len(pedidos) + 1 <= MAX_VOLTAS_PESQUISA + 1


@pytest.mark.parametrize("validados, iteracao, destino", [
    (0, 0, "no_pesquisa"), (2, 0, "no_pesquisa"), (2, 1, "no_pesquisa"),
    (2, 2, "no_comunicacao"),          # sem voltas: segue com o que passou
    (3, 0, "no_comunicacao"), (4, 1, "no_comunicacao"),
])
def test_avaliar_convergencia(validados, iteracao, destino):
    estado = {"candidatos_validados": [{"id": f"l{i}"} for i in range(validados)], "iteracao_pesquisa": iteracao}
    assert avaliar_convergencia(estado) == destino
    assert MAX_VOLTAS_PESQUISA == 2 and validacao.MINIMO_CARTOES == 3


def test_nos_e_arestas_da_issue(sala_e_lugares):
    sala, lugares = sala_e_lugares
    g = construir_grafo(cofre_da_sala(sala, lugares, AGORA), ClienteLLM(offline=True)).get_graph()
    nos = set(g.nodes) - {"__start__", "__end__"}
    assert {"no_pessoal", "no_pesquisa", "no_logistica", "no_validacao", "no_comunicacao"} <= nos
    arestas = {(a.source, a.target, a.conditional) for a in g.edges}
    for origem, destino in (("no_pessoal", "no_consolidar_grupo"), ("no_pesquisa", "no_logistica"),
                            ("no_logistica", "no_validacao"), ("no_comunicacao", "no_validacao_textos"),
                            ("no_finalizar", "__end__")):
        assert (origem, destino, False) in arestas, (origem, destino)
    assert {("no_validacao", "no_pesquisa", True), ("no_validacao", "no_comunicacao", True),
            ("no_validacao", "no_finalizar", True)} <= arestas


def test_validacao_que_nunca_aprova_para_depois_de_duas_voltas(sala_e_lugares, monkeypatch):
    original = validacao.validar_candidatos_regras

    def nada_passa(candidatos, **kw):
        r = original(candidatos, **kw)
        return r.model_copy(update={"aprovados": [], "vetos": r.vetos + [Veto(id=i, motivo="horario")
                                                                         for i in r.aprovados]})

    monkeypatch.setattr(validacao, "validar_candidatos_regras", nada_passa)
    sala, lugares = sala_e_lugares
    final = executar(cofre_da_sala(sala, lugares, AGORA), ClienteLLM(offline=True))
    assert final["iteracao_pesquisa"] == MAX_VOLTAS_PESQUISA
    assert len(_mensagens_de(final, "Pesquisa")) == MAX_VOLTAS_PESQUISA + 1
    assert final["candidatos_validados"] == [] and final["resultado_final_cartoes"] == []
    assert final["mensagens"][-1]["de"] == "Orquestrador"
    assert not _mensagens_de(final, "Comunicação"), "sem aprovados, a Comunicação não escreve"
    assert not any("Autorizado" in m["texto"] or "aprovados:" in m["texto"] for m in final["mensagens"])


# ------------------------------------------------------------------ entrada por dicionário

SALA_DICT = {"codigo": "ROLE-TESTE", "agora": "2026-11-17T10:00", "membros": [
    {"nome": nome, "origem": origem, "horarios": horarios, "teto": teto, "preferencias": prefs}
    for nome, origem, horarios, teto, prefs in MEMBROS]}


def test_executar_fluxo_multiagente_com_dicionario():
    final = executar_fluxo_multiagente(SALA_DICT, cliente=ClienteLLM(offline=True))
    assert final["sala_id"] == "ROLE-TESTE"
    assert 3 <= len(final["resultado_final_cartoes"]) <= 4
    assert 0 <= final["iteracao_pesquisa"] <= MAX_VOLTAS_PESQUISA
    pedidos = [m for m in _mensagens_de(final, "Validação") if m["para"] == "Pesquisa"]
    assert len(pedidos) == final["iteracao_pesquisa"]
    publico = serializar_estado(final)  # recusaria chave do cofre (teto, origem, usuário...)
    for nome, *_ in MEMBROS:
        assert not re.search(rf"\b{nome}\b", publico), nome


def test_cofre_dos_dados_interpreta_os_4_campos_e_guarda_fora_do_estado():
    cofre = cofre_dos_dados(SALA_DICT)
    assert list(cofre.membros) == ["m1", "m2", "m3", "m4"]
    assert cofre.membros["m3"].perfil.ra == "Samambaia" and cofre.membros["m2"].perfil.teto == 150
    assert cofre.janelas and len(cofre.lugares) == 93


@pytest.mark.parametrize("estrago, mensagem", [
    ({"membros": SALA_DICT["membros"][:1]}, "pelo menos 2"),
    ({"membros": [{k: v for k, v in m.items() if k != "teto"} for m in SALA_DICT["membros"]]}, "faltam"),
    ({"membros": [{**m, "cpf": "000"} for m in SALA_DICT["membros"]]}, "sobram"),
    ({"orcamento_total": 300}, "chaves desconhecidas"),
])
def test_dados_sala_fora_do_contrato(estrago, mensagem):
    with pytest.raises(ValueError, match=mensagem):
        executar_fluxo_multiagente({**SALA_DICT, **estrago}, cliente=ClienteLLM(offline=True))


def test_sem_horario_em_comum_termina_sem_cartoes():
    dados = {**SALA_DICT, "membros": [
        {"nome": "Ana", "origem": "Gama", "horarios": "segunda de manhã", "teto": "50", "preferencias": "café"},
        {"nome": "Rui", "origem": "Guará", "horarios": "sábado à noite", "teto": "50", "preferencias": "bar"}]}
    final = executar_fluxo_multiagente(dados, cliente=ClienteLLM(offline=True))
    assert final["resultado_final_cartoes"] == []
    assert any("horário" in e for e in final["historico_erros"])
    assert not _mensagens_de(final, "Pesquisa")


def test_grafo_preenche_o_estado_compartilhado_e_o_estado_serializa(sala_e_lugares):
    """Issue #64: os campos do MultiAgentState saem do grafo coerentes entre si e sem dado do cofre."""
    sala, lugares = sala_e_lugares
    cofre = cofre_da_sala(sala, lugares, AGORA)
    estado = executar(cofre, ClienteLLM(offline=True))
    assert estado["sala_id"] == sala.codigo
    assert len(estado["membros_anonimos"]) == 4          # um por Agente Pessoal, somados pelo reducer
    assert estado["preferencias_grupo"]["tamanho"] == 4
    assert 0 <= estado["iteracao_pesquisa"] <= MAX_VOLTAS_PESQUISA
    aprovados = estado["relatorio_validacao"]["aprovados"]
    assert [c["id"] for c in estado["candidatos_validados"]] == aprovados
    assert [c["lugar_id"] for c in estado["resultado_final_cartoes"]] == aprovados
    for v in estado["relatorio_validacao"]["vetos"]:     # os vetos da última volta estão no histórico
        assert any(v["id"] in e and v["motivo"] in e for e in estado["historico_erros"])
    texto = serializar_estado(estado, cofre)              # recusaria nome, usuário, teto ou origem
    assert desserializar_estado(texto) == json.loads(texto)


def test_nenhum_nome_teto_ou_origem_vai_para_o_llm(sala_e_lugares):
    sala, lugares = sala_e_lugares
    sessao = SessaoFalsa(_respostas())
    cliente = ClienteLLM(sessao=sessao, chave="teste")
    final = executar(cofre_da_sala(sala, lugares, AGORA), cliente, juiz_parecer=True)
    assert final["resultado_final_cartoes"]
    agentes = {c["response_format"]["json_schema"]["name"] for c in sessao.corpos}
    assert {"pesquisa_planejar", "pesquisa_selecionar", "juiz_pesquisa", "comunicacao", "juiz_comunicacao"} <= agentes
    for corpo in sessao.corpos:
        # só o que sai da sala: o prompt de sistema tem exemplos com personas fictícias ("a Bia que sai do Guará")
        texto = json.dumps([m for m in corpo["messages"] if m["role"] != "system"], ensure_ascii=False)
        for nome, *_ in MEMBROS:
            assert not re.search(rf"\b{nome}\b", texto), nome
        assert '"teto' not in texto
        grupo = _dados(corpo["messages"][1]["content"], "perfil_anonimo_do_grupo")
        if grupo:
            assert not any(o in json.dumps(grupo, ensure_ascii=False) for o in ORIGENS)
            assert not re.search(r"\b(80|150|60|100)\b", " ".join(grupo["trechos_pedido"]))


def test_juiz_usa_o_glm_sem_desligar_o_raciocinio_e_os_agentes_o_deepseek(sala_e_lugares):
    sala, lugares = sala_e_lugares
    sessao = SessaoFalsa(_respostas())
    executar(cofre_da_sala(sala, lugares, AGORA), ClienteLLM(sessao=sessao, chave="teste"), juiz_parecer=True)
    juizes = 0
    for corpo in sessao.corpos:
        if corpo["response_format"]["json_schema"]["name"].startswith("juiz"):
            juizes += 1
            assert corpo["model"] == MODELO_JUIZ and "reasoning" not in corpo
        else:
            assert corpo["model"].startswith("deepseek/") and corpo["reasoning"] == {"enabled": False}
        assert corpo["provider"]["zdr"] is True and corpo["temperature"] == 0
    assert juizes >= 2  # 1ª passagem (parecer) e 2ª (cartões)


def test_juiz_dos_cartoes_reprova_e_a_comunicacao_reescreve(sala_e_lugares):
    """A 2ª passagem do juiz (#72) acha uma exposição que a varredura em código não pega; o cartão volta para a
    Comunicação uma vez."""
    def juiz_cartoes(corpo, n):
        if n == 1:
            return {"afirmacoes": [], "exposicoes": [{"cartao": "A", "trecho": "galera do bairro",
                                                     "o_que_expoe": "origem"}]}
        return {"afirmacoes": [], "exposicoes": []}
    sala, lugares = sala_e_lugares
    sessao = SessaoFalsa({**_respostas(), "juiz_comunicacao": juiz_cartoes})
    final = executar(cofre_da_sala(sala, lugares, AGORA), ClienteLLM(sessao=sessao, chave="teste"))
    assert final["reescritas"] == 1
    assert any("vazamento_origem" in e for e in final["historico_erros"])
    assert final["resultado_final_cartoes"]


def test_cartao_que_expoe_origem_volta_para_a_comunicacao(sala_e_lugares):
    sala, lugares = sala_e_lugares
    sessao = SessaoFalsa(_respostas(primeira_expoe=True))
    final = executar(cofre_da_sala(sala, lugares, AGORA), ClienteLLM(sessao=sessao, chave="teste"))
    assert sessao.contagem["comunicacao"] == 2
    reprovacao = [m for m in _mensagens_de(final, "Validação") if m["texto"].startswith("Cartões reprovados")]
    assert reprovacao and "origem" in reprovacao[0]["texto"]
    assert all("Samambaia" not in c["resumo_acesso"] for c in final["resultado_final_cartoes"])
    assert final["resultado_final_cartoes"][0]["texto_por"] == "agente_comunicacao"


def test_llm_fora_do_ar_cai_nas_reservas_sem_parar_o_grafo(sala_e_lugares):
    class Quebrada:
        def post(self, *a, **k):
            raise __import__("requests").ConnectionError("fora do ar")
    sala, lugares = sala_e_lugares
    final = executar(cofre_da_sala(sala, lugares, AGORA), ClienteLLM(sessao=Quebrada(), chave="teste"))
    assert 3 <= len(final["resultado_final_cartoes"]) <= 4


def test_diagrama_sai_do_grafo(sala_e_lugares):
    sala, lugares = sala_e_lugares
    mermaid = construir_grafo(cofre_da_sala(sala, lugares, AGORA), ClienteLLM(offline=True)).get_graph().draw_mermaid()
    for no in ("no_pessoal", "no_pesquisa", "no_logistica", "no_validacao", "no_comunicacao", "no_validacao_textos"):
        assert no in mermaid


def test_lugar_com_trajeto_acima_de_120_min_e_vetado(sala_e_lugares):
    sala, lugares = sala_e_lugares
    final = executar(cofre_da_sala(sala, lugares, AGORA), ClienteLLM(offline=True))
    assert all((c["tempo_maximo_chegada_min"] or 0) <= 120 for c in final["resultado_final_cartoes"])


# ------------------------------------------------------------------ contratos

def test_esquema_estrito_sem_ref_e_fechado():
    esq = esquema_estrito(SaidaJuizCartoes)
    texto = json.dumps(esq)
    assert "$ref" not in texto and "$defs" not in texto
    def objetos(no):
        if isinstance(no, dict):
            if no.get("type") == "object":
                yield no
            for v in no.values():
                yield from objetos(v)
        elif isinstance(no, list):
            for v in no:
                yield from objetos(v)
    for o in objetos(esq):
        assert o["additionalProperties"] is False and set(o["required"]) == set(o["properties"])


# ------------------------------------------------------------------ os dois cenários da #66 pelo grafo inteiro

from src.agentes.cenarios import carregar_cenario, para_entrada_do_grafo  # noqa: E402
from src.agentes.validacao import selecionar_cartoes  # noqa: E402


def test_cenario_padrao_da_66_termina_sem_cartoes_e_sem_passar_pela_comunicacao():
    """Vegetariano com teto de R$ 40 e pontas opostas do DF: nada passa. O grafo faz as 2 voltas, vai direto para
    o fim e avisa o grupo, sem 'autorizado' nem 'cartões aprovados' (#71)."""
    final = executar_fluxo_multiagente(para_entrada_do_grafo(carregar_cenario("cenario_padrao_4_amigos")),
                                       cliente=ClienteLLM(offline=True))
    assert final["resultado_final_cartoes"] == []
    assert final["iteracao_pesquisa"] == MAX_VOLTAS_PESQUISA
    assert not _mensagens_de(final, "Comunicação")
    assert "sem cartões" in final["mensagens"][-1]["texto"]
    assert not any("Autorizado" in m["texto"] or "cartões aprovados" in m["texto"] for m in final["mensagens"])


def test_cenario_de_controle_da_66_so_tem_cartao_viavel():
    cenario = carregar_cenario("cenario_controle_viavel")
    final = executar_fluxo_multiagente(para_entrada_do_grafo(cenario), cliente=ClienteLLM(offline=True))
    esperados = cenario["resultados_esperados"]
    viaveis = {l["id"] for l in esperados["lugares_viaveis_esperados"]}
    nunca = {l["id"] for l in esperados["nunca_sugerir"]}
    cartoes = final["resultado_final_cartoes"]
    assert cartoes, "o controle tem lugar viável"
    assert {c["lugar_id"] for c in cartoes} <= viaveis
    assert not {c["lugar_id"] for c in cartoes} & nunca
    if len(cartoes) < 3:  # a Pesquisa ainda não acha os 5 viáveis (pendência registrada na Seção 8)
        assert "menos de 3" in final["mensagens"][-1]["texto"]


def test_selecionar_cartoes_tira_nome_repetido_e_limita_duas_por_ra():
    def r(i, nome, ra):
        return {"id": i, "nome": nome, "ra_do_lugar": ra}
    ranking = [r("a", "Espaguete", "Plano Piloto"), r("b", "Espaguete", "Plano Piloto"), r("c", "X", "Plano Piloto"),
               r("d", "Y", "Plano Piloto"), r("e", "Z", "Guará"), r("f", "W", "Gama"), r("g", "V", "Lago Sul")]
    escolhidos = [c["id"] for c in selecionar_cartoes(ranking, "abcdefg")]
    assert escolhidos == ["a", "c", "e", "f"]
    assert [c["id"] for c in selecionar_cartoes(ranking, {"c", "g"})] == ["c", "g"]


# ------------------------------------------------------------------ revisão do #80 (Duda)

def test_reescrita_troca_so_o_cartao_reprovado_e_guarda_o_texto_do_llm(sala_e_lugares):
    """O LLM devolve só o cartão corrigido, como o prompt pede: ele entra no lugar do reprovado, os outros ficam
    como estavam e todos continuam marcados como escritos pela Comunicação."""
    def comunicar(corpo, n):
        fatos = _dados(corpo["messages"][1]["content"], "fatos_dos_cartoes")["cartoes"]
        cartoes = [{"id": c["id"], "titulo": f"Rolê {c['id']}", "resumo_acesso": "Todo mundo chega junto.",
                    "por_que_combina": "Combina com o pedido do grupo."} for c in fatos]
        if n == 1:
            cartoes[0]["resumo_acesso"] = "Pertinho pra quem vem de Samambaia!"
            return {"cartoes": cartoes}
        assert [c["id"] for c in fatos] == ["A"], "na reescrita só o reprovado vai para o LLM"
        return {"cartoes": [{**cartoes[0], "titulo": "Rolê A reescrito"}]}
    respostas = {**_respostas(), "comunicacao": comunicar}
    sala, lugares = sala_e_lugares
    final = executar(cofre_da_sala(sala, lugares, AGORA), ClienteLLM(sessao=SessaoFalsa(respostas), chave="teste"))
    cartoes = final["resultado_final_cartoes"]
    assert cartoes[0]["titulo"] == "Rolê A reescrito"
    assert [c["titulo"] for c in cartoes[1:]] == [f"Rolê {c['id']}" for c in cartoes[1:]]
    assert {c["texto_por"] for c in cartoes} == {"agente_comunicacao"}


def test_cartao_final_valida_no_esquema_da_comunicacao():
    from src.agentes.comunicacao import CartaoSugestaoValidado
    final = executar_fluxo_multiagente(SALA_DICT, cliente=ClienteLLM(offline=True))
    assert final["resultado_final_cartoes"]
    for c in final["resultado_final_cartoes"]:
        CartaoSugestaoValidado.model_validate(c)


def test_varredura_pega_parte_do_nome_e_nao_reprova_palavra_comum():
    from src.agentes.validacao import varrer_cartao
    dados = json.loads(json.dumps(SALA_DICT))
    dados["membros"][0]["nome"] = "Maria Eduarda"      # Ceilândia; o Caio sai da Asa Norte (Plano Piloto)
    cofre = cofre_dos_dados(dados)
    cofre.perfis_efetivos = {m: mb.perfil for m, mb in cofre.membros.items()}
    lugar = "Águas Claras"
    assert varrer_cartao("Ótimo para a Maria curtir.", cofre, lugar) == ["nome_de_membro"]
    assert varrer_cartao("Um excelente plano de sábado para reunir a turma.", cofre, lugar) == []
    assert varrer_cartao("Uma gama de pratos num recanto tranquilo.", cofre, lugar) == []
    assert varrer_cartao("Perfeito pra galera do Plano Piloto.", cofre, lugar) == ["origem"]
    assert varrer_cartao("Pertinho de Ceilândia.", cofre, lugar) == ["origem"]


def test_varredura_ignora_nome_de_lugar_igual_ao_de_membro():
    from src.agentes.validacao import varrer_cartao
    dados = json.loads(json.dumps(SALA_DICT))
    dados["membros"][0]["nome"] = "Chico"
    lugar = {"id": "x", "nome": "Chico Padeiro", "tipo_de_role": "Cafeteria / Doceria"}
    cofre = cofre_dos_dados(dados, lugares=[lugar])
    cofre.perfis_efetivos = {m: mb.perfil for m, mb in cofre.membros.items()}
    assert varrer_cartao("Chico Padeiro: pão quentinho.", cofre, "Águas Claras") == []
    assert varrer_cartao("O Chico vai adorar.", cofre, "Águas Claras") == ["nome_de_membro"]


def test_tentativa_sem_resposta_fica_registrada_com_o_tempo_gasto():
    """Visto no demo da #74: o juiz estourou o tempo na 1ª tentativa e respondeu na 2ª; sem registrar a falha, o
    demo mostrava 20 s de juiz num nó que levou 58 s."""
    import requests

    class Sessao:
        def __init__(self):
            self.n = 0

        def post(self, url, json=None, timeout=None, headers=None):  # noqa: A002
            self.n += 1
            if self.n == 1:
                raise requests.Timeout("tempo esgotado")
            return _Resposta({"ok": True}, json["model"])

    cliente = ClienteLLM(sessao=Sessao(), chave="teste")
    assert cliente.json("juiz_comunicacao", "sistema", "usuario", {"type": "object"}, modelo=MODELO_JUIZ) == {"ok": True}
    assert [c.falhou for c in cliente.chamadas] == ["Timeout", ""]
