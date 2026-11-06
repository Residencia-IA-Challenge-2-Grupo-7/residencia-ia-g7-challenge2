"""Linha de comando do pipeline: python -m base <etapa>. As etapas seguem o ADR 0005."""
import argparse
import json
import sys


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(prog="base", description="Pipeline da base de lugares e eventos (ADR 0005)")
    sub = p.add_subparsers(dest="etapa", required=True)
    sub.add_parser("descobrir", help="1. Overture → candidatos.csv")
    s = sub.add_parser("selecionar", help="2. deduplicar e sortear por estrato")
    s.add_argument("--n", type=int, help="total de candidatos (padrão: config [piloto])")
    s.add_argument("--repor", action="store_true", help="repor as vagas dos que falharam, até a cota de --n")
    s = sub.add_parser("rastrear", help="3. robô nos sites oficiais")
    s.add_argument("--ids", nargs="*", help="só estes lugares")
    s = sub.add_parser("preparar", help="4a. montar as entradas e os lotes da extração")
    s.add_argument("--todos", action="store_true", help="reextrair também as páginas que não mudaram")
    s.add_argument("--ids", nargs="*", help="só estes lugares")
    s = sub.add_parser("ocr", help="3b. ler cardápios em imagem e PDF escaneado por OCR local")
    s.add_argument("--ids", nargs="*", help="só estes lugares")
    sub.add_parser("validar", help="5. validar as extrações")
    sub.add_parser("descrever", help="7a. montar a entrada das descrições")
    sub.add_parser("calcular", help="7. custo, estados, fichas e CSVs")
    s = sub.add_parser("vetorizar", help="8. embeddings das fichas")
    s.add_argument("--modelo", help="modelo de embeddings (padrão: config)")
    sub.add_parser("gravar", help="9. upsert no PostgreSQL com pgvector")
    sub.add_parser("relatar", help="10. relatório da rodada")
    s = sub.add_parser("buscar", help="consulta de teste: filtros em SQL + busca híbrida")
    s.add_argument("pedido")
    s.add_argument("--regiao")
    s.add_argument("--ra", nargs="*", help="RAs, com o nome de data/base/regioes.csv")
    s.add_argument("--tipo")
    s.add_argument("--teto", type=float)
    s.add_argument("--exigir", nargs="*", default=[], help="atributos que precisam ser 'sim'")
    s.add_argument("--dia", choices=["seg", "ter", "qua", "qui", "sex", "sab", "dom"], help="aberto neste dia")
    s.add_argument("--hora", help="aberto nesta hora (HH:MM), com --dia")
    s.add_argument("--modelo")
    s.add_argument("-k", type=int, default=10)
    sub.add_parser("limpar", help="apagar páginas brutas com mais de 30 dias (os hashes ficam)")
    sub.add_parser("osm", help="medir a cobertura do OpenStreetMap no DF (só consulta, nada é importado)")
    s = sub.add_parser("comparar-google", help="cobertura Google × OSM × Overture × base (só contagens)")
    s.add_argument("--por-regiao", type=int, default=8, help="lugares sorteados por região, além dos aprovados")
    a = p.parse_args()

    if a.etapa == "descobrir":
        from . import descobrir
        r = descobrir.executar()
    elif a.etapa == "selecionar":
        from . import selecionar
        r = selecionar.repor(a.n or 150) if a.repor else selecionar.executar(a.n)
    elif a.etapa == "rastrear":
        from . import rastrear
        r = rastrear.executar(a.ids)
    elif a.etapa == "preparar":
        from . import extrair
        r = extrair.preparar(a.todos, a.ids)
    elif a.etapa == "ocr":
        from . import ocr
        r = ocr.executar(a.ids)
    elif a.etapa == "validar":
        from . import validar
        r = validar.executar()
    elif a.etapa == "descrever":
        from . import extrair
        r = extrair.preparar_descricoes()
    elif a.etapa == "calcular":
        from . import calcular
        r = calcular.executar()
    elif a.etapa == "vetorizar":
        from . import vetorizar
        r = vetorizar.executar(a.modelo)
    elif a.etapa == "gravar":
        from . import gravar
        r = gravar.executar()
    elif a.etapa == "relatar":
        from . import relatar
        r = relatar.executar()
    elif a.etapa == "buscar":
        from datetime import date, datetime, timedelta
        from . import buscar
        from .contrato import ConsultaBusca, Janela
        janela = None
        if a.dia:  # próxima data com esse dia da semana, na hora pedida (ou 12h)
            hoje = date.today()
            d = hoje + timedelta(days=(buscar.DIAS.index(a.dia) - hoje.weekday()) % 7)
            janela = Janela(inicio=datetime.combine(d, datetime.strptime(a.hora or "12:00", "%H:%M").time()))
        c = ConsultaBusca(texto=a.pedido, regioes=[a.regiao] if a.regiao else [], ras=a.ra or [],
                          tipos_role=[a.tipo] if a.tipo else [], teto_pessoa=a.teto, exigir=a.exigir,
                          janela=janela, k=a.k)
        for linha in buscar.linhas(buscar.buscar(c, a.modelo)):
            print(linha)
        return
    elif a.etapa == "limpar":
        from . import rastrear
        r = rastrear.limpar()
    elif a.etapa == "osm":
        from . import osm
        r = osm.medir()
    elif a.etapa == "comparar-google":
        from . import comparar_google
        r = comparar_google.executar(a.por_regiao)
    print(json.dumps(r, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
