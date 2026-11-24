"""Testes dos 4 campos da Tela 2 (src/interpretador/campos.py), sem LLM e sem rede."""
import json
import random
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from src.interpretador.campos import (interpretar_campos, interpretar_horarios, interpretar_local,
                                      interpretar_preferencias, interpretar_teto)

TER = datetime(2026, 11, 10, 14, 0)  # terça-feira, 14h


def _janelas(texto):
    return [(j.inicio, j.fim, j.disponivel) for j in interpretar_horarios(texto, TER).janelas]


# ---------- campo 1: de onde sai

@pytest.mark.parametrize("texto, ra", [
    ("Águas Claras perto da estação", "Águas Claras"),
    ("Asa Norte 408", "Plano Piloto"),
    ("Ceilândia Centro", "Ceilândia"),
    ("moro perto da estação Arniqueiras", "Arniqueira"),
    ("SQN 210", "Plano Piloto"),
    ("SQSW 305", "Sudoeste/Octogonal"),
    ("QNM 12", "Ceilândia"),
    ("102 Sul", "Plano Piloto"),
    ("Sobradinho 2", "Sobradinho II"),
    ("Riacho Fundo 2", "Riacho Fundo II"),
    ("perto da Praça do Relógio", "Taguatinga"),
])
def test_local_vira_ra(texto, ra):
    r = interpretar_local(texto)
    assert r.ra == ra and r.pergunta is None


def test_local_ambiguo_ou_desconhecido_vira_pergunta():
    assert interpretar_local("Taguatinga e Asa Sul").motivo == "local_ambiguo"
    assert interpretar_local("perto de casa").motivo == "local_desconhecido"
    assert interpretar_local("  ").motivo == "local_vazio"


# ---------- campo 2: dias e horários

def test_exemplo_do_guia():
    assert _janelas("sexta depois das 19h ou sábado à tarde") == [
        (datetime(2026, 11, 13, 19), datetime(2026, 11, 14, 0), True),
        (datetime(2026, 11, 14, 13), datetime(2026, 11, 14, 18), True),
    ]


def test_dias_juntos_herdam_o_periodo():
    j = _janelas("sexta, sábado ou domingo à noite")
    assert [x[0].date() for x in j] == [date(2026, 11, 13), date(2026, 11, 14), date(2026, 11, 15)]
    assert all(x[0].hour == 19 for x in j)


def test_faixa_e_meia_noite():
    assert _janelas("sábado das 18h às 23h") == [(datetime(2026, 11, 14, 18), datetime(2026, 11, 14, 23), True)]
    assert _janelas("sábado das 20h até meia-noite") == [(datetime(2026, 11, 14, 20), datetime(2026, 11, 15, 0), True)]


def test_negativa_e_semana_que_vem():
    j = _janelas("sexta não posso, sábado depois das 18h")
    assert (datetime(2026, 11, 13, 8), datetime(2026, 11, 14, 0), False) in j
    assert (datetime(2026, 11, 14, 18), datetime(2026, 11, 15, 0), True) in j
    assert _janelas("fim de semana que vem")[0][0].date() == date(2026, 11, 21)


def test_hora_curta_sem_manha_e_de_tarde_ou_noite():
    assert _janelas("amanhã depois das 6")[0][0] == datetime(2026, 11, 11, 18)
    assert _janelas("amanhã de manhã depois das 6")[0][0] == datetime(2026, 11, 11, 6)


def test_sem_dia_vira_pergunta_e_llm_so_entra_se_passado():
    r = interpretar_horarios("quando der", TER)
    assert r.motivo == "falta_dia" and not r.janelas

    class LLMQueNaoPodeSerChamado:
        def interpretar(self, *a):
            raise AssertionError("as regras resolveram; o LLM não devia ser chamado")

    assert interpretar_horarios("sábado à noite", TER, llm=LLMQueNaoPodeSerChamado()).origem == "regras"


def test_reserva_do_llm_para_frase_que_as_regras_nao_entendem():
    from src.interpretador.llm import Meta

    class LLMFalso:
        def interpretar(self, sistema, usuario):
            return {"intencoes": [{"tipo": "disponibilidade", "trecho": "", "valor": None, "pagador": None,
                                   "descricao": None, "convidados": [], "tipo_role": None, "lugares": [],
                                   "exigir": [], "texto_busca": None,
                                   "janelas": [{"dias": ["sab"], "proxima_semana": False, "periodo": "noite",
                                                "apos": None, "ate": None, "disponivel": True}]}]}, \
                Meta("falso", None, 0.0, 1, 1, 0.0)

    r = interpretar_horarios("no dia do aniversário do Caio", TER, llm=LLMFalso())
    assert r.origem == "llm" and r.janelas[0].inicio == datetime(2026, 11, 14, 19)


def test_janela_que_ja_passou():
    assert interpretar_horarios("hoje de manhã", TER).motivo == "janela_passada"


# ---------- campo 3: teto

@pytest.mark.parametrize("texto, valor", [("60", "60.00"), ("R$ 60,00", "60.00"), ("uns 80 conto", "80.00"),
                                          ("cinquenta", "50.00"), ("0", "0.00")])
def test_teto(texto, valor):
    assert interpretar_teto(texto) == (Decimal(valor), None)


@pytest.mark.parametrize("texto, motivo", [("", "teto_vazio"), ("entre 50 e 70", "teto_invalido"),
                                           ("50 a 70", "teto_invalido"), ("muito", "teto_invalido"),
                                           ("2000", "teto_alto")])
def test_teto_invalido_vira_pergunta(texto, motivo):
    assert interpretar_teto(texto) == (None, motivo)


# ---------- campo 4: preferências

def test_preferencias_do_exemplo_do_guia():
    p = interpretar_preferencias("Barzinho ou café calmo, sou vegetariana, vou de metrô/Uber")
    assert p.tipos == ["Bar / Boteco / Pub", "Cafeteria / Doceria"]
    assert p.vibes == ["Calmo / Bom para Conversar"]
    assert p.restricoes == ["alim_vegetariano"]
    assert p.transporte == ["publico", "app"]


def test_vegano_tambem_pede_vegetariano_e_pet():
    p = interpretar_preferencias("sou vegano e vou levar meu cachorro")
    assert set(p.restricoes) == {"alim_vegano", "alim_vegetariano"} and p.pet


# ---------- os 4 juntos

def test_resumo_para_confirmar_em_segredo():
    p = interpretar_campos("Águas Claras perto da estação", "sábado das 18h às 23h", "60",
                           "Barzinho calmo, vou de metrô", agora=TER)
    assert p.completo
    assert p.resumo.startswith("sáb 14/11, 18h–23h; saindo de Águas Claras; teto de R$ 60,00 (só você vê)")
    assert p.para_dono()["teto"] == "60.00"


def test_pendencias_por_campo():
    p = interpretar_campos("Marte", "quando der", "muito", "", agora=TER)
    assert set(p.pendencias) == {"origem", "horarios", "teto"} and not p.completo


# ---------- campo 2: como se fala (semana 5)

QUI = datetime(2026, 11, 5, 10, 0)  # referência dos gabaritos em eval/interpretador
EVAL = Path(__file__).resolve().parents[1] / "eval" / "interpretador"


def _gabarito(arquivo, categoria=None):
    linhas = [json.loads(x) for x in (EVAL / arquivo).read_text(encoding="utf-8").splitlines() if x.strip()]
    return [pytest.param(f["texto"], f["esperado"][0], id=f["id"]) for f in linhas
            if categoria is None or f["categoria"] == categoria]


@pytest.mark.parametrize("texto, esperado",
                         _gabarito("frases.jsonl", "disponibilidade") + _gabarito("horarios_fala.jsonl"))
def test_horarios_do_gabarito(texto, esperado):
    r = interpretar_horarios(texto, QUI)
    if "pergunta" in esperado:
        assert r.motivo == esperado["pergunta"] and not r.janelas
        return
    formato = "%Y-%m-%d %H:%M"
    previsto = sorted([j.inicio.strftime(formato), j.fim.strftime(formato), j.disponivel] for j in r.janelas)
    assert r.pergunta is None and previsto == sorted(esperado["janelas"])


@pytest.mark.parametrize("texto", [
    "sexta depois do trabalho", "sábado de madrugada", "sexta mais tarde", "sábado cedo", "sábado tenho prova às 14h",
    "sexta às 9", "sexta das 9 às 11", "sexta depois das oito horas", "sexta 25h", "quarta, depois da faculdade",
    "depois das 19h ou sábado o dia todo", "Tenho aula até às 10 da noite na segunda e terça. Tô livre à noite.",
])
def test_hora_que_as_regras_nao_entendem_vira_pergunta(texto):
    """A trava: antes, estas frases viravam "dia todo" sem aviso."""
    r = interpretar_horarios(texto, QUI)
    assert r.pergunta and not r.janelas


@pytest.mark.parametrize("texto, inicio, fim", [
    ("sexta às 20", "20:00", "00:00"), ("sexta 7 da noite", "19:00", "00:00"), ("sexta vinte e uma e trinta", "21:30", "00:00"),
    ("sexta das 20h às 2h", "20:00", "02:00"), ("sexta entre sete e dez da noite", "19:00", "22:00"),
    ("sexta à noite até uma da manhã", "19:00", "01:00"), ("6ª feira depois das 19h", "19:00", "00:00"),
    ("eu e uns 3 amigos podemos sexta à noite", "19:00", "00:00"), ("sexta ocupado até as 20h", "20:00", "00:00"),
    ("sexta das 18 horas e 30 às 22 horas", "18:30", "22:00"), ("depois das 19h, sexta", "19:00", "00:00"), ("sexta depois do trabalho, tipo 19h", "19:00", "00:00"),
])
def test_horas_faladas(texto, inicio, fim):
    j = interpretar_horarios(texto, QUI).janelas
    assert [(x.inicio.strftime("%H:%M"), x.fim.strftime("%H:%M")) for x in j] == [(inicio, fim)]


def test_qualquer_texto_vira_janela_ou_pergunta_sem_quebrar():
    pecas = ["sexta", "sábado", "dia 14", "depois das", "às", "até", "8", "20h", "8 e meia", "da noite", "não", "ou", ",",
             "mas", "trabalho", "depois disso", "menos", "das 2 às 6", "25:99", "entre", "@1900", "99/99", "à tarde"]
    sorteio = random.Random(5)
    for _ in range(3000):
        texto = " ".join(sorteio.choice(pecas) for _ in range(sorteio.randint(1, 9)))
        r = interpretar_horarios(texto, QUI)
        assert bool(r.janelas) != bool(r.pergunta), texto


def test_lista_para_conferir_diz_quando_a_pessoa_nao_pode():
    p = interpretar_campos("Guará", "sábado não vai dar, mas domingo depois do almoço tô livre", "60", "bar", agora=QUI)
    assert [j["texto"] for j in p.para_dono()["janelas"]] == ["sáb 07/11, 8h–24h (não pode)", "dom 08/11, 13h–24h"]
