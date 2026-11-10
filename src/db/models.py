"""
Modelos de Domínio e Validação Pydantic
Projeto: Orquestrador de Rolês - Grupo 7 (Residência em IA | UnB & Eldorado)
Responsável: Maria Eduarda (DevOps & Backend)
Issue #41 | Referência: GUIA_OFICIAL_PROJETO.md

Define os esquemas e contratos de dados para:
- Usuários e múltiplos endereços salvos no DF (Casa, Trabalho, UnB)
- Janelas de horário com ponto de partida associado e timestamps exatos (RFC 3339)
- Salas com padrão ROLE-XXXX, tokens de autenticação (SHA-256)
- Sugestões com centavos exatos (Decimal) e integridade dos 93 lugares
- Pós-rolê com rateio individualizado e Pix BACEN
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
    ponto_referencia: Optional[str] = Field(None, description="Ponto opcional ou quadra (LGPD)")
    is_padrao: bool = Field(default=False, description="Indica se é o endereço residencial padrão")


class UsuarioCadastro(BaseModel):
    """Dados informados na inscrição inicial do usuário no aplicativo."""
    nome: str = Field(..., min_length=2, max_length=80)
    email: Optional[str] = None
    telefone: Optional[str] = None
    maior_18_anos: bool = Field(..., description="Confirmação obrigatória do MVP (ADR 0002)")
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
    Associação de uma janela de horário com data/hora ao ponto de partida no DF.
    """
    inicio: datetime
    fim: datetime
    disponivel: bool = True
    regiao_ra: str = Field(..., description="Região Administrativa de onde a pessoa sairá neste horário")
    rotulo: Optional[str] = Field(default="Casa", description="'Casa', 'Trabalho', 'Faculdade' ou 'Outro'")


class ParticipantePreenchimento(BaseModel):
    """O que o amigo preenche ao acessar o link da sala."""
    nome: str = Field(..., min_length=1, max_length=80)
    usuario_id: Optional[str] = None
    token_hash: Optional[str] = None
    confirmado: bool = False
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
    confirmado: bool
    janelas_resumo: List[Dict[str, Any]]
    vibe_hoje: Optional[str] = None
    transporte_hoje: Optional[str] = None


# ==============================================================================
# 3. SALAS, CARDS DE SUGESTÃO E VOTAÇÃO
# ==============================================================================

class SalaCriacao(BaseModel):
    nome_role: str = Field(..., min_length=3, max_length=120)
    organizador_nome: str = Field(..., min_length=2, max_length=80)
    token_organizador_hash: Optional[str] = None
    criador_id: Optional[str] = None


class SugestaoRoleCard(BaseModel):
    id: Optional[str] = None
    sala_id: Optional[str] = None
    posicao: int = 1
    letra_card: str = "A"
    local_id: str = Field(..., description="RF-16: obrigatório dos 93 lugares")
    nome_local: str
    tipo: str = "bar"
    regiao_ra: str
    endereco: str
    inicio: datetime
    fim: datetime
    horario_texto: str
    horario_situacao: str = "aberto"
    contagem: str = "todos podem"
    consumo_rs: Decimal = Decimal("0.00")
    gasto_min: Decimal = Decimal("0.00")
    gasto_max: Decimal = Decimal("0.00")
    tempo_medio_min: Optional[int] = None
    tempo_max_min: Optional[int] = None
    nota_justica: float = 0.0
    pontuacao: float = 0.0
    explicacao: str
    tiktok_url: Optional[str] = None
    fonte: str = "2fa"


class VotoRegistro(BaseModel):
    participante_id: str
    sugestao_id: str


# ==============================================================================
# 4. PÓS-ROLÊ, DIVISÃO DE CONTA E PIX
# ==============================================================================

class RateioDevedor(BaseModel):
    devedor_participante_id: str
    valor: Decimal
    pago_em: Optional[datetime] = None


class ItemDespesa(BaseModel):
    descricao: str
    valor: Decimal
    consumidores: List[str] = Field(default_factory=list, description="Lista de IDs de quem consumiu")


class DespesaPosRoleRegistro(BaseModel):
    pagador_participante_id: Optional[str] = None
    pagador_nome: str
    valor_total_rs: Decimal
    chave_pix: str
    tipo_chave_pix: str = "aleatoria"
    itens: List[ItemDespesa] = Field(default_factory=list)
    rateios: List[RateioDevedor] = Field(default_factory=list)
    comprovante_url: Optional[str] = None
    quitado: bool = False
