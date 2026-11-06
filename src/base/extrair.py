"""Etapa 4: montar a entrada da extração por LLM e os lotes.

A leitura das páginas é feita por um modelo pequeno (Claude Haiku 5.5), um lote por vez, com o prompt
em prompts/extracao_lugar.md. Cada lote lista os arquivos de entrada e onde gravar o JSON de saída.
O pipeline não confia na saída: a etapa validar confere tudo contra o texto das páginas.
"""
import csv
import json
import re
from datetime import date

from . import normalizar as nz
from .config import CFG, EXTRACAO, PAGINAS, PROC, PROMPTS, RAIZ
from .normalizar import DIAS

X = CFG["extracao"]


def _manifestos():
    for m in sorted(PAGINAS.glob("*/manifesto.json")):
        yield json.loads(m.read_text(encoding="utf-8"))


_PRECO = re.compile(r"R\$\s*\d|(?<![\d.,])\d{1,3},\d{2}(?![\d])")


def sinais(lid: str, man: dict) -> dict:
    """Sinais, achados por expressão regular, dos campos obrigatórios no texto das páginas."""
    linhas = []
    for p in man["paginas"]:
        linhas += (PAGINAS / lid / f"{p['arquivo']}.txt").read_text(encoding="utf-8").splitlines()
    texto = "\n".join(linhas)
    janelas = (" ".join(linhas[i:i + 3]) for i in range(len(linhas)))  # dia e horário podem vir em linhas vizinhas
    horario = any(len(nz.horas(j)) >= 2 and nz.dias(j) for j in janelas)
    hoje = date.today()
    datas = sum(1 for d, m, a in nz.datas(texto)
                if date(a or hoje.year, m, min(d, 28)) >= hoje)
    return {"precos": len(_PRECO.findall(texto)), "horario": horario, "gratuito": nz.diz_gratuito(texto),
            "datas_futuras": datas}


def passa_triagem(tipo: str, s: dict) -> bool:
    if tipo == "comer_beber":
        # Só o preço decide: o sinal de horário por regex perde layouts em várias linhas (visto no OCR).
        return s["precos"] >= CFG["triagem"]["precos_min"]
    if tipo == "ar_livre_gratuito":
        return s["horario"] and (s["gratuito"] or s["precos"] > 0)
    return s["datas_futuras"] > 0


def _entrada(lugar: dict, man: dict) -> str:
    hoje = date.today().isoformat()
    cab = (f"LUGAR: {lugar['lugar_id']} | {lugar['nome']} | categoria: {lugar['categoria']} | "
           f"tipo: {lugar['tipo_role']} | RA: {lugar['ra']} | endereço conhecido: "
           f"{lugar['endereco_overture'] or 'não informado'} | hoje: {hoje}")
    partes, vistas, total = [cab], set(), 0
    for i, p in enumerate(man["paginas"], 1):
        linhas = (PAGINAS / man["lugar_id"] / f"{p['arquivo']}.txt").read_text(encoding="utf-8").splitlines()
        novas = [l for l in linhas if l not in vistas]
        vistas.update(linhas)
        corpo = "\n".join(novas)[: X["max_chars_pagina"]]
        if not corpo.strip():
            continue
        if total + len(corpo) > X["max_chars_lugar"]:
            corpo = corpo[: max(0, X["max_chars_lugar"] - total)]
        if not corpo:
            break
        marca = " | lida por OCR" if p.get("ocr") else ""
        partes.append(f"=== PÁGINA {i} | {p['url']}{marca} ===\n{corpo}")
        total += len(corpo)
    return "\n\n".join(partes)


def preparar(todos: bool = False, ids: list[str] | None = None):
    lugares = {l["lugar_id"]: l for l in csv.DictReader(open(PROC / "selecionados.csv", encoding="utf-8"))}
    ent, sai, lot = EXTRACAO / "entrada", EXTRACAO / "saida", EXTRACAO / "lotes"
    for d in (ent, sai, lot):
        d.mkdir(parents=True, exist_ok=True)
    for f in lot.glob("*.txt"):
        f.unlink()
    pendentes, inalterados = [], 0
    triagem = {}
    for man in _manifestos():
        lid = man["lugar_id"]
        if man["status"] != "ok" or lid not in lugares or (ids and lid not in ids):
            continue
        mudou = any(p.get("mudou", True) for p in man["paginas"])
        if not todos and not mudou and (sai / f"{lid}.json").exists():
            inalterados += 1  # páginas iguais: vale a extração anterior, e a validação renova a data
            continue
        s = sinais(lid, man)
        triagem[lid] = {**s, "passa": passa_triagem(lugares[lid]["tipo_role"], s)}
        if not triagem[lid]["passa"]:
            continue  # sem sinal dos campos obrigatórios no texto: o LLM nem é chamado
        texto = _entrada(lugares[lid], man)
        (ent / f"{lid}.txt").write_text(texto, encoding="utf-8")
        pendentes.append((lid, len(texto)))

    # Lotes de tamanho parecido, para cada leitura caber folgada no contexto do modelo pequeno.
    pendentes.sort(key=lambda x: -x[1])
    n_lotes = max(1, -(-len(pendentes) // X["lugares_por_lote"]))
    lotes = [[] for _ in range(n_lotes)]
    for i, item in enumerate(pendentes):
        lotes[i % n_lotes].append(item)
    prompt = (PROMPTS / "extracao_lugar.md").relative_to(RAIZ).as_posix()
    indice = []
    for i, lote in enumerate(lotes, 1):
        if not lote:
            continue
        linhas = [f"prompt: {prompt}"] + [
            f"{(ent / f'{lid}.txt').relative_to(RAIZ).as_posix()} -> {(sai / f'{lid}.json').relative_to(RAIZ).as_posix()}"
            for lid, _ in lote]
        arq = lot / f"lote-{i:02d}.txt"
        arq.write_text("\n".join(linhas) + "\n", encoding="utf-8")
        indice.append({"lote": arq.relative_to(RAIZ).as_posix(), "lugares": len(lote),
                       "chars": sum(c for _, c in lote)})
    total = sum(c for _, c in pendentes)
    arq_t = EXTRACAO / "triagem.json"
    antiga = json.loads(arq_t.read_text(encoding="utf-8")) if arq_t.exists() else {}
    arq_t.write_text(json.dumps({**antiga, **triagem}, ensure_ascii=False, indent=1), encoding="utf-8")
    if pendentes:
        # Registro do consumo (RNF-15): o texto enviado ao modelo, estimado em 4 caracteres por token.
        reg = EXTRACAO / "consumo.jsonl"
        n = sum(1 for _ in open(reg, encoding="utf-8")) if reg.exists() else 0
        with open(reg, "a", encoding="utf-8") as f:
            f.write(json.dumps({"rodada": n + 1, "data": date.today().isoformat(), "lotes": len(indice),
                                "lugares": len(pendentes), "tokens_estimados": total // 4,
                                "modelo": X["modelo"]}) + "\n")
    return {"triados": len(triagem), "barrados_na_triagem": sum(not t["passa"] for t in triagem.values()),
            "para_extrair": len(pendentes), "inalterados": inalterados, "lotes": indice,
            "chars": total, "tokens_estimados": total // 4, "modelo": X["modelo"]}


def preparar_descricoes():
    """Entrada da descrição curta: só os campos já validados, nunca o texto do site (ADR 0005)."""
    val = json.loads((PROC / "validados.json").read_text(encoding="utf-8"))
    d = PROC / "descricao"
    d.mkdir(parents=True, exist_ok=True)
    fatos = []
    for v in val:
        if not v["aprovado"]:
            continue
        a = {k: x["valor"] for k, x in v["atributos"].items()}
        fatos.append({
            "lugar_id": v["lugar_id"], "nome": v["nome"], "categoria": v["categoria"], "ra": v["ra"],
            "dias_abertos": sorted({h["dia"] for h in v["horarios"]}, key=DIAS.index),
            "itens": [i["item"] for i in v["itens"]][:5], "atributos": a,
            "gratuito": (v.get("entrada") or {}).get("gratuito"),
            "eventos": [e["titulo"] for e in v.get("eventos", [])][:3],
        })
    (d / "entrada.json").write_text(json.dumps(fatos, ensure_ascii=False, indent=1), encoding="utf-8")
    return {"lugares": len(fatos), "entrada": (d / "entrada.json").relative_to(RAIZ).as_posix(),
            "prompt": (PROMPTS / "descricao.md").relative_to(RAIZ).as_posix()}
