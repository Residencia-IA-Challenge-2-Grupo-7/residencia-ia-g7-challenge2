"""Contrato tipado de busca e janelas usado pelo interpretador."""
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .lugares import ras_validas

CONTRATO_VERSAO = "1.0"

TipoRole = Literal["comer_beber", "ar_livre_gratuito", "local_evento"]
Regiao = Literal["centro", "oeste_proximo", "oeste", "sul", "norte", "leste"]
Colecao = Literal["lugares", "eventos"]
Atributo = Literal[
    "ar_livre",
    "coberto",
    "acess_entrada_sem_degrau",
    "acess_banheiro_adaptado",
    "alim_vegetariano",
    "alim_vegano",
    "alim_sem_gluten",
    "alim_sem_lactose",
]


class Janela(BaseModel):
    model_config = ConfigDict(extra="forbid")
    inicio: datetime
    fim: datetime | None = None

    @model_validator(mode="after")
    def _ordem(self):
        if self.fim is not None and self.fim <= self.inicio:
            raise ValueError("fim da janela precisa ser depois do início")
        return self


class ConsultaBusca(BaseModel):
    model_config = ConfigDict(extra="forbid")
    texto: str = Field(min_length=1, max_length=300, description="o que se quer, para a busca vetorial e textual")
    colecoes: list[Colecao] = Field(default_factory=lambda: ["lugares"], min_length=1)
    tipos_role: list[TipoRole] = Field(default_factory=list, description="vazio = todos")
    regioes: list[Regiao] = Field(default_factory=list)
    ras: list[str] = Field(default_factory=list, description="nomes das 35 RAs")
    janela: Janela | None = Field(None, description="lugar aberto no início da janela; evento começando dentro dela")
    teto_pessoa: Decimal | None = Field(None, ge=0, le=1000, description="R$ por pessoa")
    exigir: list[Atributo] = Field(default_factory=list, description="atributos que precisam ser 'sim'")
    k: int = Field(10, ge=1, le=20)

    @field_validator("ras")
    @classmethod
    def _ras(cls, v):
        validas = ras_validas()
        ruins = [r for r in v if r not in validas]
        if ruins:
            raise ValueError(f"RA desconhecida: {ruins}")
        return v


class ItemResultado(BaseModel):
    colecao: Colecao
    id: str
    nome: str
    categoria: str | None = None
    ra: str | None = None
    regiao: str | None = None
    custo_pessoa_tipico: Decimal | None = None
    taxa_entrada: Decimal | None = None
    inicio: datetime | None = None
    fonte: str | None = None
    verificado_em: date | None = None
    estado: str | None = None
    pontuacao: float


class ResultadoBusca(BaseModel):
    contrato: str = CONTRATO_VERSAO
    itens: list[ItemResultado]
    versao_base: str | None = None
    modelo_embeddings: str
    gerado_em: datetime
