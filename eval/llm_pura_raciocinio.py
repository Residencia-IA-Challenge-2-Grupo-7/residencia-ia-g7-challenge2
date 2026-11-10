"""Compara a LLM pura (Modo A, ADR 0010) sem raciocínio e com raciocínio alto, nas mesmas 8 perguntas.

Duas rodadas, com a ordem dos modos alternada a cada pergunta. Precisa da OPENROUTER_API_KEY no .env.
Relato: docs/experimentos/2026-11-10-llm-pura-raciocinio.md

    PYTHONPATH=. python eval/llm_pura_raciocinio.py eval/resultados/llm-pura-raciocinio-<modelo>-<data>.json
"""
import json
import sys
import time

sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8")
from src.rag.llm_pura import gerar_resposta_llm_pura  # noqa: E402

PERGUNTAS = [
    ("hamburguer_tagua", "Onde comer hambúrguer artesanal ou rodízio de mini hambúrgueres em Taguatinga com amigos?"),
    ("caldos_brinquedoteca", "Onde tem rodízio de caldos com brinquedoteca em Águas Claras e quanto custa?"),
    ("cafe_asa_norte", "Quero um café calmo para conversar na Asa Norte. Qual você indica e quanto custa?"),
    ("sushi_30", "Sushi barato até 30 reais por pessoa na Asa Norte?"),
    ("domingo_manha", "Onde tomar café da manhã no domingo cedo no Plano Piloto?"),
    ("ceilandia_musica", "Bar com música ao vivo em Ceilândia na sexta à noite?"),
    ("copacabana", "Onde jantar em Copacabana?"),
    ("luxo_gratis", "Restaurante de luxo grátis em Brasília?"),
]
MODOS = ["desligado", "high"]
saida = sys.argv[1]
resultados = []
for rodada in (1, 2):
    for i, (pid, pergunta) in enumerate(PERGUNTAS):
        ordem = MODOS if (i + rodada) % 2 == 0 else MODOS[::-1]
        for modo in ordem:
            t0 = time.perf_counter()
            r = gerar_resposta_llm_pura(pergunta, usar_cache=False, registrar=False, raciocinio=modo)
            r.update(id=pid, rodada=rodada, modo_raciocinio=modo, parede_s=round(time.perf_counter() - t0, 2))
            resultados.append(r)
            print(f"r{rodada} {pid:22} {modo:9} {r['latencia_ms']:8.0f} ms  raciocinio={r['tokens_raciocinio']:5} "
                  f"saida={r['tokens_saida']:5} disp={r['disponivel']} {r['erro'] or ''}", flush=True)
            with open(saida, "w", encoding="utf-8") as f:
                json.dump(resultados, f, ensure_ascii=False, indent=1)
print("fim")
