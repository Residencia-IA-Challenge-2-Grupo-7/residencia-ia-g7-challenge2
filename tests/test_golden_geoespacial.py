"""
Testes do golden dataset da Semana 3 (issue #31).

Garante que data/golden_dataset_semana3.json segue o contrato JSON da issue
e que todo gabarito esta ancorado em um registro real da base 2FA (RNF-03).
"""

import json
from collections import Counter
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
GOLDEN = json.loads(
    (RAIZ / "data" / "golden_dataset_semana3.json").read_text(encoding="utf-8")
)
BASE_2FA = {
    registro["id"]: registro
    for registro in json.loads(
        (RAIZ / "data" / "banco_aprovado_2fa.json").read_text(encoding="utf-8")
    )
}

CAMPOS_OBRIGATORIOS = (
    "id",
    "pergunta",
    "categoria",
    "ra_esperada",
    "locais_gabarito",
    "preco_maximo_gabarito",
    "horario_gabarito",
    "evidencia_id_tiktok",
    "armadilha_llm_pura",
)
CATEGORIA_FORA_DE_ESCOPO = "fora_de_escopo_df"
CAMPOS_NULOS_FORA_DE_ESCOPO = (
    "ra_esperada",
    "preco_maximo_gabarito",
    "horario_gabarito",
    "evidencia_id_tiktok",
)
IDS_PARTE_1 = [f"golden_{n:02d}" for n in range(1, 11)]

CASOS_COM_EVIDENCIA = [
    caso for caso in GOLDEN if caso.get("categoria") != CATEGORIA_FORA_DE_ESCOPO
]


def _texto_preenchido(valor):
    return isinstance(valor, str) and valor.strip() != ""


def _numero(valor):
    return isinstance(valor, (int, float)) and not isinstance(valor, bool)


def _ids(casos):
    return [caso.get("id", "sem_id") for caso in casos]


def test_golden_tem_ids_01_a_10():
    """Existem pelo menos 10 casos, com golden_01 a golden_10 e sem IDs repetidos."""
    ids = [caso.get("id") for caso in GOLDEN]

    assert len(GOLDEN) >= 10
    assert len(ids) == len(set(ids)), "Ha IDs duplicados no golden dataset"
    faltando = [id_ for id_ in IDS_PARTE_1 if id_ not in ids]
    assert not faltando, f"IDs ausentes: {faltando}"


def test_golden_parte_1_distribuicao_por_categoria():
    """A parte 1 tem 5 casos geoespaciais, 3 de horario e 2 fora do DF."""
    parte_1 = [caso for caso in GOLDEN if caso.get("id") in IDS_PARTE_1]

    assert Counter(caso["categoria"] for caso in parte_1) == {
        "geoespacial_ra_fora_centro": 5,
        "janela_horario": 3,
        "fora_de_escopo_df": 2,
    }


@pytest.mark.parametrize("caso", GOLDEN, ids=_ids(GOLDEN))
def test_golden_campos_obrigatorios(caso):
    """Todas as chaves do contrato existem; null so e aceito fora do DF."""
    faltando = [campo for campo in CAMPOS_OBRIGATORIOS if campo not in caso]
    assert not faltando, f"Campos ausentes: {faltando}"

    for campo in ("id", "pergunta", "categoria", "armadilha_llm_pura"):
        assert _texto_preenchido(caso[campo]), f"'{campo}' esta vazio"
    assert isinstance(caso["locais_gabarito"], list)

    if caso["categoria"] == CATEGORIA_FORA_DE_ESCOPO:
        assert caso["locais_gabarito"] == [], "Fora do DF o gabarito deve ser []"
        for campo in CAMPOS_NULOS_FORA_DE_ESCOPO:
            assert caso[campo] is None, f"'{campo}' deveria ser null fora do DF"
    else:
        assert caso["locais_gabarito"], "'locais_gabarito' esta vazio"
        assert all(_texto_preenchido(local) for local in caso["locais_gabarito"])
        assert _texto_preenchido(caso["ra_esperada"])
        assert _texto_preenchido(caso["horario_gabarito"])
        assert _texto_preenchido(caso["evidencia_id_tiktok"])
        preco = caso["preco_maximo_gabarito"]
        assert _numero(preco) and preco > 0, f"Preco invalido: {preco!r}"


@pytest.mark.parametrize("caso", CASOS_COM_EVIDENCIA, ids=_ids(CASOS_COM_EVIDENCIA))
def test_golden_evidencia_existe_na_base_2fa(caso):
    """Todo evidencia_id_tiktok (exceto fora do DF) existe em banco_aprovado_2fa.json."""
    assert caso["evidencia_id_tiktok"] in BASE_2FA, (
        f"Evidencia {caso['evidencia_id_tiktok']} nao existe na base 2FA"
    )


@pytest.mark.parametrize("caso", CASOS_COM_EVIDENCIA, ids=_ids(CASOS_COM_EVIDENCIA))
def test_golden_gabarito_bate_com_registro_da_base(caso):
    """Nome, RA e preco do gabarito sao copiados do registro de evidencia."""
    registro = BASE_2FA.get(caso["evidencia_id_tiktok"])
    if registro is None:
        pytest.skip("Evidencia ausente; coberta por test_golden_evidencia_existe_na_base_2fa")

    assert registro["nome"] in caso["locais_gabarito"]
    assert registro["regiao_administrativa"] == caso["ra_esperada"]
    assert registro["custo_medio_rs"] == caso["preco_maximo_gabarito"]