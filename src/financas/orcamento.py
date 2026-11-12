"""Orçamento sigiloso do grupo (RF-11, RNF-02).

O teto de cada pessoa é usado só como restrição e nunca sai do servidor. As funções daqui recebem os tetos
como uma lista sem nomes, para que nenhum resultado possa ser atribuído a alguém, e as respostas para fora
são do tipo sim ou não, ou uma frase fixa ("fora do orçamento do grupo").

    from src.financas.orcamento import cabe_no_orcamento, calcular_teto_grupo
    calcular_teto_grupo([Decimal("80"), Decimal("60"), None])   # Decimal("60.00"), uso interno
    cabe_no_orcamento(Decimal("45"), [Decimal("80"), Decimal("60")])   # True

Atenção: o teto do grupo é o valor exato de uma pessoa. Ele serve para filtrar lugares no servidor e não
deve ser mostrado a ninguém, nem ao organizador (num grupo pequeno, dá para deduzir de quem é).
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Iterable

CENTAVO = Decimal("0.01")
MENSAGEM_FORA_DO_ORCAMENTO = "fora do orçamento do grupo"


def _reais(valor) -> Decimal | None:
    if valor is None or valor == "":
        return None
    if isinstance(valor, float):
        valor = str(valor)  # evita levar o erro de ponto flutuante para os centavos
    try:
        v = Decimal(valor).quantize(CENTAVO)
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError(f"Valor inválido: {valor!r}") from None
    if v < 0:
        raise ValueError("Valor de orçamento não pode ser negativo.")
    return v


def calcular_teto_grupo(limites_individuais: Iterable) -> Decimal | None:
    """Menor teto informado no grupo (quem não informou é ignorado). None se ninguém informou.

    Recebe só os valores, sem nomes: o resultado não diz de quem é o teto. É para uso interno do servidor."""
    valores = [v for v in (_reais(x) for x in limites_individuais) if v is not None]
    return min(valores) if valores else None


def teto_seguro_grupo(tetos: list[Decimal]) -> Decimal:
    """Ponto de encaixe usado pelas salas (`src/salas/integracoes.py`): o teto seguro do grupo."""
    teto = calcular_teto_grupo(tetos)
    if teto is None:
        raise ValueError("Nenhum teto informado.")
    return teto


def cabe_no_orcamento(custo_por_pessoa, limites_individuais: Iterable) -> bool:
    """O custo por pessoa cabe no teto de todos que informaram? Responde só sim ou não (RNF-02).

    Sem nenhum teto informado, não há restrição, e a resposta é sim."""
    custo = _reais(custo_por_pessoa)
    if custo is None:
        raise ValueError("Informe o custo por pessoa.")
    teto = calcular_teto_grupo(limites_individuais)
    return teto is None or custo <= teto


def cabe_para_cada_um(custos: dict, tetos: dict) -> bool:
    """Versão por pessoa, quando o custo muda de uma para outra (ex.: transporte de cada uma, RF-17).

    `custos` e `tetos` são indexados pela mesma identificação (id do participante); a resposta é um único
    sim ou não para o grupo, sem dizer quem não coube."""
    for pessoa, teto in tetos.items():
        t = _reais(teto)
        if t is None or pessoa not in custos:
            continue
        if _reais(custos[pessoa]) > t:
            return False
    return True


def teto_de_quem_nao_respondeu(padrao_do_perfil, limites_informados: Iterable) -> Decimal | None:
    """RF-11, "sem resposta": usa o orçamento padrão do perfil ou, se não houver, o menor informado no grupo."""
    padrao = _reais(padrao_do_perfil)
    return padrao if padrao is not None else calcular_teto_grupo(limites_informados)


def explicar_descarte() -> str:
    """Texto para o grupo quando um lugar sai por preço: nunca cita a pessoa (RF-11)."""
    return MENSAGEM_FORA_DO_ORCAMENTO
