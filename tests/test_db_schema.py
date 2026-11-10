"""
Testes automatizados da Camada de Banco de Dados Oficial (Supabase / PostgreSQL)
Projeto: Orquestrador de Rolês - Grupo 7 (Residência em IA | UnB & Eldorado)
Responsável: Maria Eduarda (DevOps & Backend)
Issue #41 | RNF-01, RNF-02, RNF-11
"""

from pathlib import Path
import pytest

from src.db.supabase_client import SupabaseClient
from src.db.models import UsuarioCadastro, JanelaComOrigem


@pytest.fixture
def db(tmp_path):
    """Cria uma instância isolada do banco em arquivo temporário para cada teste."""
    banco_temporario = tmp_path / "test_app.db"
    return SupabaseClient(use_memory_fallback=False, db_path=banco_temporario)


# ==============================================================================
# TESTE DO SCRIPT DE MIGRAÇÃO SQL (src/db/schema.sql)
# ==============================================================================

def test_schema_sql_contem_todas_as_tabelas():
    """Valida que o schema.sql oficial possui as tabelas completas do modelo de negócio."""
    schema_path = Path("src/db/schema.sql")
    assert schema_path.exists(), "O arquivo src/db/schema.sql deve existir."

    conteudo = schema_path.read_text(encoding="utf-8").lower()
    tabelas_obrigatorias = [
        "create table if not exists usuarios",
        "create table if not exists usuario_enderecos",
        "create table if not exists salas",
        "create table if not exists sala_participantes",
        "create table if not exists sugestoes_role",
        "create table if not exists votos",
        "create table if not exists despesas_pos_role",
    ]

    for tabela in tabelas_obrigatorias:
        assert tabela in conteudo, f"Tabela não encontrada no schema.sql: {tabela}"


# ==============================================================================
# TESTES DE USUÁRIOS E MÚLTIPLOS ENDEREÇOS (Casa, Trabalho, UnB)
# ==============================================================================

def test_cadastrar_usuario_e_bloqueio_menoridade(db):
    """Valida cadastro e a trava estrita de maioridade 18+ (ADR 0002)."""
    user = db.cadastrar_usuario(
        nome="Maria Eduarda",
        email="duda@unb.br",
        telefone="(61) 98888-7777",
        maior_18_anos=True,
        transporte_padrao="carro",
        restricoes_permanentes="não bebe cerveja",
        chave_pix_padrao="duda@unb.br",
    )
    assert user["id"] is not None
    assert user["nome"] == "Maria Eduarda"

    # Tentativa de cadastrar menor de 18 anos deve falhar
    with pytest.raises(ValueError):
        db.cadastrar_usuario(nome="Adolescente", maior_18_anos=False)


def test_adicionar_multiplos_enderecos_usuario(db):
    """Valida que o usuário pode salvar Casa, Trabalho e UnB com indicação de padrão."""
    user = db.cadastrar_usuario(nome="Cauan Soares", email="cauan@unb.br")

    # 1. Endereço Casa (Padrão)
    db.adicionar_endereco_usuario(
        usuario_id=user["id"],
        rotulo="Casa",
        regiao_ra="Águas Claras",
        ponto_referencia="Perto da Estação Arniqueiras",
        is_padrao=True,
    )

    # 2. Endereço Trabalho
    db.adicionar_endereco_usuario(
        usuario_id=user["id"],
        rotulo="Trabalho",
        regiao_ra="Plano Piloto",
        ponto_referencia="Setor Bancário Sul",
        is_padrao=False,
    )

    # 3. Endereço UnB
    db.adicionar_endereco_usuario(
        usuario_id=user["id"],
        rotulo="Faculdade",
        regiao_ra="Plano Piloto",
        ponto_referencia="ICC Norte - Campus Darcy Ribeiro",
        is_padrao=False,
    )

    enderecos = db.listar_enderecos_usuario(user["id"])
    assert len(enderecos) == 3
    # O padrão fica no topo da lista
    assert enderecos[0]["rotulo"] == "Casa"
    assert enderecos[0]["is_padrao"] == 1


# ==============================================================================
# TESTES DE PARTICIPAÇÃO: ORIGEM AMARRADA À JANELA DE HORÁRIO
# ==============================================================================

def test_participacao_com_origem_por_janela_e_sigilo(db):
    """
    Valida que cada janela de horário tem seu ponto de partida específico:
    - Sexta 19h: saindo do Trabalho (Asa Sul);
    - Sábado 15h: saindo de Casa (Águas Claras).
    Garante também a blindagem de sigilo orçamentário (RNF-01 e RNF-02).
    """
    db.criar_sala(codigo_sala="ROLE_DF", nome_role="Happy Hour de Sexta", criador_nome="Letícia")

    janelas_cauan = [
        {
            "dia": "sex",
            "horario": "19:00",
            "rotulo": "Trabalho",
            "regiao_ra": "Plano Piloto",
            "ponto_referencia": "SBS Quadra 2",
        },
        {
            "dia": "sab",
            "horario": "15:00",
            "rotulo": "Casa",
            "regiao_ra": "Águas Claras",
            "ponto_referencia": "Arniqueiras",
        },
    ]

    part = db.adicionar_participante(
        codigo_sala="ROLE_DF",
        nome="Cauan",
        janelas=janelas_cauan,
        limite_gasto_rs=50.0,  # 100% SIGILOSO
        vibe_hoje="Barzinho descontraído",
        preferencias_transporte="Metrô na ida, Uber na volta",
    )
    assert part["id"] is not None

    # Consulta pública para a sala
    participantes_publicos = db.listar_participantes_sala("ROLE_DF", incluir_sigilo=False)
    assert len(participantes_publicos) == 1
    p = participantes_publicos[0]

    # Validações estritas de sigilo e estrutura
    assert "limite_gasto_rs" not in p, "O limite financeiro JAMAIS deve vazar em chamadas públicas!"
    assert len(p["janelas_disponiveis"]) == 2
    assert p["janelas_disponiveis"][0]["regiao_ra"] == "Plano Piloto"
    assert p["janelas_disponiveis"][1]["regiao_ra"] == "Águas Claras"


def test_obter_menor_orcamento_pela_menor_miseria(db):
    """Valida cálculo do menor teto de gastos do grupo sem vazar a identidade do amigo."""
    db.criar_sala(codigo_sala="JUSTICA01", nome_role="Rolê Justo", criador_nome="Duda")

    db.adicionar_participante("JUSTICA01", "Amigo Rico", limite_gasto_rs=300.0)
    db.adicionar_participante("JUSTICA01", "Amigo Médio", limite_gasto_rs=90.0)
    db.adicionar_participante("JUSTICA01", "Amigo Estudante", limite_gasto_rs=35.0)

    menor_teto = db.obter_menor_orcamento_sala("JUSTICA01")
    assert menor_teto == 35.0


# ==============================================================================
# TESTES DE VOTAÇÃO E PÓS-ROLÊ COM PIX
# ==============================================================================

def test_ciclo_sugestoes_votos_e_pix(db):
    """Valida o ciclo completo: sugestões da IA, votação múltipla e divisão com Pix."""
    db.criar_sala(codigo_sala="COMPLETO01", nome_role="Rolê da Vitória", criador_nome="Samara")
    part_a = db.adicionar_participante("COMPLETO01", "Duda", limite_gasto_rs=60.0)
    part_b = db.adicionar_participante("COMPLETO01", "Carol", limite_gasto_rs=70.0)

    sugestoes = [
        {
            "local_id": "LOC_01",
            "nome_local": "Spelunca DF",
            "regiao_ra": "Plano Piloto",
            "endereco": "CLS 406 Bloco D",
            "dia_horario_sugerido": "Sexta 19h30",
            "faixa_gasto_rs": 45.0,
            "mobility_summary": "12 min de metrô",
            "ranking_justica": 9.5,
            "motivo_escolha": "Perfeito para quem sai do trabalho no Plano.",
        }
    ]

    cards = db.salvar_sugestoes("COMPLETO01", sugestoes)
    assert len(cards) == 1

    # Duda e Carol votam no cartão
    db.registrar_voto("COMPLETO01", part_a["id"], cards[0]["id"])
    db.registrar_voto("COMPLETO01", part_b["id"], cards[0]["id"])

    ranking = db.contabilizar_votos("COMPLETO01")
    assert ranking[0]["total_votos"] == 2

    # Pós-rolê: Carol pagou e informa o Pix para receber
    despesa = db.registrar_despesa_pos_role(
        codigo_sala="COMPLETO01",
        pagador_nome="Carol",
        valor_total_rs=90.0,
        chave_pix="carol.mcznh@pix.com.br",
        tipo_chave_pix="email",
    )
    assert despesa["valor_total_rs"] == 90.0
    assert despesa["chave_pix"] == "carol.mcznh@pix.com.br"
