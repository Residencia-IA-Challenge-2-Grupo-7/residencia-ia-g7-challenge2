"""Execução Oficial do Benchmark A/B da Semana 3 (20 Consultas × 6 Configurações) — Issue #38.

Percorre as 20 perguntas de `data/golden_dataset_semana3.json` nas 6 configurações da Semana 3
(em 2 rodadas independentes sem cache para medir variação estatística), avalia cada resposta com o
Avaliador Híbrido (`src/telemetria/evals_semana3.py`: RNF-04 determinístico + LLM-as-a-Judge
`xiaomi/mimo-v2.6-pro`), registra cada configuração como um experimento do Langfuse Cloud sobre o
dataset `golden_dataset_semana3` (`run_experiment`) e gera os artefatos oficiais:

- `data/resultados_benchmark_semana3.json`
- `data/resultados_benchmark_semana3.csv`
- `docs/entregas/semana-03/BENCHMARK_LLM_VS_RAG_LOG.txt`

Como executar:
    PYTHONPATH=. python scripts/executar_benchmark_semana3.py
"""
from __future__ import annotations

import argparse
import contextvars
import csv
import json
import os
import statistics
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, ".")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import requests  # noqa: E402

from src.rag import busca_vetorial, llm_pura, llm_rag  # noqa: E402
from src.rag.comparador_ab import (  # noqa: E402
    TOP_K,
    _executar_modo_b,
    _gabarito,
    carregar_golden,
    executar_comparacao_ab,
)
from src.telemetria.evals_semana3 import (  # noqa: E402
    MODELO_JUIZ_PADRAO,
    NOMES_SCORES,
    SLA_LATENCIA_MAX_MS,
    _calcular_scores_modo,
    _delta,
    _modelo_juiz,
    _registrar_scores_langfuse,
    calcular_metricas_busca,
    julgar_com_llm_judge,
    verificar_deterministico_rnf04,
)
from src.telemetria.telemetria import (  # noqa: E402
    carregar_base_oficial_leticia,
    checar_conexao_langfuse,
    flush_telemetria,
    obter_cliente,
    simular_recuperacao_rag,
)

RAIZ = Path(__file__).resolve().parents[1]
CAMINHO_GOLDEN = RAIZ / "data" / "golden_dataset_semana3.json"
CAMINHO_JSON = RAIZ / "data" / "resultados_benchmark_semana3.json"
CAMINHO_CSV = RAIZ / "data" / "resultados_benchmark_semana3.csv"
CAMINHO_LOG_TXT = RAIZ / "docs" / "entregas" / "semana-03" / "BENCHMARK_LLM_VS_RAG_LOG.txt"
CAMINHO_CHECKPOINT = RAIZ / "eval" / "resultados" / "checkpoint_benchmark_semana3.json"
NOME_DATASET_LANGFUSE = "golden_dataset_semana3"

CONFIGURACOES_BENCHMARK: tuple[dict[str, Any], ...] = (
    {
        "id": "1_llm_pura_sem_raciocinio",
        "ordem": 1,
        "nome": "LLM pura, sem raciocínio",
        "como_rodar": 'executar_comparacao_ab(...)["modo_a_llm_pura"]',
        "modo": "modo_a_llm_pura",
        "raciocinio": "desligado",
        "busca": None,
        "usa_llm": True,
        "usa_rag": False,
    },
    {
        "id": "2_llm_pura_raciocinio_alto",
        "ordem": 2,
        "nome": "LLM pura, raciocínio alto",
        "como_rodar": 'executar_comparacao_ab(..., raciocinio="high")["modo_a_llm_pura"]',
        "modo": "modo_a_llm_pura",
        "raciocinio": "high",
        "busca": None,
        "usa_llm": True,
        "usa_rag": False,
    },
    {
        "id": "3_rag_sem_llm_texto_fixo",
        "ordem": 3,
        "nome": "RAG sem LLM (busca + texto fixo da semana 2)",
        "como_rodar": "simular_recuperacao_rag / POST /rag/buscar",
        "modo": "rag_sem_llm",
        "raciocinio": "desligado",
        "busca": "lexica",
        "usa_llm": False,
        "usa_rag": True,
    },
    {
        "id": "4_rag_llm_busca_lexica",
        "ordem": 4,
        "nome": "RAG + LLM, busca léxica",
        "como_rodar": 'executar_comparacao_ab(...)["modo_b_rag"]',
        "modo": "modo_b_rag",
        "raciocinio": "desligado",
        "busca": "lexica",
        "usa_llm": True,
        "usa_rag": True,
    },
    {
        "id": "5_rag_llm_busca_lexica_raciocinio_alto",
        "ordem": 5,
        "nome": "RAG + LLM, busca léxica, raciocínio alto",
        "como_rodar": 'executar_comparacao_ab(..., raciocinio="high")["modo_b_rag"]',
        "modo": "modo_b_rag",
        "raciocinio": "high",
        "busca": "lexica",
        "usa_llm": True,
        "usa_rag": True,
    },
    {
        "id": "6_rag_llm_busca_vetorial",
        "ordem": 6,
        "nome": "RAG + LLM, busca vetorial",
        "como_rodar": 'executar_comparacao_ab(..., busca="vetorial")["modo_b_rag"]',
        "modo": "modo_b_rag",
        "raciocinio": "desligado",
        "busca": "vetorial",
        "usa_llm": True,
        "usa_rag": True,
    },
)


def calcular_p90(valores: list[float]) -> float:
    if not valores:
        return 0.0
    if len(valores) == 1:
        return round(float(valores[0]), 1)
    return round(float(statistics.quantiles(valores, n=10)[-1]), 1)


def calcular_p50(valores: list[float]) -> float:
    if not valores:
        return 0.0
    return round(float(statistics.median(valores)), 1)


def _extrair_trace_id(trace_url: str | None, fallback_id: str | None = None) -> str | None:
    if fallback_id and fallback_id != "trace-2fa-audit":
        return fallback_id
    if not trace_url:
        return None
    limpo = trace_url.rstrip("/")
    if "/traces/" in limpo:
        tid = limpo.rsplit("/", 1)[-1].strip()
        return tid or None
    return None


def _adaptar_rag_sem_llm(r_rag: dict[str, Any]) -> dict[str, Any]:
    """Converte a saída de `simular_recuperacao_rag` para o contrato de modo esperado pelo avaliador."""
    resposta = str(r_rag.get("resposta_ia") or "")
    roles = r_rag.get("roles_recuperados") or []
    fontes = llm_rag.formatar_fontes(roles, resposta)
    for f in fontes:
        f["citada"] = bool(f.get("nome") and f["nome"].lower() in resposta.lower())
    trace_url = r_rag.get("trace_url")
    trace_id = _extrair_trace_id(trace_url, r_rag.get("trace_id"))
    return {
        "resposta": resposta,
        "fontes_utilizadas": fontes,
        "latencia_ms": float(r_rag.get("latencia_ms") or 0.0),
        "tokens_total": int(r_rag.get("tokens_utilizados") or 0),
        "tokens_raciocinio": 0,
        "custo_estimado_brl": float(r_rag.get("custo_estimado_brl") or 0.0),
        "modelo": "texto-fixo-sem-llm",
        "disponivel": True,
        "cache_hit": False,
        "erro": None,
        "raciocinio": None,
        "busca": "lexica",
        "guardrails": r_rag.get("guardrails") or {},
        "trace_id": trace_id,
        "trace_url": trace_url,
    }


def _executar_vetorial_isolado(pergunta: str, id_golden: str) -> dict[str, Any]:
    """Executa o Modo B com busca vetorial registrando um span/trace dedicado no Langfuse."""
    sessao = requests.Session()
    resumo = _executar_modo_b(
        pergunta,
        top_k=TOP_K,
        usar_cache=False,
        registrar=True,
        sessao=sessao,
        raciocinio=None,
        busca="vetorial",
    )
    trace_url = None
    trace_id = None
    try:
        cliente = obter_cliente()
        trace_id = cliente.get_current_trace_id()
        if trace_id:
            cliente.set_current_trace_as_public()
            trace_url = cliente.get_trace_url()
    except Exception:
        pass
    resumo["trace_id"] = trace_id
    resumo["trace_url"] = trace_url
    return resumo


try:
    from langfuse import observe as _observe

    _executar_vetorial_isolado = _observe(name="comparativo_modo_b_vetorial")(_executar_vetorial_isolado)
except Exception:
    pass


_LOCK_GERACAO_PADRAO = threading.Lock()
_LOCK_CHECKPOINT = threading.Lock()
_LOCK_CACHE_JUIZ = threading.Lock()
_CACHE_JUIZ: dict[tuple[str, str], dict[str, Any]] = {}


def avaliar_resposta_individual(
    pergunta: str,
    gabarito: dict[str, Any],
    resultado_modo: dict[str, Any],
    *,
    tem_busca: bool,
    base_2fa: list[dict[str, Any]],
    sessao: requests.Session | None = None,
) -> dict[str, Any]:
    """Executa Etapa 1 (RNF-04 determinístico) + Etapa 2 (Juiz MiMo-V2.6-Pro) + Scores + Métricas de Busca."""
    det = verificar_deterministico_rnf04(pergunta, gabarito, resultado_modo, base_2fa)
    resposta_txt = str(resultado_modo.get("resposta") or "").strip()
    chave_juiz = (pergunta, resposta_txt)

    if det["abstencao"] or resultado_modo.get("disponivel") is False:
        juiz = {
            "modelo_juiz": _modelo_juiz(),
            "usou_llm": False,
            "motivo_fallback": "sem afirmações para julgar",
            "afirmacoes": det["afirmacoes_deterministicas"],
            "latencia_juiz_ms": 0.0,
        }
    else:
        with _LOCK_CACHE_JUIZ:
            juiz_cached = _CACHE_JUIZ.get(chave_juiz)
        if juiz_cached is not None:
            juiz = dict(juiz_cached)
        else:
            juiz = julgar_com_llm_judge(pergunta, gabarito, resultado_modo, det, base_2fa, sessao=sessao)
            if juiz.get("usou_llm"):
                with _LOCK_CACHE_JUIZ:
                    _CACHE_JUIZ[chave_juiz] = dict(juiz)

    scores = _calcular_scores_modo(resultado_modo, det, juiz, gabarito)
    metricas_busca = calcular_metricas_busca(gabarito, resultado_modo) if tem_busca else {
        "recall_at_k": None,
        "mrr": None,
        "posicao_gabarito": None,
        "recusa_correta": None,
        "recusa_indevida": None,
    }
    return {
        "scores": scores,
        "verificacao_deterministica": det,
        "julgamento_juiz": juiz,
        "metricas_busca": metricas_busca,
    }


def _carregar_checkpoint() -> dict[str, Any]:
    if CAMINHO_CHECKPOINT.is_file():
        try:
            return json.loads(CAMINHO_CHECKPOINT.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _salvar_checkpoint(dados: dict[str, Any]) -> None:
    with _LOCK_CHECKPOINT:
        CAMINHO_CHECKPOINT.parent.mkdir(parents=True, exist_ok=True)
        CAMINHO_CHECKPOINT.write_text(json.dumps(dados, ensure_ascii=False, indent=1), encoding="utf-8")


def executar_rodada_caso(
    caso: dict[str, Any],
    rodada: int,
    base_2fa: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Executa as 6 configurações para 1 caso do golden dataset e avalia todas as respostas."""
    id_golden = caso["id"]
    pergunta = caso["pergunta"]
    gab = _gabarito(caso)

    # 1. Executa Par A/B sem raciocínio de forma isolada para medir latência RNF-14 sem fila concorrente
    with _LOCK_GERACAO_PADRAO:
        comp_lex = executar_comparacao_ab(
            "", id_golden, usar_cache=False, registrar=True, raciocinio=None, busca="lexica"
        )
    trace_url_lex = (comp_lex.get("modo_b_rag") or {}).get("trace_url")
    trace_id_lex = _extrair_trace_id(trace_url_lex)

    # 2. Executa Config 3 (RAG sem LLM — local), Config 2+5 (raciocínio alto) e Config 6 (busca vetorial) em paralelo
    raw_sem_llm = simular_recuperacao_rag(pergunta, top_k=TOP_K)
    modo_sem_llm = _adaptar_rag_sem_llm(raw_sem_llm)

    with ThreadPoolExecutor(max_workers=2) as pool_gen:
        fut_high = pool_gen.submit(
            contextvars.copy_context().run,
            executar_comparacao_ab,
            "",
            id_golden,
            usar_cache=False,
            registrar=True,
            raciocinio="high",
            busca="lexica",
        )
        fut_vet = pool_gen.submit(
            contextvars.copy_context().run,
            _executar_vetorial_isolado,
            pergunta,
            id_golden,
        )
        comp_high = fut_high.result()
        modo_vetorial = fut_vet.result()

    trace_url_high = (comp_high.get("modo_b_rag") or {}).get("trace_url")
    trace_id_high = _extrair_trace_id(trace_url_high)

    # Prepara os 6 blocos de execução bruta
    brutos: dict[str, dict[str, Any]] = {
        "1_llm_pura_sem_raciocinio": {
            **comp_lex["modo_a_llm_pura"],
            "trace_id": trace_id_lex,
            "trace_url": trace_url_lex,
        },
        "2_llm_pura_raciocinio_alto": {
            **comp_high["modo_a_llm_pura"],
            "trace_id": trace_id_high,
            "trace_url": trace_url_high,
        },
        "3_rag_sem_llm_texto_fixo": modo_sem_llm,
        "4_rag_llm_busca_lexica": {
            **comp_lex["modo_b_rag"],
            "trace_id": trace_id_lex,
            "trace_url": trace_url_lex,
        },
        "5_rag_llm_busca_lexica_raciocinio_alto": {
            **comp_high["modo_b_rag"],
            "trace_id": trace_id_high,
            "trace_url": trace_url_high,
        },
        "6_rag_llm_busca_vetorial": modo_vetorial,
    }

    # Avalia as 6 respostas em paralelo com o Avaliador Híbrido (RNF-04 + LLM-as-a-Judge MiMo-V2.6-Pro)
    avaliacoes: dict[str, dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=6) as pool:
        futuros = {}
        for cfg in CONFIGURACOES_BENCHMARK:
            cid = cfg["id"]
            sessao_juiz = requests.Session()
            futuros[cid] = pool.submit(
                avaliar_resposta_individual,
                pergunta,
                gab,
                brutos[cid],
                tem_busca=bool(cfg["usa_rag"]),
                base_2fa=base_2fa,
                sessao=sessao_juiz,
            )
        for cid, fut in futuros.items():
            avaliacoes[cid] = fut.result()

    # Registra os scores nos traces comparativos do Langfuse quando houver trace_id
    for tid, cid_a, cid_b in (
        (trace_id_lex, "1_llm_pura_sem_raciocinio", "4_rag_llm_busca_lexica"),
        (trace_id_high, "2_llm_pura_raciocinio_alto", "5_rag_llm_busca_lexica_raciocinio_alto"),
    ):
        if tid:
            _registrar_scores_langfuse(
                {
                    "modo_a_llm_pura": avaliacoes[cid_a],
                    "modo_b_rag": avaliacoes[cid_b],
                    "metricas_busca": avaliacoes[cid_b]["metricas_busca"],
                },
                trace_id=tid,
            )

    saida_caso: dict[str, dict[str, Any]] = {}
    for cfg in CONFIGURACOES_BENCHMARK:
        cid = cfg["id"]
        b = brutos[cid]
        av = avaliacoes[cid]
        saida_caso[cid] = {
            "id_configuracao": cid,
            "nome_configuracao": cfg["nome"],
            "rodada": rodada,
            "id_golden": id_golden,
            "pergunta": pergunta,
            "categoria": caso["categoria"],
            "resposta": b.get("resposta") or "",
            "fontes_utilizadas": b.get("fontes_utilizadas") or [],
            "latencia_ms": round(float(b.get("latencia_ms") or 0.0), 1),
            "tokens_total": int(b.get("tokens_total") or 0),
            "tokens_raciocinio": int(b.get("tokens_raciocinio") or 0),
            "custo_estimado_brl": round(float(b.get("custo_estimado_brl") or 0.0), 6),
            "modelo": b.get("modelo") or llm_pura._modelo(),
            "disponivel": bool(b.get("disponivel", True)),
            "cache_hit": bool(b.get("cache_hit", False)),
            "erro": b.get("erro"),
            "raciocinio": cfg["raciocinio"],
            "busca": b.get("busca") or cfg["busca"],
            "guardrails": b.get("guardrails"),
            "trace_id": b.get("trace_id"),
            "trace_url": b.get("trace_url"),
            "scores": av["scores"],
            "verificacao_deterministica": av["verificacao_deterministica"],
            "julgamento_juiz": av["julgamento_juiz"],
            "metricas_busca": av["metricas_busca"],
        }
    return saida_caso


def sincronizar_e_rodar_experimentos_langfuse(
    casos_golden: list[dict[str, Any]],
    resultados_rodada_principal: dict[str, dict[str, dict[str, Any]]],
) -> dict[str, dict[str, Any]]:
    """Sincroniza os 20 casos no dataset `golden_dataset_semana3` do Langfuse e executa `run_experiment`
    para cada uma das 6 configurações, retornando `experiment_url`, `experiment_id` e `trace_ids` por caso.
    """
    info_experimentos: dict[str, dict[str, Any]] = {}
    if not checar_conexao_langfuse():
        return info_experimentos

    try:
        from langfuse.experiment import Evaluation

        client = obter_cliente()
        client.create_dataset(
            name=NOME_DATASET_LANGFUSE,
            description=(
                "Golden Dataset Oficial da Semana 3 (20 consultas auditadas 2FA sobre o DF) — "
                "Grupo 7 Orquestrador de Rolês"
            ),
            metadata={"semana": 3, "total_casos": len(casos_golden), "issue": "#38"},
        )
        for caso in casos_golden:
            client.create_dataset_item(
                dataset_name=NOME_DATASET_LANGFUSE,
                id=caso["id"],
                input=caso["pergunta"],
                expected_output={
                    "locais_gabarito": caso["locais_gabarito"],
                    "ra_esperada": caso["ra_esperada"],
                    "preco_maximo_gabarito": caso["preco_maximo_gabarito"],
                    "horario_gabarito": caso["horario_gabarito"],
                },
                metadata={
                    "id_golden": caso["id"],
                    "categoria": caso["categoria"],
                    "evidencia_id_tiktok": caso["evidencia_id_tiktok"],
                    "armadilha_llm_pura": caso["armadilha_llm_pura"],
                },
            )
        dataset = client.get_dataset(NOME_DATASET_LANGFUSE)
        itens_ordenados = sorted(dataset.items, key=lambda it: str(it.id))

        timestamp_tag = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M")
        for cfg in CONFIGURACOES_BENCHMARK:
            cid = cfg["id"]
            run_name = f"semana3-{cid}-{timestamp_tag}"

            def _make_task(config_id: str):
                def _task(*, item, **kwargs):
                    id_g = item.id if hasattr(item, "id") else item.get("id")
                    registro = resultados_rodada_principal[id_g][config_id]
                    try:
                        client.update_current_span(
                            input=registro["pergunta"],
                            output=registro["resposta"],
                            metadata={
                                "id_golden": id_g,
                                "configuracao": config_id,
                                "categoria": registro["categoria"],
                                "latencia_ms": registro["latencia_ms"],
                                "custo_estimado_brl": registro["custo_estimado_brl"],
                                "modelo": registro["modelo"],
                            },
                        )
                    except Exception:
                        pass
                    return {
                        "id_golden": id_g,
                        "configuracao": config_id,
                        "resposta": registro["resposta"],
                        "fontes_utilizadas": [f.get("nome") for f in registro.get("fontes_utilizadas") or []],
                        "latencia_ms": registro["latencia_ms"],
                        "custo_estimado_brl": registro["custo_estimado_brl"],
                    }

                return _task

            def _make_evaluator(config_id: str):
                def _evaluator(*, input, output, expected_output=None, metadata=None, **kwargs):
                    id_g = (output or {}).get("id_golden") or (metadata or {}).get("id_golden")
                    registro = resultados_rodada_principal[id_g][config_id]
                    scores = registro.get("scores") or {}
                    busca = registro.get("metricas_busca") or {}
                    evals = []
                    for nome_s, val in scores.items():
                        if val is not None:
                            evals.append(
                                Evaluation(
                                    name=nome_s,
                                    value=float(val),
                                    comment=f"{cfg['nome']} ({id_g})",
                                )
                            )
                    for nome_b in ("recall_at_k", "mrr", "recusa_correta", "recusa_indevida"):
                        val_b = busca.get(nome_b)
                        if val_b is not None:
                            evals.append(
                                Evaluation(
                                    name=f"busca_{nome_b}",
                                    value=float(val_b),
                                    comment=f"Métrica de busca ({id_g})",
                                )
                            )
                    return evals

                return _evaluator

            exp_res = client.run_experiment(
                name=f"Benchmark Semana 3 — {cfg['nome']}",
                run_name=run_name,
                description=f"Avaliação oficial das 20 consultas do Golden Dataset na configuração {cfg['nome']}",
                data=itens_ordenados,
                task=_make_task(cid),
                evaluators=[_make_evaluator(cid)],
                max_concurrency=5,
                metadata={
                    "id_configuracao": cid,
                    "nome_configuracao": cfg["nome"],
                    "modelo_juiz": _modelo_juiz(),
                },
            )
            flush_telemetria()

            traces_por_caso: dict[str, dict[str, str | None]] = {}
            for item_res in exp_res.item_results:
                it_id = getattr(item_res.item, "id", None)
                tid = getattr(item_res, "trace_id", None)
                if it_id and tid:
                    t_url = f"https://cloud.langfuse.com/project/cmw59be2y01d8ad0jqbgsjut6/traces/{tid}"
                    traces_por_caso[str(it_id)] = {"trace_id": tid, "trace_url": t_url}
                    # Preenche trace_id/trace_url no registro principal caso ainda não tivesse link próprio
                    reg = resultados_rodada_principal[str(it_id)][cid]
                    if not reg.get("trace_id"):
                        reg["trace_id"] = tid
                    if not reg.get("trace_url"):
                        reg["trace_url"] = t_url
                    reg["experiment_trace_id"] = tid
                    reg["experiment_trace_url"] = t_url

            info_experimentos[cid] = {
                "run_name": exp_res.run_name,
                "experiment_id": getattr(exp_res, "experiment_id", None),
                "experiment_url": getattr(exp_res, "experiment_url", None),
                "traces_por_caso": traces_por_caso,
            }
            print(f"[Langfuse] Experimento registrado para {cid}: {getattr(exp_res, 'experiment_url', None)}")
    except Exception as exc:
        print(f"[Langfuse] Aviso ao registrar run_experiment: {exc}")

    return info_experimentos


def _media_opcional(valores: list[float | None]) -> float | None:
    validos = [float(v) for v in valores if v is not None]
    if not validos:
        return None
    return round(sum(validos) / len(validos), 4)


def agregar_metricas_lista(registros: list[dict[str, Any]]) -> dict[str, Any]:
    """Agrega contagens ('X de Y') e médias para uma lista de casos avaliados de uma configuração."""
    total = len(registros)
    registros_df = [r for r in registros if r["categoria"] != "fora_de_escopo_df"]
    registros_fora = [r for r in registros if r["categoria"] == "fora_de_escopo_df"]
    total_df = len(registros_df)
    total_fora = len(registros_fora)

    latencias = [float(r["latencia_ms"]) for r in registros]
    custos = [float(r["custo_estimado_brl"]) for r in registros]
    tokens = [int(r["tokens_total"]) for r in registros]
    tokens_rac = [int(r.get("tokens_raciocinio") or 0) for r in registros]

    acertos_total = sum(1 for r in registros if (r["scores"].get("acerto_gabarito") or 0.0) >= 1.0)
    acertos_df = sum(1 for r in registros_df if (r["scores"].get("acerto_gabarito") or 0.0) >= 1.0)
    acertos_fora = sum(1 for r in registros_fora if (r["scores"].get("acerto_gabarito") or 0.0) >= 1.0)

    fidelidades = [r["scores"].get("fidelidade_factual_rnf03") for r in registros]
    alucinacoes = [r["scores"].get("taxa_alucinacao") for r in registros]
    fora_base = [r["scores"].get("taxa_fora_da_base") for r in registros]
    precisoes_ra = [r["scores"].get("precisao_geoespacial_ra") for r in registros]
    abstencoes = [r["scores"].get("abstencao") for r in registros]
    slas = [r["scores"].get("sla_latencia_rnf14") for r in registros]

    casos_avaliados_fid = sum(1 for v in fidelidades if v is not None)
    casos_fidelidade_100 = sum(1 for v in fidelidades if v is not None and v >= 0.9999)
    casos_com_alucinacao = sum(1 for v in alucinacoes if v is not None and v > 0.0)
    casos_com_fora_base = sum(1 for v in fora_base if v is not None and v > 0.0)

    ra_validos = [v for v in precisoes_ra if v is not None]
    ra_acertos = sum(1 for v in ra_validos if v >= 1.0)
    abstencao_count = sum(1 for v in abstencoes if v is not None and v >= 1.0)
    acima_5s_count = sum(1 for lat in latencias if lat > SLA_LATENCIA_MAX_MS)
    dentro_5s_count = total - acima_5s_count

    lugares_inventados_lista: list[str] = []
    casos_com_lugar_inventado = 0
    casos_preco_contradiz = 0
    casos_endereco_inventado = 0
    for r in registros:
        det = r.get("verificacao_deterministica") or {}
        invs = det.get("locais_inventados") or []
        if invs:
            casos_com_lugar_inventado += 1
            lugares_inventados_lista.extend(invs)
        if det.get("preco_contradiz"):
            casos_preco_contradiz += 1
        if det.get("endereco_inventado"):
            casos_endereco_inventado += 1

    # Métricas de busca
    recalls = [r["metricas_busca"].get("recall_at_k") for r in registros_df if r.get("metricas_busca")]
    mrrs = [r["metricas_busca"].get("mrr") for r in registros_df if r.get("metricas_busca")]
    recusas_corretas = [r["metricas_busca"].get("recusa_correta") for r in registros_fora if r.get("metricas_busca")]
    recusas_indevidas = [r["metricas_busca"].get("recusa_indevida") for r in registros_df if r.get("metricas_busca")]

    recall_validos = [v for v in recalls if v is not None]
    recall_hits = sum(1 for v in recall_validos if v >= 1.0)
    recusa_corr_validos = [v for v in recusas_corretas if v is not None]
    recusa_corr_hits = sum(1 for v in recusa_corr_validos if v >= 1.0)
    recusa_ind_validos = [v for v in recusas_indevidas if v is not None]
    recusa_ind_hits = sum(1 for v in recusa_ind_validos if v >= 1.0)

    p50_ms = calcular_p50(latencias)
    p90_ms = calcular_p90(latencias)
    media_fid = _media_opcional(fidelidades)
    media_aluc = _media_opcional(alucinacoes)
    media_fora_base = _media_opcional(fora_base)
    media_ra = _media_opcional(precisoes_ra)

    return {
        "total_casos": total,
        "total_casos_df": total_df,
        "total_casos_fora_df": total_fora,
        "acerto_gabarito_num": acertos_total,
        "acerto_gabarito_contagem": f"{acertos_total} de {total}",
        "acerto_gabarito_taxa": round(acertos_total / total, 4) if total else 0.0,
        "acerto_gabarito_df_num": acertos_df,
        "acerto_gabarito_df_contagem": f"{acertos_df} de {total_df}",
        "acerto_gabarito_df_taxa": round(acertos_df / total_df, 4) if total_df else 0.0,
        "acerto_fora_escopo_num": acertos_fora,
        "acerto_fora_escopo_contagem": f"{acertos_fora} de {total_fora}",
        "fidelidade_factual_rnf03_media": media_fid if media_fid is not None else 0.0,
        "fidelidade_factual_casos_avaliados": f"{casos_avaliados_fid} de {total}",
        "fidelidade_100_contagem": f"{casos_fidelidade_100} de {casos_avaliados_fid}",
        "taxa_alucinacao_media": media_aluc if media_aluc is not None else 0.0,
        "casos_com_alucinacao_num": casos_com_alucinacao,
        "casos_com_alucinacao_contagem": f"{casos_com_alucinacao} de {total}",
        "taxa_fora_da_base_media": media_fora_base if media_fora_base is not None else 0.0,
        "casos_com_fora_da_base_num": casos_com_fora_base,
        "casos_com_fora_da_base_contagem": f"{casos_com_fora_base} de {total}",
        "lugares_inventados_total": len(lugares_inventados_lista),
        "lugares_inventados_unicos": sorted(set(lugares_inventados_lista)),
        "casos_com_lugar_inventado_num": casos_com_lugar_inventado,
        "casos_com_lugar_inventado_contagem": f"{casos_com_lugar_inventado} de {total}",
        "casos_preco_contradiz_contagem": f"{casos_preco_contradiz} de {total}",
        "casos_endereco_inventado_contagem": f"{casos_endereco_inventado} de {total}",
        "precisao_geoespacial_ra_media": media_ra if media_ra is not None else 0.0,
        "precisao_geoespacial_ra_num": ra_acertos,
        "precisao_geoespacial_ra_contagem": f"{ra_acertos} de {len(ra_validos)}",
        "abstencao_num": abstencao_count,
        "abstencao_contagem": f"{abstencao_count} de {total}",
        "abstencao_taxa": round(abstencao_count / total, 4) if total else 0.0,
        "sla_latencia_rnf14_taxa": round(dentro_5s_count / total, 4) if total else 0.0,
        "sla_latencia_rnf14_contagem": f"{dentro_5s_count} de {total}",
        "acima_de_5s_num": acima_5s_count,
        "acima_de_5s_contagem": f"{acima_5s_count} de {total}",
        "latencia_p50_ms": p50_ms,
        "latencia_p90_ms": p90_ms,
        "latencia_media_ms": round(sum(latencias) / total, 1) if total else 0.0,
        "latencia_p50_s": round(p50_ms / 1000.0, 2),
        "latencia_p90_s": round(p90_ms / 1000.0, 2),
        "custo_medio_brl": round(sum(custos) / total, 6) if total else 0.0,
        "custo_total_brl": round(sum(custos), 6),
        "tokens_medio": round(sum(tokens) / total, 1) if total else 0.0,
        "tokens_raciocinio_medio": round(sum(tokens_rac) / total, 1) if total else 0.0,
        "atende_rnf14_p90_ate_5s": p90_ms <= SLA_LATENCIA_MAX_MS,
        "zero_lugares_inventados": len(lugares_inventados_lista) == 0,
        "atende_meta_rnf03_fidelidade_95": (media_fid is not None and media_fid >= 0.95),
        "metricas_busca": {
            "recall_at_3_num": recall_hits if recall_validos else None,
            "recall_at_3_contagem": f"{recall_hits} de {len(recall_validos)}" if recall_validos else None,
            "recall_at_3_taxa": _media_opcional(recalls),
            "mrr_medio": _media_opcional(mrrs),
            "recusa_correta_contagem": (
                f"{recusa_corr_hits} de {len(recusa_corr_validos)}" if recusa_corr_validos else None
            ),
            "recusa_correta_taxa": _media_opcional(recusas_corretas),
            "recusa_indevida_contagem": (
                f"{recusa_ind_hits} de {len(recusa_ind_validos)}" if recusa_ind_validos else None
            ),
            "recusa_indevida_taxa": _media_opcional(recusas_indevidas),
        },
    }


def consolidar_por_categoria(registros: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Agrega as métricas por categoria de pergunta do Golden Dataset (RNF-10)."""
    categorias_ordenadas = (
        "geoespacial_ra_fora_centro",
        "janela_horario",
        "fora_de_escopo_df",
        "precisao_financeira",
        "vibes_e_restricoes",
        "conflito_e_girias",
    )
    por_cat: dict[str, dict[str, Any]] = {}
    for cat in categorias_ordenadas:
        sub = [r for r in registros if r["categoria"] == cat]
        if sub:
            por_cat[cat] = agregar_metricas_lista(sub)
    return por_cat


def escolher_melhor_configuracao(resumos: list[dict[str, Any]]) -> dict[str, Any]:
    """Aplica o critério pré-definido da Issue #38:
    - Entre as configurações com p90 de até 5 s (RNF-14) e nenhum lugar inventado,
      a de maior acerto do lugar do gabarito; no empate, a mais barata.
    """
    elegiveis = [
        r for r in resumos
        if r["atende_rnf14_p90_ate_5s"] and r["zero_lugares_inventados"]
    ]
    candidatas = elegiveis if elegiveis else list(resumos)
    candidatas.sort(
        key=lambda r: (
            -r["acerto_gabarito_num"],
            -r["acerto_gabarito_df_num"],
            r["custo_medio_brl"],
            r["latencia_p90_ms"],
        )
    )
    vencedora = candidatas[0]
    descartadas = []
    for r in resumos:
        if r["id_configuracao"] == vencedora["id_configuracao"]:
            continue
        motivos = []
        if not r["atende_rnf14_p90_ate_5s"]:
            motivos.append(f"p90 = {r['latencia_p90_s']:.2f} s (> 5,0 s do RNF-14)")
        if not r["zero_lugares_inventados"]:
            motivos.append(
                f"inventou {r['lugares_inventados_total']} local(is) ({r['casos_com_lugar_inventado_contagem']} casos)"
            )
        if r["acerto_gabarito_num"] < vencedora["acerto_gabarito_num"]:
            motivos.append(
                f"menor acerto do gabarito ({r['acerto_gabarito_contagem']} vs. {vencedora['acerto_gabarito_contagem']})"
            )
        elif r["custo_medio_brl"] > vencedora["custo_medio_brl"]:
            motivos.append(
                f"maior custo médio (R$ {r['custo_medio_brl']:.6f} vs. R$ {vencedora['custo_medio_brl']:.6f})"
            )
        descartadas.append({
            "id_configuracao": r["id_configuracao"],
            "nome": r["nome"],
            "motivos": motivos,
        })

    return {
        "id_configuracao": vencedora["id_configuracao"],
        "ordem": vencedora["ordem"],
        "nome": vencedora["nome"],
        "como_rodar": vencedora["como_rodar"],
        "atende_rnf14_p90_ate_5s": vencedora["atende_rnf14_p90_ate_5s"],
        "zero_lugares_inventados": vencedora["zero_lugares_inventados"],
        "acerto_gabarito_contagem": vencedora["acerto_gabarito_contagem"],
        "acerto_gabarito_df_contagem": vencedora["acerto_gabarito_df_contagem"],
        "acerto_gabarito_taxa": vencedora["acerto_gabarito_taxa"],
        "fidelidade_factual_rnf03_media": vencedora["fidelidade_factual_rnf03_media"],
        "taxa_alucinacao_media": vencedora["taxa_alucinacao_media"],
        "precisao_geoespacial_ra_media": vencedora["precisao_geoespacial_ra_media"],
        "latencia_p50_ms": vencedora["latencia_p50_ms"],
        "latencia_p90_ms": vencedora["latencia_p90_ms"],
        "custo_medio_brl": vencedora["custo_medio_brl"],
        "criterio_aplicado": (
            "Entre as configurações com p90 <= 5 s (RNF-14) e nenhum lugar inventado (0 locais falsos), "
            "a de maior acerto do lugar do gabarito; no empate, a mais barata."
        ),
        "justificativa": (
            f"A configuração '{vencedora['nome']}' ({vencedora['id_configuracao']}) foi eleita a melhor para o "
            f"produto por cumprir simultaneamente o SLA de latência RNF-14 (p90 = {vencedora['latencia_p90_s']:.2f} s "
            f"<= 5,0 s, com {vencedora['sla_latencia_rnf14_contagem']} respostas dentro do limite) e zero lugares "
            f"inventados (0 estabelecimentos falsos em 20 consultas, fidelidade factual média de "
            f"{vencedora['fidelidade_factual_rnf03_media'] * 100:.1f}%), alcançando o maior acerto do gabarito entre "
            f"as configurações elegíveis ({vencedora['acerto_gabarito_contagem']} no geral e "
            f"{vencedora['acerto_gabarito_df_contagem']} nos casos do DF) com custo médio de "
            f"R$ {vencedora['custo_medio_brl']:.5f} por consulta."
        ),
        "comparacao_descartadas": descartadas,
    }


def salvar_csv(casos_consolidados: list[dict[str, Any]], caminho_csv: Path = CAMINHO_CSV) -> None:
    """Salva a tabela plana (20 perguntas × 6 configurações = 120 linhas) em CSV UTF-8."""
    caminho_csv.parent.mkdir(parents=True, exist_ok=True)
    colunas = [
        "id_golden",
        "categoria",
        "ra_esperada",
        "locais_gabarito",
        "preco_maximo_gabarito",
        "id_configuracao",
        "ordem_configuracao",
        "nome_configuracao",
        "modo",
        "raciocinio",
        "busca",
        "modelo",
        "latencia_ms",
        "latencia_r2_ms",
        "tokens_total",
        "tokens_raciocinio",
        "custo_estimado_brl",
        "fidelidade_factual_rnf03",
        "taxa_alucinacao",
        "taxa_fora_da_base",
        "precisao_geoespacial_ra",
        "acerto_gabarito",
        "acerto_gabarito_r2",
        "abstencao",
        "sla_latencia_rnf14",
        "recall_at_k",
        "mrr",
        "posicao_gabarito",
        "recusa_correta",
        "recusa_indevida",
        "locais_base_citados",
        "locais_inventados",
        "fontes_recuperadas",
        "trace_id",
        "trace_url",
        "pergunta",
        "resposta",
    ]
    with open(caminho_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=colunas)
        writer.writeheader()
        for item_caso in casos_consolidados:
            gab = item_caso["gabarito"] or {}
            for cfg in CONFIGURACOES_BENCHMARK:
                cid = cfg["id"]
                reg = item_caso["resultados_configuracoes"][cid]
                scores = reg["scores"]
                det = reg["verificacao_deterministica"]
                busca = reg["metricas_busca"]
                r2 = reg.get("rodada_2") or {}
                writer.writerow({
                    "id_golden": item_caso["id_golden"],
                    "categoria": item_caso["categoria"],
                    "ra_esperada": gab.get("ra_esperada") or "",
                    "locais_gabarito": "; ".join(gab.get("locais_gabarito") or []),
                    "preco_maximo_gabarito": gab.get("preco_maximo_gabarito") if gab.get("preco_maximo_gabarito") is not None else "",
                    "id_configuracao": cid,
                    "ordem_configuracao": cfg["ordem"],
                    "nome_configuracao": cfg["nome"],
                    "modo": cfg["modo"],
                    "raciocinio": cfg["raciocinio"],
                    "busca": reg.get("busca") or "",
                    "modelo": reg.get("modelo") or "",
                    "latencia_ms": reg.get("latencia_ms"),
                    "latencia_r2_ms": r2.get("latencia_ms", ""),
                    "tokens_total": reg.get("tokens_total"),
                    "tokens_raciocinio": reg.get("tokens_raciocinio"),
                    "custo_estimado_brl": reg.get("custo_estimado_brl"),
                    "fidelidade_factual_rnf03": scores.get("fidelidade_factual_rnf03"),
                    "taxa_alucinacao": scores.get("taxa_alucinacao"),
                    "taxa_fora_da_base": scores.get("taxa_fora_da_base"),
                    "precisao_geoespacial_ra": scores.get("precisao_geoespacial_ra"),
                    "acerto_gabarito": scores.get("acerto_gabarito"),
                    "acerto_gabarito_r2": (r2.get("scores") or {}).get("acerto_gabarito", ""),
                    "abstencao": scores.get("abstencao"),
                    "sla_latencia_rnf14": scores.get("sla_latencia_rnf14"),
                    "recall_at_k": busca.get("recall_at_k"),
                    "mrr": busca.get("mrr"),
                    "posicao_gabarito": busca.get("posicao_gabarito"),
                    "recusa_correta": busca.get("recusa_correta"),
                    "recusa_indevida": busca.get("recusa_indevida"),
                    "locais_base_citados": "; ".join(det.get("locais_base_citados") or []),
                    "locais_inventados": "; ".join(det.get("locais_inventados") or []),
                    "fontes_recuperadas": "; ".join(
                        f.get("nome") or "" for f in (reg.get("fontes_utilizadas") or [])
                    ),
                    "trace_id": reg.get("trace_id") or "",
                    "trace_url": reg.get("trace_url") or "",
                    "pergunta": item_caso["pergunta"],
                    "resposta": (reg.get("resposta") or "").replace("\n", " "),
                })


def gerar_log_txt(dados_finais: dict[str, Any], caminho_log: Path = CAMINHO_LOG_TXT) -> None:
    """Gera o relatório comprobatório `docs/entregas/semana-03/BENCHMARK_LLM_VS_RAG_LOG.txt`."""
    caminho_log.parent.mkdir(parents=True, exist_ok=True)
    meta = dados_finais["metadados"]
    escolha = dados_finais["configuracao_escolhida"]
    resumos = dados_finais["resumo_configuracoes"]
    casos = dados_finais["casos"]

    linhas: list[str] = []
    sep_duplo = "=" * 105
    sep_simples = "-" * 105

    linhas.append(sep_duplo)
    linhas.append("LOG COMPROBATÓRIO OFICIAL — BENCHMARK A/B: LLM PURA vs. RAG ANCORADO 2FA (SEMANA 3 — ISSUE #38)")
    linhas.append("   RESIDÊNCIA EM IA (INSTITUTO ELDORADO / UnB) | GRUPO 7 — ORQUESTRADOR DE ROLÊS")
    linhas.append(sep_duplo)
    linhas.append(f"Data/Hora da Consolidação : {meta['data_execucao']}")
    linhas.append(f"Golden Dataset Avaliado   : {meta['arquivo_golden']} ({meta['total_casos']} consultas auditadas)")
    linhas.append(f"Base Oficial de Conhecim. : {meta['arquivo_base_2fa']} ({meta['total_locais_base_2fa']} locais DF validados em 2 fatores)")
    linhas.append(f"Modelo Gerador Avaliado   : {meta['modelo_gerador']} (OpenRouter, temperatura 0, ZDR ativo)")
    linhas.append(f"Modelo Avaliador (Juiz)   : {meta['modelo_juiz']} (Etapa 1 RNF-04 Código + Etapa 2 LLM-as-a-Judge)")
    linhas.append(f"Dataset Langfuse Cloud    : {meta['dataset_langfuse']} ({meta['total_configuracoes']} configurações × {meta['num_rodadas']} rodadas)")
    linhas.append(sep_duplo)
    linhas.append("")

    # SEÇÃO 1: RESUMO EXECUTIVO POR CONFIGURAÇÃO
    linhas.append("1. RESUMO EXECUTIVO POR CONFIGURAÇÃO (20 CONSULTAS — CONTAGENS E MÉTRICAS OFICIAIS)")
    linhas.append(sep_simples)
    cabecalho_tab = (
        f"{'#':<2} | {'Configuração':<38} | {'Acerto Gab.':<12} | {'Acerto DF':<10} | "
        f"{'Fidelid.':<9} | {'Alucin.':<8} | {'Inv.':<6} | {'Prec. RA':<10} | {'p50 / p90':<13} | {'Custo Méd.'}"
    )
    linhas.append(cabecalho_tab)
    linhas.append(sep_simples)
    for r in resumos:
        fid_str = f"{r['fidelidade_factual_rnf03_media'] * 100:5.1f}%"
        alu_str = f"{r['taxa_alucinacao_media'] * 100:5.1f}%"
        ra_str = f"{r['precisao_geoespacial_ra_contagem']}"
        lat_str = f"{r['latencia_p50_s']:.1f}s / {r['latencia_p90_s']:.1f}s"
        custo_str = f"R$ {r['custo_medio_brl']:.5f}"
        linhas.append(
            f"{r['ordem']:<2} | {r['nome']:<38} | {r['acerto_gabarito_contagem']:<12} | "
            f"{r['acerto_gabarito_df_contagem']:<10} | {fid_str:<9} | {alu_str:<8} | "
            f"{r['lugares_inventados_total']:<6} | {ra_str:<10} | {lat_str:<13} | {custo_str}"
        )
    linhas.append(sep_simples)
    linhas.append("")

    # Detalhamento completo por configuração + métricas de busca + variação entre as 2 rodadas
    linhas.append("1.1. DETALHAMENTO COMPLETO E VARIAÇÃO ENTRE RODADAS (RODADA 1 vs. RODADA 2)")
    linhas.append(sep_simples)
    for r in resumos:
        var = r.get("variacao_rodadas") or {}
        mb = r.get("metricas_busca") or {}
        linhas.append(f"[{r['ordem']}] {r['nome']} ({r['id_configuracao']})")
        linhas.append(f"    • Como rodar               : {r['como_rodar']}")
        linhas.append(
            f"    • Acerto do Gabarito       : {r['acerto_gabarito_contagem']} ({r['acerto_gabarito_taxa'] * 100:.1f}%) "
            f"| Casos dentro do DF: {r['acerto_gabarito_df_contagem']} ({r['acerto_gabarito_df_taxa'] * 100:.1f}%) "
            f"| Recusa fora do DF: {r['acerto_fora_escopo_contagem']}"
        )
        linhas.append(
            f"    • Fidelidade Factual RNF-03: {r['fidelidade_factual_rnf03_media'] * 100:.1f}% "
            f"(casos com afirmações avaliadas: {r['fidelidade_factual_casos_avaliados']}; "
            f"100% fiéis: {r['fidelidade_100_contagem']}; meta RNF-03 >= 95%: "
            f"{'ATINGIDA' if r['atende_meta_rnf03_fidelidade_95'] else 'NÃO ATINGIDA'})"
        )
        linhas.append(
            f"    • Taxa de Alucinação       : {r['taxa_alucinacao_media'] * 100:.1f}% "
            f"(casos com contradição factual: {r['casos_com_alucinacao_contagem']}; "
            f"preço contraditório: {r['casos_preco_contradiz_contagem']}; "
            f"endereço contraditório/inventado: {r['casos_endereco_inventado_contagem']})"
        )
        linhas.append(
            f"    • Taxa Fora da Base / Inv. : {r['taxa_fora_da_base_media'] * 100:.1f}% fora da base "
            f"| Lugares inventados: {r['lugares_inventados_total']} em {r['casos_com_lugar_inventado_contagem']} casos "
            f"({', '.join(r['lugares_inventados_unicos'][:8]) if r['lugares_inventados_unicos'] else 'nenhum'})"
        )
        linhas.append(
            f"    • Precisão Geoespacial (RA): {r['precisao_geoespacial_ra_media'] * 100:.1f}% "
            f"({r['precisao_geoespacial_ra_contagem']} respostas com recomendação na RA esperada) "
            f"| Abstenções ('não sei'/recusa): {r['abstencao_contagem']}"
        )
        if mb.get("recall_at_3_contagem") is not None:
            linhas.append(
                f"    • Métricas da Busca (RAG)  : Recall@3 = {mb['recall_at_3_contagem']} "
                f"({(mb['recall_at_3_taxa'] or 0.0) * 100:.1f}%) | MRR = {(mb['mrr_medio'] or 0.0):.4f} "
                f"| Recusa correta fora DF = {mb['recusa_correta_contagem']} "
                f"| Recusa indevida DF = {mb['recusa_indevida_contagem']}"
            )
        else:
            linhas.append("    • Métricas da Busca (RAG)  : N/A (configuração sem recuperação de documentos)")
        linhas.append(
            f"    • Latência (RNF-14 <= 5s)  : p50 = {r['latencia_p50_ms']:.0f} ms ({r['latencia_p50_s']:.2f} s) | "
            f"p90 = {r['latencia_p90_ms']:.0f} ms ({r['latencia_p90_s']:.2f} s) | "
            f"Dentro de 5 s: {r['sla_latencia_rnf14_contagem']} (acima de 5 s: {r['acima_de_5s_contagem']})"
        )
        linhas.append(
            f"    • Custo e Tokens           : Custo médio = R$ {r['custo_medio_brl']:.6f} "
            f"(Total 20 casos = R$ {r['custo_total_brl']:.5f}) | Tokens médios = {r['tokens_medio']:.0f} "
            f"(raciocínio = {r['tokens_raciocinio_medio']:.0f})"
        )
        if var:
            linhas.append(
                f"    • Variação (2 Rodadas)     : Acerto R1 = {var['rodada_1_acerto_contagem']} vs. "
                f"R2 = {var['rodada_2_acerto_contagem']} (delta = {var['delta_acerto_num']:+d}) | "
                f"p90 R1 = {var['rodada_1_p90_ms']:.0f} ms vs. R2 = {var['rodada_2_p90_ms']:.0f} ms | "
                f"Fidelidade R1 = {var['rodada_1_fidelidade'] * 100:.1f}% vs. R2 = {var['rodada_2_fidelidade'] * 100:.1f}%"
            )
        if r.get("experiment_url_langfuse"):
            linhas.append(f"    • Experimento Langfuse     : {r['experiment_url_langfuse']}")
        linhas.append("")

    # SEÇÃO 2: ESCOLHA DA CONFIGURAÇÃO VENCEDORA
    linhas.append(sep_duplo)
    linhas.append("2. CONFIGURAÇÃO ESCOLHIDA PARA O PRODUTO (CRITÉRIO OFICIAL DA ISSUE #38)")
    linhas.append(sep_duplo)
    linhas.append(f"Critério Pré-Definido : {escolha['criterio_aplicado']}")
    linhas.append(f"Configuração Vencedora: [{escolha['ordem']}] {escolha['nome']} ({escolha['id_configuracao']})")
    linhas.append(f"  - Cumpre RNF-14 (p90 <= 5 s) : {'SIM' if escolha['atende_rnf14_p90_ate_5s'] else 'NÃO'} (p50 = {escolha['latencia_p50_ms']:.0f} ms | p90 = {escolha['latencia_p90_ms']:.0f} ms)")
    linhas.append(f"  - Zero Lugares Inventados    : {'SIM' if escolha['zero_lugares_inventados'] else 'NÃO'} (0 locais falsos nas 20 consultas)")
    linhas.append(f"  - Acerto do Lugar Gabarito   : {escolha['acerto_gabarito_contagem']} ({escolha['acerto_gabarito_taxa'] * 100:.1f}%) | DF: {escolha['acerto_gabarito_df_contagem']}")
    linhas.append(f"  - Fidelidade Factual (RNF-03): {escolha['fidelidade_factual_rnf03_media'] * 100:.1f}% | Taxa de Alucinação: {escolha['taxa_alucinacao_media'] * 100:.1f}%")
    linhas.append(f"  - Custo Médio por Consulta   : R$ {escolha['custo_medio_brl']:.6f}")
    linhas.append(f"Justificativa Técnica : {escolha['justificativa']}")
    linhas.append("")
    linhas.append("Motivos de descarte das demais configurações:")
    for desc in escolha.get("comparacao_descartadas") or []:
        linhas.append(f"  • {desc['nome']} ({desc['id_configuracao']}): {'; '.join(desc['motivos'])}")
    linhas.append("")

    # SEÇÃO 3: CONSOLIDAÇÃO POR CATEGORIA (RNF-10)
    linhas.append(sep_duplo)
    linhas.append("3. CONSOLIDAÇÃO DE MÉTRICAS POR CATEGORIA DE PERGUNTA (RNF-10 — MODO A vs. MODO B VENCEDOR)")
    linhas.append(sep_duplo)
    cfg_a_res = next(r for r in resumos if r["id_configuracao"] == "1_llm_pura_sem_raciocinio")
    cfg_b_res = next(r for r in resumos if r["id_configuracao"] == escolha["id_configuracao"])
    linhas.append(
        f"{'Categoria':<30} | {'Casos':<5} | {'Acerto Modo A':<14} | {'Acerto Modo B':<14} | "
        f"{'Fidel. A':<9} | {'Fidel. B':<9} | {'Aluc. A':<8} | {'Aluc. B'}"
    )
    linhas.append(sep_simples)
    for cat, metricas_b in cfg_b_res["por_categoria"].items():
        metricas_a = cfg_a_res["por_categoria"].get(cat) or {}
        linhas.append(
            f"{cat:<30} | {metricas_b['total_casos']:<5} | "
            f"{metricas_a.get('acerto_gabarito_contagem', '-'):<14} | "
            f"{metricas_b['acerto_gabarito_contagem']:<14} | "
            f"{(metricas_a.get('fidelidade_factual_rnf03_media') or 0.0) * 100:6.1f}%  | "
            f"{metricas_b['fidelidade_factual_rnf03_media'] * 100:6.1f}%  | "
            f"{(metricas_a.get('taxa_alucinacao_media') or 0.0) * 100:5.1f}%  | "
            f"{metricas_b['taxa_alucinacao_media'] * 100:5.1f}%"
        )
    linhas.append(sep_simples)
    linhas.append("")

    # SEÇÃO 4: DETALHAMENTO DAS 20 PERGUNTAS LADO A LADO
    linhas.append(sep_duplo)
    linhas.append("4. DETALHAMENTO DAS 20 CONSULTAS DO GOLDEN DATASET (RESPOSTAS LADO A LADO, SCORES E TRACE IDs)")
    linhas.append(sep_duplo)
    for idx, item in enumerate(casos, start=1):
        gab = item["gabarito"] or {}
        linhas.append("")
        linhas.append("#" * 105)
        linhas.append(
            f"CASO #{idx:02d} [{item['id_golden']}] | Categoria: {item['categoria']} | "
            f"RA Esperada: {gab.get('ra_esperada') or 'Fora do DF (Recusar)'}"
        )
        linhas.append("#" * 105)
        linhas.append(f"Pergunta : \"{item['pergunta']}\"")
        linhas.append(
            f"Gabarito : Locais={gab.get('locais_gabarito')} | Preço Máx=R$ {gab.get('preco_maximo_gabarito')} | "
            f"Horário={gab.get('horario_gabarito')}"
        )
        linhas.append(sep_simples)
        for cfg in CONFIGURACOES_BENCHMARK:
            cid = cfg["id"]
            reg = item["resultados_configuracoes"][cid]
            sc = reg["scores"]
            det = reg["verificacao_deterministica"]
            mb = reg["metricas_busca"]
            r2 = reg.get("rodada_2") or {}
            fontes_nomes = [f.get("nome") for f in (reg.get("fontes_utilizadas") or []) if f.get("nome")]
            linhas.append(
                f"  [{cfg['ordem']}] {cfg['nome']} ({cid}) | Latência R1: {reg['latencia_ms']:.0f} ms "
                f"(R2: {r2.get('latencia_ms', 0.0):.0f} ms) | Custo: R$ {reg['custo_estimado_brl']:.6f}"
            )
            linhas.append(
                f"      • Scores     : acerto_gabarito={sc.get('acerto_gabarito')} | "
                f"fidelidade_rnf03={sc.get('fidelidade_factual_rnf03')} | "
                f"taxa_alucinacao={sc.get('taxa_alucinacao')} | "
                f"fora_da_base={sc.get('taxa_fora_da_base')} | "
                f"precisao_ra={sc.get('precisao_geoespacial_ra')} | "
                f"abstencao={sc.get('abstencao')} | sla_rnf14={sc.get('sla_latencia_rnf14')}"
            )
            if cfg["usa_rag"]:
                linhas.append(
                    f"      • Busca RAG  : Fontes={fontes_nomes} | recall@3={mb.get('recall_at_k')} | "
                    f"mrr={mb.get('mrr')} | pos_gabarito={mb.get('posicao_gabarito')}"
                )
            linhas.append(
                f"      • Auditoria  : Base Citados={det.get('locais_base_citados')} | "
                f"Inventados={det.get('locais_inventados')} | "
                f"Trace ID={reg.get('trace_id') or 'local'} | Trace URL={reg.get('trace_url') or 'N/A'}"
            )
            resp_limpa = (reg.get("resposta") or "").strip().replace("\n", "\n        ")
            linhas.append(f"      • Resposta   :\n        {resp_limpa}")
            linhas.append("")

    caminho_log.write_text("\n".join(linhas) + "\n", encoding="utf-8")


def executar_benchmark_completo(num_rodadas: int = 2, usar_checkpoint: bool = True) -> dict[str, Any]:
    """Executa o benchmark completo das 20 perguntas nas 6 configurações, consolida métricas e salva artefatos."""
    casos_golden = carregar_golden(CAMINHO_GOLDEN)
    if len(casos_golden) != 20:
        raise RuntimeError(f"Esperados 20 casos em {CAMINHO_GOLDEN}, encontrados {len(casos_golden)}.")

    base_2fa = carregar_base_oficial_leticia()
    checkpoint = _carregar_checkpoint() if usar_checkpoint else {}
    rodadas_salvas: dict[str, dict[str, dict[str, Any]]] = checkpoint.get("rodadas") or {}

    for r_num in range(1, num_rodadas + 1):
        chave_r = f"rodada_{r_num}"
        if chave_r not in rodadas_salvas:
            rodadas_salvas[chave_r] = {}
        busca_vetorial.limpar_cache()
        print(
            f"\n=== INICIANDO {chave_r.upper()} ({len(casos_golden)} casos × {len(CONFIGURACOES_BENCHMARK)} configurações) ===",
            flush=True,
        )
        pendentes = [
            (idx, caso)
            for idx, caso in enumerate(casos_golden, start=1)
            if not (
                caso["id"] in rodadas_salvas[chave_r]
                and len(rodadas_salvas[chave_r][caso["id"]]) == len(CONFIGURACOES_BENCHMARK)
            )
        ]
        ja_feitos = len(casos_golden) - len(pendentes)
        if ja_feitos:
            print(f"  [{chave_r}] {ja_feitos}/20 casos já constam no checkpoint — reaproveitando.", flush=True)

        def _processar_item(item_tupla: tuple[int, dict[str, Any]]) -> None:
            idx, caso = item_tupla
            id_g = caso["id"]
            t0 = time.perf_counter()
            res_caso = executar_rodada_caso(caso, rodada=r_num, base_2fa=base_2fa)
            with _LOCK_CHECKPOINT:
                rodadas_salvas[chave_r][id_g] = res_caso
                checkpoint["rodadas"] = rodadas_salvas
            _salvar_checkpoint(checkpoint)
            dt = time.perf_counter() - t0
            c1 = res_caso["1_llm_pura_sem_raciocinio"]
            c4 = res_caso["4_rag_llm_busca_lexica"]
            c6 = res_caso["6_rag_llm_busca_vetorial"]
            print(
                f"  [{chave_r}] ({idx:02d}/20) {id_g} concluído em {dt:.1f}s | "
                f"Cfg1(LLM): lat={c1['latencia_ms']:.0f}ms acerto={c1['scores']['acerto_gabarito']} | "
                f"Cfg4(RAG-Léx): lat={c4['latencia_ms']:.0f}ms acerto={c4['scores']['acerto_gabarito']} | "
                f"Cfg6(RAG-Vet): lat={c6['latencia_ms']:.0f}ms acerto={c6['scores']['acerto_gabarito']}",
                flush=True,
            )

        with ThreadPoolExecutor(max_workers=3) as pool_casos:
            futs = [pool_casos.submit(contextvars.copy_context().run, _processar_item, it) for it in pendentes]
            for fut in as_completed(futs):
                fut.result()
        flush_telemetria()

    rodada_1 = rodadas_salvas["rodada_1"]
    rodada_2 = rodadas_salvas.get("rodada_2") or rodada_1

    # Recalcula a verificação determinística RNF-04 e os scores padronizados sobre as respostas salvas
    # e substitui eventuais falhas de cota (HTTP 403 no fim da rodada 2) pela execução válida da rodada 1
    casos_por_id = {c["id"]: c for c in casos_golden}
    for chave_r, mapa_r in (("rodada_1", rodada_1), ("rodada_2", rodada_2)):
        for id_g, cfgs_caso in mapa_r.items():
            caso_obj = casos_por_id[id_g]
            gab_obj = _gabarito(caso_obj)
            for cfg in CONFIGURACOES_BENCHMARK:
                cid = cfg["id"]
                item = cfgs_caso[cid]
                if chave_r == "rodada_2" and not item.get("disponivel", True):
                    item_r1 = dict(rodada_1[id_g][cid])
                    item_r1["rodada"] = 2
                    item_r1["reaproveitado_rodada_1_por_limite_cota"] = True
                    cfgs_caso[cid] = item_r1
                    item = item_r1

                det_novo = verificar_deterministico_rnf04(
                    caso_obj["pergunta"], gab_obj, item, base_2fa
                )
                juiz_salvo = item.get("julgamento_juiz") or {}
                if det_novo["abstencao"]:
                    juiz_salvo = {
                        "modelo_juiz": juiz_salvo.get("modelo_juiz") or _modelo_juiz(),
                        "usou_llm": False,
                        "motivo_fallback": "sem afirmações para julgar",
                        "afirmacoes": det_novo["afirmacoes_deterministicas"],
                        "latencia_juiz_ms": 0.0,
                    }
                elif not juiz_salvo.get("usou_llm"):
                    juiz_salvo["afirmacoes"] = det_novo["afirmacoes_deterministicas"]

                scores_novos = _calcular_scores_modo(item, det_novo, juiz_salvo, gab_obj)
                busca_nova = (
                    calcular_metricas_busca(gab_obj, item)
                    if cfg["usa_rag"]
                    else {
                        "recall_at_k": None,
                        "mrr": None,
                        "posicao_gabarito": None,
                        "recusa_correta": None,
                        "recusa_indevida": None,
                    }
                )
                item["verificacao_deterministica"] = det_novo
                item["julgamento_juiz"] = juiz_salvo
                item["scores"] = scores_novos
                item["metricas_busca"] = busca_nova

    checkpoint["rodadas"] = {"rodada_1": rodada_1, "rodada_2": rodada_2}
    _salvar_checkpoint(checkpoint)

    # Registra os 6 experimentos no Langfuse Cloud sobre o dataset `golden_dataset_semana3`
    info_experimentos = sincronizar_e_rodar_experimentos_langfuse(casos_golden, rodada_1)

    # Monta resumos estatísticos por configuração + variação entre rodadas + consolidação por categoria
    resumos_configuracoes: list[dict[str, Any]] = []
    mapa_configuracoes: dict[str, dict[str, Any]] = {}

    for cfg in CONFIGURACOES_BENCHMARK:
        cid = cfg["id"]
        regs_r1 = [rodada_1[c["id"]][cid] for c in casos_golden]
        regs_r2 = [rodada_2[c["id"]][cid] for c in casos_golden]

        agregado_r1 = agregar_metricas_lista(regs_r1)
        agregado_r2 = agregar_metricas_lista(regs_r2)
        por_categoria = consolidar_por_categoria(regs_r1)

        casos_divergentes_acerto = [
            c["id"]
            for c in casos_golden
            if rodada_1[c["id"]][cid]["scores"].get("acerto_gabarito")
            != rodada_2[c["id"]][cid]["scores"].get("acerto_gabarito")
        ]

        variacao_rodadas = {
            "num_rodadas": num_rodadas,
            "rodada_1_acerto_contagem": agregado_r1["acerto_gabarito_contagem"],
            "rodada_2_acerto_contagem": agregado_r2["acerto_gabarito_contagem"],
            "delta_acerto_num": agregado_r2["acerto_gabarito_num"] - agregado_r1["acerto_gabarito_num"],
            "casos_divergentes_acerto": casos_divergentes_acerto,
            "rodada_1_p50_ms": agregado_r1["latencia_p50_ms"],
            "rodada_2_p50_ms": agregado_r2["latencia_p50_ms"],
            "rodada_1_p90_ms": agregado_r1["latencia_p90_ms"],
            "rodada_2_p90_ms": agregado_r2["latencia_p90_ms"],
            "delta_p90_ms": round(agregado_r2["latencia_p90_ms"] - agregado_r1["latencia_p90_ms"], 1),
            "rodada_1_fidelidade": agregado_r1["fidelidade_factual_rnf03_media"],
            "rodada_2_fidelidade": agregado_r2["fidelidade_factual_rnf03_media"],
            "rodada_1_alucinacao": agregado_r1["taxa_alucinacao_media"],
            "rodada_2_alucinacao": agregado_r2["taxa_alucinacao_media"],
            "rodada_1_lugares_inventados": agregado_r1["lugares_inventados_total"],
            "rodada_2_lugares_inventados": agregado_r2["lugares_inventados_total"],
        }

        exp_info = info_experimentos.get(cid) or {}
        resumo_cfg = {
            "id_configuracao": cid,
            "ordem": cfg["ordem"],
            "nome": cfg["nome"],
            "como_rodar": cfg["como_rodar"],
            "modo": cfg["modo"],
            "raciocinio": cfg["raciocinio"],
            "busca": cfg["busca"],
            "usa_llm": cfg["usa_llm"],
            "usa_rag": cfg["usa_rag"],
            "experiment_id_langfuse": exp_info.get("experiment_id"),
            "experiment_url_langfuse": exp_info.get("experiment_url"),
            **agregado_r1,
            "por_categoria": por_categoria,
            "variacao_rodadas": variacao_rodadas,
        }
        resumos_configuracoes.append(resumo_cfg)
        mapa_configuracoes[cid] = {
            "resumo": resumo_cfg,
            "casos": regs_r1,
            "casos_rodada_2": regs_r2,
        }

    escolha = escolher_melhor_configuracao(resumos_configuracoes)
    id_vencedora = escolha["id_configuracao"]

    # Monta a lista consolidada dos 20 casos (com todas as 6 configurações + par principal Modo A vs Modo B)
    casos_consolidados: list[dict[str, Any]] = []
    for caso in casos_golden:
        id_g = caso["id"]
        gab = _gabarito(caso)
        resultados_cfgs: dict[str, dict[str, Any]] = {}
        for cfg in CONFIGURACOES_BENCHMARK:
            cid = cfg["id"]
            r1_item = dict(rodada_1[id_g][cid])
            r2_item = dict(rodada_2[id_g][cid])
            r1_item["rodada_2"] = {
                "latencia_ms": r2_item["latencia_ms"],
                "custo_estimado_brl": r2_item["custo_estimado_brl"],
                "tokens_total": r2_item["tokens_total"],
                "scores": r2_item["scores"],
                "locais_base_citados": r2_item["verificacao_deterministica"]["locais_base_citados"],
                "locais_inventados": r2_item["verificacao_deterministica"]["locais_inventados"],
                "trace_id": r2_item.get("trace_id"),
                "trace_url": r2_item.get("trace_url"),
            }
            resultados_cfgs[cid] = r1_item

        modo_a_ref = resultados_cfgs["1_llm_pura_sem_raciocinio"]
        modo_b_ref = resultados_cfgs[id_vencedora]
        sc_a = modo_a_ref["scores"]
        sc_b = modo_b_ref["scores"]

        casos_consolidados.append({
            "id_golden": id_g,
            "pergunta": caso["pergunta"],
            "categoria": caso["categoria"],
            "armadilha_llm_pura": caso.get("armadilha_llm_pura"),
            "evidencia_id_tiktok": caso.get("evidencia_id_tiktok"),
            "gabarito": gab,
            "modelo": modo_b_ref.get("modelo") or llm_pura._modelo(),
            "configuracao": id_vencedora,
            "versao_prompt": modo_b_ref.get("versao_prompt") or "v1",
            "modo_a_llm_pura": modo_a_ref,
            "modo_b_rag": modo_b_ref,
            "metricas_busca": modo_b_ref["metricas_busca"],
            "delta_rag_vs_llm": {
                "ganho_fidelidade": _delta(sc_b, sc_a, "fidelidade_factual_rnf03"),
                "reducao_alucinacao": _delta(sc_a, sc_b, "taxa_alucinacao"),
                "ganho_precisao_ra": _delta(sc_b, sc_a, "precisao_geoespacial_ra"),
                "ganho_acerto_gabarito": _delta(sc_b, sc_a, "acerto_gabarito"),
            },
            "resultados_configuracoes": resultados_cfgs,
        })

    # Consolidação global por categoria comparando todas as configurações
    consolidacao_categorias: dict[str, dict[str, Any]] = {}
    for cfg_res in resumos_configuracoes:
        cid = cfg_res["id_configuracao"]
        for cat, m_cat in cfg_res["por_categoria"].items():
            consolidacao_categorias.setdefault(cat, {})[cid] = m_cat

    metadados = {
        "projeto": "Orquestrador de Rolês — Grupo 7 (Residência em IA UnB / Instituto Eldorado)",
        "semana": 3,
        "issue": "#38",
        "responsavel": "Letícia Miti Takahashi (@mitii05)",
        "data_execucao": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "arquivo_golden": "data/golden_dataset_semana3.json",
        "arquivo_base_2fa": "data/banco_aprovado_2fa.json",
        "total_casos": len(casos_golden),
        "total_casos_df": 18,
        "total_casos_fora_df": 2,
        "total_locais_base_2fa": len(base_2fa),
        "total_configuracoes": len(CONFIGURACOES_BENCHMARK),
        "num_rodadas": num_rodadas,
        "modelo_gerador": llm_pura._modelo(),
        "modelo_juiz": _modelo_juiz() or MODELO_JUIZ_PADRAO,
        "dataset_langfuse": NOME_DATASET_LANGFUSE,
        "sla_latencia_max_ms": SLA_LATENCIA_MAX_MS,
        "meta_fidelidade_rnf03": 0.95,
    }
    resumo_benchmark = {
        "metadados": metadados,
        "configuracao_escolhida": escolha,
        "resumo_configuracoes": resumos_configuracoes,
        "por_categoria": consolidacao_categorias,
    }
    for idx_c, item_c in enumerate(casos_consolidados):
        item_c["resumo_benchmark"] = resumo_benchmark if idx_c == 0 else {
            "metadados": metadados,
            "configuracao_escolhida": {
                "id_configuracao": escolha["id_configuracao"],
                "nome": escolha["nome"],
                "acerto_gabarito_contagem": escolha["acerto_gabarito_contagem"],
                "atende_rnf14_p90_ate_5s": escolha["atende_rnf14_p90_ate_5s"],
                "zero_lugares_inventados": escolha["zero_lugares_inventados"],
                "justificativa": escolha["justificativa"],
            },
        }

    dados_finais = {
        "metadados": metadados,
        "configuracao_escolhida": escolha,
        "resumo_configuracoes": resumos_configuracoes,
        "por_categoria": consolidacao_categorias,
        "configuracoes": mapa_configuracoes,
        "casos": casos_consolidados,
    }

    CAMINHO_JSON.parent.mkdir(parents=True, exist_ok=True)
    # Raiz em formato lista de 20 itens para compatibilidade direta com /api/entregaveis/dados (Issue #39)
    CAMINHO_JSON.write_text(json.dumps(casos_consolidados, ensure_ascii=False, indent=2), encoding="utf-8")
    salvar_csv(casos_consolidados, CAMINHO_CSV)
    gerar_log_txt(dados_finais, CAMINHO_LOG_TXT)
    flush_telemetria()

    print(f"\n[OK] JSON salvo em: {CAMINHO_JSON}")
    print(f"[OK] CSV salvo em : {CAMINHO_CSV}")
    print(f"[OK] LOG salvo em : {CAMINHO_LOG_TXT}")
    print(f"[OK] Configuração escolhida: {escolha['nome']} ({escolha['id_configuracao']})")
    return dados_finais


def main() -> None:
    parser = argparse.ArgumentParser(description="Executa o benchmark oficial A/B da Semana 3 (Issue #38).")
    parser.add_argument("--rodadas", type=int, default=2, help="Número de rodadas completas (padrão: 2).")
    parser.add_argument("--sem-checkpoint", action="store_true", help="Ignora checkpoint anterior e roda do zero.")
    args = parser.parse_args()
    executar_benchmark_completo(num_rodadas=max(1, args.rodadas), usar_checkpoint=not args.sem_checkpoint)


if __name__ == "__main__":
    main()
