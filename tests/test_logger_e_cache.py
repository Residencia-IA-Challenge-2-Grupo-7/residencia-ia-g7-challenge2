"""
Testes automatizados do Módulo de Telemetria, Logger sem PII e Cache (Semana 3)
Issue #35 | RNF-01, RNF-02, RNF-10, RNF-14, RNF-15
Responsável: Maria Eduarda (DevOps & LLMOps)
"""

import json
from pathlib import Path
import pytest

from src.telemetria.logger_metricas import (
    sanitizar_texto_pii,
    registrar_evento_metrica,
    gerar_chave_cache,
    obter_cache_avaliacao,
    salvar_cache_avaliacao,
    limpar_cache_avaliacao,
    LIMITE_LATENCIA_SLA_MS,
)


@pytest.fixture(autouse=True)
def setup_teardown_cache(tmp_path):
    """Garante isolamento completo de cache e arquivos temporários entre cada teste."""
    limpar_cache_avaliacao()
    yield
    limpar_cache_avaliacao()


# ==============================================================================
# TESTES DE SANITIZAÇÃO DE DADOS PESSOAIS E SIGILO (RNF-01, RNF-02, RNF-10)
# ==============================================================================

def test_sanitizar_email_completo():
    """Valida que qualquer formato de e-mail é estritamente mascarado."""
    texto = "Envie os detalhes para maria.eduarda@unb.br ou contato_duda+teste@gmail.com por favor."
    limpo = sanitizar_texto_pii(texto)

    assert "maria.eduarda@unb.br" not in limpo
    assert "contato_duda+teste@gmail.com" not in limpo
    assert "[EMAIL_PROTEGIDO]" in limpo


def test_sanitizar_cpf_formatado_e_puro():
    """Valida o mascaramento de CPFs com pontuação ou apenas números."""
    texto = "Documento do membro: 023.456.789-10 ou chave pix 02345678910 confirmada."
    limpo = sanitizar_texto_pii(texto)

    assert "023.456.789-10" not in limpo
    assert "02345678910" not in limpo
    assert "[CPF_PROTEGIDO]" in limpo


def test_sanitizar_telefone_variados_brasil():
    """Valida mascaramento de telefones com DDD, celular e código de país."""
    casos = [
        "me liga no (61) 98888-7777 urgente",
        "whatsapp: +55 61 99123-4567",
        "contato comercial: 61 3322-4455",
        "número direto 61987654321",
    ]
    for caso in casos:
        limpo = sanitizar_texto_pii(caso)
        assert "[TELEFONE_PROTEGIDO]" in limpo
        assert "98888-7777" not in limpo
        assert "99123-4567" not in limpo


def test_sanitizar_orcamentos_pessoais_e_sigilosos():
    """
    Valida a blindagem contra vazamento de orçamentos individuais (RNF-02 e ADR 0007).
    Garante que valores atrelados a membros da sala não fiquem expostos no log.
    """
    casos = [
        "o Caio só tem 50 conto para o rolê",
        "Rafaela tem no máximo R$ 30,00",
        "o Marcio pode gastar até 70 reais",
        "meu orçamento é 45 reais",
        "tô liso, só tenho 20 conto",
    ]
    for c in casos:
        limpo = sanitizar_texto_pii(c)
        assert "[ORCAMENTO_SIGILOSO]" in limpo
        assert "50 conto" not in limpo
        assert "30,00" not in limpo
        assert "70 reais" not in limpo


def test_sanitizar_texto_vazio_ou_seguro():
    """Garante resiliência com entradas nulas e textos sem PII."""
    assert sanitizar_texto_pii(None) == ""
    assert sanitizar_texto_pii("") == ""
    texto_seguro = "Quero um bar tranquilo na Asa Sul no sábado à tarde"
    assert sanitizar_texto_pii(texto_seguro) == texto_seguro


# ==============================================================================
# TESTES DO LOGGER ESTRUTURADO DE MÉTRICAS (RNF-10, RNF-14)
# ==============================================================================

def test_registrar_evento_metrica_estrutura_obrigatoria(tmp_path):
    """Valida a emissão estruturada de métricas com todos os campos exigidos."""
    log_file = tmp_path / "teste_metricas.jsonl"

    evento = registrar_evento_metrica(
        modo="modo_b_rag",
        latencia_ms=120.5,
        tokens_total=350,
        cache_hit=False,
        consulta="Barzinho na Asa Norte contato joao@email.com",
        arquivo_log=log_file,
    )

    # Validação de tipos e campos obrigatórios
    assert "evento_id" in evento and len(evento["evento_id"]) == 36  # UUID4
    assert "timestamp" in evento
    assert evento["modo"] == "modo_b_rag"
    assert evento["latencia_ms"] == 120.5
    assert evento["tokens_total"] == 350
    assert evento["custo_estimado_brl"] > 0.0
    assert evento["cache_hit"] is False
    assert evento["status_sla"] == "DENTRO_DO_SLA"
    assert "[EMAIL_PROTEGIDO]" in evento["consulta_sanitizada"]
    assert "joao@email.com" not in evento["consulta_sanitizada"]

    # Validação da persistência física em JSONL
    assert log_file.exists()
    linhas = log_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(linhas) == 1
    gravado = json.loads(linhas[0])
    assert gravado["evento_id"] == evento["evento_id"]


def test_registrar_evento_sla_latencia(tmp_path):
    """Valida a detecção de violação do SLA de latência (> 5.000 ms - RNF-14)."""
    log_file = tmp_path / "sla.jsonl"

    ev_ok = registrar_evento_metrica(
        modo="modo_a_llm_pura",
        latencia_ms=1800.0,
        tokens_total=100,
        arquivo_log=log_file,
    )
    assert ev_ok["status_sla"] == "DENTRO_DO_SLA"

    ev_violado = registrar_evento_metrica(
        modo="modo_a_llm_pura",
        latencia_ms=5400.0,  # Acima de 5.000 ms
        tokens_total=200,
        arquivo_log=log_file,
    )
    assert ev_violado["status_sla"] == "VIOLOU_SLA"


# ==============================================================================
# TESTES DE CACHE DETERMINÍSTICO E GOVERNANÇA DE CUSTOS (RNF-15)
# ==============================================================================

def test_cache_deterministo_sha256(tmp_path):
    """Valida que consultas idênticas geram a mesma chave SHA-256 e retornam cache_hit."""
    cache_file = tmp_path / "cache_teste.json"
    consulta = "Onde comer um rodízio barato em Águas Claras?"

    # 1. Primeira consulta: Cache Miss
    item_cache = obter_cache_avaliacao(consulta, modo="modo_b_rag", arquivo_cache=cache_file)
    assert item_cache is None

    # 2. Salva o resultado no cache
    resposta_simulada = {
        "lugares": ["Dona Cleide", "Costella"],
        "similaridade_media": 0.94,
    }
    salvar_cache_avaliacao(
        consulta=consulta,
        modo="modo_b_rag",
        resposta=resposta_simulada,
        tokens_total=420,
        latencia_ms=315.0,
        arquivo_cache=cache_file,
    )

    # 3. Segunda consulta idêntica: Cache Hit garantido com custo 0
    segunda_chamada = obter_cache_avaliacao(consulta, modo="modo_b_rag", arquivo_cache=cache_file)
    assert segunda_chamada is not None
    assert segunda_chamada["cache_hit"] is True
    assert segunda_chamada["resposta"]["lugares"] == ["Dona Cleide", "Costella"]

    # 4. Registro de evento com cache_hit confirma tokens_total = 0 e custo_estimado_brl = 0.0
    ev = registrar_evento_metrica(
        modo="modo_b_rag",
        latencia_ms=2.1,
        tokens_total=420,  # O evento deve zerar os tokens efetivos cobrados
        cache_hit=True,
        consulta=consulta,
        arquivo_log=tmp_path / "metricas.jsonl",
    )
    assert ev["cache_hit"] is True
    assert ev["tokens_total"] == 0
    assert ev["custo_estimado_brl"] == 0.0


def test_cache_diferencia_modos():
    """Garante que modo_a_llm_pura e modo_b_rag tenham chaves e caches separados para a mesma pergunta."""
    p = "Qual a melhor cafeteria na Asa Norte?"
    chave_a = gerar_chave_cache(p, modo="modo_a_llm_pura")
    chave_b = gerar_chave_cache(p, modo="modo_b_rag")

    assert chave_a != chave_b
