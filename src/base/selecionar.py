"""Etapa 2: deduplicar e sortear por estrato (região × categoria), sem escolha humana.

Grava sorteio.csv com a ordem completa de cada estrato (a reposição pega o próximo da fila) e
selecionados.csv com os sorteados.
"""
import csv
import hashlib
import json
import math
import random
import re
import unicodedata
from collections import defaultdict

from .config import CFG, PAGINAS, PROC
from .regioes import REGIOES

ESTRATOS = ["restaurante", "bar", "cafe_lanchonete_sorveteria", "ar_livre_gratuito", "local_evento"]


def lugar_id(overture_id: str) -> str:
    """Identificador estável, derivado do ID da Overture."""
    return "lug-" + hashlib.sha1(overture_id.encode()).hexdigest()[:8]


def _nome_chave(nome: str) -> str:
    s = unicodedata.normalize("NFD", nome.casefold())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", "", s)


def _distancia_m(a, b) -> float:
    dy = (float(a["lat"]) - float(b["lat"])) * 111_320
    dx = (float(a["lon"]) - float(b["lon"])) * 111_320 * math.cos(math.radians(float(a["lat"])))
    return math.hypot(dx, dy)


def elegiveis(linhas: list[dict]) -> tuple[list[dict], dict]:
    conf_min = CFG["pipeline"]["confianca_min"]
    motivos = defaultdict(int)
    ok = []
    for r in linhas:
        if not r["site"]:
            motivos["sem_site"] += 1
        elif float(r["confianca"]) < conf_min:
            motivos["confianca_baixa"] += 1
        else:
            ok.append(r)
    # Um lugar por domínio: filiais de rede compartilham o site. Fica o de maior confiança.
    ok.sort(key=lambda r: (-float(r["confianca"]), r["overture_id"]))
    por_dominio, saida = set(), []
    for r in ok:
        if r["dominio"] in por_dominio:
            motivos["duplicado_dominio"] += 1
            continue
        por_dominio.add(r["dominio"])
        saida.append(r)
    # Nome igual a menos de 150 m: mesmo lugar com dois registros.
    vistos = defaultdict(list)
    final = []
    for r in saida:
        k = _nome_chave(r["nome"])
        if any(_distancia_m(r, o) < 150 for o in vistos[k]):
            motivos["duplicado_proximo"] += 1
            continue
        vistos[k].append(r)
        final.append(r)
    return final, dict(motivos)


def _repartir(total: int, pesos: dict[str, float]) -> dict[str, int]:
    """Maiores restos: inteiros que somam o total, proporcionais aos pesos."""
    soma = sum(pesos.values())
    bruto = {k: total * v / soma for k, v in pesos.items()}
    base = {k: int(v) for k, v in bruto.items()}
    for k in sorted(bruto, key=lambda k: bruto[k] - base[k], reverse=True)[: total - sum(base.values())]:
        base[k] += 1
    return base


def cotas(n: int) -> dict[tuple[str, str], int]:
    piloto = CFG["piloto"]
    tipos, cb = piloto["tipos"], piloto["comer_beber"]
    pesos_estrato = {
        "restaurante": tipos["comer_beber"] * cb["restaurante"],
        "bar": tipos["comer_beber"] * cb["bar"],
        "cafe_lanchonete_sorveteria": tipos["comer_beber"] * cb["cafe_lanchonete_sorveteria"],
        "ar_livre_gratuito": tipos["ar_livre_gratuito"],
        "local_evento": tipos["local_evento"],
    }
    out = {}
    for reg, n_reg in _repartir(n, {r: 1 for r in REGIOES}).items():
        for est, q in _repartir(n_reg, pesos_estrato).items():
            out[(reg, est)] = q
    return out


def executar(n: int | None = None):
    n = n or CFG["piloto"]["candidatos"]
    linhas = list(csv.DictReader(open(PROC / "candidatos.csv", encoding="utf-8")))
    ok, motivos = elegiveis(linhas)
    rng = random.Random(CFG["pipeline"]["semente"])
    filas = defaultdict(list)
    for r in sorted(ok, key=lambda r: r["overture_id"]):
        filas[(r["regiao"], r["estrato"])].append(r)
    for k in sorted(filas):
        rng.shuffle(filas[k])

    alvo = cotas(n)
    escolhidos, falta = [], defaultdict(int)
    for k, q in alvo.items():
        escolhidos += filas[k][:q]
        falta[k[0]] += max(0, q - len(filas[k]))
    # Vagas que um estrato não preenche vão para os outros estratos da mesma região, em rodízio.
    sobras = 0
    for reg, f in falta.items():
        restos = [filas[(reg, e)][alvo[(reg, e)]:] for e in ESTRATOS]
        while f and any(restos):
            for fila in restos:
                if f and fila:
                    escolhidos.append(fila.pop(0))
                    f -= 1
        sobras += f

    ordem = {}
    with open(PROC / "sorteio.csv", "w", encoding="utf-8", newline="") as arq:
        campos = ["lugar_id", "ordem", *linhas[0].keys()]
        w = csv.DictWriter(arq, fieldnames=campos)
        w.writeheader()
        for k in sorted(filas):
            for i, r in enumerate(filas[k], 1):
                lid = lugar_id(r["overture_id"])
                ordem[r["overture_id"]] = i
                w.writerow({"lugar_id": lid, "ordem": i, **r})
    with open(PROC / "selecionados.csv", "w", encoding="utf-8", newline="") as arq:
        w = csv.DictWriter(arq, fieldnames=["lugar_id", "ordem", *linhas[0].keys()])
        w.writeheader()
        for r in escolhidos:
            w.writerow({"lugar_id": lugar_id(r["overture_id"]), "ordem": ordem[r["overture_id"]], **r})

    por_estrato = defaultdict(int)
    for r in escolhidos:
        por_estrato[f"{r['regiao']}/{r['estrato']}"] += 1
    return {"elegiveis": len(ok), "descartes": motivos, "selecionados": len(escolhidos),
            "vagas_sem_candidato": sobras, "por_estrato": dict(sorted(por_estrato.items()))}


def _falhou(lid: str, validados: dict) -> bool:
    if lid in validados:
        return not validados[lid]["aprovado"]
    man = PAGINAS / lid / "manifesto.json"
    return man.exists() and json.loads(man.read_text(encoding="utf-8"))["status"] != "ok"


def repor(n: int):
    """Repõe, no mesmo estrato e na ordem do sorteio, as vagas dos lugares que falharam, até a cota de n."""
    sel = list(csv.DictReader(open(PROC / "selecionados.csv", encoding="utf-8")))
    fila = list(csv.DictReader(open(PROC / "sorteio.csv", encoding="utf-8")))
    vf = PROC / "validados.json"
    validados = {v["lugar_id"]: v for v in json.loads(vf.read_text(encoding="utf-8"))} if vf.exists() else {}
    ja = {r["lugar_id"] for r in sel}
    vivos = defaultdict(int)
    for r in sel:
        if not _falhou(r["lugar_id"], validados):
            vivos[(r["regiao"], r["estrato"])] += 1
    rodada = max(int(r.get("rodada") or 0) for r in sel) + 1
    novos, esgotados = [], []
    for k, q in cotas(n).items():
        falta = q - vivos[k]
        proximos = [r for r in fila if (r["regiao"], r["estrato"]) == k and r["lugar_id"] not in ja]
        proximos.sort(key=lambda r: int(r["ordem"]))
        novos += [{**r, "rodada": rodada} for r in proximos[:max(0, falta)]]
        if falta > len(proximos):
            esgotados.append(f"{k[0]}/{k[1]}")
    campos = list(sel[0].keys()) if "rodada" in sel[0] else [*sel[0].keys(), "rodada"]
    with open(PROC / "selecionados.csv", "w", encoding="utf-8", newline="") as arq:
        w = csv.DictWriter(arq, fieldnames=campos, extrasaction="ignore")
        w.writeheader()
        w.writerows([{**r, "rodada": r.get("rodada") or 0} for r in sel] + novos)
    return {"rodada": rodada, "novos": len(novos), "ids": [r["lugar_id"] for r in novos],
            "estratos_esgotados": esgotados}
