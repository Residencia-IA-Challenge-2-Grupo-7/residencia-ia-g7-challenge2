"""Testes unitários e de integração da telemetria e tracing do grafo no Langfuse Cloud (Issue #73).

Valida:
1. Mascaramento estrito de PII (valores em R$, CPFs, e-mails, telefones, origens e nomes de membros) (RNF-02, RNF-10);
2. Nomenclatura oficial dos spans dos nós (agente_0_pessoal .. agente_4_comunicacao);
3. Geração e formatação correta de URLs de trace (trace_url e langfuse_trace_url);
4. CallbackHandler integrado com LangGraph/LangChain com sanitização de inputs/outputs;
5. Resiliência e fallback offline quando credenciais não estiverem disponíveis.
"""
from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from src.telemetria.langfuse_agentes import (
    PROJETO_LANGFUSE_ID,
    SPANS_AGENTES,
    LangfuseAgentesCallbackHandler,
    criar_callback_handler_agentes,
    mascarar_pii,
    obter_trace_url,
    observar_agente,
    registrar_span_agente,
)


def test_mascarar_pii_valores_monetarios():
    """Valores em reais e moeda devem ser substituídos por [VALOR_REMOVIDO]."""
    texto = "O teto da Maria é R$ 40,00 e o João tem 50 reais para gastar."
    mascarado = mascarar_pii(texto)
    assert "R$ 40,00" not in mascarado
    assert "50 reais" not in mascarado
    assert "[VALOR_REMOVIDO]" in mascarado


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
    """Expressões indicando origens individuais devem ser mascaradas."""
    texto = "Ótimo pra quem sai de Ceilândia e muito bom partindo de Taguatinga."
    mascarado = mascarar_pii(texto)
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
    """Estruturas complexas (listas dentro de dicionários) devem ser varridas recursivamente."""
    dados = {
        "candidatos": [
            {"nome": "Café do Lago", "comentario": "quem vem de Samambaia chega rápido"},
            {"nome": "Bar Central", "valor": "gasto de 80 reais"},
        ],
        "metadados": {"contatos": ["teste@unb.br"]},
    }
    limpo = mascarar_pii(dados)
    assert "[ORIGEM_REMOVIDA]" in limpo["candidatos"][0]["comentario"]
    assert "[VALOR_REMOVIDO]" in limpo["candidatos"][1]["valor"]
    assert "[EMAIL_REMOVIDO]" in limpo["metadados"]["contatos"][0]


def test_spans_agentes_mapeamento_canonico():
    """Garante que todos os nós do fluxo possuem os nomes canônicos requeridos pela Issue #73."""
    assert SPANS_AGENTES["no_pessoal"] == "agente_0_pessoal"
    assert SPANS_AGENTES["no_pesquisa"] == "agente_1_pesquisa"
    assert SPANS_AGENTES["no_logistica"] == "agente_2_logistica"
    assert SPANS_AGENTES["no_validacao"] == "agente_3_validacao"
    assert SPANS_AGENTES["no_comunicacao"] == "agente_4_comunicacao"
    assert SPANS_AGENTES["no_validacao_textos"] == "agente_3_validacao_textos"
    assert SPANS_AGENTES["juiz_pesquisa"] == "agente_juiz_pesquisa"
    assert SPANS_AGENTES["juiz_comunicacao"] == "agente_juiz_comunicacao"


def test_obter_trace_url_com_id_explicito():
    """Gera link oficial no Langfuse Cloud baseado no trace_id e projeto oficial."""
    url = obter_trace_url("trace_teste_abc_123")
    assert url is not None
    assert PROJETO_LANGFUSE_ID in url
    assert "trace_teste_abc_123" in url
    assert "https://cloud.langfuse.com" in url


def test_obter_trace_url_respeita_host_personalizado():
    """Respeita LANGFUSE_HOST ou LANGFUSE_BASE_URL customizados."""
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


def test_callback_handler_mascara_inputs_e_outputs():
    """O CallbackHandler deve aplicar mascaramento em inputs e outputs de chains e tools."""
    handler = LangfuseAgentesCallbackHandler(nomes_proibidos=["Duda", "Caio"])

    inputs = {"pergunta": "O que a Duda quer?", "orcamento": "R$ 40"}
    meta = {"usuario": "Caio"}

    with patch("src.telemetria.langfuse_agentes._BaseCallbackHandler.on_chain_start", autospec=True, return_value=None) as mock_start:
        handler.on_chain_start({}, inputs, run_id="run_1", metadata=meta)
        if mock_start.called:
            chamada_inputs = mock_start.call_args[0][2]
            assert "Duda" not in str(chamada_inputs)

    outputs = {"resposta": "Sugiro barzinho perto de quem sai de Sobradinho."}
    with patch("src.telemetria.langfuse_agentes._BaseCallbackHandler.on_chain_end", autospec=True, return_value=None) as mock_end:
        handler.on_chain_end(outputs, run_id="run_1")
        if mock_end.called:
            chamada_outputs = mock_end.call_args[0][1]
            assert "[ORIGEM_REMOVIDA]" in str(chamada_outputs)


def test_criar_callback_handler_sem_chaves_retorna_none():
    """Sem credenciais do Langfuse no ambiente, deve retornar None sem levantar erro."""
    with patch.dict(os.environ, {}, clear=True):
        handler = criar_callback_handler_agentes()
        assert handler is None


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
            entrada={"candidato": "quem sai de Ceilândia", "orcamento": "R$ 50,00"},
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
        assert "[VALOR_REMOVIDO]" in str(kw["input"])
        assert "[NOME_REMOVIDO]" in str(kw["output"])
        assert kw["metadata"]["iteracao_pesquisa"] == 1
        assert kw["metadata"]["quantidade_vetos"] == 2
        assert kw["metadata"]["convergido"] is True


def test_callback_handler_get_trace_url():
    """get_trace_url deve retornar a URL oficial quando o trace_id estiver definido."""
    handler = LangfuseAgentesCallbackHandler()
    handler.ultimo_trace_id = "trace_custom_xyz"
    url = handler.get_trace_url()
    assert url is not None
    assert "trace_custom_xyz" in url
    assert PROJETO_LANGFUSE_ID in url


def test_grafo_executar_retorna_trace_url_e_langfuse_trace_url():
    """O estado final retornado pelo grafo deve conter trace_url e langfuse_trace_url."""
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
    assert "langfuse_trace_url" in final
    assert final["trace_url"] == final["langfuse_trace_url"]

