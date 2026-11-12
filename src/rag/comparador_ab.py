"""Motor da comparação A/B da semana 3 (issue #34): a mesma pergunta no Modo A e no Modo B, lado a lado.

- **Modo A** (`modo_a_llm_pura`): DeepSeek V4.1 Flash sem nenhum documento (`src/rag/llm_pura.py`, ADR 0010).
- **Modo B** (`modo_b_rag`): recuperação na base de 93 lugares com os guardrails da issue #33
  (`recuperar_com_guardrails`) e o mesmo modelo gerando a resposta só com os lugares recuperados
  (`src/rag/llm_rag.py`).

Os dois modos rodam em paralelo; a latência de cada um é medida separadamente (RNF-14). Quando a pergunta vem
do golden dataset (`data/golden_dataset_semana3.json`, issues #31 e #32), o resultado traz o gabarito do caso
para o avaliador da issue #36 e o benchmark da issue #38.

    from src.rag.comparador_ab import executar_comparacao_ab
    r = executar_comparacao_ab("", id_golden="golden_01")
    r["modo_a_llm_pura"]["resposta"], r["modo_b_rag"]["fontes_utilizadas"], r["gabarito"]

Notas e taxas de alucinação não são calculadas aqui: isso é do avaliador (issue #36).
"""
from __future__ import annotations

import contextvars
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from src.rag import llm_pura, llm_rag
from src.rag.llm_pura import gerar_resposta_llm_pura

RAIZ = Path(__file__).resolve().parents[2]
CAMINHO_GOLDEN = RAIZ / "data" / "golden_dataset_semana3.json"
TOP_K = 3
TAMANHO_MAXIMO_PERGUNTA = 500
CAMPOS_GABARITO = ("categoria", "ra_esperada", "locais_gabarito", "preco_maximo_gabarito", "horario_gabarito")


class ErroComparativo(ValueError):
    """Entrada inválida. `status` é o código HTTP que a rota devolve."""

    def __init__(self, mensagem: str, status: int = 422):
        super().__init__(mensagem)
        self.status = status


def carregar_golden(caminho: Path | str | None = None) -> list[dict]:
    """Casos do golden dataset; lista vazia se o arquivo ainda não existir."""
    caminho = Path(caminho) if caminho else CAMINHO_GOLDEN
    if not caminho.is_file():
        return []
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    return dados if isinstance(dados, list) else []


def listar_golden(caminho: Path | str | None = None) -> list[dict]:
    """Perguntas disponíveis para o seletor da interface (issue #37), sem o gabarito."""
    return [{"id": c.get("id"), "pergunta": c.get("pergunta"), "categoria": c.get("categoria")}
            for c in carregar_golden(caminho)]


def obter_caso_golden(id_golden: str, caminho: Path | str | None = None) -> dict | None:
    return next((c for c in carregar_golden(caminho) if c.get("id") == id_golden), None)


def _resolver_pergunta(pergunta: str | None, id_golden: str | None) -> tuple[str, dict | None]:
    pergunta = (pergunta or "").strip()
    id_golden = (id_golden or "").strip() or None
    caso = None
    if id_golden:
        caso = obter_caso_golden(id_golden)
        if caso is None:
            raise ErroComparativo(f"Caso {id_golden!r} não existe no golden dataset.", status=404)
        do_golden = (caso.get("pergunta") or "").strip()
        if pergunta and pergunta != do_golden:
            raise ErroComparativo(
                f"A pergunta enviada é diferente da do caso {id_golden}. Envie só o id_golden, ou a pergunta "
                "sem id_golden, para o gabarito não ser aplicado à pergunta errada.")
        pergunta = do_golden
    if not pergunta:
        raise ErroComparativo("Envie uma pergunta ou um id_golden.")
    if len(pergunta) > TAMANHO_MAXIMO_PERGUNTA:
        raise ErroComparativo(f"A pergunta passa de {TAMANHO_MAXIMO_PERGUNTA} caracteres.")
    return pergunta, caso


def _gabarito(caso: dict | None) -> dict | None:
    return {campo: caso.get(campo) for campo in CAMPOS_GABARITO} if caso else None


def _resumo_modo(r: dict) -> dict:
    """Campos do contrato (issue #34) mais os que o avaliador precisa para separar falha de resposta."""
    return {
        "resposta": r["resposta"],
        "fontes_utilizadas": r["fontes_utilizadas"],
        "latencia_ms": r["latencia_ms"],
        "tokens_total": r["tokens_total"],
        "custo_estimado_brl": r["custo_estimado_brl"],
        "modelo": r["modelo"],
        "disponivel": r["disponivel"],
        "cache_hit": r["cache_hit"],
        "erro": r["erro"],
        "raciocinio": r.get("raciocinio"),
        "tokens_raciocinio": r.get("tokens_raciocinio", 0),
    }


def _executar_modo_b(pergunta: str, *, top_k: int, usar_cache: bool, registrar: bool, sessao,
                     raciocinio: str | None = None, busca: str = "lexica") -> dict:
    from src.telemetria.telemetria import recuperar_com_guardrails

    t0 = time.perf_counter()
    guard, lugares = recuperar_com_guardrails(pergunta, top_k=top_k, busca=busca)
    ms_recuperacao = (time.perf_counter() - t0) * 1000  # inclui o embedding da pergunta, se houver
    r = llm_rag.gerar_resposta_rag(pergunta, lugares, avisos=guard.avisos, usar_cache=usar_cache, registrar=registrar,
                                   sessao=sessao, raciocinio=raciocinio)
    resumo = _resumo_modo(r)
    resumo["latencia_ms"] = round(ms_recuperacao + r["latencia_ms"], 1)  # recuperação + geração
    resumo["custo_estimado_brl"] = round(r["custo_estimado_brl"] + guard.embedding_custo_usd * llm_pura.COTACAO_USD_BRL, 6)
    resumo["busca"] = guard.busca
    resumo["guardrails"] = guard.para_json()
    return resumo


def _url_trace() -> str | None:
    """Link do trace no Langfuse, só quando há chaves configuradas (sem chaves, não existe trace para abrir)."""
    if not (os.environ.get("LANGFUSE_PUBLIC_KEY") and os.environ.get("LANGFUSE_SECRET_KEY")):
        return None
    try:
        from src.telemetria.telemetria import obter_cliente

        cliente = obter_cliente()
        if not cliente.get_current_trace_id():
            return None
        cliente.set_current_trace_as_public()
        return cliente.get_trace_url()
    except Exception:
        return None


def executar_comparacao_ab(pergunta: str | None, id_golden: str | None = None, *, top_k: int = TOP_K,
                           usar_cache: bool = True, registrar: bool = True, sessao=None,
                           raciocinio: str | None = None, busca: str = "lexica") -> dict:
    """Roda a pergunta nos dois modos e devolve o contrato JSON da issue #34.

    Com `id_golden`, a pergunta vem do golden dataset e o resultado traz o `gabarito`; sem ele, `gabarito` é
    None. Lança `ErroComparativo` para entrada inválida (sem pergunta, caso inexistente, pergunta diferente da
    do caso). `usar_cache`, `registrar`, `sessao` e `raciocinio` são repassados aos dois modos (ver
    `gerar_resposta_llm_pura`); `raciocinio="high"` liga o raciocínio do modelo nos dois, para a comparação
    continuar com o mesmo modelo e a mesma configuração dos dois lados. `busca` ("lexica", "vetorial" ou
    "hibrida") vale só para o Modo B; sem embedding disponível, ele volta para a léxica e `modo_b_rag.busca`
    diz qual rodou.
    """
    pergunta, caso = _resolver_pergunta(pergunta, id_golden)
    from src.telemetria.telemetria import BUSCAS

    if busca not in BUSCAS:
        raise ErroComparativo(f"busca deve ser um de {BUSCAS}.")
    try:
        llm_pura._nivel(raciocinio)
    except ValueError as e:
        raise ErroComparativo(str(e)) from None
    sessao_a = sessao_b = sessao
    if sessao is None:
        import requests

        sessao_a, sessao_b = requests.Session(), requests.Session()

    # Cada modo roda numa cópia do contexto atual, para os dois spans entrarem no mesmo trace do Langfuse.
    with ThreadPoolExecutor(max_workers=2) as executor:
        futuro_a = executor.submit(contextvars.copy_context().run, gerar_resposta_llm_pura, pergunta,
                                   usar_cache=usar_cache, registrar=registrar, sessao=sessao_a, raciocinio=raciocinio)
        futuro_b = executor.submit(contextvars.copy_context().run, _executar_modo_b, pergunta, top_k=top_k,
                                   usar_cache=usar_cache, registrar=registrar, sessao=sessao_b, raciocinio=raciocinio,
                                   busca=busca)
        modo_a, modo_b = _resumo_modo(futuro_a.result()), futuro_b.result()

    try:
        from src.telemetria.telemetria import obter_cliente

        obter_cliente().update_current_span(
            input=pergunta,
            output={"modo_a_resposta": modo_a.get("resposta"), "modo_b_resposta": modo_b.get("resposta")},
            metadata={"id_golden": caso.get("id") if caso else None, "busca": busca},
        )
    except Exception:
        pass

    modo_b["trace_url"] = _url_trace()
    return {
        "id_golden": caso.get("id") if caso else None,
        "pergunta": pergunta,
        "gabarito": _gabarito(caso),
        "modelo": llm_pura._modelo(),
        "configuracao": {"raciocinio": llm_pura._nivel(raciocinio) or "desligado", "busca": busca},
        "versao_prompt": {"modo_a": llm_pura.VERSAO_PROMPT, "modo_b": llm_rag.VERSAO_PROMPT},
        "modo_a_llm_pura": modo_a,
        "modo_b_rag": modo_b,
    }


try:  # um trace por comparação no Langfuse, com os dois modos dentro
    from langfuse import observe

    executar_comparacao_ab = observe(name="comparativo_ab")(executar_comparacao_ab)
except Exception:  # pragma: no cover
    pass
