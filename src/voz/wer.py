"""WER e erro nos termos críticos, com normalização para pt-BR (ADR 0006)."""
import re

from interpretador.numeros import canon, extenso_para_digitos


def normalizar(texto: str) -> str:
    t = canon(texto)
    t = re.sub(r"r\$\s*", " ", t)
    t = re.sub(r"(\d)\.(\d{3})\b", r"\1\2", t)               # 1.200 -> 1200
    t = re.sub(r"[^\w\s]", " ", t)                            # pontuação (47,50 -> 47 50)
    t = extenso_para_digitos(re.sub(r"\s+", " ", t).strip())
    t = re.sub(r"\b(\d{1,2})\s*h(?:oras?)?\b", r"\1", t)      # 19h, 19 horas -> 19
    t = re.sub(r"\b(\d{1,2})h(\d{2})\b", r"\1 \2", t)         # 19h30 -> 19 30
    t = re.sub(r"\breais\b", " ", t)                           # "R$ 100" = "100 reais" ($ já saiu)
    return re.sub(r"\s+", " ", t).strip()


def distancia(ref: list[str], hip: list[str]) -> int:
    ant = list(range(len(hip) + 1))
    for i, r in enumerate(ref, 1):
        atual = [i]
        for j, h in enumerate(hip, 1):
            atual.append(min(ant[j] + 1, atual[j - 1] + 1, ant[j - 1] + (r != h)))
        ant = atual
    return ant[-1]


def wer(ref: str, hip: str) -> tuple[int, int]:
    """(erros, palavras da referência), para somar no corpus antes de dividir."""
    r, h = normalizar(ref).split(), normalizar(hip).split()
    return distancia(r, h), len(r)


def criticos_faltando(criticos: list[str], hip: str) -> list[str]:
    h = f" {normalizar(hip)} "
    return [c for c in criticos if f" {normalizar(c)} " not in h]
