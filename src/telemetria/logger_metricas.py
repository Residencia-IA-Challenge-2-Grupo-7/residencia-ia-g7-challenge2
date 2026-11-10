"""
Módulo de Telemetria e Registro Estruturado de Métricas (LLMOps)
Projeto: Orquestrador de Rolês - Grupo 7 (Residência em IA | Instituto Eldorado & UnB)
Responsável: Maria Eduarda (DevOps & LLMOps)

Requisitos Atendidos:
- RNF-01 e RNF-02 (Privacidade, LGPD e Sigilo Orçamentário):
    Mascaramento estrito de PII (CPFs, e-mails, telefones e orçamentos individuais).
- RNF-10 (Registro Estruturado para Métricas):
    Logs estruturados em JSONL com latência, tokens, modo, SLA e custos.
- RNF-14 (SLA de Desempenho):
    Validação de latência <= 5.000 ms (5 s).
- RNF-15 (Resiliência, Governança de Custos e Cache Determinístico):
    Cache determinístico via SHA-256 para evitar consumo de tokens em benchmarks repetidos.
"""

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any, Dict, Optional, Union
import uuid

# Diretório padrão para persistência de logs estruturados e cache
DIRETORIO_TELEMETRIA = Path("data/telemetria")
ARQUIVO_METRICAS_PADRAO = DIRETORIO_TELEMETRIA / "metricas_execucao.jsonl"
ARQUIVO_CACHE_PADRAO = DIRETORIO_TELEMETRIA / "cache_avaliacoes.json"

# Custo médio estimado por token para Gemini 1.5 Flash em BRL (cotação média USD/BRL ~5.80)
# Entrada: $0.075/1M tokens, Saída: $0.30/1M tokens -> Média ponderada ~0.0000009 BRL/token
FATOR_CUSTO_TOKEN_BRL = 0.0000009

# SLA de Latência estabelecido no RNF-14 (5.000 ms)
LIMITE_LATENCIA_SLA_MS = 5000.0

# Cache em memória para acesso ultra-rápido (O(1))
_MEMORIA_CACHE: Dict[str, Dict[str, Any]] = {}


def sanitizar_texto_pii(texto: Optional[str]) -> str:
    """
    Sanitiza e mascara qualquer Dado Pessoal Identificável (PII) e orçamentos
    individuais confidenciais, em conformidade estrita com a LGPD, RNF-01 e RNF-02.

    Mascara:
    - E-mails -> [EMAIL_PROTEGIDO]
    - Telefones (formatos BR com/sem DDD) -> [TELEFONE_PROTEGIDO]
    - CPFs (com/sem pontuação) -> [CPF_PROTEGIDO]
    - Orçamentos e valores privados associados a membros -> [ORCAMENTO_SIGILOSO]
    """
    if not texto:
        return ""

    limpo = str(texto)

    # 1. Mascaramento de E-mails
    regex_email = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
    limpo = re.sub(regex_email, "[EMAIL_PROTEGIDO]", limpo)

    # 2. Mascaramento de CPFs formatados (com pontuação oficial)
    regex_cpf_formatado = r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b"
    limpo = re.sub(regex_cpf_formatado, "[CPF_PROTEGIDO]", limpo)

    # 3. Mascaramento de Telefones Brasileiros (+55, DDD, celular com 9 dígitos ou fixo)
    # Cobre: (61) 98888-7777, +55 61 99123-4567, 61 3322-4455, 61987654321
    regex_telefone = (
        r"(?:\+?55\s?)?(?:\(?0?[1-9]{2}\)?[\s-]?)?(?:9\s?\d{4}|\d{4})[\s-]?\d{4}\b"
    )
    def _sub_telefone(match: re.Match) -> str:
        s = match.group(0).strip()
        num_digitos = sum(c.isdigit() for c in s)
        if 8 <= num_digitos <= 13:
            return "[TELEFONE_PROTEGIDO]"
        return s

    limpo = re.sub(regex_telefone, _sub_telefone, limpo)

    # 4. Mascaramento de CPFs não formatados (11 dígitos sequenciais restantes)
    regex_cpf_puro = r"(?<!\d)\d{11}(?!\d)"
    limpo = re.sub(regex_cpf_puro, "[CPF_PROTEGIDO]", limpo)

    # 4. Mascaramento de Orçamentos Pessoais e Valores Sigilosos (RNF-02 / ADR 0007)
    # Exemplos: "o Caio só tem 50 conto", "Rafaela: R$ 30,00", "meu orçamento é 40 reais", "posso gastar até 70"
    regex_orcamento_pessoal = (
        r"(?i)\b(?:o\s+|a\s+)?([A-ZÁÉÍÓÚÂÊÔÃÕÇ][a-záéíóúâêôãõç]+)\s+(?:só\s+tem|tem|pode\s+gastar|orçamento\s*(?:de|é)?)\s*"
        r"(?:no\s+máximo\s+|até\s+)?(?:r\$\s*|\b)\d+(?:[.,]\d{1,2})?\s*(?:reais|conto|pila)?\b"
    )
    limpo = re.sub(regex_orcamento_pessoal, "[ORCAMENTO_SIGILOSO]", limpo)

    regex_orcamento_direto = (
        r"(?i)\b(?:orçamento|orcamento|meu\s+teto|posso\s+gastar|só\s+tenho|so\s+tenho|tô\s+liso|to\s+liso)\b"
        r"[^\n\.,;]*?(?:r\$\s*|\b)\d+(?:[.,]\d{1,2})?\s*(?:reais|conto|pila)?\b"
    )
    limpo = re.sub(regex_orcamento_direto, "[ORCAMENTO_SIGILOSO]", limpo)

    return limpo


def registrar_evento_metrica(
    modo: str,
    latencia_ms: float,
    tokens_total: int = 0,
    custo_estimado_brl: Optional[float] = None,
    cache_hit: bool = False,
    consulta: Optional[str] = None,
    status_sla: Optional[str] = None,
    metadados: Optional[Dict[str, Any]] = None,
    arquivo_log: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    """
    Registra estruturadamente uma métrica de execução do sistema (RNF-10).
    Blindado contra PII e vazamentos de dados privados.

    Retorna o dicionário serializado do evento gravado.
    """
    evento_id = str(uuid.uuid4())
    timestamp_iso = datetime.now(timezone.utc).isoformat()

    modo_normalizado = str(modo).lower().strip()
    if modo_normalizado not in ["modo_a_llm_pura", "modo_b_rag"]:
        # Tolera pequenas variações de nomenclatura
        if "rag" in modo_normalizado:
            modo_normalizado = "modo_b_rag"
        elif "pura" in modo_normalizado or "llm" in modo_normalizado:
            modo_normalizado = "modo_a_llm_pura"

    latencia = max(0.0, float(latencia_ms))

    # Cálculo do status de SLA (RNF-14: <= 5.0 s)
    if status_sla is None:
        status_sla = "DENTRO_DO_SLA" if latencia <= LIMITE_LATENCIA_SLA_MS else "VIOLOU_SLA"

    # Se houve cache_hit, custo e tokens adicionais da API são 0.0
    if cache_hit:
        tokens_efetivos = 0
        custo_final = 0.0
    else:
        tokens_efetivos = max(0, int(tokens_total))
        if custo_estimado_brl is not None:
            custo_final = float(custo_estimado_brl)
        else:
            custo_final = round(tokens_efetivos * FATOR_CUSTO_TOKEN_BRL, 6)

    # Consulta sempre higienizada
    consulta_sanitizada = sanitizar_texto_pii(consulta) if consulta else None

    # Sanitização recursiva de strings nos metadados opcionais
    meta_limpo: Dict[str, Any] = {}
    if metadados and isinstance(metadados, dict):
        for k, v in metadados.items():
            if isinstance(v, str):
                meta_limpo[k] = sanitizar_texto_pii(v)
            else:
                meta_limpo[k] = v

    registro: Dict[str, Any] = {
        "evento_id": evento_id,
        "timestamp": timestamp_iso,
        "modo": modo_normalizado,
        "latencia_ms": round(latencia, 2),
        "tokens_total": tokens_efetivos,
        "custo_estimado_brl": custo_final,
        "cache_hit": bool(cache_hit),
        "status_sla": status_sla,
        "consulta_sanitizada": consulta_sanitizada,
        "metadados": meta_limpo,
    }

    # Gravação persistente em formato JSONL (JSON Lines)
    destino_log = Path(arquivo_log) if arquivo_log else ARQUIVO_METRICAS_PADRAO
    try:
        destino_log.parent.mkdir(parents=True, exist_ok=True)
        with open(destino_log, "a", encoding="utf-8") as f:
            f.write(json.dumps(registro, ensure_ascii=False) + "\n")
    except Exception as exc:
        # Falhas de I/O em disco não podem derrubar o pipeline de IA
        registro["aviso_persistencia"] = str(exc)

    return registro


# ==============================================================================
# CAMADA DE CACHE DETERMINÍSTICO (RNF-15)
# ==============================================================================

def gerar_chave_cache(consulta: str, modo: str = "modo_b_rag", parametros: Optional[Dict[str, Any]] = None) -> str:
    """
    Gera uma chave SHA-256 única e determinística a partir da consulta e modo.
    Normaliza espaços, acentos/caixa alta para maximizar reaproveitamento de chamadas idênticas.
    """
    texto_norm = " ".join(str(consulta or "").lower().split())
    modo_norm = str(modo or "").lower().strip()
    payload = f"{modo_norm}:{texto_norm}"

    if parametros:
        # Garante ordenação determinística das chaves do dicionário
        payload += ":" + json.dumps(parametros, sort_keys=True, ensure_ascii=False)

    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def obter_cache_avaliacao(
    consulta: str,
    modo: str = "modo_b_rag",
    parametros: Optional[Dict[str, Any]] = None,
    arquivo_cache: Optional[Union[str, Path]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Busca uma resposta previamente calculada no cache em memória ou em disco (RNF-15).
    Se encontrada, retorna o payload com `cache_hit=True`.
    """
    chave = gerar_chave_cache(consulta, modo, parametros)

    # 1. Consulta em memória RAM (O(1))
    if chave in _MEMORIA_CACHE:
        item = dict(_MEMORIA_CACHE[chave])
        item["cache_hit"] = True
        return item

    # 2. Consulta em arquivo JSON em disco
    destino = Path(arquivo_cache) if arquivo_cache else ARQUIVO_CACHE_PADRAO
    if destino.exists():
        try:
            with open(destino, "r", encoding="utf-8") as f:
                dados_disco = json.load(f)
                if chave in dados_disco:
                    item = dict(dados_disco[chave])
                    item["cache_hit"] = True
                    # Armazena na memória RAM para as próximas chamadas
                    _MEMORIA_CACHE[chave] = item
                    return item
        except Exception:
            pass

    return None


def salvar_cache_avaliacao(
    consulta: str,
    resposta: Any,
    modo: str = "modo_b_rag",
    tokens_total: int = 0,
    latencia_ms: float = 0.0,
    parametros: Optional[Dict[str, Any]] = None,
    metadados: Optional[Dict[str, Any]] = None,
    arquivo_cache: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    """
    Armazena deterministicamente o resultado de uma avaliação em memória e disco.
    Garante que baterias de teste subsequentes tenham custo 0 e latência desprezível.
    """
    chave = gerar_chave_cache(consulta, modo, parametros)

    item: Dict[str, Any] = {
        "chave_sha256": chave,
        "timestamp_salvamento": datetime.now(timezone.utc).isoformat(),
        "consulta_original": sanitizar_texto_pii(consulta),
        "modo": modo,
        "resposta": resposta,
        "tokens_originais": tokens_total,
        "latencia_original_ms": latencia_ms,
        "metadados": metadados or {},
    }

    # Salva em memória
    _MEMORIA_CACHE[chave] = item

    # Salva em disco
    destino = Path(arquivo_cache) if arquivo_cache else ARQUIVO_CACHE_PADRAO
    try:
        destino.parent.mkdir(parents=True, exist_ok=True)
        dados_disco: Dict[str, Any] = {}
        if destino.exists():
            try:
                with open(destino, "r", encoding="utf-8") as f:
                    dados_disco = json.load(f)
            except Exception:
                dados_disco = {}

        dados_disco[chave] = item
        with open(destino, "w", encoding="utf-8") as f:
            json.dump(dados_disco, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    return item


def limpar_cache_avaliacao(arquivo_cache: Optional[Union[str, Path]] = None) -> None:
    """Limpa o cache em memória e em disco (útil para suítes de testes isoladas)."""
    global _MEMORIA_CACHE
    _MEMORIA_CACHE.clear()

    destino = Path(arquivo_cache) if arquivo_cache else ARQUIVO_CACHE_PADRAO
    if destino.exists():
        try:
            destino.unlink()
        except Exception:
            pass
