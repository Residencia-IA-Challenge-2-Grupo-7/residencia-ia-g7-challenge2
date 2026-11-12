"""Roda o comparativo A/B (issue #34) em todos os casos do golden dataset e grava o resultado bruto em JSON.

Sem cache e sem registrar métricas, para medir latência e custo de verdade. Precisa da OPENROUTER_API_KEY no
.env; sem ela, os dois modos saem marcados com `disponivel: false`. A avaliação (alucinação, fidelidade, acerto
de RA e preço) é das issues #36 e #38, sobre este arquivo.

    PYTHONPATH=. python eval/comparativo_ab.py eval/resultados/comparativo-ab-<data>.json [low|medium|high]

O terceiro argumento, opcional, liga o raciocínio do modelo nos dois modos (padrão: desligado).
"""
import json
import statistics
import sys
import time

sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8")
from src.rag.comparador_ab import executar_comparacao_ab, listar_golden  # noqa: E402
from src.telemetria.telemetria import flush_telemetria  # noqa: E402


def p90(valores):
    return statistics.quantiles(valores, n=10)[-1] if len(valores) > 1 else (valores[0] if valores else 0.0)


saida = sys.argv[1]
raciocinio = sys.argv[2] if len(sys.argv) > 2 else None
resultados = []
for caso in listar_golden():
    t0 = time.perf_counter()
    r = executar_comparacao_ab("", caso["id"], usar_cache=False, registrar=False, raciocinio=raciocinio)
    r["latencia_total_ms"] = round((time.perf_counter() - t0) * 1000, 1)
    resultados.append(r)
    b = r["modo_b_rag"]
    print(f"{caso['id']}: A {r['modo_a_llm_pura']['latencia_ms']:.0f} ms | B {b['latencia_ms']:.0f} ms | "
          f"fontes B: {[f['nome'] for f in b['fontes_utilizadas']]} | gabarito: {r['gabarito']['locais_gabarito']}")
flush_telemetria()

with open(saida, "w", encoding="utf-8") as f:
    json.dump(resultados, f, ensure_ascii=False, indent=1)
for modo in ("modo_a_llm_pura", "modo_b_rag"):
    lat = [r[modo]["latencia_ms"] for r in resultados]
    print(f"{modo}: p50 {statistics.median(lat):.0f} ms, p90 {p90(lat):.0f} ms, "
          f"acima de 5 s: {sum(x > 5000 for x in lat)} de {len(lat)}")
