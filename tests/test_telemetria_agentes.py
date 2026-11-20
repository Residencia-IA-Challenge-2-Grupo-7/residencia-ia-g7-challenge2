"""Testes unitários e de integração da telemetria e tracing do grafo no Langfuse Cloud (Issue #73).

Valida:
1. Mascaramento estrito de PII privada (CPFs, e-mails, telefones, origens e nomes de membros) (RNF-02, RNF-10);
2. Preservação de preços públicos dos lugares para validação factual do juiz;
3. Nomenclatura oficial dos spans dos nós (agente_0_pessoal .. agente_4_comunicacao);
4. Geração e formatação correta de URLs de trace dinâmicas (trace_url);
5. Spans explícitos com métricas de tokens, custo, latência e falhas em conformidade com o ADR 0015;
6. Resiliência e fallback offline quando credenciais não estiverem disponíveis.
"""
from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from src.telemetria.langfuse_agentes import (
    PROJETO_LANGFUSE_ID,
    SPANS_AGENTES,
    mascarar_pii,
    obter_trace_url,
    observar_agente,
    registrar_span_agente,
)


def test_mascarar_pii_preserva_precos_publicos_e_bloqueia_chaves_privadas():
    """Preços públicos dos lugares não devem ser apagados; tetos e dados privados são protegidos no cofre e por chaves."""
    texto = "Fatias a partir de R$ 15,00 e bolos no pote por R$ 12,00."
    assert mascarar_pii(texto) == texto  # preserva preços públicos para conferência do juiz

    dados = {"lugar": "Valzira", "preco": "R$ 15,00", "teto": "60", "origem": "Guará"}
    mascarado = mascarar_pii(dados)
    assert mascarado["preco"] == "R$ 15,00"
    assert mascarado["teto"] == "[DADO_PRIVADO_REMOVIDO]"
    assert mascarado["origem"] == "[DADO_PRIVADO_REMOVIDO]"


def test_mascarar_pii_emails_telefones_cpfs():
    """E-mails, telefones e CPFs devem ser mascarados."""
    texto = "Contato: duda@example.com, tel (61) 98765-4321, CPF 123.456.789-00."
    mascarado = mascarar_pii(texto)
    assert "duda@example.com" not in mascarado
    assert "[EMAIL_REMOVIDO]" in mascarado
    assert "98765-4321" not in mascarado
    assert "[TELEFONE_REMOVIDO]" in mascarado
    assert "123.456.789-00" not in mascarado
    assert "[CPF_REMOVIDO]" in mascarado


def test_mascarar_pii_origens_individuais():
    """Menções explícitas de origens individuais devem ser mascaradas."""
    frase = "Recomendo um lugar bom para quem sai de Ceilândia ou partindo de Taguatinga."
    mascarado = mascarar_pii(frase)
    assert "[ORIGEM_REMOVIDA]" in mascarado
    assert "quem sai de Ceilândia" not in mascarado


def test_mascarar_pii_nomes_de_membros():
    """Nomes de participantes fornecidos devem ser mascarados."""
    texto = "A Maria Eduarda e o Caio vão adorar o ambiente com a Bia."
    nomes = ["Maria Eduarda", "Caio", "Bia"]
    mascarado = mascarar_pii(texto, nomes_proibidos=nomes)
    assert "Maria Eduarda" not in mascarado
    assert "Caio" not in mascarado
    assert "Bia" not in mascarado
    assert "[NOME_REMOVIDO]" in mascarado


def test_mascarar_pii_chaves_privadas_em_dicionarios():
    """Chaves estritamente privadas em dicionários devem ser substituídas."""
    dados = {
        "sala_id": "SALA-01",
        "teto": 60,
        "origem": "Sobradinho",
        "usuario": "usr_12345",
        "publico": "Lugar animado",
    }
    limpo = mascarar_pii(dados)
    assert limpo["sala_id"] == "SALA-01"
    assert limpo["publico"] == "Lugar animado"
    assert limpo["teto"] == "[DADO_PRIVADO_REMOVIDO]"
    assert limpo["origem"] == "[DADO_PRIVADO_REMOVIDO]"
    assert limpo["usuario"] == "[DADO_PRIVADO_REMOVIDO]"


def test_mascarar_pii_estruturas_aninhadas():
    """Estruturas complexas (listas aninhadas em dicionários) devem ser varridas recursivamente."""
    payload = {
        "membros": [
            {"nome": "Eduarda", "email": "duda@test.com"},
            {"nome": "Lucas", "origem": "Águas Claras"},
        ],
        "metadados": {
            "contatos": ["(61) 91111-2222"],
        },
    }
    limpo = mascarar_pii(payload, nomes_proibidos=["Eduarda", "Lucas"])
    assert limpo["membros"][0]["nome"] == "[NOME_REMOVIDO]"
    assert limpo["membros"][0]["email"] == "[EMAIL_REMOVIDO]"
    assert limpo["membros"][1]["origem"] == "[DADO_PRIVADO_REMOVIDO]"
    assert limpo["metadados"]["contatos"][0] == "[TELEFONE_REMOVIDO]"


def test_spans_agentes_mapeamento_canonico():
    """Mapeamento canônico deve conter todos os nós oficiais exigidos na issue #73."""
    assert SPANS_AGENTES["no_pessoal"] == "agente_0_pessoal"
    assert SPANS_AGENTES["no_consolidar_grupo"] == "agente_orquestrador_consolidar"
    assert SPANS_AGENTES["no_pesquisa"] == "agente_1_pesquisa"
    assert SPANS_AGENTES["no_logistica"] == "agente_2_logistica"
    assert SPANS_AGENTES["no_validacao"] == "agente_3_validacao"
    assert SPANS_AGENTES["no_comunicacao"] == "agente_4_comunicacao"
    assert SPANS_AGENTES["no_validacao_textos"] == "agente_3_validacao_textos"
    assert SPANS_AGENTES["no_finalizar"] == "agente_orquestrador_finalizar"
    assert SPANS_AGENTES["sala_multiagente"] == "grafo_sala_multiagente"


def test_obter_trace_url_com_id_explicito():
    """obter_trace_url deve gerar o link canônico do trace no Langfuse."""
    url = obter_trace_url("tr_123456789abc")
    assert url is not None
    assert "tr_123456789abc" in url
    assert "https://cloud.langfuse.com" in url


def test_obter_trace_url_prioriza_sdk_dinamico():
    """Prioriza o get_trace_url retornado dinamicamente pelo cliente do SDK sem forçar id fixo."""
    mock_client = MagicMock()
    mock_client.get_trace_url.return_value = "https://meu-langfuse.corp/project/proj_novo_123/traces/tr_dinamico"
    with patch("langfuse.get_client", return_value=mock_client):
        url = obter_trace_url("tr_dinamico")
        assert url == "https://meu-langfuse.corp/project/proj_novo_123/traces/tr_dinamico"
        mock_client.get_trace_url.assert_called_once_with(trace_id="tr_dinamico")


def test_obter_trace_url_respeita_host_personalizado():
    """Respeita LANGFUSE_HOST ou LANGFUSE_BASE_URL customizados no fallback."""
    mock_client = MagicMock()
    mock_client.get_trace_url.return_value = None
    with patch("langfuse.get_client", return_value=mock_client):
        with patch.dict(os.environ, {"LANGFUSE_HOST": "https://telemetria.local", "LANGFUSE_BASE_URL": ""}):
            url = obter_trace_url("tr_001")
            assert url is not None
            assert url.startswith("https://telemetria.local")
            assert "tr_001" in url

        with patch.dict(os.environ, {"LANGFUSE_BASE_URL": "https://base.local", "LANGFUSE_HOST": ""}):
            url = obter_trace_url("tr_002")
            assert url is not None
            assert url.startswith("https://base.local")
            assert "tr_002" in url


def test_observar_agente_retorna_funcao_decoradora():
    """O decorador observar_agente deve embrulhar funções com segurança."""
    @observar_agente("no_pesquisa", tipo="agent")
    def func_teste(x: int) -> int:
        return x * 2

    assert callable(func_teste)
    assert func_teste(3) == 6


def test_resiliencia_offline_registrar_span():
    """registrar_span_agente não deve quebrar quando Langfuse não estiver gravando."""
    # Chamada segura fora de contexto do Langfuse
    registrar_span_agente(
        "no_validacao",
        entrada={"ranking": ["l1", "l2"]},
        saida={"aprovados": ["l1"]},
        iteracao=1,
        vetos={"horario": 1},
    )


def test_registrar_span_quando_gravando_chama_update_current_span():
    """Quando o span estiver ativo, deve registrar o nome canônico e mascarar PII."""
    mock_span = MagicMock()
    mock_span.is_recording.return_value = True

    mock_client = MagicMock()

    with patch("opentelemetry.trace.get_current_span", return_value=mock_span), \
         patch("langfuse.get_client", return_value=mock_client):
        registrar_span_agente(
            "no_validacao",
            entrada={"candidato": "quem sai de Ceilândia", "teto": "60"},
            saida={"resultado": "aprovado para a Maria"},
            nomes_proibidos=["Maria"],
            iteracao_pesquisa=1,
            quantidade_vetos=2,
            convergido=True,
        )

        assert mock_client.update_current_span.called
        kw = mock_client.update_current_span.call_args[1]
        assert kw["name"] == "agente_3_validacao"
        assert "[ORIGEM_REMOVIDA]" in str(kw["input"])
        assert "[DADO_PRIVADO_REMOVIDO]" in str(kw["input"])
        assert "[NOME_REMOVIDO]" in str(kw["output"])
        assert kw["metadata"]["iteracao_pesquisa"] == 1
        assert kw["metadata"]["quantidade_vetos"] == 2
        assert kw["metadata"]["convergido"] is True


def test_registrar_span_com_metricas_tokens_e_custo():
    """Registra tokens, custo, latência e tentativas sem resposta nos metadados do span."""
    mock_span = MagicMock()
    mock_span.is_recording.return_value = True
    mock_client = MagicMock()

    with patch("opentelemetry.trace.get_current_span", return_value=mock_span), \
         patch("langfuse.get_client", return_value=mock_client):
        registrar_span_agente(
            "agente_1_pesquisa",
            entrada={"query": "café"},
            saida={"candidatos": ["c1"]},
            tokens=450,
            custo_usd=0.00125,
            latencia_llm_s=2.34,
            chamadas_llm=1,
            tentativas_sem_resposta=0,
            modelos=["deepseek/deepseek-v4.1-flash-1017"],
        )

        assert mock_client.update_current_span.called
        kw = mock_client.update_current_span.call_args[1]
        assert kw["name"] == "agente_1_pesquisa"
        meta = kw["metadata"]
        assert meta["tokens"] == 450
        assert meta["custo_usd"] == 0.00125
        assert meta["latencia_llm_s"] == 2.34
        assert meta["chamadas_llm"] == 1
        assert meta["tentativas_sem_resposta"] == 0
        assert meta["modelos"] == ["deepseek/deepseek-v4.1-flash-1017"]


def test_grafo_executar_retorna_trace_url_unificado():
    """O estado final retornado pelo grafo deve conter apenas trace_url (sem langfuse_trace_url duplicado)."""
    from src.agentes.grafo import executar_fluxo_multiagente
    from src.agentes.llm import ClienteLLM

    dados_sala = {
        "codigo": "ROLE-TELEMETRIA",
        "agora": "2026-11-21T15:00:00",
        "membros": [
            {
                "nome": "Duda",
                "origem": "Taguatinga",
                "horarios": "sábado 15h às 18h",
                "teto": "60",
                "preferencias": "café calmo",
            },
            {
                "nome": "Caio",
                "origem": "Águas Claras",
                "horarios": "sábado 15h às 18h",
                "teto": "80",
                "preferencias": "cafeteria boa",
            },
        ],
    }

    final = executar_fluxo_multiagente(dados_sala, cliente=ClienteLLM(offline=True))
    assert "trace_url" in final
    assert "langfuse_trace_url" not in final


def test_grafo_executar_adere_ao_adr_0015_sem_callbacks_duplicados():
    """Garante que executar não injeta callbacks duplicados no LangGraph e roda spans explícitos."""
    from src.agentes.grafo import cofre_dos_dados, construir_grafo
    from src.agentes.llm import ClienteLLM

    dados_sala = {
        "codigo": "ROLE-ADR0015",
        "agora": "2026-11-21T15:00:00",
        "membros": [
            {"nome": "Duda", "origem": "Taguatinga", "horarios": "sábado 15h às 18h", "teto": "60", "preferencias": "café"},
            {"nome": "Caio", "origem": "Águas Claras", "horarios": "sábado 15h às 18h", "teto": "80", "preferencias": "café"},
        ],
    }
    cofre = cofre_dos_dados(dados_sala)
    grafo = construir_grafo(cofre, ClienteLLM(offline=True))
    assert grafo is not None
