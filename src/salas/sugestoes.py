"""Monta os 3 a 4 cartões de sugestão da sala (Tela 3), só com lugares da base de 93 (RF-16, RNF-03).

Etapas, todas por código (RNF-04):

1. **Horário (RF-17):** para cada lugar, a primeira janela comum (na ordem do cruzamento) em que ele não está
   fechado nem encerrado.
2. **Deslocamento:** de cada participante que pode naquela janela até o lugar, pelo meio de transporte dele.
3. **Orçamento (RF-11, RF-17):** o consumo médio precisa caber no teto do grupo (função da Eduarda), e o consumo
   mais o transporte de cada participante precisa caber no teto dele. A conta por pessoa fica no servidor; o
   descarte é contado como "fora do orçamento do grupo", nunca atribuído a alguém.
4. **Pontuação:** 45% aderência ao que o grupo pediu, 35% nota de justiça (Menor Miséria, RF-19), 20% certeza do
   horário. Ficam os 4 melhores, no máximo 2 por RA, para o grupo ter opção de região.
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from decimal import Decimal

from src.interpretador.campos import PerfilInterpretado
from src.interpretador.numeros import canon
from src.salas import integracoes as integ
from src.salas.horario_lugar import ano_do_lugar, ler_funcionamento
from src.salas.janelas import JanelaComum, texto_intervalo
from src.salas.modelos import Sugestao

PESOS = {"aderencia": 0.45, "justica": 0.35, "horario": 0.20}
CERTEZA_HORARIO = {"aberto": 1.0, "provavel": 0.7, "incerto": 0.4}
HORA_PREFERIDA = {"Bar / Boteco / Pub": 19, "Restaurante / Gastronomia": 19, "Cafeteria / Doceria": 16,
                  "Experiência / Evento": 18, "Ao Ar Livre / Parque": 15}
DURACAO_MAXIMA = timedelta(hours=4)
TERMOS_RESTRICAO = {"alim_vegetariano": r"vegetarian|vegan", "alim_vegano": r"vegan",
                    "alim_sem_gluten": r"sem gluten|gluten free", "alim_sem_lactose": r"sem lactose|zero lactose",
                    "acess_entrada_sem_degrau": r"acessivel|acessibilidade|rampa"}
NOME_RESTRICAO = {"alim_vegetariano": "opção vegetariana", "alim_vegano": "opção vegana",
                  "alim_sem_gluten": "opção sem glúten", "alim_sem_lactose": "opção sem lactose",
                  "acess_entrada_sem_degrau": "acessibilidade"}
LETRAS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
TEMPO_ACEITAVEL_MIN = 75


@dataclass
class ResultadoSugestoes:
    sugestoes: list[Sugestao]
    avisos: list[str] = field(default_factory=list)
    descartes: Counter = field(default_factory=Counter)
    teto_aplicado: bool = False


def _deslocamento(perfil: PerfilInterpretado, lugar: dict) -> dict | None:
    """Entre os meios que a pessoa disse que usa, o mais barato que chega em até 75 min; se nenhum chegar, o mais
    rápido. Sem meio informado, ônibus/metrô. Assim quem disse "metrô ou Uber" não paga Uber à toa (Menor Miséria)."""
    modos = perfil.preferencias.transporte or ["publico"]
    opcoes = [d for d in (integ.deslocamento(perfil.ra, lugar, m) for m in modos) if d]
    if not opcoes:
        return None
    viaveis = [d for d in opcoes if d["minutos"] <= TEMPO_ACEITAVEL_MIN]
    if viaveis:
        return min(viaveis, key=lambda d: (d["custo_ida_volta"], d["minutos"]))
    return min(opcoes, key=lambda d: (d["minutos"], d["custo_ida_volta"]))


def _texto_lugar(lugar: dict) -> str:
    return canon(" ".join(str(lugar.get(k) or "") for k in
                          ("nome", "tipo_de_role", "resumo_sensorial", "legenda_original", "transcricao_audio_whisper")))


def _aderencia(lugar: dict, perfis: list[PerfilInterpretado], texto_grupo: str) -> tuple[float, int, int]:
    """(0 a 1, quantos pediram o tipo do lugar, quantos disseram algum tipo)."""
    com_tipo = [p for p in perfis if p.preferencias.tipos]
    pediram = sum(1 for p in com_tipo if lugar.get("tipo_de_role") in p.preferencias.tipos)
    f_tipo = pediram / len(com_tipo) if com_tipo else 0.5
    com_vibe = [p for p in perfis if p.preferencias.vibes]
    vibes = set(lugar.get("vibes") or [])
    f_vibe = (sum(1 for p in com_vibe if vibes & set(p.preferencias.vibes)) / len(com_vibe)) if com_vibe else 0.5
    if any("Kid Friendly" in p.preferencias.vibes for p in perfis) and not lugar.get("kid_friendly"):
        f_vibe *= 0.5
    texto = _texto_lugar(lugar)
    restr = {r for p in perfis for r in p.preferencias.restricoes}
    f_restr = (sum(1 for r in restr if re.search(TERMOS_RESTRICAO[r], texto)) / len(restr)) if restr else 1.0
    leticia = integ.aderencia(texto_grupo, lugar)
    f_busca = leticia if leticia is not None else 0.5
    nota = 0.45 * f_tipo + 0.25 * f_vibe + 0.15 * f_restr + 0.15 * f_busca
    return nota, pediram, len(com_tipo)


def _horario_sugerido(inicio: datetime, fim: datetime, tipo: str) -> tuple[datetime, datetime]:
    pref = HORA_PREFERIDA.get(tipo)
    if pref is not None:
        cand = datetime.combine(inicio.date(), time(pref))
        if inicio <= cand <= fim - timedelta(hours=2):
            inicio = cand
    return inicio, min(fim, inicio + DURACAO_MAXIMA)


def _reais(v: Decimal) -> str:
    return "R$ " + f"{v:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def _explicacao(jc: JanelaComum, desl: list[dict], teto: bool, pediram: int, com_tipo: int, tipo: str,
                situacao: str, faltam: list[str]) -> str:
    partes = [jc.contagem.capitalize()]
    if desl:
        tempos = [d["minutos"] for d in desl]
        prov = " (estimativa provisória)" if any(d["estimado_por"] == "reserva" for d in desl) else ""
        partes.append(f"ninguém leva mais de ~{round(max(tempos))} min para chegar, média de ~{round(sum(tempos) / len(tempos))} min{prov}")
    else:
        partes.append("tempo de chegada ainda não calculado para este grupo")
    if teto:
        partes.append("cabe no orçamento de todo o grupo, transporte incluído")
    if com_tipo and pediram:
        partes.append(f"{pediram} de {com_tipo} pediram {tipo.split(' / ')[0].lower()}")
    partes.append({"aberto": "aberto nesse horário segundo o vídeo",
                   "provavel": "abre nesse dia; confirme o horário antes de ir",
                   "incerto": "o vídeo não informa o horário; confirme antes de ir"}[situacao])
    if faltam:
        partes.append("confirme " + " e ".join(faltam) + " no local")
    return "; ".join(partes) + "."


def gerar(perfis: dict[str, PerfilInterpretado], janelas: list[JanelaComum], lugares: tuple[dict, ...] | list[dict],
          agora: datetime, maximo: int = 4) -> ResultadoSugestoes:
    """{participante: perfil confirmado} + janelas comuns -> até `maximo` cartões, do melhor para o pior."""
    res = ResultadoSugestoes([])
    if not janelas:
        res.avisos.append("Não há horário em que pelo menos 2 pessoas possam. Que tal ampliar os dias?")
        return res
    teto = integ.teto_do_grupo([p.teto for p in perfis.values() if p.teto is not None])
    res.teto_aplicado = teto is not None
    texto_grupo = " ".join(p.preferencias.texto_busca for p in perfis.values() if p.preferencias.texto_busca)
    restr = sorted({r for p in perfis.values() for r in p.preferencias.restricoes})
    candidatos = []
    for lugar in lugares:
        func = ler_funcionamento(lugar.get("horario_funcionamento"), ano_do_lugar(lugar, agora.year))
        escolha = None
        for jc in janelas:
            sit, trecho = func.situacao(jc.inicio, jc.fim)
            if sit in CERTEZA_HORARIO:
                escolha = (jc, sit, trecho)
                break
        if escolha is None:
            res.descartes["horario"] += 1
            continue
        jc, sit, trecho = escolha
        presentes = [perfis[p] for p in sorted(jc.presentes) if p in perfis]
        desl_por = {p: _deslocamento(perfis[p], lugar) for p in sorted(jc.presentes)
                    if p in perfis}
        conhecidos = [d for d in desl_por.values() if d]
        consumo = Decimal(str(lugar.get("custo_medio_rs") or 0)).quantize(Decimal("0.01"))
        gastos = [consumo + d["custo_ida_volta"] for d in conhecidos] or [consumo]
        estoura = (teto is not None and consumo > teto) or any(
            perfis[p].teto is not None and consumo + (d["custo_ida_volta"] if d else 0) > perfis[p].teto
            for p, d in desl_por.items())
        if estoura:
            res.descartes["orcamento"] += 1
            continue
        ader, pediram, com_tipo = _aderencia(lugar, presentes, texto_grupo)
        justica = integ.nota_justica(conhecidos)
        pont = (PESOS["aderencia"] * ader + PESOS["justica"] * justica / 100
                + PESOS["horario"] * CERTEZA_HORARIO[sit])
        texto = _texto_lugar(lugar)
        faltam = [NOME_RESTRICAO[r] for r in restr if not re.search(TERMOS_RESTRICAO[r], texto)]
        ini, fim = _horario_sugerido(*(trecho or (jc.inicio, jc.fim)), lugar.get("tipo_de_role", ""))
        tempos = [d["minutos"] for d in conhecidos]
        candidatos.append((pont, justica, lugar, jc, sit, ini, fim, consumo, gastos, tempos, desl_por, pediram,
                           com_tipo, faltam))

    candidatos.sort(key=lambda c: (-c[0], -c[1], c[7]))
    por_ra: Counter = Counter()
    nomes: set[str] = set()
    escolhidos = []
    for c in candidatos:
        lugar = c[2]
        ra = integ.ra_do_lugar(lugar)
        nome = canon(lugar.get("nome", ""))
        if nome in nomes or por_ra[ra] >= 2:
            continue
        escolhidos.append(c)
        nomes.add(nome)
        por_ra[ra] += 1
        if len(escolhidos) == maximo:
            break

    for i, (pont, justica, lugar, jc, sit, ini, fim, consumo, gastos, tempos, desl_por, pediram, com_tipo,
            faltam) in enumerate(escolhidos):
        tipo = lugar.get("tipo_de_role", "")
        conhecidos = [d for d in desl_por.values() if d]
        res.sugestoes.append(Sugestao(
            id=LETRAS[i], posicao=i + 1, lugar_id=str(lugar.get("id")), nome=lugar.get("nome", ""), tipo=tipo,
            ra=integ.ra_do_lugar(lugar), regiao_texto=lugar.get("regiao_administrativa", ""),
            endereco=lugar.get("endereco", ""), inicio=ini, fim=fim, horario_texto=texto_intervalo(ini, fim),
            horario_situacao=sit, contagem=jc.contagem, consumo_rs=consumo, gasto_min=min(gastos),
            gasto_max=max(gastos), tempo_medio_min=round(sum(tempos) / len(tempos)) if tempos else None,
            tempo_max_min=round(max(tempos)) if tempos else None, nota_justica=justica, pontuacao=round(pont, 3),
            explicacao=_explicacao(jc, conhecidos, res.teto_aplicado, pediram, com_tipo, tipo, sit, faltam),
            tiktok_url=lugar.get("tiktok_url"),
            fonte=f"Vídeo de {lugar.get('autor_tiktok', 'autor desconhecido')} publicado em {lugar.get('data_publicacao', 's/d')}",
            vibes=list(lugar.get("vibes") or []),
            por_participante={p: ({"modo": d["modo"], "minutos": d["minutos"],
                                   "gasto_total_rs": str(consumo + d["custo_ida_volta"])} if d else None)
                              for p, d in desl_por.items()},
        ))

    if res.descartes["orcamento"] and len(res.sugestoes) < 3:
        res.avisos.append(f"{res.descartes['orcamento']} lugares ficaram fora do orçamento do grupo.")
    if len(res.sugestoes) < 3:
        res.avisos.append(f"Só {len(res.sugestoes)} lugar(es) da base atendem ao horário e ao orçamento do grupo.")
    return res
