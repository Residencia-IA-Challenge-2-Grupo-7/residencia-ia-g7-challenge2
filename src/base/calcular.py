"""Etapa 7: custo por pessoa, estados por idade, fichas do índice e CSVs versionados.

O custo segue a fórmula do guia de curadoria (RNF-04: o código calcula, o LLM não). A ficha é gerada só a
partir dos campos validados; nada é escrito à mão nem copiado do site (ADR 0005, Documentos indexados).
"""
import csv
import hashlib
import json
import re
import statistics
from collections import defaultdict
from datetime import date

from .config import BASE, CFG, PROC, VERSAO
from .normalizar import DIAS
from .regioes import REGIOES, RAS, Localizador

E = CFG["estados"]
CATEGORIA_TEXTO = {
    "restaurante": "restaurante", "bar": "bar", "cafe": "café", "lanchonete": "lanchonete",
    "sorveteria": "sorveteria", "parque": "parque", "mirante": "mirante", "feira": "feira", "museu": "museu",
    "centro_cultural": "centro cultural", "teatro": "teatro", "casa_de_show": "casa de show", "outro": "passeio",
}
DIA_TEXTO = {"seg": "segunda", "ter": "terça", "qua": "quarta", "qui": "quinta", "sex": "sexta",
             "sab": "sábado", "dom": "domingo"}
ALIM = {"alim_vegetariano": "vegetariana", "alim_vegano": "vegana", "alim_sem_gluten": "sem glúten",
        "alim_sem_lactose": "sem lactose"}
# Termos proibidos na descrição (modelo do guia: linguagem neutra, sem propaganda)
PROPAGANDA = re.compile(r"\b(melhor|imperd[ií]vel|incr[ií]vel|perfeit|maravilh|sensacional|[uú]nic[oa]|"
                        r"excelente|espetacular|inesquec[ií]vel|delicios)", re.I)


def estado(tipo: str, verificado_em: str | None, hoje: date | None = None) -> str:
    if not verificado_em:
        return "vencido"
    idade = ((hoje or date.today()) - date.fromisoformat(verificado_em)).days
    exato, aprox = E[tipo]
    return "exato" if idade <= exato else "aproximado" if idade <= aprox else "vencido"


def custo(categoria: str, itens: list[dict], couvert, taxa_pct, entrada) -> tuple[float | None, float | None]:
    """(mínimo, típico) por pessoa. Pedido típico usa a mediana de cada papel (o item mais comum)."""
    if entrada is not None and categoria not in ("restaurante", "bar", "cafe", "lanchonete", "sorveteria"):
        return entrada, entrada
    p = defaultdict(list)
    for i in itens:
        p[i["papel"]].append(i["preco"])
    med = lambda k: statistics.median(p[k]) if p[k] else None  # noqa: E731
    tip = mn = None
    if categoria == "restaurante" and p["principal"]:
        tip = med("principal") + (med("bebida_nao_alcoolica") or 0)
        mn = min(p["principal"])
    elif categoria == "bar" and p["bebida"]:
        tip = (med("porcao") or 0) / 2 + 2 * med("bebida")
        mn = min(p["bebida"])
    elif categoria == "bar" and p["principal"]:
        # Bar sem preço de bebida no site: o pedido típico vira o de restaurante, sem estimar a bebida.
        tip = med("principal") + (med("bebida_nao_alcoolica") or 0)
        mn = min(p["principal"])
    elif categoria in ("cafe", "lanchonete") and p["principal"]:
        tip = med("principal") + (med("bebida_nao_alcoolica") or 0)
        mn = min(x for v in p.values() for x in v)
    elif categoria == "sorveteria" and p["principal"]:
        tip, mn = med("principal"), min(p["principal"])
    if tip is None:
        return None, None
    fator = 1 + (taxa_pct or 0) / 100
    extra = couvert or 0
    return round(min(mn, tip) * fator + extra, 2), round(tip * fator + extra, 2)


def _resumo_dias(horarios: list[dict]) -> str:
    abertos = [d for d in DIAS if any(h["dia"] == d for h in horarios)]
    if len(abertos) == 7:
        return "todos os dias"
    return ", ".join(DIA_TEXTO[d] for d in abertos)


def ficha_lugar(l: dict) -> str:
    a = l["atributos"]
    cat = CATEGORIA_TEXTO[l["categoria"]]
    partes = [f"{l['nome']} — {cat} em {l['ra']} ({REGIOES[l['regiao']]})."]
    if l.get("descricao"):
        partes.append(l["descricao"])
    amb = []
    if a.get("ruido"):
        amb.append({"baixo": "ambiente tranquilo", "medio": "música ambiente", "alto": "som alto ou música ao vivo"}
                   [a["ruido"]])
    if a.get("ar_livre") == "sim":
        amb.append("ao ar livre")
    if a.get("coberto") == "sim":
        amb.append("área coberta")
    if a.get("foco_alcool") == "sim":
        amb.append("foco em bebida alcoólica")
    if amb:
        partes.append("Ambiente: " + "; ".join(amb) + ".")
    if l["tipo_role"] == "comer_beber" and l.get("custo_pessoa_tipico") is not None:
        partes.append(f"Preço típico por pessoa: R$ {l['custo_pessoa_tipico']:.0f}.")
    elif l.get("taxa_entrada") == 0:
        partes.append("Entrada gratuita.")
    elif l.get("taxa_entrada"):
        partes.append(f"Entrada: R$ {l['taxa_entrada']:.0f}.")
    opc = [t for k, t in ALIM.items() if a.get(k) == "sim"]
    if opc:
        partes.append("Opções " + ", ".join(opc) + ".")
    if l.get("itens"):
        partes.append("No cardápio: " + ", ".join(i["item"] for i in l["itens"][:6]) + ".")
    if l["horarios"]:
        partes.append(f"Abre: {_resumo_dias(l['horarios'])}.")
    return " ".join(partes)


def ficha_evento(e: dict, local: dict) -> str:
    d = date.fromisoformat(e["data"])
    preco = "Gratuito." if e["gratuito"] else (
        f"R$ {e['preco_min']:.0f}." if e["preco_min"] == e["preco_max"] else
        f"R$ {e['preco_min']:.0f} a R$ {e['preco_max']:.0f}.")
    return (f"{e['titulo']} — {DIA_TEXTO[DIAS[d.weekday()]]}, {d.strftime('%d/%m')} às {e['hora']}, em "
            f"{local['nome']} ({local['ra']}, {REGIOES[local['regiao']]}). {preco}")


def _descricoes() -> dict:
    arq = PROC / "descricao" / "saida.json"
    if not arq.exists():
        return {}
    out = {}
    for lid, txt in json.loads(arq.read_text(encoding="utf-8")).items():
        txt = (txt or "").strip()
        if 0 < len(txt) <= 300 and not PROPAGANDA.search(txt):
            out[lid] = txt
    return out


def _hash(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()[:16]


def executar():
    val = json.loads((PROC / "validados.json").read_text(encoding="utf-8"))
    desc = _descricoes()
    hoje = date.today().isoformat()
    lugares, itens, eventos = [], [], []
    for v in (x for x in val if x["aprovado"]):
        ent = v.get("entrada")
        taxa_entrada = ent["valor"] if ent else None
        couv = (v.get("couvert") or {}).get("valor")
        serv = (v.get("taxa_servico_pct") or {}).get("valor")
        mn, tip = custo(v["categoria"], v["itens"], couv, serv, taxa_entrada)
        ver = v["verificado_em"]
        fontes_h = sorted({h["fonte"] for h in v["horarios"]})
        fontes_p = sorted({i["fonte"] for i in v["itens"]})
        l = {
            "id": v["lugar_id"], "overture_id": v["overture_id"], "nome": v["nome"], "tipo_role": v["tipo_role"],
            "categoria": v["categoria"],
            "endereco": (v.get("endereco") or {}).get("valor") or v["endereco_overture"],
            "ra": v["ra"], "regiao": v["regiao"], "lat": float(v["lat"]), "lon": float(v["lon"]),
            "coord_fonte": "overture", "site_oficial": v["site"],
            "horarios": [{k: h[k] for k in ("dia", "abre", "fecha")} for h in v["horarios"]],
            "horarios_fonte": " ".join(fontes_h), "horarios_verificado_em": ver if v["horarios"] else None,
            "couvert": couv, "taxa_servico_pct": serv,
            "precos_fonte": " ".join(fontes_p), "precos_verificado_em": ver if v["itens"] else None,
            "custo_pessoa_min": mn, "custo_pessoa_tipico": tip, "taxa_entrada": taxa_entrada,
            "atributos": {k: x["valor"] for k, x in v["atributos"].items()},
            "atributos_verificado_em": ver if v["atributos"] else None,
            "status": "ativo", "status_fonte": v["site"], "status_verificado_em": ver,
            "descricao": desc.get(v["lugar_id"], ""), "licenca_origem": v["licenca"],
            "pipeline_versao": VERSAO, "modelo_extracao": CFG["extracao"]["modelo"],
            "criado_em": ver, "atualizado_em": hoje, "itens": v["itens"],
        }
        estados = [estado("horario", l["horarios_verificado_em"])] if l["horarios"] else []
        if l["tipo_role"] == "comer_beber":
            estados.append(estado("preco", l["precos_verificado_em"]))
        elif taxa_entrada is not None:
            estados.append(estado("taxa_entrada", ver))
        l["estado"] = "vencido" if "vencido" in estados else "aproximado" if "aproximado" in estados else "exato"
        l["ficha"] = ficha_lugar(l)
        lugares.append(l)
        itens += [{"lugar_id": l["id"], **{k: i[k] for k in ("item", "preco", "papel", "fonte")},
                   "verificado_em": ver} for i in v["itens"]]
        for e in v.get("eventos", []):
            eid = "evt-" + _hash(f"{l['id']}|{e['titulo']}|{e['data']}|{e['hora']}")[:10]
            eventos.append({"id": eid, "local_id": l["id"], "titulo": e["titulo"],
                            "inicio": f"{e['data']}T{e['hora']}", "preco_min": e["preco_min"],
                            "preco_max": e["preco_max"], "gratuito": e["gratuito"],
                            "link_oficial": e["link_oficial"], "regiao": l["regiao"],
                            "verificado_em": e["verificado_em"], "estado": estado("evento", e["verificado_em"]),
                            "pipeline_versao": VERSAO, "ficha": ficha_evento(e, l)})
    viz = Localizador().vizinhas()
    regioes = [{"ra": nome, "regiao": reg, "vizinhas": viz[nome],
                "ficha": f"{nome} — região administrativa do DF, na região {REGIOES[reg]}. "
                         f"Faz divisa com {', '.join(viz[nome])}."}
               for nome, reg in sorted(RAS.values())]

    fichas = {"lugares": lugares, "eventos": eventos, "regioes": regioes}
    (PROC / "fichas.json").write_text(json.dumps(fichas, ensure_ascii=False, indent=1), encoding="utf-8")
    _csvs(lugares, itens, eventos, regioes)
    return {"lugares": len(lugares), "itens": len(itens), "eventos": len(eventos), "regioes": len(regioes),
            "com_descricao": sum(1 for l in lugares if l["descricao"]),
            "com_custo": sum(1 for l in lugares if l["custo_pessoa_tipico"] is not None)}


def _csvs(lugares, itens, eventos, regioes):
    BASE.mkdir(parents=True, exist_ok=True)
    cols = [k for k in lugares[0] if k not in ("itens", "ficha")] if lugares else []

    def gravar(nome, linhas, campos):
        with open(BASE / nome, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=campos, extrasaction="ignore")
            w.writeheader()
            for r in linhas:
                w.writerow({k: json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v
                            for k, v in r.items()})

    gravar("lugares.csv", lugares, cols)
    gravar("itens.csv", itens, ["lugar_id", "item", "preco", "papel", "fonte", "verificado_em"])
    gravar("eventos.csv", eventos, ["id", "local_id", "titulo", "inicio", "preco_min", "preco_max", "gratuito",
                                     "link_oficial", "verificado_em", "pipeline_versao"])
    gravar("regioes.csv", regioes, ["ra", "regiao", "vizinhas"])
