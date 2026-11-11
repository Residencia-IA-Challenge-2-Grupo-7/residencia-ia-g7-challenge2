"""
Teste Completo de Ponta a Ponta: 2 Amigos Combinando um Rolê
Projeto: Orquestrador de Rolês - Grupo 7 (Residência em IA | UnB & Eldorado)
Responsável: Maria Eduarda (DevOps & Backend)

Cenário Real do DF:
1. Duda cria a sala de rolê no Plano Piloto (ROLE-AMIGOS).
2. Duda sai do Plano Piloto (Trabalho na Sexta 19h) com teto seguro de R$ 60,00.
3. Cauan sai de Águas Claras (Casa na Sexta 19h) com teto seguro de R$ 45,00.
4. Validação de Sigilo: o limite financeiro individual NÃO aparece na listagem pública da sala.
5. Verificação de Orçamento Conjunto:
   - Rolê de R$ 40,00 cabe no bolso dos dois? SIM.
   - Rolê de R$ 55,00 cabe no bolso dos dois? NÃO (excede o teto do Cauan, protegendo o amigo).
6. IA gera as opções oficiais dos 93 lugares aprovados com centavos exatos (Decimal).
7. Votação Democrática: Duda e Cauan votam e elegem o lugar favorito.
8. Pós-Rolê (Tela 4):
   - A conta deu R$ 80,00 e a Duda pagou no cartão dela.
   - É gerado o rateio individual: Cauan deve R$ 40,00 com a Chave Pix da Duda.
   - Cauan faz o Pix e dá baixa no rateio individual. Status: Quitado!
"""

from datetime import datetime, timezone
from decimal import Decimal
import pytest

from src.db.supabase_client import SupabaseClient


@pytest.fixture
def cliente_db(tmp_path):
    """Cria banco isolado para o teste de fluxo."""
    caminho = tmp_path / "teste_amigos.db"
    c = SupabaseClient(use_memory_fallback=False, db_path=caminho)
    c.garantir_schema()
    yield c
    c.fechar()


def test_fluxo_completo_dois_amigos_do_inicio_ao_pix(cliente_db):
    # -------------------------------------------------------------------------
    # PASSO 1: Duda cria a Sala oficial no DF
    # -------------------------------------------------------------------------
    codigo_sala = "ROLE-AMIGOS"
    sala = cliente_db.criar_sala(
        codigo_sala=codigo_sala,
        nome_role="Comemoração Residência IA",
        organizador_nome="Duda",
        token_organizador_hash="token_hash_organizador_duda",
    )
    assert sala["id"] is not None
    assert sala["codigo_sala"] == "ROLE-AMIGOS"
    assert sala["status"] == "coletando"

    # -------------------------------------------------------------------------
    # PASSO 2: Duda entra na sala e preenche seus 4 campos em segredo
    # -------------------------------------------------------------------------
    part_duda = cliente_db.adicionar_participante(
        codigo_sala=codigo_sala,
        nome="Duda",
        limite_gasto_rs=Decimal("60.00"),  # Teto da Duda: R$ 60
        janelas=[
            {
                "inicio": "2026-11-13T19:00:00Z",
                "fim": "2026-11-13T23:30:00Z",
                "ra_origem": "Plano Piloto",
            }
        ],
        vibe_hoje="Barzinho calmo para conversar",
        transporte_hoje="metro",
        token_hash="sha256_token_duda",
    )
    assert part_duda["id"] is not None

    # -------------------------------------------------------------------------
    # PASSO 3: Cauan entra na sala e preenche seus 4 campos em segredo
    # -------------------------------------------------------------------------
    part_cauan = cliente_db.adicionar_participante(
        codigo_sala=codigo_sala,
        nome="Cauan",
        limite_gasto_rs=Decimal("45.00"),  # Teto do Cauan: R$ 45 (o mais restritivo)
        janelas=[
            {
                "inicio": "2026-11-13T19:00:00Z",
                "fim": "2026-11-13T23:30:00Z",
                "ra_origem": "Águas Claras",
            }
        ],
        vibe_hoje="Música ao vivo ou petiscos",
        transporte_hoje="metro",
        token_hash="sha256_token_cauan",
    )
    assert part_cauan["id"] is not None

    # -------------------------------------------------------------------------
    # PASSO 4: Validação de Sigilo Orçamentário (RNF-01 e RNF-02)
    # -------------------------------------------------------------------------
    participantes_na_sala = cliente_db.listar_participantes_sala(codigo_sala)
    assert len(participantes_na_sala) == 2

    for p in participantes_na_sala:
        # O valor financeiro JAMAIS deve estar na listagem pública da sala
        assert "limite_gasto_rs" not in p, "Vazamento de privacidade orçamentária detectado!"
        assert len(p["janelas_disponiveis"]) == 1

    # -------------------------------------------------------------------------
    # PASSO 5: A IA consulta a função cabe_no_orcamento()
    # -------------------------------------------------------------------------
    # Como o Cauan pode até R$ 45,00 e a Duda até R$ 60,00:
    assert cliente_db.cabe_no_orcamento(codigo_sala, Decimal("40.00")) is True
    assert cliente_db.cabe_no_orcamento(codigo_sala, Decimal("45.00")) is True
    assert cliente_db.cabe_no_orcamento(codigo_sala, Decimal("50.00")) is False  # Cauan não pode!

    # -------------------------------------------------------------------------
    # PASSO 6: Geração dos Cartões de Sugestão (Catálogo oficial 2FA)
    # -------------------------------------------------------------------------
    agora = datetime.now(timezone.utc)
    sugestao_lugar = cliente_db.adicionar_sugestao(
        codigo_sala=codigo_sala,
        local_id="LOC_2FA_093",
        nome_local="Spelunca Bar & Restaurante",
        regiao_ra="Plano Piloto",
        endereco="CLS 406 Bloco D",
        inicio=agora,
        fim=agora,
        horario_texto="Sexta das 19h às 23h30",
        consumo_rs=Decimal("38.00"),     # Dentro do teto do Cauan e da Duda
        gasto_min=Decimal("43.50"),      # Com metrô
        gasto_max=Decimal("45.00"),
        explicacao="Local próximo ao metrô na Asa Sul, ideal para quem sai de Águas Claras e do Plano.",
        nota_justica=9.6,
    )
    assert sugestao_lugar["id"] is not None
    assert sugestao_lugar["consumo_rs"] == Decimal("38.00")

    # -------------------------------------------------------------------------
    # PASSO 7: Votação Democrática (Duda e Cauan votam no Spelunca)
    # -------------------------------------------------------------------------
    voto_duda = cliente_db.registrar_voto(codigo_sala, part_duda["id"], sugestao_lugar["id"])
    voto_cauan = cliente_db.registrar_voto(codigo_sala, part_cauan["id"], sugestao_lugar["id"])
    assert voto_duda is True
    assert voto_cauan is True

    placar = cliente_db.obter_placar_votos(codigo_sala)
    assert placar[sugestao_lugar["id"]] == 2

    # -------------------------------------------------------------------------
    # PASSO 8: Pós-Rolê (Tela 4) - Duda pagou a conta e divide via Pix BACEN
    # -------------------------------------------------------------------------
    # Conta total: R$ 80,00 (R$ 40,00 de cada)
    despesa = cliente_db.registrar_despesa_pos_role(
        codigo_sala=codigo_sala,
        pagador_nome="Duda",
        pagador_participante_id=part_duda["id"],
        valor_total_rs=Decimal("80.00"),
        chave_pix="duda.red35@gmail.com",
        tipo_chave_pix="email",
        rateios=[
            {
                "devedor_participante_id": part_cauan["id"],
                "valor": Decimal("40.00"),
            }
        ],
    )
    assert despesa["valor_total_rs"] == Decimal("80.00")
    assert despesa["chave_pix"] == "duda.red35@gmail.com"
    assert despesa["rateios_count"] == 1

    # Cauan faz o Pix para a Duda e o sistema dá baixa no rateio dele
    baixou = cliente_db.dar_baixa_rateio(
        despesa_id=despesa["id"],
        devedor_participante_id=part_cauan["id"],
    )
    assert baixou is True, "A baixa do rateio individual no Pix deve retornar True."
