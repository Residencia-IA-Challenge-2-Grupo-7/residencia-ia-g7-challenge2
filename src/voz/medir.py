"""Mede um provedor de transcrição nas gravações de teste (ADR 0006, "Como vamos validar").

Arquivos: <pasta>/[mN/]<ID>[-qualquer].{wav,m4a,mp3,ogg,opus,webm,aac,flac}, com ID do gabarito (D01, G02…).
Saídas em eval/resultados/: voz-<rótulo>-<provedor>-<modelo>-<data>.json (métricas e cada frase) e
transcricoes-....json ({id: texto}), que alimenta `python -m interpretador avaliar --transcricoes`.
Os áudios não são copiados nem apagados aqui; ficam em data/raw/ (fora do git) até a medição final.
"""
import json
import math
import platform
import re
import statistics
import time
from datetime import datetime
from pathlib import Path

from interpretador.avaliar import RESULTADOS, carregar

from .transcrever import CFG, carregar as carregar_modelo, modelo_padrao, transcrever
from .wer import criticos_faltando, normalizar, wer

EXTENSOES = {".wav", ".m4a", ".mp3", ".ogg", ".opus", ".webm", ".aac", ".flac", ".aiff"}


def _p(xs, q):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, math.ceil(q * len(xs)) - 1)] if xs else None


def audios(pasta: Path) -> list[tuple[str, str, Path]]:
    """(id da frase, falante, caminho)."""
    out = []
    for a in sorted(pasta.rglob("*")):
        # D01.m4a, D01-qualquer.m4a ou C1-D01.m4a (prefixo de quem gravou)
        m = re.search(r"(?:^|[-_ ])([A-Z]\d{2})(?=[-_. ]|$)", a.stem + ".")
        if a.suffix.lower() in EXTENSOES and m:
            falante = a.parent.name if re.fullmatch(r"m\d+", a.parent.name) else pasta.name
            out.append((m.group(1), falante, a))
    return out


def custo(provedor: str, duracao_s: float | None) -> float:
    if provedor != "groq" or duracao_s is None:
        return 0.0
    g = CFG["groq"]
    return max(duracao_s, g["minimo_s"]) / 3600 * g["preco_hora_usd"]


def medir(pasta: Path, provedor: str | None = None, modelo: str | None = None, usar_prompt: bool = True,
          rotulo: str | None = None) -> dict:
    provedor = provedor or CFG["transcricao"]["provedor"]
    modelo = modelo or modelo_padrao(provedor)
    frases = {f["id"]: f for f in carregar()[0]}
    lista = [x for x in audios(pasta) if x[0] in frases]
    if not lista:
        raise SystemExit(f"Nenhum áudio com ID do gabarito em {pasta}")
    carregar_modelo(provedor, modelo)
    transcrever(lista[0][2], provedor, modelo, usar_prompt=usar_prompt)  # aquecimento, fora da conta
    linhas = []
    pausa = CFG["groq"]["pausa_medicao_s"] if provedor == "groq" else 0
    for id_, falante, arq in lista:
        if pausa:
            time.sleep(pausa)
        f = frases[id_]
        t = transcrever(arq, provedor, modelo, usar_prompt=usar_prompt)
        e, n = wer(f["texto"], t.texto)
        falta = criticos_faltando(f["criticos"], t.texto)
        linhas.append({"id": id_, "falante": falante, "arquivo": arq.name, "referencia": f["texto"],
                       "transcricao": t.texto, "erros": e, "palavras": n, "wer": e / n if n else 0,
                       "criticos": len(f["criticos"]), "criticos_faltando": falta,
                       "latencia_s": t.latencia_s, "duracao_s": t.duracao_s, "custo_usd": custo(provedor, t.duracao_s)})
        print(f"{e / n:5.0%} {t.latencia_s:5.2f}s {id_} {falante}: {t.texto}" + (f"  [faltou: {falta}]" if falta else ""),
              flush=True)
    lat = [l["latencia_s"] for l in linhas]
    dur = [l["duracao_s"] for l in linhas if l["duracao_s"]]
    crit = sum(l["criticos"] for l in linhas)
    r = {
        "rotulo": rotulo or pasta.name, "provedor": provedor, "modelo": modelo, "prompt": usar_prompt,
        "maquina": f"{platform.system()} {platform.machine()} {platform.processor()}".strip(),
        "quando": datetime.now().isoformat(timespec="seconds"), "audios": len(linhas),
        "falantes": sorted({l["falante"] for l in linhas}),
        "wer": sum(l["erros"] for l in linhas) / sum(l["palavras"] for l in linhas),
        "erro_criticos": sum(len(l["criticos_faltando"]) for l in linhas) / crit if crit else None,
        "frases_com_critico_errado": sum(bool(l["criticos_faltando"]) for l in linhas),
        "latencia_p50_s": statistics.median(lat), "latencia_p90_s": _p(lat, 0.9),
        "fator_tempo_real": (sum(lat) / sum(dur)) if dur and len(dur) == len(lat) else None,
        "custo_total_usd": sum(l["custo_usd"] for l in linhas),
        "linhas": linhas,
    }
    RESULTADOS.mkdir(parents=True, exist_ok=True)
    nome = (f"{r['rotulo']}-{provedor}-{modelo.split('/')[-1]}{'' if usar_prompt else '-sem-prompt'}-"
            f"{r['quando'][:10]}")
    (RESULTADOS / f"voz-{nome}.json").write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    textos = {}
    for l in linhas:
        textos.setdefault(l["id"], l["transcricao"])
    (RESULTADOS / f"transcricoes-{nome}.json").write_text(json.dumps(textos, ensure_ascii=False, indent=1),
                                                          encoding="utf-8")
    r["arquivo"] = str(RESULTADOS / f"voz-{nome}.json")
    return r


def resumo_md(r: dict) -> str:
    pct = lambda x: "—" if x is None else f"{100 * x:.1f}%"
    return (f"| {r['provedor']} `{r['modelo']}`{'' if r['prompt'] else ' (sem prompt)'} | {r['rotulo']} | "
            f"{r['audios']} | {pct(r['wer'])} | {pct(r['erro_criticos'])} ({r['frases_com_critico_errado']} frases) | "
            f"{r['latencia_p50_s']:.2f} / {r['latencia_p90_s']:.2f} s | "
            f"{'—' if r['fator_tempo_real'] is None else f'{r['fator_tempo_real']:.2f}'} | "
            f"US$ {r['custo_total_usd']:.4f} |")


CABECALHO = ("| Provedor e modelo | Áudios | N | WER | Erro nos termos críticos | Latência p50 / p90 | "
             "Tempo ÷ duração | Custo |\n|---|---|---|---|---|---|---|---|")
