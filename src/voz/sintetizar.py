"""Voz sintética pt-BR para testar o pipeline e a latência enquanto as gravações da equipe não chegam.

Não entra no WER oficial (ADR 0006): TTS não tem sotaque, ruído nem gíria falada. Tudo local:
Windows usa a voz "Microsoft Maria Desktop" (System.Speech); macOS usa `say -v Luciana`.
"""
import json
import platform
import shutil
import subprocess
import tempfile
from pathlib import Path

from interpretador.avaliar import carregar
from interpretador.config import RAIZ

SAIDA = RAIZ / "data" / "raw" / "voz" / "sintetico"

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


def sintetizar(voz: str | None = None) -> Path:
    frases, _ = carregar()
    sistema = platform.system()
    if sistema == "Windows":
        voz = voz or "Microsoft Maria Desktop"
        pasta = SAIDA / voz.replace(" ", "_")
        pasta.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory() as tmp:
            entrada = Path(tmp) / "frases.json"
            entrada.write_text(json.dumps({f["id"]: f["texto"] for f in frases}, ensure_ascii=False), encoding="utf-8")
            script = Path(tmp) / "tts.ps1"
            script.write_text(_PS.format(voz=voz, entrada=entrada, pasta=pasta), encoding="utf-8-sig")
            subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script)], check=True)
    elif sistema == "Darwin":
        voz = voz or "Luciana"
        pasta = SAIDA / voz
        pasta.mkdir(parents=True, exist_ok=True)
        for f in frases:
            subprocess.run(["say", "-v", voz, "-o", str(pasta / f"{f['id']}.wav"), "--file-format=WAVE",
                            "--data-format=LEI16@16000", f["texto"]], check=True)
    else:
        if not shutil.which("espeak-ng"):
            raise SystemExit("Sem voz pt-BR local: instale espeak-ng ou rode no Windows/macOS.")
        voz = voz or "pt-br"
        pasta = SAIDA / voz
        pasta.mkdir(parents=True, exist_ok=True)
        for f in frases:
            subprocess.run(["espeak-ng", "-v", voz, "-w", str(pasta / f"{f['id']}.wav"), f["texto"]], check=True)
    return pasta
