"""Troca os nomes dos membros da sala por marcadores antes do LLM e desfaz na volta (RNF-01)."""
import re

from .numeros import canon

_VARIANTES = {"a": "aáàâãä", "e": "eéèêë", "i": "iíìîï", "o": "oóòôõö", "u": "uúùûü", "c": "cç", "n": "nñ"}


def _padrao(nome: str) -> str:
    """Regex do nome inteiro que aceita qualquer acentuação ('Marcio' casa 'Márcio')."""
    partes = []
    for ch in canon(nome):
        if ch.isspace():
            partes.append(r"\s+")
        elif ch in _VARIANTES:
            partes.append(f"[{_VARIANTES[ch]}]")
        else:
            partes.append(re.escape(ch))
    return rf"(?<!\w){''.join(partes)}(?!\w)"


class Pseudonimos:
    def __init__(self, membros: list[str], autor: str | None = None):
        self.autor = autor
        self.marcadores = {nome: f"@m{i}" for i, nome in enumerate(membros, 1)}
        self.para_nome = {m: n for n, m in self.marcadores.items()}

    def ocultar(self, texto: str) -> str:
        for nome in sorted(self.marcadores, key=len, reverse=True):  # "Ana Paula" antes de "Ana"
            texto = re.sub(_padrao(nome), self.marcadores[nome], texto, flags=re.IGNORECASE)
        return texto

    def revelar(self, valor: str | None) -> str | None:
        """'@m3' -> 'Bia'; 'eu' -> autor da mensagem; outro texto fica como está."""
        if valor is None:
            return None
        v = valor.strip()
        if canon(v) in ("eu", "mim", "autor"):
            return self.autor
        return self.para_nome.get(v, v)

    def revelar_texto(self, texto: str) -> str:
        return re.sub(r"@m\d+", lambda m: self.para_nome.get(m.group(0), m.group(0)), texto)
