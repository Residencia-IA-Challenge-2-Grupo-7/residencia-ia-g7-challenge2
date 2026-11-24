"""Linha de comando da voz (ADR 0017). Rode da raiz do repositório.

    python -m src.voz conferir data/raw/voz/equipe      # sem rede: o que está pronto e o que falta
    python -m src.voz medir data/raw/voz/equipe         # transcreve, interpreta e compara com o gabarito
    python -m src.voz julgar data/raw/voz/julgamento-....csv
    python -m src.voz sintetizar                        # voz do Windows e gravações sem fala
"""
import argparse
import json
import sys
from pathlib import Path

from src.voz import medir as m


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(prog="src.voz", description="Voz no campo de horários (ADR 0017)")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("conferir", help="lista áudios prontos, sem gabarito e sem ID no nome")
    s.add_argument("pasta", type=Path)
    s = sub.add_parser("medir", help="mede uma pasta de áudios (envia cada áudio à OpenRouter, sem retenção)")
    s.add_argument("pasta", type=Path)
    s.add_argument("--modelo", help="outro modelo de transcrição da OpenRouter")
    s.add_argument("--rotulo", help="nome da rodada no arquivo de resultado (padrão: nome da pasta)")
    s.add_argument("--conjunto", help="só um conjunto do gabarito: gabarito, desenvolvimento, cego, falha")
    s = sub.add_parser("julgar", help="resume a coluna julgamento de um CSV")
    s.add_argument("csv", type=Path)
    sub.add_parser("sintetizar", help="voz sintética local; não entra no resultado oficial")
    a = p.parse_args()
    if a.cmd == "conferir":
        print(json.dumps(m.conferir(a.pasta), ensure_ascii=False, indent=1))
    elif a.cmd == "medir":
        r = m.medir(a.pasta, modelo=a.modelo, rotulo=a.rotulo, conjunto=a.conjunto)
        print("\n" + m.CABECALHO)
        for nome, x in [*r["por_conjunto"].items(), ("**total**", r["total"])]:
            print(m.linha_md(nome, x))
        print(f"\nPara julgar (fora do git): {r['csv']}")
    elif a.cmd == "julgar":
        print(json.dumps(m.julgar(a.csv), ensure_ascii=False, indent=1))
    else:
        from src.voz.sintetizar import sintetizar
        print(f"Áudios em {sintetizar()}")


if __name__ == "__main__":
    main()
