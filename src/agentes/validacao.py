"""Filtros Determinísticos do Agente de Validação (Agente 3).

Executa a camada de Vetos Duros em Python puro (RNF-04), garantindo que nenhum
local inválido por horário, restrição alimentar ou estouro de orçamento passe
para a síntese de cartões ou votação.

Requisitos atendidos:
- RF-17 (Orçamento Sigiloso): Verificação individual (consumo + transporte <= teto).
- RF-12 (Horários): Validação de funcionamento na janela comum do grupo contra a base 2FA.
- RNF-04 (Cálculos Fora do LLM): Verificação determinística antes do Juiz LLM.
"""
from __future__ import annotations

import re
from collections import Counter
from datetime import datetime
from decimal import Decimal
from typing import Any, Iterable, Mapping

from src.agentes.contratos import Cofre, MotivoVeto, Restricao
from src.agentes.estado import PedidoNovaBusca, RelatorioValidacao, Veto
from src.interpretador.numeros import canon
from src.salas.horario_lugar import ano_do_lugar, ler_funcionamento
from src.salas.janelas import JanelaComum

# Situações de horário viáveis para realização do rolê
SITUACOES_ACEITAS = frozenset({"aberto", "provavel", "incerto"})

# Termos para validação textual de restrições alimentares duras (RF-17 / RNF-04)
TERMOS_RESTRICAO: dict[str, str] = {
    "alim_vegetariano": r"vegetarian[oa]|vegan[oa]|sem carne|opcoes vegetarianas",
    "alim_vegano": r"vegan[oa]|opcoes veganas",
    "alim_sem_gluten": r"sem gluten|gluten free",
    "alim_sem_lactose": r"sem lactose|zero lactose",
    "acess_entrada_sem_degrau": r"acessivel|acessibilidade|rampa|cadeirante",
}

# Palavras que indicam foco estrito em carnes / churrasco
TERMOS_CARNES: str = r"churrascaria|rodizio de carnes|parrilla|100% carnes?|carnivor[oa]"


def dentro_do_orcamento_individual(
    custo_consumo: Decimal,
    tetos: Mapping[str, Decimal | None],
    custos_deslocamentos: Mapping[str, Decimal] | None = None,
) -> bool:
    """Verifica se (consumo + transporte individual) <= teto de cada participante (RF-17).
    
    Quem não informou teto (None) não restringe o rolê. Se estourar para qualquer
    um que informou teto, retorna False.
    """
    deslocamento = custos_deslocamentos or {}

    for membro_id, teto in tetos.items():
        if teto is None:
            continue

        transporte = deslocamento.get(membro_id, Decimal("0.00"))
        gastos_total = custo_consumo + transporte

        if gastos_total > teto:
            return False

    return True


# Apelido de compatibilidade com a issue #68
cabe_para_cada_um = dentro_do_orcamento_individual


def validar_horario_e_evento(
    lugar: dict,
    janelas: list[JanelaComum],
    agora: datetime,
) -> tuple[bool, MotivoVeto | None, str]:
    """Verifica se o local funciona na janela comum do grupo e se não expirou (RF-12).
    
    Retorna:
        (valido, motivo_veto, situacao)
        Exemplos:
          - (True, None, 'aberto')
          - (False, 'horario', 'fechado')
          - (False, 'encerrado', 'encerrado')
    """
    if not janelas:
        return False, "horario", "fechado"

    ano = ano_do_lugar(lugar, agora.year)
    func = ler_funcionamento(lugar.get("horario_funcionamento"), ano)

    evento_encerrado = False

    for jc in janelas:
        situacao, _ = func.situacao(jc.inicio, jc.fim)
        if situacao in SITUACOES_ACEITAS:
            return True, None, situacao
        if situacao == "encerrado":
            evento_encerrado = True

    if evento_encerrado:
        return False, "encerrado", "encerrado"

    return False, "horario", "fechado"


def _texto_lugar_para_restricao(lugar: dict) -> str:
    """Concatena campos textuais do local para busca por evidência sensorial de restrição."""
    campos = (
        lugar.get("nome"),
        lugar.get("tipo_de_role"),
        lugar.get("resumo_sensorial"),
        lugar.get("legenda_original"),
        lugar.get("transcricao_audio_whisper"),
    )
    return canon(" ".join(str(c or "") for c in campos))


def atende_restricoes_duras(
    lugar: dict,
    restricoes: Iterable[str],
) -> tuple[bool, MotivoVeto | None]:
    """Verifica se o local atende às restrições alimentares/acessibilidade duras do grupo.
    
    Regras duras:
    - Se o grupo não tem restrições: Aprovado (True, None).
    - Local focado estritamente em carnes sem menção vegetariana vetado para vegetariano/vegano.
    - Se a restrição exigir opções comprovadas e o local não apresentar no texto nem tags: Vetado.
    """
    lista_restricoes = [r for r in restricoes if r]
    if not lista_restricoes:
        return True, None

    texto = _texto_lugar_para_restricao(lugar)
    restricoes_atendidas = set(lugar.get("restricoes_atendidas") or [])

    for r in lista_restricoes:
        if r in restricoes_atendidas:
            continue

        padrao = TERMOS_RESTRICAO.get(r)
        achou_opcao = bool(padrao and re.search(padrao, texto))

        # Caso especial do Veto 4: local 100% carnes sem opção para vegetariano/vegano
        if r in ("alim_vegetariano", "alim_vegano"):
            eh_carnes = bool(re.search(TERMOS_CARNES, texto))
            if eh_carnes and not achou_opcao:
                return False, "restricao"

        # Se não achou evidência nem opção declarada para a restrição dura
        if not achou_opcao:
            return False, "restricao"

    return True, None


def validar_candidatos_regras(
    candidatos: list[dict],
    janelas: list[JanelaComum] | None = None,
    agora: datetime | None = None,
    tetos: dict[str, Decimal | None] | None = None,
    lugares_base: dict[str, dict] | None = None,
    deslocamentos: dict[str, dict[str, Decimal]] | None = None,
    restricoes: list[str] | None = None,
    cofre: Cofre | None = None,
) -> RelatorioValidacao:
    """Executa a suíte de filtros determinísticos (Vetos 1, 2, 3 e 4).
    
    Aceita parâmetros diretos ou extração automática a partir do `Cofre` do servidor.
    Retorna um `RelatorioValidacao` estruturado pronto para o estado do LangGraph.
    """
    # 1. Resolve dependências vindas do cofre (se fornecido)
    if cofre is not None:
        janelas = cofre.janelas if janelas is None else janelas
        agora = cofre.agora if agora is None else agora
        lugares_base = cofre.lugares if lugares_base is None else lugares_base
        
        if tetos is None:
            perfis = cofre.perfis_efetivos or {m.id: m.perfil for m in cofre.membros.values()}
            tetos = {mid: p.teto for mid, p in perfis.items()}
            
        if restricoes is None:
            perfis = cofre.perfis_efetivos or {m.id: m.perfil for m in cofre.membros.values()}
            restricoes = sorted({r for p in perfis.values() for r in p.preferencias.restricoes})

        if deslocamentos is None and cofre.analises:
            deslocamentos = {
                lugar_id: {mid: d.get("custo_ida_volta", Decimal("0.00")) for mid, d in membros_desl.items()}
                for lugar_id, membros_desl in cofre.analises.items()
            }

    janelas = janelas or []
    agora = agora or datetime.now()
    tetos = tetos or {}
    lugares_base = lugares_base or {}
    deslocamentos = deslocamentos or {}
    restricoes = restricoes or []

    teto_aplicado = any(t is not None for t in tetos.values())
    aprovados: list[str] = []
    vetos: list[Veto] = []
    contagem: Counter = Counter()

    for cand in candidatos:
        cand_id = cand.get("id") or cand.get("lugar_id") or ""
        lugar = lugares_base.get(cand_id, cand)

        # -------------------------------------------------------------
        # VETO 2 & 3: Horário e Validade de Evento
        # -------------------------------------------------------------
        horario_ok, motivo_h, _ = validar_horario_e_evento(lugar, janelas, agora)
        if not horario_ok and motivo_h:
            vetos.append(Veto(id=cand_id, motivo=motivo_h))
            contagem[motivo_h] += 1
            continue

        # -------------------------------------------------------------
        # VETO 4: Restrições Alimentares Duras
        # -------------------------------------------------------------
        restr_ok, motivo_r = atende_restricoes_duras(lugar, restricoes)
        if not restr_ok and motivo_r:
            vetos.append(Veto(id=cand_id, motivo=motivo_r))
            contagem[motivo_r] += 1
            continue

        # -------------------------------------------------------------
        # VETO 1: Orçamento Sigiloso com Deslocamento
        # -------------------------------------------------------------
        custo_rs = Decimal(str(lugar.get("custo_medio_rs") or 0))
        desl_lugar = deslocamentos.get(cand_id, {})
        orcamento_ok = dentro_do_orcamento_individual(custo_rs, tetos, desl_lugar)
        if not orcamento_ok:
            vetos.append(Veto(id=cand_id, motivo="orcamento"))
            contagem["orcamento"] += 1
            continue

        # Local aprovado em todos os 4 filtros determinísticos!
        aprovados.append(cand_id)

    # Garante todas as chaves padrão no relatório
    contagem_final = {
        "horario": contagem["horario"],
        "orcamento": contagem["orcamento"],
        "restricao": contagem["restricao"],
        "encerrado": contagem["encerrado"],
        "deslocamento": contagem["deslocamento"],
    }

    return RelatorioValidacao(
        aprovados=aprovados,
        vetos=vetos,
        contagem=contagem_final,
        teto_aplicado=teto_aplicado,
        derrubados_pelo_juiz=[],
    )


def gerar_pedido_nova_busca(
    relatorio: RelatorioValidacao,
    total_vistos: int,
    minimo_esperado: int = 3,
) -> PedidoNovaBusca | None:
    """Gera o pedido estruturado de realimentação para o Agente de Pesquisa caso restem < 3 candidatos."""
    faltam = minimo_esperado - len(relatorio.aprovados)
    if faltam <= 0:
        return None

    return PedidoNovaBusca(
        faltam=faltam,
        vetos=dict(relatorio.contagem),
        ja_vistos=total_vistos,
    )
