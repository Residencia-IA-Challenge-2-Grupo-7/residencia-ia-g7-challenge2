"""Estado de uma sala: participantes, perfis secretos, cartões de sugestão, votos e resultado.

Mapeia as 5 tabelas do banco da Eduarda (guia oficial): `salas` (Sala), `participantes` (Participante, com o
perfil secreto), `sugestoes_role` (Sugestao), `votos` (Sala.votos) e `despesas_pos_role` (semana 5, ainda fora).

O que é segredo fica marcado no campo. Só `painel_publico()` do gerenciador monta o que o grupo vê.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from src.interpretador.campos import PerfilInterpretado
from src.salas.janelas import JanelaComum

LIMITE_PARTICIPANTES = 20  # RF-03
MINIMO_PARTICIPANTES = 2   # RF-03 e RF-05

# Situações da sala
COLETANDO = "coletando"        # recebendo os 4 campos
VOTACAO = "votacao"            # cartões gerados, votos abertos
ORQUESTRADO = "orquestrado"    # votação fechada, rolê escolhido


@dataclass
class Participante:
    id: str
    nome: str
    token_hash: str                       # segredo: só o hash do token fica guardado
    perfil: PerfilInterpretado | None     # segredo: tem o teto e a origem
    confirmado: bool = False
    criado_em: datetime | None = None


@dataclass
class Sugestao:
    id: str                               # "A", "B", "C", "D"
    posicao: int                          # lugar no ranking (1 = melhor)
    lugar_id: str
    nome: str
    tipo: str
    ra: str | None
    regiao_texto: str
    endereco: str
    inicio: datetime
    fim: datetime
    horario_texto: str
    horario_situacao: str                 # aberto, provavel ou incerto
    contagem: str                         # "4 de 5 podem"
    consumo_rs: Decimal
    gasto_min: Decimal                    # consumo + transporte, do menor ao maior (RF-15)
    gasto_max: Decimal
    tempo_medio_min: int | None
    tempo_max_min: int | None
    nota_justica: float
    pontuacao: float
    explicacao: str
    tiktok_url: str | None
    fonte: str
    vibes: list[str] = field(default_factory=list)
    por_participante: dict[str, dict] = field(default_factory=dict)  # segredo: custo e tempo de cada um

    def publico(self) -> dict:
        return {
            "id": self.id, "posicao": self.posicao, "lugar_id": self.lugar_id, "nome": self.nome, "tipo": self.tipo,
            "ra": self.ra, "regiao_administrativa": self.regiao_texto, "endereco": self.endereco,
            "inicio": self.inicio.isoformat(), "fim": self.fim.isoformat(), "horario": self.horario_texto,
            "horario_situacao": self.horario_situacao, "quantos_podem": self.contagem,
            "consumo_estimado_rs": str(self.consumo_rs),
            "faixa_gasto_rs": {"min": str(self.gasto_min), "max": str(self.gasto_max)},
            "tempo_medio_chegada_min": self.tempo_medio_min, "tempo_maximo_chegada_min": self.tempo_max_min,
            "nota_justica": self.nota_justica, "explicacao": self.explicacao, "tiktok_url": self.tiktok_url,
            "fonte": self.fonte, "vibes": self.vibes,
        }


@dataclass
class Resultado:
    sugestao_id: str
    votos: int
    desempate_por_justica: bool
    mensagem: str
    resumo_whatsapp: str
    fechado_em: datetime


@dataclass
class Sala:
    codigo: str
    nome_role: str
    organizador_nome: str
    token_organizador_hash: str
    criado_em: datetime
    status: str = COLETANDO
    participantes: dict[str, Participante] = field(default_factory=dict)
    janelas_comuns: list[JanelaComum] = field(default_factory=list)
    sugestoes: list[Sugestao] = field(default_factory=list)
    votos: dict[str, list[str]] = field(default_factory=dict)  # participante -> cartões (votação múltipla)
    resultado: Resultado | None = None
    avisos: list[str] = field(default_factory=list)

    def confirmados(self) -> list[Participante]:
        return [p for p in self.participantes.values() if p.confirmado and p.perfil is not None]
