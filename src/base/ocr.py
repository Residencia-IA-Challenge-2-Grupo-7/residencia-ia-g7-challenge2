"""Etapa 3b: leitura de cardápio em imagem e PDF escaneado por OCR local (opção A do piloto, ADR 0005).

As imagens e PDFs de cardápio são achados nas páginas que o robô já salvou e baixados com as mesmas regras
(robots.txt, 2 s por domínio). O OCR roda na máquina (EasyOCR, português) e o texto, montado linha a linha,
entra no manifesto como mais uma página. O validador confere as evidências contra esse texto, como em
qualquer página: o LLM continua só lendo, e o código decide.
"""
import csv
import hashlib
import io
import json
import re
from datetime import datetime
from urllib.parse import urljoin, urlparse

import numpy as np
import requests
from bs4 import BeautifulSoup

from .config import CFG, PAGINAS, PROC
from .descobrir import dominio
from .rastrear import Robo, _mesmo_site, _sem_acento

O = CFG["ocr"]
CHAVES = ("cardapio", "menu", "carta", "preco", "pratos", "bebidas", "drinks", "lanches", "pizzas", "combos",
          "porcoes", "sobremesas", "almoco", "executivo", "buffet")
EXCLUIR = ("logo", "icon", "favicon", "sprite", "avatar", "whatsapp", "instagram", "facebook", "ifood", "loading",
           "placeholder", "pixel", "selo", "badge", "flag", "seta", "arrow", ".svg", ".gif")
EXT_IMG = (".jpg", ".jpeg", ".png", ".webp")
_LEITOR = None


def _leitor():
    global _LEITOR
    if _LEITOR is None:
        import easyocr
        _LEITOR = easyocr.Reader(["pt", "en"], gpu=False, verbose=False)
    return _LEITOR


def _src(img) -> str:
    for attr in ("data-src", "data-lazy-src", "data-original", "src"):
        v = img.get(attr)
        if v and not v.startswith("data:"):
            return v
    srcset = img.get("srcset") or img.get("data-srcset") or ""
    partes = [p.strip().split(" ")[0] for p in srcset.split(",") if p.strip()]
    return partes[-1] if partes else ""


def candidatas(man: dict) -> list[tuple[int, str]]:
    """(pontos, url) das imagens e PDFs que parecem cardápio, nas páginas já salvas do lugar."""
    pasta = PAGINAS / man["lugar_id"]
    dom = man["dominio"]
    achadas = {}
    for p in man["paginas"]:
        if p.get("ocr"):
            continue
        if p["tipo"] == "application/pdf":
            if p["chars"] < 200:  # PDF sem camada de texto: provavelmente cardápio escaneado
                achadas[p["url"]] = max(achadas.get(p["url"], 0), 5)
            continue
        html = pasta / f"{p['arquivo']}.html"
        if not html.exists():
            continue
        soup = BeautifulSoup(html.read_bytes(), "lxml")
        pagina_menu = any(k in _sem_acento(p["url"]) for k in CHAVES)
        for img in soup.find_all("img"):
            u = _src(img)
            if not u:
                continue
            u = urljoin(p["url"], u)
            alvo = _sem_acento(u + " " + (img.get("alt") or "") + " " + (img.get("title") or ""))
            if any(x in alvo for x in EXCLUIR):
                continue
            try:
                if 0 < int(img.get("width") or 0) < 300:
                    continue
            except ValueError:
                pass
            pts = 3 * any(k in alvo for k in CHAVES) + 2 * pagina_menu
            if pts >= 2:
                achadas[u] = max(achadas.get(u, 0), pts)
        for a in soup.find_all("a"):
            u = urljoin(p["url"], a.get("href") or "")
            baixo = u.lower().split("?")[0]
            if not baixo.endswith(EXT_IMG + (".pdf",)):
                continue
            alvo = _sem_acento(u + " " + a.get_text(" ", strip=True))
            if any(k in alvo for k in CHAVES) and not any(x in alvo for x in EXCLUIR):
                achadas[u] = max(achadas.get(u, 0), 4)
    # Imagens hospedadas em CDNs de construtores de site (Wix, WordPress) também valem; outras origens, não.
    cdn = ("wixstatic.com", "wp.com", "squarespace-cdn.com", "googleusercontent.com", "cloudfront.net")
    ok = [(pts, u) for u, pts in achadas.items()
          if u.startswith("http") and (_mesmo_site(u, dom) or any(c in dominio(u) for c in cdn))]
    return sorted(ok, key=lambda x: -x[0])[: O["max_imagens_lugar"]]


def _imagens(url: str, corpo: bytes, tipo: str) -> list:
    """Imagens (PIL) a ler: a própria imagem, ou as primeiras páginas do PDF renderizadas."""
    from PIL import Image
    if "pdf" in tipo or url.lower().split("?")[0].endswith(".pdf"):
        import pypdfium2 as pdfium
        try:
            doc = pdfium.PdfDocument(corpo)
        except Exception:
            return []
        return [doc[i].render(scale=2).to_pil() for i in range(min(len(doc), O["max_paginas_pdf"]))]
    try:
        im = Image.open(io.BytesIO(corpo))
        im.load()
    except Exception:
        return []
    if min(im.size) < O["lado_min_px"]:
        return []  # ícone, foto de prato, miniatura
    return [im.convert("RGB")]


def ler(im) -> str:
    """OCR com as caixas reagrupadas em linhas, para que o nome do item e o preço fiquem na mesma linha."""
    lado = max(im.size)
    if lado > O["lado_max_px"]:
        f = O["lado_max_px"] / lado
        im = im.resize((int(im.size[0] * f), int(im.size[1] * f)))
    elif lado < 1000:  # cardápio em miniatura: ampliar ajuda o reconhecimento de letras pequenas
        im = im.resize((im.size[0] * 2, im.size[1] * 2))
    caixas = _leitor().readtext(np.array(im), detail=1, paragraph=False)
    itens = []
    for box, txt, conf in caixas:
        if conf < O["confianca_min"] or not txt.strip():
            continue
        ys = [pt[1] for pt in box]
        itens.append((sum(ys) / 4, max(ys) - min(ys), min(pt[0] for pt in box), txt.strip()))
    itens.sort()
    linhas, atual = [], []
    for it in itens:
        if atual and abs(it[0] - atual[-1][0]) > 0.6 * max(it[1], atual[-1][1]):
            linhas.append(atual)
            atual = []
        atual.append(it)
    if atual:
        linhas.append(atual)
    return "\n".join(" ".join(t for *_, t in sorted(l, key=lambda x: x[2])) for l in linhas)


def processar(robo: Robo, man: dict) -> dict:
    pasta = PAGINAS / man["lugar_id"]
    feitas = {p["url"] for p in man["paginas"] if p.get("ocr")}
    novas = 0
    for _, url in candidatas(man):
        if url in feitas:
            continue
        try:
            if not robo.permitido(url):
                continue
            resp, corpo = robo.baixar(url)
        except requests.RequestException:
            continue
        tipo = (resp.headers.get("Content-Type") or "").lower()
        if resp.status_code >= 400 or len(corpo) < O["bytes_min"] or len(corpo) >= CFG["robo"]["max_bytes"]:
            continue
        textos = [ler(im) for im in _imagens(url, corpo, tipo)]
        texto = "\n".join(t for t in textos if t)
        if len(texto) < 40:
            continue
        nome = "ocr-" + hashlib.sha1(url.encode()).hexdigest()[:12]
        (pasta / f"{nome}.txt").write_text(texto, encoding="utf-8")
        man["paginas"].append({"url": url, "http": resp.status_code, "tipo": "ocr", "ocr": True,
                               "sha256": hashlib.sha256(corpo).hexdigest(), "arquivo": nome, "chars": len(texto),
                               "baixado_em": datetime.now().isoformat(timespec="seconds"), "mudou": True})
        novas += 1
    if novas:
        (pasta / "manifesto.json").write_text(json.dumps(man, ensure_ascii=False, indent=1), encoding="utf-8")
    return {"lugar_id": man["lugar_id"], "paginas_ocr": novas}


def executar(ids: list[str] | None = None):
    """Roda o OCR nos lugares de comer e beber com site no ar que ainda não foram aprovados."""
    sel = {l["lugar_id"]: l for l in csv.DictReader(open(PROC / "selecionados.csv", encoding="utf-8"))}
    vf = PROC / "validados.json"
    aprovados = {v["lugar_id"] for v in json.loads(vf.read_text(encoding="utf-8")) if v["aprovado"]} \
        if vf.exists() else set()
    alvos = []
    for lid, l in sel.items():
        m = PAGINAS / lid / "manifesto.json"
        if (ids and lid not in ids) or not m.exists() or lid in aprovados or l["tipo_role"] != "comer_beber":
            continue
        man = json.loads(m.read_text(encoding="utf-8"))
        if man["status"] == "ok":
            alvos.append(man)
    robo = Robo()
    # O OCR já usa todos os núcleos; o download é o que espera os 2 s, então segue em série por lugar.
    res = [processar(robo, man) for man in alvos]
    com = [r for r in res if r["paginas_ocr"]]
    return {"lugares_tentados": len(alvos), "lugares_com_ocr": len(com),
            "paginas_ocr": sum(r["paginas_ocr"] for r in res), "ids": [r["lugar_id"] for r in com]}
