"""Rotas da voz (ADR 0017, RF-47), montadas em `src/main.py`.

| Rota                                     | O que faz                                                             |
|------------------------------------------|-----------------------------------------------------------------------|
| `GET  /api/voz`                          | Diz se há voz neste servidor e os limites (o botão só aparece se houver) |
| `POST /api/salas/{codigo}/voz/horarios`  | Áudio no corpo -> `{"texto", "aviso"}` para o campo 2 da Tela 2       |

O corpo é o áudio cru (sem formulário). O texto volta só a quem falou e não é guardado: ele segue pela rota dos 4
campos, se e quando a pessoa enviar. Nem o áudio nem o texto vão para log, métrica ou Langfuse (RNF-01, RNF-10).
"""
from __future__ import annotations

import time

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse

from src.salas.gerenciador_salas import ErroSala, GerenciadorSalas
from src.salas.modelos import ORQUESTRADO
from src.salas.rotas import obter_gerenciador
from src.telemetria.langfuse_agentes import observar_agente, registrar_span_agente
from src.telemetria.logger_metricas import registrar_evento_metrica
from src.voz import transcrever as tr
from src.voz.limites import L, CotaExcedida, Cotas

router = APIRouter(prefix="/api", tags=["Voz"])
_cotas = Cotas()
_SEM_GUARDAR = {"Cache-Control": "no-store"}
_USD_BRL = 5.80  # mesma cotação de referência de logger_metricas.py

_MENSAGENS = {
    "sem_chave": (503, "A voz não está disponível agora. Digite seus horários."),
    "indisponivel": (503, "Não consegui transcrever agora. Digite seus horários ou tente de novo daqui a pouco."),
    "formato": (415, "Não consegui abrir essa gravação. Tente gravar de novo ou digite seus horários."),
    "vazio": (422, "Não ouvi nada. Fale mais perto do microfone ou digite seus horários."),
}


def _erro(status: int, mensagem: str) -> HTTPException:
    return HTTPException(status_code=status, detail={"mensagem": mensagem}, headers=_SEM_GUARDAR)


def obter_cotas() -> Cotas:
    return _cotas


def obter_transcritor():
    """Ponto de troca nos testes."""
    return tr.transcrever


@router.get("/voz")
def situacao():
    return {"disponivel": tr.disponivel(), "max_s": L["max_s"], "max_caracteres": L["max_caracteres"]}


async def _ler_corpo(request: Request) -> bytes:
    maximo = L["max_bytes"]
    declarado = request.headers.get("content-length", "")
    if declarado.isdigit() and int(declarado) > maximo:
        raise _erro(413, f"A gravação ficou longa demais. Fale em até {L['max_s']} segundos.")
    partes, total = [], 0
    async for pedaco in request.stream():
        total += len(pedaco)
        if total > maximo:
            raise _erro(413, f"A gravação ficou longa demais. Fale em até {L['max_s']} segundos.")
        partes.append(pedaco)
    return b"".join(partes)


@observar_agente("voz_transcricao", tipo="span")
def _transcrever(audio: bytes, transcritor) -> tr.Transcricao:
    """Só metadados no span e na métrica: formato, tamanho, tempo, custo e resultado."""
    meta = {"formato": tr.formato_do_audio(audio), "bytes": len(audio), "modelo": tr.T["modelo"]}
    inicio, custo = time.perf_counter(), 0.0
    try:
        t = transcritor(audio)
        custo = t.custo_usd
        meta |= {"resultado": "ok", "segundos_cobrados": t.duracao_s, "tentativas": t.tentativas}
        return t
    except tr.ErroVoz as e:
        meta["resultado"] = e.motivo
        raise
    finally:
        meta["custo_usd"] = custo
        registrar_span_agente("voz_transcricao", **meta)
        registrar_evento_metrica("voz_horarios", (time.perf_counter() - inicio) * 1000,
                                 custo_estimado_brl=round(custo * _USD_BRL, 6), metadados=meta)


@router.post("/salas/{codigo}/voz/horarios")
async def voz_horarios(codigo: str, request: Request, x_consentimento_voz: str | None = Header(None),
                       g: GerenciadorSalas = Depends(obter_gerenciador), cotas: Cotas = Depends(obter_cotas),
                       transcritor=Depends(obter_transcritor)):
    """Tela 2: transcreve a fala do campo de horários. Exige consentimento (RF-02) e não guarda nada."""
    if x_consentimento_voz != "1":
        raise _erro(403, "Para usar a voz, aceite antes o aviso de privacidade. Você também pode digitar.")
    try:
        sala = await run_in_threadpool(g.painel, codigo)
    except ErroSala as e:
        raise _erro(e.status, e.mensagem)
    if sala["status"] == ORQUESTRADO:
        raise _erro(409, "Este rolê já foi orquestrado.")
    audio = await _ler_corpo(request)
    if tr.formato_do_audio(audio) is None:
        raise _erro(*_MENSAGENS["formato"])
    try:
        with cotas.usar(sala["codigo"]):
            t = await run_in_threadpool(_transcrever, audio, transcritor)
    except CotaExcedida:
        raise _erro(429, "Muitas gravações em pouco tempo. Espere um pouco ou digite seus horários.")
    except tr.ErroVoz as e:
        raise _erro(*_MENSAGENS.get(e.motivo, _MENSAGENS["indisponivel"]))
    texto, aviso = t.texto, None
    if len(texto) > L["max_caracteres"]:
        texto = texto[:L["max_caracteres"]].rsplit(" ", 1)[0]
        aviso = "Sua fala passou do tamanho do campo. Confira o final do texto."
    return JSONResponse({"texto": texto, "aviso": aviso}, headers=_SEM_GUARDAR)
