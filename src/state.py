"""Onde as salas ficam guardadas (guia oficial, semana 3).

O gerenciador de salas só conversa com um `Repositorio`. Hoje há o de memória, que serve para os testes e
para rodar local; e o `RepositorioSupabase` da Eduarda (`src/db/supabase_client.py`), escolhido por
`ROLES_REPOSITORIO=supabase` no `.env`.

A sala é guardada inteira (participantes, cartões, votos), como um agregado: quem grava no banco decide como
quebrar nas 5 tabelas. O de memória perde tudo ao reiniciar o servidor.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
import copy
import os
import threading
from typing import Any, Optional

from src.salas.modelos import Sala
from src.db.supabase_client import RepositorioSupabase


class Repositorio(ABC):
    @abstractmethod
    def existe(self, codigo: str) -> bool: ...

    @abstractmethod
    def obter(self, codigo: str) -> Sala | Any | None:
        """Uma cópia da sala; mudanças só valem depois de `salvar`."""

    @abstractmethod
    def salvar(self, sala: Sala | Any) -> None: ...


class RepositorioMemoria(Repositorio):
    def __init__(self):
        self._salas: dict[str, Any] = {}
        self._trava = threading.Lock()

    def existe(self, codigo: str) -> bool:
        with self._trava:
            return codigo in self._salas

    def obter(self, codigo: str) -> Any | None:
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
