# src/voz — voz no campo de horários

RF-47, [ADR 0017](../../docs/decisoes/0017-voz-no-campo-de-horarios.md) (proposta). Áudio vira texto editável no campo 2 da Tela 2; daí em diante vale o caminho de quem digita.

| Arquivo | Papel |
|---|---|
| `config.toml` | Modelo, provedores sem retenção, vocabulário e limites (RNF-12) |
| `transcrever.py` | Áudio em bytes → texto, só em memória; formato pela assinatura; segunda tentativa na reserva |
| `limites.py` | Cotas por sala, por dia e de pedidos ao mesmo tempo |
| `rotas.py` | `GET /api/voz` e `POST /api/salas/{codigo}/voz/horarios` |
| `medir.py`, `wer.py`, `sintetizar.py`, `__main__.py` | Medição de ponta a ponta ([eval/voz](../../eval/voz/README.md)) |
| `../telas/static/voz.js` e `voz.css` | O botão de falar, isolado das outras telas |

## Contrato

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

Erros vêm em `detail.mensagem`, prontos para mostrar.

## Para quem redesenha a Tela 2

Mantenha `<textarea id="horarios">`, o `<link>` de `voz.css` e o `<script>` de `voz.js` depois de `perfil.js`. O componente se monta sozinho depois do campo e usa só as variáveis de `app.css`. Não use o reconhecimento de fala do navegador (`SpeechRecognition`): o áudio vai ao fabricante sem controle de retenção.

## Regras

- Nunca gravar áudio ou texto em disco, log, métrica ou Langfuse; `tests/test_voz.py` confere.
- Nunca pôr dias ou horas no vocabulário: o modelo passa a ouvi-los (24/11).
- Nunca estender o microfone a origem e limite de gasto sem rever os ADRs 0008 e 0009.

## Rodar

```bash
python -m src.voz conferir data/raw/voz/<pasta>   # sem rede
python -m src.voz medir data/raw/voz/<pasta>      # envia os áudios à OpenRouter, sem retenção
python -m pytest tests/test_voz.py
```
