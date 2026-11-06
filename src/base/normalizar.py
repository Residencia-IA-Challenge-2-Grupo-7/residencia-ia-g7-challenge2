"""Leitura, em código, de horários, dias, datas e valores dentro de um trecho de evidência.

O validador usa estas funções para conferir se o valor que o LLM devolveu aparece mesmo no trecho
(ADR 0005, regra 2 do validador).
"""
import re
import unicodedata

DIAS = ["seg", "ter", "qua", "qui", "sex", "sab", "dom"]

_TROCAS = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-",
                         "—": "-", " ": " ", " ": " ", " ": " ", "…": "..."})


def norm(s: str) -> str:
    """Forma canônica para comparar trechos: NFKC, aspas e travessões simples, espaços colapsados, minúsculas."""
    s = unicodedata.normalize("NFKC", s or "").translate(_TROCAS)
    return re.sub(r"\s+", " ", s).strip().casefold()


def sem_acento(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


_RS = re.compile(r"\br\s?[sa5$]\s*(?=\d)")  # o NFKC já transformou "ª" em "a"
_O_DEPOIS_DE_DIGITO = re.compile(r"(?<=\d)o+")
_PRECO_NO_MEIO = re.compile(r"r\$ ?\d|\d,\d{2}\b")
GAP_MAX = 400  # distância máxima, em caracteres, entre partes de uma evidência separadas por "..."


def canon(s: str) -> str:
    """norm() mais as confusões típicas de OCR, aplicadas igual na evidência e no texto da página:
    'rs 34', 'rª34' e 'R$ 34' viram 'r$ 34'; '5ooml' vira '500ml'."""
    s = _RS.sub("r$ ", norm(s))
    return _O_DEPOIS_DE_DIGITO.sub(lambda m: "0" * len(m.group()), s)


def trecho_no_texto(evidencia: str, texto_canon: str) -> bool:
    """O trecho existe literalmente no texto (ambos em canon()). Partes separadas por '...' precisam aparecer
    em ordem, próximas, e sem outro preço no meio: assim o nome de um item não é costurado ao preço de outro."""
    e = canon(evidencia)
    partes = [p.strip() for p in e.split("...") if p.strip()]
    if not partes:
        return False
    pos = None
    for p in partes:
        i = texto_canon.find(p, pos or 0)
        if i < 0:
            return False
        if pos is not None and (i - pos > GAP_MAX or _PRECO_NO_MEIO.search(texto_canon[pos:i])):
            return False
        pos = i + len(p)
    return True


# ---------- números e preços ----------

_NUM = re.compile(r"\d[\d.,]*\d|\d")


def numeros(s: str) -> set[float]:
    """Números no formato brasileiro ou com ponto decimal: '39,90', '1.234,56', '39.90', '12'."""
    out = set()
    for t in _NUM.findall(s or ""):
        try:
            if "," in t:
                out.add(float(t.replace(".", "").replace(",", ".")))
            elif re.fullmatch(r"\d+\.\d{1,2}", t):
                out.add(float(t))
            elif re.fullmatch(r"\d{1,3}(\.\d{3})+", t):
                out.add(float(t.replace(".", "")))
            else:
                out.add(float(t.replace(".", "")))
        except ValueError:
            continue
    return out


def valor_no_trecho(valor: float, trecho: str) -> bool:
    return any(abs(n - float(valor)) < 0.006 for n in numeros(trecho))


# ---------- horários ----------

_HHMM = re.compile(r"(?<![\d])([01]?\d|2[0-4])\s*:\s*([0-5]\d)(?![\d])")
_HH_H = re.compile(r"(?<![\d:,.])([01]?\d|2[0-4])\s*(?:h|hs|hrs|horas?)\s*:?\s*([0-5]\d)?(?![\d])", re.I)


def _hora(h: str, m: str | None) -> str:
    h = int(h) % 24
    return f"{h:02d}:{int(m or 0):02d}"


def horas(s: str) -> set[str]:
    """Horários citados no trecho, como 'HH:MM'. 24h vira 00:00; meia-noite e meio-dia são reconhecidos."""
    t = sem_acento(norm(s))
    out = {_hora(h, m) for h, m in _HHMM.findall(t)} | {_hora(h, m) for h, m in _HH_H.findall(t)}
    if re.search(r"meia[- ]noite", t):
        out.add("00:00")
    if re.search(r"meio[- ]dia", t):
        out.add("12:00")
    return out


def hora_valida(h: str) -> bool:
    return bool(re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", h or ""))


def minutos_abertos(abre: str, fecha: str) -> int:
    a = int(abre[:2]) * 60 + int(abre[3:])
    f = int(fecha[:2]) * 60 + int(fecha[3:])
    return (f - a) % (24 * 60) or 24 * 60


# ---------- dias da semana ----------

_DIA_PT = {
    "segunda": 0, "seg": 0, "terca": 1, "ter": 1, "quarta": 2, "qua": 2, "quinta": 3, "qui": 3,
    "sexta": 4, "sex": 4, "sabado": 5, "sab": 5, "domingo": 6, "dom": 6,
    "monday": 0, "mon": 0, "tuesday": 1, "tue": 1, "wednesday": 2, "wed": 2, "thursday": 3, "thu": 3,
    "friday": 4, "fri": 4, "saturday": 5, "sat": 5, "sunday": 6, "sun": 6,
}
_ABREV_FRACAS = {"ter", "qua", "sex", "dom", "sat", "sun", "mon", "wed"}  # também são palavras comuns
_RE_DIA = re.compile(r"\b(" + "|".join(sorted(_DIA_PT, key=len, reverse=True)) + r")s?\b\.?")
# schema.org: Mo, Tu, We, Th, Fr, Sa, Su (com maiúscula, no texto original)
_SCHEMA = {"Mo": 0, "Tu": 1, "We": 2, "Th": 3, "Fr": 4, "Sa": 5, "Su": 6}
_RE_SCHEMA = re.compile(r"\b(Mo|Tu|We|Th|Fr|Sa|Su)\b")
_SEP_INTERVALO = re.compile(r"^\s*(?:a|ao|as|ate|-|to|through)\s*$")
_NEGACAO = re.compile(r"(fechad[oa]s?|exceto|menos|nao abr\w*|nao funciona\w*|nao atende\w*)\s+((?:\S+\s*){1,6})")


def _expandir(i: int, j: int) -> set[int]:
    if i == j:  # "de segunda a segunda", "domingo a domingo": a semana inteira
        return set(range(7))
    return {(i + k) % 7 for k in range(((j - i) % 7) + 1)}


def _dias_tokens(t: str, tokens) -> set[int]:
    out = set()
    k = 0
    while k < len(tokens):
        ini, fim_, d = tokens[k]
        if k + 1 < len(tokens) and _SEP_INTERVALO.match(t[fim_:tokens[k + 1][0]]):
            out |= _expandir(d, tokens[k + 1][2])
            k += 2
            continue
        out.add(d)
        k += 1
    return out


def dias(s: str) -> set[str]:
    """Dias da semana cobertos pelo trecho, com intervalos ('ter a dom') e negações ('fechado às segundas')."""
    t = sem_acento(norm(s))
    t = re.sub(r"\b(segunda|terca|quarta|quinta|sexta)[- ]feiras?\b", r"\1", t)
    if re.search(r"todos os dias|diariamente|de segunda a segunda|7 dias por semana|sete dias", t):
        return set(DIAS)
    out = set()
    if re.search(r"\bfins? de semana|finais de semana", t):
        out |= {5, 6}
    if re.search(r"dias uteis", t):
        out |= {0, 1, 2, 3, 4}
    toks = [(m.start(), m.end(), _DIA_PT[m.group(1)], m.group(1)) for m in _RE_DIA.finditer(t)]
    if len(toks) < 2:
        # Abreviações que também são palavras ('ter', 'sex') só valem com ponto ou junto de outro dia.
        toks = [x for x in toks if x[3] not in _ABREV_FRACAS or t[x[1] - 1:x[1]] == "."]
    out |= _dias_tokens(t, [(a, b, d) for a, b, d, _ in toks])
    orig = unicodedata.normalize("NFKC", s or "").translate(_TROCAS)
    sch = [(m.start(), m.end(), _SCHEMA[m.group(1)]) for m in _RE_SCHEMA.finditer(orig)]
    out |= _dias_tokens(orig, sch)
    for m in _NEGACAO.finditer(t):
        trecho = m.group(2)
        neg = [(x.start(), x.end(), _DIA_PT[x.group(1)]) for x in _RE_DIA.finditer(trecho)]
        out -= _dias_tokens(trecho, neg)
    return {DIAS[d] for d in out}


# ---------- datas ----------

MESES = {"janeiro": 1, "jan": 1, "fevereiro": 2, "fev": 2, "marco": 3, "mar": 3, "abril": 4, "abr": 4,
         "maio": 5, "mai": 5, "junho": 6, "jun": 6, "julho": 7, "jul": 7, "agosto": 8, "ago": 8,
         "setembro": 9, "set": 9, "outubro": 10, "out": 10, "novembro": 11, "nov": 11, "dezembro": 12, "dez": 12}
_RE_DMY = re.compile(r"(?<!\d)(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?(?!\d)")
_RE_ISO = re.compile(r"(?<!\d)(\d{4})-(\d{2})-(\d{2})")
_RE_EXT = re.compile(r"(?<!\d)(\d{1,2})(?:º|o)?\s*(?:de\s+)?(" + "|".join(sorted(MESES, key=len, reverse=True))
                     + r")\b\.?(?:\s*(?:de\s+)?(\d{4}))?")


def datas(s: str) -> set[tuple[int, int, int | None]]:
    """(dia, mês, ano ou None) citados no trecho."""
    t = sem_acento(norm(s))
    out = set()
    for d, m, a in _RE_DMY.findall(t):
        a = int(a) + (2000 if len(a) == 2 else 0) if a else None
        out.add((int(d), int(m), a))
    for a, m, d in _RE_ISO.findall(t):
        out.add((int(d), int(m), int(a)))
    for d, m, a in _RE_EXT.findall(t):
        out.add((int(d), MESES[m], int(a) if a else None))
    return {x for x in out if 1 <= x[0] <= 31 and 1 <= x[1] <= 12}


def data_no_trecho(iso: str, trecho: str) -> bool:
    a, m, d = (int(x) for x in iso.split("-"))
    return any(dd == d and mm == m and (aa is None or aa == a) for dd, mm, aa in datas(trecho))


GRATUITO = re.compile(r"\b(gratis|gratuit[oa]s?|entrada franca|entrada livre|acesso livre|acesso gratuito|"
                      r"sem custo|nao cobra\w*|free entry|free admission)\b")


def diz_gratuito(trecho: str) -> bool:
    return bool(GRATUITO.search(sem_acento(norm(trecho))))
