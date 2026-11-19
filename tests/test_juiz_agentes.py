"""Testes do Avaliador Semântico (LLM-as-a-Judge) em 2 Passagens (ADR 0014, Issue #72).

Cobre:
- Passagem 1: Auditoria da Pesquisa (confere, contradiz, sem_apoio);
- Passagem 2: Auditoria da Comunicação (fidelidade e ausência de vazamento de PII);
- Detecção estrita de exposições: origem, orçamento, restrição e texto pessoal (RNF-02);
- Fallback determinístico offline e tratamento gracioso de indisponibilidade da LLM;
- Suporte a MockLLM com JSON schema estrito;
- Utilitários de integração com o Grafo Multiagente (filtragem e mapa de reprovações);
- Integração com a base oficial curada de 93 locais do TikTok (2FA).
"""
import json
from pathlib import Path
from typing import Any
import pytest

from src.agentes.contratos import (
    AfirmacaoCartao,
    AfirmacaoParecer,
    Candidato,
    CartaoTexto,
    Exposicao,
    SaidaJuizCartoes,
    SaidaJuizParecer,
)
from src.agentes.juiz import (
    avaliar_reprovacoes_cartoes,
    filtrar_candidatos_aprovados_pelo_juiz,
    julgar_cartoes_comunicacao,
    julgar_parecer_pesquisa,
    obter_modelo_juiz,
)
from src.agentes.llm import ClienteLLM, ErroLLM


# -----------------------------------------------------------------------------
# Mocks de LLM para Testes Controlados
# -----------------------------------------------------------------------------

class MockLLMParecerSucesso:
    """Simula resposta válida do juiz na Passagem 1."""
    disponivel = True
    offline = False

    def json(self, agente: str, sistema: str, usuario: str, esquema: dict, **kwargs) -> dict:
        return {
            "afirmacoes": [
                {
                    "id": "cand_1",
                    "justificativa": "Trecho e motivo confirmados no documento da base 2FA.",
                    "veredito": "confere",
                },
                {
                    "id": "cand_alucinado",
                    "justificativa": "O documento não menciona deck panorâmico nem área VIP.",
                    "veredito": "sem_apoio",
                },
            ]
        }


class MockLLMCartoesSucesso:
    """Simula resposta válida do juiz na Passagem 2 com detecção de vazamento."""
    disponivel = True
    offline = False

    def json(self, agente: str, sistema: str, usuario: str, esquema: dict, **kwargs) -> dict:
        return {
            "afirmacoes": [
                {
                    "cartao": "A",
                    "trecho": "Bar aconchegante com opções de petiscos",
                    "justificativa": "Coerente com a descrição do documento oficial.",
                    "veredito": "confere",
                },
                {
                    "cartao": "B",
                    "trecho": "Fica perto de quem sai de Taguatinga",
                    "justificativa": "Contém insinuação de ponto de partida individual.",
                    "veredito": "confere",
                },
            ],
            "exposicoes": [
                {
                    "cartao": "B",
                    "trecho": "quem sai de Taguatinga",
                    "o_que_expoe": "origem",
                }
            ],
        }


class MockLLMFalha:
    """Simula erro na API OpenRouter (ex: timeout ou quota)."""
    disponivel = True
    offline = False

    def json(self, agente: str, sistema: str, usuario: str, esquema: dict, **kwargs) -> dict:
        raise ErroLLM("HTTP 503: Service Unavailable")


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------

@pytest.fixture
def base_docs_mock() -> dict[str, dict]:
    return {
        "lugar_01": {
            "id": "lugar_01",
            "nome": "Café das Flores",
            "tipo_de_role": "Cafeteria / Doceria",
            "regiao_administrativa": "Asa Norte",
            "endereco_completo": "CLN 110 Bloco A",
            "horario_funcionamento": "Segunda a sábado: 08h as 20h",
            "custo_medio_rs": 35.0,
            "resumo_sensorial": "Cafeteria intimista cercada de plantas e flores naturais com bolos artesanais.",
            "legenda_original": "O melhor café com tortas da Asa Norte! Ambiente floral maravilhoso.",
            "transcricao_audio_whisper": "Aqui no Café das Flores o atendimento é excelente e tem opções sem glúten.",
        },
        "lugar_02": {
            "id": "lugar_02",
            "nome": "Parrilla dos Pampas",
            "tipo_de_role": "Restaurante de Carnes",
            "regiao_administrativa": "Guará",
            "endereco_completo": "QE 15 Guará II",
            "horario_funcionamento": "Terca a domingo: 12h as 23h",
            "custo_medio_rs": 85.0,
            "resumo_sensorial": "Cortes nobres preparados na brasa com cortes argentinos tradicionais.",
            "legenda_original": "Rodízio de carnes nobres e churrasco de primeira qualidade.",
            "transcricao_audio_whisper": "Ambiente movimentado para carnívoros exigentes.",
        },
    }


# -----------------------------------------------------------------------------
# Testes Passagem 1: Auditoria da Pesquisa (RNF-03)
# -----------------------------------------------------------------------------

def test_passagem1_aprova_quando_trecho_confere_na_base(base_docs_mock):
    """Cenário 1: Trecho literal e motivo coerentes recebem veredito 'confere' no fallback."""
    candidatos = [
        Candidato(
            id="lugar_01",
            motivo="Cafeteria com ambiente floral e agradável",
            trecho="Ambiente floral maravilhoso",
        )
    ]
    resultado, usou_llm = julgar_parecer_pesquisa(
        candidatos,
        documentos=base_docs_mock,
        llm=None,
        devolver_status=True,
    )
    assert usou_llm is False
    assert len(resultado.afirmacoes) == 1
    assert resultado.afirmacoes[0].id == "lugar_01"
    assert resultado.afirmacoes[0].veredito == "confere"


def test_passagem1_marca_sem_apoio_quando_local_inexistente(base_docs_mock):
    """Cenário 2: Local inventado que não está na base 2FA recebe 'sem_apoio'."""
    candidatos = [
        Candidato(
            id="lugar_fantasma_99",
            motivo="Pizzaria no espaço sideral",
            trecho="Pizzas de outro planeta",
        )
    ]
    resultado = julgar_parecer_pesquisa(candidatos, documentos=base_docs_mock, llm=None)
    assert len(resultado.afirmacoes) == 1
    assert resultado.afirmacoes[0].id == "lugar_fantasma_99"
    assert resultado.afirmacoes[0].veredito == "sem_apoio"


def test_passagem1_marca_contradiz_quando_cita_cidade_fora_do_df(base_docs_mock):
    """Cenário 3: Citar localização fora do DF (ex: São Paulo) configura contradição direta."""
    candidatos = [
        Candidato(
            id="lugar_01",
            motivo="Unidade maravilhosa em São Paulo com comida típica",
            trecho="Melhor restaurante de São Paulo",
        )
    ]
    resultado = julgar_parecer_pesquisa(candidatos, documentos=base_docs_mock, llm=None)
    assert len(resultado.afirmacoes) == 1
    assert resultado.afirmacoes[0].veredito == "contradiz"


def test_passagem1_marca_sem_apoio_quando_trecho_nao_consta_no_documento(base_docs_mock):
    """Cenário 4: Trecho ou atração que não consta no documento do local recebe 'sem_apoio'."""
    candidatos = [
        Candidato(
            id="lugar_01",
            motivo="Espaço com piscina de bolinhas e pista de dança eletrônica",
            trecho="Pista de dança eletrônica com DJ residente até as 5h",
        )
    ]
    resultado = julgar_parecer_pesquisa(candidatos, documentos=base_docs_mock, llm=None)
    assert len(resultado.afirmacoes) == 1
    assert resultado.afirmacoes[0].veredito == "sem_apoio"


def test_passagem1_executa_com_mock_llm(base_docs_mock):
    """Cenário 5: Execução via LLM auditando múltiplos candidatos com esquema estrito."""
    candidatos = [
        Candidato(id="cand_1", motivo="Café calmo", trecho="Café com bolos"),
        Candidato(id="cand_alucinado", motivo="Deck no lago", trecho="Deck com vista para o mar"),
    ]
    resultado, usou_llm = julgar_parecer_pesquisa(
        candidatos,
        documentos=base_docs_mock,
        llm=MockLLMParecerSucesso(),
        devolver_status=True,
    )
    assert usou_llm is True
    assert len(resultado.afirmacoes) == 2
    assert resultado.afirmacoes[0].veredito == "confere"
    assert resultado.afirmacoes[1].veredito == "sem_apoio"


def test_passagem1_ativa_fallback_gracioso_quando_llm_falha(base_docs_mock):
    """Cenário 6: Se a LLM levantar exceção, fallback determinístico assume sem quebrar."""
    candidatos = [
        Candidato(
            id="lugar_01",
            motivo="Cafeteria floral intimista",
            trecho="Ambiente floral maravilhoso",
        )
    ]
    resultado, usou_llm = julgar_parecer_pesquisa(
        candidatos,
        documentos=base_docs_mock,
        llm=MockLLMFalha(),
        devolver_status=True,
    )
    assert usou_llm is False
    assert len(resultado.afirmacoes) == 1
    assert resultado.afirmacoes[0].veredito == "confere"


# -----------------------------------------------------------------------------
# Testes Passagem 2: Auditoria da Comunicação e Prevenção de PII (RNF-02)
# -----------------------------------------------------------------------------

def test_passagem2_aprova_cartao_limpo_sem_vazamento(base_docs_mock):
    """Cenário 7: Cartão sem menção a dados individuais passa limpo sem exposições."""
    cartoes = [
        CartaoTexto(
            id="A",
            titulo="Café Floral Aconchegante",
            resumo_acesso="Fica na Asa Norte, localização central e tranquila para o grupo.",
            por_que_combina="Ambiente repleto de flores e doces artesanais, ideal para conversar.",
        )
    ]
    fatos = [{"id": "A", "lugar_id": "lugar_01", "nome": "Café das Flores"}]

    resultado, usou_llm = julgar_cartoes_comunicacao(
        cartoes,
        fatos=fatos,
        documentos=base_docs_mock,
        llm=None,
        devolver_status=True,
    )
    assert usou_llm is False
    assert len(resultado.exposicoes) == 0
    assert len(resultado.afirmacoes) == 1
    assert resultado.afirmacoes[0].veredito == "confere"


def test_passagem2_detecta_vazamento_de_origem(base_docs_mock):
    """Cenário 8: Menção a ponto de partida de membro é detectada como exposição de 'origem'."""
    cartoes = [
        CartaoTexto(
            id="A",
            titulo="Café Central",
            resumo_acesso="Excelente opção para quem sai de Taguatinga e quer fugir do trânsito.",
            por_que_combina="Café muito agradável.",
        )
    ]
    resultado = julgar_cartoes_comunicacao(cartoes, documentos=base_docs_mock, llm=None)
    assert len(resultado.exposicoes) == 1
    assert resultado.exposicoes[0].cartao == "A"
    assert resultado.exposicoes[0].o_que_expoe == "origem"
    assert "quem sai de Taguatinga" in resultado.exposicoes[0].trecho


def test_passagem2_detecta_vazamento_de_orcamento(base_docs_mock):
    """Cenário 9: Menção a teto individual ou valores em reais é detectada como 'orcamento'."""
    cartoes = [
        CartaoTexto(
            id="B",
            titulo="Churrasco Completo",
            resumo_acesso="Fácil acesso.",
            por_que_combina="Perfeito porque cabe no teto individual de R$ 50 do nosso amigo.",
        )
    ]
    resultado = julgar_cartoes_comunicacao(cartoes, documentos=base_docs_mock, llm=None)
    assert len(resultado.exposicoes) >= 1
    exposicao_orcamento = next((e for e in resultado.exposicoes if e.o_que_expoe == "orcamento"), None)
    assert exposicao_orcamento is not None
    assert exposicao_orcamento.cartao == "B"


def test_passagem2_detecta_vazamento_de_restricao_individual(base_docs_mock):
    """Cenário 10: Menção atribuída a restrição de membro individual é detectada como 'restricao'."""
    cartoes = [
        CartaoTexto(
            id="C",
            titulo="Opção Saudável",
            resumo_acesso="Localizado na Asa Norte.",
            por_que_combina="Pensado especialmente já que o amigo do grupo é vegetariano.",
        )
    ]
    resultado = julgar_cartoes_comunicacao(cartoes, documentos=base_docs_mock, llm=None)
    assert len(resultado.exposicoes) >= 1
    exposicao_restr = next((e for e in resultado.exposicoes if e.o_que_expoe == "restricao"), None)
    assert exposicao_restr is not None
    assert exposicao_restr.cartao == "C"


def test_passagem2_detecta_vazamento_de_texto_pessoal(base_docs_mock):
    """Cenário 11: Citação explícita do pedido privado do usuário é detectada como 'texto_pessoal'."""
    cartoes = [
        CartaoTexto(
            id="D",
            titulo="Bar Animado",
            resumo_acesso="Acesso rápido.",
            por_que_combina="Exatamente como você pediu no chat 'quero um lugar com música alta'.",
        )
    ]
    resultado = julgar_cartoes_comunicacao(cartoes, documentos=base_docs_mock, llm=None)
    assert len(resultado.exposicoes) >= 1
    exposicao_pessoal = next((e for e in resultado.exposicoes if e.o_que_expoe == "texto_pessoal"), None)
    assert exposicao_pessoal is not None
    assert exposicao_pessoal.cartao == "D"


def test_passagem2_executa_com_mock_llm(base_docs_mock):
    """Cenário 12: Execução com MockLLM na Passagem 2 detecta vazamentos semanticamente."""
    cartoes = [
        CartaoTexto(id="A", titulo="Bar", resumo_acesso="Acesso bom", por_que_combina="Combina"),
        CartaoTexto(id="B", titulo="Outro Bar", resumo_acesso="Acesso bom", por_que_combina="Combina"),
    ]
    resultado, usou_llm = julgar_cartoes_comunicacao(
        cartoes,
        documentos=base_docs_mock,
        llm=MockLLMCartoesSucesso(),
        devolver_status=True,
    )
    assert usou_llm is True
    assert len(resultado.exposicoes) == 1
    assert resultado.exposicoes[0].cartao == "B"
    assert resultado.exposicoes[0].o_que_expoe == "origem"


# -----------------------------------------------------------------------------
# Testes dos Utilitários de Grafo e Integração
# -----------------------------------------------------------------------------

def test_filtrar_candidatos_aprovados_pelo_juiz():
    """Cenário 13: Filtra candidatos aprovando apenas 'confere' e catalogando os derrubados."""
    candidatos = [
        {"id": "c1", "nome": "Local Bom"},
        {"id": "c2", "nome": "Local Alucinado"},
        {"id": "c3", "nome": "Local Contraditório"},
    ]
    julgamento = SaidaJuizParecer(
        afirmacoes=[
            AfirmacaoParecer(id="c1", justificativa="OK", veredito="confere"),
            AfirmacaoParecer(id="c2", justificativa="Inventou atração", veredito="sem_apoio"),
            AfirmacaoParecer(id="c3", justificativa="Preço divergente", veredito="contradiz"),
        ]
    )

    aprovados, derrubados = filtrar_candidatos_aprovados_pelo_juiz(candidatos, julgamento)
    assert len(aprovados) == 1
    assert aprovados[0]["id"] == "c1"
    assert sorted(derrubados) == ["c2", "c3"]


def test_avaliar_reprovacoes_cartoes():
    """Cenário 14: Gera mapa estruturado de reprovações de cartões para realimentação."""
    julgamento = SaidaJuizCartoes(
        afirmacoes=[
            AfirmacaoCartao(cartao="A", trecho="T1", justificativa="OK", veredito="confere"),
            AfirmacaoCartao(cartao="B", trecho="T2", justificativa="Falso", veredito="contradiz"),
            AfirmacaoCartao(cartao="C", trecho="T3", justificativa="Alucinado", veredito="sem_apoio"),
        ],
        exposicoes=[
            Exposicao(cartao="A", trecho="sai de Taguatinga", o_que_expoe="origem"),
            Exposicao(cartao="B", trecho="teto de R$ 50", o_que_expoe="orcamento"),
        ],
    )

    reprovacoes = avaliar_reprovacoes_cartoes(julgamento)
    assert "A" in reprovacoes
    assert "vazamento_origem" in reprovacoes["A"]

    assert "B" in reprovacoes
    assert "vazamento_orcamento" in reprovacoes["B"]
    assert "factual_contradiz" in reprovacoes["B"]

    assert "C" in reprovacoes
    assert "factual_sem_apoio" in reprovacoes["C"]


def test_obter_modelo_juiz_respeita_variavel_ambiente(monkeypatch):
    """Cenário 15: Confirma flexibilidade de troca de modelo via JUIZ_LLM_MODELO (RNF-12)."""
    monkeypatch.setenv("JUIZ_LLM_MODELO", "xiaomi/mimo-v2.6-pro")
    assert obter_modelo_juiz() == "xiaomi/mimo-v2.6-pro"

    monkeypatch.delenv("JUIZ_LLM_MODELO", raising=False)
    assert obter_modelo_juiz() == "z-ai/glm-5.3-flash"


def test_passagem1_integracao_com_base_real_2fa():
    """Cenário 16: Integração com a base oficial de 93 locais curados (banco_aprovado_2fa.json)."""
    caminho_base = Path("data/banco_aprovado_2fa.json")
    with open(caminho_base, encoding="utf-8") as f:
        lugares_reais = json.load(f)

    # Escolhe um lugar real: Cachorrão da 5
    lugar = next(l for l in lugares_reais if l["id"] == "tiktok_7676588020346309896")

    candidatos = [
        Candidato(
            id=lugar["id"],
            motivo="Lanchonete tradicional de cachorro-quente prensado na Asa Sul",
            trecho=lugar["legenda_original"][:50],
        )
    ]

    resultado = julgar_parecer_pesquisa(candidatos, base_completa={l["id"]: l for l in lugares_reais}, llm=None)
    assert len(resultado.afirmacoes) == 1
    assert resultado.afirmacoes[0].id == lugar["id"]
    assert resultado.afirmacoes[0].veredito == "confere"
