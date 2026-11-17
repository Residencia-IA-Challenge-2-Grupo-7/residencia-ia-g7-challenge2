"""Agente 0 — Agente Pessoal, um por membro (PLANO_AGENTES.md, seção 3).

É a fronteira do RNF-02: só ele conhece os 4 campos e o log de preferências do seu membro.

- **Antes do rolê** (código, sem LLM): interpreta os 4 campos por regras (`src/interpretador/campos.py`, ADR 0009)
  e junta o log pessoal; o que a pessoa escreveu agora vence o log. Devolve `PerfilMembroAnonimizado`, identificado
  só pelo marcador da sala (m1, m2...), com 4 canais separados (issue #65):

  | Canal | Conteúdo | Vai para | Público? |
  |---|---|---|---|
  | 1. orçamento | teto individual | vetos financeiros da Validação (código) | não, fica no cofre |
  | 2. restrições | restrições duras (alimentação, acessibilidade) | vetos da Validação (código) | não, fica no cofre |
  | 3. preferências | tipos, vibes, o que evitar, transporte e pedido sanitizado | perfil anônimo do grupo → Pesquisa | sim |
  | 4. logística | origem, janelas de horário e transporte | Logística e cruzamento de janelas (código) | não, fica no cofre |

  O grupo recebe só o canal 3, e as restrições chegam a ele somadas com as dos outros, sem dizer de quem são.
- **Depois do rolê** (LLM): transforma o comentário da pessoa em uma atualização de campos fechados, que só é
  gravada no log depois da confirmação dela.

O log fica no *store* do LangGraph, no espaço ("log_pessoal", usuário pseudônimo). Guarda só enumerações e datas:
nada de texto livre (contra o envenenamento da memória), valor em reais ou dado de outra pessoa.
"""
from __future__ import annotations

import copy
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from src.agentes.contratos import AtualizacaoLog, Membro, PerfilAnonimoMembro, esquema_estrito
from src.agentes.llm import ClienteLLM, ErroLLM, embrulhar, prompt
from src.interpretador.campos import PerfilInterpretado, interpretar_campos
from src.interpretador.lugares import _indice
from src.interpretador.numeros import canon
from src.interpretador.pseudonimo import Pseudonimos

NAMESPACE = "log_pessoal"
CHAVE = "perfil"
VALIDADE = timedelta(days=180)  # item do log sem confirmação nesse prazo deixa de valer

# aspecto do log -> efeito no perfil: (vibes a acrescentar, o que evitar)
EFEITOS = {
    ("barulho", "evita"): (["Calmo / Bom para Conversar"], ["lugares barulhentos"]),
    ("lugar_calmo", "gosta"): (["Calmo / Bom para Conversar"], []),
    ("lotacao", "evita"): ([], ["lugares lotados"]),
    ("preco", "evita"): (["Baratinho"], []),
    ("musica_ao_vivo", "gosta"): (["Animado / Galera"], []),
    ("musica_ao_vivo", "evita"): ([], ["música ao vivo alta"]),
    ("ar_livre", "gosta"): ([], []),
    ("distancia", "evita"): ([], ["lugares muito longe"]),
}
TRANSPORTE_DO_LOG = {("transporte_publico", "gosta"): "publico", ("transporte_app", "gosta"): "app"}
CAMPOS = ("origem", "horarios", "teto", "preferencias")  # os 4 campos da Tela 2, na ordem de interpretar_campos
FUSO = ZoneInfo("America/Sao_Paulo")


# ------------------------------------------------------------------ log pessoal

def ler_log(store, usuario: str) -> dict:
    """Log do usuário; sem store ou sem usuário (pessoa sem conta), um log vazio."""
    item = store.get((NAMESPACE, usuario), CHAVE) if store is not None and usuario else None
    return copy.deepcopy(item.value) if item else {"preferencias": {}, "restricoes": {}, "roles_avaliados": 0}


def _valido(item: dict, agora: datetime) -> bool:
    return agora - datetime.fromisoformat(item["atualizado_em"]) <= VALIDADE


def gravar_no_log(store, usuario: str, atualizacao: AtualizacaoLog, agora: datetime) -> dict:
    """Grava a atualização **já confirmada pela pessoa**. Só campos fechados; o trecho não é guardado."""
    log = ler_log(store, usuario)
    quando = agora.isoformat(timespec="minutes")
    for p in atualizacao.preferencias:
        chave = f"{p.aspecto}:{p.sentido}"
        oposto = f"{p.aspecto}:{'gosta' if p.sentido == 'evita' else 'evita'}"
        log["preferencias"].pop(oposto, None)  # mudou de ideia: vale o mais recente
        atual = log["preferencias"].get(chave, {"vezes": 0})
        log["preferencias"][chave] = {"vezes": atual["vezes"] + 1, "atualizado_em": quando}
    for r in atualizacao.restricoes:
        atual = log["restricoes"].get(r.tipo, {"vezes": 0})
        log["restricoes"][r.tipo] = {"vezes": atual["vezes"] + 1, "atualizado_em": quando}
    log["roles_avaliados"] = log.get("roles_avaliados", 0) + 1
    store.put((NAMESPACE, usuario), CHAVE, log)
    return log


# ------------------------------------------------------------------ antes do rolê (código)

def sanitizar_pedido(texto: str, nomes: list[str]) -> str:
    """O campo 4 sem nomes da sala, sem regiões administrativas (a origem é segredo) e sem números."""
    t = Pseudonimos(nomes).ocultar(texto or "")
    t = re.sub(r"@m\d+", "alguém", t)
    t = " " + canon(t) + " "
    for forma, _ in _indice():
        t = t.replace(f" {forma} ", " ")
    t = re.sub(r"r\$\s*|\d+([.,]\d+)?", " ", t)
    return " ".join(t.split())[:200]


def antes_do_role(membro: Membro, store, agora: datetime, nomes_da_sala: list[str]
                  ) -> tuple[PerfilInterpretado, PerfilAnonimoMembro]:
    perfil = copy.deepcopy(membro.perfil)
    prefs = perfil.preferencias
    log = ler_log(store, membro.usuario)
    usados = 0
    evitar: list[str] = []

    for tipo, item in log["restricoes"].items():
        if _valido(item, agora) and tipo not in prefs.restricoes:
            prefs.restricoes.append(tipo)
            usados += 1
    for chave, item in log["preferencias"].items():
        if not _valido(item, agora):
            continue
        aspecto, sentido = chave.split(":")
        vibes, evita = EFEITOS.get((aspecto, sentido), ([], []))
        novos = [v for v in vibes if v not in prefs.vibes]
        prefs.vibes.extend(novos)
        evitar.extend(e for e in evita if e not in evitar)
        modo = TRANSPORTE_DO_LOG.get((aspecto, sentido))
        if modo and not prefs.transporte:  # o campo 4 vence o log
            prefs.transporte.append(modo)
            usados += 1
        usados += bool(novos or evita)

    anonimo = PerfilAnonimoMembro(
        tipos=list(prefs.tipos), vibes=list(prefs.vibes), evitar=evitar, restricoes=list(prefs.restricoes),
        transporte=list(prefs.transporte), trecho_pedido=sanitizar_pedido(prefs.texto_busca, nomes_da_sala),
        itens_do_log_usados=usados)
    return perfil, anonimo


# ------------------------------------------------------------------ saída em 4 canais (issue #65)

@dataclass(frozen=True)
class CanalLogistica:
    ra: str | None
    regiao: str | None
    janelas: tuple            # JanelaResolvida de campos.py
    transporte: tuple[str, ...]


@dataclass(frozen=True)
class PerfilMembroAnonimizado:
    """Saída do Agente Pessoal de um membro. Sem nome nem id de usuário: só o marcador da sala. Os canais 1, 2 e 4
    e o perfil efetivo ficam fora do `repr`, para não irem parar num log por engano; `publico()` é o que pode
    sair do cofre."""
    marcador: str
    preferencias: PerfilAnonimoMembro                                       # canal 3, o único público
    orcamento: Decimal | None = field(repr=False)                           # canal 1
    restricoes: tuple[str, ...] = field(repr=False)                         # canal 2
    logistica: CanalLogistica = field(repr=False)                           # canal 4
    perfil_efetivo: PerfilInterpretado = field(repr=False)                  # 4 campos + log, para o cofre
    pendencias: dict[str, str] = field(default_factory=dict, repr=False)    # campo -> pergunta à própria pessoa

    def publico(self) -> dict:
        return self.preferencias.model_dump()


def agente_pessoal(membro: Membro, store, agora: datetime, nomes_da_sala: list[str]) -> PerfilMembroAnonimizado:
    """O Agente Pessoal de um membro já interpretado (o nó do grafo usa este)."""
    efetivo, anonimo = antes_do_role(membro, store, agora, nomes_da_sala)
    p = efetivo.preferencias
    return PerfilMembroAnonimizado(
        marcador=membro.id, preferencias=anonimo, orcamento=efetivo.teto, restricoes=tuple(p.restricoes),
        logistica=CanalLogistica(ra=efetivo.ra, regiao=efetivo.regiao, janelas=tuple(efetivo.janelas),
                                 transporte=tuple(p.transporte)),
        perfil_efetivo=efetivo, pendencias=dict(efetivo.pendencias))


def executar_agente_pessoal(campos_usuario: dict[str, str], *, marcador: str = "m1", agora: datetime | None = None,
                            nomes_da_sala: list[str] | tuple[str, ...] = (), store=None,
                            usuario: str | None = None) -> PerfilMembroAnonimizado:
    """Os 4 campos de texto de um membro -> `PerfilMembroAnonimizado` (issue #65).

    `campos_usuario`: {"origem", "horarios", "teto", "preferencias"}, exatamente essas chaves. `nomes_da_sala` são
    tirados do pedido que vai ao grupo. Com `store` e `usuario` (id pseudônimo permanente), o log pessoal entra;
    sem eles, só os 4 campos. `agora`: hora local de Brasília sem fuso (padrão: o relógio)."""
    chaves = set(campos_usuario)
    if chaves != set(CAMPOS):
        raise ValueError(f"campos esperados {list(CAMPOS)}; faltam {sorted(set(CAMPOS) - chaves)}, "
                         f"sobram {sorted(chaves - set(CAMPOS))}")
    if not re.fullmatch(r"m\d+", marcador):
        raise ValueError("o marcador é o da sala (m1, m2...), nunca um nome ou id")
    agora = agora or datetime.now(FUSO).replace(tzinfo=None)
    perfil = interpretar_campos(*(campos_usuario[c] or "" for c in CAMPOS), agora=agora)
    membro = Membro(id=marcador, usuario=usuario or "", nome="", perfil=perfil)
    return agente_pessoal(membro, store, agora, list(nomes_da_sala))


# ------------------------------------------------------------------ depois do rolê (LLM)

def depois_do_role(comentario: str, cliente: ClienteLLM) -> AtualizacaoLog:
    """Proposta de atualização para a pessoa confirmar. O código descarta item com trecho que não está no
    comentário. Sem LLM, devolve uma proposta vazia (nada é gravado sem a pessoa)."""
    vazio = AtualizacaoLog(preferencias=[], restricoes=[], tentativa_de_instrucao=False,
                           frase_de_confirmacao="Não consegui ler seu comentário agora; nada foi guardado.")
    if not cliente.disponivel:
        return vazio
    try:
        bruto = cliente.json("pessoal_pos_role", prompt("pessoal_pos_role"),
                             embrulhar("comentario_pos_role", comentario), esquema_estrito(AtualizacaoLog),
                             max_tokens=800)
        a = AtualizacaoLog.model_validate(bruto)
    except (ErroLLM, ValueError):
        return vazio
    c = canon(comentario)
    literal = lambda trecho: len(canon(trecho)) >= 3 and canon(trecho) in c  # noqa: E731
    return a.model_copy(update={"preferencias": [p for p in a.preferencias if literal(p.trecho)],
                                "restricoes": [r for r in a.restricoes if literal(r.trecho)]})
