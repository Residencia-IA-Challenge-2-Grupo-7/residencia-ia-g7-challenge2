"""Estado compartilhado do grafo multiagente (issue #64, ADR 0016).

Dois canais, nunca misturados:

- **Público** (`MultiAgentState`): o que circula entre os nós do LangGraph e fica no checkpoint. Só marcadores de
  sala (m1, m2...), perfis anônimos, candidatos da base e textos. Nenhum nome, id de usuário, teto, origem ou
  gasto de alguém.
- **Privado** (`Cofre`, em contratos.py): os 4 campos de cada membro, preso ao grafo na construção e lido só pelos
  nós de código (Agente Pessoal, Logística, vetos da Validação). Não entra no estado, então não vai para o
  checkpoint, para o Langfuse nem para um LLM (RNF-02).

Os campos com reducer (`operator.add`) acumulam o que cada nó devolve; os demais são substituídos. A serialização
passa por `EstadoSerializado`, um espelho Pydantic com `extra="forbid"` em todos os níveis com forma fixa: uma chave
desconhecida (um `teto`, uma `origem` posta ali por engano) faz a serialização falhar em vez de gravar o dado.

    from src.agentes.estado import MultiAgentState, serializar_estado, desserializar_estado
    texto = serializar_estado(estado)          # JSON validado
    estado = desserializar_estado(texto)       # dict pronto para o grafo
"""
from __future__ import annotations

import json
import operator
import re
from typing import Annotated, Any, TypedDict

from pydantic import BaseModel, ConfigDict

from src.agentes.contratos import Candidato, CartaoTexto, Cofre, MotivoVeto, PerfilAnonimoMembro
from src.interpretador.numeros import canon

# Chaves que só existem no cofre. Aparecer uma delas em qualquer nível do estado é vazamento (RNF-02).
CHAVES_PRIVADAS = frozenset({"teto", "teto_rs", "teto_individual", "origem", "origem_ra", "ra_origem", "usuario",
                             "nome_membro", "por_participante", "desl_por", "campos", "perfil"})
# Partículas de nomes compostos que não identificam ninguém sozinhas ("Ana dos Santos" não procura "dos").
PARTICULAS = frozenset({"de", "da", "do", "das", "dos", "e", "di", "du", "del", "van", "von"})
# Campos só com texto copiado da base de lugares, nunca de um membro: ficam fora da varredura de nomes
# (uma descrição com "vista clara" não é vazamento de uma "Clara"). A varredura de chaves continua valendo.
CAMPOS_DA_BASE = frozenset({"documentos"})


class MultiAgentState(TypedDict, total=False):
    # entrada
    sala_id: str                                               # código da sala (não identifica ninguém)
    trace_url: str | None                                      # link oficial do trace no Langfuse Cloud (Issue #73)
    membros: list[str]                                         # marcadores m1..mN; o Send abre um Agente Pessoal por um
    # Agente 0 (Pessoal) -> grupo
    membros_anonimos: Annotated[list[dict], operator.add]      # PerfilAnonimoMembro, um por membro, em paralelo
    preferencias_grupo: dict                                   # PreferenciasGrupo: tipos e vibes agregados, restrições
    # Agente 1 (Pesquisa)
    candidatos_pesquisa: list[dict]                            # Candidato: id, motivo e trecho literal conferido
    documentos: dict[str, dict]                                # documentos da base que a Pesquisa leu, por id
    vistos: list[str]                                          # ids já devolvidos pela Pesquisa (não repetir)
    pedido_nova_busca: dict | None                             # PedidoNovaBusca: só contagens, nunca texto livre
    iteracao_pesquisa: int                                     # voltas Validação -> Pesquisa (máximo 2)
    # Agente 2 (Logística)
    candidatos_avaliados: list[dict]                           # CandidatoAvaliado: agregados de deslocamento e nota
    # Agente 3 (Validação)
    julgados: list[str]                                        # ids que já passaram pelo juiz do parecer
    relatorio_validacao: dict                                  # RelatorioValidacao: aprovados, vetos e contagem
    candidatos_validados: list[dict]                           # CandidatoAvaliado dos aprovados, na ordem do ranking
    # Agente 4 (Comunicação) e Validação dos textos
    fatos: list[dict]                                          # o que a Comunicação pode afirmar de cada cartão
    cartoes: list[dict]                                        # CartaoTexto escritos pela Comunicação
    cartoes_por_llm: bool
    reprovados: dict[str, list[str]]                           # cartão -> motivos (só enumerações)
    reescritas: int                                            # voltas Validação -> Comunicação (máximo 1)
    # saída
    resultado_final_cartoes: list[dict]                        # cartões públicos para a votação (Tela 3)
    mensagens: Annotated[list[dict], operator.add]             # Mensagem: a conversa entre os agentes
    historico_erros: Annotated[list[str], operator.add]        # vetos, reprovações e falhas, em ordem


# ------------------------------------------------------------------ esquemas auxiliares (Pydantic)

class _Fechado(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PreferenciasGrupo(_Fechado):
    tamanho: int
    tipos: list[str]
    tipos_pedidos: dict[str, str]                              # tipo -> "x de y"
    vibes: list[str]
    evitar: list[str]
    restricoes: list[str]
    trechos_pedido: list[str]                                  # pedidos sanitizados (sem nome, região ou número)
    janela: str | None


class DocumentoBase(_Fechado):
    id: str
    nome: str
    tipo: str
    regiao_do_lugar: str
    vibes: list[str]
    descricao: str
    pontuacao: float | None = None                             # similaridade na busca que o trouxe


class PedidoNovaBusca(_Fechado):
    faltam: int
    vetos: dict[str, int]
    ja_vistos: int


class CandidatoAvaliado(_Fechado):
    id: str
    nome: str
    ra_do_lugar: str
    janela: str
    quantos_podem: str
    horario_situacao: str
    nota_justica: int | float
    pior_trajeto_min: int | None
    media_trajeto_min: int | None
    diferenca_min: int | None
    estimativa_provisoria: bool
    pontuacao: float


class Veto(_Fechado):
    id: str
    motivo: MotivoVeto


class RelatorioValidacao(_Fechado):
    aprovados: list[str]
    vetos: list[Veto]
    contagem: dict[str, int]
    teto_aplicado: bool
    derrubados_pelo_juiz: list[str] = []


class Mensagem(_Fechado):
    de: str
    para: str
    texto: str
    em: str
    usou_llm: bool | None = None
    consultas: list[str] | None = None
    vereditos_juiz: dict[str, Any] | None = None
    exposicoes: list[dict[str, Any]] | None = None


class EstadoSerializado(_Fechado):
    """Espelho validado de `MultiAgentState`, para gravar e ler o estado em JSON."""
    sala_id: str | None = None
    trace_url: str | None = None
    membros: list[str] | None = None
    membros_anonimos: list[PerfilAnonimoMembro] | None = None
    preferencias_grupo: PreferenciasGrupo | None = None
    candidatos_pesquisa: list[Candidato] | None = None
    documentos: dict[str, DocumentoBase] | None = None
    vistos: list[str] | None = None
    pedido_nova_busca: PedidoNovaBusca | None = None
    iteracao_pesquisa: int | None = None
    candidatos_avaliados: list[CandidatoAvaliado] | None = None
    julgados: list[str] | None = None
    relatorio_validacao: RelatorioValidacao | None = None
    candidatos_validados: list[CandidatoAvaliado] | None = None
    fatos: list[dict[str, Any]] | None = None
    cartoes: list[CartaoTexto] | None = None
    cartoes_por_llm: bool | None = None
    reprovados: dict[str, list[str]] | None = None
    reescritas: int | None = None
    resultado_final_cartoes: list[dict[str, Any]] | None = None
    mensagens: list[Mensagem] | None = None
    historico_erros: list[str] | None = None


# ------------------------------------------------------------------ serialização e varredura

class VazamentoNoEstado(ValueError):
    """O estado tem uma chave ou um valor que só deveria existir no cofre."""


def _chaves_privadas(no: Any, caminho: str = "") -> list[str]:
    if isinstance(no, dict):
        achados = [f"{caminho}.{k}".lstrip(".") for k in no if k in CHAVES_PRIVADAS]
        for k, v in no.items():
            achados += _chaves_privadas(v, f"{caminho}.{k}")
        return achados
    if isinstance(no, list):
        return [a for i, v in enumerate(no) for a in _chaves_privadas(v, f"{caminho}[{i}]")]
    return []


def dados_privados_no_estado(estado: dict, cofre: Cofre | None = None) -> list[str]:
    """Varre o estado atrás do que só pode estar no cofre: chaves privadas em qualquer nível e, com o cofre, o id de
    usuário, o nome ou parte do nome composto de algum membro em qualquer texto, sem diferenciar maiúsculas nem
    acentos ("bia" pega "Bia", "otavio" pega "Otávio", "Maria" pega "Maria Eduarda"). Devolve onde achou; lista
    vazia é o esperado."""
    achados = _chaves_privadas(estado)
    if cofre is not None:
        texto = _texto_para_nomes(estado, cofre)
        for m in cofre.membros.values():
            if m.usuario and _contem_palavra(texto, canon(m.usuario)):
                achados.append(f"usuario de {m.id}")
            nome = " ".join(canon(m.nome or "").split())
            if nome and _contem_palavra(texto, nome):
                achados.append(f"nome de {m.id}")
            elif any(_contem_palavra(texto, parte) for parte in _partes_do_nome(nome)):
                achados.append(f"nome parcial de {m.id}")
    return achados


def _partes_do_nome(nome: str) -> list[str]:
    partes = nome.split()
    return [p for p in partes if len(p) >= 3 and p not in PARTICULAS] if len(partes) > 1 else []


def _texto_para_nomes(estado: dict, cofre: Cofre) -> str:
    """O estado em texto, sem os campos da base e sem os nomes dos lugares da base: "Maria Fumaça" é um lugar, não
    a "Maria" da sala."""
    texto = canon(json.dumps({k: v for k, v in estado.items() if k not in CAMPOS_DA_BASE},
                             ensure_ascii=False, default=str))
    lugares = sorted({canon(l.get("nome") or "") for l in cofre.lugares.values()} - {""}, key=len, reverse=True)
    for lugar in lugares:
        texto = re.sub(rf"(?<!\w){re.escape(lugar)}(?!\w)", " ", texto)
    return texto


def _contem_palavra(texto: str, valor: str) -> bool:
    """`valor` como palavra inteira em `texto`; os dois já normalizados por `canon`."""
    return re.search(rf"(?<!\w){re.escape(valor)}(?!\w)", texto) is not None


def serializar_estado(estado: dict, cofre: Cofre | None = None) -> str:
    """JSON do estado, validado por `EstadoSerializado`. Falha com `VazamentoNoEstado` se achar dado do cofre e
    com `pydantic.ValidationError` se um campo tiver forma inesperada ou chave desconhecida."""
    achados = dados_privados_no_estado(estado, cofre)
    if achados:
        raise VazamentoNoEstado("dados do cofre no estado: " + ", ".join(achados))
    return EstadoSerializado.model_validate(estado).model_dump_json(exclude_unset=True)


def desserializar_estado(texto: str) -> MultiAgentState:
    """Lê um JSON gravado por `serializar_estado`, validando de novo, e devolve o dict que o grafo usa."""
    modelo = EstadoSerializado.model_validate_json(texto)
    estado = modelo.model_dump(mode="json", exclude_unset=True)
    achados = _chaves_privadas(estado)
    if achados:  # inalcançável com extra="forbid" nos níveis fixos; protege os campos dict livres
        raise VazamentoNoEstado("dados do cofre no estado: " + ", ".join(achados))
    return estado  # type: ignore[return-value]

