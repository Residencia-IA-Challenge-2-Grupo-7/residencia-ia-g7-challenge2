"""Transcrição de fala atrás de uma interface única (ADR 0006).

No app, o áudio chega em bytes: vai para um arquivo temporário, apagado num `finally` depois da transcrição,
com ou sem erro (RNF-01). Nada aqui registra o áudio nem o texto. Quem chama recebe só texto e precisa
mostrá-lo para confirmação antes de qualquer ação com data, valor ou presença (RF-39).
"""
import os
import tempfile
import time
import tomllib
from dataclasses import dataclass
from functools import cache
from pathlib import Path

from interpretador.config import segredo

CFG = tomllib.loads(Path(__file__).with_name("config.toml").read_text(encoding="utf-8"))
T = CFG["transcricao"]


@dataclass
class Transcricao:
    texto: str
    provedor: str
    modelo: str
    latencia_s: float
    duracao_s: float | None = None


@cache
def _faster_whisper(modelo: str):
    from faster_whisper import WhisperModel
    c = CFG["faster_whisper"]
    return WhisperModel(modelo, device=c["dispositivo"], compute_type=c["computacao"], cpu_threads=c["threads"])


def decodificar(caminho: Path):
    """Áudio em qualquer formato -> float32 mono 16 kHz.

    PyAV no mesmo processo (o faster-whisper 1.2 chama um parâmetro que o PyAV 19 removeu, por isso não usamos
    o decodificador dele); ffmpeg pela linha de comando como reserva. Medido em 05/11: subir o ffmpeg custa
    mais de 1 s por frase no Windows.
    """
    import numpy as np
    try:
        import av
        partes = []
        with av.open(str(caminho)) as c:
            reamostrar = av.AudioResampler(format="s16", layout="mono", rate=16000)
            for quadro in c.decode(audio=0):
                for q in reamostrar.resample(quadro):
                    partes.append(q.to_ndarray().reshape(-1))
            for q in reamostrar.resample(None):
                partes.append(q.to_ndarray().reshape(-1))
        return np.concatenate(partes).astype(np.float32) / 32768.0
    except (ImportError, Exception):  # formato que o PyAV não abre: tenta o ffmpeg
        import subprocess
        r = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", str(caminho), "-f", "s16le", "-ac", "1",
                            "-ar", "16000", "-"], capture_output=True, check=True)
        return np.frombuffer(r.stdout, np.int16).astype(np.float32) / 32768.0


def _fw(caminho: Path, modelo: str, prompt: str | None) -> tuple[str, float | None]:
    c = CFG["faster_whisper"]
    audio = decodificar(caminho)
    segs, info = _faster_whisper(modelo).transcribe(audio, language=T["idioma"], beam_size=c["feixe"],
                                                     initial_prompt=prompt, vad_filter=c["vad"],
                                                     condition_on_previous_text=False)
    return " ".join(s.text.strip() for s in segs).strip(), info.duration


def _mlx(caminho: Path, modelo: str, prompt: str | None) -> tuple[str, float | None]:
    import mlx_whisper
    audio = decodificar(caminho)  # mesma decodificação dos outros provedores, sem chamar o ffmpeg
    r = mlx_whisper.transcribe(audio, path_or_hf_repo=modelo, language=T["idioma"], initial_prompt=prompt,
                               condition_on_previous_text=False, temperature=0.0)
    return r["text"].strip(), len(audio) / 16000


def _groq(caminho: Path, modelo: str, prompt: str | None) -> tuple[str, float | None]:
    import requests
    g = CFG["groq"]
    chave = segredo(g["chave_env"])
    if not chave:
        raise RuntimeError(f"Defina {g['chave_env']} no .env (fora do git) ou no ambiente.")
    dados = {"model": modelo, "language": T["idioma"], "response_format": "verbose_json", "temperature": "0"}
    if prompt:
        dados["prompt"] = prompt
    for tentativa in range(g["tentativas"]):
        with open(caminho, "rb") as f:
            r = requests.post(g["url"], headers={"Authorization": f"Bearer {chave}"}, data=dados,
                              files={"file": (caminho.name, f)}, timeout=g["timeout_s"])
        if r.status_code != 429 or tentativa == g["tentativas"] - 1:
            break
        time.sleep(min(float(r.headers.get("retry-after", 2) or 2), 10))  # limite por minuto do plano gratuito
    r.raise_for_status()
    d = r.json()
    return d["text"].strip(), d.get("duration")


PROVEDORES = {"faster_whisper": _fw, "mlx_whisper": _mlx, "groq": _groq}


def modelo_padrao(provedor: str) -> str:
    return CFG[provedor]["modelo"]


def carregar(provedor: str | None = None, modelo: str | None = None):
    """Carrega o modelo local antes da primeira frase (a latência medida não inclui o carregamento)."""
    provedor = provedor or T["provedor"]
    if provedor == "faster_whisper":
        _faster_whisper(modelo or modelo_padrao(provedor))


def transcrever(audio: bytes | Path, provedor: str | None = None, modelo: str | None = None,
                descartar: bool = False, sufixo: str = ".webm", usar_prompt: bool = True) -> Transcricao:
    """bytes: sempre apagados depois (fluxo do app). Path: apagado só com descartar=True."""
    provedor = provedor or T["provedor"]
    modelo = modelo or modelo_padrao(provedor)
    temporario = isinstance(audio, (bytes, bytearray))
    if temporario:
        fd, nome = tempfile.mkstemp(suffix=sufixo, prefix="voz-")
        with os.fdopen(fd, "wb") as f:
            f.write(audio)
        caminho = Path(nome)
    else:
        caminho = Path(audio)
    try:
        t0 = time.perf_counter()
        texto, dur = PROVEDORES[provedor](caminho, modelo, T["prompt"] if usar_prompt else None)
        return Transcricao(texto, provedor, modelo, time.perf_counter() - t0, dur)
    finally:
        if temporario or descartar:
            caminho.unlink(missing_ok=True)  # RNF-01: o áudio não sobrevive à transcrição
