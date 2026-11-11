"""Deixa os dois estilos de import funcionarem com um `pytest tests` simples, sem PYTHONPATH:
`src.main` / `src.salas` (API, raiz no caminho) e `interpretador` (módulos antigos, `src/` no caminho)."""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
for caminho in (RAIZ, RAIZ / "src"):
    if str(caminho) not in sys.path:
        sys.path.insert(0, str(caminho))
