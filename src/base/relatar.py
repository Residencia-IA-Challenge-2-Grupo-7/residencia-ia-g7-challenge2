"""Etapa 10: relatório da rodada (ADR 0005): contagens por estrato, taxa de aprovação, motivos de falha,
valores barrados pelo validador e consumo estimado de tokens. Grava data/base/relatorio.md (versionado).
"""
import csv
import json
from collections import Counter, defaultdict
from datetime import date

from .config import BASE, CFG, EXTRACAO, PAGINAS, PROC, VERSAO
from .regioes import REGIOES
from .selecionar import ESTRATOS


def _ler_csv(nome):
    return list(csv.DictReader(open(PROC / nome, encoding="utf-8")))


def _tabela(cab, linhas):
    out = ["| " + " | ".join(cab) + " |", "|" + "---|" * len(cab)]
    out += ["| " + " | ".join(str(x) for x in l) + " |" for l in linhas]
    return "\n".join(out)


def _por_estrato(sel, status, aprov):
    t = defaultdict(lambda: [0, 0, 0])
    for r in sel:
        k = (r["regiao"], r["estrato"])
        t[k][0] += 1
        t[k][1] += status.get(r["lugar_id"]) == "ok"
        t[k][2] += aprov.get(r["lugar_id"], False)
    linhas = []
    for reg in REGIOES:
        cel = [f"{t[(reg, e)][2]}/{t[(reg, e)][1]}/{t[(reg, e)][0]}" for e in ESTRATOS]
        tot = [sum(t[(reg, e)][i] for e in ESTRATOS) for i in range(3)]
        linhas.append([REGIOES[reg], *cel, f"{tot[2]}/{tot[1]}/{tot[0]}"])
    return linhas


def executar():
    cand = _ler_csv("candidatos.csv")
    fila = _ler_csv("sorteio.csv")
    sel = _ler_csv("selecionados.csv")
    status = {}
    for r in sel:
        m = PAGINAS / r["lugar_id"] / "manifesto.json"
        status[r["lugar_id"]] = json.loads(m.read_text(encoding="utf-8"))["status"] if m.exists() else "nao_rastreado"
    val = json.loads((PROC / "validados.json").read_text(encoding="utf-8"))
    aprov = {v["lugar_id"]: v["aprovado"] for v in val}
    motivos = Counter(m for v in val for m in v["motivos"])
    rej = Counter()
    for v in val:
        rej.update(v.get("rejeicoes", {}))
    aceitos = sum(1 for _ in open(PROC / "evidencias.jsonl", encoding="utf-8"))
    fichas = json.loads((PROC / "fichas.json").read_text(encoding="utf-8")) if (PROC / "fichas.json").exists() else {}
    consumo = []
    if (EXTRACAO / "consumo.jsonl").exists():
        consumo = [json.loads(l) for l in open(EXTRACAO / "consumo.jsonl", encoding="utf-8")]
    piloto = [r for r in sel if (r.get("rodada") or "0") == "0"]
    cab = ["Região", *ESTRATOS, "Total"]
    n_valores = aceitos + sum(rej.values())

    txt = [
        f"# Relatório da rodada da base — {date.today().isoformat()}",
        "",
        f"Pipeline {VERSAO} (ADR 0005), Overture {CFG['pipeline']['release_overture']}, "
        f"extração por {CFG['extracao']['modelo']}. Gerado por `python -m base relatar`; nenhum número foi digitado.",
        "",
        "## Funil",
        "",
        _tabela(["Etapa", "Lugares"], [
            ["Candidatos da Overture nos tipos de rolê, dentro do DF", len(cand)],
            ["Com site próprio (sem redes, agregadores e delivery)", sum(1 for r in cand if r["site"])],
            ["Elegíveis (confiança, um por domínio, sem duplicatas)", len(fila)],
            ["Sorteados (piloto mais reposições)", len(sel)],
            ["Site respondeu com conteúdo", sum(1 for s in status.values() if s == "ok")],
            ["Aprovados com os campos obrigatórios", sum(aprov.values())],
        ]),
        "",
        "## Piloto: 100 primeiros sorteados",
        "",
        "Cada célula: aprovados / site respondeu / sorteados.",
        "",
        _tabela(cab, _por_estrato(piloto, status, aprov)),
        "",
        "Situação do site no piloto: " + ", ".join(
            f"{k} {v}" for k, v in Counter(status[r["lugar_id"]] for r in piloto).most_common()) + ".",
        "",
        "## Base: todas as rodadas",
        "",
        _tabela(cab, _por_estrato(sel, status, aprov)),
        "",
        "## Motivos de reprovação",
        "",
        _tabela(["Motivo", "Lugares"], motivos.most_common()),
        "",
        "## Valores extraídos pelo LLM",
        "",
        f"{n_valores} valores conferidos: {aceitos} aceitos e {sum(rej.values())} barrados pelo validador.",
        "",
        _tabela(["Por que foi barrado", "Valores"], rej.most_common()),
        "",
        "`evidencia_ausente` é o indicador de alucinação: o trecho citado não existe na página.",
        "",
        "## Base gravada",
        "",
        _tabela(["Coleção", "Documentos"], [[k, len(v)] for k, v in fichas.items()]),
        "",
        "## Consumo da extração",
        "",
        _tabela(["Rodada", "Lotes", "Lugares", "Texto das páginas (tokens estimados)",
                 "Total dos subagentes (tokens medidos)"],
                [[c["rodada"], c["lotes"], c["lugares"], c["tokens_estimados"], c.get("tokens_subagentes", "—")]
                 for c in consumo])
        if consumo else "Sem registro.",
        "",
        "O total medido inclui o prompt, as leituras e as escritas de arquivo de cada subagente.",
        "",
    ]
    BASE.mkdir(parents=True, exist_ok=True)
    (BASE / "relatorio.md").write_text("\n".join(txt), encoding="utf-8")
    return {"relatorio": "data/base/relatorio.md", "aprovados": sum(aprov.values()), "sorteados": len(sel)}
