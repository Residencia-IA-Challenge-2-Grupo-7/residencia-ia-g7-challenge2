"""Testes do interpretador (ADR 0007) sem LLM: o LLM é trocado por um falso que devolve o JSON do esquema."""
from datetime import date, datetime
from decimal import Decimal

import pytest

from interpretador.avaliar import comparar, comparavel, limite_inferior
from interpretador.esquema import schema_llm
from interpretador.interpretar import interpretar, reais
from interpretador.llm import ErroLLM, Meta
from interpretador.lugares import casar
from interpretador.numeros import extenso_para_digitos, trecho_na_mensagem, valor_em_reais
from interpretador.pseudonimo import Pseudonimos
from interpretador.tempo import ErroTempo, resolver_dias, resolver_horario, resolver_janelas

QUI = datetime(2026, 11, 5, 10, 0)  # quinta-feira
SALA = ["Rafaela", "Cadu", "Bia", "Márcio", "Caio", "Ana"]


def it(tipo, **k):
    base = {"tipo": tipo, "trecho": "", "janelas": [], "valor": None, "pagador": None, "descricao": None,
            "convidados": [], "tipo_role": None, "lugares": [], "exigir": [], "texto_busca": None}
    return base | k


def jan(dias, periodo=None, apos=None, ate=None, disponivel=True, proxima_semana=False):
    return {"dias": dias, "proxima_semana": proxima_semana, "periodo": periodo, "apos": apos, "ate": ate,
            "disponivel": disponivel}


class LLMFalso:
    def __init__(self, *intencoes, falhar=False):
        self.saida = {"intencoes": list(intencoes)}
        self.falhar = falhar
        self.recebido = None

    def interpretar(self, sistema, usuario):
        self.recebido = usuario
        if self.falhar:
            raise ErroLLM("fora do ar")
        return self.saida, Meta("falso", None, 0.0, 10, 10, 0.0)


def rodar(msg, *intencoes, contexto="privado", autor="Rafaela", origem="texto"):
    llm = LLMFalso(*intencoes)
    r = interpretar(msg, contexto=contexto, autor=autor, membros=SALA, agora=QUI, origem=origem, llm=llm)
    return r, llm


# ---------- datas e horários (código, não LLM) ----------

def test_dias_relativos_a_quinta():
    h = QUI.date()
    assert resolver_dias(["sex"], h) == [date(2026, 11, 6)]
    assert resolver_dias(["qui"], h) == [h]  # o próprio dia conta
    assert resolver_dias(["sab"], h, proxima_semana=True) == [date(2026, 11, 14)]
    assert resolver_dias(["fim_de_semana"], h) == [date(2026, 11, 7), date(2026, 11, 8)]
    assert resolver_dias(["semana_que_vem"], h) == [date(2026, 11, d) for d in range(9, 16)]
    assert resolver_dias(["amanha", "depois_de_amanha"], h) == [date(2026, 11, 6), date(2026, 11, 7)]
    assert resolver_dias(["14"], h) == [date(2026, 11, 14)]
    assert resolver_dias(["3"], h) == [date(2026, 12, 3)]       # dia 3 já passou neste mês
    assert resolver_dias(["02/01"], h) == [date(2027, 1, 2)]
    with pytest.raises(ErroTempo):
        resolver_dias(["sextou"], h)


def test_convencoes_de_horario():
    assert resolver_horario("tarde", None, None)[:2] == (datetime(1, 1, 1, 13).time(), datetime(1, 1, 1, 18).time())
    ini, fim, seguinte = resolver_horario(None, "19:00", None)
    assert (ini.hour, fim.hour, seguinte) == (19, 0, True)          # depois das 19h = 19h–24h
    ini, fim, _ = resolver_horario(None, None, "16:00")
    assert (ini.hour, fim.hour) == (8, 16)                          # até as 16h = 8h–16h
    ini, fim, _ = resolver_horario("noite", None, "23:00")
    assert (ini.hour, fim.hour) == (19, 23)
    _, fim, seguinte = resolver_horario("noite", None, "02:00")
    assert (fim.hour, seguinte) == (2, True)                        # passa da meia-noite
    with pytest.raises(ErroTempo):
        resolver_horario(None, "22:00", "20:00")
    with pytest.raises(ErroTempo):
        resolver_horario(None, "25:00", None)


def test_falta_dia_vira_pergunta():
    with pytest.raises(ErroTempo) as e:
        resolver_janelas([], "tarde", None, None, QUI)
    assert e.value.motivo == "falta_dia"
    j = resolver_janelas(["sex"], None, "19:00", None, QUI)[0]
    assert j.texto() == "sex 06/11, 19h–24h"


# ---------- valores em reais ----------

@pytest.mark.parametrize("trecho,valor", [
    ("180", 180), ("47,50", Decimal("47.50")), ("R$ 312,90", Decimal("312.90")), ("120 conto", 120),
    ("35 pila", 35), ("cento e vinte", 120), ("cem reais", 100), ("1.200", 1200), ("23 e 40", Decimal("23.40")),
    ("uns 80", 80), ("2 mil", 2000), ("1,5k", 1500), ("mil e duzentos", 1200), ("39.90", Decimal("39.90")),
])
def test_valores(trecho, valor):
    assert valor_em_reais(trecho) == Decimal(valor)


def test_valor_ambiguo_ou_ausente():
    assert valor_em_reais("entre 50 e 80") is None or valor_em_reais("entre 50 e 80") != 50
    assert valor_em_reais("barato") is None
    assert extenso_para_digitos("um bar com trinta e cinco reais") == "um bar com 35 reais"
    assert trecho_na_mensagem("47,50", "deu 47,50 o iFood")
    assert not trecho_na_mensagem("57,50", "deu 47,50 o iFood")


def test_reais_formato_brasileiro():
    assert reais(Decimal("1200")) == "R$ 1.200,00"
    assert reais(Decimal("23.4")) == "R$ 23,40"


# ---------- pseudonimização e lugares ----------

def test_pseudonimos_ida_e_volta():
    p = Pseudonimos(SALA, "Rafaela")
    t = p.ocultar("o caio pagou e o Marcio também, a Bianca não")
    assert t == "o @m5 pagou e o @m4 também, a Bianca não"
    assert p.revelar("@m4") == "Márcio" and p.revelar("eu") == "Rafaela"
    assert p.revelar_texto("@m3 e @m5") == "Bia e Caio"


def test_lugares():
    assert casar(["Asa Sul"])[0] == ["Plano Piloto"]
    assert casar(["lá pros lados de Ceilândia"])[0] == ["Ceilândia"]
    assert casar(["Taguá"])[0] == ["Taguatinga"]
    assert casar(["Riacho Fundo II"])[0] == ["Riacho Fundo II"]
    assert casar(["Pirenópolis"]) == ([], [], ["Pirenópolis"])


# ---------- interpretar() de ponta a ponta com LLM falso ----------

def test_disponibilidade_confirmacao_e_nome_oculto():
    r, llm = rodar("sexta depois das 19h ou sábado o dia todo, diz pra Bia",
                   it("disponibilidade", janelas=[jan(["sex"], apos="19:00"), jan(["sab"], "dia_todo")]))
    i = r.intencoes[0]
    assert "Bia" not in llm.recebido and "@m3" in llm.recebido   # nome não vai ao LLM
    assert i.destino == "agente_membro" and i.requer_confirmacao
    assert i.confirmacao == "sex 06/11, 19h–24h; sáb 07/11, 8h–24h. Está certo?"


def test_de_tarde_sem_dia_pergunta():
    r, _ = rodar("eu consigo de tarde", it("disponibilidade", janelas=[jan([], "tarde")]))
    i = r.intencoes[0]
    assert i.motivo_pergunta == "falta_dia" and i.pergunta and not i.requer_confirmacao


def test_orcamento_no_grupo_e_ignorado():
    r, _ = rodar("só tenho 50 conto", it("orcamento", valor="50 conto"), contexto="grupo")
    i = r.intencoes[0]
    assert i.destino == "ignorado" and not i.requer_confirmacao and i.confirmacao is None


def test_orcamento_no_privado():
    r, _ = rodar("tô liso, no máximo 30 conto", it("orcamento", valor="30 conto"))
    i = r.intencoes[0]
    assert i.valor == 30 and i.destino == "agente_membro" and "R$ 30,00" in i.confirmacao


def test_gasto_de_outra_pessoa_pede_confirmacao_dela():
    r, _ = rodar("o Caio pagou 90 do Uber", it("gasto", valor="90", pagador="@m5", descricao="Uber"),
                 contexto="grupo", autor="Bia")
    i = r.intencoes[0]
    assert (i.valor, i.pagador, i.confirmar_com, i.destino) == (90, "Caio", "Caio", "financas")


def test_valor_inventado_pelo_llm_e_descartado():
    # O LLM "calculou" 23,40 a partir de "23 e 40": o trecho não está na mensagem, então vira pergunta.
    r, _ = rodar("paguei o Uber, deu 23 e 40", it("gasto", valor="23,40", pagador="eu"))
    assert r.intencoes[0].motivo_pergunta == "valor_invalido" and r.intencoes[0].valor is None
    r, _ = rodar("paguei o Uber, deu 23 e 40", it("gasto", valor="23 e 40", pagador="eu"))
    assert r.intencoes[0].valor == Decimal("23.40")


def test_gasto_sem_valor():
    r, _ = rodar("paguei o estacionamento", it("gasto", pagador="eu", descricao="estacionamento"))
    assert r.intencoes[0].motivo_pergunta == "falta_valor"


def test_busca_monta_consulta_validada():
    r, _ = rodar("tem algum bar tranquilo em Taguatinga até 50 por pessoa?",
                 it("busca_lugar", valor="50", tipo_role="comer_beber", lugares=["Taguatinga"],
                    texto_busca="bar tranquilo", janelas=[jan(["sab"], apos="21:00")]))
    c = r.intencoes[0].consulta
    assert c.ras == ["Taguatinga"] and c.teto_pessoa == 50 and c.tipos_role == ["comer_beber"]
    assert c.texto == "bar tranquilo" and c.janela.inicio == datetime(2026, 11, 7, 21)


def test_pedido_por_voz_com_data_requer_confirmacao():
    r, _ = rodar("bora num show dia 14?", it("pedido_role", tipo_role="local_evento", janelas=[jan(["14"])]),
                 contexto="grupo", origem="voz")
    i = r.intencoes[0]
    assert (i.periodo_de, i.periodo_ate) == (date(2026, 11, 14), date(2026, 11, 14))
    assert i.requer_confirmacao and i.destino == "mediador"


def test_varias_intencoes():
    r, _ = rodar("sexta depois das 19h e no máximo 50 conto",
                 it("disponibilidade", janelas=[jan(["sex"], apos="19:00")]), it("orcamento", valor="50 conto"))
    assert [i.tipo for i in r.intencoes] == ["disponibilidade", "orcamento"]


def test_disponibilidades_separadas_viram_uma_confirmacao():
    r, _ = rodar("sábado eu não posso, mas domingo tô livre o dia todo",
                 it("disponibilidade", janelas=[jan(["sab"], disponivel=False)]),
                 it("disponibilidade", janelas=[jan(["dom"], "dia_todo")]))
    assert len(r.intencoes) == 1
    assert r.intencoes[0].confirmacao == "sáb 07/11, 8h–24h (não pode); dom 08/11, 8h–24h. Está certo?"


def test_falha_do_llm_nao_registra_nada():
    llm = LLMFalso(falhar=True)
    r = interpretar("paguei 180 do bar", membros=SALA, autor="Rafaela", agora=QUI, llm=llm)
    assert r.erro and r.intencoes[0].motivo_pergunta == "falha_llm" and r.intencoes[0].valor is None


def test_saida_fora_do_esquema_e_recusada():
    llm = LLMFalso(it("gasto", valor="10") | {"sql": "DROP TABLE lugares"})
    r = interpretar("paguei 10", membros=SALA, agora=QUI, llm=llm)
    assert r.erro and "ValidationError" in r.erro


def test_schema_estrito():
    def conferir(s):
        if s.get("type") == "object":
            assert s["additionalProperties"] is False and set(s["required"]) == set(s["properties"])
            for v in s["properties"].values():
                conferir(v)
        if "items" in s:
            conferir(s["items"])
    conferir(schema_llm())


# ---------- avaliação ----------

def test_comparar_e_clopper_pearson():
    r, _ = rodar("paguei 60 do bar e o Caio pagou 40 do Uber",
                 it("gasto", valor="40", pagador="@m5"), it("gasto", valor="60", pagador="eu"), contexto="grupo")
    prev = [comparavel(i) for i in r.intencoes]
    esp = [{"tipo": "gasto", "valor": 60, "pagador": "Rafaela"}, {"tipo": "gasto", "valor": 40, "pagador": "Caio"}]
    assert comparar(esp, prev)["frase_ok"]
    assert not comparar([{"tipo": "gasto", "valor": 61, "pagador": "Rafaela"}], prev[:1])["frase_ok"]
    assert abs(limite_inferior(34, 34) - 0.897) < 0.002
    assert abs(limite_inferior(31, 34) - 0.763) < 0.005
