"""Finanças do app (issue #45): orçamento sigiloso, divisão da conta do pós-rolê e código Pix.

Tudo é calculado em código (RNF-04). O encaixe com as salas é `teto_seguro_grupo`, procurado por
`src/salas/integracoes.py`. Detalhes no README.md desta pasta.
"""
from src.financas.divisao_conta import Divisao, ItemConta, dividir_despesa
from src.financas.orcamento import (cabe_no_orcamento, cabe_para_cada_um, calcular_teto_grupo, explicar_descarte,
                                    teto_de_quem_nao_respondeu, teto_seguro_grupo)
from src.financas.pix import ErroPix, crc16_ccitt, crc_confere, gerar_pix, normalizar_chave

__all__ = [
    "Divisao", "ErroPix", "ItemConta", "cabe_no_orcamento", "cabe_para_cada_um", "calcular_teto_grupo",
    "crc16_ccitt", "crc_confere", "dividir_despesa", "explicar_descarte", "gerar_pix", "normalizar_chave",
    "teto_de_quem_nao_respondeu", "teto_seguro_grupo",
]
