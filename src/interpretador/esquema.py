"""Esquemas do interpretador (ADR 0007).

- `SaidaLLM`: o que o LLM preenche. Vocabulário fechado, valores como trecho literal, nenhuma data absoluta.
- `Intencao` e `Interpretacao`: o resultado depois do código (datas resolvidas, valores convertidos, destino).
"""
from dataclasses import asdict, dataclass, field
from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .contrato import Atributo, ConsultaBusca

from .tempo import FICHAS_DIA, JanelaResolvida

TipoIntencao = Literal["pedido_role", "disponibilidade", "orcamento", "gasto", "busca_lugar", "outra"]
TipoRoleLLM = Literal["comer_beber", "ar_livre_gratuito", "local_evento", "em_casa"]
Periodo = Literal["manha", "tarde", "noite", "dia_todo"]
TIPOS: tuple[str, ...] = TipoIntencao.__args__
ATRIBUTOS: tuple[str, ...] = Atributo.__args__


class JanelaLLM(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dias: list[str] = Field(default_factory=list)
    proxima_semana: bool = False
    periodo: Periodo | None = None
    apos: str | None = Field(None, pattern=r"^\d{1,2}:\d{2}$")
    ate: str | None = Field(None, pattern=r"^\d{1,2}:\d{2}$")
    disponivel: bool = True


class IntencaoLLM(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tipo: TipoIntencao
    trecho: str = ""
    janelas: list[JanelaLLM] = Field(default_factory=list)
    valor: str | None = None
    pagador: str | None = None
    descricao: str | None = None
    convidados: list[str] = Field(default_factory=list)
    tipo_role: TipoRoleLLM | None = None
    lugares: list[str] = Field(default_factory=list)
    exigir: list[Atributo] = Field(default_factory=list)
    texto_busca: str | None = None


class SaidaLLM(BaseModel):
    model_config = ConfigDict(extra="forbid")
    intencoes: list[IntencaoLLM] = Field(min_length=1, max_length=6)


def _anulavel(tipo: str, enum=None, **extra) -> dict:
    d = {"type": [tipo, "null"], **extra}
    if enum:
        d["enum"] = list(enum) + [None]
    return d


def schema_llm() -> dict:
    """JSON Schema estrito (todas as chaves obrigatórias, nada além delas) para response_format."""
    janela = {
        "type": "object", "additionalProperties": False,
        "properties": {
            "dias": {"type": "array", "items": {"type": "string"},
                     "description": f"fichas: {', '.join(FICHAS_DIA)}, 'dd' ou 'dd/mm'"},
            "proxima_semana": {"type": "boolean"},
            "periodo": _anulavel("string", Periodo.__args__),
            "apos": _anulavel("string", description="HH:MM"),
            "ate": _anulavel("string", description="HH:MM"),
            "disponivel": {"type": "boolean"},
        },
    }
    janela["required"] = list(janela["properties"])
    intencao = {
        "type": "object", "additionalProperties": False,
        "properties": {
            "tipo": {"type": "string", "enum": list(TIPOS)},
            "trecho": {"type": "string"},
            "janelas": {"type": "array", "items": janela},
            "valor": _anulavel("string", description="trecho literal do valor em reais"),
            "pagador": _anulavel("string", description="'eu' ou marcador @mN"),
            "descricao": _anulavel("string"),
            "convidados": {"type": "array", "items": {"type": "string"}},
            "tipo_role": _anulavel("string", TipoRoleLLM.__args__),
            "lugares": {"type": "array", "items": {"type": "string"}},
            "exigir": {"type": "array", "items": {"type": "string", "enum": list(ATRIBUTOS)}},
            "texto_busca": _anulavel("string"),
        },
    }
    intencao["required"] = list(intencao["properties"])
    return {"type": "object", "additionalProperties": False, "required": ["intencoes"],
            "properties": {"intencoes": {"type": "array", "items": intencao}}}


Destino = Literal["mediador", "agente_membro", "financas", "base", "conversa", "ignorado", "nenhum"]


@dataclass
class Intencao:
    tipo: str
    destino: str
    trecho: str = ""
    requer_confirmacao: bool = False
    confirmacao: str | None = None          # frase montada por código ("sex 06/11, 19h–24h. Está certo?")
    confirmar_com: str | None = None        # outra pessoa que precisa confirmar (gasto lançado por terceiro)
    pergunta: str | None = None             # quando falta algo ou é ambíguo
    motivo_pergunta: str | None = None      # falta_dia, falta_valor, valor_invalido, dia_invalido, horario_invalido
    janelas: list[JanelaResolvida] = field(default_factory=list)
    valor: Decimal | None = None
    pagador: str | None = None
    descricao: str | None = None
    tipo_role: str | None = None
    convidados: list[str] = field(default_factory=list)
    periodo_de: date | None = None
    periodo_ate: date | None = None
    consulta: ConsultaBusca | None = None


@dataclass
class Interpretacao:
    mensagem: str
    contexto: str
    origem: str
    intencoes: list[Intencao]
    modelo: str | None = None
    latencia_s: float | None = None
    tokens_entrada: int | None = None
    tokens_saida: int | None = None
    custo_usd: float | None = None
    erro: str | None = None

    def para_json(self) -> dict:
        d = asdict(self)
        for i, it in zip(d["intencoes"], self.intencoes):
            i["consulta"] = it.consulta.model_dump(mode="json") if it.consulta else None
        return d
