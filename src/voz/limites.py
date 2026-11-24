"""Cotas da rota de voz (ADR 0017): por sala, por dia e de pedidos ao mesmo tempo.

A rota não pede token, porque na Tela 2 a pessoa ainda não entrou na sala. As cotas evitam que alguém use a chave do
projeto à vontade. Ficam em memória: zeram quando o servidor reinicia e não valem entre processos.
"""
from __future__ import annotations

import threading
import time
from collections import deque
from contextlib import contextmanager

from src.voz.transcrever import CFG

L = CFG["limites"]


class CotaExcedida(RuntimeError):
    pass


class Cotas:
    def __init__(self, por_sala: int = L["por_sala"], janela_s: float = L["janela_s"], por_dia: int = L["por_dia"],
                 simultaneos: int = L["simultaneos"], relogio=time.monotonic):
        self.por_sala, self.janela_s, self.por_dia, self.simultaneos = por_sala, janela_s, por_dia, simultaneos
        self.relogio = relogio
        self._trava = threading.Lock()
        self._salas: dict[str, deque[float]] = {}
        self._dia: deque[float] = deque()
        self._em_uso = 0

    @contextmanager
    def usar(self, sala: str):
        """Reserva uma gravação da sala enquanto o bloco roda. Pedido que falha também conta: já custou."""
        with self._trava:
            agora = self.relogio()
            self._limpar(agora)
            fila = self._salas.setdefault(sala, deque())
            if self._em_uso >= self.simultaneos or len(fila) >= self.por_sala or len(self._dia) >= self.por_dia:
                if not fila:
                    del self._salas[sala]
                raise CotaExcedida
            fila.append(agora)
            self._dia.append(agora)
            self._em_uso += 1
        try:
            yield
        finally:
            with self._trava:
                self._em_uso -= 1

    def _limpar(self, agora: float) -> None:
        while self._dia and agora - self._dia[0] >= 86_400:
            self._dia.popleft()
        for sala, fila in list(self._salas.items()):
            while fila and agora - fila[0] >= self.janela_s:
                fila.popleft()
            if not fila:
                del self._salas[sala]
