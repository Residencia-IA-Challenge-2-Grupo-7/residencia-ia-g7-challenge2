"""Testes do Agente 2, Logística & Justiça (issue #67).

Grupos fictícios saindo da periferia do DF (Ceilândia, Samambaia, Sobradinho) e do Plano Piloto. Os lugares são
sintéticos, um no ponto de referência de cada RA, para o teste medir só a regra da Logística: trajeto pelo meio que
a pessoa usaria, Menor Miséria pelo pior trajeto e pontuação 45/35/20.

No fim, os dois cenários da #66 (data/cenarios_teste_multiagente.json) passam pelo agente com a base real de 93
lugares: perfis de interpretar_campos, janelas de cruzar, vetos de deslocamento conferidos contra o gabarito e o
parecer sem pista de quem tem o pior trajeto (RNF-02).
"""
from collections import Counter
from datetime import datetime
from decimal import Decimal
from functools import lru_cache

import pytest

from src.agentes.cenarios import CAMPOS_TELA2, carregar_cenario, carregar_cenarios
from src.agentes.contratos import Cofre, Membro
from src.agentes.estado import CandidatoAvaliado, dados_privados_no_estado
from src.agentes.logistica import PESOS_ADERENCIA, executar_agente_logistica, gerar_parecer
from src.interpretador.campos import ROTULOS_TRANSPORTE, PerfilInterpretado, Preferencias, interpretar_campos
from src.logistica.transporte_df import TEMPO_ACEITAVEL_MIN, ponto_da_ra
from src.salas.integracoes import carregar_lugares
from src.salas.janelas import JanelaComum, cruzar

AGORA = datetime(2026, 11, 17, 12)
SABADO = JanelaComum(datetime(2026, 11, 21, 15), datetime(2026, 11, 21, 18), frozenset({"m1", "m2", "m3"}), 3)
DOMINGO = JanelaComum(datetime(2026, 11, 22, 15), datetime(2026, 11, 22, 18), frozenset({"m1", "m2", "m3"}), 3)
ABERTO = "Todos os dias: 10h às 23h"


def _perfil(ra, transporte=("publico",), **prefs):
    return PerfilInterpretado(ra=ra, regiao=None, janelas=[], teto=Decimal("80"),
                              preferencias=Preferencias(transporte=list(transporte), **prefs))


def _lugar(id_, ra, horario=ABERTO, **extra):
    lat, lng = ponto_da_ra(ra)
    return {"id": id_, "nome": f"Lugar {ra}", "tipo_de_role": "Bar / Boteco / Pub", "vibes": [],
            "regiao_administrativa": ra, "lat": lat, "lng": lng, "horario_funcionamento": horario, **extra}


def _rodar(membros, lugares, janelas=(SABADO,), candidatos=None, analises=None):
    base = {l["id"]: l for l in lugares}
    cands = candidatos if candidatos is not None else [{"id": i, "motivo": "", "trecho": ""} for i in base]
    return executar_agente_logistica(cands, membros, lugares=base, janelas=list(janelas), agora=AGORA,
                                     analises=analises)


PERIFERIA = {"m1": _perfil("Ceilândia"), "m2": _perfil("Samambaia"), "m3": _perfil("Plano Piloto")}
TAGUATINGA, PLANO = _lugar("tagua", "Taguatinga"), _lugar("plano", "Plano Piloto")


# ------------------------------------------------------------------ Menor Miséria com a periferia

def test_lugar_no_meio_do_caminho_vence_o_centro_para_quem_mora_na_periferia():
    """Ceilândia + Samambaia + Plano Piloto: Taguatinga tem pior trajeto menor que o Plano, então vem primeiro."""
    saida = _rodar(PERIFERIA, [PLANO, TAGUATINGA])
    assert [c["id"] for c in saida] == ["tagua", "plano"]
    tagua, plano = saida
    assert tagua["pior_trajeto_min"] < plano["pior_trajeto_min"]
    assert tagua["nota_justica"] > plano["nota_justica"]


def test_pontas_opostas_do_df_sao_avaliadas_sem_veto_e_com_nota_baixa():
    """Ceilândia + Sobradinho de ônibus/metrô: o pior trajeto passa de 75 min, mas a Logística só mede;
    quem veta é a Validação (#68). A nota cai e nunca zera."""
    membros = {"m1": _perfil("Ceilândia"), "m2": _perfil("Sobradinho")}
    janela = JanelaComum(SABADO.inicio, SABADO.fim, frozenset({"m1", "m2"}), 2)
    (plano,) = _rodar(membros, [PLANO], janelas=[janela])
    perto = {"m1": _perfil("Plano Piloto"), "m2": _perfil("Plano Piloto")}
    (referencia,) = _rodar(perto, [PLANO], janelas=[janela])
    assert plano["pior_trajeto_min"] > 75
    assert 0 < plano["nota_justica"] < 0.6 * referencia["nota_justica"]


def test_quem_usa_metro_ou_uber_vai_de_uber_so_quando_o_metro_nao_chega_a_tempo():
    membros = {"m1": _perfil("Ceilândia", ("publico", "app")), "m2": _perfil("Plano Piloto")}
    janela = JanelaComum(SABADO.inicio, SABADO.fim, frozenset({"m1", "m2"}), 2)
    analises = {}
    _rodar(membros, [PLANO, TAGUATINGA], janelas=[janela], analises=analises)
    assert analises["plano"]["m1"]["modo"] == "app"        # ~120 min de ônibus/metrô contra ~68 de app
    assert analises["tagua"]["m1"]["modo"] == "publico"    # ~40 min: cabe e é mais barato


def test_agregados_batem_com_o_detalhe_de_cada_pessoa():
    analises = {}
    (tagua,) = _rodar(PERIFERIA, [TAGUATINGA], analises=analises)
    tempos = [d["minutos"] for d in analises["tagua"].values()]
    assert tagua["pior_trajeto_min"] == round(max(tempos))
    assert tagua["media_trajeto_min"] == round(sum(tempos) / len(tempos))
    assert tagua["diferenca_min"] == round(max(tempos) - min(tempos))
    assert tagua["estimativa_provisoria"] is False


def test_domingo_tem_onibus_e_metro_de_graca():
    analises = {}
    _rodar(PERIFERIA, [TAGUATINGA], janelas=[DOMINGO], analises=analises)
    assert all(d["custo_ida_volta"] == Decimal("0.00") for d in analises["tagua"].values())


# ------------------------------------------------------------------ pontuação 45/35/20 e horário

def test_pontuacao_segue_os_pesos_45_35_20():
    """Sem tipo, vibe nem restrição pedidos, a aderência é neutra: tipo 0,5, vibe 0,5 e restrição 1,0."""
    (tagua,) = _rodar(PERIFERIA, [TAGUATINGA])
    aderencia = PESOS_ADERENCIA["tipo"] * 0.5 + PESOS_ADERENCIA["vibe"] * 0.5 + PESOS_ADERENCIA["restricao"] * 1.0
    esperado = 0.45 * aderencia + 0.35 * tagua["nota_justica"] / 100 + 0.20 * 1.0
    assert tagua["horario_situacao"] == "aberto"
    assert tagua["pontuacao"] == round(esperado, 3)


def test_pesos_da_aderencia_somam_1():
    assert abs(sum(PESOS_ADERENCIA.values()) - 1) < 1e-9


def test_lugar_que_o_grupo_pediu_sobe_no_ranking():
    membros = {m: _perfil(p.ra, tipos=["Cafeteria / Doceria"]) for m, p in PERIFERIA.items()}
    cafe = _lugar("cafe", "Plano Piloto", tipo_de_role="Cafeteria / Doceria")
    saida = _rodar(membros, [PLANO, cafe])
    assert saida[0]["id"] == "cafe"


def test_fechado_em_todas_as_janelas_fica_com_certeza_zero_e_sem_veto():
    fechado = _lugar("fechado", "Taguatinga", horario="Segunda a sexta: 18h às 23h")
    saida = _rodar(PERIFERIA, [TAGUATINGA, fechado], janelas=[SABADO, DOMINGO])
    por_id = {c["id"]: c for c in saida}
    assert por_id["fechado"]["horario_situacao"] == "fechado"
    assert por_id["fechado"]["janela"] == SABADO.texto()
    assert por_id["fechado"]["pontuacao"] == round(por_id["tagua"]["pontuacao"] - 0.20, 3)
    assert [c["id"] for c in saida] == ["tagua", "fechado"]


def test_usa_a_primeira_janela_em_que_o_lugar_abre():
    so_domingo = _lugar("dom", "Taguatinga", horario="Fechado aos sábados; domingo: 10h às 18h")
    (dom,) = _rodar(PERIFERIA, [so_domingo], janelas=[SABADO, DOMINGO])
    assert dom["janela"] == DOMINGO.texto()
    assert dom["horario_situacao"] == "aberto"


# ------------------------------------------------------------------ contrato, privacidade e determinismo

def test_saida_e_candidato_avaliado_sem_dado_privado():
    saida = _rodar(PERIFERIA, [PLANO, TAGUATINGA])
    for c in saida:
        CandidatoAvaliado.model_validate(c)
        assert set(c) == set(CandidatoAvaliado.model_fields)
    assert dados_privados_no_estado({"candidatos_avaliados": saida}) == []
    texto = str(saida)
    assert "Ceilândia" not in texto and "Samambaia" not in texto   # nenhuma RA de origem na saída
    assert "80" not in texto                                         # nem o teto


def test_mesma_entrada_mesma_saida_em_qualquer_ordem():
    a = _rodar(PERIFERIA, [PLANO, TAGUATINGA])
    b = _rodar(PERIFERIA, [TAGUATINGA, PLANO])
    assert a == b == _rodar(PERIFERIA, [PLANO, TAGUATINGA])


def test_id_fora_da_base_e_sem_janela():
    cands = [{"id": "inventado", "motivo": "", "trecho": ""}, {"id": "tagua", "motivo": "", "trecho": ""}]
    assert [c["id"] for c in _rodar(PERIFERIA, [TAGUATINGA], candidatos=cands)] == ["tagua"]
    assert _rodar(PERIFERIA, [TAGUATINGA], janelas=[]) == []


def test_sem_analises_nada_e_gravado_e_lugar_sem_coordenada_e_provisorio():
    sem_gps = {**TAGUATINGA, "id": "sem_gps", "lat": None, "lng": None}
    (c,) = _rodar(PERIFERIA, [sem_gps])
    assert c["pior_trajeto_min"] is None and c["estimativa_provisoria"] is True
    assert c["nota_justica"] == 30.0


# ------------------------------------------------------------------ parecer textual

def test_parecer_traz_score_pior_trajeto_com_o_meio_e_media():
    analises = {}
    saida = _rodar(PERIFERIA, [PLANO, TAGUATINGA], analises=analises)
    tagua = saida[0]
    texto = gerar_parecer(saida, analises)
    assert texto.startswith("Ranking Logístico: Lugar Taguatinga (score ")
    assert (f"pior trajeto {tagua['pior_trajeto_min']} min de ônibus/metrô; "
            f"média {tagua['media_trajeto_min']} min") in texto


def test_parecer_mostra_tempos_so_do_primeiro_e_do_ultimo():
    meio = _lugar("meio", "Águas Claras")
    saida = _rodar(PERIFERIA, [PLANO, TAGUATINGA, meio])
    texto = gerar_parecer(saida)
    assert texto.count("pior trajeto") == 2
    assert f"{saida[1]['nome']} (score {round(saida[1]['pontuacao'] * 100)})" in texto


def test_parecer_sem_analises_nao_cita_o_meio():
    saida = _rodar(PERIFERIA, [TAGUATINGA])
    texto = gerar_parecer(saida)
    assert "ônibus/metrô" not in texto and "min;" in texto


def test_parecer_avisa_trajeto_acima_de_75_min_sem_dizer_de_quem():
    membros = {"m1": _perfil("Ceilândia"), "m2": _perfil("Sobradinho")}
    janela = JanelaComum(SABADO.inicio, SABADO.fim, frozenset({"m1", "m2"}), 2)
    analises = {}
    saida = _rodar(membros, [PLANO], janelas=[janela], analises=analises)
    texto = gerar_parecer(saida, analises)
    assert texto.endswith("1 lugar com trajeto acima de 75 min para alguém do grupo.")
    for segredo in ("Ceilândia", "Sobradinho", "m1", "m2", "80", "R$"):
        assert segredo not in texto


def test_parecer_e_deterministico_e_trata_lista_vazia_e_sem_coordenada():
    saida = _rodar(PERIFERIA, [PLANO, TAGUATINGA])
    assert gerar_parecer(saida) == gerar_parecer(list(saida))
    assert gerar_parecer([]) == "Ranking Logístico: nenhum candidato para avaliar."
    sem_gps = {**TAGUATINGA, "id": "sem_gps", "lat": None, "lng": None}
    texto = gerar_parecer(_rodar(PERIFERIA, [sem_gps]))
    assert "trajeto não calculado; estimativa provisória" in texto


def _parecer_do_lugar_em_ceilandia(membros):
    lugar = _lugar("ceil", "Ceilândia")
    janela = JanelaComum(SABADO.inicio, SABADO.fim, frozenset(membros), len(membros))
    analises = {}
    saida = _rodar(membros, [lugar], janelas=[janela], analises=analises)
    pior = max(analises["ceil"].values(), key=lambda d: d["minutos"])
    return gerar_parecer(saida, analises), saida[0], pior


def test_parecer_nao_cita_o_meio_quando_so_uma_pessoa_o_usa():
    """Só m3 vai de carro e tem o pior trajeto: "de carro" apontaria quem mora longe (RNF-02)."""
    membros = {"m1": _perfil("Ceilândia"), "m2": _perfil("Samambaia"), "m3": _perfil("Plano Piloto", ("carro",))}
    texto, cand, pior = _parecer_do_lugar_em_ceilandia(membros)
    assert pior["modo"] == "carro"                      # o pior trajeto é mesmo o de quem vai de carro
    assert "de carro" not in texto
    assert f"pior trajeto {cand['pior_trajeto_min']} min; média {cand['media_trajeto_min']} min" in texto


def test_parecer_cita_o_meio_quando_duas_pessoas_o_usam():
    """Espelho do teste anterior: com dois de carro, o meio não aponta ninguém e aparece."""
    membros = {"m1": _perfil("Ceilândia"), "m2": _perfil("Samambaia"),
               "m3": _perfil("Plano Piloto", ("carro",)), "m4": _perfil("Plano Piloto", ("carro",))}
    texto, cand, pior = _parecer_do_lugar_em_ceilandia(membros)
    assert pior["modo"] == "carro"
    assert f"pior trajeto {cand['pior_trajeto_min']} min de carro;" in texto


# ------------------------------------------------------------------ cenários da #66 com a base real

CENARIOS = carregar_cenarios()
LUGARES_DO_GABARITO = [(c["id"], lugar) for c in CENARIOS
                       for lugar in c["resultados_esperados"]["locais_plausiveis"]
                       + c["resultados_esperados"]["nunca_sugerir"]]


@lru_cache(maxsize=None)
def _rodar_cenario(cenario_id):
    """Os 4 campos de cada amigo -> interpretar_campos -> cruzar -> Agente 2 sobre os 93 lugares (uma vez só)."""
    cenario = carregar_cenario(cenario_id)
    agora = datetime.fromisoformat(cenario["agora_referencia"])
    perfis = {a["marcador"]: interpretar_campos(*(a["campos_tela2"][k] for k in CAMPOS_TELA2), agora=agora)
              for a in cenario["amigos"]}
    janelas = cruzar({m: p.janelas for m, p in perfis.items()}, agora)
    lugares = {l["id"]: l for l in carregar_lugares()}
    analises = {}
    saida = executar_agente_logistica([{"id": i, "motivo": "", "trecho": ""} for i in lugares], perfis,
                                      lugares=lugares, janelas=janelas, agora=agora, analises=analises)
    return cenario, perfis, janelas, lugares, saida, analises


def _modos(desl_por):
    return Counter(d["modo"] for d in desl_por.values() if d)


def _pior(desl_por):
    conhecidos = [d for d in desl_por.values() if d]
    return max(conhecidos, key=lambda d: d["minutos"]) if conhecidos else None


@pytest.mark.parametrize("cenario_id", [c["id"] for c in CENARIOS])
def test_cenario_avalia_a_base_inteira_no_contrato_e_em_ordem(cenario_id):
    _, _, _, lugares, saida, analises = _rodar_cenario(cenario_id)
    assert len(saida) == len(lugares) == len(analises)
    for c in saida:
        CandidatoAvaliado.model_validate(c)
    pontos = [c["pontuacao"] for c in saida]
    assert pontos == sorted(pontos, reverse=True)


@pytest.mark.parametrize("cenario_id,lugar", LUGARES_DO_GABARITO,
                         ids=[f"{cid}:{lugar['nome']}" for cid, lugar in LUGARES_DO_GABARITO])
def test_vetos_de_deslocamento_do_gabarito_batem_com_os_trajetos(cenario_id, lugar):
    """O gabarito veta por deslocamento quem passa de 75 min pelo meio mais rápido. O agente escolhe o mais barato
    que chega em até 75 min, senão o mais rápido: o trajeto dele passa de 75 min exatamente para os vetados."""
    *_, saida, analises = _rodar_cenario(cenario_id)
    desl_por = analises[lugar["id"]]
    esperados = set(lugar["vetos_por_membro"].get("deslocamento", [])) & set(desl_por)
    acima = {m for m, d in desl_por.items() if d and d["minutos"] > TEMPO_ACEITAVEL_MIN}
    assert acima == esperados
    cand = next(c for c in saida if c["id"] == lugar["id"])
    assert (cand["pior_trajeto_min"] > TEMPO_ACEITAVEL_MIN) == bool(esperados)


@pytest.mark.parametrize("cenario_id", [c["id"] for c in CENARIOS])
def test_parecer_nunca_cita_o_meio_de_uma_pessoa_so(cenario_id):
    """Em todos os 93 lugares: se o parecer diz o meio do pior trajeto, pelo menos 2 presentes usam esse meio."""
    *_, saida, analises = _rodar_cenario(cenario_id)
    for c in saida:
        texto = gerar_parecer([c], analises)
        modos = _modos(analises[c["id"]])
        for modo, rotulo in ROTULOS_TRANSPORTE.items():
            if f" min de {rotulo};" in texto:
                assert modos[modo] >= 2, f"{c['nome']}: '{rotulo}' aponta uma pessoa só"


def test_cenario_de_controle_tem_os_dois_casos_do_meio_no_parecer():
    """Garante que o teste anterior não passa por falta de caso: no controle, o m3 é o único de carro ou app e tem
    o pior trajeto em algum lugar (o meio some), e em outro o pior é de ônibus/metrô, que 3 usam (o meio aparece)."""
    *_, saida, analises = _rodar_cenario("cenario_controle_viavel")
    some, aparece = [], []
    for c in saida:
        pior = _pior(analises[c["id"]])
        if pior is None:
            continue
        unico = _modos(analises[c["id"]])[pior["modo"]] == 1
        (some if unico else aparece).append((c, ROTULOS_TRANSPORTE[pior["modo"]]))
    assert some and aparece
    for c, rotulo in some:
        assert f" min de {rotulo};" not in gerar_parecer([c], analises)
    for c, rotulo in aparece:
        assert f" min de {rotulo};" in gerar_parecer([c], analises)


@pytest.mark.parametrize("cenario_id", [c["id"] for c in CENARIOS])
def test_saida_e_parecer_dos_cenarios_passam_na_varredura_do_cofre(cenario_id):
    """Com o cofre de verdade (nomes fictícios dos amigos), nem a saída nem o parecer têm chave privada, nome ou
    id de usuário de alguém (a varredura do #64)."""
    cenario, perfis, janelas, lugares, saida, analises = _rodar_cenario(cenario_id)
    agora = datetime.fromisoformat(cenario["agora_referencia"])
    membros = {a["marcador"]: Membro(id=a["marcador"], usuario=f"usuario-{a['marcador']}", nome=a["nome_ficticio"],
                                     perfil=perfis[a["marcador"]]) for a in cenario["amigos"]}
    cofre = Cofre(membros=membros, janelas=janelas, agora=agora, lugares=lugares, store=None)
    estado = {"candidatos_avaliados": saida,
              "mensagens": [{"de": "logistica", "para": "validacao", "texto": gerar_parecer(saida, analises),
                             "em": agora.isoformat()}]}
    assert dados_privados_no_estado(estado, cofre) == []
