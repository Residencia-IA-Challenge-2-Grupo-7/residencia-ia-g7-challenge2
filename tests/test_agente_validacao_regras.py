"""Testes dos Filtros Determinísticos do Agente de Validação (Issue #68).

Cobre:
- Veto 1: dentro_do_orcamento_individual (RF-17: consumo + transporte individual <= teto individual);
- Veto 2: Horário de funcionamento sobreposto à janela comum (RF-12);
- Veto 3: Eventos com data passada ou promoções encerradas;
- Veto 4: Restrições alimentares duras e inegociáveis (sem evidência no texto/vídeo);
- Veto de Deslocamento: Menor Miséria (> 75 min, TEMPO_ACEITAVEL_MIN, ADR 0013);
- Suporte a saídas reais da Logística com 'None' (cofre.analises);
- Relatório estruturado de validação e feedback de busca (RelatorioValidacao e PedidoNovaBusca);
- Integração com cenários reais da issue #66 (cenário padrão e cenário de controle com 5 viáveis).
"""
import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path
import pytest

from src.agentes.cenarios import carregar_cenario
from src.agentes.contratos import Cofre, Membro
from src.agentes.validacao import (
    dentro_do_orcamento_individual,
    validar_horario_e_evento,
    atende_restricoes_duras,
    validar_deslocamento_membros,
    validar_candidatos_regras,
    gerar_pedido_nova_busca,
)
from src.interpretador.campos import interpretar_campos
from src.logistica.transporte_df import estimar_deslocamento
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


def test_restricao_dura_veta_churrascaria_sem_opcao_para_vegetariano():
    """Cenário 8: Lugar sem evidência de opção vegetariana vetado para vegetariano."""
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
    """Cenário 9: Sem restrições duras informadas, o local passa."""
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
# Testes do Veto de Deslocamento (ADR 0013 / Menor Miséria)
# -------------------------------------------------------------------------

def test_validar_deslocamento_aprova_dentro_do_limite():
    """Cenário 10: Trajetos até 75 minutos são aprovados."""
    analises = {
        "m1": {"minutos": 45, "custo_ida_volta": Decimal("11.00")},
        "m2": {"minutos": 70, "custo_ida_volta": Decimal("11.00")},
    }
    valido, motivo = validar_deslocamento_membros(analises)
    assert valido is True
    assert motivo is None


def test_validar_deslocamento_veta_quando_excede_75_min():
    """Cenário 11: Trajeto superior a 75 minutos é vetado por deslocamento."""
    analises = {
        "m1": {"minutos": 45, "custo_ida_volta": Decimal("11.00")},
        "m2": {"minutos": 120, "custo_ida_volta": Decimal("11.00")},  # 120 > 75
    }
    valido, motivo = validar_deslocamento_membros(analises)
    assert valido is False
    assert motivo == "deslocamento"


def test_validar_candidatos_regras_trata_none_na_saida_da_logistica():
    """Cenário 12: Lugar sem trajeto estimável (None em cofre.analises) não causa AttributeError."""
    candidatos = [{"id": "lugar_sem_coords", "nome": "Lugar Misterioso", "custo_medio_rs": 30.0}]
    janela = JanelaComum(
        inicio=datetime(2026, 11, 21, 19, 0),
        fim=datetime(2026, 11, 21, 22, 0),
        presentes=frozenset({"m1", "m2"}),
        total=2,
    )
    # A Logística grava None quando o trajeto não pode ser estimado
    analises_com_none = {
        "lugar_sem_coords": {"m1": None, "m2": {"minutos": 30, "custo_ida_volta": Decimal("10.00")}}
    }
    tetos = {"m1": Decimal("50.00"), "m2": Decimal("50.00")}

    # Não deve lançar AttributeError: 'NoneType' object has no attribute 'get'
    relatorio = validar_candidatos_regras(
        candidatos=candidatos,
        janelas=[janela],
        tetos=tetos,
        analises_completas=analises_com_none,
    )
    assert isinstance(relatorio.contagem, dict)


# -------------------------------------------------------------------------
# Testes com os Cenários Reais da Issue #66 (Gabarito Oficial)
# -------------------------------------------------------------------------

def test_cenario_controle_viavel_aprova_exatamente_os_5_esperados():
    """Cenário 13: No cenario_controle_viavel da issue #66, passam exatamente os 5 lugares viáveis."""
    cenario = carregar_cenario("cenario_controle_viavel")
    caminho_base = Path("data/banco_aprovado_2fa.json")
    with open(caminho_base, encoding="utf-8") as f:
        lugares_reais = {l["id"]: l for l in json.load(f)}

    inicio = datetime.fromisoformat(cenario["resultados_esperados"]["janela_comum"]["inicio"])
    fim = datetime.fromisoformat(cenario["resultados_esperados"]["janela_comum"]["fim"])
    janela = JanelaComum(inicio=inicio, fim=fim, presentes=frozenset({"m1", "m2", "m3", "m4"}), total=4)
    agora = datetime.fromisoformat(cenario["agora_referencia"])

    tetos = {amigo["marcador"]: Decimal(str(amigo["interpretacao_esperada"]["teto_rs"])) for amigo in cenario["amigos"]}
    restricoes = list({r for a in cenario["amigos"] for r in a["interpretacao_esperada"]["restricoes"]})

    # Simula as análises de trajeto da Logística
    analises = {}
    for lid, lugar in lugares_reais.items():
        analises[lid] = {}
        for amigo in cenario["amigos"]:
            m = amigo["marcador"]
            esperado = amigo["interpretacao_esperada"]
            if lugar.get("lat") is not None and lugar.get("lng") is not None:
                trajetos = [
                    estimar_deslocamento(esperado["ra"], lugar["lat"], lugar["lng"], modo, inicio)
                    for modo in esperado["transporte"]
                ]
                trajetos = [t for t in trajetos if t]
                if trajetos:
                    viaveis = [t for t in trajetos if t["minutos"] <= 75]
                    melhor = min(viaveis, key=lambda t: (t["custo_ida_volta"], t["minutos"])) if viaveis else min(trajetos, key=lambda t: (t["minutos"], t["custo_ida_volta"]))
                    analises[lid][m] = melhor
                else:
                    analises[lid][m] = None
            else:
                analises[lid][m] = None

    relatorio = validar_candidatos_regras(
        candidatos=list(lugares_reais.values()),
        janelas=[janela],
        agora=agora,
        tetos=tetos,
        lugares_base=lugares_reais,
        restricoes=restricoes,
        analises_completas=analises,
    )

    esperados_viaveis = sorted(l["id"] for l in cenario["resultados_esperados"]["lugares_viaveis_esperados"])
    assert sorted(relatorio.aprovados) == esperados_viaveis
    assert len(relatorio.aprovados) == 5
    assert relatorio.contagem["deslocamento"] > 0


def test_cenario_padrao_sem_lugares_viaveis():
    """Cenário 14: No cenario_padrao_4_amigos da issue #66, nenhum lugar passa e há múltiplos vetos."""
    cenario = carregar_cenario("cenario_padrao_4_amigos")
    caminho_base = Path("data/banco_aprovado_2fa.json")
    with open(caminho_base, encoding="utf-8") as f:
        lugares_reais = {l["id"]: l for l in json.load(f)}

    inicio = datetime.fromisoformat(cenario["resultados_esperados"]["janela_comum"]["inicio"])
    fim = datetime.fromisoformat(cenario["resultados_esperados"]["janela_comum"]["fim"])
    janela = JanelaComum(inicio=inicio, fim=fim, presentes=frozenset({"m1", "m2", "m3", "m4"}), total=4)
    agora = datetime.fromisoformat(cenario["agora_referencia"])

    tetos = {amigo["marcador"]: Decimal(str(amigo["interpretacao_esperada"]["teto_rs"])) for amigo in cenario["amigos"]}
    restricoes = list({r for a in cenario["amigos"] for r in a["interpretacao_esperada"]["restricoes"]})

    analises = {}
    for lid, lugar in lugares_reais.items():
        analises[lid] = {}
        for amigo in cenario["amigos"]:
            m = amigo["marcador"]
            esperado = amigo["interpretacao_esperada"]
            if lugar.get("lat") is not None and lugar.get("lng") is not None:
                trajetos = [
                    estimar_deslocamento(esperado["ra"], lugar["lat"], lugar["lng"], modo, inicio)
                    for modo in esperado["transporte"]
                ]
                trajetos = [t for t in trajetos if t]
                if trajetos:
                    viaveis = [t for t in trajetos if t["minutos"] <= 75]
                    melhor = min(viaveis, key=lambda t: (t["custo_ida_volta"], t["minutos"])) if viaveis else min(trajetos, key=lambda t: (t["minutos"], t["custo_ida_volta"]))
                    analises[lid][m] = melhor
                else:
                    analises[lid][m] = None
            else:
                analises[lid][m] = None

    relatorio = validar_candidatos_regras(
        candidatos=list(lugares_reais.values()),
        janelas=[janela],
        agora=agora,
        tetos=tetos,
        lugares_base=lugares_reais,
        restricoes=restricoes,
        analises_completas=analises,
    )

    # No cenário padrão, nenhum lugar é viável
    assert len(relatorio.aprovados) == 0
    assert relatorio.contagem["restricao"] > 0
    assert relatorio.contagem["orcamento"] > 0



# ------------------------------------------------------------------ ajustes da issue #71

def test_lugar_sem_nenhum_trajeto_estimado_e_vetado_por_deslocamento():
    """Sem coordenadas, a Logística grava None para todos: não dá para saber se alguém chega, então não aprova."""
    assert validar_deslocamento_membros({"m1": None, "m3": None}) == (False, "deslocamento")
    assert validar_deslocamento_membros({"m1": None, "m2": {"minutos": 30}}) == (True, None)


def test_orcamento_so_conta_quem_esta_na_janela_do_lugar():
    """Na janela parcial (m2 fora), o teto do m2 não veta o lugar; o dos presentes continua valendo."""
    lugar = {"id": "x", "nome": "Lugar", "custo_medio_rs": 50, "horario_funcionamento": "Todos os dias: 10h às 23h",
             "tipo_de_role": "Restaurante / Gastronomia"}
    analises = {"x": {"m1": {"minutos": 20, "custo_ida_volta": Decimal("0")},
                      "m3": {"minutos": 20, "custo_ida_volta": Decimal("0")}}}
    janela = JanelaComum(datetime(2026, 11, 21, 18), datetime(2026, 11, 21, 22), frozenset({"m1", "m3"}), 3)
    comum = dict(candidatos=[lugar], janelas=[janela], agora=datetime(2026, 11, 17, 12), lugares_base={"x": lugar},
                 analises_completas=analises, restricoes=[])
    assert validar_candidatos_regras(tetos={"m1": Decimal("80"), "m2": Decimal("30"), "m3": None}, **comum).aprovados == ["x"]
    assert validar_candidatos_regras(tetos={"m1": Decimal("40"), "m2": Decimal("30"), "m3": None}, **comum).aprovados == []
