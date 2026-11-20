"""Grafo dos agentes da semana 4 em LangGraph (ADR 0015, issue #71).

    START ─▶ no_pessoal ×N (Send, em paralelo) ─▶ no_consolidar_grupo ─▶ no_pesquisa ─▶ no_logistica ─▶ no_validacao
                                                                         ▲                                    │
                                                    avaliar_convergencia └── menos de 3 validados e voltas < 2 ┤
                                                                                                               ▼
                no_finalizar ◀── aprovado ou reserva ── no_validacao_textos ◀────────────────────── no_comunicacao
                     │                                         │  reprovado (1 reescrita)  ▲
                     ▼                                         └───────────────────────────┘
                    END

O estado do grafo (`MultiAgentState`, estado.py) só tem mensagens anônimas. O cofre, com os 4 campos de cada
membro, fica fora do estado, preso ao grafo na construção: só os nós de código o leem (RNF-02). Cada nó é um span
do Langfuse com entrada e saída escolhidas à mão (`_registrar`), nunca o estado inteiro.

    from src.agentes.grafo import executar_fluxo_multiagente
    final = executar_fluxo_multiagente({"membros": [{"nome": ..., "origem": ..., "horarios": ..., "teto": ...,
                                                     "preferencias": ...}, ...]})
    final["resultado_final_cartoes"]   # cartões públicos, com o texto dos agentes

Com uma sala de `src/salas`: `executar(cofre_da_sala(sala, lugares, agora, store), ClienteLLM())`.
"""
from __future__ import annotations

import re
import time
from collections import Counter
from datetime import datetime
from decimal import Decimal
from typing import Callable

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.store.memory import InMemoryStore
from langgraph.types import Send

from src.agentes import comunicacao, juiz, logistica, pesquisa, pessoal, validacao
from src.agentes.contratos import Cofre, Membro
from src.agentes.estado import MultiAgentState, PedidoNovaBusca
from src.agentes.llm import ClienteLLM, versao_prompt
from src.interpretador.campos import interpretar_campos
from src.salas import integracoes as integ
from src.salas.horario_lugar import ano_do_lugar, ler_funcionamento
from src.salas.janelas import cruzar, texto_intervalo
from src.salas.modelos import Sala, Sugestao
from src.salas.sugestoes import (CERTEZA_HORARIO, NOME_RESTRICAO, TERMOS_RESTRICAO, _aderencia, _explicacao,
                                 _horario_sugerido, _texto_lugar)

MAX_VOLTAS_PESQUISA = 2
MAX_REESCRITAS = 1
NOMES = {"no_pessoal": "Agente Pessoal", "no_consolidar_grupo": "Orquestrador", "no_pesquisa": "Pesquisa",
         "no_logistica": "Logística", "no_validacao": "Validação", "no_comunicacao": "Comunicação",
         "no_validacao_textos": "Validação (textos)", "no_finalizar": "Orquestrador"}


def avaliar_convergencia(estado: MultiAgentState) -> str:
    """Aresta condicional depois da Validação (issue #71): volta para a Pesquisa enquanto houver menos de
    `validacao.MINIMO_CARTOES` (3) candidatos validados e `iteracao_pesquisa` < `MAX_VOLTAS_PESQUISA` (2); senão segue
    para a Comunicação com o que passou, ou direto para o fim se nada passou (não há cartão para escrever).
    A Pesquisa conta a volta ao receber o pedido, então o laço tem fim."""
    validados = len(estado.get("candidatos_validados") or [])
    if validados < validacao.MINIMO_CARTOES and estado.get("iteracao_pesquisa", 0) < MAX_VOLTAS_PESQUISA:
        return "no_pesquisa"
    return "no_comunicacao" if validados else "no_finalizar"


def _todos(contagem: str) -> bool:
    """'4 de 4' -> True; '3 de 4' -> False."""
    m = re.match(r"(\d+) de (\d+)", contagem or "")
    return bool(m and m.group(1) == m.group(2))


def _janela_e_trecho(lugar: dict, cofre: Cofre):
    """(janela, situação, trecho aberto) com a mesma regra da Logística: a primeira janela em que o lugar abre."""
    func = ler_funcionamento(lugar.get("horario_funcionamento"), ano_do_lugar(lugar, cofre.agora.year))
    primeira = None
    for jc in cofre.janelas:
        sit, trecho = func.situacao(jc.inicio, jc.fim)
        primeira = primeira or (jc, sit, trecho)
        if sit in CERTEZA_HORARIO:
            return jc, sit, trecho
    return primeira


def _msg(de: str, para: str, texto: str, **extra) -> dict:
    return {"de": de, "para": para, "texto": texto, "em": time.strftime("%H:%M:%S"), **extra}


def _registrar(entrada=None, saida=None, **metadados) -> None:
    """Entrada e saída do span atual no Langfuse, escolhidas à mão. Sem chaves, não faz nada."""
    try:
        from opentelemetry import trace
        if not trace.get_current_span().is_recording():
            return
        from langfuse import get_client
        get_client().update_current_span(input=entrada, output=saida, metadata=metadados or None)
    except Exception:
        pass


def _observado(nome: str, tipo: str = "agent"):
    try:
        from langfuse import observe
        return observe(name=nome, as_type=tipo, capture_input=False, capture_output=False)
    except Exception:  # sem Langfuse instalado
        return lambda f: f


# ------------------------------------------------------------------ cofre a partir de uma sala real

def cofre_da_sala(sala: Sala, lugares, agora: datetime, store=None, usuarios: dict[str, str] | None = None) -> Cofre:
    """Monta o cofre com os participantes confirmados da sala (src/salas). `usuarios`: {participante: id
    pseudônimo permanente} para ler o log pessoal; sem ele, cada participante é um usuário novo."""
    confirmados = sala.confirmados()
    membros = {}
    for i, p in enumerate(confirmados, 1):
        mid = f"m{i}"
        membros[mid] = Membro(id=mid, usuario=(usuarios or {}).get(p.id, f"sala:{sala.codigo}:{p.id}"),
                              nome=p.nome, perfil=p.perfil)
    janelas = cruzar({mid: m.perfil.janelas for mid, m in membros.items()}, agora)
    return Cofre(sala_id=sala.codigo, membros=membros, janelas=janelas, agora=agora,
                 lugares={l["id"]: l for l in lugares},
                 store=store if store is not None else InMemoryStore())


# ------------------------------------------------------------------ o grafo

def construir_grafo(cofre: Cofre, cliente: ClienteLLM, *, busca: str = "lexica", juiz_parecer: bool = False,
                    checkpointer=None):
    """`juiz_parecer`: liga a 1ª passagem do juiz (#72) sobre os motivos da Pesquisa; a 2ª, sobre os cartões,
    roda sempre (sem LLM, cai nas regras do próprio juiz)."""
    lugares = list(cofre.lugares.values())

    def distribuir(estado: MultiAgentState):
        return [Send("no_pessoal", {"membro": m}) for m in estado["membros"]]

    @_observado("agente_pessoal")
    def no_pessoal(entrada: dict):
        m = cofre.membros[entrada["membro"]]
        saida = pessoal.agente_pessoal(m, cofre.store, cofre.agora, cofre.nomes())
        cofre.perfis_efetivos[m.id] = saida.perfil_efetivo   # canais 1, 2 e 4 ficam no cofre
        a = saida.publico()                                   # canal 3 vai para o grupo
        _registrar({"campos_preenchidos": 4}, {"preferencias": len(a["tipos"]) + len(a["vibes"]),
                                                "restricoes": len(a["restricoes"]),
                                                "itens_do_log_usados": a["itens_do_log_usados"]})
        return {"membros_anonimos": [a]}

    @_observado("consolidar_grupo", "chain")
    def no_consolidar_grupo(estado: MultiAgentState):
        perfis = estado["membros_anonimos"]
        n = len(perfis)
        conta = lambda campo: Counter(x for p in perfis for x in set(p[campo]))  # noqa: E731
        tipos = conta("tipos")
        grupo = {
            "tamanho": n,
            "tipos": [t for t, _ in tipos.most_common()],
            "tipos_pedidos": {t: f"{c} de {n}" for t, c in tipos.most_common()},
            "vibes": [v for v, _ in conta("vibes").most_common()],
            "evitar": sorted(conta("evitar")),
            "restricoes": sorted(conta("restricoes")),
            "trechos_pedido": [p["trecho_pedido"] for p in perfis if p["trecho_pedido"]],
            "janela": (f"{cofre.janelas[0].texto()} ({cofre.janelas[0].contagem})" if cofre.janelas else None),
        }
        usados = sum(p["itens_do_log_usados"] for p in perfis)
        avisos = [] if cofre.janelas else ["Não há horário em que pelo menos 2 pessoas possam."]
        texto = (f"{n} agentes pessoais responderam. Tipos pedidos: "
                 + (", ".join(f"{t.split(' / ')[0]} ({c})" for t, c in grupo["tipos_pedidos"].items()) or "nenhum")
                 + f". Restrições do grupo: {len(grupo['restricoes'])}. Itens de memória usados: {usados}."
                 + (f" Melhor janela: {grupo['janela']}." if grupo["janela"] else ""))
        _registrar({"membros_anonimos": n}, grupo)
        return {"preferencias_grupo": grupo, "iteracao_pesquisa": 0, "reescritas": 0, "vistos": [],
                "candidatos_pesquisa": [], "pedido_nova_busca": None, "historico_erros": avisos,
                "mensagens": [_msg("Agentes Pessoais", "Pesquisa", texto)]}

    def depois_de_consolidar(estado: MultiAgentState):
        return "no_pesquisa" if cofre.janelas else "no_finalizar"

    @_observado("pesquisa")
    def no_pesquisa(estado: MultiAgentState):
        pedido = estado.get("pedido_nova_busca")
        aprovados = set((estado.get("relatorio_validacao") or {}).get("aprovados", []))
        mantidos = [c for c in estado.get("candidatos_pesquisa", []) if c["id"] in aprovados]
        r = pesquisa.pesquisar(estado["preferencias_grupo"], pedido, lugares, cliente, busca=busca,
                               excluir=set(estado.get("vistos", [])))
        novos = [c for c in r["candidatos"] if c["id"] not in aprovados]
        candidatos = mantidos + novos
        docs = {**estado.get("documentos", {}), **r["documentos"]}
        nomes = ", ".join(cofre.lugares[c["id"]]["nome"] for c in novos[:4])
        texto = (f"{'Nova busca: ' if pedido else ''}encontrei {len(novos)} candidatos na base "
                 f"({len(r['consultas'])} consultas, busca {r['buscas'][0]['busca'] if r['buscas'] else '?'}). "
                 f"Destaques: {nomes}." + (f" Observação: {r['observacao']}" if r["observacao"] else ""))
        _registrar({"preferencias_grupo": estado["preferencias_grupo"], "pedido": pedido},
                   {"consultas": r["consultas"], "candidatos": [c["id"] for c in novos]},
                   usou_llm=r["usou_llm"], trechos_descartados=r["descartados"], prompt=versao_prompt("pesquisa"))
        return {"candidatos_pesquisa": candidatos, "documentos": docs, "pedido_nova_busca": None,
                "iteracao_pesquisa": estado.get("iteracao_pesquisa", 0) + (1 if pedido else 0),
                "vistos": sorted(set(estado.get("vistos", [])) | {c["id"] for c in r["candidatos"]}),
                "mensagens": [_msg("Pesquisa", "Logística", texto, usou_llm=r["usou_llm"],
                                   consultas=[c["texto"] for c in r["consultas"]])]}

    @_observado("logistica", "tool")
    def no_logistica(estado: MultiAgentState):
        ranking = logistica.executar_agente_logistica(
            estado["candidatos_pesquisa"], cofre.perfis_efetivos, lugares=cofre.lugares, janelas=cofre.janelas,
            agora=cofre.agora, analises=cofre.analises)
        _registrar({"candidatos": len(estado["candidatos_pesquisa"])},
                   [{k: r[k] for k in ("id", "nota_justica", "pior_trajeto_min", "pontuacao")} for r in ranking])
        return {"candidatos_avaliados": ranking,
                "mensagens": [_msg("Logística", "Validação", logistica.gerar_parecer(ranking, cofre.analises))]}

    @_observado("validacao", "guardrail")
    def no_validacao(estado: MultiAgentState):
        # 1ª passagem do juiz (#72, opcional): derruba só o candidato cujo motivo contradiz o documento
        julgados = set(estado.get("julgados", []))
        novos = [c for c in estado["candidatos_pesquisa"] if c["id"] not in julgados]
        derrubados: set[str] = set()
        vereditos: dict = {}
        if juiz_parecer and novos:
            julgamento, _ = juiz.julgar_parecer_pesquisa(novos, llm=cliente, base_completa=cofre.lugares,
                                                         devolver_status=True)
            derrubados = set(juiz.filtrar_candidatos_aprovados_pelo_juiz(novos, julgamento)[1])
            vereditos = dict(Counter(a.veredito for a in julgamento.afirmacoes))
        ranking = [r for r in estado["candidatos_avaliados"] if r["id"] not in derrubados]
        rel = validacao.validar_candidatos_regras(ranking, cofre=cofre)
        res = rel.model_dump()
        res["derrubados_pelo_juiz"] = sorted(derrubados)
        voltas = estado.get("iteracao_pesquisa", 0)
        validados = validacao.selecionar_cartoes(ranking, res["aprovados"])
        parciais = sum(1 for r in validados if not _todos(r["quantos_podem"]))
        vetos = ", ".join(f"{c} por {m}" for m, c in res["contagem"].items() if c) or "nenhum"
        destino = avaliar_convergencia({"candidatos_validados": validados, "iteracao_pesquisa": voltas})
        pedido = None
        if destino == "no_pesquisa":
            pedido = PedidoNovaBusca(faltam=validacao.MINIMO_CARTOES - len(validados), vetos=res["contagem"],
                                     ja_vistos=len(estado.get("vistos", []))).model_dump()
            texto = (f"Só {len(validados)} {'lugar passou' if len(validados) == 1 else 'lugares passaram'} "
                     f"(vetos: {vetos}{'; ' + str(len(derrubados)) + ' derrubados pelo juiz' if derrubados else ''}). "
                     f"Pesquisa, preciso de mais {pedido['faltam']} candidatos.")
            para = "Pesquisa"
        elif destino == "no_finalizar":
            texto = (f"Nenhum lugar passou em horário, deslocamento, orçamento e restrições depois de {voltas} "
                     f"novas buscas (vetos: {vetos}). Sem cartões: o grupo precisa flexibilizar algum critério.")
            para = "Orquestrador"
        else:
            texto = (f"Validação concluída: {len(validados)} lugares para os cartões (vetos: {vetos})."
                     + (f" {parciais} só cabem numa janela em que nem todos podem; o cartão mostra quantos."
                        if parciais else "")
                     + (" Menos de 3 opções: aviso o grupo." if len(validados) < validacao.MINIMO_CARTOES else "")
                     + " Comunicação, pode escrever.")
            para = "Comunicação"
        _registrar({"ranking": [r["id"] for r in ranking]}, {k: res[k] for k in ("aprovados", "contagem")},
                   juiz=vereditos, volta=voltas)
        erros = [f"validacao (volta {voltas}): {v['id']} vetado por {v['motivo']}" for v in res["vetos"]] + \
            [f"validacao (volta {voltas}): {i} derrubado pelo juiz do parecer" for i in sorted(derrubados)]
        return {"relatorio_validacao": res, "pedido_nova_busca": pedido, "candidatos_validados": validados,
                "julgados": sorted(julgados | {c["id"] for c in novos}), "historico_erros": erros,
                "candidatos_pesquisa": [c for c in estado["candidatos_pesquisa"] if c["id"] not in derrubados],
                "mensagens": [_msg("Validação", para, texto, vereditos_juiz=vereditos or None)]}

    @_observado("comunicacao")
    def no_comunicacao(estado: MultiAgentState):
        res = estado["relatorio_validacao"]
        fatos = comunicacao.montar_fatos([c["id"] for c in estado["candidatos_validados"]],
                                         estado["candidatos_avaliados"], estado["candidatos_pesquisa"],
                                         estado.get("documentos", {}), res["teto_aplicado"])
        pedido = {k: estado["preferencias_grupo"][k] for k in ("tipos", "vibes", "evitar", "trechos_pedido")}
        correcoes = estado.get("reprovados") if estado.get("reescritas") else None
        r = comunicacao.escrever(fatos, pedido, cliente, correcoes)
        cartoes = r["cartoes"]
        if correcoes and estado.get("cartoes"):  # na reescrita, só os reprovados mudam
            novos = {c["id"]: c for c in cartoes}
            cartoes = [novos[c["id"]] if c["id"] in correcoes else c for c in estado["cartoes"]]
        _registrar({"fatos": fatos, "correcoes": correcoes}, cartoes, usou_llm=r["usou_llm"],
                   prompt=versao_prompt("comunicacao"))
        texto = f"{'Reescrevi' if correcoes else 'Escrevi'} {len(cartoes)} cartões: " + \
            "; ".join(f"{c['id']}) {c['titulo']}" for c in cartoes) + "."
        # Na reescrita, os cartões que não foram reprovados continuam com o texto de antes (#71, revisão do #80)
        por_llm = (estado.get("cartoes_por_llm", False) and r["usou_llm"]) if correcoes else r["usou_llm"]
        return {"fatos": fatos, "cartoes": cartoes, "cartoes_por_llm": por_llm,
                "mensagens": [_msg("Comunicação", "Validação", texto, usou_llm=r["usou_llm"])]}

    @_observado("validacao_textos", "guardrail")
    def no_validacao_textos(estado: MultiAgentState):
        # Varredura em código (nomes e RAs do cofre, que o juiz não vê) + 2ª passagem do juiz (#72)
        reprovados = {k: list(v) for k, v in validacao.verificar_cartoes(estado["cartoes"], estado["fatos"],
                                                                          cofre)["reprovados"].items()}
        julgamento, usou_juiz = juiz.julgar_cartoes_comunicacao(estado["cartoes"], estado["fatos"], llm=cliente,
                                                                 base_completa=cofre.lugares, devolver_status=True)
        for letra, motivos in juiz.avaliar_reprovacoes_cartoes(julgamento).items():
            reprovados.setdefault(letra, []).extend(m for m in motivos if m not in reprovados[letra])
        vereditos = dict(Counter(a.veredito for a in julgamento.afirmacoes))
        exposicoes = [e.model_dump() for e in julgamento.exposicoes]
        reescritas = estado.get("reescritas", 0)
        if reprovados and reescritas < MAX_REESCRITAS:
            texto = "Cartões reprovados: " + "; ".join(f"{k} ({', '.join(v)})" for k, v in reprovados.items()) + \
                ". Comunicação, reescreva."
            para, reescritas = "Comunicação", reescritas + 1
        else:
            texto = (f"{len(estado['cartoes'])} cartões aprovados: a varredura não achou número, nome nem origem "
                     f"de ninguém, e o juiz {'(LLM)' if usou_juiz else '(regras)'} não achou contradição nem "
                     "exposição." if not reprovados
                     else "Ainda reprovados depois da reescrita: " + ", ".join(reprovados) + "; uso o texto de reserva.")
            para = "Orquestrador"
        _registrar({"cartoes": len(estado["cartoes"])}, {"reprovados": reprovados}, juiz=vereditos,
                   juiz_llm=usou_juiz, exposicoes=len(exposicoes), reescrita=estado.get("reescritas", 0))
        erros = [f"validacao_textos (reescrita {estado.get('reescritas', 0)}): cartão {k} reprovado por "
                 f"{', '.join(v)}" for k, v in reprovados.items()]
        return {"reprovados": reprovados, "reescritas": reescritas, "historico_erros": erros,
                "mensagens": [_msg("Validação", para, texto, vereditos_juiz=vereditos or None,
                                   exposicoes=exposicoes or None)]}

    def depois_dos_textos(estado: MultiAgentState):
        return "no_comunicacao" if estado["mensagens"][-1]["para"] == "Comunicação" else "no_finalizar"

    @_observado("finalizar", "chain")
    def no_finalizar(estado: MultiAgentState):
        res = estado.get("relatorio_validacao") or {"aprovados": [], "teto_aplicado": False}
        escolhidos = [c["id"] for c in estado.get("candidatos_validados") or []]
        fatos = {f["id"]: f for f in estado.get("fatos", [])}
        reprovados = estado.get("reprovados") or {}
        textos = {c["id"]: (comunicacao.texto_reserva(fatos[c["id"]], seguro=True) if c["id"] in reprovados else c)
                  for c in estado.get("cartoes", [])}
        restr = sorted({r for p in cofre.perfis_efetivos.values() for r in p.preferencias.restricoes})
        texto_grupo = " ".join(p.preferencias.texto_busca for p in cofre.perfis_efetivos.values())
        avaliados = {r["id"]: r for r in estado.get("candidatos_avaliados", [])}
        cofre.sugestoes = []
        finais = []
        for i, (letra, lid) in enumerate(zip("ABCD", escolhidos)):
            lugar, r = cofre.lugares[lid], avaliados[lid]
            jc, sit, trecho = _janela_e_trecho(lugar, cofre)
            ini, fim = _horario_sugerido(*(trecho or (jc.inicio, jc.fim)), lugar.get("tipo_de_role", ""))
            desl_por = cofre.analises.get(lid, {})
            consumo = Decimal(str(lugar.get("custo_medio_rs") or 0)).quantize(Decimal("0.01"))
            presentes = [cofre.perfis_efetivos[m] for m in sorted(jc.presentes) if m in cofre.perfis_efetivos]
            _, pediram, com_tipo = _aderencia(lugar, presentes, texto_grupo)
            conhecidos = [d for d in desl_por.values() if d]
            gastos = [consumo + d["custo_ida_volta"] for d in conhecidos] or [consumo]
            tempos = [d["minutos"] for d in conhecidos]
            faltam = [NOME_RESTRICAO[x] for x in restr if x in TERMOS_RESTRICAO
                      and not re.search(TERMOS_RESTRICAO[x], _texto_lugar(lugar))]
            s = Sugestao(
                id=letra, posicao=i + 1, lugar_id=lid, nome=lugar.get("nome", ""), tipo=lugar.get("tipo_de_role", ""),
                ra=integ.ra_do_lugar(lugar), regiao_texto=lugar.get("regiao_administrativa", ""),
                endereco=lugar.get("endereco", ""), inicio=ini, fim=fim,
                horario_texto=texto_intervalo(ini, fim), horario_situacao=sit, contagem=jc.contagem,
                consumo_rs=consumo, gasto_min=min(gastos), gasto_max=max(gastos),
                tempo_medio_min=round(sum(tempos) / len(tempos)) if tempos else None,
                tempo_max_min=round(max(tempos)) if tempos else None, nota_justica=r["nota_justica"],
                pontuacao=r["pontuacao"],
                explicacao=_explicacao(jc, conhecidos, res["teto_aplicado"], pediram, com_tipo,
                                       lugar.get("tipo_de_role", ""), sit, faltam),
                tiktok_url=lugar.get("tiktok_url"),
                fonte=f"Vídeo de {lugar.get('autor_tiktok', 'autor desconhecido')} publicado em "
                      f"{lugar.get('data_publicacao', 's/d')}",
                vibes=list(lugar.get("vibes") or []),
                por_participante={m: ({"modo": d["modo"], "minutos": d["minutos"],
                                       "gasto_total_rs": str(consumo + d["custo_ida_volta"])} if d else None)
                                  for m, d in desl_por.items()})
            cofre.sugestoes.append(s)
            t = textos.get(letra, {})
            finais.append({**s.publico(), "titulo": t.get("titulo", s.nome), "resumo_acesso": t.get("resumo_acesso", ""),
                           "por_que_combina": t.get("por_que_combina", ""),
                           "texto_por": ("agente_comunicacao" if estado.get("cartoes_por_llm") and letra not in reprovados
                                         else "reserva_por_regras")})
        if not finais:
            fecho = "Nenhum lugar da base atende o grupo nesta janela: sem cartões para votar."
        elif len(finais) < validacao.MINIMO_CARTOES:
            fecho = f"Só {len(finais)} cartões prontos para a votação (menos de 3 opções viáveis na base)."
        else:
            fecho = f"{len(finais)} cartões prontos para a votação."
        _registrar({"aprovados": escolhidos}, [{k: c[k] for k in ("id", "nome", "titulo")} for c in finais])
        return {"resultado_final_cartoes": finais, "mensagens": [_msg("Orquestrador", "Tela 3", fecho)]}

    g = StateGraph(MultiAgentState)
    for nome, f in (("no_pessoal", no_pessoal), ("no_consolidar_grupo", no_consolidar_grupo),
                    ("no_pesquisa", no_pesquisa), ("no_logistica", no_logistica), ("no_validacao", no_validacao),
                    ("no_comunicacao", no_comunicacao), ("no_validacao_textos", no_validacao_textos),
                    ("no_finalizar", no_finalizar)):
        g.add_node(nome, f)
    g.add_conditional_edges(START, distribuir, ["no_pessoal"])
    g.add_edge("no_pessoal", "no_consolidar_grupo")
    g.add_conditional_edges("no_consolidar_grupo", depois_de_consolidar, ["no_pesquisa", "no_finalizar"])
    g.add_edge("no_pesquisa", "no_logistica")
    g.add_edge("no_logistica", "no_validacao")
    g.add_conditional_edges("no_validacao", avaliar_convergencia, ["no_pesquisa", "no_comunicacao", "no_finalizar"])
    g.add_edge("no_comunicacao", "no_validacao_textos")
    g.add_conditional_edges("no_validacao_textos", depois_dos_textos, ["no_comunicacao", "no_finalizar"])
    g.add_edge("no_finalizar", END)
    return g.compile(checkpointer=checkpointer if checkpointer is not None else InMemorySaver())


def executar(cofre: Cofre, cliente: ClienteLLM, *, busca: str = "lexica", juiz_parecer: bool = False,
             ao_atualizar: Callable[[str, dict], None] | None = None, thread_id: str = "sala") -> dict:
    """Roda o grafo e devolve o estado final. `ao_atualizar(nó, atualização)` recebe o progresso de cada agente
    (RNF-14: mostrar o progresso), como o `stream_mode="updates"` do LangGraph entrega."""
    grafo = construir_grafo(cofre, cliente, busca=busca, juiz_parecer=juiz_parecer)
    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 40}

    @_observado("sala_multiagente", "chain")
    def rodar():
        _registrar({"membros": len(cofre.membros), "busca": busca}, None)
        inicial = {"sala_id": cofre.sala_id, "membros": list(cofre.membros)}
        for parte in grafo.stream(inicial, config, stream_mode="updates"):
            for no, atualizacao in parte.items():
                if ao_atualizar and atualizacao:
                    ao_atualizar(no, atualizacao)
        final = dict(grafo.get_state(config).values)
        _registrar(None, {"cartoes": [c["nome"] for c in final.get("resultado_final_cartoes", [])]})
        final["trace_url"] = _url_do_trace()
        return final

    return rodar()


# ------------------------------------------------------------------ entrada por dicionário (issue #71)

CHAVES_MEMBRO = frozenset({"nome", *pessoal.CAMPOS})   # nome + os 4 campos de texto da Tela 2
CHAVES_OPCIONAIS_MEMBRO = frozenset({"usuario"})       # id pseudônimo permanente, para ler o log pessoal


def cofre_dos_dados(dados_sala: dict, *, lugares: list[dict] | None = None, store=None) -> Cofre:
    """Cofre a partir de um dicionário, sem passar pelas rotas das salas (testes, cenários e demonstração).

    `dados_sala`: `{"codigo"?: str, "agora"?: datetime | str ISO, "membros": [{"nome", "origem", "horarios", "teto",
    "preferencias", "usuario"?}, ...]}`, com pelo menos 2 membros. Os 4 campos são interpretados por regras
    (`src/interpretador/campos.py`), como na Tela 2."""
    membros_in = dados_sala.get("membros")
    if not isinstance(membros_in, list) or len(membros_in) < 2:
        raise ValueError("dados_sala['membros'] precisa ser uma lista com pelo menos 2 membros")
    desconhecidas = set(dados_sala) - {"codigo", "agora", "membros"}
    if desconhecidas:
        raise ValueError(f"chaves desconhecidas em dados_sala: {sorted(desconhecidas)}")
    agora = dados_sala.get("agora") or datetime.now(pessoal.FUSO).replace(tzinfo=None)
    agora = datetime.fromisoformat(agora) if isinstance(agora, str) else agora
    codigo = str(dados_sala.get("codigo") or "SALA-LOCAL")
    membros = {}
    for i, m in enumerate(membros_in, 1):
        chaves = set(m)
        if not CHAVES_MEMBRO <= chaves <= CHAVES_MEMBRO | CHAVES_OPCIONAIS_MEMBRO:
            raise ValueError(f"membro {i}: esperado {sorted(CHAVES_MEMBRO)} (e opcionalmente 'usuario'); "
                             f"faltam {sorted(CHAVES_MEMBRO - chaves)}, "
                             f"sobram {sorted(chaves - CHAVES_MEMBRO - CHAVES_OPCIONAIS_MEMBRO)}")
        perfil = interpretar_campos(*(str(m[c] or "") for c in pessoal.CAMPOS), agora=agora)
        mid = f"m{i}"
        membros[mid] = Membro(id=mid, usuario=m.get("usuario") or f"sala:{codigo}:{mid}", nome=str(m["nome"]),
                              perfil=perfil)
    janelas = cruzar({mid: mb.perfil.janelas for mid, mb in membros.items()}, agora)
    base = lugares if lugares is not None else integ.carregar_lugares()
    return Cofre(sala_id=codigo, membros=membros, janelas=janelas, agora=agora, lugares={l["id"]: l for l in base},
                 store=store if store is not None else InMemoryStore())


def executar_fluxo_multiagente(dados_sala: dict, *, cliente: ClienteLLM | None = None, busca: str = "lexica",
                               juiz_parecer: bool = False, lugares: list[dict] | None = None, store=None,
                               ao_atualizar: Callable[[str, dict], None] | None = None) -> dict:
    """O fluxo completo dos 5 agentes para uma sala descrita num dicionário (issue #71); ver `cofre_dos_dados`.

    Devolve o estado final do grafo (`MultiAgentState`): só dados públicos. Os cartões estão em
    `resultado_final_cartoes`, a conversa entre os agentes em `mensagens`, os vetos e as reprovações em
    `historico_erros`, as voltas da Validação para a Pesquisa em `iteracao_pesquisa` e o link do trace no
    Langfuse em `trace_url`. Sem `cliente`, usa a OpenRouter do .env; sem chave, tudo sai por regras."""
    cofre = cofre_dos_dados(dados_sala, lugares=lugares, store=store)
    return executar(cofre, cliente or ClienteLLM(), busca=busca, juiz_parecer=juiz_parecer, ao_atualizar=ao_atualizar,
                    thread_id=cofre.sala_id)

def _url_do_trace() -> str | None:
    """Link do trace atual no Langfuse, ou None sem chaves."""
    try:
        from opentelemetry import trace
        if not trace.get_current_span().is_recording():
            return None
        from langfuse import get_client
        c = get_client()
        return c.get_trace_url(trace_id=c.get_current_trace_id())
    except Exception:
        return None
