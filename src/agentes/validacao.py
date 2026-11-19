"""Filtros Determinísticos do Agente de Validação (Agente 3).

Executa a camada de Vetos Duros em Python puro (RNF-04), garantindo que nenhum
local inválido por horário, restrição alimentar, tempo de deslocamento excessivo
ou estouro de orçamento passe para a síntese de cartões ou votação.

Requisitos atendidos:
- RF-17 (Orçamento Sigiloso): Verificação individual (consumo + transporte <= teto).
- RF-12 (Horários): Validação de funcionamento na janela comum do grupo contra a base 2FA.
- ADR 0013 / Menor Miséria: Veto de deslocamento quando tempo individual > 75 min (TEMPO_ACEITAVEL_MIN).
- RNF-04 (Cálculos Fora do LLM): Verificação determinística antes do Juiz LLM.
"""
from __future__ import annotations

import re
from collections import Counter
from datetime import datetime
from decimal import Decimal
from typing import Any, Iterable, Mapping

from src.agentes.contratos import Cofre, MotivoVeto
from src.agentes.estado import PedidoNovaBusca, RelatorioValidacao, Veto
from src.interpretador.numeros import canon
from src.salas.horario_lugar import ano_do_lugar, ler_funcionamento
from src.salas.janelas import JanelaComum
from src.salas.sugestoes import TEMPO_ACEITAVEL_MIN, TERMOS_RESTRICAO

# Situações de horário viáveis para realização do rolê
SITUACOES_ACEITAS = frozenset({"aberto", "provavel", "incerto"})

# Onde o texto de um lugar pode comprovar uma restrição (padrão oficial da base)
CAMPOS_TEXTO_LUGAR = (
    "nome",
    "tipo_de_role",
    "resumo_sensorial",
    "legenda_original",
    "transcricao_audio_whisper",
)


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
    return canon(" ".join(str(lugar.get(campo) or "") for campo in CAMPOS_TEXTO_LUGAR))


def atende_restricoes_duras(
    lugar: dict,
    restricoes: Iterable[str],
) -> tuple[bool, MotivoVeto | None]:
    """Verifica se o local comprova atendimento às restrições alimentares/acessibilidade duras do grupo.
    
    Regra oficial (gabarito e Tela 3):
    - Se o grupo não tem restrições: Aprovado (True, None).
    - Veta o lugar sem evidência comprovada da restrição no vídeo/legenda (via TERMOS_RESTRICAO).
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
        if not padrao or not re.search(padrao, texto):
            return False, "restricao"

    return True, None


def validar_deslocamento_membros(
    analises_membros: Mapping[str, Any] | None,
    tempo_maximo_min: int = TEMPO_ACEITAVEL_MIN,
) -> tuple[bool, MotivoVeto | None]:
    """Verifica se algum membro presente excede o teto aceitável de trajeto (ADR 0013).
    
    A Logística grava None quando o trajeto de um membro não pôde ser estimado.
    Veta por 'deslocamento' se para algum membro o tempo exceder o limite aceitável (75 min).
    """
    if not analises_membros:
        return True, None

    for d in analises_membros.values():
        if d is not None and isinstance(d, dict):
            minutos = d.get("minutos")
            if minutos is not None and minutos > tempo_maximo_min:
                return False, "deslocamento"

    return True, None


def validar_candidatos_regras(
    candidatos: list[dict],
    janelas: list[JanelaComum] | None = None,
    agora: datetime | None = None,
    tetos: dict[str, Decimal | None] | None = None,
    lugares_base: dict[str, dict] | None = None,
    deslocamentos: dict[str, dict[str, Decimal]] | None = None,
    restricoes: list[str] | None = None,
    analises_completas: dict[str, dict[str, Any]] | None = None,
    cofre: Cofre | None = None,
) -> RelatorioValidacao:
    """Executa a suíte de filtros determinísticos (Vetos 1, 2, 3 e 4).
    
    Aceita parâmetros diretos ou extração automática a partir do `Cofre` do servidor.
    Avalia todos os filtros para cada candidato e contabiliza todos os motivos infringidos.
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

        if analises_completas is None and cofre.analises:
            analises_completas = cofre.analises

    janelas = janelas or []
    agora = agora or datetime.now()
    tetos = tetos or {}
    lugares_base = lugares_base or {}
    analises_completas = analises_completas or {}
    restricoes = restricoes or []

    # Extrai automaticamente os custos de transporte a partir de analises_completas
    if deslocamentos is None and analises_completas:
        deslocamentos = {
            lugar_id: {
                mid: d["custo_ida_volta"]
                for mid, d in membros_desl.items()
                if d is not None and isinstance(d, dict) and "custo_ida_volta" in d
            }
            for lugar_id, membros_desl in analises_completas.items()
        }
    deslocamentos = deslocamentos or {}

    teto_aplicado = any(t is not None for t in tetos.values())
    aprovados: list[str] = []
    vetos: list[Veto] = []
    contagem: Counter = Counter()

    for cand in candidatos:
        cand_id = cand.get("id") or cand.get("lugar_id") or ""
        lugar = lugares_base.get(cand_id, cand)

        motivos_do_lugar: list[MotivoVeto] = []

        # -------------------------------------------------------------
        # VETO 2 & 3: Horário de Funcionamento e Validade de Evento
        # -------------------------------------------------------------
        horario_ok, motivo_h, _ = validar_horario_e_evento(lugar, janelas, agora)
        if not horario_ok and motivo_h:
            motivos_do_lugar.append(motivo_h)

        # -------------------------------------------------------------
        # VETO 4: Restrições Alimentares Duras
        # -------------------------------------------------------------
        restr_ok, motivo_r = atende_restricoes_duras(lugar, restricoes)
        if not restr_ok and motivo_r:
            motivos_do_lugar.append(motivo_r)

        # -------------------------------------------------------------
        # VETO DE DESLOCAMENTO: Menor Miséria (> 75 min)
        # -------------------------------------------------------------
        analises_lugar = analises_completas.get(cand_id, {})
        desl_ok, motivo_d = validar_deslocamento_membros(analises_lugar)
        if not desl_ok and motivo_d:
            motivos_do_lugar.append(motivo_d)

        # -------------------------------------------------------------
        # VETO 1: Orçamento Sigiloso com Deslocamento
        # -------------------------------------------------------------
        custo_rs = Decimal(str(lugar.get("custo_medio_rs") or 0))
        desl_custos = deslocamentos.get(cand_id, {})
        orcamento_ok = dentro_do_orcamento_individual(custo_rs, tetos, desl_custos)
        if not orcamento_ok:
            motivos_do_lugar.append("orcamento")

        # -------------------------------------------------------------
        # Consolidação do Candidato
        # -------------------------------------------------------------
        if motivos_do_lugar:
            # Incrementa todos os motivos infringidos para enriquecer o diagnóstico da Pesquisa
            for m in motivos_do_lugar:
                contagem[m] += 1
            # Registra no relatório o primeiro veto encontrado para o lugar
            vetos.append(Veto(id=cand_id, motivo=motivos_do_lugar[0]))
        else:
            # Aprovado em todos os filtros determinísticos!
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
