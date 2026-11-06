"""Casa os lugares citados ("Asa Sul", "lá pros lados de Ceilândia") com as RAs e regiões da base."""
import re

from base.contrato import ras_validas

from .config import CFG
from .numeros import canon

REGIOES = {"centro": "centro", "oeste proximo": "oeste_proximo", "oeste": "oeste", "sul": "sul",
           "norte": "norte", "leste": "leste"}


def _indice() -> list[tuple[str, str]]:
    """(forma canônica, RA), das mais longas para as mais curtas, para casar 'riacho fundo ii' antes de 'riacho fundo'."""
    idx = {canon(ra): ra for ra in ras_validas()}
    idx |= {canon(k): v for k, v in CFG["lugares"]["apelidos"].items()}
    return sorted(idx.items(), key=lambda kv: -len(kv[0]))


def casar(citados: list[str]) -> tuple[list[str], list[str], list[str]]:
    """-> (RAs, regiões, citados que não casaram)."""
    ras, regioes, sobra = [], [], []
    idx = _indice()
    for c in citados:
        t = " " + re.sub(r"[^\w/ ]", " ", canon(c)) + " "
        achou = False
        for forma, ra in idx:
            if f" {forma} " in t:
                if ra not in ras:
                    ras.append(ra)
                t = t.replace(f" {forma} ", " ")
                achou = True
        for forma, reg in REGIOES.items():
            if re.search(rf"\b(regiao|zona|lado)?\s*{forma}\b", t) and re.search(r"regiao|zona", t):
                regioes.append(reg)
                achou = True
        if not achou:
            sobra.append(c)
    return ras, regioes, sobra
