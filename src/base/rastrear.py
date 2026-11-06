"""Etapa 3: robô que lê só o site oficial de cada lugar (ADR 0005, Regras do robô).

- obedece ao robots.txt; um domínio que proíbe fica de fora;
- no máximo uma requisição a cada 2 s por domínio e até 10 páginas por lugar;
- user-agent próprio; páginas brutas fora do git, apagadas depois de 30 dias (só o hash fica).
"""
import csv
import hashlib
import json
import socket
import threading
import time
import unicodedata
import urllib.robotparser
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from urllib.parse import urldefrag, urljoin, urlparse

import requests

from .config import CFG, PAGINAS, PROC
from .descobrir import bloqueado, dominio
from .texto import html_para_texto, pdf_para_texto

R = CFG["robo"]
# Palavras que indicam páginas com horário, cardápio, preço ou agenda, com peso.
PALAVRAS = {
    "cardapio": 5, "menu": 4, "precos": 4, "preco": 3, "horario": 5, "funcionamento": 5, "contato": 2,
    "sobre": 1, "quem-somos": 1, "quemsomos": 1, "localizacao": 2, "onde": 1, "unidade": 2, "pratos": 3,
    "bebidas": 3, "drinks": 2, "carta": 2, "ingresso": 4, "programacao": 5, "agenda": 5, "eventos": 4,
    "evento": 3, "visite": 3, "visitacao": 4, "visita": 2, "servicos": 1, "acessibilidade": 2,
}
EXT_IGNORAR = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".css", ".js", ".zip", ".mp4", ".mp3",
               ".doc", ".docx", ".xls", ".xlsx", ".ico", ".rar")


def _sem_acento(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s.casefold()) if unicodedata.category(c) != "Mn")


class Ritmo:
    """Intervalo mínimo entre requisições ao mesmo domínio, valendo para todas as threads."""

    def __init__(self, intervalo: float):
        self.intervalo = intervalo
        self._trava = threading.Lock()
        self._por_dom: dict[str, tuple[threading.Lock, list]] = {}

    def esperar(self, dom: str):
        with self._trava:
            trava, ultimo = self._por_dom.setdefault(dom, (threading.Lock(), [0.0]))
        with trava:
            espera = ultimo[0] + self.intervalo - time.monotonic()
            if espera > 0:
                time.sleep(espera)
            ultimo[0] = time.monotonic()


class Robo:
    def __init__(self):
        self.s = requests.Session()
        self.s.headers.update({"User-Agent": R["user_agent"], "Accept-Language": "pt-BR,pt;q=0.9"})
        self.ritmo = Ritmo(R["intervalo_s"])
        self._robots: dict[str, urllib.robotparser.RobotFileParser | None] = {}
        self._trava = threading.Lock()

    def baixar(self, url: str):
        self.ritmo.esperar(dominio(url))
        r = self.s.get(url, timeout=R["timeout_s"], stream=True, allow_redirects=True)
        corpo = b""
        for parte in r.iter_content(65536):
            corpo += parte
            if len(corpo) > R["max_bytes"]:
                break
        r.close()
        return r, corpo

    def permitido(self, url: str) -> bool:
        p = urlparse(url)
        base = f"{p.scheme}://{p.netloc}"
        with self._trava:
            conhecido = base in self._robots
        if not conhecido:
            rp = urllib.robotparser.RobotFileParser()
            # RFC 9309: 4xx no robots.txt libera a coleta; 5xx (indisponível) proíbe por precaução.
            try:
                r, corpo = self.baixar(base + "/robots.txt")
                if r.status_code >= 500:
                    rp.disallow_all = True
                elif r.status_code == 200 and b"<html" not in corpo[:500].lower():
                    rp.parse(corpo.decode("utf-8", errors="replace").splitlines())
                else:
                    rp.allow_all = True
            except requests.RequestException:
                rp.allow_all = True
            with self._trava:
                self._robots[base] = rp
        return self._robots[base].can_fetch(R["token_robots"], url)


def _pontuar(href: str, texto: str) -> int:
    alvo = _sem_acento(href + " " + texto)
    return sum(p for k, p in PALAVRAS.items() if k in alvo)


def _mesmo_site(url: str, dom: str) -> bool:
    d = dominio(url)
    return d == dom or d.endswith("." + dom)


def _salvar(pasta, url, resp, corpo, max_pdf):
    tipo = (resp.headers.get("Content-Type") or "").split(";")[0].strip().lower()
    h = hashlib.sha256(corpo).hexdigest()
    nome = hashlib.sha1(url.encode()).hexdigest()[:12]
    links = []
    if "pdf" in tipo or url.lower().endswith(".pdf"):
        (pasta / f"{nome}.pdf").write_bytes(corpo)
        texto = pdf_para_texto(corpo, max_pdf)
        tipo = "application/pdf"
    elif "html" in tipo or not tipo:
        (pasta / f"{nome}.html").write_bytes(corpo)
        texto, links = html_para_texto(corpo)
    else:
        return None, []
    (pasta / f"{nome}.txt").write_text(texto, encoding="utf-8")
    return {"url": url, "http": resp.status_code, "tipo": tipo, "sha256": h, "arquivo": nome,
            "chars": len(texto), "baixado_em": datetime.now().isoformat(timespec="seconds")}, links


def rastrear_lugar(robo: Robo, lugar: dict) -> dict:
    lid, site = lugar["lugar_id"], lugar["site"]
    pasta = PAGINAS / lid
    pasta.mkdir(parents=True, exist_ok=True)
    anterior = {}
    man_arq = pasta / "manifesto.json"
    if man_arq.exists():
        anterior = {p["url"]: p["sha256"] for p in json.loads(man_arq.read_text(encoding="utf-8"))["paginas"]}
    man = {"lugar_id": lid, "site": site, "dominio": dominio(site), "status": "ok", "motivo": "",
           "data": date.today().isoformat(), "paginas": []}

    def fim(status, motivo=""):
        man["status"], man["motivo"] = status, motivo
        man_arq.write_text(json.dumps(man, ensure_ascii=False, indent=1), encoding="utf-8")
        return man

    try:
        socket.getaddrinfo(urlparse(site).hostname, None)
    except (socket.gaierror, UnicodeError):
        return fim("dominio_inexistente")  # site listado na Overture que não existe mais
    try:
        if not robo.permitido(site):
            return fim("robots_proibe")
        try:
            resp, corpo = robo.baixar(site)
        except requests.exceptions.SSLError:
            # Certificado inválido: tenta uma vez sem TLS, como muitos sites pequenos ainda servem.
            site = "http://" + site.split("://", 1)[1]
            resp, corpo = robo.baixar(site)
    except requests.RequestException as e:
        return fim("site_fora_do_ar", type(e).__name__)
    final = resp.url
    dom = dominio(final)
    if bloqueado(dom):
        return fim("redireciona_agregador", dom)
    if resp.status_code in (401, 403, 429):
        return fim("bloqueia_robo", f"HTTP {resp.status_code}")
    if resp.status_code >= 400:
        return fim("site_fora_do_ar", f"HTTP {resp.status_code}")
    if dom != man["dominio"] and not robo.permitido(final):
        return fim("robots_proibe")
    man["dominio"] = dom
    reg, links = _salvar(pasta, final, resp, corpo, R["max_paginas_pdf"])
    if not reg:
        return fim("nao_html", resp.headers.get("Content-Type", ""))
    reg["mudou"] = anterior.get(final) != reg["sha256"]
    man["paginas"].append(reg)

    vistos = {urldefrag(final)[0].rstrip("/")}
    fila = []
    for href, txt in links:
        u = urldefrag(urljoin(final, href))[0]
        if not u.startswith("http") or not _mesmo_site(u, dom) or u.lower().endswith(EXT_IGNORAR):
            continue
        chave = u.rstrip("/")
        if chave in vistos:
            continue
        vistos.add(chave)
        pts = _pontuar(urlparse(u).path, txt)
        if pts > 0:
            fila.append((pts, u))
    fila.sort(key=lambda x: (-x[0], len(x[1])))
    for _, u in fila[: R["max_paginas"] - 1]:
        try:
            if not robo.permitido(u):
                continue
            resp, corpo = robo.baixar(u)
        except requests.RequestException:
            continue
        if resp.status_code >= 400 or not _mesmo_site(resp.url, dom):
            continue
        reg, _ = _salvar(pasta, resp.url, resp, corpo, R["max_paginas_pdf"])
        if reg:
            reg["mudou"] = anterior.get(resp.url) != reg["sha256"]
            man["paginas"].append(reg)
    if sum(p["chars"] for p in man["paginas"]) < 300:
        # Página montada por JavaScript: o Playwright entra só aqui (ainda não instalado no piloto).
        return fim("precisa_js")
    return fim("ok")


def executar(ids: list[str] | None = None):
    lugares = list(csv.DictReader(open(PROC / "selecionados.csv", encoding="utf-8")))
    if ids:
        lugares = [l for l in lugares if l["lugar_id"] in ids]
    hoje = date.today().isoformat()
    feitos = []
    for l in list(lugares):
        m = PAGINAS / l["lugar_id"] / "manifesto.json"
        if not ids and m.exists() and json.loads(m.read_text(encoding="utf-8"))["data"] == hoje:
            feitos.append(json.loads(m.read_text(encoding="utf-8")))  # já rastreado hoje
            lugares.remove(l)
    robo = Robo()

    def seguro(l):
        try:
            return rastrear_lugar(robo, l)
        except Exception as e:  # um site estranho não derruba a rodada
            man = {"lugar_id": l["lugar_id"], "site": l["site"], "dominio": dominio(l["site"]), "status": "erro_robo",
                   "motivo": type(e).__name__, "data": hoje, "paginas": []}
            (PAGINAS / l["lugar_id"]).mkdir(parents=True, exist_ok=True)
            (PAGINAS / l["lugar_id"] / "manifesto.json").write_text(json.dumps(man, ensure_ascii=False),
                                                                    encoding="utf-8")
            return man

    with ThreadPoolExecutor(R["trabalhadores"]) as ex:
        mans = list(ex.map(seguro, lugares))
    novos = len(mans)
    mans += feitos
    cont = {}
    for m in mans:
        cont[m["status"]] = cont.get(m["status"], 0) + 1
    return {"lugares": len(mans), "rastreados_agora": novos, "status": cont,
            "paginas": sum(len(m["paginas"]) for m in mans),
            "paginas_mudaram": sum(p.get("mudou", True) for m in mans for p in m["paginas"])}


def limpar():
    """Apaga as páginas brutas e os textos com mais de reter_dias. Os manifestos (com os hashes) ficam."""
    limite = time.time() - timedelta(days=R["reter_dias"]).total_seconds()
    n = 0
    for arq in PAGINAS.glob("*/*"):
        if arq.name != "manifesto.json" and arq.stat().st_mtime < limite:
            arq.unlink()
            n += 1
    return {"apagados": n}
