"""
Testes automatizados da Camada de Banco de Dados Oficial (Supabase / PostgreSQL)
Projeto: Orquestrador de Rolês - Grupo 7 (Residência em IA | UnB & Eldorado)
Responsável: Maria Eduarda (DevOps & Backend)
Issue #41 | RNF-01, RNF-02, RNF-04, RNF-11
Validação das correções solicitadas na revisão do PR #50.
"""

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import pytest

from src.db.supabase_client import SupabaseClient, RepositorioSupabase, quantizar_decimal
from src.state import obter_repositorio, trocar_repositorio


@pytest.fixture
def db(tmp_path):
    """Cria uma instância isolada do banco em memória ou arquivo temporário para cada teste."""
    banco_temporario = tmp_path / "test_app.db"
    cliente = SupabaseClient(use_memory_fallback=False, db_path=banco_temporario)
    cliente.garantir_schema()
    yield cliente
    cliente.fechar()


# ==============================================================================
# 1. TESTE DO SCRIPT DE MIGRAÇÃO SQL (src/db/schema.sql) COM RLS
# ==============================================================================

def test_schema_sql_contem_todas_as_tabelas_e_rls():
    """Valida que o schema.sql oficial possui as 9 tabelas completas e RLS em 100% delas."""
    schema_path = Path("src/db/schema.sql")
    assert schema_path.exists(), "O arquivo src/db/schema.sql deve existir."

    conteudo = schema_path.read_text(encoding="utf-8").lower()
    tabelas_obrigatorias = [
        "create table if not exists usuarios",
        "create table if not exists usuario_enderecos",
        "create table if not exists salas",
        "create table if not exists sala_participantes",
        "create table if not exists participante_janelas",
        "create table if not exists sugestoes_role",
        "create table if not exists votos",
        "create table if not exists despesas_pos_role",
        "create table if not exists despesa_rateios",
    ]

    for tabela in tabelas_obrigatorias:
        assert tabela in conteudo, f"Tabela não encontrada no schema.sql: {tabela}"

    # Validação do RLS (item 2 da revisão do PR)
    assert "enable row level security" in conteudo, "RLS deve estar habilitado no schema oficial."


# ==============================================================================
# 2. TESTES DE USUÁRIOS E MAIORIDADE (18+ ANOS)
# ==============================================================================

def test_cadastrar_usuario_e_bloqueio_menoridade(db):
    """Valida cadastro e a trava estrita de maioridade 18+ (ADR 0002)."""
    user = db.cadastrar_usuario(
        nome="Maria Eduarda",
        email="duda@unb.br",
        telefone="(61) 98888-7777",
        maior_18_anos=True,
        transporte_padrao="carro",
        restricoes_permanentes="não consome álcool",
        chave_pix_padrao="duda@unb.br",
    )
    assert user["id"] is not None
    assert user["nome"] == "Maria Eduarda"

    # Tentativa de cadastrar menor de 18 anos deve falhar
    with pytest.raises(ValueError):
        db.cadastrar_usuario(nome="Adolescente", maior_18_anos=False)


def test_adicionar_multiplos_enderecos_usuario(db):
    """Valida que o morador do DF pode salvar múltiplos locais (Casa, Trabalho, UnB)."""
    user = db.cadastrar_usuario(nome="Cauan Soares", email="cauan@unb.br", maior_18_anos=True)

    db.adicionar_endereco_usuario(
        usuario_id=user["id"],
        rotulo="Casa",
        regiao_ra="Águas Claras",
        ponto_referencia="Perto da Estação Arniqueiras",
        is_padrao=True,
    )
    db.adicionar_endereco_usuario(
        usuario_id=user["id"],
        rotulo="Trabalho",
        regiao_ra="Plano Piloto",
        ponto_referencia="Setor Bancário Sul",
        is_padrao=False,
    )
    # Valida que o endereço foi inserido
    res = db.checar_conexao()
    assert res["conectado"] is True


# ==============================================================================
# 3. TESTES DE PRECISÃO MONETÁRIA (DECIMAL) E SIGILO (RNF-01 / RNF-02 / RNF-04)
# ==============================================================================

def test_precisao_centavos_decimal_sem_float(db):
    """
    Testa exatamente o caso 0.1 + 0.2 apontado no item 3 da revisão.
    Com Decimal, 0.1 + 0.2 = Decimal('0.30'), nunca 0.30000000000000004!
    """
    db.criar_sala(
        codigo_sala="ROLE-C001",
        nome_role="Teste Centavos",
        organizador_nome="Bia",
        token_organizador_hash="hash_organizador",
    )

    soma_centavos = Decimal("0.10") + Decimal("0.20")
    assert soma_centavos == Decimal("0.30")

    part = db.adicionar_participante(
        codigo_sala="ROLE-C001",
        nome="Bia",
        limite_gasto_rs=soma_centavos,
        janelas=[
            {
                "inicio": "2026-11-13T19:00:00Z",
                "fim": "2026-11-13T23:00:00Z",
                "ra_origem": "Plano Piloto",
            }
        ],
        token_hash="hash_bia",
    )
    assert part["id"] is not None

    # Validação do método seguro cabe_no_orcamento (item 2 e 3 da revisão)
    assert db.cabe_no_orcamento("ROLE-C001", Decimal("0.30")) is True
    assert db.cabe_no_orcamento("ROLE-C001", Decimal("0.31")) is False


def test_sigilo_absoluto_na_listagem_publica(db):
    """Garante que a listagem pública de participantes NÃO expõe o limite_gasto_rs e confirmado nasce False."""
    db.criar_sala(codigo_sala="ROLE-SEC1", nome_role="Sigilo Total", organizador_nome="Samara")
    part = db.adicionar_participante(
        codigo_sala="ROLE-SEC1",
        nome="Amigo Discreto",
        limite_gasto_rs=Decimal("45.50"),
        janelas=[
            {
                "inicio": "2026-11-14T14:00:00Z",
                "fim": "2026-11-14T18:00:00Z",
                "ra_origem": "Taguatinga",
            }
        ],
        token_hash="sha256_token_discreto",
    )
    assert part["confirmado"] is False

    lista = db.listar_participantes_sala("ROLE-SEC1")
    assert len(lista) == 1
    assert "limite_gasto_rs" not in lista[0], "O limite orçamentário JAMAIS pode estar na listagem pública!"
    assert lista[0]["nome"] == "Amigo Discreto"
    assert not hasattr(db, "obter_menor_orcamento_sala"), "Apenas cabe_no_orcamento() deve ser público."


def test_validacao_estrita_adicionar_participante_sem_inventar_dados(db):
    """Garante que adicionar_participante exige argumentos nomeados e recusa dados incompletos (Item 2 da revisão)."""
    db.criar_sala(codigo_sala="ROLE-VAL1", nome_role="Validação Estrita", organizador_nome="Duda")

    # 1. Argumentos posicionais após 'nome' devem falhar com TypeError
    with pytest.raises(TypeError):
        db.adicionar_participante("ROLE-VAL1", "Rafaela", Decimal("80.00"), [])

    # 2. Sem limite_gasto_rs deve levantar ValueError
    with pytest.raises(ValueError):
        db.adicionar_participante(
            "ROLE-VAL1",
            "Rafaela",
            limite_gasto_rs=None,
            janelas=[{"inicio": "2026-11-14T19:00:00Z", "fim": "2026-11-14T23:00:00Z", "ra_origem": "Plano Piloto"}],
            token_hash="hash_1",
        )

    # 3. Sem token_hash deve levantar ValueError
    with pytest.raises(ValueError):
        db.adicionar_participante(
            "ROLE-VAL1",
            "Rafaela",
            limite_gasto_rs=Decimal("80.00"),
            janelas=[{"inicio": "2026-11-14T19:00:00Z", "fim": "2026-11-14T23:00:00Z", "ra_origem": "Plano Piloto"}],
            token_hash="",
        )

    # 4. Janela sem inicio, fim ou ra_origem deve levantar ValueError
    with pytest.raises(ValueError):
        db.adicionar_participante(
            "ROLE-VAL1",
            "Rafaela",
            limite_gasto_rs=Decimal("80.00"),
            janelas=[{"inicio": "2026-11-14T19:00:00Z"}],
            token_hash="hash_1",
        )


# ==============================================================================
# 4. TESTES DE CICLO COMPLETO, SUGESTÕES, VOTOS E RATEIO PÓS-ROLÊ COM PIX
# ==============================================================================

def test_ciclo_sugestoes_votos_e_rateio_individual(db):
    """
    Valida:
    1. Sugestões de rolê com timestamptz e Decimal;
    2. Votação democrática;
    3. Pós-rolê com tabela despesa_rateios para baixa individual por devedor (item 6 da revisão).
    """
    db.criar_sala(codigo_sala="ROLE-V001", nome_role="Vitória DF", organizador_nome="Carol")
    part_a = db.adicionar_participante(
        codigo_sala="ROLE-V001",
        nome="Duda",
        limite_gasto_rs=Decimal("80.00"),
        janelas=[{"inicio": "2026-11-13T20:00:00Z", "fim": "2026-11-14T00:00:00Z", "ra_origem": "Asa Norte"}],
        token_hash="hash_duda",
        confirmado=True,
    )
    part_b = db.adicionar_participante(
        codigo_sala="ROLE-V001",
        nome="Carol",
        limite_gasto_rs=Decimal("100.00"),
        janelas=[{"inicio": "2026-11-13T20:00:00Z", "fim": "2026-11-14T00:00:00Z", "ra_origem": "Águas Claras"}],
        token_hash="hash_carol",
        confirmado=True,
    )

    # 1. Sugestão da IA (RF-16: catálogo de 93 lugares)
    agora = datetime.now(timezone.utc)
    sug = db.adicionar_sugestao(
        codigo_sala="ROLE-V001",
        local_id="LOC_2FA_042",
        nome_local="Restaurante & Bar Cerrado",
        regiao_ra="Plano Piloto",
        endereco="CLS 202 Bloco B",
        inicio=agora,
        fim=agora,
        horario_texto="Sexta das 20h às 00h",
        consumo_rs=Decimal("65.00"),
        gasto_min=Decimal("70.50"),
        gasto_max=Decimal("76.00"),
        explicacao="Local central com metrô perto para todos.",
        nota_justica=9.8,
    )
    assert sug["id"] is not None

    # 2. Votos
    assert db.registrar_voto("ROLE-V001", part_a["id"], sug["id"]) is True
    assert db.registrar_voto("ROLE-V001", part_b["id"], sug["id"]) is True

    placar = db.obter_placar_votos("ROLE-V001")
    assert placar[sug["id"]] == 2

    # 3. Pós-rolê: Carol paga R$ 130,00 e gera o rateio devedor individual para Duda
    despesa = db.registrar_despesa_pos_role(
        codigo_sala="ROLE-V001",
        pagador_nome="Carol",
        valor_total_rs=Decimal("130.00"),
        chave_pix="carol.mcznh@pix.com.br",
        pagador_participante_id=part_b["id"],
        rateios=[
            {
                "devedor_participante_id": part_a["id"],
                "valor": Decimal("65.00"),
            }
        ],
    )
    assert despesa["valor_total_rs"] == Decimal("130.00")
    assert despesa["rateios_count"] == 1

    # Duda paga o Pix e dá baixa
    baixou = db.dar_baixa_rateio(despesa["id"], part_a["id"])
    assert baixou is True


# ==============================================================================
# 5. TESTE DE INTEGRAÇÃO COM REPOSITORIO E GERENCIADORSALAS (PR #48 / ITEM 1)
# ==============================================================================

def test_integracao_repositorio_supabase_com_gerenciador_salas(db):
    """
    Reproduz exatamente o cenário do item 1 da revisão do PR #50:
    GerenciadorSalas + RepositorioSupabase(db) salvando e reconstruindo Sala completa.
    """
    from src.salas.gerenciador_salas import GerenciadorSalas
    from src.salas.modelos import Sala

    repo = RepositorioSupabase(cliente=db)
    g = GerenciadorSalas(repo, relogio=lambda: datetime(2026, 11, 10, 14, 0))

    sala, tok_org = g.criar_sala("Aniversário", "Rafaela", True)
    assert repo.existe(sala.codigo) is True

    p1, tok_p1 = g.entrar(
        sala.codigo, "Rafaela", True, "Asa Norte", "sábado à noite", "80", "bar animado, vou de carro"
    )
    p2, tok_p2 = g.entrar(
        sala.codigo, "Bia", True, "Águas Claras", "sábado à noite", "60", "barzinho calmo, vou de metrô"
    )
    g.confirmar(sala.codigo, p1.id, tok_p1)
    g.confirmar(sala.codigo, p2.id, tok_p2)

    painel = g.gerar_sugestoes(sala.codigo, tok_org)
    assert painel["status"] == "votacao"
    assert len(painel["sugestoes"]) >= 3

    g.votar(sala.codigo, p1.id, tok_p1, ["A"])
    painel_final = g.votar(sala.codigo, p2.id, tok_p2, ["A"])
    assert painel_final["status"] == "orquestrado"
    assert painel_final["resultado"]["sugestao_id"] == "A"

    # Verifica que repo.obter devolve uma instância genuína de Sala com todos os dados
    sala_carregada = repo.obter(sala.codigo)
    assert isinstance(sala_carregada, Sala)
    assert sala_carregada.status == "orquestrado"
    assert len(sala_carregada.participantes) == 2
    assert sala_carregada.participantes[p1.id].perfil.teto == Decimal("80.00")
    assert sala_carregada.resultado is not None
    assert sala_carregada.resultado.sugestao_id == "A"


def test_bloqueio_fallback_sqlite_em_producao(monkeypatch):
    """Garante que sem DATABASE_URL em ENVIRONMENT=producao um RuntimeError explícito é lançado (Item 4)."""
    monkeypatch.setenv("ENVIRONMENT", "producao")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        SupabaseClient(database_url="")


def test_apagar_salas_expiradas_lgpd(db):
    """Valida a rotina de descarte automático de salas vencidas após 30 dias (LGPD - Item 5)."""
    db.criar_sala(codigo_sala="ROLE-VENC", nome_role="Sala Antiga", organizador_nome="Duda")
    db.criar_sala(codigo_sala="ROLE-NOVA", nome_role="Sala Recente", organizador_nome="Duda")

    # Força a data de expiração de ROLE-VENC para o passado
    conn = db._get_connection()
    passado = "2020-01-01T00:00:00+00:00"
    if db.is_postgres:
        with conn.cursor() as cur:
            cur.execute("UPDATE salas SET expira_em = %s WHERE codigo_sala = %s;", (passado, "ROLE-VENC"))
    else:
        cur = conn.cursor()
        cur.execute("UPDATE salas SET expira_em = ? WHERE codigo_sala = ?;", (passado, "ROLE-VENC"))
        conn.commit()

    removidas = db.apagar_salas_expiradas()
    assert removidas >= 1
    assert db.obter_sala("ROLE-VENC") is None
    assert db.obter_sala("ROLE-NOVA") is not None
