"""Testes dos Filtros Determinísticos do Agente de Validação (Issue #68).

Cobre:
- Veto 1: dentro_do_orcamento_individual (RF-17: consumo + transporte individual <= teto individual);
- Veto 2: Horário de funcionamento sobreposto à janela comum (RF-12);
- Veto 3: Eventos com data passada ou promoções encerradas;
- Veto 4: Restrições alimentares duras e inegociáveis;
- Relatório estruturado de validação e feedback de busca (RelatorioValidacao e PedidoNovaBusca).
"""
from datetime import datetime
from decimal import Decimal
import pytest

from src.agentes.validacao import (
    dentro_do_orcamento_individual,
    validar_horario_e_evento,
    atende_restricoes_duras,
    validar_candidatos_regras,
    gerar_pedido_nova_busca,
)
from src.salas.janelas import JanelaComum


# -------------------------------------------------------------------------
# Testes do Veto 1: Orçamento Sigiloso com Deslocamento
# -------------------------------------------------------------------------

def test_dentro_do_orcamento_individual_de_todos():
    """Cenário 1: O gasto (consumo + transporte) cabe no teto de todos."""
    custo_consumo = Decimal("35.00")
    tetos = {
        "membro1": Decimal("50.00"),
        "membro2": Decimal("40.00"),
    }
    deslocamentos = {
        "membro1": Decimal("10.00"),
        "membro2": Decimal("5.00"),
    }
    assert dentro_do_orcamento_individual(custo_consumo, tetos, deslocamentos) is True


def test_dentro_do_orcamento_individual_excede_teto():
    """Cenário 2: O frete faz o membro m2 estourar o orçamento."""
    custo_consumo = Decimal("35.00")
    tetos = {
        "membro1": Decimal("50.00"),
        "membro2": Decimal("40.00"),
    }
    deslocamentos = {
        "membro1": Decimal("10.00"),
        "membro2": Decimal("10.00"),
    }
    assert dentro_do_orcamento_individual(custo_consumo, tetos, deslocamentos) is False


def test_dentro_do_orcamento_individual_ignora_membro_sem_teto():
    """Cenário 3: Membro com teto None não restringe o rolê."""
    custo_consumo = Decimal("70.00")
    tetos = {
        "membro1": Decimal("80.00"),
        "membro2": None,
    }
    deslocamentos = {
        "membro1": Decimal("10.00"),
        "membro2": Decimal("10.00"),
    }
    assert dentro_do_orcamento_individual(custo_consumo, tetos, deslocamentos) is True


# -------------------------------------------------------------------------
# Testes dos Vetos 2 e 3: Horário e Eventos Encerrados (RF-12)
# -------------------------------------------------------------------------

def test_validar_horario_aprova_quando_lugar_esta_aberto_na_janela():
    """Cenário 4: Bar que abre de terça a domingo e janela sábado à noite."""
    lugar = {
        "id": "bar_01",
        "nome": "Bar do Lago",
        "horario_funcionamento": "Terca a domingo: 17h as 23h30",
        "ano_mes": "2026-11",
    }
    janela = JanelaComum(
        inicio=datetime(2026, 11, 21, 19, 0),
        fim=datetime(2026, 11, 21, 22, 0),
        presentes=frozenset({"m1", "m2"}),
        total=2,
    )
    agora = datetime(2026, 11, 17, 12, 0)

    valido, motivo, situacao = validar_horario_e_evento(lugar, [janela], agora)
    assert valido is True
    assert motivo is None
    assert situacao == "aberto"


def test_validar_horario_veta_quando_lugar_esta_fechado_no_dia():
    """Cenário 5: Local só abre seg-sex e a janela é no domingo."""
    lugar = {
        "id": "cafe_seg_sex",
        "nome": "Café Executivo",
        "horario_funcionamento": "Segunda a sexta: 8h as 18h. Fechado aos sabados e domingos.",
        "ano_mes": "2026-11",
    }
    janela_domingo = JanelaComum(
        inicio=datetime(2026, 11, 22, 10, 0),
        fim=datetime(2026, 11, 22, 13, 0),
        presentes=frozenset({"m1", "m2"}),
        total=2,
    )
    agora = datetime(2026, 11, 17, 12, 0)

    valido, motivo, situacao = validar_horario_e_evento(lugar, [janela_domingo], agora)
    assert valido is False
    assert motivo == "horario"
    assert situacao == "fechado"


def test_validar_horario_veta_quando_evento_esta_encerrado():
    """Cenário 6: Evento temporário com data expirada."""
    lugar = {
        "id": "festival_passado",
        "nome": "Festival de Inverno 2024",
        "horario_funcionamento": "Valido ate 10 de maio",
        "ano_mes": "2024-05",
    }
    janela = JanelaComum(
        inicio=datetime(2026, 11, 21, 19, 0),
        fim=datetime(2026, 11, 21, 22, 0),
        presentes=frozenset({"m1", "m2"}),
        total=2,
    )
    agora = datetime(2026, 11, 17, 12, 0)

    valido, motivo, situacao = validar_horario_e_evento(lugar, [janela], agora)
    assert valido is False
    assert motivo == "encerrado"
    assert situacao == "encerrado"


# -------------------------------------------------------------------------
# Testes do Veto 4: Restrições Alimentares Duras
# -------------------------------------------------------------------------

def test_restricao_dura_aprova_quando_lugar_tem_opcao():
    """Cenário 7: Restaurante com opções vegetarianas aprovado para vegetariano."""
    lugar = {
        "id": "burger_green",
        "nome": "Burger & Green",
        "tipo_de_role": "Hamburgueria",
        "resumo_sensorial": "Hambúrgueres artesanais com deliciosas opções vegetarianas e veganas no cardápio.",
    }
    valido, motivo = atende_restricoes_duras(lugar, ["alim_vegetariano"])
    assert valido is True
    assert motivo is None


def test_restricao_dura_veta_churrascaria_100_carnes_para_vegetariano():
    """Cenário 8: Churrascaria tradicional sem opção vegetariana vetada para vegetariano."""
    lugar = {
        "id": "parrilla_sul",
        "nome": "Parrilla dos Pampas",
        "tipo_de_role": "Churrascaria / Carnes",
        "resumo_sensorial": "Rodízio tradicional 100% focado em carnes nobres bovinas.",
    }
    valido, motivo = atende_restricoes_duras(lugar, ["alim_vegetariano"])
    assert valido is False
    assert motivo == "restricao"


def test_restricao_dura_aprova_se_ninguem_no_grupo_tiver_restricoes():
    """Cenário 9: Sem restrições duras informadas, churrascaria passa."""
    lugar = {
        "id": "parrilla_sul",
        "nome": "Parrilla dos Pampas",
        "tipo_de_role": "Churrascaria / Carnes",
        "resumo_sensorial": "Rodízio tradicional 100% focado em carnes nobres bovinas.",
    }
    valido, motivo = atende_restricoes_duras(lugar, [])
    assert valido is True
    assert motivo is None


# -------------------------------------------------------------------------
# Testes do Orquestrador de Validação e Feedback Estruturado
# -------------------------------------------------------------------------

def test_validar_candidatos_regras_gera_relatorio_estruturado():
    """Cenário 10: Executa os 4 vetos em lote e gera o RelatorioValidacao."""
    agora = datetime(2026, 11, 17, 12, 0)
    janela = JanelaComum(
        inicio=datetime(2026, 11, 21, 19, 0),
        fim=datetime(2026, 11, 21, 22, 0),
        presentes=frozenset({"m1", "m2"}),
        total=2,
    )

    candidatos = [
        # 1. Deve ser aprovado
        {
            "id": "cand_aprovado",
            "nome": "Bistrô Aconchego",
            "horario_funcionamento": "Terca a domingo: 18h as 23h",
            "tipo_de_role": "Restaurante",
            "resumo_sensorial": "Massas artesanais com opções vegetarianas deliciosas.",
            "custo_medio_rs": 40.0,
        },
        # 2. Vetado por horário (fechado aos sábados)
        {
            "id": "cand_fechado",
            "nome": "Café Centro",
            "horario_funcionamento": "Segunda a sexta: 8h as 17h. Fechado sabado e domingo.",
            "tipo_de_role": "Café",
            "resumo_sensorial": "Café coado e pão de queijo.",
            "custo_medio_rs": 25.0,
        },
        # 3. Vetado por restrição (churrascaria para vegetariano)
        {
            "id": "cand_carnes",
            "nome": "Churrascaria Fogo Forte",
            "horario_funcionamento": "Diariamente: 11h as 23h",
            "tipo_de_role": "Churrascaria",
            "resumo_sensorial": "Rodízio completo 100% carnes nobres.",
            "custo_medio_rs": 45.0,
        },
        # 4. Vetado por orçamento (custo + transporte > teto de m2)
        {
            "id": "cand_caro",
            "nome": "Restaurante Luxo",
            "horario_funcionamento": "Diariamente: 18h as 23h",
            "tipo_de_role": "Gastronomia",
            "resumo_sensorial": "Menu degustação com opções vegetarianas.",
            "custo_medio_rs": 75.0,
        },
    ]

    tetos = {"m1": Decimal("100.00"), "m2": Decimal("60.00")}
    deslocamentos = {
        "cand_aprovado": {"m1": Decimal("10.00"), "m2": Decimal("10.00")},  # 40 + 10 = 50 <= 60 (OK)
        "cand_fechado": {"m1": Decimal("5.00"), "m2": Decimal("5.00")},
        "cand_carnes": {"m1": Decimal("5.00"), "m2": Decimal("5.00")},
        "cand_caro": {"m1": Decimal("10.00"), "m2": Decimal("10.00")},      # 75 + 10 = 85 > 60 (Veto Orçamento)
    }
    restricoes = ["alim_vegetariano"]

    relatorio = validar_candidatos_regras(
        candidatos=candidatos,
        janelas=[janela],
        agora=agora,
        tetos=tetos,
        deslocamentos=deslocamentos,
        restricoes=restricoes,
    )

    assert relatorio.aprovados == ["cand_aprovado"]
    assert len(relatorio.vetos) == 3
    assert relatorio.contagem["horario"] == 1
    assert relatorio.contagem["restricao"] == 1
    assert relatorio.contagem["orcamento"] == 1
    assert relatorio.teto_aplicado is True

    # Como restou apenas 1 aprovado (< 3), gera PedidoNovaBusca com feedback
    pedido = gerar_pedido_nova_busca(relatorio, total_vistos=len(candidatos), minimo_esperado=3)
    assert pedido is not None
    assert pedido.faltam == 2
    assert pedido.ja_vistos == 4
    assert pedido.vetos["orcamento"] == 1
    assert pedido.vetos["horario"] == 1
    assert pedido.vetos["restricao"] == 1


# -------------------------------------------------------------------------
# Teste com a Base Real de 93 Lugares (RF-12 e Contexto Oficial do App)
# -------------------------------------------------------------------------

def test_validacao_com_base_real_de_93_lugares_2fa():
    """Cenário 11: Valida diretamente contra o arquivo oficial data/banco_aprovado_2fa.json."""
    import json
    from pathlib import Path

    caminho_base = Path("data/banco_aprovado_2fa.json")
    assert caminho_base.exists(), "Base oficial 2FA de 93 lugares não encontrada"

    with open(caminho_base, encoding="utf-8") as f:
        lugares_reais = json.load(f)

    assert len(lugares_reais) == 93

    # Janela num sábado à noite (21/11/2026, 19h às 23h)
    janela_sabado = JanelaComum(
        inicio=datetime(2026, 11, 21, 19, 0),
        fim=datetime(2026, 11, 21, 23, 0),
        presentes=frozenset({"m1", "m2", "m3", "m4"}),
        total=4,
    )
    agora = datetime(2026, 11, 19, 12, 0)

    # Cenário de orçamento realista para o grupo de 4 amigos
    tetos = {
        "m1": Decimal("80.00"),
        "m2": Decimal("60.00"),
        "m3": Decimal("120.00"),
        "m4": None,  # sem restrição
    }

    # Deslocamentos padrão simbólicos
    deslocamentos = {
        l["id"]: {"m1": Decimal("8.00"), "m2": Decimal("10.00"), "m3": Decimal("12.00"), "m4": Decimal("5.00")}
        for l in lugares_reais
    }

    relatorio = validar_candidatos_regras(
        candidatos=lugares_reais,
        janelas=[janela_sabado],
        agora=agora,
        tetos=tetos,
        deslocamentos=deslocamentos,
        restricoes=[],
    )

    # Na base real, devem ocorrer vetos de horário e de encerrados
    assert relatorio.contagem["horario"] > 0
    assert relatorio.contagem["encerrado"] > 0
    assert len(relatorio.aprovados) > 0
    assert relatorio.teto_aplicado is True

