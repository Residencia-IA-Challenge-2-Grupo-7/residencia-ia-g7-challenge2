"""Onde as salas ficam guardadas (guia oficial, semana 3).

O gerenciador de salas só conversa com um `Repositorio`. Hoje há o de memória, que serve para os testes e
para rodar local; quando o cliente do Supabase da Eduarda (`src/db/supabase_client.py`) existir, entra um
`RepositorioSupabase` com os mesmos três métodos, escolhido por `ROLES_REPOSITORIO=supabase` no `.env`.

A sala é guardada inteira (participantes, cartões, votos), como um agregado: quem grava no banco decide como
quebrar nas 5 tabelas. O de memória perde tudo ao reiniciar o servidor.
"""
from __future__ import annotations

import copy
import os
import threading
from abc import ABC, abstractmethod

from src.salas.modelos import Sala


class Repositorio(ABC):
    @abstractmethod
    def existe(self, codigo: str) -> bool: ...

    @abstractmethod
    def obter(self, codigo: str) -> Sala | None:
        """Uma cópia da sala; mudanças só valem depois de `salvar`."""

    @abstractmethod
    def salvar(self, sala: Sala) -> None: ...


class RepositorioMemoria(Repositorio):
    def __init__(self):
        self._salas: dict[str, Sala] = {}
        self._trava = threading.Lock()

    def existe(self, codigo: str) -> bool:
        with self._trava:
            return codigo in self._salas

    def obter(self, codigo: str) -> Sala | None:
        with self._trava:
            s = self._salas.get(codigo)
            return copy.deepcopy(s) if s else None

    def salvar(self, sala: Sala) -> None:
        with self._trava:
            self._salas[sala.codigo] = copy.deepcopy(sala)


_repositorio: Repositorio | None = None
_trava_global = threading.Lock()


def obter_repositorio() -> Repositorio:
    """O repositório do processo, escolhido por `ROLES_REPOSITORIO` (padrão: memoria)."""
    global _repositorio
    with _trava_global:
        if _repositorio is None:
            tipo = os.environ.get("ROLES_REPOSITORIO", "memoria").lower()
            if tipo == "memoria":
                _repositorio = RepositorioMemoria()
            elif tipo == "supabase":
                from src.db.supabase_client import RepositorioSupabase
                _repositorio = RepositorioSupabase()
            else:
                raise RuntimeError(
                    f"ROLES_REPOSITORIO={tipo!r} ainda não existe. Implemente um Repositorio em src/db/ "
                    "(obter, salvar, existe) e registre aqui.")
        return _repositorio


def trocar_repositorio(repo: Repositorio | None) -> None:
    """Para testes: usa outro repositório (ou volta ao padrão com None)."""
    global _repositorio
    with _trava_global:
        _repositorio = repo
