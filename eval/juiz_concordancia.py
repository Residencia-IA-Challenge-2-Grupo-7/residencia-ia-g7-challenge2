"""Julga de novo, com outro juiz, as respostas da rodada 2 do benchmark da semana 3 e compara com o MiMo (ADR 0014).

A rodada 2 foi julgada pelo `xiaomi/mimo-v2.6-pro` com a versão atual do prompt do juiz nas 6 configurações. Este
script passa as mesmas respostas, com os mesmos documentos e a mesma verificação em código, pelo juiz atual
(`JUIZ_LLM_MODELO` ou `MODELO_JUIZ_PADRAO`) e grava, por resposta, os vereditos e as notas dos dois juízes.

Só entram as respostas em que o MiMo foi chamado; recusas e "não sei" não gastam chamada em nenhum dos dois.
Precisa da OPENROUTER_API_KEY no .env.

    PYTHONPATH=. python eval/juiz_concordancia.py eval/resultados/juiz-<modelo>-vs-mimo-<data>.json
"""
import json
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8")
from src.telemetria.evals_semana3 import (  # noqa: E402
    _calcular_scores_modo,
    _modelo_juiz,
    julgar_com_llm_judge,
)
from src.telemetria.telemetria import carregar_base_oficial_leticia  # noqa: E402

RESULTADOS = Path("data/resultados_benchmark_semana3.json")
NOTAS = ("fidelidade_factual_rnf03", "taxa_alucinacao", "taxa_fora_da_base")


def p90(valores):
    return statistics.quantiles(valores, n=10)[-1] if len(valores) > 1 else (valores[0] if valores else 0.0)


def casos_rodada_2(dados: list[dict]) -> list[dict]:
    """Uma entrada por (pergunta, configuração): a resposta da rodada 2 com as fontes e os guardrails da rodada 1.

    A busca é determinística (as fontes das duas rodadas são as mesmas); só a geração foi repetida."""
    casos = []
    for item in dados:
        for id_cfg, cfg in item["resultados_configuracoes"].items():
            r2 = cfg.get("rodada_2") or {}
            base = {k: v for k, v in cfg.items() if k != "rodada_2"}
            resultado = {**base, **{k: r2[k] for k in ("resposta", "latencia_ms", "tokens_total") if k in r2},
                         "rodada": 2}
            casos.append({
                "id_golden": item["id_golden"], "configuracao": id_cfg, "pergunta": item["pergunta"],
                "gabarito": item["gabarito"], "resultado": resultado,
                "det": r2["verificacao_deterministica"], "juiz_mimo": r2["julgamento_juiz"],
                "scores_mimo": r2["scores"],
            })
    return casos


def main(saida: str) -> None:
    dados = json.loads(RESULTADOS.read_text(encoding="utf-8"))
    base = carregar_base_oficial_leticia()
    todos = casos_rodada_2(dados)
    julgaveis = [c for c in todos if c["juiz_mimo"].get("usou_llm")]
    modelo = _modelo_juiz()
    print(f"{len(todos)} respostas na rodada 2; {len(julgaveis)} julgadas pelo MiMo. Juiz novo: {modelo}")

    def julgar(c):
        juiz = julgar_com_llm_judge(c["pergunta"], c["gabarito"], c["resultado"], c["det"], base)
        return c, juiz

    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=8) as pool:
        pares = list(pool.map(julgar, julgaveis))
    duracao = time.perf_counter() - t0

    linhas = []
    for c, juiz in pares:
        recalc_mimo = _calcular_scores_modo(c["resultado"], c["det"], c["juiz_mimo"], c["gabarito"])
        novo = _calcular_scores_modo(c["resultado"], c["det"], juiz, c["gabarito"])
        linhas.append({
            "id_golden": c["id_golden"], "configuracao": c["configuracao"],
            "mimo": {"notas": {n: c["scores_mimo"].get(n) for n in NOTAS},
                     "notas_recalculadas": {n: recalc_mimo.get(n) for n in NOTAS},
                     "afirmacoes": c["juiz_mimo"].get("afirmacoes"),
                     "latencia_ms": c["juiz_mimo"].get("latencia_juiz_ms"),
                     "custo_usd": c["juiz_mimo"].get("custo_usd"), "tokens": c["juiz_mimo"].get("tokens_total")},
            "novo": {"modelo": juiz.get("modelo_juiz"), "usou_llm": juiz.get("usou_llm"),
                     "motivo_fallback": juiz.get("motivo_fallback"), "notas": {n: novo.get(n) for n in NOTAS},
                     "afirmacoes": juiz.get("afirmacoes"), "resumo": juiz.get("resumo_juiz"),
                     "latencia_ms": juiz.get("latencia_juiz_ms"), "custo_usd": juiz.get("custo_usd"),
                     "tokens": juiz.get("tokens_total")},
        })

    ok = [l for l in linhas if l["novo"]["usou_llm"]]
    reproduz = sum(1 for l in linhas if l["mimo"]["notas"] == l["mimo"]["notas_recalculadas"])

    def contradiz(notas):
        return (notas.get("taxa_alucinacao") or 0) > 0

    def fiel(notas):
        return notas.get("fidelidade_factual_rnf03") == 1.0

    por_cfg = {}
    for l in ok:
        g = por_cfg.setdefault(l["configuracao"], {"n": 0, **{f"{j}_{n}": [] for j in ("mimo", "novo") for n in NOTAS}})
        g["n"] += 1
        for j in ("mimo", "novo"):
            for n in NOTAS:
                if l[j]["notas"].get(n) is not None:
                    g[f"{j}_{n}"].append(l[j]["notas"][n])
    tabela = {cfg: {"respostas": g["n"],
                    **{k: round(statistics.mean(v), 4) if v else None for k, v in g.items() if k != "n"}}
              for cfg, g in sorted(por_cfg.items())}

    lat_novo = [l["novo"]["latencia_ms"] / 1000 for l in ok]
    lat_mimo = [l["mimo"]["latencia_ms"] / 1000 for l in ok if l["mimo"]["latencia_ms"]]
    resumo = {
        "juiz_novo": modelo,
        "juiz_antigo": "xiaomi/mimo-v2.6-pro",
        "data": time.strftime("%Y-%m-%d %H:%M"),
        "respostas_rodada_2": len(todos),
        "julgadas_pelo_mimo": len(julgaveis),
        "julgadas_pelo_novo": len(ok),
        "falhas_do_novo": {l["id_golden"] + "/" + l["configuracao"]: l["novo"]["motivo_fallback"]
                           for l in linhas if not l["novo"]["usou_llm"]},
        "notas_mimo_reproduzidas_pelo_codigo": f"{reproduz} de {len(linhas)}",
        "concordancia_contradicao": f"{sum(1 for l in ok if contradiz(l['mimo']['notas']) == contradiz(l['novo']['notas']))} de {len(ok)}",
        "contradicao_so_no_mimo": [f"{l['id_golden']}/{l['configuracao']}" for l in ok
                                   if contradiz(l["mimo"]["notas"]) and not contradiz(l["novo"]["notas"])],
        "contradicao_so_no_novo": [f"{l['id_golden']}/{l['configuracao']}" for l in ok
                                   if contradiz(l["novo"]["notas"]) and not contradiz(l["mimo"]["notas"])],
        "concordancia_fidelidade_total": f"{sum(1 for l in ok if fiel(l['mimo']['notas']) == fiel(l['novo']['notas']))} de {len(ok)}",
        "diferenca_media_absoluta_fidelidade": round(statistics.mean(
            abs((l["mimo"]["notas"]["fidelidade_factual_rnf03"] or 0) - (l["novo"]["notas"]["fidelidade_factual_rnf03"] or 0))
            for l in ok), 4) if ok else None,
        "medias_por_configuracao": tabela,
        "custo_total_usd": {"mimo": round(sum(l["mimo"]["custo_usd"] or 0 for l in ok), 5),
                            "novo": round(sum(l["novo"]["custo_usd"] or 0 for l in ok), 5)},
        "latencia_s": {"mimo_p50": round(statistics.median(lat_mimo), 2) if lat_mimo else None,
                       "mimo_p90": round(p90(lat_mimo), 2) if lat_mimo else None,
                       "novo_p50": round(statistics.median(lat_novo), 2) if lat_novo else None,
                       "novo_p90": round(p90(lat_novo), 2) if lat_novo else None},
        "tokens_medianos": {"mimo": statistics.median([l["mimo"]["tokens"] or 0 for l in ok]) if ok else None,
                            "novo": statistics.median([l["novo"]["tokens"] or 0 for l in ok]) if ok else None},
        "duracao_execucao_s": round(duracao, 1),
    }
    Path(saida).parent.mkdir(parents=True, exist_ok=True)
    Path(saida).write_text(json.dumps({"resumo": resumo, "respostas": linhas}, ensure_ascii=False, indent=2),
                           encoding="utf-8")
    print(json.dumps(resumo, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else f"eval/resultados/juiz-glm-5.3-flash-vs-mimo-{time.strftime('%Y-%m-%d')}.json")
