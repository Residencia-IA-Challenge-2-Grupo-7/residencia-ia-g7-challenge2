"""Etapa 5: validar em código o que o LLM extraiu (ADR 0005, Extração por LLM com evidência literal).

Um valor só é aceito se:
1. o trecho de evidência existe literalmente no texto da página baixada;
2. o valor normalizado aparece no trecho;
3. o valor passa nas regras de plausibilidade;
4. não há contradição entre páginas do mesmo site.
Depois, o lugar só entra na base com os campos obrigatórios do seu tipo.
"""
import csv
import json
import re
from collections import Counter, defaultdict
from datetime import date, timedelta

from . import normalizar as nz
from .config import CFG, EXTRACAO, PAGINAS, PROC

P = CFG["plausibilidade"]
EVID_MAX = CFG["extracao"]["evidencia_max_chars"]
PAPEIS = {"principal", "bebida_nao_alcoolica", "bebida", "porcao", "acompanhamento", "ingresso"}

# Palavras que justificam cada valor de atributo (prefixos, sem acento). Ver o guia de curadoria.
LEXICO = {
    "alim_vegetariano": {"sim": ["vegetarian"]},
    "alim_vegano": {"sim": ["vegan"]},
    "alim_sem_gluten": {"sim": ["sem gluten", "gluten free", "gluten-free", "zero gluten", "glutenfree"]},
    "alim_sem_lactose": {"sim": ["sem lactose", "zero lactose", "lactose free", "lactose-free"]},
    "ar_livre": {"sim": ["ar livre", "area externa", "varanda", "terraco", "deck", "rooftop", "jardim",
                         "mesas externas", "area aberta", "quintal"]},
    "coberto": {"sim": ["coberto", "coberta", "salao", "ambiente interno", "area interna", "climatizad",
                        "ar condicionado", "ar-condicionado"]},
    "acess_entrada_sem_degrau": {"sim": ["rampa", "cadeirante", "acessivel", "acessibilidade",
                                         "mobilidade reduzida", "pcd"]},
    "acess_banheiro_adaptado": {"sim": ["banheiro adaptado", "banheiros adaptados", "banheiro acessivel",
                                        "banheiros acessiveis", "sanitario adaptado", "sanitario acessivel",
                                        "sanitarios adaptados", "banheiro pcd", "banheiro para cadeirante"]},
    "ruido": {"alto": ["musica ao vivo", "dj", "show", "balada", "som ao vivo", "banda"],
              "medio": ["musica ambiente"], "baixo": ["tranquil", "silencio", "calm", "sossego"]},
    "foco_alcool": {"sim": ["choperia", "chopperia", "cervejaria", "carta de drinks", "drinks", "drinques",
                            "boteco", "adega", "chope", "chopp", "cerveja artesanal", "open bar", "coquetelaria",
                            "wine bar", "bar de vinhos", "vinhoteca", "enoteca"]},
    "exige_reserva": {"sim": ["somente com reserva", "apenas com reserva", "reserva obrigatoria",
                              "mediante reserva", "mediante agendamento", "agendamento previo",
                              "necessario reservar", "necessario agendar"],
                      "nao": ["nao aceitamos reserva", "nao fazemos reserva", "nao trabalhamos com reserva",
                              "ordem de chegada", "sem reserva"]},
}
# Atributos que decorrem da categoria (método "calculado"), quando o site não diz nada.
POR_CATEGORIA = {"parque": {"ar_livre": "sim"}, "mirante": {"ar_livre": "sim"}}

_PESSOAL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+|\(?\b\d{2}\)?\s?9?\d{4}[-\s]?\d{4}\b")
_PALAVRA = re.compile(r"[a-z0-9]{3,}")


def _tem(lex: list[str], trecho: str) -> bool:
    t = nz.sem_acento(nz.norm(trecho))
    return any(re.search(r"\b" + re.escape(k), t) for k in lex)


class Paginas:
    """Textos normalizados das páginas de um lugar, por URL."""

    def __init__(self, man: dict):
        self.por_url = {}
        for p in man["paginas"]:
            arq = PAGINAS / man["lugar_id"] / f"{p['arquivo']}.txt"
            if arq.exists():
                self.por_url[p["url"]] = (nz.canon(arq.read_text(encoding="utf-8")), p["baixado_em"][:10])

    def achar(self, url: str, trecho: str):
        """(url, data) da página que contém o trecho: primeiro a citada, depois as outras do mesmo site."""
        cands = [u for u in self.por_url if u == url or u.rstrip("/") == (url or "").rstrip("/")]
        cands += [u for u in self.por_url if u not in cands]
        for u in cands:
            if nz.trecho_no_texto(trecho, self.por_url[u][0]):
                return u, self.por_url[u][1]
        return None

    def contem(self, frase: str) -> bool:
        f = nz.canon(frase)
        return any(f in t for t, _ in self.por_url.values())


class Validador:
    def __init__(self, paginas: Paginas):
        self.pg = paginas
        self.rejeicoes = Counter()
        self.evidencias = []

    def _evid(self, campo, valor, url, trecho):
        """Confere as regras 1 e de dados pessoais; devolve (url, data) ou None."""
        if not isinstance(trecho, str) or len(nz.norm(trecho)) < 4:
            self.rejeicoes["sem_evidencia"] += 1
            return None
        if len(nz.norm(trecho)) > EVID_MAX:
            self.rejeicoes["evidencia_longa"] += 1
            return None
        if _PESSOAL.search(trecho):
            self.rejeicoes["dado_pessoal_na_evidencia"] += 1
            return None
        achou = self.pg.achar(url, trecho)
        if not achou:
            self.rejeicoes["evidencia_ausente"] += 1  # é isto que barra alucinação
            return None
        self.evidencias.append({"campo": campo, "valor": valor, "url": achou[0], "evidencia": trecho,
                                "data": achou[1]})
        return achou

    def _falha(self, motivo):
        self.rejeicoes[motivo] += 1
        return None

    def horarios(self, entradas) -> list[dict]:
        por_dia_url = defaultdict(lambda: defaultdict(set))
        for e in entradas or []:
            dias_, abre, fecha = e.get("dias") or [], e.get("abre"), e.get("fecha")
            if not (dias_ and set(dias_) <= set(nz.DIAS) and nz.hora_valida(abre) and nz.hora_valida(fecha)):
                self._falha("formato_invalido")
                continue
            ev = e.get("evidencia", "")
            if not (set(dias_) <= nz.dias(ev) and {abre, fecha} <= nz.horas(ev)):
                self._falha("valor_fora_do_trecho")
                continue
            achou = self._evid("horario", f"{','.join(dias_)} {abre}-{fecha}", e.get("url"), ev)
            if not achou:
                continue
            for d in dias_:
                por_dia_url[d][achou[0]].add((abre, fecha))
        out = []
        for d, por_url in por_dia_url.items():
            faixas = {frozenset(v) for v in por_url.values()}
            if len(faixas) > 1:
                self._falha("contradicao_entre_paginas")
                return []  # o campo inteiro fica sem informação
            faixa = next(iter(faixas))
            if sum(nz.minutos_abertos(a, f) for a, f in faixa) > P["horas_max_dia"] * 60:
                self._falha("implausivel")
                return []
            url = next(iter(por_url))
            out += [{"dia": d, "abre": a, "fecha": f, "fonte": url} for a, f in sorted(faixa)]
        return sorted(out, key=lambda h: (nz.DIAS.index(h["dia"]), h["abre"]))

    def itens(self, entradas) -> list[dict]:
        aceitos = {}
        conflito = set()
        for e in entradas or []:
            item, preco, papel = (e.get("item") or "").strip(), e.get("preco"), e.get("papel")
            if not item or papel not in PAPEIS or not isinstance(preco, (int, float)):
                self._falha("formato_invalido")
                continue
            if not P["preco_min"] <= preco <= P["preco_max"]:
                self._falha("implausivel")
                continue
            ev = e.get("evidencia", "")
            palavras = set(_PALAVRA.findall(nz.sem_acento(nz.norm(item))))
            no_trecho = set(_PALAVRA.findall(nz.sem_acento(nz.norm(ev))))
            if not nz.valor_no_trecho(preco, ev) or not palavras or len(palavras & no_trecho) < len(palavras) / 2:
                self._falha("valor_fora_do_trecho")
                continue
            achou = self._evid("item", f"{item} {preco}", e.get("url"), ev)
            if not achou:
                continue
            k = nz.sem_acento(nz.norm(item))
            if k in aceitos and abs(aceitos[k]["preco"] - preco) > 0.005:
                conflito.add(k)
                continue
            aceitos[k] = {"item": item, "preco": round(float(preco), 2), "papel": papel, "fonte": achou[0]}
        for k in conflito:
            self._falha("contradicao_entre_paginas")
            aceitos.pop(k, None)
        return list(aceitos.values())[:8]

    def numero(self, campo, e, palavras, faixa):
        if not isinstance(e, dict) or not isinstance(e.get("valor"), (int, float)):
            return None
        v, ev = e["valor"], e.get("evidencia", "")
        if not faixa[0] <= v <= faixa[1]:
            return self._falha("implausivel")
        if not nz.valor_no_trecho(v, ev) or not _tem(palavras, ev):
            return self._falha("valor_fora_do_trecho")
        achou = self._evid(campo, v, e.get("url"), ev)
        return {"valor": round(float(v), 2), "fonte": achou[0]} if achou else None

    def entrada(self, e):
        if not isinstance(e, dict):
            return None
        ev = e.get("evidencia", "")
        if e.get("gratuito") is True:
            if not nz.diz_gratuito(ev):
                return self._falha("valor_fora_do_trecho")
            achou = self._evid("entrada", "gratuito", e.get("url"), ev)
            return {"gratuito": True, "valor": 0.0, "fonte": achou[0]} if achou else None
        v = e.get("valor")
        if not isinstance(v, (int, float)):
            return self._falha("formato_invalido")
        if not 0 < v <= P["preco_max"]:
            return self._falha("implausivel")
        if not nz.valor_no_trecho(v, ev):
            return self._falha("valor_fora_do_trecho")
        achou = self._evid("entrada", v, e.get("url"), ev)
        return {"gratuito": False, "valor": round(float(v), 2), "fonte": achou[0]} if achou else None

    def atributos(self, entradas, categoria) -> dict:
        out = {}
        for nome, e in (entradas or {}).items():
            if not isinstance(e, dict):
                continue
            v, ev = e.get("valor"), e.get("evidencia", "")
            if nome == "grupo_max":
                r = self.numero("grupo_max", e, ["pessoas", "lugares", "capacidade"], (2, 2000))
                if r:
                    out[nome] = {"valor": int(r["valor"]), "fonte": r["fonte"], "metodo": "extracao_site"}
                continue
            lex = LEXICO.get(nome, {}).get(v)
            if not lex:
                self._falha("formato_invalido")
                continue
            if not _tem(lex, ev):
                self._falha("valor_fora_do_trecho")
                continue
            achou = self._evid(nome, v, e.get("url"), ev)
            if achou:
                out[nome] = {"valor": v, "fonte": achou[0], "metodo": "extracao_site"}
        for nome, v in POR_CATEGORIA.get(categoria, {}).items():
            out.setdefault(nome, {"valor": v, "fonte": "", "metodo": "calculado"})
        return out

    def endereco(self, e):
        if not isinstance(e, dict) or not isinstance(e.get("valor"), str):
            return None
        ev = e.get("evidencia", "")
        palavras = set(_PALAVRA.findall(nz.sem_acento(nz.norm(e["valor"]))))
        no_trecho = set(_PALAVRA.findall(nz.sem_acento(nz.norm(ev))))
        if not palavras or len(palavras & no_trecho) < 0.7 * len(palavras):
            return self._falha("valor_fora_do_trecho")
        achou = self._evid("endereco", e["valor"], e.get("url"), ev)
        return {"valor": e["valor"].strip(), "fonte": achou[0]} if achou else None

    def eventos(self, entradas) -> list[dict]:
        hoje = date.today()
        limite = hoje + timedelta(days=P["evento_dias_max"])
        out = []
        for e in entradas or []:
            titulo, data_, hora = (e.get("titulo") or "").strip(), e.get("data") or "", e.get("hora") or ""
            try:
                d = date.fromisoformat(data_)
            except ValueError:
                self._falha("formato_invalido")
                continue
            if not (hoje <= d <= limite) or not nz.hora_valida(hora):
                self._falha("implausivel")
                continue
            if not titulo or not self.pg.contem(titulo):
                self._falha("evidencia_ausente")
                continue
            ev_d, ev_h, ev_p = e.get("evidencia_data", ""), e.get("evidencia_hora", ""), e.get("evidencia_preco", "")
            if not nz.data_no_trecho(data_, ev_d) or hora not in nz.horas(ev_h):
                self._falha("valor_fora_do_trecho")
                continue
            gratuito = e.get("gratuito") is True
            pmin, pmax = e.get("preco_min"), e.get("preco_max")
            if gratuito:
                ok_preco = nz.diz_gratuito(ev_p)
                pmin = pmax = 0.0
            else:
                ok_preco = isinstance(pmin, (int, float)) and P["preco_min"] <= pmin <= P["preco_max"] \
                    and nz.valor_no_trecho(pmin, ev_p) and (pmax is None or nz.valor_no_trecho(pmax, ev_p))
            if not ok_preco:
                self._falha("valor_fora_do_trecho")
                continue
            achados = [self._evid(f"evento_{c}", titulo, e.get("url"), t)
                       for c, t in (("data", ev_d), ("hora", ev_h), ("preco", ev_p))]
            if not all(achados):
                continue
            out.append({"titulo": titulo, "data": data_, "hora": hora, "gratuito": gratuito,
                        "preco_min": pmin, "preco_max": pmax if pmax is not None else pmin,
                        "link_oficial": achados[0][0], "verificado_em": achados[0][1]})
        return out


_GENERICAS = {"restaurante", "bar", "cafe", "lanchonete", "sorveteria", "parque", "museu", "teatro", "casa",
              "espaco", "centro", "cultural", "ecologico", "lanches", "pizzaria", "burger", "brasilia", "the", "and"}


def site_do_lugar(nome: str, pg: Paginas) -> bool:
    """O site cita o nome do lugar? Muitos sites listados na Overture são de outro negócio ou domínio revendido."""
    palavras = set(_PALAVRA.findall(nz.sem_acento(nz.norm(nome)))) - _GENERICAS
    if not palavras:
        palavras = set(_PALAVRA.findall(nz.sem_acento(nz.norm(nome))))
    textos = " ".join(nz.sem_acento(t) for t, _ in pg.por_url.values())
    return sum(1 for p in palavras if re.search(r"\b" + re.escape(p), textos)) >= max(1, len(palavras) / 2)


def obrigatorios(tipo: str, v: dict) -> list[str]:
    falta = []
    if tipo == "comer_beber":
        if not v["horarios"]:
            falta.append("sem_horario")
        if len(v["itens"]) < 3:
            falta.append("menos_de_3_precos")
    elif tipo == "ar_livre_gratuito":
        if not v["horarios"]:
            falta.append("sem_horario")
        if not v["entrada"]:
            falta.append("sem_entrada_ou_gratuito")
    elif tipo == "local_evento" and not v["eventos"]:
        falta.append("sem_evento_proximo")
    return falta


def executar():
    lugares = list(csv.DictReader(open(PROC / "selecionados.csv", encoding="utf-8")))
    saida = EXTRACAO / "saida"
    arq_t = EXTRACAO / "triagem.json"
    triagem = json.loads(arq_t.read_text(encoding="utf-8")) if arq_t.exists() else {}
    resultados, evidencias, rejeicoes = [], [], Counter()
    for l in lugares:
        lid = l["lugar_id"]
        base = {k: l[k] for k in ("lugar_id", "overture_id", "nome", "categoria", "tipo_role", "estrato", "ra",
                                  "regiao", "lat", "lon", "site", "licenca", "endereco_overture")}
        man_arq = PAGINAS / lid / "manifesto.json"
        man = json.loads(man_arq.read_text(encoding="utf-8")) if man_arq.exists() else None
        if not man or man["status"] != "ok":
            resultados.append({**base, "aprovado": False, "motivos": [man["status"] if man else "nao_rastreado"]})
            continue
        arq = saida / f"{lid}.json"
        try:
            ext = json.loads(arq.read_text(encoding="utf-8"))
        except (FileNotFoundError, ValueError):
            t = triagem.get(lid)
            motivo = "triagem_sem_sinal" if t and not t["passa"] else "sem_extracao"
            resultados.append({**base, "aprovado": False, "motivos": [motivo], "triagem": t})
            continue
        pg = Paginas(man)
        if not site_do_lugar(l["nome"], pg):
            resultados.append({**base, "aprovado": False, "motivos": ["site_de_outro_negocio"]})
            continue
        val = Validador(pg)
        v = {
            **base,
            "horarios": val.horarios(ext.get("horarios")),
            "itens": val.itens(ext.get("itens")),
            "couvert": val.numero("couvert", ext.get("couvert"), ["couvert"], (1, 100)),
            "taxa_servico_pct": val.numero("taxa_servico_pct", ext.get("taxa_servico_pct"),
                                           ["servico", "garcom", "gorjeta"], (1, 20)),
            "entrada": val.entrada(ext.get("entrada")),
            "atributos": val.atributos(ext.get("atributos"), l["categoria"]),
            "endereco": val.endereco(ext.get("endereco")),
            "eventos": val.eventos(ext.get("eventos")),
            "verificado_em": man["data"],
            "dominio": man["dominio"],
        }
        v["motivos"] = obrigatorios(l["tipo_role"], v)
        v["aprovado"] = not v["motivos"]
        v["rejeicoes"] = dict(val.rejeicoes)
        rejeicoes.update(val.rejeicoes)
        evidencias += [{"lugar_id": lid, **e} for e in val.evidencias]
        resultados.append(v)

    (PROC / "validados.json").write_text(json.dumps(resultados, ensure_ascii=False, indent=1), encoding="utf-8")
    with open(PROC / "evidencias.jsonl", "w", encoding="utf-8") as f:
        for e in evidencias:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    motivos = Counter(m for r in resultados for m in r["motivos"])
    return {"lugares": len(resultados), "aprovados": sum(r["aprovado"] for r in resultados),
            "motivos_de_reprovacao": dict(motivos.most_common()),
            "valores_aceitos": len(evidencias), "valores_rejeitados": dict(rejeicoes.most_common())}
