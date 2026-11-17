"""Testes do módulo de finanças (issue #45): orçamento sigiloso, divisão da conta e código Pix (BR Code)."""
import random
from decimal import Decimal as D
from fractions import Fraction

import pytest

from src.financas import (ErroPix, ItemConta, cabe_no_orcamento, cabe_para_cada_um, calcular_teto_grupo,
                          crc16_ccitt, crc_confere, dividir_despesa, explicar_descarte, gerar_pix, normalizar_chave,
                          teto_de_quem_nao_respondeu, teto_seguro_grupo)
from src.financas.pix import ler_campos

# Exemplo de código estático do manual do BR Code do Banco Central (chave aleatória, sem valor)
EXEMPLO_BACEN = ("00020126580014br.gov.bcb.pix0136123e4567-e12b-12d1-a456-4266554400005204000053039865802BR"
                 "5913Fulano de Tal6008BRASILIA62070503***63041D3D")
CPF_VALIDO = "529.982.247-25"


# ======================================================================================== Pix (RF-33)

def test_crc16_ccitt_bate_com_o_valor_de_referencia():
    assert crc16_ccitt("123456789") == "29B1"  # valor de conferência do CRC-16/CCITT-FALSE


def test_reproduz_o_exemplo_do_banco_central():
    assert crc_confere(EXEMPLO_BACEN)
    gerado = gerar_pix("123e4567-e12b-12d1-a456-426655440000", "Fulano de Tal", cidade="Brasília")
    assert gerado == EXEMPLO_BACEN


def test_codigo_com_valor_tem_os_campos_do_padrao_e_crc_valido():
    codigo = gerar_pix("Rafaela@Email.com", "Rafaela Souza Gonçalves de Albuquerque", D("46.66"),
                       cidade="Águas Claras", descricao="Rolê de sábado")
    assert crc_confere(codigo)
    campos = ler_campos(codigo)
    assert campos["00"] == "01" and campos["52"] == "0000" and campos["53"] == "986" and campos["58"] == "BR"
    assert campos["54"] == "46.66"
    assert campos["59"] == "Rafaela Souza Goncalves d" and len(campos["59"]) <= 25  # sem acento, até 25
    assert campos["60"] == "AGUAS CLARAS" and len(campos["60"]) <= 15
    conta = ler_campos(campos["26"])
    assert conta["00"] == "br.gov.bcb.pix" and conta["01"] == "rafaela@email.com"
    assert conta["02"] == "Role de sabado"
    assert ler_campos(campos["62"]) == {"05": "***"}


def test_qualquer_alteracao_no_codigo_quebra_o_crc():
    codigo = gerar_pix("rafaela@email.com", "Rafaela", D("10.00"))
    adulterado = codigo.replace("10.00", "90.00")
    assert crc_confere(codigo) and not crc_confere(adulterado)


def test_sem_valor_o_campo_54_fica_de_fora():
    assert "54" not in ler_campos(gerar_pix("rafaela@email.com", "Rafaela"))


@pytest.mark.parametrize("valor", [D("0"), D("-5"), "abc"])
def test_valor_invalido(valor):
    with pytest.raises(ErroPix):
        gerar_pix("rafaela@email.com", "Rafaela", valor)


def test_descricao_longa_e_cortada_para_caber_no_campo_26():
    codigo = gerar_pix("123e4567-e12b-12d1-a456-426655440000", "Rafaela", D("1"), descricao="x" * 200)
    assert crc_confere(codigo) and len(ler_campos(codigo)["26"]) <= 99


@pytest.mark.parametrize("chave, tipo, esperado", [
    (CPF_VALIDO, None, ("52998224725", "cpf")),
    ("+55 (61) 99999-8888", None, ("+5561999998888", "telefone")),
    ("61 99999-8888", "telefone", ("+5561999998888", "telefone")),
    ("Rafaela@Email.COM", None, ("rafaela@email.com", "email")),
    ("123E4567-E12B-12D1-A456-426655440000", None, ("123e4567-e12b-12d1-a456-426655440000", "aleatoria")),
])
def test_normaliza_os_tipos_de_chave(chave, tipo, esperado):
    assert normalizar_chave(chave, tipo) == esperado


@pytest.mark.parametrize("chave", ["111.111.111-11", "123.456.789-00", "rafaela@", "abc", ""])
def test_recusa_chave_invalida(chave):
    with pytest.raises(ErroPix):
        normalizar_chave(chave)


# ============================================================================= orçamento (RF-11, RNF-02)

def test_teto_do_grupo_e_o_menor_informado_e_ignora_quem_nao_respondeu():
    assert calcular_teto_grupo([D("80"), D("60"), None, "55.5"]) == D("55.50")
    assert calcular_teto_grupo([None, None]) is None


def test_teto_nao_herda_erro_de_ponto_flutuante():
    assert calcular_teto_grupo([0.1 + 0.2]) == D("0.30")


def test_teto_negativo_e_recusado():
    with pytest.raises(ValueError):
        calcular_teto_grupo([D("-1")])


def test_cabe_no_orcamento_responde_so_sim_ou_nao():
    tetos = [D("80"), D("60"), D("55")]
    assert cabe_no_orcamento(D("55"), tetos) is True
    assert cabe_no_orcamento(D("55.01"), tetos) is False
    assert cabe_no_orcamento(D("500"), []) is True  # sem teto informado, sem restrição


def test_cabe_para_cada_um_considera_o_custo_de_cada_pessoa():
    tetos = {"bia": D("60"), "cadu": D("55"), "rafa": None}
    assert cabe_para_cada_um({"bia": D("58"), "cadu": D("50")}, tetos) is True
    assert cabe_para_cada_um({"bia": D("58"), "cadu": D("56")}, tetos) is False


def test_quem_nao_respondeu_usa_o_padrao_do_perfil_ou_o_menor_do_grupo():
    assert teto_de_quem_nao_respondeu(D("70"), [D("80"), D("60")]) == D("70.00")
    assert teto_de_quem_nao_respondeu(None, [D("80"), D("60")]) == D("60.00")


def test_explicacao_de_descarte_nao_cita_ninguem():
    assert explicar_descarte() == "fora do orçamento do grupo"


def test_encaixe_com_as_salas_usa_este_modulo():
    from src.salas import integracoes

    assert teto_seguro_grupo([D("80"), D("60")]) == D("60.00")
    assert integracoes.teto_do_grupo([D("80"), D("60")]) == D("60.00")


# ========================================================================== divisão da conta (RF-32)

def test_cenario_do_requisito_quem_foi_desmarcado_nao_paga():
    d = dividir_despesa(D("200"), ["rafaela", "bia", "cadu", "duda"], [{"valor": D("200"), "excluidos": ["duda"]}],
                        pagador="rafaela")
    assert "duda" not in d.devidos and d.cotas["duda"] == D("0.00")
    assert d.devidos == {"bia": D("66.66"), "cadu": D("66.66")}


def test_centavos_ficam_com_quem_pagou():
    d = dividir_despesa(D("100"), ["a", "b", "c"], pagador="a")
    assert d.devidos == {"b": D("33.33"), "c": D("33.33")}
    assert d.cotas["a"] == D("33.34") and sum(d.cotas.values()) == D("100.00")
    assert d.centavos_do_pagador == D("0.01")


def test_item_que_so_parte_consumiu():
    chope = ItemConta(D("60"), frozenset({"bia"}), "chope")  # a Bia não bebe
    d = dividir_despesa(D("200"), ["rafaela", "bia", "cadu"], [chope], pagador="rafaela")
    assert d.devidos == {"bia": D("46.66"), "cadu": D("76.66")}  # 140/3 e 140/3 + 30, para baixo
    assert sum(d.cotas.values()) == D("200.00")


def test_aceita_o_formato_do_banco_com_consumidores():
    d = dividir_despesa(D("90"), ["a", "b", "c"], [{"descricao": "vinho", "valor": D("60"), "consumidores": ["a", "b"]}],
                        pagador="c")
    assert d.devidos == {"a": D("40.00"), "b": D("40.00")}
    assert d.cotas["c"] == D("10.00")


def test_ninguem_paga_mais_que_a_propria_parte_em_casos_aleatorios():
    rnd = random.Random(45)
    for _ in range(300):
        pessoas = [f"p{i}" for i in range(rnd.randint(2, 9))]
        total = D(rnd.randint(1, 100_000)) / 100
        itens, resto = [], total
        for _ in range(rnd.randint(0, 3)):
            valor = (D(rnd.randint(0, int(resto * 100))) / 100).quantize(D("0.01"))
            excl = set(rnd.sample(pessoas, rnd.randint(0, len(pessoas) - 1)))
            itens.append(ItemConta(valor, frozenset(excl)))
            resto -= valor
        pagador = rnd.choice(pessoas)
        d = dividir_despesa(total, pessoas, itens, pagador=pagador)
        assert sum(d.cotas.values()) == total
        exatas = {p: Fraction(total - sum(i.valor for i in itens)) / len(pessoas) for p in pessoas}
        for i in itens:
            cons = [p for p in pessoas if p not in i.excluidos]
            for p in cons:
                exatas[p] += Fraction(i.valor) / len(cons)
        for p, v in d.devidos.items():
            assert Fraction(v) <= exatas[p] < Fraction(v) + Fraction(1, 100)  # no máximo 1 centavo a menos
        assert Fraction(d.cotas[pagador]) >= exatas[pagador]


def test_um_codigo_pix_por_devedor_com_o_valor_de_cada_um():
    d = dividir_despesa(D("200"), ["rafaela", "bia", "cadu"], [ItemConta(D("60"), frozenset({"bia"}))],
                        pagador="rafaela")
    codigos = d.codigos_pix(chave="rafaela@email.com", nome="Rafaela Souza", descricao="Rolê de sábado")
    assert set(codigos) == {"bia", "cadu"}
    for devedor, codigo in codigos.items():
        assert crc_confere(codigo)
        assert D(ler_campos(codigo)["54"]) == d.devidos[devedor]
    assert d.para_rateios() == [{"devedor_participante_id": "bia", "valor": D("46.66")},
                                {"devedor_participante_id": "cadu", "valor": D("76.66")}]


@pytest.mark.parametrize("kwargs, mensagem", [
    (dict(valor_total=D("100"), participantes_presentes=["a", "b"], pagador="z"), "presentes"),
    (dict(valor_total=D("0"), participantes_presentes=["a", "b"], pagador="a"), "maior que zero"),
    (dict(valor_total=D("10.005"), participantes_presentes=["a", "b"], pagador="a"), "2 casas"),
    (dict(valor_total=D("100"), participantes_presentes=["a", "a"], pagador="a"), "repetidos"),
    (dict(valor_total=D("100"), participantes_presentes=["a", "b"], pagador="a",
          exclusoes_por_item=[ItemConta(D("150"))]), "somam mais"),
    (dict(valor_total=D("100"), participantes_presentes=["a", "b"], pagador="a",
          exclusoes_por_item=[ItemConta(D("50"), frozenset({"a", "b"}))]), "Ninguém"),
    (dict(valor_total=D("100"), participantes_presentes=["a", "b"], pagador="a",
          exclusoes_por_item=[ItemConta(D("50"), frozenset({"x"}))]), "não estava"),
])
def test_entradas_invalidas_na_divisao(kwargs, mensagem):
    with pytest.raises(ValueError, match=mensagem):
        dividir_despesa(**kwargs)
