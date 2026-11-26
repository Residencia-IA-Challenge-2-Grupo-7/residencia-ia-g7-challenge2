# src/voz — voz no campo de horários

RF-47, [ADR 0017](../../docs/decisoes/0017-voz-no-campo-de-horarios.md) (proposta). Áudio vira texto editável no campo 2 da Tela 2; daí em diante vale o caminho de quem digita (`src/interpretador/campos.py`).

Esta pasta é só o backend. O botão de gravar e a medição com áudios ficam na branch `feat/semana5-voz`.

| Arquivo | Papel |
|---|---|
| `config.toml` | Modelo, provedores sem retenção, vocabulário e limites (RNF-12) |
| `transcrever.py` | Áudio em bytes → texto, só em memória; formato pela assinatura; segunda tentativa na reserva |
| `limites.py` | Cotas por sala, por dia e de pedidos ao mesmo tempo |
| `rotas.py` | `GET /api/voz` e `POST /api/salas/{codigo}/voz/horarios` |

## Contrato

`GET /api/voz` diz se há voz (`disponivel`, `max_s`, `max_caracteres`), sem expor a chave. Sem `OPENROUTER_API_KEY`, `disponivel` é `false`.

`POST /api/salas/{codigo}/voz/horarios`, com o áudio cru no corpo e `X-Consentimento-Voz: 1`:

| Código | Quando |
|---|---|
| 200 | `{"texto": "...", "aviso": null}`, com `Cache-Control: no-store` |
| 403 | Sem consentimento |
| 404, 409 | Sala inexistente; rolê já orquestrado |
| 413, 415 | Acima de 1 MB; não é webm, mp4, ogg ou wav |
| 422 | Nada ouvido |
| 429 | Cota esgotada |
| 503 | Sem chave ou provedores fora do ar |

Erros vêm em `detail.mensagem`, prontos para mostrar. A rota só devolve o texto: quem chama o põe no campo, e a pessoa confirma.

## Regras

- Nunca gravar áudio ou texto em disco, log, métrica ou Langfuse; `tests/test_voz.py` confere.
- Nunca pôr dias ou horas no vocabulário: o modelo passa a ouvi-los (medido em 24/11).
- Nunca estender o microfone a origem e limite de gasto sem rever os ADRs 0008 e 0009.
- No navegador, não usar o reconhecimento de fala do próprio navegador (`SpeechRecognition`): o áudio vai ao fabricante sem controle de retenção.

## Testar

```bash
python -m pytest tests/test_voz.py tests/test_campos.py
python -m src.interpretador --audio caminho/do/audio.m4a   # envia o áudio à OpenRouter, sem retenção
```
