"""Números e valores em reais no português falado do Brasil, por código (RNF-04).

O LLM só aponta o trecho literal ("120 conto", "cento e vinte", "23 e 40"); quem converte é esta função.
Também serve à normalização do WER (src/voz), que troca números por extenso por dígitos.
"""
import re
import unicodedata
from decimal import Decimal, InvalidOperation

UNIDADES = {"zero": 0, "um": 1, "uma": 1, "dois": 2, "duas": 2, "tres": 3, "quatro": 4, "cinco": 5, "seis": 6,
            "sete": 7, "oito": 8, "nove": 9, "dez": 10, "onze": 11, "doze": 12, "treze": 13, "catorze": 14,
            "quatorze": 14, "quinze": 15, "dezesseis": 16, "dezessete": 17, "dezoito": 18, "dezenove": 19}
DEZENAS = {"vinte": 20, "trinta": 30, "quarenta": 40, "cinquenta": 50, "sessenta": 60, "setenta": 70,
           "oitenta": 80, "noventa": 90}
CENTENAS = {"cem": 100, "cento": 100, "duzentos": 200, "duzentas": 200, "trezentos": 300, "trezentas": 300,
            "quatrocentos": 400, "quinhentos": 500, "seiscentos": 600, "setecentos": 700, "oitocentos": 800,
            "novecentos": 900}
PALAVRAS = UNIDADES | DEZENAS | CENTENAS


def canon(s: str) -> str:
    """Minúsculas e sem acento."""
    s = unicodedata.normalize("NFKD", s.lower())
    return "".join(ch for ch in s if not unicodedata.combining(ch))


def _extenso(tokens: list[str]) -> int | None:
    """'cento e vinte' -> 120; 'mil e duzentos' -> 1200. None se não for número."""
    total, atual, viu = 0, 0, False
    for t in tokens:
        if t == "e":
            continue
        if t == "mil":
            total += (atual or 1) * 1000
            atual, viu = 0, True
        elif t in PALAVRAS:
            atual += PALAVRAS[t]
            viu = True
        else:
            return None
    return total + atual if viu else None


_PALAVRA_NUM = r"(?:" + "|".join(sorted(PALAVRAS, key=len, reverse=True)) + r"|mil)"
_SEQ_EXTENSO = re.compile(rf"\b{_PALAVRA_NUM}(?:\s+(?:e\s+)?{_PALAVRA_NUM})*\b")


def extenso_para_digitos(texto: str) -> str:
    """Troca sequências de números por extenso por dígitos (texto já em canon)."""
    def troca(m):
        n = _extenso(m.group(0).split())
        # "um" e "uma" sozinhos costumam ser artigo ("um bar"), não número; "2 mil" fica para o multiplicador
        multiplicador = m.group(0).startswith("mil") and re.search(r"\d\s*$", texto[:m.start()])
        if n is None or m.group(0) in ("um", "uma") or multiplicador:
            return m.group(0)
        return str(n)
    return _SEQ_EXTENSO.sub(troca, texto)


_MULT = re.compile(r"(\d+(?:[.,]\d+)?)\s*(mil|k)\b")
_REAIS_E_CENTAVOS = re.compile(r"\b(\d+)\s*(?:reais\s+)?e\s+(\d{2})\b(?!\s*(?:mil|reais))")
_NUM = re.compile(r"\d{1,3}(?:\.\d{3})+(?:,\d{1,2})?|\d+,\d{1,2}|\d+\.\d{2}\b|\d+")


def _decimal(s: str) -> Decimal | None:
    if re.fullmatch(r"\d{1,3}(?:\.\d{3})+(?:,\d{1,2})?", s):
        s = s.replace(".", "").replace(",", ".")
    else:
        s = s.replace(",", ".")
    try:
        return Decimal(s)
    except InvalidOperation:
        return None


def valor_em_reais(trecho: str) -> Decimal | None:
    """Converte o trecho de um valor dito na conversa. None se não houver exatamente um valor."""
    t = extenso_para_digitos(canon(trecho))
    t = re.sub(r"r\$\s*", "", t)
    m = _MULT.search(t)
    if m:
        base = _decimal(m.group(1).replace(".", ","))
        return base * 1000 if base is not None else None
    m = _REAIS_E_CENTAVOS.search(t)
    if m:  # "23 e 40" -> 23,40
        return Decimal(m.group(1)) + Decimal(m.group(2)) / 100
    nums = {_decimal(x) for x in _NUM.findall(t)}
    nums.discard(None)
    if len(nums) != 1:
        return None
    return nums.pop()


def trecho_na_mensagem(trecho: str, mensagem: str) -> bool:
    """O trecho apontado pelo LLM está literalmente na mensagem (ignorando caixa, acento e espaços)?"""
    norm = lambda s: re.sub(r"\s+", " ", canon(s)).strip()
    return bool(trecho.strip()) and norm(trecho) in norm(mensagem)
