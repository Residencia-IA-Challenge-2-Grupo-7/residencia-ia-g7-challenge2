# Entrada por voz

Implementação do [ADR 0006](../../docs/decisoes/0006-transcricao-de-fala.md): transcrição da família Whisper atrás de uma interface única. O provedor é trocado em [config.toml](config.toml): `faster_whisper` (local, CPU), `mlx_whisper` (local, Mac com Apple Silicon) ou `groq` (API).

- **RNF-01:** no app, o áudio chega em bytes, vai para um arquivo temporário e é apagado num `finally`, com ou sem erro. Nada é registrado.
- **RF-39:** o texto transcrito passa pelo [interpretador](../interpretador/README.md), que marca como `requer_confirmacao` toda ação com data, valor ou presença.

## Preparar

```bash
.venv/Scripts/python -m pip install -r requirements.txt   # inclui faster-whisper
```

Precisa do `ffmpeg` no PATH: ele decodifica qualquer formato (m4a do celular, webm do navegador) para 16 kHz mono. No Mac, para o MLX:

```bash
pip install mlx-whisper && brew install ffmpeg
```

O Groq precisa de `GROQ_API_KEY` no `.env`. Ligue também a retenção zero nos Data Controls da conta antes de mandar voz de alguém.

## Rodar

Da raiz, com `PYTHONPATH=src`:

| Comando | O que faz |
|---|---|
| `python -m voz transcrever arquivo.m4a [--provedor groq]` | Transcreve um arquivo (não o apaga) |
| `python -m voz sintetizar` | Gera as 50 frases com voz sintética local em `data/raw/voz/sintetico/` (Windows: Maria; Mac: Luciana). Só testa o pipeline: não entra no WER oficial |
| `python -m voz medir <pasta> [--provedor ...] [--modelo ...] [--sem-prompt]` | WER, erro nos termos críticos, latência p50/p90, tempo ÷ duração e custo. Grava `eval/resultados/voz-*.json` e `transcricoes-*.json` |
| `python -m interpretador --audio arquivo.m4a` | Transcreve e interpreta |

Rodada no Mac M4, para comparar com o notebook:

```bash
PYTHONPATH=src python -m voz medir data/raw/voz/equipe --provedor mlx_whisper --rotulo equipe
PYTHONPATH=src python -m voz medir data/raw/voz/equipe --provedor faster_whisper --modelo small --rotulo equipe
```

As gravações seguem o [roteiro](../../eval/voz/roteiro.md): `data/raw/voz/equipe/m1/D01.m4a` etc.

## Normalização do WER

Minúsculas, sem acento nem pontuação; números por extenso viram dígitos ("cento e oitenta" = "180"); "19h" e "19 horas" viram "19"; "R$" e "reais" saem. O **erro nos termos críticos** confere se cada termo marcado no gabarito (dias, horas, valores, nomes, RAs, gírias) aparece na transcrição normalizada. É o critério principal, porque "sexta" transcrita como "6" vale uma palavra no WER e estraga a ação.
