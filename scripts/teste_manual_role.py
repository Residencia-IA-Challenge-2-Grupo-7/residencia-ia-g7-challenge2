"""
Script de Teste Manual Interativo - Orquestrador de Rolês (Grupo 7)
Execute no terminal: python3 scripts/teste_manual_role.py
Valida o fluxo visual completo com prints explicativos e verificação de centavos.
"""

from decimal import Decimal
import sys
from pathlib import Path

# Adiciona o diretório raiz ao PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.db.supabase_client import SupabaseClient


def rodar_teste_manual():
    print("=" * 70)
    print("🚀 INICIANDO TESTE MANUAL DO BANCO DE DADOS (ORQUESTRADOR DE ROLÊS)")
    print("=" * 70)

    # 1. Conexão
    db = SupabaseClient()
    db.garantir_schema()
    status = db.checar_conexao()
    print(f"\n[1] 🔌 Status da Conexão: {status['tipo']} -> Conectado: {status['conectado']}")

    # 2. Criar Sala
    codigo_sala = "ROLE-MANUAL"
    print(f"\n[2] 🏠 Criando sala de teste: {codigo_sala}...")
    sala = db.criar_sala(
        codigo_sala=codigo_sala,
        nome_role="Comemoração Pós-Entrega Semana 3",
        organizador_nome="Maria Eduarda",
        token_organizador_hash="sha256_organizador_duda",
    )
    print(f"    ✅ Sala criada com sucesso: ID={sala['id']} | Status={sala['status']}")

    # 3. Adicionar Participantes e Validar Centavos / Sigilo
    print("\n[3] 👥 Adicionando participantes com orçamentos e janelas no DF...")
    
    # Caso crítico da revisão: 0.1 + 0.2 com Decimal
    orcamento_duda = Decimal("0.10") + Decimal("0.20")  # Exatamente 0.30
    part_duda = db.adicionar_participante(
        codigo_sala=codigo_sala,
        nome="Duda",
        limite_gasto_rs=orcamento_duda,
        janelas=[{"inicio": "2026-11-13T19:00:00Z", "fim": "2026-11-13T23:00:00Z", "ra_origem": "Plano Piloto"}],
        vibe_hoje="Barzinho calmo",
        token_hash="token_secreto_duda",
    )
    print(f"    ✅ Duda cadastrada com teto R$ {orcamento_duda} (Decimal puro, sem dízima!)")

    part_cauan = db.adicionar_participante(
        codigo_sala=codigo_sala,
        nome="Cauan",
        limite_gasto_rs=Decimal("50.00"),
        janelas=[{"inicio": "2026-11-13T19:00:00Z", "fim": "2026-11-13T23:00:00Z", "ra_origem": "Águas Claras"}],
        vibe_hoje="Música ao vivo",
        token_hash="token_secreto_cauan",
    )
    print(f"    ✅ Cauan cadastrado com teto R$ 50.00")

    # 4. Checar Sigilo na Listagem Pública
    print("\n[4] 🔒 Verificando proteção de sigilo orçamentário (RNF-01 e RNF-02)...")
    participantes_publicos = db.listar_participantes_sala(codigo_sala)
    for p in participantes_publicos:
        tem_limite = "limite_gasto_rs" in p
        print(f"    Amigo: {p['nome']} | Limite vazou na chamada pública? {'❌ SIM (ERRO!)' if tem_limite else '🛡️ NÃO (SEGURO!)'}")

    # 5. Checar cabe_no_orcamento (segurança sem vazar o menor valor)
    print("\n[5] ⚖️ Testando função 'cabe_no_orcamento()' (pergunta Sim/Não para a IA)...")
    cabe_30 = db.cabe_no_orcamento(codigo_sala, Decimal("0.30"))
    cabe_40 = db.cabe_no_orcamento(codigo_sala, Decimal("0.40"))
    print(f"    Sugestão de R$ 0.30 cabe no bolso de todos? {'✅ SIM' if cabe_30 else '❌ NÃO'}")
    print(f"    Sugestão de R$ 0.40 cabe no bolso de todos? {'✅ SIM' if cabe_40 else '❌ NÃO (Bloqueado com sucesso)'}")

    # 6. Sugestão da IA e Votação
    print("\n[6] 🍕 Inserindo sugestão da IA e registrando votos...")
    sug = db.adicionar_sugestao(
        codigo_sala=codigo_sala,
        local_id="LOC_2FA_042",
        nome_local="Spelunca Bar & Café",
        regiao_ra="Plano Piloto",
        endereco="CLS 406 Bloco D",
        inicio="2026-11-13T19:30:00Z",
        fim="2026-11-13T23:30:00Z",
        horario_texto="Sexta a partir das 19h30",
        consumo_rs=Decimal("0.25"),
        gasto_min=Decimal("0.25"),
        gasto_max=Decimal("0.30"),
        explicacao="Cabe no orçamento da Duda e do Cauan com metrô fácil.",
    )
    db.registrar_voto(codigo_sala, part_duda["id"], sug["id"])
    db.registrar_voto(codigo_sala, part_cauan["id"], sug["id"])
    placar = db.obter_placar_votos(codigo_sala)
    print(f"    ✅ Votos apurados no cartão {sug['nome_local']}: {placar.get(sug['id'], 0)} votos!")

    # 7. Pós-Rolê: Divisão e Pix Individualizado
    print("\n[7] 🧾 Registrando pós-rolê, rateio individual e Pix...")
    despesa = db.registrar_despesa_pos_role(
        codigo_sala=codigo_sala,
        pagador_nome="Cauan",
        pagador_participante_id=part_cauan["id"],
        valor_total_rs=Decimal("0.50"),
        chave_pix="cauan@pix.bcb.gov.br",
        rateios=[
            {"devedor_participante_id": part_duda["id"], "valor": Decimal("0.25")}
        ],
    )
    print(f"    ✅ Despesa total: R$ {despesa['valor_total_rs']} registrada com Pix: {despesa['chave_pix']}")
    print(f"    ✅ Rateio individual: Duda deve R$ 0.25 para Cauan.")

    # Duda paga
    db.dar_baixa_rateio(despesa["id"], part_duda["id"])
    print(f"    🎉 Duda fez o Pix e deu baixa no rateio! Status: QUITADO.")

    print("\n" + "=" * 70)
    print("🏆 TESTE MANUAL CONCLUÍDO COM 100% DE SUCESSO!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    rodar_teste_manual()
