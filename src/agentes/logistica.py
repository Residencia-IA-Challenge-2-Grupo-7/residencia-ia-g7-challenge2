"""Agente 2: Logística & Justiça (issue #67, docs/semanas/semana-04.md, seção 3.2).

Código puro, sem LLM (RNF-04, ADR 0013): as mesmas entradas dão sempre a mesma saída. Não veta nada; mede e
ordena. Vetar por horário, orçamento ou deslocamento é da Validação (#68).

Para cada candidato da Pesquisa:

1. **Horário:** a primeira janela comum em que o lugar não está fechado nem encerrado, com a certeza do horário
   (aberto 1,0; provável 0,7; incerto 0,4). Fechado em todas: fica a primeira janela, com certeza 0.
2. **Deslocamento:** de cada membro que pode na janela, pelo meio que ele usaria (`escolher_meio`: o mais barato
   que chega em até 75 min, senão o mais rápido). O detalhe de cada pessoa só vai para `analises` (o cofre).
3. **Menor Miséria:** `nota_menor_miseria` pelos tempos, sem saber de quem é cada um.
4. **Pontuação:** 45% aderência ao que o grupo pediu, 35% justiça, 20% certeza do horário, de 0 a 1.

A saída pública é uma lista de `CandidatoAvaliado` (só agregados: pior trajeto, média, diferença), do melhor
para o pior. `gerar_parecer` resume essa lista num texto feito por regra, para a mensagem do agente no grafo.
"""
from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import datetime

from src.agentes.estado import CandidatoAvaliado
from src.interpretador.campos import ROTULOS_TRANSPORTE, PerfilInterpretado
from src.interpretador.numeros import canon
from src.logistica.transporte_df import TEMPO_ACEITAVEL_MIN, escolher_meio, nota_menor_miseria
from src.salas import integracoes as integ
from src.salas.horario_lugar import ano_do_lugar, ler_funcionamento
from src.salas.janelas import JanelaComum
from src.salas.sugestoes import CERTEZA_HORARIO, PESOS, TERMOS_RESTRICAO

MODO_PADRAO = "publico"
"""Quem não disse como vai, vai de ônibus/metrô (o mesmo padrão da Tela 3)."""

PESOS_ADERENCIA = {"tipo": 0.45 / 0.85, "vibe": 0.25 / 0.85, "restricao": 0.15 / 0.85}
"""Os pesos da aderência da Tela 3 sem o termo da busca vetorial (0,15), redistribuídos na mesma proporção.
A busca usa embeddings e pode variar; aqui tudo tem de ser determinístico (RNF-04)."""


def _texto_lugar(lugar: dict) -> str:
    """O texto do lugar onde procurar as restrições (o mesmo da Tela 3)."""
    return canon(" ".join(str(lugar.get(k) or "") for k in
                          ("nome", "tipo_de_role", "resumo_sensorial", "legenda_original", "transcricao_audio_whisper")))


def _aderencia(lugar: dict, perfis: list[PerfilInterpretado]) -> float:
    """0 a 1: quanto o lugar combina com o tipo, as vibes e as restrições de quem pode ir."""
    com_tipo = [p for p in perfis if p.preferencias.tipos]
    f_tipo = (sum(1 for p in com_tipo if lugar.get("tipo_de_role") in p.preferencias.tipos) / len(com_tipo)
              if com_tipo else 0.5)
    com_vibe = [p for p in perfis if p.preferencias.vibes]
    vibes = set(lugar.get("vibes") or [])
    f_vibe = (sum(1 for p in com_vibe if vibes & set(p.preferencias.vibes)) / len(com_vibe)) if com_vibe else 0.5
    if any("Kid Friendly" in p.preferencias.vibes for p in perfis) and not lugar.get("kid_friendly"):
        f_vibe *= 0.5
    restr = {r for p in perfis for r in p.preferencias.restricoes}
    texto = _texto_lugar(lugar)
    f_restr = (sum(1 for r in restr if re.search(TERMOS_RESTRICAO[r], texto)) / len(restr)) if restr else 1.0
    return (PESOS_ADERENCIA["tipo"] * f_tipo + PESOS_ADERENCIA["vibe"] * f_vibe
            + PESOS_ADERENCIA["restricao"] * f_restr)


def _janela(lugar: dict, janelas: list[JanelaComum], agora: datetime):
    """(janela, situação, início do trecho aberto) da primeira janela em que o lugar abre; senão, a primeira."""
    func = ler_funcionamento(lugar.get("horario_funcionamento"), ano_do_lugar(lugar, agora.year))
    primeira = None
    for jc in janelas:
        sit, trecho = func.situacao(jc.inicio, jc.fim)
        inicio = (trecho or (jc.inicio, jc.fim))[0]
        if sit in CERTEZA_HORARIO:
            return jc, sit, inicio
        if primeira is None:
            primeira = (jc, sit, inicio)
    return primeira


def _deslocamento(perfil: PerfilInterpretado, lugar: dict, quando: datetime) -> dict | None:
    modos = perfil.preferencias.transporte or [MODO_PADRAO]
    return escolher_meio([integ.deslocamento(perfil.ra, lugar, m, quando) for m in modos])


def executar_agente_logistica(candidatos: list[dict], origens_membros: Mapping[str, PerfilInterpretado], *,
                              lugares: Mapping[str, dict], janelas: list[JanelaComum], agora: datetime,
                              analises: dict | None = None) -> list[dict]:
    """Candidatos da Pesquisa -> `CandidatoAvaliado` (como dict), do melhor para o pior.

    - `candidatos`: o que a Pesquisa devolveu; só o `id` é usado. Um id fora da base é ignorado (RNF-03).
    - `origens_membros`: {marcador: perfil} do cofre ("m1": PerfilInterpretado). Tem RA, teto e transporte, por
      isso nunca sai daqui; da saída só saem agregados.
    - `lugares`: a base por id (`Cofre.lugares`). `janelas`: as janelas comuns, na ordem do cruzamento.
    - `agora`: o "agora" da sala; dá o ano das datas dos vídeos e deixa a função determinística.
    - `analises`: se vier (`Cofre.analises`), recebe {id do lugar: {marcador: deslocamento ou None}}, o detalhe
      por pessoa que a Validação usa para o orçamento de cada um.

    Sem janela comum não há o que avaliar (a sala avisa antes, RF-17): devolve lista vazia.
    """
    if not janelas:
        return []
    avaliados = []
    for cand in candidatos:
        lugar = lugares.get(cand["id"])
        if lugar is None:
            continue
        jc, situacao, quando = _janela(lugar, janelas, agora)
        presentes = [m for m in sorted(jc.presentes) if m in origens_membros]
        desl_por = {m: _deslocamento(origens_membros[m], lugar, quando) for m in presentes}
        if analises is not None:
            analises[cand["id"]] = desl_por
        conhecidos = [d for d in desl_por.values() if d]
        tempos = [d["minutos"] for d in conhecidos]
        justica = nota_menor_miseria(conhecidos)
        certeza = CERTEZA_HORARIO.get(situacao, 0.0)
        aderencia = _aderencia(lugar, [origens_membros[m] for m in presentes])
        pontuacao = PESOS["aderencia"] * aderencia + PESOS["justica"] * justica / 100 + PESOS["horario"] * certeza
        avaliados.append(CandidatoAvaliado(
            id=cand["id"], nome=lugar.get("nome", ""),
            ra_do_lugar=integ.ra_do_lugar(lugar) or lugar.get("regiao_administrativa", ""),
            janela=jc.texto(), quantos_podem=jc.contagem, horario_situacao=situacao,
            nota_justica=justica,
            pior_trajeto_min=round(max(tempos)) if tempos else None,
            media_trajeto_min=round(sum(tempos) / len(tempos)) if tempos else None,
            diferenca_min=round(max(tempos) - min(tempos)) if tempos else None,
            estimativa_provisoria=len(conhecidos) < len(presentes)
            or any(d.get("estimado_por") == "reserva" for d in conhecidos),
            pontuacao=round(pontuacao, 3),
        ))
    avaliados.sort(key=lambda c: (-c.pontuacao, -c.nota_justica, c.id))
    return [c.model_dump() for c in avaliados]


# ------------------------------------------------------------------ parecer (texto por regra, sem LLM)

def _modo_do_pior(desl_por: Mapping[str, dict | None] | None) -> str | None:
    """Rótulo do meio do pior trajeto ("ônibus/metrô"), sem dizer de quem é. Empate: o primeiro marcador."""
    conhecidos = [d for d in (desl_por or {}).values() if d]
    if not conhecidos:
        return None
    return ROTULOS_TRANSPORTE.get(max(conhecidos, key=lambda d: d["minutos"]).get("modo"))


def _resumo(c: dict, modo: str | None, completo: bool) -> str:
    score = f"score {round(c['pontuacao'] * 100)}"
    if not completo:
        return f"{c['nome']} ({score})"
    if c["pior_trajeto_min"] is None:
        trajeto = "trajeto não calculado"
    else:
        de = f" de {modo}" if modo else ""
        trajeto = f"pior trajeto {c['pior_trajeto_min']} min{de}; média {c['media_trajeto_min']} min"
    prov = "; estimativa provisória" if c["estimativa_provisoria"] else ""
    return f"{c['nome']} ({score}; {trajeto}{prov})"


def gerar_parecer(avaliados: list[dict], analises: Mapping[str, Mapping] | None = None) -> str:
    """Parecer da Logística a partir da saída de `executar_agente_logistica`, sempre o mesmo para a mesma entrada.

    Ex.: "Ranking Logístico: Lugar A (score 81; pior trajeto 38 min de ônibus/metrô; média 27 min), Lugar C
    (score 74). 1 lugar com trajeto acima de 75 min para alguém do grupo."

    O primeiro e o último vêm com os tempos; os do meio, só com o score. Com `analises` (o cofre), diz o meio do
    pior trajeto. Nunca diz de onde alguém sai, quem tem o pior trajeto nem quanto alguém gasta (RNF-02).
    """
    if not avaliados:
        return "Ranking Logístico: nenhum candidato para avaliar."
    ultimo = len(avaliados) - 1
    partes = [_resumo(c, _modo_do_pior((analises or {}).get(c["id"])), i in (0, ultimo))
              for i, c in enumerate(avaliados)]
    texto = "Ranking Logístico: " + ", ".join(partes) + "."
    longe = sum(1 for c in avaliados if (c["pior_trajeto_min"] or 0) > TEMPO_ACEITAVEL_MIN)
    if longe:
        texto += (f" {longe} lugar{'es' if longe > 1 else ''} com trajeto acima de {TEMPO_ACEITAVEL_MIN} min"
                  " para alguém do grupo.")
    return texto
