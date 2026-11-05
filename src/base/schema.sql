-- Base de lugares e eventos em PostgreSQL com pgvector (ADR 0005, Parte B).
-- Recriável a partir dos CSVs de data/base e da configuração. Evidências e páginas brutas não entram aqui.
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS lugares (
    id                      text PRIMARY KEY,
    overture_id             text,
    nome                    text NOT NULL,
    tipo_role               text NOT NULL,
    categoria               text NOT NULL,
    endereco                text,
    ra                      text NOT NULL,
    regiao                  text NOT NULL,
    lat                     double precision,
    lon                     double precision,
    coord_fonte             text,
    site_oficial            text,
    horarios                jsonb NOT NULL DEFAULT '[]',
    horarios_fonte          text,
    horarios_verificado_em  date,
    couvert                 numeric,
    taxa_servico_pct        numeric,
    precos_fonte            text,
    precos_verificado_em    date,
    custo_pessoa_min        numeric,
    custo_pessoa_tipico     numeric,
    taxa_entrada            numeric,
    atributos               jsonb NOT NULL DEFAULT '{}',
    atributos_verificado_em date,
    status                  text NOT NULL DEFAULT 'ativo',
    status_fonte            text,
    status_verificado_em    date,
    estado                  text NOT NULL DEFAULT 'exato',
    descricao               text,
    ficha                   text NOT NULL,
    ficha_tsv               tsvector GENERATED ALWAYS AS (to_tsvector('portuguese', ficha)) STORED,
    licenca_origem          text,
    ativo                   boolean NOT NULL DEFAULT true,
    versao_base             text,
    pipeline_versao         text,
    modelo_extracao         text,
    criado_em               date,
    atualizado_em           date
);
CREATE INDEX IF NOT EXISTS lugares_tsv ON lugares USING gin (ficha_tsv);
CREATE INDEX IF NOT EXISTS lugares_filtro ON lugares (ativo, regiao, tipo_role);

CREATE TABLE IF NOT EXISTS itens (
    lugar_id      text REFERENCES lugares (id) ON DELETE CASCADE,
    item          text,
    preco         numeric NOT NULL,
    papel         text NOT NULL,
    fonte         text,
    verificado_em date,
    PRIMARY KEY (lugar_id, item)
);

CREATE TABLE IF NOT EXISTS eventos (
    id              text PRIMARY KEY,
    local_id        text REFERENCES lugares (id),
    titulo          text NOT NULL,
    inicio          timestamp NOT NULL,
    preco_min       numeric,
    preco_max       numeric,
    gratuito        boolean,
    esgotado        boolean DEFAULT false,
    cancelado       boolean DEFAULT false,
    link_oficial    text,
    regiao          text,
    ficha           text NOT NULL,
    ficha_tsv       tsvector GENERATED ALWAYS AS (to_tsvector('portuguese', ficha)) STORED,
    verificado_em   date,
    ativo           boolean NOT NULL DEFAULT true,
    versao_base     text,
    pipeline_versao text
);
CREATE INDEX IF NOT EXISTS eventos_tsv ON eventos USING gin (ficha_tsv);

CREATE TABLE IF NOT EXISTS regioes (
    ra        text PRIMARY KEY,
    regiao    text NOT NULL,
    vizinhas  jsonb NOT NULL DEFAULT '[]',
    ficha     text NOT NULL,
    ficha_tsv tsvector GENERATED ALWAYS AS (to_tsvector('portuguese', ficha)) STORED
);

-- Um vetor por documento e por modelo: permite comparar BGE-M3 e e5 sobre a mesma base.
CREATE TABLE IF NOT EXISTS vetores (
    colecao    text NOT NULL,          -- lugares, eventos ou regioes
    doc_id     text NOT NULL,
    modelo     text NOT NULL,
    texto_hash text NOT NULL,
    embedding  vector(1024) NOT NULL,
    PRIMARY KEY (colecao, doc_id, modelo)
);
CREATE INDEX IF NOT EXISTS vetores_hnsw ON vetores USING hnsw (embedding vector_cosine_ops);

CREATE TABLE IF NOT EXISTS rodadas (
    versao_base     text PRIMARY KEY,
    pipeline_versao text,
    executada_em    timestamp DEFAULT now(),
    lugares         int,
    eventos         int,
    resumo          jsonb
);
