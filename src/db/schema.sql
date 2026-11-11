-- ==============================================================================
-- ESQUEMA OFICIAL DO BANCO DE DADOS (ORQUESTRADOR DE ROLÊS - GRUPO 7)
-- ==============================================================================
-- PostgreSQL / Supabase na nuvem (sa-east-1) & Docker local (pgvector/pg17)
-- 
-- Decisões de Negócio & Segurança implementadas:
-- 1. Row Level Security (RLS) habilitado em 100% das tabelas.
-- 2. Moeda e Centavos estritos com NUMERIC(10,2) (sem ponto flutuante).
-- 3. Horários com TIMESTAMPTZ (início e fim) com rastreabilidade de data.
-- 4. Sigilo Orçamentário e Segredos (token_hash e token_organizador_hash SHA-256).
-- 5. Rateio individual pós-rolê com tabela despesa_rateios e Pix BACEN.
-- 6. Integridade referencial composta: votos amarrados rigorosamente à mesma sala.
-- 7. Descarte LGPD automatizado (expira_em padrão em 30 dias).
-- ==============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ------------------------------------------------------------------------------
-- 1. TABELA: usuarios (Perfil permanente opcional)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS usuarios (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nome VARCHAR(80) NOT NULL,
    email VARCHAR(120) UNIQUE NULL,
    telefone VARCHAR(30) NULL,
    maior_18_anos BOOLEAN NOT NULL CHECK (maior_18_anos IS TRUE),
    transporte_padrao VARCHAR(40) DEFAULT 'misto' CHECK (transporte_padrao IN ('carro', 'metro_onibus', 'uber', 'misto')),
    restricoes_permanentes TEXT NULL,
    chave_pix_padrao VARCHAR(120) NULL,
    tipo_chave_pix_padrao VARCHAR(30) DEFAULT 'aleatoria',
    criado_em TIMESTAMPTZ DEFAULT NOW(),
    atualizado_em TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_usuarios_email ON usuarios(email);

-- ------------------------------------------------------------------------------
-- 2. TABELA: usuario_enderecos (Pontos de partida frequentes no DF)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS usuario_enderecos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    usuario_id UUID NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    rotulo VARCHAR(50) NOT NULL,                       -- 'Casa', 'Trabalho', 'UnB'
    regiao_ra VARCHAR(80) NOT NULL,                    -- RA do DF (ex: 'Águas Claras', 'Plano Piloto')
    ponto_referencia VARCHAR(200) NULL,                -- Opcional (LGPD)
    is_padrao BOOLEAN DEFAULT FALSE,
    criado_em TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_usuario_enderecos_usuario ON usuario_enderecos(usuario_id);

-- ------------------------------------------------------------------------------
-- 3. TABELA: salas
-- Salas de combinação de rolê (ROLE-XXXX)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS salas (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    codigo_sala VARCHAR(16) NOT NULL UNIQUE,           -- Código amigável (ex: 'ROLE-A1B2')
    nome_role VARCHAR(120) NOT NULL,
    organizador_nome VARCHAR(80) NOT NULL,
    token_organizador_hash VARCHAR(64) NOT NULL,       -- SHA-256 do token do criador
    status VARCHAR(30) NOT NULL DEFAULT 'coletando' CHECK (status IN ('coletando', 'votacao', 'orquestrado', 'finalizada')),
    criador_id UUID NULL REFERENCES usuarios(id) ON DELETE SET NULL,
    janela_escolhida_inicio TIMESTAMPTZ NULL,
    janela_escolhida_fim TIMESTAMPTZ NULL,
    sugestao_vencedora_id UUID NULL,                   -- FK vinculada posteriormente
    janelas_comuns_json JSONB NULL,                    -- Janelas comuns calculadas (JanelaComum)
    resultado_json JSONB NULL,                         -- Metadados do resultado final (Resultado)
    avisos_json JSONB NULL,                            -- Avisos da orquestração
    expira_em TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '30 days'), -- Descarte LGPD (ADR 0008)
    criado_em TIMESTAMPTZ DEFAULT NOW(),
    atualizado_em TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_salas_id_codigo UNIQUE (id, codigo_sala)
);

CREATE INDEX IF NOT EXISTS idx_salas_codigo ON salas(codigo_sala);
CREATE INDEX IF NOT EXISTS idx_salas_status ON salas(status);

-- ------------------------------------------------------------------------------
-- 4. TABELA: sala_participantes
-- Participantes da sala com credencial e sigilo financeiro (RNF-01 e RNF-02)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sala_participantes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    codigo_participante VARCHAR(64) NULL,              -- Identificador de domínio (ex: token_hex de 12 chars)
    sala_id UUID NOT NULL REFERENCES salas(id) ON DELETE CASCADE,
    usuario_id UUID NULL REFERENCES usuarios(id) ON DELETE SET NULL,
    nome VARCHAR(80) NOT NULL,
    token_hash VARCHAR(64) NOT NULL,                   -- SHA-256 do token individual
    confirmado BOOLEAN NOT NULL DEFAULT FALSE,
    limite_gasto_rs NUMERIC(10, 2) NULL CHECK (limite_gasto_rs IS NULL OR limite_gasto_rs >= 0), -- 100% SIGILOSO
    vibe_hoje VARCHAR(200) NULL,
    transporte_hoje VARCHAR(40) NULL,
    perfil_json JSONB NULL,                            -- PerfilInterpretado completo (sem expor no painel público)
    respondeu_em TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_participante_sala_id UNIQUE (sala_id, id)
);

CREATE INDEX IF NOT EXISTS idx_sala_participantes_sala ON sala_participantes(sala_id);

-- ------------------------------------------------------------------------------
-- 5. TABELA: participante_janelas
-- Janelas de disponibilidade com data e origem de saída por janela
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS participante_janelas (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    participante_id UUID NOT NULL REFERENCES sala_participantes(id) ON DELETE CASCADE,
    inicio TIMESTAMPTZ NOT NULL,
    fim TIMESTAMPTZ NOT NULL,
    disponivel BOOLEAN NOT NULL DEFAULT TRUE,
    ra_origem VARCHAR(80) NOT NULL,                    -- RA de onde sai neste horário
    criado_em TIMESTAMPTZ DEFAULT NOW(),
    CHECK (fim > inicio)
);

CREATE INDEX IF NOT EXISTS idx_participante_janelas_part ON participante_janelas(participante_id);

-- ------------------------------------------------------------------------------
-- 6. TABELA: sugestoes_role
-- Cartões de sugestão da IA vinculados aos 93 locais do catálogo 2FA
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sugestoes_role (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sala_id UUID NOT NULL REFERENCES salas(id) ON DELETE CASCADE,
    posicao INT DEFAULT 1,
    letra_card VARCHAR(4) DEFAULT 'A',                 -- 'A', 'B', 'C', 'D'
    local_id VARCHAR(64) NOT NULL,                     -- RF-16: obrigatório dos 93 lugares
    nome_local VARCHAR(120) NOT NULL,
    tipo VARCHAR(60) NOT NULL DEFAULT 'bar',
    regiao_ra VARCHAR(80) NOT NULL,
    regiao_texto VARCHAR(120) NULL,
    endereco TEXT NOT NULL,
    inicio TIMESTAMPTZ NOT NULL,
    fim TIMESTAMPTZ NOT NULL,
    horario_texto VARCHAR(120) NOT NULL,
    horario_situacao VARCHAR(40) DEFAULT 'aberto',
    contagem VARCHAR(40) DEFAULT 'todos podem',
    consumo_rs NUMERIC(10, 2) NOT NULL DEFAULT 0.00 CHECK (consumo_rs >= 0),
    gasto_min NUMERIC(10, 2) NOT NULL DEFAULT 0.00 CHECK (gasto_min >= 0),
    gasto_max NUMERIC(10, 2) NOT NULL DEFAULT 0.00 CHECK (gasto_max >= 0),
    tempo_medio_min INT NULL,
    tempo_max_min INT NULL,
    nota_justica NUMERIC(5, 2) DEFAULT 0.00,           -- Algoritmo Menor Miséria
    pontuacao NUMERIC(5, 2) DEFAULT 0.00,
    explicacao TEXT NOT NULL,
    tiktok_url TEXT NULL,
    fonte VARCHAR(80) DEFAULT '2fa',
    vibes_json JSONB NULL,
    por_participante_json JSONB NULL,                  -- Custo e tempo por participante (RF-15)
    criado_em TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_sugestao_sala_id UNIQUE (sala_id, id)
);

CREATE INDEX IF NOT EXISTS idx_sugestoes_sala ON sugestoes_role(sala_id);

-- Adiciona a FK da sugestão vencedora e garante migração idempotente de colunas em bancos já existentes
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_salas_sugestao_vencedora'
    ) THEN
        ALTER TABLE salas ADD CONSTRAINT fk_salas_sugestao_vencedora
        FOREIGN KEY (sugestao_vencedora_id) REFERENCES sugestoes_role(id) ON DELETE SET NULL;
    END IF;

    ALTER TABLE salas ADD COLUMN IF NOT EXISTS janelas_comuns_json JSONB NULL;
    ALTER TABLE salas ADD COLUMN IF NOT EXISTS resultado_json JSONB NULL;
    ALTER TABLE salas ADD COLUMN IF NOT EXISTS avisos_json JSONB NULL;

    ALTER TABLE sala_participantes ADD COLUMN IF NOT EXISTS codigo_participante VARCHAR(64) NULL;
    ALTER TABLE sala_participantes ADD COLUMN IF NOT EXISTS perfil_json JSONB NULL;
    ALTER TABLE sala_participantes ALTER COLUMN limite_gasto_rs DROP NOT NULL;

    ALTER TABLE sugestoes_role ADD COLUMN IF NOT EXISTS regiao_texto VARCHAR(120) NULL;
    ALTER TABLE sugestoes_role ADD COLUMN IF NOT EXISTS vibes_json JSONB NULL;
    ALTER TABLE sugestoes_role ADD COLUMN IF NOT EXISTS por_participante_json JSONB NULL;
END $$;

-- ------------------------------------------------------------------------------
-- 7. TABELA: votos
-- Votação democrática vinculada estritamente à mesma sala
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS votos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sala_id UUID NOT NULL,
    participante_id UUID NOT NULL,
    sugestao_id UUID NOT NULL,
    votado_em TIMESTAMPTZ DEFAULT NOW(),
    FOREIGN KEY (sala_id, participante_id) REFERENCES sala_participantes(sala_id, id) ON DELETE CASCADE,
    FOREIGN KEY (sala_id, sugestao_id) REFERENCES sugestoes_role(sala_id, id) ON DELETE CASCADE,
    CONSTRAINT uq_voto_participante_sugestao UNIQUE (participante_id, sugestao_id)
);

CREATE INDEX IF NOT EXISTS idx_votos_sala ON votos(sala_id);

-- ------------------------------------------------------------------------------
-- 8. TABELA: despesas_pos_role
-- Divisão da conta e geração de Pix BACEN
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS despesas_pos_role (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sala_id UUID NOT NULL REFERENCES salas(id) ON DELETE CASCADE,
    pagador_participante_id UUID NULL REFERENCES sala_participantes(id) ON DELETE SET NULL,
    pagador_nome VARCHAR(80) NOT NULL,
    valor_total_rs NUMERIC(10, 2) NOT NULL CHECK (valor_total_rs >= 0),
    chave_pix VARCHAR(120) NOT NULL,
    tipo_chave_pix VARCHAR(30) DEFAULT 'aleatoria',
    itens_json JSONB NULL,
    comprovante_url TEXT NULL,
    quitado BOOLEAN DEFAULT FALSE,
    criado_em TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_despesas_sala ON despesas_pos_role(sala_id);

-- ------------------------------------------------------------------------------
-- 9. TABELA: despesa_rateios
-- Baixa individual por devedor no Pix
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS despesa_rateios (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    despesa_id UUID NOT NULL REFERENCES despesas_pos_role(id) ON DELETE CASCADE,
    devedor_participante_id UUID NOT NULL REFERENCES sala_participantes(id) ON DELETE CASCADE,
    valor NUMERIC(10, 2) NOT NULL CHECK (valor >= 0),
    pago_em TIMESTAMPTZ NULL,
    criado_em TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_despesa_devedor UNIQUE (despesa_id, devedor_participante_id)
);

CREATE INDEX IF NOT EXISTS idx_despesa_rateios_despesa ON despesa_rateios(despesa_id);

-- ==============================================================================
-- BLINDAGEM ROW LEVEL SECURITY (RLS) - RNF-01 e RNF-02
-- Habilita RLS em todas as tabelas para bloquear acesso REST desprotegido
-- ==============================================================================
ALTER TABLE usuarios ENABLE ROW LEVEL SECURITY;
ALTER TABLE usuario_enderecos ENABLE ROW LEVEL SECURITY;
ALTER TABLE salas ENABLE ROW LEVEL SECURITY;
ALTER TABLE sala_participantes ENABLE ROW LEVEL SECURITY;
ALTER TABLE participante_janelas ENABLE ROW LEVEL SECURITY;
ALTER TABLE sugestoes_role ENABLE ROW LEVEL SECURITY;
ALTER TABLE votos ENABLE ROW LEVEL SECURITY;
ALTER TABLE despesas_pos_role ENABLE ROW LEVEL SECURITY;
ALTER TABLE despesa_rateios ENABLE ROW LEVEL SECURITY;
