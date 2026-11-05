"""Medição do OpenStreetMap no DF: só consulta, nada é importado para a base (ADR 0004, ODbL).

Responde a duas perguntas: quanto o OSM tem de horário, site e atributos nos tipos de rolê, e quanto ele
cobriria dos lugares que a Overture e os sites oficiais não cobriram. Grava só contagens agregadas.
"""
import csv
import json
import re
import socket
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

import requests

from .config import CFG, PAGINAS, PROC, RAW
from .descobrir import bloqueado, dominio, normalizar_site
from .normalizar import norm, sem_acento
from .regioes import Localizador

ARQ = RAW / "osm" / "df_lazer.json"
CONSULTA = """[out:json][timeout:240];area["ISO3166-2"="BR-DF"]->.df;(
nwr["amenity"~"^(restaurant|bar|pub|cafe|fast_food|ice_cream|biergarten|food_court|theatre|arts_centre|nightclub|marketplace)$"](area.df);
nwr["leisure"="park"](area.df);nwr["tourism"~"^(museum|viewpoint|gallery)$"](area.df););out center tags;"""

TIPO = {"restaurant": "comer_beber", "bar": "comer_beber", "pub": "comer_beber", "cafe": "comer_beber",
        "fast_food": "comer_beber", "ice_cream": "comer_beber", "biergarten": "comer_beber",
        "food_court": "comer_beber", "theatre": "local_evento", "arts_centre": "local_evento",
        "nightclub": "local_evento", "marketplace": "ar_livre_gratuito", "park": "ar_livre_gratuito",
        "museum": "ar_livre_gratuito", "viewpoint": "ar_livre_gratuito", "gallery": "ar_livre_gratuito"}
ATRIBUTOS = ["opening_hours", "website", "cuisine", "diet:vegetarian", "diet:vegan", "wheelchair",
             "outdoor_seating", "check_date", "check_date:opening_hours", "fee", "charge"]
_PAL = re.compile(r"[a-z0-9]{3,}")


def baixar():
    ARQ.parent.mkdir(parents=True, exist_ok=True)
    r = requests.post("https://overpass-api.de/api/interpreter", data={"data": CONSULTA},
                      headers={"User-Agent": CFG["robo"]["user_agent"]}, timeout=300)
    r.raise_for_status()
    ARQ.write_bytes(r.content)


def _pontos():
    if not ARQ.exists():
        baixar()
    for e in json.loads(ARQ.read_text(encoding="utf-8"))["elements"]:
        t = e.get("tags", {})
        lat = e.get("lat") or e.get("center", {}).get("lat")
        lon = e.get("lon") or e.get("center", {}).get("lon")
        chave = t.get("amenity") or t.get("leisure") or t.get("tourism")
        if lat is None or chave not in TIPO:
            continue
        yield {"tipo": TIPO[chave], "chave": chave, "nome": t.get("name", ""), "lat": lat, "lon": lon, "tags": t}


def _palavras(nome):
    return set(_PAL.findall(sem_acento(norm(nome)))) - {"restaurante", "bar", "lanchonete", "cafe", "parque"}


def _casar(lugar, osm_por_celula):
    """Mesmo lugar no OSM: a menos de 150 m e com metade das palavras do nome em comum."""
    lat, lon = float(lugar["lat"]), float(lugar["lon"])
    p = _palavras(lugar["nome"])
    if not p:
        return None
    melhor = None
    for dlat in (-1, 0, 1):
        for dlon in (-1, 0, 1):
            for o in osm_por_celula.get((round(lat * 500) + dlat, round(lon * 500) + dlon), []):
                d = ((o["lat"] - lat) * 111_320, (o["lon"] - lon) * 107_000)
                if (d[0] ** 2 + d[1] ** 2) ** 0.5 > 150:
                    continue
                comum = len(p & _palavras(o["nome"]))
                if comum >= max(1, len(p) / 2) and (not melhor or comum > melhor[0]):
                    melhor = (comum, o)
    return melhor[1] if melhor else None


def _vivo(url):
    try:
        socket.getaddrinfo(urlparse(url).hostname, None)
        return True
    except (socket.gaierror, UnicodeError, TypeError):
        return False


def medir():
    loc = Localizador()
    pts = [p for p in _pontos() if p["nome"] and loc.ra(p["lon"], p["lat"])]
    por_tipo = Counter(p["tipo"] for p in pts)
    tags = {t: {tp: sum(1 for p in pts if p["tipo"] == tp and t in p["tags"]) for tp in por_tipo} for t in ATRIBUTOS}
    anos = Counter((p["tags"].get("check_date:opening_hours") or p["tags"].get("check_date") or "")[:4]
                   for p in pts if "opening_hours" in p["tags"])

    # Sites do OSM: quantos domínios ainda existem (a Overture teve 52% de domínios mortos no piloto)
    sites = [normalizar_site(p["tags"]["website"]) for p in pts if "website" in p["tags"]]
    sites = [s for s in sites if not bloqueado(dominio(s))]
    with ThreadPoolExecutor(32) as ex:
        vivos = sum(ex.map(_vivo, sites))

    # Cruzamento com os lugares do piloto e com todos os elegíveis da Overture
    celulas = {}
    for p in pts:
        celulas.setdefault((round(p["lat"] * 500), round(p["lon"] * 500)), []).append(p)
    sel = list(csv.DictReader(open(PROC / "selecionados.csv", encoding="utf-8")))
    fila = list(csv.DictReader(open(PROC / "sorteio.csv", encoding="utf-8")))

    def cobertura(lugares):
        c = Counter()
        for l in lugares:
            o = _casar(l, celulas)
            c["lugares"] += 1
            if o:
                c["no_osm"] += 1
                c["com_horario"] += "opening_hours" in o["tags"]
                c["com_site"] += "website" in o["tags"]
        return dict(c)

    sem_dados = []
    for l in sel:
        m = PAGINAS / l["lugar_id"] / "manifesto.json"
        st = json.loads(m.read_text(encoding="utf-8"))["status"] if m.exists() else ""
        if st != "ok":
            sem_dados.append(l)
    out = {
        "pontos_osm_no_df": len(pts), "por_tipo": dict(por_tipo),
        "com_tag": tags, "ano_da_conferencia_do_horario": dict(sorted(anos.items())),
        "sites_osm": len(sites), "sites_osm_dominio_vivo": vivos,
        "piloto": cobertura(sel), "piloto_site_falhou": cobertura(sem_dados),
        "elegiveis_overture": cobertura(fila),
    }
    (PROC / "osm_medicao.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out
