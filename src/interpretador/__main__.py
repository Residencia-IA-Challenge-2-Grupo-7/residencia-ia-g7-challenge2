"""Linha de comando do interpretador (ADR 0007).

    python -m interpretador "sexta depois das 19h e no máximo 50 conto" --contexto privado
    python -m interpretador --audio gravacao.m4a          # transcreve (ADR 0006) e interpreta
    python -m interpretador avaliar [--ids D01 G02] [--transcricoes eval/resultados/transcricoes-....json]
"""
import argparse
import json
import sys
from pathlib import Path


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) > 1 and sys.argv[1] == "avaliar":
        p = argparse.ArgumentParser(prog="interpretador avaliar")
        p.add_argument("avaliar")
        p.add_argument("--ids", nargs="*")
        p.add_argument("--transcricoes", type=Path, help="JSON {id: texto transcrito}, saída de `python -m voz medir`")
        p.add_argument("--rotulo", help="nome da rodada no arquivo de resultado (padrão: texto ou voz)")
        p.add_argument("--modelo", help="outro modelo da OpenRouter só nesta rodada")
        a = p.parse_args()
        from .avaliar import avaliar, gravar, resumo_md
        r = avaliar(a.ids, a.transcricoes, a.rotulo or ("voz" if a.transcricoes else "texto"), a.modelo)
        arq = gravar(r)
        print("\n" + resumo_md(r))
        print(f"\nDetalhes: {arq}")
        return

    p = argparse.ArgumentParser(prog="interpretador", description="Interpreta uma mensagem (ADR 0007)")
    p.add_argument("mensagem", nargs="?")
    p.add_argument("--audio", type=Path, help="arquivo de áudio: transcreve antes (não apaga o arquivo)")
    p.add_argument("--contexto", choices=["privado", "grupo"], default="privado")
    p.add_argument("--autor", default="Rafaela")
    p.add_argument("--membros", nargs="*", default=["Rafaela", "Cadu", "Bia", "Márcio", "Caio", "Ana"])
    p.add_argument("--buscar", action="store_true", help="executa a busca na base para busca_lugar (precisa do Postgres)")
    a = p.parse_args()
    origem, texto = "texto", a.mensagem
    if a.audio:
        from voz.transcrever import transcrever
        t = transcrever(a.audio, descartar=False)
        print(f"Transcrição ({t.provedor}/{t.modelo}, {t.latencia_s:.2f} s): {t.texto}")
        origem, texto = "voz", t.texto
    if not texto:
        p.error("informe a mensagem ou --audio")
    from .interpretar import interpretar
    r = interpretar(texto, contexto=a.contexto, autor=a.autor, membros=a.membros, origem=origem)
    print(json.dumps(r.para_json(), ensure_ascii=False, indent=1, default=str))
    if a.buscar:
        from base.buscar import buscar, linhas
        for i in r.intencoes:
            if i.consulta:
                for l in linhas(buscar(i.consulta)):
                    print(l)


if __name__ == "__main__":
    main()
