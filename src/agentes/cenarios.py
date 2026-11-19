"""Cenários de teste do multiagente (issue #66) na forma que o grafo recebe.

`data/cenarios_teste_multiagente.json` guarda, para cada amigo, os 4 campos da Tela 2 e o gabarito do que o
sistema deve concluir. Esta função monta só a entrada do fluxo (`executar_fluxo_multiagente(dados_sala)`, #71):

    {"codigo": "ROLE-PADR", "agora": "2026-11-17T12:00:00",
     "membros": [{"nome", "origem", "horarios", "teto", "preferencias"}, ...]}

Uma conversão só, para a demonstração (#74) e os testes da Logística (#67) e da Validação (#68) não escreverem
cada um a sua. Dois cuidados que ela garante:

- `agora` é sempre o `agora_referencia` do cenário: sem ele, "sábado das 14h às 22h" vira o sábado seguinte ao
  dia em que o teste roda, e as janelas mudam;
- nada do gabarito (interpretação esperada, vetos, veredito) nem o marcador m1..m4 entra na entrada: o grafo
  numera os membros sozinho, e o sistema testado não pode ver a resposta.

    from src.agentes.cenarios import carregar_cenario, para_entrada_do_grafo
    dados_sala = para_entrada_do_grafo(carregar_cenario("cenario_controle_viavel"))
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

ARQUIVO_CENARIOS = Path(__file__).resolve().parents[2] / "data" / "cenarios_teste_multiagente.json"
CAMPOS_TELA2 = ("origem", "horarios", "teto", "preferencias")


@lru_cache(maxsize=1)
def _dataset() -> dict:
    return json.loads(ARQUIVO_CENARIOS.read_text(encoding="utf-8"))


def carregar_cenarios() -> list[dict]:
    """Todos os cenários do dataset, na ordem do arquivo (o padrão primeiro)."""
    return list(_dataset()["cenarios"])


def carregar_cenario(cenario_id: str) -> dict:
    """Um cenário pelo id. KeyError com os ids que existem, se não achar."""
    for cenario in _dataset()["cenarios"]:
        if cenario["id"] == cenario_id:
            return cenario
    existentes = ", ".join(c["id"] for c in _dataset()["cenarios"])
    raise KeyError(f"Cenário {cenario_id!r} não existe. Cenários do dataset: {existentes}.")


def para_entrada_do_grafo(cenario: dict) -> dict:
    """Cenário do dataset -> `dados_sala` do fluxo multiagente, só com o que a Tela 2 teria recebido."""
    return {
        "codigo": cenario["codigo_sala"],
        "agora": cenario["agora_referencia"],
        "membros": [
            {"nome": amigo["nome_ficticio"], **{campo: amigo["campos_tela2"][campo] for campo in CAMPOS_TELA2}}
            for amigo in cenario["amigos"]
        ],
    }
