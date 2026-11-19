"""Rotas HTML das Telas 1 a 3 do guia oficial (issue #42), montadas em `src/main.py`.

| Rota                      | Tela | O que mostra                                               |
|---------------------------|------|------------------------------------------------------------|
| `/app`                    | 1    | Criar sala (ou entrar com um código) e link de convite     |
| `/sala/{codigo}/perfil`   | 2    | Os 4 campos secretos e o resumo para confirmar em segredo  |
| `/sala/{codigo}`          | 3    | Painel: quem preencheu, 3 a 4 cartões, votação e resultado |

As páginas são estáticas: o JavaScript lê o código da URL e conversa com a API de `src/salas/rotas.py`.
O servidor nunca injeta dado da sala no HTML, então nada de teto, origem ou horário passa por aqui.
`/sala/demo` e `/sala/demo/perfil` funcionam sem back-end, com dados de exemplo (prints e testes).

Os tokens ficam no `localStorage` do aparelho e vão no cabeçalho `X-Token`, nunca na URL.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

PASTA = Path(__file__).resolve().parent
PAGINAS = PASTA / "paginas"
ESTATICOS = PASTA / "static"

router = APIRouter(tags=["Telas do app"])
estaticos = StaticFiles(directory=ESTATICOS)  # montado em /static/telas pelo main.py

# Sem cache no HTML: a página muda junto com o deploy e não guarda nada da sala.
_SEM_CACHE = {"Cache-Control": "no-cache"}


def _pagina(nome: str) -> HTMLResponse:
    return HTMLResponse((PAGINAS / nome).read_text(encoding="utf-8"), headers=_SEM_CACHE)


@router.get("/app", response_class=HTMLResponse)
def tela_criar_sala():
    """Tela 1: criar a sala (nome do organizador e do rolê) e gerar o link de convite."""
    return _pagina("app.html")


@router.get("/sala/{codigo}/perfil", response_class=HTMLResponse)
def tela_perfil(codigo: str):
    """Tela 2: os 4 campos de texto secretos e o resumo interpretado para confirmar."""
    return _pagina("app.html")


@router.get("/sala/{codigo}", response_class=HTMLResponse)
def tela_painel(codigo: str):
    """Tela 3: painel da sala, cartões de sugestão, votação múltipla e resultado."""
    return _pagina("app.html")


@router.get("/manifest.webmanifest", include_in_schema=False)
def manifesto():
    """Manifesto do PWA (RNF-09): permite instalar o app na tela inicial do celular."""
    return FileResponse(ESTATICOS / "manifest.webmanifest", media_type="application/manifest+json")


@router.get("/sw.js", include_in_schema=False)
def service_worker():
    """Service worker na raiz para ter escopo `/` (RNF-09). Não guarda resposta da API."""
    return FileResponse(ESTATICOS / "sw.js", media_type="text/javascript",
                        headers={"Cache-Control": "no-cache", "Service-Worker-Allowed": "/"})
