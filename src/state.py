"""Onde as salas ficam guardadas (guia oficial, semana 3).

O gerenciador de salas só conversa com um `Repositorio`. Hoje há o de memória, que serve para os testes e
para rodar local; e o `RepositorioSupabase` da Eduarda (`src/db/supabase_client.py`), escolhido por
`ROLES_REPOSITORIO=supabase` no `.env`.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
import copy
import os
import threading
from typing import Any

from src.db.supabase_client import RepositorioSupabase


class Repositorio(ABC):
    @abstractmethod
    def existe(self, codigo: str) -> bool: ...

    @abstractmethod
    def obter(self, codigo: str) -> Any: ...

    @abstractmethod
    def salvar(self, sala: Any) -> None: ...


class RepositorioMemoria(Repositorio):
    def __init__(self):
        self._salas: dict[str, Any] = {}
        self._trava = threading.Lock()

    def existe(self, codigo: str) -> bool:
        with self._trava:
            return codigo in self._salas

    def obter(self, codigo: str) -> Any:
        with self._trava:
            s = self._salas.get(codigo)
            return copy.deepcopy(s) if s else None

    def salvar(self, sala: Any) -> None:
        with self._trava:
            codigo = getattr(sala, "codigo", getattr(sala, "codigo_sala", None))
            if codigo:
                self._salas[codigo] = copy.deepcopy(sala)


_repositorio: Repositorio | None = None
_trava_global = threading.Lock()


def obter_repositorio() -> Repositorio:
    """O repositório do processo, escolhido por `ROLES_REPOSITORIO` (padrão: memoria ou supabase)."""
    global _repositorio
    with _trava_global:
        if _repositorio is None:
            tipo = os.environ.get("ROLES_REPOSITORIO", "memoria").lower()
            if tipo == "supabase":
                _repositorio = RepositorioSupabase()
            else:
                _repositorio = RepositorioMemoria()
        return _repositorio


def trocar_repositorio(repo: Repositorio | None) -> None:
    """Para testes: usa outro repositório (ou volta ao padrão com None)."""
    global _repositorio
    with _trava_global:
        _repositorio = repo
