"""Etapa 1: baixar o recorte do DF da Overture, mapear as categorias e gravar os candidatos.

Lista fechada de campos: telefone, e-mail e redes sociais nunca são lidos (ADR 0004, LGPD).
"""
import csv
from urllib.parse import urlparse

import duckdb

from . import categorias
from .config import CFG, PROC, overture_arquivo
from .regioes import Localizador

S3 = "s3://overturemaps-us-west-2/release/{rel}/theme=places/type=place/*"

# Redes, agregadores, encurtadores e plataformas de delivery: o robô não entra (ADR 0005, Fontes permitidas).
BLOQUEADOS = {
    "instagram.com", "facebook.com", "fb.com", "fb.me", "m.facebook.com", "wa.me", "api.whatsapp.com",
    "whatsapp.com", "whats.link", "linktr.ee", "linklist.bio", "bio.site", "bio.link", "beacons.ai",
    "linkme.bio", "taplink.cc", "linkin.bio", "ifood.com.br", "tripadvisor.com", "tripadvisor.com.br",
    "sympla.com.br", "google.com", "goo.gl", "g.page", "maps.app.goo.gl", "business.site", "sites.google.com",
    "twitter.com", "x.com", "tiktok.com", "youtube.com", "youtu.be", "bit.ly", "encurtador.com.br", "tinyurl.com",
    "ubereats.com", "rappi.com.br", "anota.ai", "goomer.app", "menudino.com", "cardapioweb.com", "aiqfome.com",
    "deliverydireto.com.br", "delivery.much.com.br", "olaclick.com", "pedir.delivery", "eventim.com.br",
    "ingresse.com", "bileto.sympla.com.br", "shotgun.live", "instadelivery.com.br", "business.monster",
    "clicoupizza.com", "goomer.com.br", "cardapio.ai", "neemo.com.br", "saipos.com", "pedido.anota.ai",
    # Geradores automáticos de páginas de negócios e guias: o conteúdo não é do lugar.
    "placeweb.site", "negocio.site", "placestars.com", "amawebs.com", "ola.click", "deeliv.app",
    "foursquare.com", "kekanto.com", "soubrasilia.com",
}


def dominio(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


def bloqueado(dom: str) -> bool:
    return not dom or "." not in dom or any(dom == b or dom.endswith("." + b) for b in BLOQUEADOS)


def normalizar_site(url: str) -> str:
    url = url.strip()
    if not url.lower().startswith(("http://", "https://")):
        url = "https://" + url.lstrip("/")
    return url


def baixar():
    destino = overture_arquivo()
    if destino.exists():
        return destino
    destino.parent.mkdir(parents=True, exist_ok=True)
    o, s, l, n = CFG["pipeline"]["bbox"]
    c = duckdb.connect()
    c.sql("INSTALL httpfs; LOAD httpfs; SET s3_region='us-west-2';")
    src = S3.format(rel=CFG["pipeline"]["release_overture"])
    c.sql(f"""COPY (SELECT * FROM read_parquet('{src}', hive_partitioning=1)
              WHERE bbox.xmin BETWEEN {o} AND {l} AND bbox.ymin BETWEEN {s} AND {n})
              TO '{destino.as_posix()}' (FORMAT parquet)""")
    return destino


CAMPOS = ["overture_id", "nome", "categoria", "tipo_role", "estrato", "ra", "regiao", "lat", "lon",
          "site", "dominio", "confianca", "endereco_overture", "licenca", "categoria_overture", "status_overture"]


def executar():
    arq = baixar()
    c = duckdb.connect()
    linhas = c.sql(f"""
        SELECT id, names.primary, confidence, websites, basic_category, taxonomy.primary, taxonomy.hierarchy,
               bbox.xmin, bbox.ymin, addresses[1].freeform, list_distinct([s.license for s in sources]),
               operating_status
        FROM read_parquet('{arq.as_posix()}')""").fetchall()
    loc = Localizador()
    out, contagem = [], {"total": len(linhas), "sem_categoria": 0, "fora_do_df": 0, "fechado": 0,
                         "sem_site_permitido": 0}
    for (oid, nome, conf, sites, basica, prim, hier, lon, lat, end, lic, st) in linhas:
        cat = categorias.mapear(basica, prim, hier)
        if not cat or not nome:
            contagem["sem_categoria"] += 1
            continue
        if st and st != "open":
            contagem["fechado"] += 1
            continue
        ra = loc.ra(lon, lat)
        if not ra:
            contagem["fora_do_df"] += 1
            continue
        site = next((normalizar_site(w) for w in (sites or []) if not bloqueado(dominio(normalizar_site(w)))), "")
        if not site:
            contagem["sem_site_permitido"] += 1
        out.append({
            "overture_id": oid, "nome": nome.strip(), "categoria": cat, "tipo_role": categorias.TIPO[cat],
            "estrato": categorias.estrato(cat), "ra": ra[0], "regiao": ra[1], "lat": round(lat, 6),
            "lon": round(lon, 6), "site": site, "dominio": dominio(site) if site else "",
            "confianca": round(conf or 0, 3), "endereco_overture": end or "", "licenca": ";".join(sorted(lic or [])),
            "categoria_overture": prim or basica or "", "status_overture": st or "",
        })
    PROC.mkdir(parents=True, exist_ok=True)
    with open(PROC / "candidatos.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS)
        w.writeheader()
        w.writerows(out)
    contagem["candidatos"] = len(out)
    contagem["com_site"] = sum(1 for r in out if r["site"])
    return contagem
