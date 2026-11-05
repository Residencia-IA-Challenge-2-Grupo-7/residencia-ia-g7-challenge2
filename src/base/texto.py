"""Texto limpo de HTML e PDF. É contra este texto, salvo junto da página, que o validador confere as evidências."""
import io
import json
import re

from bs4 import BeautifulSoup

_ESPACOS = re.compile(r"[ \t\r\f\v   ]+")
_REMOVER = ["script", "style", "noscript", "svg", "iframe", "template", "canvas"]


def _linhas(texto: str) -> list[str]:
    out, anterior = [], None
    for l in texto.splitlines():
        l = _ESPACOS.sub(" ", l).strip()
        if l and l != anterior:
            out.append(l)
            anterior = l
    return out


def html_para_texto(conteudo: bytes) -> tuple[str, list[str]]:
    """(texto, links) da página. Os blocos JSON-LD (schema.org) entram no fim, compactados."""
    soup = BeautifulSoup(conteudo, "lxml")
    titulo = soup.title.get_text(" ", strip=True) if soup.title else ""
    meta = soup.find("meta", attrs={"name": "description"})
    desc = (meta.get("content") or "").strip() if meta else ""
    blocos = []
    for s in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            blocos.append(json.dumps(json.loads(s.string or s.get_text()), ensure_ascii=False))
        except (ValueError, TypeError):
            pass
    links = [(a.get("href") or "", a.get_text(" ", strip=True)) for a in soup.find_all("a")]
    for t in soup(_REMOVER):
        t.decompose()
    linhas = _linhas("\n".join([titulo, desc, soup.get_text("\n")]))
    if blocos:
        linhas += ["[dados estruturados da página]"] + blocos
    return "\n".join(linhas), links


def pdf_para_texto(conteudo: bytes, max_paginas: int) -> str:
    from pypdf import PdfReader
    try:
        leitor = PdfReader(io.BytesIO(conteudo))
    except Exception:  # PDF cortado pelo limite de bytes ou corrompido: fica sem texto
        return ""
    partes = []
    for pg in leitor.pages[:max_paginas]:
        try:
            partes.append(pg.extract_text() or "")
        except Exception:  # PDF mal formado numa página não derruba as outras
            continue
    return "\n".join(_linhas("\n".join(partes)))
