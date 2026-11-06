"""Etapa 9: upsert no PostgreSQL com pgvector, com versao_base.

Lugares e eventos que saíram da rodada ficam inativos, não são apagados, para manter o histórico dos rolês.
"""
import json
from datetime import date

import numpy as np
import psycopg
from pgvector.psycopg import register_vector
from psycopg.types.json import Jsonb

from .config import DSN, PROC, VERSAO
from .vetorizar import PASTA

L_COLS = ["id", "overture_id", "nome", "tipo_role", "categoria", "endereco", "ra", "regiao", "lat", "lon",
          "coord_fonte", "site_oficial", "horarios", "horarios_fonte", "horarios_verificado_em", "couvert",
          "taxa_servico_pct", "precos_fonte", "precos_verificado_em", "custo_pessoa_min", "custo_pessoa_tipico",
          "taxa_entrada", "atributos", "atributos_verificado_em", "status", "status_fonte", "status_verificado_em",
          "estado", "descricao", "ficha", "licenca_origem", "pipeline_versao", "modelo_extracao", "criado_em",
          "atualizado_em"]
E_COLS = ["id", "local_id", "titulo", "inicio", "preco_min", "preco_max", "gratuito", "link_oficial", "regiao",
          "ficha", "verificado_em", "pipeline_versao"]


def conectar():
    c = psycopg.connect(DSN, autocommit=False)
    c.execute("CREATE EXTENSION IF NOT EXISTS vector")
    register_vector(c)
    return c


def _upsert(cur, tabela, cols, linhas, extra=None):
    extra = extra or {}
    todas = cols + list(extra)
    sql = (f"INSERT INTO {tabela} ({', '.join(todas)}) VALUES ({', '.join(['%s'] * len(todas))}) "
           f"ON CONFLICT ({todas[0]}) DO UPDATE SET " + ", ".join(f"{c} = EXCLUDED.{c}" for c in todas[1:]))
    for l in linhas:
        cur.execute(sql, [Jsonb(l[c]) if isinstance(l.get(c), (list, dict)) else l.get(c) for c in cols]
                    + list(extra.values()))


def executar():
    from pathlib import Path
    fichas = json.loads((PROC / "fichas.json").read_text(encoding="utf-8"))
    versao = f"{date.today().isoformat()}-{VERSAO}"
    with conectar() as c, c.cursor() as cur:
        cur.execute(Path(__file__).with_name("schema.sql").read_text(encoding="utf-8"))
        _upsert(cur, "lugares", L_COLS, fichas["lugares"], {"ativo": True, "versao_base": versao})
        ids = [l["id"] for l in fichas["lugares"]]
        cur.execute("UPDATE lugares SET ativo = false WHERE NOT (id = ANY(%s))", (ids,))
        cur.execute("DELETE FROM itens WHERE lugar_id = ANY(%s)", (ids,))
        for l in fichas["lugares"]:
            for i in l["itens"]:
                cur.execute("INSERT INTO itens VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
                            (l["id"], i["item"], i["preco"], i["papel"], i["fonte"], l["precos_verificado_em"]))
        _upsert(cur, "eventos", E_COLS, fichas["eventos"], {"ativo": True, "versao_base": versao})
        cur.execute("UPDATE eventos SET ativo = false WHERE NOT (id = ANY(%s)) OR inicio < now()",
                    ([e["id"] for e in fichas["eventos"]],))
        _upsert(cur, "regioes", ["ra", "regiao", "vizinhas", "ficha"], fichas["regioes"])
        modelos = []
        for arq in sorted(PASTA.glob("*.npz")):
            z = np.load(arq, allow_pickle=False)
            modelo = str(z["modelo"])
            modelos.append(modelo)
            for col, doc, h, v in zip(z["colecao"], z["doc_id"], z["hash"], z["vetor"]):
                cur.execute("""INSERT INTO vetores VALUES (%s, %s, %s, %s, %s)
                               ON CONFLICT (colecao, doc_id, modelo) DO UPDATE
                               SET texto_hash = EXCLUDED.texto_hash, embedding = EXCLUDED.embedding""",
                            (str(col), str(doc), modelo, str(h), v))
        resumo = {"modelos": modelos}
        cur.execute("""INSERT INTO rodadas (versao_base, pipeline_versao, lugares, eventos, resumo)
                       VALUES (%s, %s, %s, %s, %s) ON CONFLICT (versao_base) DO UPDATE
                       SET lugares = EXCLUDED.lugares, eventos = EXCLUDED.eventos, resumo = EXCLUDED.resumo""",
                    (versao, VERSAO, len(ids), len(fichas["eventos"]), Jsonb(resumo)))
        cur.execute("SELECT count(*) FILTER (WHERE ativo), count(*) FROM lugares")
        ativos, total = cur.fetchone()
        cur.execute("SELECT modelo, count(*) FROM vetores GROUP BY 1")
        vet = dict(cur.fetchall())
    return {"versao_base": versao, "lugares_ativos": ativos, "lugares_total": total,
            "eventos": len(fichas["eventos"]), "regioes": len(fichas["regioes"]), "vetores": vet}
