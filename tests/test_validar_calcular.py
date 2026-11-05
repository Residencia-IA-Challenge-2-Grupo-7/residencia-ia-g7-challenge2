"""Testes com um lugar fictício, só em memória: nada disto vai para a base."""
from datetime import date

from base import normalizar as nz
from base.calcular import custo, estado, ficha_lugar
from base.validar import Paginas, Validador, obrigatorios

PAGINA = """Bistrô Exemplo
Funcionamento: terça a domingo, das 12h às 23h. Fechado às segundas.
Cardápio
Risoto de cogumelos R$ 58,00
Parmegiana de frango R$ 49,90
Suco de laranja R$ 12,00
Opções veganas no cardápio
Couvert artístico R$ 8,00
"""


def _validador():
    pg = Paginas({"lugar_id": "x", "paginas": []})
    pg.por_url = {"https://exemplo.com.br/": (nz.canon(PAGINA), "2026-11-03")}
    return Validador(pg)


def test_horario_com_evidencia_e_rejeicao_de_alucinacao():
    v = _validador()
    hs = v.horarios([
        {"dias": ["ter", "qua", "qui", "sex", "sab", "dom"], "abre": "12:00", "fecha": "23:00",
         "url": "https://exemplo.com.br/", "evidencia": "terça a domingo, das 12h às 23h"},
        {"dias": ["seg"], "abre": "12:00", "fecha": "23:00",
         "url": "https://exemplo.com.br/", "evidencia": "segunda, das 12h às 23h"},
    ])
    assert {h["dia"] for h in hs} == {"ter", "qua", "qui", "sex", "sab", "dom"}
    assert v.rejeicoes["evidencia_ausente"] == 1  # "segunda, das 12h às 23h" não está na página


def test_itens_preco_no_trecho_e_evidencia_inventada():
    v = _validador()
    its = v.itens([
        {"item": "Risoto de cogumelos", "preco": 58, "papel": "principal", "url": "https://exemplo.com.br/",
         "evidencia": "Risoto de cogumelos R$ 58,00"},
        {"item": "Parmegiana de frango", "preco": 49.9, "papel": "principal", "url": "https://exemplo.com.br/",
         "evidencia": "Parmegiana de frango R$ 49,90"},
        {"item": "Suco de laranja", "preco": 12, "papel": "bebida_nao_alcoolica", "url": "https://exemplo.com.br/",
         "evidencia": "Suco de laranja R$ 12,00"},
        {"item": "Lasanha", "preco": 45, "papel": "principal", "url": "https://exemplo.com.br/",
         "evidencia": "Lasanha R$ 45,00"},
        {"item": "Suco de laranja", "preco": 15, "papel": "bebida_nao_alcoolica", "url": "https://exemplo.com.br/",
         "evidencia": "Suco de laranja R$ 15,00"},
    ])
    assert [i["item"] for i in its] == ["Risoto de cogumelos", "Parmegiana de frango", "Suco de laranja"]
    assert v.rejeicoes["evidencia_ausente"] == 2  # lasanha e o suco a R$ 15 não estão na página


def test_atributo_exige_palavra_e_obrigatorios():
    v = _validador()
    at = v.atributos({"alim_vegano": {"valor": "sim", "url": "https://exemplo.com.br/",
                                      "evidencia": "Opções veganas no cardápio"},
                      "ar_livre": {"valor": "sim", "url": "https://exemplo.com.br/",
                                   "evidencia": "Opções veganas no cardápio"}}, "restaurante")
    assert set(at) == {"alim_vegano"}
    assert obrigatorios("comer_beber", {"horarios": [1], "itens": [1, 2]}) == ["menos_de_3_precos"]


def test_custo_por_pessoa_pela_formula_do_guia():
    itens = [{"papel": "principal", "preco": 58.0}, {"papel": "principal", "preco": 49.9},
             {"papel": "bebida_nao_alcoolica", "preco": 12.0}]
    mn, tip = custo("restaurante", itens, couvert=8.0, taxa_pct=10, entrada=None)
    assert tip == round(((58.0 + 49.9) / 2 + 12.0) * 1.1 + 8.0, 2)
    assert mn == round(49.9 * 1.1 + 8.0, 2)
    assert custo("parque", [], None, None, 0.0) == (0.0, 0.0)
    # bar sem preço de bebida: usa os pratos, e o mínimo nunca passa do típico
    bar = [{"papel": "principal", "preco": 29.9}, {"papel": "principal", "preco": 39.9},
           {"papel": "porcao", "preco": 37.9}]
    mn, tip = custo("bar", bar, None, None, None)
    assert (mn, tip) == (29.9, 34.9)


def test_estados_por_idade():
    hoje = date(2026, 11, 3)
    assert estado("horario", "2026-10-10", hoje) == "exato"
    assert estado("horario", "2026-09-01", hoje) == "aproximado"
    assert estado("horario", "2026-07-01", hoje) == "vencido"


def test_ficha_sem_campos_desconhecidos():
    l = {"nome": "Bistrô Exemplo", "categoria": "restaurante", "ra": "Taguatinga", "regiao": "oeste_proximo",
         "tipo_role": "comer_beber", "descricao": "", "atributos": {"alim_vegano": "sim"},
         "custo_pessoa_tipico": 75.4, "taxa_entrada": None, "itens": [{"item": "Risoto"}],
         "horarios": [{"dia": d} for d in nz.DIAS]}
    f = ficha_lugar(l)
    assert "Oeste próximo" in f and "R$ 75" in f and "vegana" in f and "todos os dias" in f
    assert "sem_informacao" not in f and "ruído" not in f
