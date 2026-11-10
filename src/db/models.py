"""
Modelos de Domínio e Validação Pydantic
Projeto: Orquestrador de Rolês - Grupo 7 (Residência em IA | UnB & Eldorado)
Responsável: Maria Eduarda (DevOps & Backend)
Issue #41 | Referência: GUIA_OFICIAL_PROJETO.md

Define os esquemas e contratos de dados para:
- Usuários e seus múltiplos endereços salvos no DF (Casa, Trabalho, UnB)
- Janelas de horário com ponto de partida associado
- Salas de rolê, cartões de sugestão, votos e divisão de conta pós-rolê (Pix)
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


# ==============================================================================
# 1. PERFIL DO USUÁRIO E ENDEREÇOS SALVOS
# ==============================================================================

class EnderecoUsuario(BaseModel):
    """Endereço salvo do usuário no DF (Casa, Trabalho, Faculdade/UnB)."""
    id: Optional[str] = None
    usuario_id: Optional[str] = None
    rotulo: str = Field(..., description="Apelido do local, ex: 'Casa', 'Trabalho', 'Faculdade/UnB'")
    regiao_ra: str = Field(..., description="Região Administrativa do DF, ex: 'Águas Claras', 'Plano Piloto'")
    ponto_referencia: str = Field(..., description="Ponto ou quadra, ex: 'Estação Arniqueiras', 'SBS Qd 2'")
    is_padrao: bool = Field(default=False, description="Indica se é o endereço residencial padrão")


class UsuarioCadastro(BaseModel):
    """Dados informados na inscrição inicial do usuário no aplicativo."""
    nome: str = Field(..., min_length=2, max_length=80)
    email: Optional[str] = None
    telefone: Optional[str] = None
    maior_18_anos: bool = Field(default=True, description="Confirmação obrigatória do MVP (ADR 0002)")
    transporte_padrao: str = Field(default="misto", description="carro, metro_onibus, uber, misto")
    restricoes_permanentes: Optional[str] = None
    chave_pix_padrao: Optional[str] = None
    tipo_chave_pix_padrao: str = "aleatoria"
    enderecos: List[EnderecoUsuario] = Field(default_factory=list)

    @field_validator("maior_18_anos")
    @classmethod
    def validar_maioridade(cls, v: bool) -> bool:
        if not v:
            raise ValueError("O Orquestrador de Rolês é exclusivo para maiores de 18 anos (ADR 0002).")
        return v


class UsuarioPublico(BaseModel):
    """Visualização pública/compartilhada do perfil de um amigo na sala."""
    id: str
    nome: str
    transporte_padrao: str
    restricoes_permanentes: Optional[str] = None


# ==============================================================================
# 2. PARTICIPAÇÃO NO ROLÊ (DADOS DINÂMICOS ESPECÍFICOS DE UM ROLÊ)
# ==============================================================================

class JanelaComOrigem(BaseModel):
    """
    Associação de uma janela de horário ao respectivo ponto de partida no DF.
    Ex: Sexta após 19h saindo do Trabalho; Sábado à tarde saindo de Casa.
    """
    dia: str = Field(..., description="sex, sab, dom, etc.")
    periodo: Optional[str] = Field(None, description="tarde, noite, dia_todo")
    horario_inicio: Optional[str] = Field(None, description="Ex: '19:00'")
    horario_fim: Optional[str] = Field(None, description="Ex: '23:30'")
    endereco_rotulo: str = Field(default="Casa", description="'Casa', 'Trabalho', 'Faculdade' ou 'Outro'")
    regiao_ra: str = Field(..., description="Região Administrativa de onde a pessoa sairá neste horário")
    ponto_referencia: Optional[str] = None


class ParticipantePreenchimento(BaseModel):
    """O que o amigo preenche ao acessar o link da sala."""
    nome: str
    usuario_id: Optional[str] = None
    janelas: List[JanelaComOrigem] = Field(..., min_length=1)
    limite_gasto_rs: Decimal = Field(..., ge=0, description="RNF-01/02: 100% SIGILOSO (nunca exposto publicamente)")
    vibe_hoje: Optional[str] = None
    transporte_hoje: Optional[str] = None


class ParticipantePublico(BaseModel):
    """
    Retorno público de um participante para os outros amigos da sala.
    O limite_gasto_rs é EXCLUÍDO por design (RNF-01 e RNF-02).
    """
    id: str
    sala_id: str
    nome: str
    janelas_resumo: List[Dict[str, Any]]
    vibe_hoje: Optional[str] = None
    transporte_hoje: Optional[str] = None


# ==============================================================================
# 3. SALAS, CARDS DE SUGESTÃO E VOTAÇÃO
# ==============================================================================

class SalaCriacao(BaseModel):
    nome_role: str = Field(..., min_length=3, max_length=120)
    criador_nome: str = Field(..., min_length=2, max_length=80)
    criador_id: Optional[str] = None


class SugestaoRoleCard(BaseModel):
    id: Optional[str] = None
    sala_id: Optional[str] = None
    local_id: Optional[str] = None
    nome_local: str
    regiao_ra: str
    endereco: str
    dia_horario_sugerido: str
    faixa_gasto_rs: Decimal
    mobility_summary: Optional[str] = None
    ranking_justica: float = 0.0
    motivo_escolha: Optional[str] = None


class VotoRegistro(BaseModel):
    participante_id: str
    sugestao_id: str


# ==============================================================================
# 4. PÓS-ROLÊ, DIVISÃO DE CONTA E PIX
# ==============================================================================

class ItemDespesa(BaseModel):
    descricao: str
    valor: Decimal
    consumidores: List[str] = Field(default_factory=list, description="Lista de nomes de quem consumiu este item")


class DespesaPosRoleRegistro(BaseModel):
    pagador_nome: str
    valor_total_rs: Decimal
    chave_pix: str
    tipo_chave_pix: str = "aleatoria"
    itens: List[ItemDespesa] = Field(default_factory=list)
    comprovante_url: Optional[str] = None
