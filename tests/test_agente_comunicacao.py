"""Testes do Agente 4 (Comunicação - Anfitrião de Brasília) para a Issue #69.

Valida:
1. Esquema dos cartões gerados conforme Sugestao e CartaoSugestaoValidado;
2. Preenchimento determinístico de preços, tempos, links do TikTok e endereços (RNF-04);
3. Persona do Anfitrião e saída estrita em JSON com titulo, resumo_acesso e por_que_combina (RF-06);
4. Zero citação e vazamento de dados individuais ou orçamentos (RNF-02);
5. Fallback caloroso e determinístico quando offline ou em falha da API;
6. Compatibilidade com instâncias de Sugestao e dicts de CandidatoAvaliado;
7. Integração com o nó do LangGraph (no_comunicacao).
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from src.agentes.comunicacao import (CartaoSugestaoValidado, executar_agente_comunicacao,
                                     no_comunicacao)
from src.agentes.contratos import CartaoTexto, SaidaComunicacao
from src.agentes.estado import CHAVES_PRIVADAS
from src.agentes.llm import ClienteLLM
from src.salas.modelos import Sugestao

AGORA = datetime(2026, 11, 21, 18, 0, 0)

CANDIDATOS_EXEMPLO = [
    {
        "id": "cand_1",
        "lugar_id": "tiktok_7612334793040186632",
        "nome": "Restaurante Dona Cleide",
        "tipo": "Restaurante / Gastronomia",
        "ra_do_lugar": "Águas Claras",
        "regiao_administrativa": "Águas Claras",
        "endereco": "Águas Claras - Avenida das Araucárias, lote 885",
        "janela": "sábado, 18h às 21h",
        "quantos_podem": "4 de 4 podem",
        "horario_situacao": "aberto",
        "consumo_rs": Decimal("54.90"),
        "gasto_min": Decimal("54.90"),
        "gasto_max": Decimal("75.00"),
        "tempo_medio_chegada_min": 28,
        "tempo_maximo_chegada_min": 42,
        "nota_justica": 85.5,
        "pontuacao": 0.88,
        "tiktok_url": "https://www.tiktok.com/@rolezandoembrasilia/video/7612334793040186632",
        "fonte": "Vídeo de @rolezandoembrasilia publicado em 01/03/2026",
        "vibes": ["Kid Friendly", "Animado / Galera"],
        "inicio": AGORA,
        "fim": AGORA + timedelta(hours=3),
    },
    {
        "id": "cand_2",
        "lugar_id": "tiktok_9999999999999999999",
        "nome": "Café do Parque",
        "tipo": "Cafeteria / Doceria",
        "ra_do_lugar": "Guará",
        "regiao_administrativa": "Guará",
        "endereco": "QE 15, Guará II, Brasília - DF",
        "janela": "sábado, 16h às 19h",
        "quantos_podem": "4 de 4 podem",
        "horario_situacao": "provavel",
        "consumo_rs": Decimal("35.00"),
        "gasto_min": Decimal("35.00"),
        "gasto_max": Decimal("46.00"),
        "tempo_medio_chegada_min": 22,
        "tempo_maximo_chegada_min": 35,
        "nota_justica": 92.0,
        "pontuacao": 0.91,
        "tiktok_url": "https://www.tiktok.com/@rolezandoembrasilia/video/9999999",
        "fonte": "Vídeo de @rolezandoembrasilia publicado em 15/02/2026",
        "vibes": ["Calmo / Bom para Conversar", "Ao Ar Livre / Parque"],
        "inicio": AGORA,
        "fim": AGORA + timedelta(hours=3),
    },
]


def test_executar_comunicacao_offline_gera_esquema_valido():
    """Gera cartões válidos em modo offline sem rede ou chaves externas."""
    llm = ClienteLLM(offline=True)
    cartoes = executar_agente_comunicacao(CANDIDATOS_EXEMPLO, llm=llm)

    assert len(cartoes) == 2
    for c in cartoes:
        validado = CartaoSugestaoValidado.model_validate(c)
        assert validado.id in ("A", "B")
        assert validado.posicao in (1, 2)
        assert len(validado.titulo) > 5
        assert len(validado.resumo_acesso) > 10
        assert len(validado.por_que_combina) > 10
        assert validado.consumo_estimado_rs != ""
        assert "min" in validado.faixa_gasto_rs
        assert "max" in validado.faixa_gasto_rs


def test_preenchimento_deterministico_preserva_dados_reais():
    """Dados financeiros, tempos e links são preenchidos deterministicamente fora do LLM (RNF-04)."""
    llm = ClienteLLM(offline=True)
    cartoes = executar_agente_comunicacao(CANDIDATOS_EXEMPLO, llm=llm)

    c1 = cartoes[0]
    assert c1["nome"] == "Restaurante Dona Cleide"
    assert c1["consumo_estimado_rs"] == "54.90"
    assert c1["faixa_gasto_rs"] == {"min": "54.90", "max": "75.00"}
    assert c1["tempo_medio_chegada_min"] == 28
    assert c1["tempo_maximo_chegada_min"] == 42
    assert c1["nota_justica"] == 85.5
    assert c1["tiktok_url"] == "https://www.tiktok.com/@rolezandoembrasilia/video/7612334793040186632"
    assert "Dona Cleide" in c1["titulo"]


def test_chamada_llm_com_mock_injetado():
    """Valida o envio do prompt do Anfitrião e recepção estruturada via JSON Schema estrito."""
    sessao_mock = MagicMock()
    corpo_resposta = {
        "choices": [{
            "message": {
                "content": json.dumps({
                    "cartoes": [
                        {
                            "id": "A",
                            "titulo": "Noite de caldos e pizzas no Dona Cleide",
                            "resumo_acesso": "Acesso central em Águas Claras com trajeto tranquilo e balanceado para a turma.",
                            "por_que_combina": "Espaço amplo com música ao vivo e rodízio farto, ótimo para reunir a galera com descontração.",
                        },
                        {
                            "id": "B",
                            "titulo": "Tardezinha gostosa no Café do Parque",
                            "resumo_acesso": "Localização bem servida de transporte no Guará com chegada rápida para todos.",
                            "por_que_combina": "Clima tranquilo ao ar livre perfeito para papear e relaxar.",
                        },
                    ]
                })
            }
        }],
        "usage": {"total_tokens": 320, "cost": 0.0001},
        "model": "deepseek/deepseek-v4.1-flash-1017",
    }
    resposta_post = MagicMock()
    resposta_post.status_code = 200
    resposta_post.json.return_value = corpo_resposta
    sessao_mock.post.return_value = resposta_post

    llm = ClienteLLM(sessao=sessao_mock, chave="sk-mock-key")
    cartoes = executar_agente_comunicacao(CANDIDATOS_EXEMPLO, llm=llm)

    assert len(cartoes) == 2
    assert cartoes[0]["titulo"] == "Noite de caldos e pizzas no Dona Cleide"
    assert cartoes[0]["resumo_acesso"] == "Acesso central em Águas Claras com trajeto tranquilo e balanceado para a turma."
    assert cartoes[0]["por_que_combina"] == "Espaço amplo com música ao vivo e rodízio farto, ótimo para reunir a galera com descontração."
    assert "Espaço amplo" in cartoes[0]["explicacao"]

    # Verifica os parâmetros enviados na chamada
    chamada = sessao_mock.post.call_args
    assert chamada is not None
    url, kwargs = chamada[0][0], chamada[1]
    payload = kwargs["json"]
    assert payload["response_format"]["type"] == "json_schema"
    assert payload["response_format"]["json_schema"]["strict"] is True

    prompt_sistema = payload["messages"][0]["content"]
    assert "Anfitrião" in prompt_sistema
    assert "Brasília" in prompt_sistema


def test_rnf02_zero_vazamento_privacidade_nos_cartoes():
    """Nenhuma chave privada ou identificador confidencial pode constar nos cartões finais (RNF-02)."""
    llm = ClienteLLM(offline=True)
    cartoes = executar_agente_comunicacao(CANDIDATOS_EXEMPLO, llm=llm)

    for c in cartoes:
        for chave_privada in CHAVES_PRIVADAS:
            assert chave_privada not in c, f"Vazamento da chave privada '{chave_privada}' no cartão!"


def test_fallback_automatico_quando_llm_falha():
    """Se a chamada à API falhar com erro de rede ou HTTP 500, o fallback determinístico é acionado."""
    sessao_mock = MagicMock()
    resposta_500 = MagicMock()
    resposta_500.status_code = 500
    sessao_mock.post.return_value = resposta_500

    llm = ClienteLLM(sessao=sessao_mock, chave="sk-mock-key")
    cartoes = executar_agente_comunicacao(CANDIDATOS_EXEMPLO, llm=llm)

    assert len(cartoes) == 2
    assert "Dona Cleide" in cartoes[0]["titulo"]
    assert cartoes[0]["consumo_estimado_rs"] == "54.90"
    assert CartaoSugestaoValidado.model_validate(cartoes[0])


def test_compatibilidade_com_instancias_da_classe_sugestao():
    """Permite receber instâncias da dataclass Sugestao de src/salas/modelos.py."""
    sugestao_real = Sugestao(
        id="A",
        posicao=1,
        lugar_id="tiktok_7612334793040186632",
        nome="Restaurante Dona Cleide",
        tipo="Restaurante / Gastronomia",
        ra="Águas Claras",
        regiao_texto="Águas Claras",
        endereco="Avenida das Araucárias, lote 885",
        inicio=AGORA,
        fim=AGORA + timedelta(hours=3),
        horario_texto="18h às 21h",
        horario_situacao="aberto",
        contagem="4 de 4 podem",
        consumo_rs=Decimal("54.90"),
        gasto_min=Decimal("54.90"),
        gasto_max=Decimal("65.90"),
        tempo_medio_min=30,
        tempo_max_min=45,
        nota_justica=88.0,
        pontuacao=0.85,
        explicacao="Aprovado no cruzamento de horários.",
        tiktok_url="https://tiktok.com/@video",
        fonte="2FA TikTok",
        vibes=["Kid Friendly", "Animado / Galera"],
    )

    llm = ClienteLLM(offline=True)
    cartoes = executar_agente_comunicacao([sugestao_real], llm=llm)

    assert len(cartoes) == 1
    c = cartoes[0]
    assert c["id"] == "A"
    assert c["posicao"] == 1
    assert c["lugar_id"] == "tiktok_7612334793040186632"
    assert c["consumo_estimado_rs"] == "54.90"
    assert c["titulo"] != ""
    assert c["resumo_acesso"] != ""
    assert c["por_que_combina"] != ""


def test_no_comunicacao_integracao_langgraph_state():
    """Valida o funcionamento do nó de comunicação pronto para o grafo do LangGraph (#71)."""
    estado_entrada = {
        "candidatos_validados": CANDIDATOS_EXEMPLO,
        "preferencias_grupo": {"vibes": ["Animado / Galera"], "tipos": ["comer_beber"]},
    }

    resultado_no = no_comunicacao(estado_entrada, llm=ClienteLLM(offline=True))

    assert "cartoes" in resultado_no
    assert "cartoes_por_llm" in resultado_no
    assert "resultado_final_cartoes" in resultado_no
    assert len(resultado_no["resultado_final_cartoes"]) == 2
    assert len(resultado_no["cartoes"]) == 2
    assert resultado_no["cartoes"][0]["id"] == "A"
    assert "titulo" in resultado_no["cartoes"][0]


def test_lista_vazia_retorna_lista_vazia():
    """Com lista vazia de candidatos validados, retorna lista vazia imediatamente."""
    assert executar_agente_comunicacao([]) == []


def test_busca_automatica_na_base_2fa_por_id_ou_nome():
    """Busca dados da base oficial de 93 lugares quando fornecido apenas o id do TikTok."""
    llm = ClienteLLM(offline=True)
    candidatos_minimos = [{"id": "tiktok_7612334793040186632"}]
    cartoes = executar_agente_comunicacao(candidatos_minimos, llm=llm)

    assert len(cartoes) == 1
    c = cartoes[0]
    assert c["nome"] == "Restaurante Dona Cleide"
    assert c["tipo"] == "Restaurante / Gastronomia"
    assert c["regiao_administrativa"] == "Águas Claras"
    assert "Avenida das Araucárias" in c["endereco"]
    assert c["consumo_estimado_rs"] == "54.90"
    assert "tiktok.com" in c["tiktok_url"]
    assert "Kid Friendly" in c["vibes"]


def test_candidato_avaliado_pydantic_compatibilidade():
    """Funciona com instâncias da classe CandidatoAvaliado do estado do LangGraph."""
    from src.agentes.estado import CandidatoAvaliado

    cand_model = CandidatoAvaliado(
        id="tiktok_7612334793040186632",
        nome="Restaurante Dona Cleide",
        ra_do_lugar="Águas Claras",
        janela="sábado, 18h às 21h",
        quantos_podem="4 de 4",
        horario_situacao="aberto",
        nota_justica=88,
        pior_trajeto_min=35,
        media_trajeto_min=25,
        diferenca_min=10,
        estimativa_provisoria=False,
        pontuacao=0.88,
    )

    llm = ClienteLLM(offline=True)
    cartoes = executar_agente_comunicacao([cand_model], llm=llm)

    assert len(cartoes) == 1
    assert cartoes[0]["id"] == "A"
    assert cartoes[0]["tempo_medio_chegada_min"] == 25
    assert cartoes[0]["tempo_maximo_chegada_min"] == 35
    assert cartoes[0]["nota_justica"] == 88.0

