"""Configuração do interpretador (ADR 0007) e leitura de segredos do ambiente ou do .env."""
import os
import tomllib
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
CFG = tomllib.loads(Path(__file__).with_name("config.toml").read_text(encoding="utf-8"))
PROMPTS = Path(__file__).with_name("prompts")
EVAL = RAIZ / "eval"


def segredo(nome: str) -> str | None:
    """Variável de ambiente ou linha NOME=valor do .env na raiz (fora do git)."""
    if os.environ.get(nome):
        return os.environ[nome]
    env = RAIZ / ".env"
    if env.exists():
        for linha in env.read_text(encoding="utf-8").splitlines():
            k, _, v = linha.partition("=")
            if k.strip() == nome and v.strip():
                return v.strip().strip('"').strip("'")
    return None
