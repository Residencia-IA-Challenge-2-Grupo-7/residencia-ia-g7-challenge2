"""Gera o pacote ZIP do entregável da Semana 3 (issue #40).

Uso: PYTHONPATH=. python scripts/gerar_pacote_semana3.py

Rode depois de colocar o PDF compilado no Overleaf em docs/entregas/semana-03/RELATORIO_TECNICO_SEMANA_03.pdf.
"""
from __future__ import annotations

import sys
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
PASTA = RAIZ / "docs" / "entregas" / "semana-03"
# Mesmo nome que a rota /download/entregavel-semana3-zip da Central de Entregáveis procura (PR #62)
ZIP = PASTA / "Entregavel_Grupo7_Semana_03.zip"

# (caminho no repositório, caminho dentro do ZIP)
ARQUIVOS = [
    ("docs/entregas/semana-03/RELATORIO_TECNICO_SEMANA_03.pdf", "RELATORIO_TECNICO_SEMANA_03.pdf"),
    ("docs/entregas/semana-03/RELATORIO_TECNICO_SEMANA_03.md", "RELATORIO_TECNICO_SEMANA_03.md"),
    ("docs/entregas/semana-03/RELATORIO_TECNICO_SEMANA_03.tex", "RELATORIO_TECNICO_SEMANA_03.tex"),
    ("docs/entregas/semana-03/BENCHMARK_LLM_VS_RAG_LOG.txt", "BENCHMARK_LLM_VS_RAG_LOG.txt"),
    ("data/resultados_benchmark_semana3.json", "dados/resultados_benchmark_semana3.json"),
    ("data/resultados_benchmark_semana3.csv", "dados/resultados_benchmark_semana3.csv"),
    ("data/golden_dataset_semana3.json", "dados/golden_dataset_semana3.json"),
    ("docs/experimentos/2026-11-13-benchmark-semana3.md", "experimentos/2026-11-13-benchmark-semana3.md"),
]


def gerar() -> Path:
    faltando = [origem for origem, _ in ARQUIVOS if not (RAIZ / origem).is_file()]
    if faltando:
        raise SystemExit("Arquivos faltando para o pacote:\n  " + "\n  ".join(faltando))
    with zipfile.ZipFile(ZIP, "w", compression=zipfile.ZIP_DEFLATED) as pacote:
        for origem, destino in ARQUIVOS:
            pacote.write(RAIZ / origem, destino)
    return ZIP


if __name__ == "__main__":
    caminho = gerar()
    print(f"Pacote gerado: {caminho.relative_to(RAIZ)} ({caminho.stat().st_size} bytes)")
    sys.exit(0)
