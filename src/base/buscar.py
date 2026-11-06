"""Busca na base: filtros duros em SQL e depois busca híbrida (vetor + texto em português) por RRF.

Implementa o contrato do ADR 0007 (`contrato.py`) sobre o fluxo do ADR 0005 ("Como os LLMs consultam").
A SQL é montada só a partir dos campos validados da ConsultaBusca, sempre com parâmetros: nenhum texto
vindo de LLM ou de usuário entra na string da consulta.
"""
from datetime import datetime, timedelta

from .config import CFG
from .contrato import ConsultaBusca, ItemResultado, ResultadoBusca

B = CFG["busca"]
DIAS = ["seg", "ter", "qua", "qui", "sex", "sab", "dom"]


def _filtros_lugar(c: ConsultaBusca, alias: str, args: dict) -> list[str]:
    """Filtros que valem para o lugar (ou para o local do evento)."""
    f = []
    if c.regioes:
        f.append(f"{alias}.regiao = ANY(%(regioes)s)")
        args["regioes"] = list(c.regioes)
    if c.ras:
        f.append(f"{alias}.ra = ANY(%(ras)s)")
        args["ras"] = list(c.ras)
    for i, at in enumerate(c.exigir):
        f.append(f"{alias}.atributos ->> %(at{i})s = 'sim'")
        args[f"at{i}"] = at
    return f


def montar_sql(c: ConsultaBusca, colecao: str, modelo: str) -> tuple[str, dict]:
    """SQL parametrizada para uma coleção. O vetor da consulta entra depois, em args['vetor']."""
    args = {"modelo": modelo, "n": B["candidatos"], "pedido": c.texto, "k": c.k, "colecao": colecao}
    if colecao == "lugares":
        filtros = ["l.ativo", "l.status = 'ativo'", "l.estado <> 'vencido'"] + _filtros_lugar(c, "l", args)
        if c.tipos_role:
            filtros.append("l.tipo_role = ANY(%(tipos)s)")
            args["tipos"] = list(c.tipos_role)
        if c.teto_pessoa is not None:
            filtros.append("coalesce(l.custo_pessoa_tipico, l.taxa_entrada) <= %(teto)s")
            args["teto"] = c.teto_pessoa
        if c.janela:
            # Aberto no início da janela (limitação declarada no ADR 0007: não confere a janela inteira).
            filtros.append("""EXISTS (SELECT 1 FROM jsonb_array_elements(l.horarios) h WHERE h->>'dia' = %(dia)s
                              AND h->>'abre' <= %(hora)s AND (h->>'fecha' > %(hora)s OR h->>'fecha' < h->>'abre'))""")
            args["dia"] = DIAS[c.janela.inicio.weekday()]
            args["hora"] = c.janela.inicio.strftime("%H:%M")
        base = "SELECT l.id FROM lugares l WHERE " + " AND ".join(filtros)
        tabela = "lugares"
        campos = """'lugares' colecao, d.id, d.nome, d.categoria, d.ra, d.regiao, d.custo_pessoa_tipico,
                    d.taxa_entrada, NULL::timestamp inicio, coalesce(d.horarios_fonte, d.site_oficial) fonte,
                    coalesce(d.horarios_verificado_em, d.precos_verificado_em) verificado_em, d.estado"""
    elif colecao == "eventos":
        filtros = ["e.ativo", "NOT e.cancelado", "NOT e.esgotado"] + _filtros_lugar(c, "l", args)
        if c.teto_pessoa is not None:
            filtros.append("(e.gratuito OR coalesce(e.preco_min, 0) <= %(teto)s)")
            args["teto"] = c.teto_pessoa
        # Evento que começa dentro da janela (sem fim: até 1 dia depois); sem janela, de agora em diante.
        filtros.append("e.inicio >= %(ini)s")
        if c.janela:
            args["ini"] = c.janela.inicio.replace(tzinfo=None)
            args["fim"] = (c.janela.fim or c.janela.inicio + timedelta(days=1)).replace(tzinfo=None)
            filtros.append("e.inicio < %(fim)s")
        else:
            args["ini"] = datetime.now()
        base = "SELECT e.id FROM eventos e LEFT JOIN lugares l ON l.id = e.local_id WHERE " + " AND ".join(filtros)
        tabela = "eventos"
        campos = """'eventos' colecao, d.id, d.titulo nome, NULL categoria, lg.ra, d.regiao, NULL::numeric
                    custo_pessoa_tipico, d.preco_min taxa_entrada, d.inicio, d.link_oficial fonte, d.verificado_em,
                    NULL estado"""
    else:
        raise ValueError(colecao)
    junta_local = "LEFT JOIN lugares lg ON lg.id = d.local_id" if colecao == "eventos" else ""
    sql = f"""
    WITH filtrados AS ({base}),
    vet AS (SELECT v.doc_id, row_number() OVER (ORDER BY v.embedding <=> %(vetor)s) r
            FROM vetores v JOIN filtrados f ON f.id = v.doc_id
            WHERE v.colecao = %(colecao)s AND v.modelo = %(modelo)s
            ORDER BY v.embedding <=> %(vetor)s LIMIT %(n)s),
    txt AS (SELECT t.id doc_id, row_number() OVER (ORDER BY ts_rank(t.ficha_tsv, q) DESC) r
            FROM {tabela} t JOIN filtrados f ON f.id = t.id, websearch_to_tsquery('portuguese', %(pedido)s) q
            WHERE t.ficha_tsv @@ q LIMIT %(n)s),
    rrf AS (SELECT doc_id, sum(1.0 / ({int(B['rrf_k'])} + r)) s FROM (SELECT * FROM vet UNION ALL SELECT * FROM txt) u
            GROUP BY doc_id)
    SELECT {campos}, rrf.s::float pontuacao
    FROM rrf JOIN {tabela} d ON d.id = rrf.doc_id {junta_local}
    ORDER BY rrf.s DESC LIMIT %(k)s"""
    return sql, args


def buscar(c: ConsultaBusca, modelo: str | None = None) -> ResultadoBusca:
    from .gravar import conectar
    from .vetorizar import embutir

    modelo = modelo or CFG["embeddings"]["modelo"]
    vetor = embutir([c.texto], modelo, papel="query")[0]
    itens = []
    with conectar() as cx:
        for col in c.colecoes:
            sql, args = montar_sql(c, col, modelo)
            args["vetor"] = vetor
            cur = cx.execute(sql, args)
            nomes = [d.name for d in cur.description]
            itens += [ItemResultado(**dict(zip(nomes, linha))) for linha in cur.fetchall()]
        versao = cx.execute("SELECT max(versao_base) FROM lugares").fetchone()[0]
    itens.sort(key=lambda i: -i.pontuacao)
    return ResultadoBusca(itens=itens[:c.k], versao_base=versao, modelo_embeddings=modelo, gerado_em=datetime.now())


def linhas(r: ResultadoBusca):
    """Uma linha legível por item (linha de comando)."""
    for i in r.itens:
        if i.colecao == "eventos":
            preco = "gratuito" if not i.taxa_entrada else f"a partir de R$ {i.taxa_entrada:.0f}"
        elif i.taxa_entrada is not None:
            preco = "gratuito" if i.taxa_entrada == 0 else f"entrada R$ {i.taxa_entrada:.0f}"
        else:
            preco = f"R$ {i.custo_pessoa_tipico:.0f}/pessoa" if i.custo_pessoa_tipico is not None else "preço sem informação"
        yield f"{i.pontuacao:.4f}  {i.nome} · {i.categoria or i.colecao} · {i.ra} · {preco} · {i.fonte} (verificado em {i.verificado_em})"
