"""Testes automatizados dos resultados oficiais do Benchmark A/B da Semana 3 (issue #38).

Valida que:
1. Os artefatos `data/resultados_benchmark_semana3.json`, `data/resultados_benchmark_semana3.csv`,
   `docs/entregas/semana-03/BENCHMARK_LLM_VS_RAG_LOG.txt` e `scripts/executar_benchmark_semana3.py`
   existem e não estão vazios.
2. `data/resultados_benchmark_semana3.json` contém os 20 casos do Golden Dataset (`golden_01` a
   `golden_20`) avaliados em cada uma das configurações (ao menos 4 configurações, incluindo as 6
   da tabela da issue #38) e ao menos 2 rodadas registradas.
3. Todos os campos de métricas por caso, por categoria (RNF-10) e por configuração estão
   preenchidos e dentro do domínio esperado, sem exigir um piso artificial de fidelidade
   (o teste valida a integridade e completude do experimento).
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from src.telemetria.evals_semana3 import NOMES_SCORES

RAIZ = Path(__file__).resolve().parents[1]
CAMINHO_JSON = RAIZ / "data" / "resultados_benchmark_semana3.json"
CAMINHO_CSV = RAIZ / "data" / "resultados_benchmark_semana3.csv"
CAMINHO_LOG = RAIZ / "docs" / "entregas" / "semana-03" / "BENCHMARK_LLM_VS_RAG_LOG.txt"
CAMINHO_SCRIPT = RAIZ / "scripts" / "executar_benchmark_semana3.py"

IDS_GOLDEN_ESPERADOS = [f"golden_{i:02d}" for i in range(1, 21)]
CATEGORIAS_ESPERADAS = {
    "geoespacial_ra_fora_centro",
    "janela_horario",
    "fora_de_escopo_df",
    "precisao_financeira",
    "vibes_e_restricoes",
    "conflito_e_girias",
}
CONFIGURACOES_ESPERADAS = (
    "1_llm_pura_sem_raciocinio",
    "2_llm_pura_raciocinio_alto",
    "3_rag_sem_llm_texto_fixo",
    "4_rag_llm_busca_lexica",
    "5_rag_llm_busca_lexica_raciocinio_alto",
    "6_rag_llm_busca_vetorial",
)
CAMPOS_RESUMO_OBRIGATORIOS = (
    "id_configuracao",
    "ordem",
    "nome",
    "como_rodar",
    "modo",
    "total_casos",
    "acerto_gabarito_contagem",
    "acerto_gabarito_df_contagem",
    "acerto_gabarito_taxa",
    "fidelidade_factual_rnf03_media",
    "taxa_alucinacao_media",
    "taxa_fora_da_base_media",
    "lugares_inventados_total",
    "precisao_geoespacial_ra_media",
    "precisao_geoespacial_ra_contagem",
    "abstencao_contagem",
    "sla_latencia_rnf14_contagem",
    "sla_latencia_rnf14_taxa",
    "acima_de_5s_contagem",
    "latencia_p50_ms",
    "latencia_p90_ms",
    "latencia_media_ms",
    "custo_medio_brl",
    "custo_total_brl",
    "tokens_medio",
    "atende_rnf14_p90_ate_5s",
    "zero_lugares_inventados",
    "metricas_busca",
    "por_categoria",
    "variacao_rodadas",
)


@pytest.fixture(scope="module")
def lista_casos_json() -> list[dict]:
    assert CAMINHO_JSON.is_file(), f"Arquivo ausente: {CAMINHO_JSON}"
    conteudo = CAMINHO_JSON.read_text(encoding="utf-8")
    assert len(conteudo.strip()) > 100
    dados = json.loads(conteudo)
    assert isinstance(dados, list), "A raiz de resultados_benchmark_semana3.json deve ser uma lista de 20 casos"
    assert len(dados) == 20
    return dados


@pytest.fixture(scope="module")
def dados_benchmark(lista_casos_json: list[dict]) -> dict:
    resumo_bench = lista_casos_json[0].get("resumo_benchmark") or {}
    assert isinstance(resumo_bench, dict) and resumo_bench
    return {
        "metadados": resumo_bench.get("metadados") or {},
        "configuracao_escolhida": resumo_bench.get("configuracao_escolhida") or {},
        "resumo_configuracoes": resumo_bench.get("resumo_configuracoes") or [],
        "por_categoria": resumo_bench.get("por_categoria") or {},
        "casos": lista_casos_json,
    }


def test_artefatos_existem_e_nao_estao_vazios():
    """Garante a presença do script, JSON, CSV e Log TXT comprobatório da Semana 3."""
    for caminho in (CAMINHO_SCRIPT, CAMINHO_JSON, CAMINHO_CSV, CAMINHO_LOG):
        assert caminho.is_file(), f"Artefato obrigatório não encontrado: {caminho}"
        assert caminho.stat().st_size > 0, f"Artefato está vazio: {caminho}"


def test_metadados_e_escolha_da_configuracao(dados_benchmark: dict):
    """Valida metadados gerais e o bloco de escolha da configuração vencedora."""
    meta = dados_benchmark.get("metadados") or {}
    assert meta.get("total_casos") == 20
    assert meta.get("total_configuracoes", 0) >= 4
    assert meta.get("num_rodadas", 0) >= 2
    assert meta.get("modelo_gerador")
    assert meta.get("modelo_juiz")

    escolha = dados_benchmark.get("configuracao_escolhida") or {}
    assert escolha.get("id_configuracao") == "3_rag_sem_llm_texto_fixo"
    assert escolha.get("nome")
    assert escolha.get("custo_medio_brl") == 0.0
    assert isinstance(escolha.get("atende_rnf14_p90_ate_5s"), bool)
    assert isinstance(escolha.get("zero_lugares_inventados"), bool)
    assert " de 20" in str(escolha.get("acerto_gabarito_contagem"))
    assert len(str(escolha.get("justificativa") or "")) >= 40
    assert isinstance(escolha.get("decisao_produto_com_llm"), dict)


def test_resumo_de_todas_as_configuracoes_preenchido(dados_benchmark: dict):
    """Confere que cada configuração testada possui resumo estatístico, categorias e variação entre rodadas."""
    resumos = dados_benchmark.get("resumo_configuracoes") or []
    assert len(resumos) >= 6
    ids_encontrados = {r.get("id_configuracao") for r in resumos}
    for cid in CONFIGURACOES_ESPERADAS:
        assert cid in ids_encontrados, f"Configuração {cid} ausente em resumo_configuracoes"

    for resumo in resumos:
        cid = resumo["id_configuracao"]
        for campo in CAMPOS_RESUMO_OBRIGATORIOS:
            assert campo in resumo, f"Campo {campo!r} ausente no resumo de {cid}"
            assert resumo[campo] is not None, f"Campo {campo!r} nulo no resumo de {cid}"

        assert resumo["total_casos"] == 20
        assert " de 20" in resumo["acerto_gabarito_contagem"]
        assert " de 18" in resumo["acerto_gabarito_df_contagem"]
        assert 0.0 <= float(resumo["acerto_gabarito_taxa"]) <= 1.0
        assert 0.0 <= float(resumo["fidelidade_factual_rnf03_media"]) <= 1.0
        assert 0.0 <= float(resumo["taxa_alucinacao_media"]) <= 1.0
        assert 0.0 <= float(resumo["taxa_fora_da_base_media"]) <= 1.0
        assert float(resumo["latencia_p50_ms"]) > 0.0
        assert float(resumo["latencia_p90_ms"]) >= float(resumo["latencia_p50_ms"])
        assert float(resumo["custo_medio_brl"]) >= 0.0

        # RNF-10: Consolidação por categoria
        por_cat = resumo["por_categoria"]
        assert set(por_cat.keys()) == CATEGORIAS_ESPERADAS
        assert sum(por_cat[c]["total_casos"] for c in CATEGORIAS_ESPERADAS) == 20

        # Variação entre ao menos 2 rodadas
        var = resumo["variacao_rodadas"]
        assert var.get("num_rodadas", 0) >= 2
        assert " de 20" in str(var.get("rodada_1_acerto_contagem"))
        assert " de 20" in str(var.get("rodada_2_acerto_contagem"))
        assert float(var.get("rodada_1_p90_ms") or 0.0) > 0.0
        assert float(var.get("rodada_2_p90_ms") or 0.0) > 0.0


@pytest.mark.parametrize("id_configuracao", CONFIGURACOES_ESPERADAS)
def test_vinte_casos_completos_por_configuracao(dados_benchmark: dict, id_configuracao: str):
    """Valida que cada configuração possui exatamente os 20 casos avaliados com scores e metadados."""
    casos = dados_benchmark.get("casos") or []
    assert len(casos) == 20
    assert [c.get("id_golden") for c in casos] == IDS_GOLDEN_ESPERADOS

    casos_r1 = [c["resultados_configuracoes"][id_configuracao] for c in casos]
    casos_r2 = [c["resultados_configuracoes"][id_configuracao].get("rodada_2") for c in casos]
    assert len(casos_r1) == 20
    assert len(casos_r2) == 20
    assert all(r2 is not None for r2 in casos_r2)

    for item in casos_r1:
        id_g = item["id_golden"]
        assert item.get("pergunta"), f"[{id_configuracao}/{id_g}] pergunta vazia"
        assert item.get("categoria") in CATEGORIAS_ESPERADAS
        assert isinstance(item.get("resposta"), str) and len(item["resposta"].strip()) > 0
        assert isinstance(item.get("fontes_utilizadas"), list)
        assert float(item.get("latencia_ms") or 0.0) > 0.0
        assert float(item.get("custo_estimado_brl") or 0.0) >= 0.0
        assert item.get("modelo")
        assert item.get("disponivel") is True, f"[{id_configuracao}/{id_g}] execução marcada como indisponível"

        scores = item.get("scores") or {}
        for nome_score in NOMES_SCORES:
            assert nome_score in scores, f"[{id_configuracao}/{id_g}] score {nome_score} ausente"

        assert scores["acerto_gabarito"] in (0.0, 1.0)
        assert scores["abstencao"] in (0.0, 1.0)
        assert scores["sla_latencia_rnf14"] in (0.0, 1.0)

        # Quando não houve abstenção, fidelidade, alucinação e fora_da_base devem estar preenchidos
        if scores["abstencao"] == 0.0:
            for s_factual in ("fidelidade_factual_rnf03", "taxa_alucinacao", "taxa_fora_da_base"):
                val = scores[s_factual]
                assert val is not None, f"[{id_configuracao}/{id_g}] {s_factual} é None sem abstenção"
                assert 0.0 <= float(val) <= 1.0

        det = item.get("verificacao_deterministica") or {}
        assert isinstance(det.get("locais_base_citados"), list)
        assert isinstance(det.get("locais_inventados"), list)
        assert isinstance(det.get("afirmacoes_deterministicas"), list)

        juiz = item.get("julgamento_juiz") or {}
        assert juiz.get("modelo_juiz")
        assert isinstance(juiz.get("afirmacoes"), list)

        busca = item.get("metricas_busca") or {}
        for chave_b in ("recall_at_k", "mrr", "posicao_gabarito", "recusa_correta", "recusa_indevida"):
            assert chave_b in busca


def test_lista_casos_consolidados_e_csv_e_log(dados_benchmark: dict):
    """Confere a lista `casos` (20 perguntas lado a lado), as 120 linhas do CSV e o conteúdo do Log TXT."""
    casos = dados_benchmark.get("casos") or []
    assert len(casos) == 20
    assert [c.get("id_golden") for c in casos] == IDS_GOLDEN_ESPERADOS

    for c in casos:
        assert "modo_a_llm_pura" in c
        assert "modo_b_rag" in c
        assert "delta_rag_vs_llm" in c
        cfgs = c.get("resultados_configuracoes") or {}
        for cid in CONFIGURACOES_ESPERADAS:
            assert cid in cfgs
            assert "rodada_2" in cfgs[cid]
            assert isinstance(cfgs[cid]["rodada_2"].get("resposta"), str)
            assert len(cfgs[cid]["rodada_2"]["resposta"].strip()) > 0

    with open(CAMINHO_CSV, "r", encoding="utf-8") as f:
        linhas_csv = list(csv.DictReader(f))
    assert len(linhas_csv) == 20 * len(CONFIGURACOES_ESPERADAS)

    texto_log = CAMINHO_LOG.read_text(encoding="utf-8")
    assert "RESUMO EXECUTIVO POR CONFIGURAÇÃO" in texto_log
    assert "CONFIGURAÇÃO ESCOLHIDA PARA O PRODUTO" in texto_log
    for id_g in IDS_GOLDEN_ESPERADOS:
        assert id_g in texto_log, f"Caso {id_g} não encontrado no log comprobatório TXT"
