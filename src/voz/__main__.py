"""Linha de comando da transcrição (ADR 0006).

    python -m voz transcrever arquivo.m4a [--provedor groq]
    python -m voz sintetizar                       # vozes pt-BR locais -> data/raw/voz/sintetico/
    python -m voz medir data/raw/voz/equipe [--provedor faster_whisper --modelo medium] [--sem-prompt]
"""
import argparse
import sys
from pathlib import Path


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(prog="voz", description="Transcrição de fala (ADR 0006)")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("transcrever")
    s.add_argument("arquivo", type=Path)
    s.add_argument("--provedor", choices=["faster_whisper", "mlx_whisper", "groq"])
    s.add_argument("--modelo")
    s = sub.add_parser("sintetizar", help="voz sintética local para testar o pipeline (não entra no WER oficial)")
    s.add_argument("--voz")
    s = sub.add_parser("medir", help="WER, termos críticos, latência e custo numa pasta de áudios")
    s.add_argument("pasta", type=Path)
    s.add_argument("--provedor", choices=["faster_whisper", "mlx_whisper", "groq"])
    s.add_argument("--modelo")
    s.add_argument("--sem-prompt", action="store_true", help="sem o vocabulário do domínio no prompt inicial")
    s.add_argument("--rotulo")
    a = p.parse_args()

    if a.cmd == "transcrever":
        from .transcrever import transcrever
        t = transcrever(a.arquivo, a.provedor, a.modelo)
        print(f"{t.texto}\n({t.provedor}/{t.modelo}, {t.latencia_s:.2f} s)")
    elif a.cmd == "sintetizar":
        from .sintetizar import sintetizar
        print(f"Áudios em {sintetizar(a.voz)}")
    elif a.cmd == "medir":
        from .medir import CABECALHO, medir, resumo_md
        r = medir(a.pasta, a.provedor, a.modelo, not a.sem_prompt, a.rotulo)
        print("\n" + CABECALHO + "\n" + resumo_md(r) + f"\n\nDetalhes: {r['arquivo']}")


if __name__ == "__main__":
    main()
