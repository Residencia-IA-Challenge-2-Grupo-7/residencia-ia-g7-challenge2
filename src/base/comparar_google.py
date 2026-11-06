"""Comparação interna de cobertura: Google Places (New) × OpenStreetMap × Overture × nossa base.

Regras dos termos da Google (ADR 0004), seguidas aqui:
- nada da Google é gravado: as respostas ficam só na memória; o arquivo de saída tem apenas contagens
  ("tem horário: sim/não", "horário igual ao do OSM: sim/não"), sem valores nem place IDs;
- a concordância de valores é medida só contra OSM e Overture, nunca contra o que o nosso extrator (um LLM)
  produziu, porque isso seria usar conteúdo da Google para validar IA (3.2.3(c)(vii));
- o resultado é interno e não vai para o site público (3.2.4).

Chamadas: Text Search só com IDs (sem custo) e Place Details com campos Enterprise + Atmosphere
(1.000 gratuitas por mês). Chave em GOOGLE_PLACES_API_KEY (variável de ambiente ou .env, fora do git).
"""
import csv
import json
import math
import os
import random
import re
import time
from collections import Counter, defaultdict

import requests

from . import osm
from .config import CFG, PROC, RAIZ
from .normalizar import DIAS, norm, sem_acento
from .regioes import REGIOES

CAMPOS = ",".join([
    "id", "displayName", "location", "businessStatus", "regularOpeningHours", "priceLevel", "priceRange",
    "servesVegetarianFood", "outdoorSeating", "liveMusic", "servesBeer", "servesWine", "servesCocktails",
    "accessibilityOptions", "reservable", "goodForGroups", "websiteUri",
])
_PAL = re.compile(r"[a-z0-9]{3,}")
_DIA_OSM = {"Mo": 0, "Tu": 1, "We": 2, "Th": 3, "Fr": 4, "Sa": 5, "Su": 6}


def _chave() -> str:
    k = os.environ.get("GOOGLE_PLACES_API_KEY")
    env = RAIZ / ".env"
    if not k and env.exists():
        for linha in env.read_text(encoding="utf-8").splitlines():
            if linha.startswith("GOOGLE_PLACES_API_KEY="):
                k = linha.split("=", 1)[1].strip().strip('"')
    if not k:
        raise SystemExit("Defina GOOGLE_PLACES_API_KEY no .env (fora do git) ou no ambiente.")
    return k


def _palavras(nome: str) -> set[str]:
    return set(_PAL.findall(sem_acento(norm(nome)))) - {"restaurante", "bar", "lanchonete", "cafe", "brasilia"}


def _distancia(a, b) -> float:
    dy = (a[0] - b[0]) * 111_320
    dx = (a[1] - b[1]) * 111_320 * math.cos(math.radians(a[0]))
    return math.hypot(dx, dy)


def buscar_google(s: requests.Session, lugar: dict) -> dict | None:
    lat, lon = float(lugar["lat"]), float(lugar["lon"])
    r = s.post("https://places.googleapis.com/v1/places:searchText",
               headers={"X-Goog-FieldMask": "places.id"},
               json={"textQuery": f"{lugar['nome']}, {lugar['ra']}, Brasília - DF", "languageCode": "pt-BR",
                     "regionCode": "BR", "pageSize": 1,
                     "locationBias": {"circle": {"center": {"latitude": lat, "longitude": lon}, "radius": 500.0}}},
               timeout=20)
    r.raise_for_status()
    achados = r.json().get("places") or []
    if not achados:
        return None
    d = s.get(f"https://places.googleapis.com/v1/places/{achados[0]['id']}",
              headers={"X-Goog-FieldMask": CAMPOS}, params={"languageCode": "pt-BR"}, timeout=20)
    d.raise_for_status()
    p = d.json()
    loc = p.get("location") or {}
    perto = loc and _distancia((lat, lon), (loc["latitude"], loc["longitude"])) < 250
    nome_ok = len(_palavras(lugar["nome"]) & _palavras((p.get("displayName") or {}).get("text", ""))) >= \
        max(1, len(_palavras(lugar["nome"])) / 2)
    return p if perto and nome_ok else None


def horario_google(p: dict) -> dict | None:
    periodos = (p.get("regularOpeningHours") or {}).get("periods")
    if not periodos:
        return None
    out = {d: set() for d in DIAS}
    for per in periodos:
        a, f = per.get("open", {}), per.get("close")
        dia = DIAS[(a.get("day", 0) + 6) % 7]  # Google: 0 = domingo
        if f is None:  # aberto 24 horas
            out[dia].add(("00:00", "00:00"))
            continue
        out[dia].add((f"{a.get('hour', 0):02d}:{a.get('minute', 0):02d}",
                      f"{f.get('hour', 0):02d}:{f.get('minute', 0):02d}"))
    return out


def horario_osm(texto: str) -> dict | None:
    """Leitor do opening_hours do OSM para os formatos comuns ("Mo-Fr 11:00-23:00; Sa 12:00-15:00"); senão None."""
    if texto.strip() == "24/7":
        return {d: {("00:00", "00:00")} for d in DIAS}
    out = {d: set() for d in DIAS}
    for regra in texto.split(";"):
        regra = regra.strip()
        if not regra or regra.startswith("PH"):
            continue
        m = re.fullmatch(r"((?:Mo|Tu|We|Th|Fr|Sa|Su)(?:[-,](?:Mo|Tu|We|Th|Fr|Sa|Su))*)\s+(off|closed|[\d:,\-\s]+)",
                         regra)
        if not m:
            return None
        dias = set()
        for parte in m.group(1).split(","):
            if "-" in parte:
                i, j = (_DIA_OSM[x] for x in parte.split("-"))
                dias |= {(i + k) % 7 for k in range((j - i) % 7 + 1)}
            else:
                dias.add(_DIA_OSM[parte])
        for d in dias:
            out[DIAS[d]] = set()
            if m.group(2) in ("off", "closed"):
                continue
            for faixa in m.group(2).split(","):
                a, _, f = faixa.strip().partition("-")
                if not re.fullmatch(r"\d{2}:\d{2}", a) or not re.fullmatch(r"\d{2}:\d{2}", f):
                    return None
                out[DIAS[d]].add((a, "00:00" if f == "24:00" else f))
    return out


def amostra(n_por_regiao: int) -> list[dict]:
    """Os aprovados da base mais um sorteio de comer e beber por região entre todos os candidatos da
    Overture, com ou sem site: é onde a nossa rota não chega que a comparação importa."""
    from .selecionar import lugar_id
    cand = list(csv.DictReader(open(PROC / "candidatos.csv", encoding="utf-8")))
    for r in cand:
        r["lugar_id"] = lugar_id(r["overture_id"])
    val = {v["lugar_id"]: v for v in json.loads((PROC / "validados.json").read_text(encoding="utf-8"))}
    rng = random.Random(CFG["pipeline"]["semente"] + 1)
    escolhidos = [r for r in cand if val.get(r["lugar_id"], {}).get("aprovado")]
    ja = {r["lugar_id"] for r in escolhidos}
    por_reg = defaultdict(list)
    for r in sorted(cand, key=lambda r: r["overture_id"]):
        if r["tipo_role"] == "comer_beber" and r["lugar_id"] not in ja and float(r["confianca"]) >= 0.5:
            por_reg[r["regiao"]].append(r)
    for reg in REGIOES:
        escolhidos += rng.sample(por_reg[reg], min(n_por_regiao, len(por_reg[reg])))
    return escolhidos


def executar(n_por_regiao: int = 8):
    s = requests.Session()
    s.headers["X-Goog-Api-Key"] = _chave()
    val = {v["lugar_id"]: v for v in json.loads((PROC / "validados.json").read_text(encoding="utf-8"))}
    celulas = {}
    for p in osm._pontos():
        celulas.setdefault((round(p["lat"] * 500), round(p["lon"] * 500)), []).append(p)

    cont = defaultdict(Counter)  # região → contagens; "total" soma tudo
    for lugar in amostra(n_por_regiao):
        reg = lugar["regiao"]
        try:
            g = buscar_google(s, lugar)
        except requests.HTTPError as e:
            raise SystemExit(f"Google respondeu {e.response.status_code}: confira a chave, a API e as cotas.")
        time.sleep(0.2)
        o = osm._casar(lugar, celulas)
        nossa = val.get(lugar["lugar_id"], {})
        linhas = {
            "lugares": True,
            "overture_site": bool(lugar["site"]),
            "osm_encontrado": bool(o), "osm_horario": bool(o and "opening_hours" in o["tags"]),
            "osm_vegetariano": bool(o and "diet:vegetarian" in o["tags"]),
            "osm_acessibilidade": bool(o and "wheelchair" in o["tags"]),
            "osm_area_externa": bool(o and "outdoor_seating" in o["tags"]),
            "base_aprovado": bool(nossa.get("aprovado")), "base_horario": bool(nossa.get("horarios")),
            "base_preco": len(nossa.get("itens") or []) >= 3,
            "google_encontrado": bool(g),
        }
        if g:
            acc = g.get("accessibilityOptions") or {}
            linhas.update({
                "google_operando": g.get("businessStatus") == "OPERATIONAL",
                "google_horario": bool((g.get("regularOpeningHours") or {}).get("periods")),
                "google_faixa_preco": bool(g.get("priceRange")),
                "google_nivel_preco": bool(g.get("priceLevel")),
                "google_vegetariano": "servesVegetarianFood" in g,
                "google_area_externa": "outdoorSeating" in g,
                "google_musica_ao_vivo": "liveMusic" in g,
                "google_alcool": any(k in g for k in ("servesBeer", "servesWine", "servesCocktails")),
                "google_acess_entrada": "wheelchairAccessibleEntrance" in acc,
                "google_acess_banheiro": "wheelchairAccessibleRestroom" in acc,
                "google_reserva": "reservable" in g,
                "google_grupos": "goodForGroups" in g,
                "google_site": bool(g.get("websiteUri")),
            })
            gh = horario_google(g)
            oh = horario_osm(o["tags"]["opening_hours"]) if o and "opening_hours" in o["tags"] else None
            if gh and oh:
                iguais = sum(gh[d] == oh[d] for d in DIAS)
                linhas["horario_google_e_osm"] = True
                linhas["horario_google_igual_osm_7_dias"] = iguais == 7
                cont[reg]["dias_iguais_google_osm"] += iguais
        for k, v in linhas.items():
            cont[reg][k] += int(bool(v))
        del g  # nada da Google sai desta iteração

    total = Counter()
    for c in cont.values():
        total.update(c)
    out = {"por_regiao": {REGIOES[r]: dict(c) for r, c in cont.items()}, "total": dict(total),
           "observacao": "Só contagens. Nenhum valor nem ID da Google foi gravado (ADR 0004)."}
    (PROC / "comparacao_fontes.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out
