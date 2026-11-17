"""Contratos entre os agentes da semana 4 (ADR 0015, docs/entregas/semana-04/PLANO_AGENTES.md).

Dois lados:

- **Cofre** (dataclasses): o que só o servidor vê. Os 4 campos interpretados de cada membro, com teto e origem,
  as janelas comuns com quem pode em cada uma e o log pessoal. Os nós de código (Logística, vetos da Validação)
  leem o cofre; os agentes LLM nunca o recebem (RNF-02).
- **Mensagens** (Pydantic): o que passa de um agente a outro no estado do grafo. Nenhuma tem nome, teto ou origem.
  As saídas dos LLMs são validadas por estes modelos, e `esquema_estrito` gera o JSON Schema da chamada.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from src.interpretador.campos import PerfilInterpretado
from src.salas.janelas import JanelaComum

TipoRole = Literal["comer_beber", "ar_livre_gratuito", "local_evento"]
Restricao = Literal["alim_vegetariano", "alim_vegano", "alim_sem_gluten", "alim_sem_lactose",
                    "acess_entrada_sem_degrau"]
Aspecto = Literal["barulho", "lotacao", "preco", "distancia", "transporte_publico", "transporte_app", "ar_livre",
                  "comida", "musica_ao_vivo", "lugar_calmo", "atendimento"]
MotivoVeto = Literal["horario", "orcamento", "restricao", "encerrado", "deslocamento"]


# ------------------------------------------------------------------ cofre (só o servidor)

@dataclass
class Membro:
    id: str                       # marcador da sala: "m1", "m2"... (pseudonimo.py)
    usuario: str                  # id pseudônimo permanente, chave do log pessoal
    nome: str                     # segredo: nunca vai a um LLM
    perfil: PerfilInterpretado    # segredo: tem teto e origem


@dataclass
class Cofre:
    membros: dict[str, Membro]
    janelas: list[JanelaComum]
    agora: datetime
    lugares: dict[str, dict]                                  # base de 93 por id
    store: object                                             # BaseStore do LangGraph (log pessoal)
    perfis_efetivos: dict[str, PerfilInterpretado] = field(default_factory=dict)  # 4 campos + log
    analises: dict[str, dict] = field(default_factory=dict)   # Logística: deslocamento de cada um por lugar
    sugestoes: list = field(default_factory=list)             # Sugestao, com o custo de cada um
    sala_id: str = ""                                         # código da sala (vai para o estado público)

    def nomes(self) -> list[str]:
        return [m.nome for m in self.membros.values()]


# ------------------------------------------------------------------ mensagens entre agentes

class _M(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PerfilAnonimoMembro(_M):
    """O que o Agente Pessoal de um membro repassa ao grupo: sem nome, id, teto ou origem."""
    tipos: list[str]
    vibes: list[str]
    evitar: list[str]
    restricoes: list[str]
    transporte: list[str]
    trecho_pedido: str
    itens_do_log_usados: int


class Consulta(_M):
    texto: str = Field(min_length=1, max_length=300)
    tipos_role: list[TipoRole]
    exigir: list[Restricao]
    ras: list[str]


class SaidaPlanejar(_M):
    consultas: list[Consulta] = Field(min_length=1, max_length=3)
    raciocinio: str


class Candidato(_M):
    id: str
    motivo: str
    trecho: str


class SaidaSelecionar(_M):
    candidatos: list[Candidato]
    observacao: str


class AfirmacaoParecer(_M):
    id: str
    justificativa: str
    veredito: Literal["confere", "contradiz", "sem_apoio"]


class SaidaJuizParecer(_M):
    afirmacoes: list[AfirmacaoParecer]


class CartaoTexto(_M):
    id: str
    titulo: str
    resumo_acesso: str
    por_que_combina: str


class SaidaComunicacao(_M):
    cartoes: list[CartaoTexto]


class AfirmacaoCartao(_M):
    cartao: str
    trecho: str
    justificativa: str
    veredito: Literal["confere", "contradiz", "sem_apoio"]


class Exposicao(_M):
    cartao: str
    trecho: str
    o_que_expoe: Literal["origem", "orcamento", "restricao", "texto_pessoal"]


class SaidaJuizCartoes(_M):
    afirmacoes: list[AfirmacaoCartao]
    exposicoes: list[Exposicao]


class ItemPreferencia(_M):
    aspecto: Aspecto
    sentido: Literal["gosta", "evita"]
    trecho: str


class ItemRestricao(_M):
    tipo: Restricao
    trecho: str


class AtualizacaoLog(_M):
    preferencias: list[ItemPreferencia]
    restricoes: list[ItemRestricao]
    frase_de_confirmacao: str
    tentativa_de_instrucao: bool


def esquema_estrito(modelo: type[BaseModel]) -> dict:
    """JSON Schema para `response_format` estrito: sem $ref, sem títulos e padrões, todos os campos exigidos e
    `additionalProperties: false` (o que os provedores da OpenRouter aceitam com `require_parameters`)."""
    bruto = modelo.model_json_schema()
    defs = bruto.pop("$defs", {})

    def limpar(no):
        if isinstance(no, dict):
            if "$ref" in no:
                return limpar(copy.deepcopy(defs[no["$ref"].split("/")[-1]]))
            no = {k: limpar(v) for k, v in no.items() if k not in ("title", "default", "description")}
            if no.get("type") == "object":
                no["additionalProperties"] = False
                no["required"] = list(no.get("properties", {}))
            for k in ("minLength", "maxLength", "minItems", "maxItems"):
                no.pop(k, None)  # a validação de tamanho fica no Pydantic
            return no
        if isinstance(no, list):
            return [limpar(x) for x in no]
        return no

    return limpar(bruto)
