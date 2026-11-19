"""Testes unitários e de integração para o Agente 4 (Comunicação e Formatação de Cartões).

Issue #69: [Semana 4] [BACKEND] Agente 4 (Comunicação): Prompt do Anfitrião e Formatação de Cartões em JSON.
Atende rigorosamente aos 10 apontamentos da revisão do PR #81 e aos requisitos:
- RF-06: Cartões de recomendação explicados e estruturados;
- RNF-02: Sigilo absoluto de PII, orçamentos individuais e origens;
- RNF-03: Ancoragem na base curada 2FA de Brasília (93 lugares);
- RNF-04: Cálculos matemáticos, financeiros e logísticos fora do LLM;
- RNF-16: Responsabilidade e segurança em locais com bebidas alcoólicas.
"""
from __future__ import annotations

import json
from decimal import Decimal
from typing import Any
import pytest
from pydantic import ValidationError

from src.agentes.comunicacao import (
    CartaoSugestaoValidado,
    LIMITE_MAXIMO_CARTOES,
    executar_agente_comunicacao,
    no_comunicacao,
    texto_conforme_regras,
    _calcular_sinais,
)
from src.agentes.contratos import CartaoTexto, SaidaComunicacao
from src.agentes.llm import ClienteLLM, ErroLLM, prompt, versao_prompt
from src.salas.modelos import Sugestao


class MockLLMSucesso(ClienteLLM):
    """Mock de LLM que retorna JSON estrito em conformidade com as regras."""
    def __init__(self, cartoes_resposta: list[dict] | None = None):
        super().__init__(chave="sk-mock-valido")
        self._cartoes = cartoes_resposta or [
            {
                "id": "A",
                "titulo": "Café acolhedor no Guará",
                "resumo_acesso": "Fica no meio do caminho para o grupo sem ninguém atravessar a cidade.",
                "por_que_combina": "Ambiente tranquilo e perfeito para conversar com todo mundo junto.",
            }
        ]

    def json(self, agente: str, prompt_sistema: str, prompt_usuario: str, esquema: dict, **kwargs) -> dict:
        return {"cartoes": self._cartoes}


class MockLLMComViolacao(ClienteLLM):
    """Mock de LLM que viola regras (inclui números, valores monetários ou origens)."""
    def __init__(self):
        super().__init__(chave="sk-mock-valido")

    def json(self, agente: str, prompt_sistema: str, prompt_usuario: str, esquema: dict, **kwargs) -> dict:
        return {
            "cartoes": [
                {
                    "id": "A",
                    "titulo": "Bar 10 estrelas",
                    "resumo_acesso": "Fica a apenas 15 min de metrô para quem sai de Ceilândia.",
                    "por_que_combina": "Custa apenas R$ 50 reais por pessoa.",
                }
            ]
        }


class MockLLMFalha(ClienteLLM):
    """Mock de LLM que dispara ErroLLM."""
    def __init__(self):
        super().__init__(chave="sk-mock-valido")

    def json(self, agente: str, prompt_sistema: str, prompt_usuario: str, esquema: dict, **kwargs) -> dict:
        raise ErroLLM("Falha na API da LLM simulada")


# -----------------------------------------------------------------------------
# Testes do Item 1: no_comunicacao consome exclusivamente candidatos_validados
# -----------------------------------------------------------------------------
def test_no_comunicacao_ignora_candidatos_avaliados_quando_validados_vazio():
    """Garante que locais vetados ou pendentes em candidatos_avaliados jamais vazem (RNF-02, RNF-04)."""
    estado_com_vetados = {
        "candidatos_avaliados": [
            {"id": "lugar_vetado_1", "nome": "Local Fora do Orçamento", "nota_justica": 20.0}
        ],
        "candidatos_validados": [],  # Todos foram vetados pelo Agente 3
    }

    resultado = no_comunicacao(estado_com_vetados)
    assert resultado["cartoes"] == []
    assert resultado["cartoes_por_llm"] is False
    assert resultado["resultado_final_cartoes"] == []


def test_no_comunicacao_processa_apenas_candidatos_validados():
    """Garante que apenas candidatos_validados chegam aos cartões finais."""
    candidato_valido = {
        "id": "cand_1",
        "nome": "Café Bistrô",
        "regiao_administrativa": "Guará",
        "tipo": "Café / Gastronomia",
        "nota_justica": 85.0,
        "consumo_rs": "40.00",
        "faixa_gasto_rs": {"min": "40.00", "max": "55.00"},
        "tempo_medio_chegada_min": 25,
        "tempo_maximo_chegada_min": 35,
        "quantos_podem": "4 de 4",
        "horario_situacao": "aberto",
    }
    estado = {
        "candidatos_avaliados": [
            {"id": "vetado_1", "nome": "Lugar Proibido"},
            candidato_valido,
        ],
        "candidatos_validados": [candidato_valido],
    }

    mock_llm = MockLLMSucesso()
    res = no_comunicacao(estado, llm=mock_llm)

    assert len(res["cartoes"]) == 1
    assert res["cartoes"][0]["id"] == "A"
    assert res["cartoes_por_llm"] is True
    assert len(res["resultado_final_cartoes"]) == 1
    assert res["resultado_final_cartoes"][0]["nome"] == "Café Bistrô"


# -----------------------------------------------------------------------------
# Testes do Item 2: Validação em código do texto gerado (texto_conforme_regras)
# -----------------------------------------------------------------------------
@pytest.mark.parametrize(
    "texto_invalido",
    [
        "Fica a apenas 15 min de distância.",  # números e 'min'
        "Custa cerca de R$ 50 por pessoa.",    # 'R$' e número
        "Gasto de vinte reais.",               # 'reais'
        "Apenas 3 km da estação.",             # número e 'km'
        "Perfeito pra quem sai de Ceilândia.", # origem individual
        "Ótimo para quem vem de Taguatinga.",  # origem individual
        "Saindo de Águas Claras é rápido.",    # origem individual
        "",                                    # vazio
        "   ",                                 # espaços
    ]
)
def test_texto_conforme_regras_rejeita_violacoes(texto_invalido: str):
    assert texto_conforme_regras(texto_invalido) is False


@pytest.mark.parametrize(
    "texto_valido",
    [
        "Fica no meio do caminho para o grupo, sem ninguém atravessar o DF.",
        "Ambiente descontraído e aconchegante, ideal para bater papo.",
        "Vale combinar a volta com carona ou transporte sem dirigir.",
        "Um cantinho acolhedor com música ambiente suave.",
    ]
)
def test_texto_conforme_regras_aceita_textos_limpos(texto_valido: str):
    assert texto_conforme_regras(texto_valido) is True


def test_executar_agente_comunicacao_ativa_fallback_se_llm_violar_regras():
    """Se o LLM gerar números ou origens, o agente deve descartar e usar o fallback determinístico."""
    candidato = {
        "id": "cand_1",
        "nome": "Bistrô do Lago",
        "regiao_administrativa": "Lago Sul",
        "tipo": "Gastronomia",
        "nota_justica": 90.0,
        "consumo_rs": "60.00",
        "tempo_maximo_chegada_min": 30,
        "diferenca_min": 10,
    }

    mock_violador = MockLLMComViolacao()
    cartoes, usou_llm = executar_agente_comunicacao([candidato], llm=mock_violador, devolver_status=True)

    assert len(cartoes) == 1
    assert usou_llm is False  # Como violou, textos do LLM foram descartados
    # Fallback não contém números nem origens
    assert texto_conforme_regras(cartoes[0]["resumo_acesso"])
    assert texto_conforme_regras(cartoes[0]["por_que_combina"])
    assert "Fica no meio do caminho" in cartoes[0]["resumo_acesso"]


# -----------------------------------------------------------------------------
# Testes do Item 3: Sinais logísticos e condicionamento qualitativo
# -----------------------------------------------------------------------------
def test_calcular_sinais_logistica():
    """Valida o cálculo determinístico de sinais para o LLM e fallbacks."""
    # Candidato equilibrado (trajeto curto <= 45 min, diferença <= 30 min, todos podem)
    cand_eq = {
        "tempo_maximo_chegada_min": 35,
        "diferenca_min": 15,
        "nota_justica": 80.0,
        "quantos_podem": "4 de 4 pessoas",
    }
    sinais_eq = _calcular_sinais(cand_eq)
    assert sinais_eq["chegada_equilibrada"] is True
    assert sinais_eq["todos_podem_na_janela"] is True
    assert sinais_eq["cabe_no_orcamento_do_grupo"] is True

    # Candidato desequilibrado (pior trajeto longo > 45 min)
    cand_deseq = {
        "tempo_maximo_chegada_min": 65,
        "diferenca_min": 45,
        "nota_justica": 40.0,
        "quantos_podem": "3 de 4 pessoas",
    }
    sinais_deseq = _calcular_sinais(cand_deseq)
    assert sinais_deseq["chegada_equilibrada"] is False
    assert sinais_deseq["todos_podem_na_janela"] is False


def test_fallback_texto_respeita_sinal_chegada_equilibrada():
    """Verifica que o texto qualitativo do fallback reflete fielmente o sinal de equilíbrio."""
    cand_perto = {
        "id": "c1",
        "nome": "Local Central",
        "regiao_administrativa": "Plano Piloto",
        "tempo_maximo_chegada_min": 25,
        "diferenca_min": 10,
        "nota_justica": 90.0,
    }
    cand_longe = {
        "id": "c2",
        "nome": "Local Afastado",
        "regiao_administrativa": "Planaltina",
        "tempo_maximo_chegada_min": 70,
        "diferenca_min": 50,
        "nota_justica": 50.0,
    }

    cartoes = executar_agente_comunicacao([cand_perto, cand_longe], llm=None)
    assert "Fica no meio do caminho para o grupo" in cartoes[0]["resumo_acesso"]
    assert "Vale combinar o transporte antes" in cartoes[1]["resumo_acesso"]


# -----------------------------------------------------------------------------
# Testes do Item 4: Tratamento de CandidatoAvaliado sem campos inicio/fim
# -----------------------------------------------------------------------------
def test_candidato_avaliado_sem_datas_mantem_none_sem_inventar_data_atual():
    """Garante que campos de data/hora não sejam preenchidos com datetime.now() arbitrário."""
    cand_sem_datas = {
        "id": "cand_raw",
        "nome": "Café Típico",
        "regiao_administrativa": "Asa Norte",
        "tipo": "Café",
        "nota_justica": 88.0,
        "consumo_rs": "35.00",
        # Sem 'inicio' e sem 'fim'
    }

    cartoes = executar_agente_comunicacao([cand_sem_datas], llm=None)
    assert len(cartoes) == 1
    assert cartoes[0]["inicio"] is None
    assert cartoes[0]["fim"] is None
    assert cartoes[0]["horario"] == "Horário a combinar"
    assert cartoes[0]["faixa_gasto_rs"] == {"min": "35.00", "max": "35.00"}


# -----------------------------------------------------------------------------
# Testes do Item 5: Prompt do Anfitrião e Versionamento
# -----------------------------------------------------------------------------
def test_prompt_anfitriao_carrega_versao_oficial():
    assert versao_prompt("comunicacao") == "2026-11-17.2"
    prompt_txt = prompt("comunicacao")
    assert "Você é o anfitrião" in prompt_txt
    assert "chegada_equilibrada" in prompt_txt
    assert "cabe_no_orcamento_do_grupo" in prompt_txt
    assert "RNF-16" in prompt_txt
    assert "Não escreva números nem algarismos" in prompt_txt
    assert "Nunca mencione de onde alguém sai" in prompt_txt


# -----------------------------------------------------------------------------
# Testes do Item 6: Rastreamento real de cartoes_por_llm
# -----------------------------------------------------------------------------
def test_rastreamento_cartoes_por_llm():
    cand = {"id": "c1", "nome": "Lugar Teste", "regiao_administrativa": "Guará"}

    # Caso 1: LLM respondeu com sucesso
    _, usou_1 = executar_agente_comunicacao([cand], llm=MockLLMSucesso(), devolver_status=True)
    assert usou_1 is True

    # Caso 2: LLM falhou
    _, usou_2 = executar_agente_comunicacao([cand], llm=MockLLMFalha(), devolver_status=True)
    assert usou_2 is False

    # Caso 3: Sem LLM
    _, usou_3 = executar_agente_comunicacao([cand], llm=None, devolver_status=True)
    assert usou_3 is False


# -----------------------------------------------------------------------------
# Testes do Item 7: Limite estrito de no máximo 4 cartões
# -----------------------------------------------------------------------------
def test_limite_estrito_maximo_4_cartoes():
    seis_candidatos = [
        {"id": f"c_{i}", "nome": f"Lugar {i}", "regiao_administrativa": "Taguatinga"}
        for i in range(1, 7)
    ]

    cartoes = executar_agente_comunicacao(seis_candidatos, llm=None)
    assert len(cartoes) == LIMITE_MAXIMO_CARTOES
    assert [c["id"] for c in cartoes] == ["A", "B", "C", "D"]
    assert [c["posicao"] for c in cartoes] == [1, 2, 3, 4]


# -----------------------------------------------------------------------------
# Testes do Item 8: Tratamento estreito de exceção do LLM
# -----------------------------------------------------------------------------
def test_tratamento_excecao_estreito_llm():
    """Garante que ErroLLM ou ValueError caem no fallback sem interromper a execução."""
    cand = {"id": "c1", "nome": "Lugar Fallback", "regiao_administrativa": "Asa Sul"}
    cartoes, usou_llm = executar_agente_comunicacao([cand], llm=MockLLMFalha(), devolver_status=True)

    assert len(cartoes) == 1
    assert usou_llm is False
    assert cartoes[0]["nome"] == "Lugar Fallback"


# -----------------------------------------------------------------------------
# Testes do Item 9: Validação estrita por Pydantic (extra='forbid')
# -----------------------------------------------------------------------------
def test_cartao_sugestao_validado_rejeita_campos_extras():
    """Garante que campos privados de membros ou chaves inventadas sejam banidos (RNF-02)."""
    dados_validos = {
        "id": "A",
        "posicao": 1,
        "lugar_id": "lugar_1",
        "nome": "Bar do Parque",
        "tipo": "Bar",
        "regiao_administrativa": "Águas Claras",
        "endereco": "Rua 10, Águas Claras - DF",
        "inicio": None,
        "fim": None,
        "horario": "Sábado a partir das 18h",
        "horario_situacao": "aberto",
        "quantos_podem": "4 de 4",
        "consumo_estimado_rs": "50.00",
        "faixa_gasto_rs": {"min": "50.00", "max": "70.00"},
        "tempo_medio_chegada_min": 30,
        "tempo_maximo_chegada_min": 40,
        "nota_justica": 82.5,
        "pontuacao": 0.85,
        "explicacao": "Ambiente descontraído.",
        "tiktok_url": None,
        "fonte": "TikTok @exemplo",
        "vibes": ["Animado"],
        "titulo": "Noite animada em Águas Claras",
        "resumo_acesso": "Fica no meio do caminho para todos.",
        "por_que_combina": "Espaço ideal para grupos grandes.",
    }

    # Deve validar com sucesso
    cartao = CartaoSugestaoValidado.model_validate(dados_validos)
    assert cartao.id == "A"
    assert cartao.pontuacao == 0.85

    # Tentar injetar campos proibidos de PII ou orçamentos individuais (RNF-02)
    with pytest.raises(ValidationError):
        CartaoSugestaoValidado.model_validate({**dados_validos, "orcamento_privado": "100.00"})

    with pytest.raises(ValidationError):
        CartaoSugestaoValidado.model_validate({**dados_validos, "origem_membro_1": "Ceilândia"})


# -----------------------------------------------------------------------------
# Testes do RNF-16: Regulação de bebidas alcoólicas e transporte responsável
# -----------------------------------------------------------------------------
def test_alerta_transporte_seguro_para_bares():
    """Locais do tipo Bar/Pub devem incluir lembrete de transporte seguro sem dirigir no fallback."""
    cand_bar = {
        "id": "c1",
        "nome": "Cervejaria Artesanal",
        "regiao_administrativa": "Asa Norte",
        "tipo": "Bar / Cervejaria",
    }
    cartoes = executar_agente_comunicacao([cand_bar], llm=None)
    assert len(cartoes) == 1
    assert "transporte sem dirigir" in cartoes[0]["por_que_combina"]
