"""Divisão da conta do pós-rolê (RF-32), com itens que nem todos consumiram e o Pix de cada devedor (RF-33).

Regras do RF-32:
- cada gasto é dividido igualmente entre os presentes; quem lançou pode desmarcar quem não consumiu um item
  (quem não bebe não paga o chope);
- quando a divisão não fecha em centavos, a diferença fica com quem pagou, e ninguém paga mais do que a
  própria parte.

    from src.financas.divisao_conta import ItemConta, dividir_despesa
    d = dividir_despesa(Decimal("200"), ["rafaela", "bia", "cadu"], pagador="rafaela",
                        exclusoes_por_item=[ItemConta(Decimal("60"), excluidos={"bia"}, descricao="chope")])
    d.devidos          # {"bia": Decimal("46.66"), "cadu": Decimal("76.66")}
    d.codigos_pix(chave="rafaela@email.com", nome="Rafaela Souza")   # um código por devedor

As contas são exatas (frações), sem ponto flutuante, e só no fim viram centavos (RNF-04).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from fractions import Fraction
from typing import Iterable, Mapping

from src.financas import pix

CENTAVO = Decimal("0.01")


def _reais(valor, nome: str = "valor") -> Decimal:
    if isinstance(valor, float):
        valor = str(valor)
    try:
        v = Decimal(valor)
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError(f"{nome} inválido: {valor!r}") from None
    if v != v.quantize(CENTAVO):
        raise ValueError(f"{nome} com mais de 2 casas decimais: {valor!r}")
    return v.quantize(CENTAVO)


def _centavos_para_baixo(fracao: Fraction) -> Decimal:
    """Parte exata em reais, arredondada para baixo no centavo (ninguém paga mais do que a própria parte)."""
    centavos = (fracao.numerator * 100) // fracao.denominator
    return (Decimal(centavos) / 100).quantize(CENTAVO)


@dataclass(frozen=True)
class ItemConta:
    """Um item da conta que nem todos consumiram. `excluidos`: quem foi desmarcado deste item."""
    valor: Decimal
    excluidos: frozenset[str] = field(default_factory=frozenset)
    descricao: str = ""

    def __post_init__(self):
        object.__setattr__(self, "valor", _reais(self.valor, "valor do item"))
        object.__setattr__(self, "excluidos", frozenset(self.excluidos))


@dataclass(frozen=True)
class Divisao:
    pagador: str
    total: Decimal
    cotas: dict[str, Decimal]       # parte de cada presente, pagador incluído; a soma é o total
    devidos: dict[str, Decimal]     # quanto cada devedor paga a quem pagou (só valores maiores que zero)
    centavos_do_pagador: Decimal    # o que os devedores deixam de pagar pelo arredondamento (fica com quem pagou)

    def para_rateios(self) -> list[dict]:
        """No formato da tabela `despesa_rateios` do banco (`src/db/models.py`, RateioDevedor)."""
        return [{"devedor_participante_id": d, "valor": v} for d, v in self.devidos.items()]

    def codigos_pix(self, *, chave: str, nome: str, cidade: str = "Brasilia", descricao: str | None = None,
                    tipo_chave: str | None = None) -> dict[str, str]:
        """Um código Pix copia e cola por devedor, com a chave de quem pagou e o valor devido (RF-33).

        Cada código vai em particular para o próprio devedor: o valor de um não deve aparecer para o outro."""
        return {devedor: pix.gerar_pix(chave, nome, valor, cidade=cidade, descricao=descricao, tipo_chave=tipo_chave)
                for devedor, valor in self.devidos.items()}


def _como_item(item, presentes: list[str]) -> ItemConta:
    if isinstance(item, ItemConta):
        return item
    if isinstance(item, Mapping):
        if "consumidores" in item and item["consumidores"]:  # formato do banco: quem consumiu
            excluidos = set(presentes) - set(item["consumidores"])
        else:
            excluidos = set(item.get("excluidos") or [])
        return ItemConta(item["valor"], frozenset(excluidos), item.get("descricao", ""))
    raise ValueError(f"Item da conta em formato desconhecido: {item!r}")


def dividir_despesa(valor_total, participantes_presentes: Iterable[str],
                    exclusoes_por_item: Iterable[ItemConta | Mapping] = (), *, pagador: str) -> Divisao:
    """Divide um gasto entre os presentes, com itens que só parte deles consumiu.

    `valor_total`: o valor pago (em reais, com até 2 casas). `participantes_presentes`: ids de quem estava no
    rolê; quem confirmou e não foi fica de fora (RF-32). `exclusoes_por_item`: itens com quem não consumiu;
    o que sobra do total, fora esses itens, é dividido entre todos os presentes. `pagador`: quem pagou, que
    precisa estar entre os presentes e recebe dos demais.
    """
    total = _reais(valor_total, "valor total")
    if total <= 0:
        raise ValueError("O valor total precisa ser maior que zero.")
    presentes = list(participantes_presentes)
    if not presentes:
        raise ValueError("Informe quem estava presente.")
    if len(set(presentes)) != len(presentes):
        raise ValueError("Há participantes repetidos; use ids únicos.")
    if pagador not in presentes:
        raise ValueError("Quem pagou precisa estar entre os presentes.")

    itens = [_como_item(i, presentes) for i in exclusoes_por_item]
    soma_itens = sum((i.valor for i in itens), Decimal("0"))
    if soma_itens > total:
        raise ValueError("Os itens somam mais que o total da conta.")

    partes = {p: Fraction(0) for p in presentes}
    geral = Fraction(total - soma_itens)
    for p in presentes:
        partes[p] += geral / len(presentes)
    for item in itens:
        estranhos = item.excluidos - set(presentes)
        if estranhos:
            raise ValueError(f"Desmarcado quem não estava presente: {sorted(estranhos)}")
        consumidores = [p for p in presentes if p not in item.excluidos]
        if not consumidores:
            raise ValueError(f"Ninguém ficou marcado no item {item.descricao or item.valor}.")
        for p in consumidores:
            partes[p] += Fraction(item.valor) / len(consumidores)

    cotas = {p: _centavos_para_baixo(partes[p]) for p in presentes if p != pagador}
    cotas[pagador] = total - sum(cotas.values(), Decimal("0"))
    absorvido = sum((partes[p] - Fraction(cotas[p]) for p in presentes if p != pagador), Fraction(0))
    absorvido_reais = (Decimal(absorvido.numerator) / Decimal(absorvido.denominator)).quantize(CENTAVO, ROUND_HALF_UP)
    return Divisao(
        pagador=pagador,
        total=total,
        cotas={p: cotas[p] for p in presentes},
        devidos={p: v for p, v in cotas.items() if p != pagador and v > 0},
        centavos_do_pagador=absorvido_reais,
    )
