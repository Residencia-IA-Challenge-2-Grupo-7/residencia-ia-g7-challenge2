"""Testes automatizados do motor de Avaliação Híbrida da Semana 3 (issue #36).

Garante sem chamadas externas de rede:
1. Resposta alucinada (inventando local, endereço e preço) recebe `taxa_alucinacao > 0.5` e
   `fidelidade_factual_rnf03 < 0.5`.
2. Resposta fundamentada no gabarito 2FA recebe `fidelidade_factual_rnf03 == 1.0` e
   `taxa_alucinacao == 0.0`.
3. O juiz usa `xiaomi/mimo-v2.6-pro`, temperatura 0, `response_format={"type": "json_object"}` e
   roteamento sem retenção, com fallback determinístico quando offline ou sem chave.
4. As métricas de busca (`recall_at_k`, `mrr`, `recusa_correta`, `recusa_indevida`) e o SLA de
   latência (`sla_latencia_rnf14`) são calculados corretamente.
5. Os scores são registrados no Langfuse Cloud via `create_score`, e `simular_recuperacao_rag`
   não registra mais a nota fixa `fidelidade_rnf03_zero_alucinacao`.
"""
from __future__ import annotations

import json

import pytest

from src.telemetria.evals_semana3 import (
    MODELO_JUIZ_PADRAO,
    avaliar_par_comparativo,
    calcular_metricas_busca,
    verificar_deterministico_rnf04,
)


class _RespostaHTTPFalsa:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload

    def json(self) -> dict:
        return self._payload


class _SessaoJuizFalsa:
    """Simula a API da OpenRouter para o juiz MiMo-V2.6-Pro."""

    def __init__(self, respostas_por_chamada: list[dict] | None = None, status_code: int = 200):
        self.respostas = list(respostas_por_chamada or [])
        self.status_code = status_code
        self.chamadas: list[dict] = []

    def post(self, url: str, json: dict | None = None, timeout: int = 20, headers: dict | None = None):
        self.chamadas.append({"url": url, "json": json, "headers": headers, "timeout": timeout})
        if self.status_code >= 400:
            return _RespostaHTTPFalsa(self.status_code, {"error": "falha simulada"})
        conteudo = self.respostas.pop(0) if self.respostas else {
            "afirmacoes": [
                {
                    "tipo": "lugar",
                    "trecho": "Filomenambúrguer",
                    "veredito": "confere com a base",
                    "justificativa": "Consta na base 2FA.",
                }
            ],
            "resumo_juiz": "OK",
        }
        return _RespostaHTTPFalsa(
            200,
            {
                "model": MODELO_JUIZ_PADRAO,
                "choices": [{"message": {"content": json_dumps(conteudo)}, "finish_reason": "stop"}],
            },
        )


def json_dumps(obj: dict) -> str:
    return json.dumps(obj, ensure_ascii=False)


@pytest.fixture
def caso_golden_01() -> dict:
    return {
        "pergunta": "Onde tem rodízio de mini hambúrguer e pão de queijo em Taguatinga para ir com amigos?",
        "gabarito": {
            "categoria": "geoespacial_ra_fora_centro",
            "ra_esperada": "Taguatinga",
            "locais_gabarito": ["Filomenambúrguer"],
            "preco_maximo_gabarito": 49.99,
            "horario_gabarito": "Todos os dias",
            "evidencia_id_tiktok": "tiktok_7626405885388197128",
        },
        "modo_a_alucinado": {
            "resposta": (
                "Recomendo a **Hamburgueria Fantasma do Cerrado**, localizada na SQN 999 Bloco Z na Asa Norte, "
                "com rodízio completo por R$ 129,90 aberto 24h."
            ),
            "fontes_utilizadas": [],
            "latencia_ms": 3450.0,
            "disponivel": True,
        },
        "modo_b_ancorado": {
            "resposta": (
                "Em Taguatinga, a recomendação oficial da base é o **Filomenambúrguer** [FONTE #2], "
                "em Taguatinga Norte, Brasília - DF. Preço médio de R$ 49,99, aberto todos os dias com "
                "rodízio de mini hambúrguer e pão de queijo."
            ),
            "fontes_utilizadas": [
                {
                    "id": "tiktok_7600073980363574535",
                    "nome": "Casa Bari",
                    "ra": "Taguatinga",
                    "custo_medio_rs": 69.9,
                    "score_similaridade": 0.98,
                    "citada": False,
                },
                {
                    "id": "tiktok_7626405885388197128",
                    "nome": "Filomenambúrguer",
                    "ra": "Taguatinga",
                    "custo_medio_rs": 49.99,
                    "score_similaridade": 0.98,
                    "citada": True,
                },
            ],
            "guardrails": {"permitido": True, "motivo_bloqueio": None, "teto_aplicado_rs": None, "avisos": []},
            "latencia_ms": 2980.0,
            "disponivel": True,
        },
    }


def test_resposta_alucinada_vs_fundamentada_com_juiz_mimo(monkeypatch, caso_golden_01):
    """Requisito obrigatório da issue #36:
    - resposta alucinada recebe `taxa_alucinacao > 0.5` e `fidelidade_factual_rnf03 < 0.5`
    - resposta fundamentada no gabarito 2FA recebe `fidelidade_factual_rnf03 == 1.0` e `taxa_alucinacao == 0.0`.
    """
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test-dummy")

    julgamento_modo_a = {
        "afirmacoes": [
            {
                "tipo": "lugar",
                "trecho": "Hamburgueria Fantasma do Cerrado",
                "veredito": "não está na base",
                "justificativa": "Estabelecimento inventado que não existe nos 93 locais.",
            },
            {
                "tipo": "endereco",
                "trecho": "SQN 999 Bloco Z na Asa Norte",
                "veredito": "contradiz a base",
                "justificativa": "Quadra inexistente e fora de Taguatinga.",
            },
            {
                "tipo": "preco",
                "trecho": "R$ 129,90",
                "veredito": "contradiz a base",
                "justificativa": "Preço inventado.",
            },
        ],
        "resumo_juiz": "Alucinação completa de local, endereço e preço.",
    }
    julgamento_modo_b = {
        "afirmacoes": [
            {
                "tipo": "lugar",
                "trecho": "Filomenambúrguer",
                "veredito": "confere com a base",
                "justificativa": "Local oficial da base 2FA em Taguatinga.",
            },
            {
                "tipo": "endereco",
                "trecho": "Taguatinga Norte, Brasília - DF",
                "veredito": "confere com a base",
                "justificativa": "Confere com o endereço cadastrado.",
            },
            {
                "tipo": "preco",
                "trecho": "R$ 49,99",
                "veredito": "confere com a base",
                "justificativa": "Confere com custo_medio_rs = 49.99.",
            },
        ],
        "resumo_juiz": "Totalmente fiel à base 2FA.",
    }

    sessao = _SessaoJuizFalsa([julgamento_modo_a, julgamento_modo_b])
    resultado = avaliar_par_comparativo(
        caso_golden_01["pergunta"],
        caso_golden_01["gabarito"],
        caso_golden_01["modo_a_alucinado"],
        caso_golden_01["modo_b_ancorado"],
        sessao=sessao,
        registrar_langfuse=False,
    )

    scores_a = resultado["modo_a_llm_pura"]["scores"]
    scores_b = resultado["modo_b_rag"]["scores"]

    assert scores_a["taxa_alucinacao"] > 0.5
    assert scores_a["fidelidade_factual_rnf03"] < 0.5
    assert scores_a["precisao_geoespacial_ra"] == 0.0

    assert scores_b["fidelidade_factual_rnf03"] == 1.0
    assert scores_b["taxa_alucinacao"] == 0.0
    assert scores_b["precisao_geoespacial_ra"] == 1.0
    assert scores_b["sla_latencia_rnf14"] == 1.0

    # Confere parâmetros da chamada à OpenRouter (modelo MiMo-V2.6-Pro, temperatura 0, JSON object e ZDR)
    assert len(sessao.chamadas) == 2
    corpo_enviado = sessao.chamadas[0]["json"]
    assert corpo_enviado["model"] == "xiaomi/mimo-v2.6-pro"
    assert corpo_enviado["temperature"] == 0
    assert corpo_enviado["response_format"] == {"type": "json_object"}
    assert corpo_enviado["provider"]["zdr"] is True
    assert corpo_enviado["provider"]["data_collection"] == "deny"


def test_fallback_deterministico_offline_garante_mesmos_limites_de_alucinacao_e_fidelidade(
    monkeypatch, caso_golden_01
):
    """Mesmo sem chave da OpenRouter ou offline, o verificador determinístico (RNF-04) garante
    `taxa_alucinacao > 0.5` e `fidelidade < 0.5` para a resposta alucinada, e `1.0 / 0.0` para a ancorada.
    """
    sessao_falha = _SessaoJuizFalsa(status_code=503)
    resultado = avaliar_par_comparativo(
        {
            "id_golden": "golden_01",
            "pergunta": caso_golden_01["pergunta"],
            "gabarito": caso_golden_01["gabarito"],
            "modo_a_llm_pura": caso_golden_01["modo_a_alucinado"],
            "modo_b_rag": caso_golden_01["modo_b_ancorado"],
        },
        sessao=sessao_falha,
        registrar_langfuse=False,
    )

    assert resultado["id_golden"] == "golden_01"
    assert resultado["modo_a_llm_pura"]["julgamento_juiz"]["usou_llm"] is False
    assert resultado["modo_b_rag"]["julgamento_juiz"]["usou_llm"] is False

    scores_a = resultado["modo_a_llm_pura"]["scores"]
    scores_b = resultado["modo_b_rag"]["scores"]

    assert scores_a["taxa_alucinacao"] > 0.5
    assert scores_a["fidelidade_factual_rnf03"] < 0.5

    assert scores_b["fidelidade_factual_rnf03"] == 1.0
    assert scores_b["taxa_alucinacao"] == 0.0


def test_metricas_busca_recall_mrr_e_recusas():
    """Valida cálculo de recall@k, MRR, recusa correta fora do DF e recusa indevida no DF."""
    # 1. Lugar do gabarito na 2ª posição -> recall@k = 1.0, MRR = 0.5
    gabarito_df = {
        "categoria": "geoespacial_ra_fora_centro",
        "ra_esperada": "Taguatinga",
        "locais_gabarito": ["Filomenambúrguer"],
        "evidencia_id_tiktok": "tiktok_7626405885388197128",
    }
    modo_b_pos2 = {
        "fontes_utilizadas": [
            {"id": "tiktok_7600073980363574535", "nome": "Casa Bari"},
            {"id": "tiktok_7626405885388197128", "nome": "Filomenambúrguer"},
        ],
        "guardrails": {"permitido": True},
    }
    m1 = calcular_metricas_busca(gabarito_df, modo_b_pos2)
    assert m1["recall_at_k"] == 1.0
    assert m1["mrr"] == 0.5
    assert m1["posicao_gabarito"] == 2
    assert m1["recusa_indevida"] == 0.0

    # 2. Pergunta válida do DF bloqueada pelo guardrail (como golden_06) -> recusa_indevida = 1.0
    modo_b_bloqueado = {
        "fontes_utilizadas": [],
        "guardrails": {"permitido": False, "motivo_bloqueio": "baixa_aderencia"},
    }
    m2 = calcular_metricas_busca(gabarito_df, modo_b_bloqueado)
    assert m2["recall_at_k"] == 0.0
    assert m2["mrr"] == 0.0
    assert m2["recusa_indevida"] == 1.0

    # 3. Pergunta fora do DF recusada pelo guardrail (como golden_09) -> recusa_correta = 1.0
    gabarito_fora = {
        "categoria": "fora_de_escopo_df",
        "ra_esperada": None,
        "locais_gabarito": [],
    }
    m3 = calcular_metricas_busca(gabarito_fora, modo_b_bloqueado)
    assert m3["recall_at_k"] is None
    assert m3["mrr"] is None
    assert m3["recusa_correta"] == 1.0
    assert m3["recusa_indevida"] == 0.0


def test_sla_latencia_rnf14_respeita_teto_de_5000ms(caso_golden_01):
    """Valida que latência <= 5000 ms recebe 1.0 e > 5000 ms recebe 0.0."""
    modo_lento = {**caso_golden_01["modo_a_alucinado"], "latencia_ms": 5420.0}
    modo_rapido = {**caso_golden_01["modo_b_ancorado"], "latencia_ms": 4890.0}
    sessao_offline = _SessaoJuizFalsa(status_code=503)

    res = avaliar_par_comparativo(
        caso_golden_01["pergunta"],
        caso_golden_01["gabarito"],
        modo_lento,
        modo_rapido,
        sessao=sessao_offline,
        registrar_langfuse=False,
    )
    assert res["modo_a_llm_pura"]["scores"]["sla_latencia_rnf14"] == 0.0
    assert res["modo_b_rag"]["scores"]["sla_latencia_rnf14"] == 1.0


def test_registro_scores_no_langfuse_e_remocao_de_nota_fixa(monkeypatch, caso_golden_01):
    """Confere que os scores calculados são enviados ao cliente do Langfuse e que
    `simular_recuperacao_rag` não cria mais a nota fixa `fidelidade_rnf03_zero_alucinacao`.
    """
    scores_registrados: list[dict] = []

    class _ClienteLangfuseFalso:
        def get_current_trace_id(self):
            return "trace-teste-36"

        def set_current_trace_as_public(self):
            pass

        def get_trace_url(self):
            return "https://cloud.langfuse.com/trace/trace-teste-36"

        def create_score(self, **kwargs):
            scores_registrados.append(kwargs)

        def update_current_span(self, **kwargs):
            pass

        def update_current_generation(self, **kwargs):
            pass

    monkeypatch.setattr("src.telemetria.evals_semana3.obter_cliente", lambda: _ClienteLangfuseFalso())
    monkeypatch.setattr("src.telemetria.telemetria.obter_cliente", lambda: _ClienteLangfuseFalso())

    sessao_offline = _SessaoJuizFalsa(status_code=503)
    res = avaliar_par_comparativo(
        caso_golden_01["pergunta"],
        caso_golden_01["gabarito"],
        caso_golden_01["modo_a_alucinado"],
        caso_golden_01["modo_b_ancorado"],
        sessao=sessao_offline,
        registrar_langfuse=True,
    )
    assert res["registrado_langfuse"] is True
    nomes = {s["name"] for s in scores_registrados}
    assert "fidelidade_factual_rnf03" in nomes
    assert "taxa_alucinacao" in nomes
    assert "precisao_geoespacial_ra" in nomes
    assert "sla_latencia_rnf14" in nomes
    assert "busca_recall_at_k" in nomes
    assert "busca_mrr" in nomes

    # Verifica que simular_recuperacao_rag não registra mais fidelidade_rnf03_zero_alucinacao fixa
    scores_registrados.clear()
    from src.telemetria.telemetria import simular_recuperacao_rag

    simular_recuperacao_rag("Onde comer hambúrguer em Taguatinga?")
    nomes_simular = {s["name"] for s in scores_registrados}
    assert "fidelidade_rnf03_zero_alucinacao" not in nomes_simular


def test_endpoint_comparativo_avaliar(monkeypatch, caso_golden_01):
    from unittest.mock import patch
    from fastapi.testclient import TestClient
    from src.main import app

    client = TestClient(app)
    # Testa rota passando o json simulado
    payload = {
        "pergunta": caso_golden_01["pergunta"],
        "gabarito": caso_golden_01["gabarito"],
        "modo_a_llm_pura": caso_golden_01["modo_a_alucinado"],
        "modo_b_rag": caso_golden_01["modo_b_ancorado"],
    }
    with patch("src.telemetria.evals_semana3.julgar_com_llm_judge") as mock_judge:
        mock_judge.return_value = {
            "disponivel": True,
            "fidelidade_factual_rnf03": 1.0,
            "taxa_alucinacao": 0.0,
            "precisao_geoespacial_ra": 1.0,
            "ra_correta": True,
            "preco_contradiz": False,
            "endereco_inventado": False,
            "alucinacoes_detectadas": [],
            "justificativa": "Sem alucinações",
        }
        res = client.post("/api/comparativo/avaliar", json=payload)
        assert res.status_code == 200
        dados = res.json()
        assert "avaliacao" in dados
        assert dados["avaliacao"]["modo_b_rag"]["scores"]["fidelidade_factual_rnf03"] == 1.0



def test_trecho_de_frase_entre_negritos_nao_vira_local_inventado():
    """Regressão (12/11): pares de ** desalinhados não podem marcar trecho de frase como lugar inventado."""
    from src.telemetria.evals_semana3 import _extrair_candidatos_locais_texto, _normalizar

    base = {_normalizar("Omura Sushi"): {"nome": "Omura Sushi"}}
    resposta = ("A base não tem um lugar que atenda a todos os critérios** (rodízio de pizza e **sushi, à noite, "
                "em Samambaia). Veja o que existe:\n\n**- **Omura Sushi** — Samambaia. Preço médio: R$ 70,00.")
    _, inventados = _extrair_candidatos_locais_texto(resposta, base)
    assert inventados == []

    # Nome próprio fora da base continua sendo pego
    _, inventados = _extrair_candidatos_locais_texto("Vá no **Bar do Zé Inventado** hoje.", base)
    assert inventados == ["Bar do Zé Inventado"]
