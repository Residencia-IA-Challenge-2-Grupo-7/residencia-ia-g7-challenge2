"""Rotas da API das salas (guia oficial, Telas 1 a 3), montadas em `src/main.py` sob `/api/salas`.

Autenticação leve: criar a sala devolve o `token_organizador`; entrar devolve o `token` do participante.
Os dois vão no cabeçalho `X-Token` das rotas que pedem. Nenhum token vai na URL (ficaria nos logs).

| Método e rota                                         | Quem          | Tela |
|-------------------------------------------------------|---------------|------|
| `POST /api/salas`                                     | qualquer um   | 1    |
| `GET  /api/salas/{codigo}`                            | qualquer um   | 3    |
| `POST /api/salas/{codigo}/participantes`              | quem tem o link | 2  |
| `PUT  /api/salas/{codigo}/participantes/{id}`         | o participante | 2   |
| `POST /api/salas/{codigo}/participantes/{id}/confirmar` | o participante | 2 |
| `GET  /api/salas/{codigo}/participantes/{id}`         | o participante | 2 e 3 |
| `POST /api/salas/{codigo}/gerar-sugestoes`            | o organizador | 3    |
| `POST /api/salas/{codigo}/votar`                      | o participante | 3   |
| `POST /api/salas/{codigo}/fechar-votacao`             | o organizador | 3    |
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from src.salas.gerenciador_salas import ErroSala, GerenciadorSalas

router = APIRouter(prefix="/api/salas", tags=["Salas"])
_gerenciador: GerenciadorSalas | None = None


def obter_gerenciador() -> GerenciadorSalas:
    global _gerenciador
    if _gerenciador is None:
        _gerenciador = GerenciadorSalas()
    return _gerenciador


class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CriarSala(_Base):
    nome_role: str = Field(min_length=1, max_length=80, examples=["Aniversário da Galera"])
    organizador: str = Field(min_length=1, max_length=40, examples=["Rafaela"])
    maior_de_idade: bool = Field(description="Declaração de que tem 18 anos ou mais (RF-01)")


class Campos(_Base):
    origem: str = Field("", max_length=200, description="De onde você vai sair no DF?",
                        examples=["Águas Claras perto da estação"])
    horarios: str = Field("", max_length=300, description="Quais dias e horários você pode?",
                          examples=["Sexta depois das 19h ou sábado à tarde"])
    teto: str = Field("", max_length=40, description="Qual seu limite máximo de gasto em R$? (secreto)",
                      examples=["60"])
    preferencias: str = Field("", max_length=300, description="O que você anima fazer e como vai?",
                              examples=["Barzinho ou café calmo, sou vegetariana, vou de metrô/Uber"])


class Entrar(Campos):
    nome: str = Field(min_length=1, max_length=40, examples=["Bia"])
    maior_de_idade: bool


class Votar(_Base):
    participante_id: str
    opcoes: list[str] = Field(min_length=1, max_length=4, examples=[["A", "C"]])


def _erro(e: ErroSala) -> HTTPException:
    return HTTPException(status_code=e.status, detail={"mensagem": e.mensagem, **e.extra})


@router.post("", status_code=201)
def criar_sala(req: CriarSala, g: GerenciadorSalas = Depends(obter_gerenciador)):
    """Tela 1: cria a sala e devolve o link de convite e o token do organizador (guarde-o)."""
    try:
        sala, token = g.criar_sala(req.nome_role, req.organizador, req.maior_de_idade)
    except ErroSala as e:
        raise _erro(e)
    return {"codigo": sala.codigo, "link_convite": f"/sala/{sala.codigo}", "token_organizador": token,
            "sala": g.painel(sala.codigo)}


@router.get("/{codigo}")
def painel(codigo: str, g: GerenciadorSalas = Depends(obter_gerenciador)):
    """Tela 3: o que todo o grupo vê (sem teto, origem nem horários de ninguém)."""
    try:
        return g.painel(codigo)
    except ErroSala as e:
        raise _erro(e)


@router.post("/{codigo}/participantes", status_code=201)
def entrar(codigo: str, req: Entrar, g: GerenciadorSalas = Depends(obter_gerenciador)):
    """Tela 2: recebe os 4 campos, interpreta e devolve o resumo para a pessoa confirmar em segredo."""
    try:
        p, token = g.entrar(codigo, req.nome, req.maior_de_idade, req.origem, req.horarios, req.teto,
                            req.preferencias)
    except ErroSala as e:
        raise _erro(e)
    return {"participante_id": p.id, "token": token, "confirmado": False, "perfil": p.perfil.para_dono()}


@router.put("/{codigo}/participantes/{pid}")
def corrigir(codigo: str, pid: str, req: Campos, x_token: str | None = Header(None),
             g: GerenciadorSalas = Depends(obter_gerenciador)):
    """Tela 2: reenvia os 4 campos (quando o resumo saiu errado ou havia pergunta pendente)."""
    try:
        p = g.corrigir(codigo, pid, x_token, req.origem, req.horarios, req.teto, req.preferencias)
    except ErroSala as e:
        raise _erro(e)
    return {"participante_id": p.id, "confirmado": False, "perfil": p.perfil.para_dono()}


@router.post("/{codigo}/participantes/{pid}/confirmar")
def confirmar(codigo: str, pid: str, x_token: str | None = Header(None),
              g: GerenciadorSalas = Depends(obter_gerenciador)):
    """Tela 2: botão "Confirmar em Segredo"."""
    try:
        g.confirmar(codigo, pid, x_token)
        return {"participante_id": pid, "confirmado": True, "sala": g.painel(codigo)}
    except ErroSala as e:
        raise _erro(e)


@router.get("/{codigo}/participantes/{pid}")
def minha_visao(codigo: str, pid: str, x_token: str | None = Header(None),
                g: GerenciadorSalas = Depends(obter_gerenciador)):
    """O próprio perfil (com o teto) e o próprio custo e tempo em cada cartão. Só para o dono."""
    try:
        return g.visao_do_participante(codigo, pid, x_token)
    except ErroSala as e:
        raise _erro(e)


@router.post("/{codigo}/gerar-sugestoes")
def gerar_sugestoes(codigo: str, x_token: str | None = Header(None),
                    g: GerenciadorSalas = Depends(obter_gerenciador)):
    """Tela 3: cruza horários, aplica o teto do grupo e o deslocamento e devolve 3 a 4 cartões."""
    try:
        return g.gerar_sugestoes(codigo, x_token)
    except ErroSala as e:
        raise _erro(e)


@router.post("/{codigo}/votar")
def votar(codigo: str, req: Votar, x_token: str | None = Header(None),
          g: GerenciadorSalas = Depends(obter_gerenciador)):
    """Tela 3: votação múltipla. Quando todos os confirmados votam, a votação fecha sozinha."""
    try:
        return g.votar(codigo, req.participante_id, x_token, req.opcoes)
    except ErroSala as e:
        raise _erro(e)


@router.post("/{codigo}/fechar-votacao")
def fechar_votacao(codigo: str, x_token: str | None = Header(None),
                   g: GerenciadorSalas = Depends(obter_gerenciador)):
    """Tela 3: o organizador fecha a votação sem esperar quem não votou (RF-25)."""
    try:
        return g.fechar_votacao(codigo, x_token)
    except ErroSala as e:
        raise _erro(e)
