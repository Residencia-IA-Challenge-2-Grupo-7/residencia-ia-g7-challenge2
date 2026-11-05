"""Mede o interpretador no conjunto de frases com gabarito (ADR 0007, "Como vamos validar").

Métricas: acerto da intenção, acerto dos campos, frases inteiramente certas (RNF-08: disponibilidade e gastos),
perguntas certas, sigilo, latência p50/p90 e custo. Com --transcricoes, mede a partir do texto transcrito (voz).
"""
import json
import math
import statistics
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

from .config import EVAL
from .esquema import Intencao
from .interpretar import interpretar

FRASES = EVAL / "interpretador" / "frases.jsonl"
SALA = EVAL / "interpretador" / "sala.json"
RESULTADOS = EVAL / "resultados"


def carregar(ids: list[str] | None = None) -> tuple[list[dict], dict]:
    frases = [json.loads(l) for l in FRASES.read_text(encoding="utf-8").splitlines() if l.strip()]
    if ids:
        frases = [f for f in frases if f["id"] in ids]
    return frases, json.loads(SALA.read_text(encoding="utf-8"))


def comparavel(i: Intencao) -> dict:
    """Forma da intenção prevista que se compara com o gabarito."""
    d = {"tipo": i.tipo, "destino": i.destino}
    if i.motivo_pergunta:
        d["pergunta"] = i.motivo_pergunta
    f = lambda x: x.strftime("%Y-%m-%d %H:%M")
    d["janelas"] = sorted([f(j.inicio), f(j.fim), j.disponivel] for j in i.janelas)
    d["valor"] = float(i.valor) if i.valor is not None else None
    d["pagador"] = i.pagador
    d["de"] = i.periodo_de.isoformat() if i.periodo_de else None
    d["ate"] = i.periodo_ate.isoformat() if i.periodo_ate else None
    d["tipo_role"] = i.tipo_role
    d["convidados"] = sorted(i.convidados)
    if i.consulta:
        c = i.consulta
        d |= {"tipos_role": sorted(c.tipos_role), "ras": sorted(c.ras),
              "teto": float(c.teto_pessoa) if c.teto_pessoa is not None else None, "exigir": sorted(c.exigir),
              "janela_inicio": f(c.janela.inicio) if c.janela else None}
    return d


def _campos(esp: dict, prev: dict) -> list[tuple[str, bool]]:
    out = []
    for k, v in esp.items():
        if k == "tipo":
            continue
        pv = prev.get(k)
        if k == "janelas":
            v = sorted(v)
        if k == "pergunta" or "pergunta" in esp:
            out.append((k, pv == v))
        else:
            out.append((k, pv == v and "pergunta" not in prev))
    return out


def comparar(esperado: list[dict], previsto: list[dict]) -> dict:
    tipos_ok = Counter(e["tipo"] for e in esperado) == Counter(p["tipo"] for p in previsto)
    livres = list(previsto)
    campos = []
    for e in esperado:
        candidatos = [p for p in livres if p["tipo"] == e["tipo"]]
        if not candidatos:
            campos += [(k, False) for k in e if k != "tipo"]
            continue
        melhor = max(candidatos, key=lambda p: sum(ok for _, ok in _campos(e, p)))
        livres.remove(melhor)
        campos += _campos(e, melhor)
    return {"intencao_ok": tipos_ok, "campos": campos,
            "frase_ok": tipos_ok and all(ok for _, ok in campos)}


def limite_inferior(k: int, n: int, conf: float = 0.95) -> float:
    """Limite inferior de Clopper-Pearson (bilateral), por bisseção na cauda binomial."""
    if n == 0 or k == 0:
        return 0.0
    alvo = (1 - conf) / 2
    cauda = lambda p: sum(math.comb(n, i) * p**i * (1 - p)**(n - i) for i in range(k, n + 1))
    lo, hi = 0.0, k / n
    for _ in range(60):
        mid = (lo + hi) / 2
        if cauda(mid) < alvo:
            lo = mid
        else:
            hi = mid
    return lo


def _p(xs: list[float], q: float) -> float:
    xs = sorted(xs)
    return xs[min(len(xs) - 1, math.ceil(q * len(xs)) - 1)] if xs else float("nan")


def avaliar(ids=None, transcricoes: Path | None = None, rotulo: str = "texto", modelo: str | None = None,
            pausa_s: float = 0.0) -> dict:
    from .llm import OpenRouter

    frases, sala = carregar(ids)
    agora = datetime.fromisoformat(sala["agora"])
    textos = json.loads(transcricoes.read_text(encoding="utf-8")) if transcricoes else {}
    llm = OpenRouter(modelo)
    linhas = []
    for f in frases:
        texto = textos.get(f["id"], f["texto"]) if transcricoes else f["texto"]
        if transcricoes and f["id"] not in textos:
            continue
        r = interpretar(texto, contexto=f["contexto"], autor=f["autor"], membros=sala["membros"], agora=agora,
                        origem="voz" if transcricoes else "texto", llm=llm)
        prev = [comparavel(i) for i in r.intencoes]
        c = comparar(f["esperado"], prev)
        linhas.append({"id": f["id"], "categoria": f["categoria"], "texto": texto, "esperado": f["esperado"],
                       "previsto": prev, "erro": r.erro, "latencia_s": r.latencia_s, "custo_usd": r.custo_usd,
                       "tokens": [r.tokens_entrada, r.tokens_saida], "modelo": r.modelo, **c})
        marca = "ok " if c["frase_ok"] else "ERR"
        print(f"{marca} {f['id']} {r.latencia_s:5.2f}s  {texto}", flush=True)
        if pausa_s:
            time.sleep(pausa_s)
    return resumir(linhas, rotulo, llm.modelos[0])


def resumir(linhas: list[dict], rotulo: str, modelo: str) -> dict:
    n = len(linhas)
    rnf08 = [l for l in linhas if any(e["tipo"] in ("disponibilidade", "gasto") for e in l["esperado"])]
    perg = [l for l in linhas if any("pergunta" in e for e in l["esperado"])]
    sigilo = [l for l in linhas if l["id"] in ("O04", "X02")]
    campos = [ok for l in linhas for _, ok in l["campos"]]
    lat = [l["latencia_s"] for l in linhas if l["latencia_s"] is not None]
    custo = [l["custo_usd"] for l in linhas if l["custo_usd"] is not None]
    k08 = sum(l["frase_ok"] for l in rnf08)
    por_cat = {}
    for l in linhas:
        a = por_cat.setdefault(l["categoria"], [0, 0])
        a[0] += l["frase_ok"]
        a[1] += 1
    return {
        "rotulo": rotulo, "modelo": modelo, "quando": datetime.now().isoformat(timespec="seconds"), "frases": n,
        "intencao": sum(l["intencao_ok"] for l in linhas) / n if n else None,
        "campos": sum(campos) / len(campos) if campos else None,
        "frases_certas": sum(l["frase_ok"] for l in linhas) / n if n else None,
        "rnf08": {"certas": k08, "total": len(rnf08), "acerto": k08 / len(rnf08) if rnf08 else None,
                  "limite_inferior_95": limite_inferior(k08, len(rnf08))},
        "perguntas": f"{sum(l['frase_ok'] for l in perg)}/{len(perg)}",
        "sigilo": f"{sum(l['frase_ok'] for l in sigilo)}/{len(sigilo)}",
        "por_categoria": {k: f"{a}/{b}" for k, (a, b) in sorted(por_cat.items())},
        "latencia_p50_s": statistics.median(lat) if lat else None, "latencia_p90_s": _p(lat, 0.9),
        "custo_total_usd": sum(custo) if custo else None,
        "custo_por_frase_usd": sum(custo) / len(custo) if custo else None,
        "falhas_llm": sum(1 for l in linhas if l["erro"]),
        "linhas": linhas,
    }


def gravar(r: dict) -> Path:
    RESULTADOS.mkdir(parents=True, exist_ok=True)
    nome = f"interpretador-{r['rotulo']}-{r['modelo'].split('/')[-1]}-{r['quando'][:10]}"
    (RESULTADOS / f"{nome}.json").write_text(json.dumps(r, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    return RESULTADOS / f"{nome}.json"


def resumo_md(r: dict) -> str:
    pct = lambda x: "—" if x is None else f"{100 * x:.1f}%"
    s = r["rnf08"]
    erros = [l for l in r["linhas"] if not l["frase_ok"]]
    custo = "—" if r["custo_por_frase_usd"] is None else f"US$ {r['custo_por_frase_usd']:.6f}"
    linhas = [
        f"| Modelo | `{r['modelo']}` |", f"| Entrada | {r['rotulo']} |", f"| Frases | {r['frases']} |",
        f"| Intenção certa | {pct(r['intencao'])} |", f"| Campos certos | {pct(r['campos'])} |",
        f"| Frases inteiramente certas | {pct(r['frases_certas'])} |",
        f"| **RNF-08** (disponibilidade e gastos) | {s['certas']}/{s['total']} = {pct(s['acerto'])}; "
        f"limite inferior 95%: {pct(s['limite_inferior_95'])} |",
        f"| Perguntas certas | {r['perguntas']} |", f"| Sigilo (O04, X02) | {r['sigilo']} |",
        f"| Latência p50 / p90 | {r['latencia_p50_s'] or 0:.2f} s / {r['latencia_p90_s'] or 0:.2f} s |",
        f"| Custo por frase | {custo} |",
        f"| Falhas do LLM | {r['falhas_llm']} |",
    ]
    out = "| Métrica | Valor |\n|---|---|\n" + "\n".join(linhas)
    out += "\n\nPor categoria: " + ", ".join(f"{k} {v}" for k, v in r["por_categoria"].items())
    if erros:
        out += "\n\nErros:\n" + "\n".join(f"- {l['id']} \"{l['texto']}\": campos errados "
                                          f"{[k for k, ok in l['campos'] if not ok] or 'intenções'}" for l in erros)
    return out
