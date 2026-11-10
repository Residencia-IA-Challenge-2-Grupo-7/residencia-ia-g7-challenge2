-- ==============================================================================
-- SCHEMA OFICIAL DO BANCO DE DADOS (SUPABASE / POSTGRESQL)
-- Projeto: Orquestrador de Rolês - Grupo 7 (Residência em IA | UnB & Eldorado)
-- Responsável: Maria Eduarda (DevOps & Backend)
-- Issue #41 | Referência: GUIA_OFICIAL_PROJETO.md
-- ==============================================================================
-- Regras de Negócio Implementadas:
-- 1. Cadastro de Usuário (Perfil Fixo) vs. Participação no Rolê (Dados Dinâmicos).
-- 2. Múltiplos endereços salvos (Casa, Trabalho, UnB) com endereço padrão.
-- 3. Origem associada à Janela de Horário (Sexta sai do Trabalho, Sábado sai de Casa).
-- 4. Blindagem Absoluta de Sigilo Orçamentário (RNF-01 e RNF-02).
-- ==============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ------------------------------------------------------------------------------
-- 1. TABELA: usuarios
-- Perfil base do usuário (preenche uma única vez ao se cadastrar no app)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS usuarios (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nome VARCHAR(80) NOT NULL,
    email VARCHAR(120) UNIQUE NULL,
    telefone VARCHAR(30) NULL,
    maior_18_anos BOOLEAN NOT NULL DEFAULT TRUE,       -- Requisito obrigatório do MVP (ADR 0002)
    transporte_padrao VARCHAR(40) DEFAULT 'misto',     -- 'carro', 'metro_onibus', 'uber', 'misto'
    restricoes_permanentes TEXT NULL,                  -- Ex: 'vegetariano, não consome álcool'
    chave_pix_padrao VARCHAR(120) NULL,                -- Chave Pix padrão para receber troco/divisão
    tipo_chave_pix_padrao VARCHAR(30) DEFAULT 'aleatoria',
    criado_em TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    atualizado_em TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_usuarios_email ON usuarios(email);

-- ------------------------------------------------------------------------------
-- 2. TABELA: usuario_enderecos
-- Endereços salvos do usuário (Casa, Trabalho, Faculdade/UnB) no DF
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS usuario_enderecos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    usuario_id UUID NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    rotulo VARCHAR(50) NOT NULL,                       -- 'Casa', 'Trabalho', 'Faculdade/UnB', 'Outro'
    regiao_ra VARCHAR(80) NOT NULL,                    -- Qual das 35 RAs do DF (ex: 'Águas Claras', 'Plano Piloto')
    ponto_referencia VARCHAR(200) NOT NULL,            -- Ex: 'Perto da Estação Arniqueiras', 'SBS Qd 2'
    is_padrao BOOLEAN DEFAULT FALSE,                   -- Marca o endereço principal residencial
    criado_em TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_usuario_enderecos_usuario ON usuario_enderecos(usuario_id);

-- ------------------------------------------------------------------------------
-- 3. TABELA: salas
-- Salas de combinação de rolê entre amigos (2 a 20 membros adultos)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS salas (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    codigo_sala VARCHAR(32) NOT NULL UNIQUE,           -- Código amigável (ex: 'ROLE123')
    nome_role VARCHAR(120) NOT NULL,                   -- Ex: 'Aniversário do Cadu'
    criador_id UUID NULL REFERENCES usuarios(id) ON DELETE SET NULL,
    criador_nome VARCHAR(80) NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'aberta',      -- 'aberta', 'votando', 'fechada', 'finalizada'
    janela_escolhida_json JSONB NULL,                  -- Janela em comum eleita (dia, horário e participantes)
    sugestao_vencedora_id UUID NULL,
    criado_em TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    atualizado_em TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_salas_codigo ON salas(codigo_sala);
CREATE INDEX IF NOT EXISTS idx_salas_status ON salas(status);

-- ------------------------------------------------------------------------------
-- 4. TABELA: sala_participantes
-- Respostas de cada amigo especificamente para ESTE rolê.
-- Implementa a amarração da Origem por Janela de Horário e Sigilo Orçamentário.
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sala_participantes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sala_id UUID NOT NULL REFERENCES salas(id) ON DELETE CASCADE,
    usuario_id UUID NULL REFERENCES usuarios(id) ON DELETE SET NULL,
    nome VARCHAR(80) NOT NULL,
    -- Janelas com origem associada em JSON:
    -- Ex: [{"dia": "sex", "horario": "19h", "rotulo": "Trabalho", "regiao_ra": "Plano Piloto"},
    --      {"dia": "sab", "horario": "15h", "rotulo": "Casa", "regiao_ra": "Águas Claras"}]
    janelas_disponiveis_json JSONB NOT NULL,
    limite_gasto_rs NUMERIC(10, 2) NOT NULL,           -- RNF-01 e RNF-02: 100% SIGILOSO (nunca exposto publicamente)
    vibe_hoje VARCHAR(200) NULL,                       -- Ex: "Bar calmo com música ao vivo"
    transporte_hoje VARCHAR(40) NULL,                  -- Como vai hoje ('carro', 'metro', 'uber')
    respondeu_em TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sala_participantes_sala ON sala_participantes(sala_id);
CREATE INDEX IF NOT EXISTS idx_sala_participantes_usuario ON sala_participantes(usuario_id);

-- ------------------------------------------------------------------------------
-- 5. TABELA: sugestoes_role
-- Os 3 a 4 cartões de sugestão gerados pela IA após cruzar horários, menor orçamento
-- e rotas no DF (ligados aos 93 locais da base oficial 2FA).
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sugestoes_role (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sala_id UUID NOT NULL REFERENCES salas(id) ON DELETE CASCADE,
    local_id VARCHAR(64) NULL,                         -- ID no catálogo 2FA da Letícia
    nome_local VARCHAR(120) NOT NULL,
    regiao_ra VARCHAR(80) NOT NULL,
    endereco TEXT NOT NULL,
    dia_horario_sugerido VARCHAR(120) NOT NULL,
    faixa_gasto_rs NUMERIC(10, 2) NOT NULL,            -- Consumo médio estimado + deslocamento
    mobility_summary TEXT NULL,                        -- Ex: "Média de 18 min de metrô para o grupo"
    ranking_justica NUMERIC(5, 2) DEFAULT 0.0,         -- Score do mediador (Menor Miséria)
    motivo_escolha TEXT NULL,
    criado_em TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sugestoes_sala ON sugestoes_role(sala_id);

-- ------------------------------------------------------------------------------
-- 6. TABELA: votos
-- Votação democrática de múltipla escolha dos amigos nos 3 a 4 cartões
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS votos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sala_id UUID NOT NULL REFERENCES salas(id) ON DELETE CASCADE,
    participante_id UUID NOT NULL REFERENCES sala_participantes(id) ON DELETE CASCADE,
    sugestao_id UUID NOT NULL REFERENCES sugestoes_role(id) ON DELETE CASCADE,
    votado_em TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT uq_participante_sugestao UNIQUE (participante_id, sugestao_id)
);

CREATE INDEX IF NOT EXISTS idx_votos_sala ON votos(sala_id);
CREATE INDEX IF NOT EXISTS idx_votos_sugestao ON votos(sugestao_id);

-- ------------------------------------------------------------------------------
-- 7. TABELA: despesas_pos_role
-- Pós-Rolê (Tela 4): leitura da nota fiscal, divisão de conta e Pix (BACEN)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS despesas_pos_role (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sala_id UUID NOT NULL REFERENCES salas(id) ON DELETE CASCADE,
    pagador_nome VARCHAR(80) NOT NULL,
    valor_total_rs NUMERIC(10, 2) NOT NULL,
    chave_pix VARCHAR(120) NOT NULL,
    tipo_chave_pix VARCHAR(30) DEFAULT 'aleatoria',
    itens_json JSONB NULL,                             -- Itens identificados na comanda/nota fiscal
    comprovante_url TEXT NULL,
    quitado BOOLEAN DEFAULT FALSE,
    criado_em TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_despesas_sala ON despesas_pos_role(sala_id);
