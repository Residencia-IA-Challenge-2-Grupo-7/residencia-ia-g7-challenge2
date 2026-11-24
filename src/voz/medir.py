"""Mede a fala de ponta a ponta: áudio -> texto -> janelas do campo 2 (ADR 0017, "Como vamos validar").

Para julgar um áudio novo não se mexe no código: põe o arquivo em `data/raw/voz/<conjunto>/<pessoa>/<ID>.<ext>` (fora
do git), escreve o gabarito em `eval/voz/falas.jsonl` e roda. Passo a passo em `eval/voz/README.md`.

O que sai:
- `eval/resultados/voz-*.json` (vai para o git): números e o veredito de cada ID, **sem o que foi dito**;
- `data/raw/voz/julgamento-*.csv` (fora do git): transcrição e janelas de cada áudio, com a coluna `julgamento` para
  uma pessoa preencher; `python -m src.voz julgar` resume e compara com o veredito automático.
"""
from __future__ import annotations

import csv
import json
import math
import re
import statistics
from datetime import datetime
from pathlib import Path

from src.interpretador.avaliar import limite_inferior
from src.interpretador.campos import interpretar_horarios
from src.interpretador.config import EVAL, RAIZ
from src.voz.transcrever import T, ErroVoz, transcrever
from src.voz.wer import criticos_faltando, wer

EXTENSOES = {".wav", ".m4a", ".mp4", ".ogg", ".opus", ".webm"}  # as que formato_do_audio reconhece
PASTA_VOZ = RAIZ / "data" / "raw" / "voz"
FALAS = EVAL / "voz" / "falas.jsonl"
AGORA = datetime(2026, 11, 5, 10, 0)  # referência dos gabaritos (qui 05/11/2026, 10h, hora de Brasília)
CERTO, PERGUNTOU, SILENCIOSO, FALHOU = "certo", "perguntou", "erro_silencioso", "sem_transcricao"
COLUNAS = ["id", "pessoa", "conjunto", "transcricao", "janelas", "veredito_automatico", "julgamento", "observacao"]


def _linhas(arquivo: Path) -> list[dict]:
    if not arquivo.exists():
        return []
    return [json.loads(x) for x in arquivo.read_text(encoding="utf-8").splitlines() if x.strip()]


def carregar_gabarito() -> dict[str, dict]:
    """ID -> {texto, criticos, conjunto, agora, esperado}. ID repetido é erro: um gabarito esconderia o outro."""
    frases = [f | {"conjunto": "gabarito"} for f in _linhas(EVAL / "interpretador" / "frases.jsonl")
              if f["categoria"] == "disponibilidade"]
    out: dict[str, dict] = {}
    for f in frases + _linhas(EVAL / "interpretador" / "horarios_fala.jsonl") + _linhas(FALAS):
        if f["id"] in out:
            raise ValueError(f"ID repetido no gabarito: {f['id']}")
        out[f["id"]] = {"texto": f.get("texto", ""), "criticos": f.get("criticos", []), "conjunto": f["conjunto"],
                        "agora": datetime.fromisoformat(f["agora"]) if f.get("agora") else AGORA,
                        "esperado": f["esperado"][0]}
    return out


def audios(pasta: Path) -> list[tuple[str, str, Path]]:
    """(ID, pessoa, caminho). Aceita D01.m4a, D01-segunda.m4a e C1-D01.m4a; a pessoa é a pasta (m1, m2...)."""
    out = []
    for a in sorted(pasta.rglob("*")):
        m = re.search(r"(?:^|[-_ ])([A-Z]{1,2}\d{2,3})(?=[-_ ]|$)", a.stem)
        if a.suffix.lower() in EXTENSOES and m:
            out.append((m.group(1), a.parent.name, a))
    return out


def conferir(pasta: Path) -> dict[str, list[str]]:
    """Sem rede: o que falta para julgar a pasta."""
    gab, lista = carregar_gabarito(), audios(pasta)
    com_id = {a for _, _, a in lista}
    return {
        "prontos": sorted(i for i, _, _ in lista if i in gab),
        "audio_sem_gabarito": sorted(str(a.relative_to(pasta)) for i, _, a in lista if i not in gab),
        "audio_sem_id_no_nome": sorted(str(a.relative_to(pasta)) for a in pasta.rglob("*")
                                       if a.is_file() and a not in com_id),
    }


def comparar(texto: str, esperado: dict, agora: datetime) -> tuple[str, str]:
    """(veredito, janelas entendidas). Erro silencioso: entendeu outra coisa e não perguntou."""
    r = interpretar_horarios(texto, agora)
    entendido = r.confirmacao or f"pergunta: {r.motivo}"
    if "pergunta" in esperado:
        return (CERTO if r.motivo == esperado["pergunta"] else PERGUNTOU if r.pergunta else SILENCIOSO), entendido
    if r.pergunta:
        return PERGUNTOU, entendido
    formato = "%Y-%m-%d %H:%M"
    previsto = sorted([j.inicio.strftime(formato), j.fim.strftime(formato), j.disponivel] for j in r.janelas)
    return (CERTO if previsto == sorted(esperado["janelas"]) else SILENCIOSO), entendido


def _p90(xs: list[float]) -> float | None:
    xs = sorted(xs)
    return xs[math.ceil(0.9 * len(xs)) - 1] if xs else None


def resumir(linhas: list[dict]) -> dict:
    n = len(linhas)
    conta = {v: sum(x["veredito"] == v for x in linhas) for v in (CERTO, PERGUNTOU, SILENCIOSO, FALHOU)}
    lat = [x["latencia_s"] for x in linhas if x["latencia_s"] is not None]
    palavras, criticos = sum(x["palavras"] for x in linhas), sum(x["criticos"] for x in linhas)
    return {
        "audios": n, "pessoas": len({x["pessoa"] for x in linhas}), **conta,
        "acerto": round(conta[CERTO] / n, 4) if n else None,
        "acerto_limite_inferior_95": round(limite_inferior(conta[CERTO], n), 4) if n else None,
        "wer": round(sum(x["erros"] for x in linhas) / palavras, 4) if palavras else None,
        "erro_termos_criticos": round(sum(x["criticos_faltando"] for x in linhas) / criticos, 4) if criticos else None,
        "latencia_p50_s": round(statistics.median(lat), 2) if lat else None,
        "latencia_p90_s": round(_p90(lat), 2) if lat else None,
        "custo_usd": round(sum(x["custo_usd"] for x in linhas), 6),
    }


def medir(pasta: Path, *, modelo: str | None = None, rotulo: str | None = None, conjunto: str | None = None,
          transcritor=transcrever, saida: Path | None = None, privado: Path | None = None) -> dict:
    gab = carregar_gabarito()
    lista = [x for x in audios(pasta) if x[0] in gab and (conjunto is None or gab[x[0]]["conjunto"] == conjunto)]
    if not lista:
        raise SystemExit(f"Nenhum áudio com gabarito em {pasta}. Rode `python -m src.voz conferir {pasta}`.")
    linhas, detalhes = [], []
    for id_, pessoa, arquivo in lista:
        g = gab[id_]
        texto, lat, custo, entendido = "", None, 0.0, ""
        try:
            t = transcritor(arquivo.read_bytes(), modelo=modelo)
            texto, lat, custo = t.texto, t.latencia_s, t.custo_usd
            veredito, entendido = comparar(texto, g["esperado"], g["agora"])
        except ErroVoz as e:
            # fala nenhuma ouvida onde não havia fala é o resultado certo
            veredito = CERTO if e.motivo == "vazio" and g["conjunto"] == "falha" else FALHOU
            entendido = f"erro: {e.motivo}"
        erros, palavras = wer(g["texto"], texto) if g["texto"] else (0, 0)
        faltando = criticos_faltando(g["criticos"], texto)
        linhas.append({"id": id_, "pessoa": pessoa, "conjunto": g["conjunto"], "veredito": veredito, "erros": erros,
                       "palavras": palavras, "criticos": len(g["criticos"]), "criticos_faltando": len(faltando),
                       "latencia_s": lat, "custo_usd": custo})
        detalhes.append({"id": id_, "pessoa": pessoa, "conjunto": g["conjunto"], "transcricao": texto,
                         "janelas": entendido, "veredito_automatico": veredito, "julgamento": "", "observacao": ""})
        print(f"{veredito:16} {id_} {pessoa}: {texto} => {entendido}", flush=True)
    quando = datetime.now()
    r = {"rotulo": rotulo or pasta.name, "modelo": modelo or T["modelo"], "quando": quando.isoformat(timespec="seconds"),
         "total": resumir(linhas),
         "por_conjunto": {c: resumir([x for x in linhas if x["conjunto"] == c])
                          for c in sorted({x["conjunto"] for x in linhas})},
         "por_audio": linhas}
    nome = f"voz-{r['rotulo']}-{r['modelo'].split('/')[-1]}-{quando:%Y-%m-%d}"
    saida, privado = saida or EVAL / "resultados", privado or PASTA_VOZ
    saida.mkdir(parents=True, exist_ok=True)
    privado.mkdir(parents=True, exist_ok=True)
    (saida / f"{nome}.json").write_text(json.dumps(r, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    r["csv"] = str(privado / f"julgamento-{nome}.csv")
    with open(r["csv"], "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, COLUNAS, delimiter=";")
        w.writeheader()
        w.writerows(detalhes)
    return r


def julgar(arquivo: Path) -> dict:
    """Resume a coluna `julgamento` (certo ou errado) e compara com o veredito automático."""
    with open(arquivo, encoding="utf-8-sig", newline="") as f:
        linhas = [x for x in csv.DictReader(f, delimiter=";")]
    feitos = [x for x in linhas if x["julgamento"].strip().lower() in ("certo", "errado")]
    certos = [x for x in feitos if x["julgamento"].strip().lower() == "certo"]
    iguais = [x for x in feitos if (x["julgamento"].strip().lower() == "certo") == (x["veredito_automatico"] == CERTO)]
    return {"audios": len(linhas), "julgados": len(feitos), "certos": len(certos),
            "acerto_limite_inferior_95": round(limite_inferior(len(certos), len(feitos)), 4) if feitos else None,
            "concordam_com_o_automatico": len(iguais),
            "divergem": [x["id"] for x in feitos if x not in iguais]}


CABECALHO = ("| Conjunto | Áudios | Pessoas | Certos | Perguntou | Erro silencioso | Sem transcrição | WER | "
             "Termos críticos | p50 / p90 | Custo |\n|---|---|---|---|---|---|---|---|---|---|---|")


def linha_md(nome: str, r: dict) -> str:
    pct = lambda x: "—" if x is None else f"{100 * x:.1f}%".replace(".", ",")
    lat = "—" if r["latencia_p50_s"] is None else f"{r['latencia_p50_s']:.2f} / {r['latencia_p90_s']:.2f} s".replace(".", ",")
    return (f"| {nome} | {r['audios']} | {r['pessoas']} | {r[CERTO]} ({pct(r['acerto'])}, mín. "
            f"{pct(r['acerto_limite_inferior_95'])}) | {r[PERGUNTOU]} | {r[SILENCIOSO]} | {r[FALHOU]} | {pct(r['wer'])} | "
            f"{pct(r['erro_termos_criticos'])} | {lat} | US$ {r['custo_usd']:.4f} |")
