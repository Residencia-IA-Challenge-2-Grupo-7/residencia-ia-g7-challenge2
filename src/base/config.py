"""Caminhos e configuração do pipeline da base (ADR 0005)."""
import os
import tomllib
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
CFG = tomllib.loads(Path(__file__).with_name("config.toml").read_text(encoding="utf-8"))

DADOS = RAIZ / "data"
RAW = DADOS / "raw"            # fora do git: Overture, páginas brutas
PROC = DADOS / "processed"     # fora do git: etapas intermediárias, evidências
BASE = DADOS / "base"          # versionado: CSVs aprovados e relatório
PAGINAS = RAW / "paginas"
EXTRACAO = PROC / "extracao"
PROMPTS = Path(__file__).with_name("prompts")

VERSAO = CFG["pipeline"]["versao"]
DSN = os.environ.get("BASE_DSN", CFG["banco"]["dsn_local"])


def overture_arquivo() -> Path:
    return RAW / "overture" / f"places_df_{CFG['pipeline']['release_overture']}.parquet"
