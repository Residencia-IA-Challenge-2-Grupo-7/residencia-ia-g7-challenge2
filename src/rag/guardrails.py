"""Guardrails determinísticos do Modo B (RAG) — issue #33, RNF-03, RNF-04 e RNF-05.

Tudo em Python puro, antes e depois da recuperação; nenhuma decisão aqui passa pelo LLM.

| Guardrail | Quando                                                              | O que acontece                                  |
|-----------|---------------------------------------------------------------------|-------------------------------------------------|
| 1a        | a pergunta cita um lugar fora do DF e nenhuma RA do DF              | nenhum lugar é recomendado; aviso de escopo      |
| 1b        | a maior pontuação da recuperação fica abaixo de 0,65                | nenhum lugar é recomendado; aviso de "sem lugar" |
| 2         | a pergunta traz um teto em reais ("até 30 reais") ou "grátis"       | filtro duro `custo_medio_rs <= teto` em Python   |
| 2b        | teto incompatível com o pedido ("restaurante de luxo grátis")       | aviso de conflito, sem esconder o filtro         |

O limiar de 0,65 vale sobre a pontuação que o retriever devolve (hoje a de `calcular_similaridade_leticia`,
de 0,20 a 0,98). Medido em 10/11: perguntas fora do tema da base ficam entre 0,50 e 0,56; pedidos que a base
atende ficam entre 0,80 e 0,98.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from decimal import Decimal

from src.interpretador.lugares import casar
from src.interpretador.numeros import canon, extenso_para_digitos, valor_em_reais

LIMIAR_SIMILARIDADE = 0.65
# Mesmo guardrail 1b na escala do cosseno (busca vetorial e híbrida, gemini-embedding-001). Calibrado em 12/11
# com eval/calibrar_busca.py: ver docs/experimentos/2026-11-12-busca-vetorial.md
LIMIAR_COSSENO = 0.63  # fora do tema: 0,574 a 0,624; golden do DF: 0,625 a 0,812 (margem pequena)
# Abaixo disso, "luxo" é incompatível: o lugar marcado como "Caro ($$$)" mais barato da base custa R$ 50 (10/11)
TETO_MINIMO_LUXO = Decimal("50")

# Lugares fora do DF que aparecem em perguntas. Só nomes sem ambiguidade com lugares ou restaurantes do DF
# ("Paris 6" é um bistrô na Asa Sul; "Natal" é data; "Santos" é sobrenome).
FORA_DO_DF: dict[str, str] = {
    "rio de janeiro": "Rio de Janeiro", "copacabana": "Copacabana (RJ)", "ipanema": "Ipanema (RJ)",
    "leblon": "Leblon (RJ)", "lapa carioca": "Lapa (RJ)", "niteroi": "Niterói (RJ)", "buzios": "Búzios (RJ)",
    "sao paulo": "São Paulo", "pinheiros": "Pinheiros (SP)", "vila madalena": "Vila Madalena (SP)",
    "avenida paulista": "Avenida Paulista (SP)", "campinas": "Campinas (SP)",
    "belo horizonte": "Belo Horizonte", "salvador": "Salvador", "recife": "Recife", "fortaleza": "Fortaleza",
    "curitiba": "Curitiba", "porto alegre": "Porto Alegre", "florianopolis": "Florianópolis",
    "goiania": "Goiânia", "manaus": "Manaus", "gramado": "Gramado", "pirenopolis": "Pirenópolis (GO)",
    "alto paraiso": "Alto Paraíso (GO)", "chapada dos veadeiros": "Chapada dos Veadeiros (GO)",
    # Entorno: perto, mas fora do DF e fora da base
    "valparaiso": "Valparaíso de Goiás (GO)", "aguas lindas": "Águas Lindas de Goiás (GO)",
    "luziania": "Luziânia (GO)", "formosa": "Formosa (GO)", "cidade ocidental": "Cidade Ocidental (GO)",
    "novo gama": "Novo Gama (GO)", "planaltina de goias": "Planaltina de Goiás (GO)",
    "santo antonio do descoberto": "Santo Antônio do Descoberto (GO)",
}
_MARCAS_DF = r"\b(brasilia|distrito federal|df|plano piloto|candangolandia)\b"

_RE_GRATIS = re.compile(r"\b(gratis|de graca|gratuit[oa]s?|sem gastar( nada)?|0800|free)\b")
_RE_LUXO = re.compile(r"\b(luxo|luxuos[oa]|sofisticad[oa]|requintad[oa]|chique|alta gastronomia|fine dining|premium|estrelad[oa])\b")
_RE_DINHEIRO = re.compile(r"(r\$\s*)?(\d+(?:[.,]\d{1,2})?)\s*(reais|real|conto|contos|pila|pilas|mangos?)?\b(?!\s*(?:h\b|horas?|:|min|km|pessoas|amigos))")
_GATILHO_TETO = re.compile(r"(ate|no maximo|maximo de|maximo|menos de|abaixo de|teto( de)?|limite( de)?|com|gastando|gastar|pagar|orcamento( de)?|por)\s*(r\$\s*)?$")

AVISO_FORA_DO_DF = ("A base do Orquestrador de Rolês cobre só o Distrito Federal (93 lugares verificados). "
                    "{lugares} fica fora do DF, então não vou recomendar nenhum lugar para não inventar informação. "
                    "Quer uma sugestão em alguma região do DF?")
AVISO_SIMILARIDADE = ("Não encontrei na base de 93 lugares do DF nenhum lugar que atenda bem a esse pedido "
                      "(maior aderência {score}, abaixo do mínimo de {limiar}). Para não recomendar um lugar "
                      "aleatório, prefiro não sugerir nada. Tente descrever o tipo de rolê, a região ou o clima.")
AVISO_SEM_LUGAR_NO_TETO = ("Nenhum lugar da base {cabe}: o mais barato custa, em média, {minimo}. "
                           "Quer aumentar o limite?")
AVISO_CONFLITO = ("Atenção: o pedido combina {pedido} com {teto}, o que é incompatível. O limite de preço vale "
                  "mesmo assim, então nenhum lugar sugerido será de luxo.")


@dataclass
class Guardrails:
    permitido: bool = True
    motivo: str | None = None                  # fora_do_df, similaridade_baixa, sem_lugar_no_teto
    avisos: list[str] = field(default_factory=list)
    teto: Decimal | None = None                # R$ por pessoa (0 = grátis)
    gratis: bool = False
    conflito: bool = False
    lugares_fora_df: list[str] = field(default_factory=list)
    score_maximo: float | None = None
    filtrados_por_teto: int = 0
    busca: str = "lexica"                      # lexica, vetorial ou hibrida (a que de fato rodou)
    busca_erro: str | None = None              # por que a busca pedida voltou para a léxica, se voltou
    embedding_ms: float = 0.0                  # tempo do embedding da pergunta (entra na latência do Modo B)
    embedding_custo_usd: float = 0.0

    def para_json(self) -> dict:
        d = asdict(self)
        d["teto"] = float(self.teto) if self.teto is not None else None
        return d


def _reais(v: Decimal | float) -> str:
    return "R$ " + f"{Decimal(str(v)):,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


# ---------------------------------------------------------------- guardrail 1a: escopo geográfico

def lugares_fora_do_df(pergunta: str) -> list[str]:
    """Lugares fora do DF citados, a não ser que a pergunta também cite o DF ou uma RA dele."""
    t = " " + re.sub(r"[^\w ]", " ", canon(pergunta)) + " "
    citados = [nome for chave, nome in FORA_DO_DF.items() if f" {chave} " in t]
    if not citados:
        return []
    ras, _, _ = casar([pergunta])
    # "Planaltina de Goiás" casa com a RA Planaltina; não conta como DF
    ras = [r for r in ras if not (r == "Planaltina" and "planaltina de goias" in t)]
    if ras or re.search(_MARCAS_DF, t):
        return []
    return citados


# ---------------------------------------------------------------- guardrail 2: teto em reais

def extrair_teto(pergunta: str) -> tuple[Decimal | None, bool]:
    """(teto em R$, é grátis?). 'até 30 reais' -> 30; 'no máximo R$ 45,50' -> 45.50; 'grátis' -> 0.

    Só vale como teto um número com cara de dinheiro (R$ antes ou reais/conto depois) e precedido de
    "até", "no máximo", "menos de", "gastando", "com"… — "até as 22h" e "até 5 pessoas" não contam.
    """
    t = extenso_para_digitos(canon(pergunta))
    if _RE_GRATIS.search(t):
        return Decimal("0"), True
    for m in _RE_DINHEIRO.finditer(t):
        if not (m.group(1) or m.group(3)):
            continue
        if not _GATILHO_TETO.search(t[max(0, m.start() - 25):m.start()] + (m.group(1) or "")):
            continue
        v = valor_em_reais(m.group(0))
        if v is not None:
            return v, False
    return None, False


def filtrar_por_teto(lugares: list[dict], teto: Decimal | None) -> list[dict]:
    """Filtro duro do RNF-04: `custo_medio_rs <= teto`. Lugar sem custo informado sai quando há teto."""
    if teto is None:
        return list(lugares)
    return [x for x in lugares
            if x.get("custo_medio_rs") is not None and Decimal(str(x["custo_medio_rs"])) <= teto]


# ---------------------------------------------------------------- avaliação antes e depois da recuperação

def avaliar_pergunta(pergunta: str) -> Guardrails:
    """Antes da recuperação: escopo geográfico, teto e conflito."""
    g = Guardrails()
    fora = lugares_fora_do_df(pergunta)
    if fora:
        g.permitido, g.motivo, g.lugares_fora_df = False, "fora_do_df", fora
        g.avisos.append(AVISO_FORA_DO_DF.format(lugares=" e ".join(fora)))
        return g
    g.teto, g.gratis = extrair_teto(pergunta)
    luxo = _RE_LUXO.search(canon(pergunta))
    if luxo and g.teto is not None and g.teto < TETO_MINIMO_LUXO:
        g.conflito = True
        g.avisos.append(AVISO_CONFLITO.format(pedido=f"\"{luxo.group(0)}\"",
                                              teto="\"grátis\"" if g.gratis else f"um teto de {_reais(g.teto)}"))
    return g


def aplicar_teto(g: Guardrails, lugares: list[dict]) -> list[dict]:
    """Aplica o filtro de teto e, se nada sobrar, bloqueia com o aviso de "sem lugar no teto"."""
    filtrados = filtrar_por_teto(lugares, g.teto)
    g.filtrados_por_teto = len(lugares) - len(filtrados)
    if g.teto is not None and not filtrados and lugares:
        minimo = min(Decimal(str(x["custo_medio_rs"])) for x in lugares if x.get("custo_medio_rs") is not None)
        g.permitido, g.motivo = False, "sem_lugar_no_teto"
        g.avisos.append(AVISO_SEM_LUGAR_NO_TETO.format(cabe="é grátis" if g.gratis else f"cabe em até {_reais(g.teto)}",
                                                       minimo=_reais(minimo)))
    return filtrados


def avaliar_recuperacao(g: Guardrails, scores: list[float], limiar: float = LIMIAR_SIMILARIDADE) -> Guardrails:
    """Depois da recuperação: se o melhor resultado não chega ao limiar, nada é recomendado."""
    g.score_maximo = max(scores) if scores else None
    if g.permitido and (g.score_maximo is None or g.score_maximo < limiar):
        g.permitido, g.motivo = False, "similaridade_baixa"
        g.avisos.append(AVISO_SIMILARIDADE.format(score=f"{g.score_maximo or 0.0:.2f}".replace(".", ","),
                                                   limiar=f"{limiar:.2f}".replace(".", ",")))
    return g
