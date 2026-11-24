"""Transcrição de fala pela OpenRouter, só com provedores sem retenção (ADR 0017).

O áudio existe só na memória, durante o pedido: nada aqui grava em disco, registra em log ou guarda o áudio ou o
texto (RNF-01). Quem chama recebe só texto, que é dado, nunca instrução (RNF-11), e precisa mostrá-lo para a pessoa
conferir antes de usar.
"""
from __future__ import annotations

import base64
import time
import tomllib
from dataclasses import dataclass
from pathlib import Path

import requests

from src.interpretador.config import segredo

CFG = tomllib.loads(Path(__file__).with_name("config.toml").read_text(encoding="utf-8"))
T = CFG["transcricao"]
FORMATOS = ("webm", "mp4", "ogg", "wav")


class ErroVoz(RuntimeError):
    """`motivo`: sem_chave, formato, vazio ou indisponivel. A mensagem nunca leva o áudio, o texto ou a chave."""

    def __init__(self, motivo: str, detalhe: str = ""):
        super().__init__(f"{motivo}: {detalhe}" if detalhe else motivo)
        self.motivo = motivo


@dataclass(frozen=True)
class Transcricao:
    texto: str
    modelo: str
    latencia_s: float
    duracao_s: float | None  # segundos cobrados pelo provedor (a Groq cobra no mínimo 10)
    custo_usd: float
    tentativas: int = 1

    def __repr__(self) -> str:  # o texto não aparece se o objeto for parar num log
        return f"Transcricao({len(self.texto)} caracteres, {self.modelo}, {self.latencia_s:.2f} s)"


def formato_do_audio(audio: bytes) -> str | None:
    """Formato pela assinatura do arquivo, não pelo que o cliente declarou."""
    if audio[:4] == b"\x1a\x45\xdf\xa3":
        return "webm"
    if audio[:4] == b"OggS":
        return "ogg"
    if audio[:4] == b"RIFF" and audio[8:12] == b"WAVE":
        return "wav"
    if audio[4:8] == b"ftyp":  # mp4 e m4a (gravador do iPhone)
        return "mp4"
    return None


def disponivel() -> bool:
    return bool(segredo(T["chave_env"]))


def transcrever(audio: bytes, *, modelo: str | None = None, sessao=None, chave: str | None = None) -> Transcricao:
    """Áudio em bytes -> texto. `sessao` (com `post`) e `chave` só são passados nos testes e na medição."""
    formato = formato_do_audio(audio)
    if formato is None:
        raise ErroVoz("formato")
    chave = chave or segredo(T["chave_env"])
    if not chave:
        raise ErroVoz("sem_chave")
    modelo = modelo or T["modelo"]
    post = (sessao or requests).post
    rota = dict(T["roteamento"])
    if modelo != T["modelo"]:  # medição com outro modelo: outros provedores, mas sempre sem retenção
        rota.pop("only", None)
        rota.pop("order", None)
    corpo = {"model": modelo, "input_audio": {"data": base64.b64encode(audio).decode("ascii"), "format": formato},
             "language": T["idioma"], "temperature": 0, "prompt": T["prompt"]}
    inicio, erro = time.perf_counter(), ""
    for tentativa in (1, 2):
        if tentativa == 2 and "order" in rota:
            rota = rota | {"order": list(reversed(rota["order"]))}
        try:
            r = post(T["url"], json=corpo | {"provider": rota}, timeout=T["timeout_s"],
                     headers={"Authorization": f"Bearer {chave}", "X-Title": "Orquestrador de Roles - voz"})
        except requests.RequestException as e:
            erro = type(e).__name__
            continue
        if r.status_code == 400:
            raise ErroVoz("formato", "HTTP 400")  # arquivo que o provedor não abre
        if r.status_code != 200:
            erro = f"HTTP {r.status_code}"
            if r.status_code in (401, 402, 403, 404):  # chave, crédito ou nenhum provedor sem retenção
                break
            continue
        try:
            d = r.json()
            texto = " ".join(str(d["text"]).split())
        except (ValueError, KeyError, TypeError) as e:
            erro = type(e).__name__
            continue
        if not any(ch.isalnum() for ch in texto):  # silêncio e ruído costumam voltar como "." ou vazio
            raise ErroVoz("vazio")
        uso = d.get("usage") or {}
        return Transcricao(texto, modelo, round(time.perf_counter() - inicio, 3), uso.get("seconds"),
                           float(uso.get("cost") or 0.0), tentativa)
    raise ErroVoz("indisponivel", erro)
