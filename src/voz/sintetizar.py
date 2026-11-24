"""Voz sintética pt-BR local (Windows) e gravações sem fala, para testar o caminho inteiro sem áudio de pessoas.

Não entra no resultado oficial (ADR 0006): TTS não tem sotaque, ruído nem gíria falada. Não usa rede.
"""
from __future__ import annotations

import json
import platform
import random
import struct
import subprocess
import tempfile
import wave
from pathlib import Path

from src.voz.medir import PASTA_VOZ, carregar_gabarito

_PS = r"""
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
$s.SelectVoice('{voz}')
$fmt = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(16000, [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen, [System.Speech.AudioFormat.AudioChannel]::Mono)
$itens = Get-Content -Raw -Encoding UTF8 '{entrada}' | ConvertFrom-Json
foreach ($p in $itens.PSObject.Properties) {{
  $s.SetOutputToWaveFile((Join-Path '{pasta}' ($p.Name + '.wav')), $fmt)
  $s.Speak($p.Value)
}}
$s.SetOutputToNull()
"""


def sem_fala(arquivo: Path, volume: int, segundos: int = 4) -> None:
    """Silêncio (volume 0) ou ruído."""
    sorteio = random.Random(5)
    with wave.open(str(arquivo), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(b"".join(struct.pack("<h", sorteio.randint(-volume, volume)) for _ in range(16000 * segundos)))


def sintetizar(voz: str = "Microsoft Maria Desktop", pasta: Path | None = None) -> Path:
    if platform.system() != "Windows":
        raise SystemExit("A voz sintética deste script é a do Windows.")
    pasta = pasta or PASTA_VOZ / "sintetico" / voz.replace(" ", "_")
    pasta.mkdir(parents=True, exist_ok=True)
    frases = {i: g["texto"] for i, g in carregar_gabarito().items() if g["texto"]}
    with tempfile.TemporaryDirectory() as tmp:
        entrada, script = Path(tmp) / "frases.json", Path(tmp) / "tts.ps1"
        entrada.write_text(json.dumps(frases, ensure_ascii=False), encoding="utf-8")
        script.write_text(_PS.format(voz=voz, entrada=entrada, pasta=pasta), encoding="utf-8-sig")
        subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script)], check=True)
    sem_fala(pasta / "F01.wav", 0)
    sem_fala(pasta / "F02.wav", 300)
    return pasta
