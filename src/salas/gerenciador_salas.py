"""Regras das salas (guia oficial, Telas 1 a 3): criar, entrar com os 4 campos, confirmar em segredo, cruzar
horários, gerar os cartões, votar e fechar com "Rolê orquestrado com sucesso!".

Quem pode o quê:

| Ação                         | Precisa de                        | Regra                                            |
|------------------------------|-----------------------------------|--------------------------------------------------|
| Criar sala                   | declarar 18+                      | RF-01, RF-03                                     |
| Entrar com os 4 campos       | código da sala, declarar 18+      | até 20 pessoas; menor de idade não é guardado    |
| Corrigir, confirmar, ver o próprio perfil | token do participante | o teto só volta para o dono                    |
| Gerar sugestões, fechar votação | token do organizador           | pelo menos 2 perfis confirmados                  |
| Votar                        | token do participante confirmado  | votação múltipla; pode trocar o voto até fechar  |

Tokens: `secrets.token_urlsafe`, devolvidos uma vez; só o SHA-256 fica guardado.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
from collections import Counter
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

from src.interpretador.campos import interpretar_campos
from src.salas import integracoes as integ
from src.salas import sugestoes as motor
from src.salas.janelas import cruzar
from src.salas.modelos import (COLETANDO, LIMITE_PARTICIPANTES, MINIMO_PARTICIPANTES, ORQUESTRADO, VOTACAO,
                               Participante, Resultado, Sala)
from src.state import Repositorio, obter_repositorio

FUSO = timezone(timedelta(hours=-3))  # America/Sao_Paulo, sem horário de verão desde 2019
ALFABETO_CODIGO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # sem 0/O e 1/I, para ditar o código sem erro
PREFIXO_CODIGO = "ROLE-"  # formato da issue #43 e do guia: ROLE-7KQ2 (32^4 ≈ 1 milhão de códigos)
MENSAGEM_SUCESSO = "🎉 Rolê orquestrado com sucesso!"


class ErroSala(Exception):
    def __init__(self, status: int, mensagem: str, extra: dict | None = None):
        super().__init__(mensagem)
        self.status = status
        self.mensagem = mensagem
        self.extra = extra or {}


def agora_local() -> datetime:
    return datetime.now(FUSO).replace(tzinfo=None)


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _confere(token: str | None, guardado: str) -> bool:
    return bool(token) and hmac.compare_digest(_hash(token), guardado)


def _nome(nome: str, campo: str) -> str:
    nome = " ".join((nome or "").split())
    if not 1 <= len(nome) <= 40:
        raise ErroSala(422, f"{campo} precisa ter de 1 a 40 caracteres.")
    return nome


class GerenciadorSalas:
    def __init__(self, repo: Repositorio | None = None, relogio=agora_local, llm_horarios=None,
                 lugares: list[dict] | None = None):
        self.repo = repo or obter_repositorio()
        self.relogio = relogio
        self.llm_horarios = llm_horarios  # cliente do ADR 0007, só como reserva do campo de horários
        self._lugares = lugares

    @property
    def lugares(self):
        return self._lugares if self._lugares is not None else integ.carregar_lugares()

    # ------------------------------------------------------------ leitura e escrita

    def _sala(self, codigo: str) -> Sala:
        sala = self.repo.obter((codigo or "").strip().upper())
        if sala is None:
            raise ErroSala(404, "Sala não encontrada. Confira o código do convite.")
        return sala

    def _participante(self, sala: Sala, pid: str, token: str | None) -> Participante:
        p = sala.participantes.get(pid)
        if p is None or not _confere(token, p.token_hash):
            raise ErroSala(403, "Participante ou token inválido.")
        return p

    def _organizador(self, sala: Sala, token: str | None) -> None:
        if not _confere(token, sala.token_organizador_hash):
            raise ErroSala(403, "Só quem criou a sala pode fazer isso.")

    def _novo_codigo(self) -> str:
        for _ in range(50):
            codigo = PREFIXO_CODIGO + "".join(secrets.choice(ALFABETO_CODIGO) for _ in range(4))
            if not self.repo.existe(codigo):
                return codigo
        raise ErroSala(503, "Não foi possível gerar um código de sala agora. Tente de novo.")

    # ------------------------------------------------------------ Tela 1: criar sala

    def criar_sala(self, nome_role: str, organizador: str, maior_de_idade: bool) -> tuple[Sala, str]:
        if not maior_de_idade:
            raise ErroSala(403, "O Orquestrador de Rolês é só para maiores de 18 anos. Nenhum dado foi guardado.")
        nome_role = " ".join((nome_role or "").split())
        if not 1 <= len(nome_role) <= 80:
            raise ErroSala(422, "O nome do rolê precisa ter de 1 a 80 caracteres.")
        token = secrets.token_urlsafe(24)
        sala = Sala(codigo=self._novo_codigo(), nome_role=nome_role, organizador_nome=_nome(organizador, "O nome"),
                    token_organizador_hash=_hash(token), criado_em=self.relogio())
        self.repo.salvar(sala)
        return sala, token

    # ------------------------------------------------------------ Tela 2: os 4 campos secretos

    def entrar(self, codigo: str, nome: str, maior_de_idade: bool, origem: str, horarios: str, teto: str,
               preferencias: str) -> tuple[Participante, str]:
        sala = self._sala(codigo)
        if not maior_de_idade:
            raise ErroSala(403, "O Orquestrador de Rolês é só para maiores de 18 anos. Nenhum dado foi guardado.")
        if sala.status == ORQUESTRADO:
            raise ErroSala(409, "Este rolê já foi orquestrado. Peça ao organizador para criar outra sala.")
        if len(sala.participantes) >= LIMITE_PARTICIPANTES:
            raise ErroSala(409, f"A sala já tem {LIMITE_PARTICIPANTES} pessoas, o máximo permitido.")
        nome = _nome(nome, "O nome")
        if any(p.nome.casefold() == nome.casefold() for p in sala.participantes.values()):
            raise ErroSala(409, "Já tem alguém com esse nome na sala. Use um apelido ou sobrenome.")
        perfil = interpretar_campos(origem, horarios, teto, preferencias, agora=self.relogio(), llm=self.llm_horarios)
        token = secrets.token_urlsafe(24)
        pid = secrets.token_hex(6)
        p = Participante(id=pid, nome=nome, token_hash=_hash(token), perfil=perfil, criado_em=self.relogio())
        sala.participantes[pid] = p
        self.repo.salvar(sala)
        return p, token

    def corrigir(self, codigo: str, pid: str, token: str | None, origem: str, horarios: str, teto: str,
                 preferencias: str) -> Participante:
        sala = self._sala(codigo)
        p = self._participante(sala, pid, token)
        if sala.status == ORQUESTRADO:
            raise ErroSala(409, "Este rolê já foi orquestrado.")
        p.perfil = interpretar_campos(origem, horarios, teto, preferencias, agora=self.relogio(), llm=self.llm_horarios)
        p.confirmado = False
        sala.votos.pop(pid, None)
        self.repo.salvar(sala)
        return p

    def confirmar(self, codigo: str, pid: str, token: str | None) -> Participante:
        sala = self._sala(codigo)
        p = self._participante(sala, pid, token)
        if p.perfil is None or p.perfil.pendencias:
            raise ErroSala(422, "Ainda falta responder algumas perguntas antes de confirmar.",
                           {"pendencias": p.perfil.pendencias if p.perfil else {}})
        p.confirmado = True
        self.repo.salvar(sala)
        return p

    def visao_do_participante(self, codigo: str, pid: str, token: str | None) -> dict:
        """O que só o dono vê: o perfil inteiro (com o teto) e o próprio custo e tempo em cada cartão (RF-15)."""
        sala = self._sala(codigo)
        p = self._participante(sala, pid, token)
        return {
            "participante_id": p.id, "nome": p.nome, "confirmado": p.confirmado,
            "perfil": p.perfil.para_dono() if p.perfil else None,
            "meus_votos": sala.votos.get(pid, []),
            "meu_custo_e_tempo": {s.id: s.por_participante.get(pid) for s in sala.sugestoes},
        }

    # ------------------------------------------------------------ Tela 3: painel, sugestões e votação

    def painel(self, codigo: str) -> dict:
        return self._painel(self._sala(codigo))

    def _painel(self, sala: Sala) -> dict:
        """O que todo o grupo vê. Nunca inclui teto, origem, horários individuais nem quem votou em quê."""
        confirmados = sala.confirmados()
        placar = Counter(o for ops in sala.votos.values() for o in ops)
        r = sala.resultado
        return {
            "codigo": sala.codigo, "nome_role": sala.nome_role, "organizador": sala.organizador_nome,
            "status": sala.status, "link_convite": f"/sala/{sala.codigo}",
            "limite_participantes": LIMITE_PARTICIPANTES,
            "participantes": [{"id": p.id, "nome": p.nome, "preencheu": p.confirmado}
                              for p in sala.participantes.values()],
            "preencheram": f"{len(confirmados)} de {len(sala.participantes)}",
            "pode_gerar_sugestoes": len(confirmados) >= MINIMO_PARTICIPANTES and sala.status != ORQUESTRADO,
            "janela_escolhida": ({"horario": sala.janelas_comuns[0].texto(), "quantos_podem": sala.janelas_comuns[0].contagem}
                                 if sala.janelas_comuns else None),
            "sugestoes": [s.publico() for s in sala.sugestoes],
            "placar": {s.id: placar.get(s.id, 0) for s in sala.sugestoes},
            "votaram": f"{len(sala.votos)} de {len(confirmados)}",
            "resultado": ({"sugestao_id": r.sugestao_id, "votos": r.votos,
                           "desempate_por_justica": r.desempate_por_justica, "mensagem": r.mensagem,
                           "resumo_whatsapp": r.resumo_whatsapp,
                           "link_agenda": self._link_agenda(sala, r.sugestao_id)} if r else None),
            "avisos": sala.avisos,
        }

    def gerar_sugestoes(self, codigo: str, token_organizador: str | None) -> dict:
        sala = self._sala(codigo)
        self._organizador(sala, token_organizador)
        if sala.status == ORQUESTRADO:
            raise ErroSala(409, "A votação já foi fechada.")
        confirmados = sala.confirmados()
        if len(confirmados) < MINIMO_PARTICIPANTES:
            raise ErroSala(409, "É preciso pelo menos 2 pessoas com os dados confirmados. Convide mais alguém!")
        agora = self.relogio()
        perfis = {p.id: p.perfil for p in confirmados}
        sala.janelas_comuns = cruzar({pid: pf.janelas for pid, pf in perfis.items()}, agora)
        res = motor.gerar(perfis, sala.janelas_comuns, self.lugares, agora)
        sala.sugestoes = res.sugestoes
        sala.avisos = res.avisos
        sala.votos = {}
        sala.resultado = None
        sala.status = VOTACAO if sala.sugestoes else COLETANDO
        self.repo.salvar(sala)
        return self._painel(sala)

    def votar(self, codigo: str, pid: str, token: str | None, opcoes: list[str]) -> dict:
        sala = self._sala(codigo)
        p = self._participante(sala, pid, token)
        if sala.status != VOTACAO:
            raise ErroSala(409, "A votação não está aberta.")
        if not p.confirmado:
            raise ErroSala(409, "Confirme seus dados antes de votar.")
        validas = {s.id for s in sala.sugestoes}
        escolha = list(dict.fromkeys(o.strip().upper() for o in opcoes))
        if not escolha or any(o not in validas for o in escolha):
            raise ErroSala(422, f"Escolha uma ou mais opções entre {', '.join(sorted(validas))}.")
        sala.votos[pid] = escolha
        if all(c.id in sala.votos for c in sala.confirmados()):
            self._fechar(sala)
        self.repo.salvar(sala)
        return self._painel(sala)

    def fechar_votacao(self, codigo: str, token_organizador: str | None) -> dict:
        sala = self._sala(codigo)
        self._organizador(sala, token_organizador)
        if sala.status != VOTACAO:
            raise ErroSala(409, "A votação não está aberta.")
        self._fechar(sala)
        self.repo.salvar(sala)
        return self._painel(sala)

    def _fechar(self, sala: Sala) -> None:
        """RF-25: vence o mais votado; empate (ou ninguém votou) vai para a melhor nota de justiça e, depois,
        para a melhor posição no ranking."""
        placar = Counter(o for ops in sala.votos.values() for o in ops)
        maior = max((placar.get(s.id, 0) for s in sala.sugestoes), default=0)
        empatados = [s for s in sala.sugestoes if placar.get(s.id, 0) == maior]
        vencedor = sorted(empatados, key=lambda s: (-s.nota_justica, s.posicao))[0]
        s = vencedor
        resumo = "\n".join([
            MENSAGEM_SUCESSO, f"*{sala.nome_role}*", f"📍 {s.nome} ({s.regiao_texto})", f"🏠 {s.endereco}",
            f"🗓️ {s.horario_texto}",
            f"💸 {motor._reais(s.gasto_min)} a {motor._reais(s.gasto_max)} por pessoa, transporte incluído",
            *([f"🎬 {s.tiktok_url}"] if s.tiktok_url else []),
        ])
        sala.resultado = Resultado(sugestao_id=s.id, votos=maior, desempate_por_justica=len(empatados) > 1,
                                   mensagem=MENSAGEM_SUCESSO, resumo_whatsapp=resumo, fechado_em=self.relogio())
        sala.status = ORQUESTRADO

    @staticmethod
    def _link_agenda(sala: Sala, sugestao_id: str) -> str | None:
        """Link do Google Agenda com o lugar e o horário (só dados públicos do cartão)."""
        s = next((x for x in sala.sugestoes if x.id == sugestao_id), None)
        if s is None:
            return None
        datas = f"{s.inicio:%Y%m%dT%H%M%S}/{s.fim:%Y%m%dT%H%M%S}"
        q = urlencode({"action": "TEMPLATE", "text": f"{sala.nome_role} – {s.nome}", "dates": datas,
                       "ctz": "America/Sao_Paulo", "location": s.endereco,
                       "details": f"Orquestrado pelo Orquestrador de Rolês. {s.tiktok_url or ''}".strip()})
        return f"https://calendar.google.com/calendar/render?{q}"
