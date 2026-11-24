# Áudios de teste da voz

Mede o caminho inteiro do [ADR 0017](../../docs/decisoes/0017-voz-no-campo-de-horarios.md): áudio → texto → janelas do campo 2. Para julgar áudios novos não é preciso mexer no código.

## Consentimento (LGPD, RNF-01)

Voz é dado pessoal. Antes de gravar, cada pessoa confirma por escrito, no chat do grupo:

> Autorizo o uso das minhas gravações de teste do Orquestrador de Rolês só para medir a entrada por voz no projeto da Residência em IA. Sei que elas são enviadas à OpenRouter (Groq ou DeepInfra), em modo sem retenção, para virar texto. Elas ficam fora do repositório, identificadas por um código (m1, m2…), e são apagadas depois da medição final da semana 6.

- A correspondência entre código e pessoa não vai para o repositório.
- Quem gravou com o termo de 05/11, que não citava a OpenRouter, confirma este antes de o áudio ser usado de novo.
- Não diga nomes, endereços nem valores nas gravações.

## Acrescentar áudios

1. **Gabarito primeiro.** Escreva o esperado antes de ver o resultado, uma linha por fala em [falas.jsonl](falas.jsonl):

   ```json
   {"id": "C01", "conjunto": "cego", "texto": "o que foi dito, palavra por palavra", "criticos": ["sexta", "19"], "esperado": [{"janelas": [["2026-11-06 19:00", "2026-11-07 00:00", true]]}]}
   ```

   - `id`: uma ou duas letras e 2 ou 3 dígitos, sem repetir. Sugestão: `C01`, `C02`… para o conjunto cego.
   - As datas valem para **quinta, 05/11/2026, 10h**, a menos que a linha traga `"agora": "2026-12-01T10:00:00"`.
   - Meia-noite é `00:00` do dia seguinte. O terceiro valor é `true` (pode) ou `false` (não pode).
   - Quando o certo é o app perguntar: `{"pergunta": "falta_dia"}`, `hora_ambigua`, `horario_invalido` ou `so_negativa`.

2. **Áudio** em `data/raw/voz/<conjunto>/<código da pessoa>/<ID>.<ext>` (fora do git), em webm, m4a, mp4, ogg ou wav. Várias gravações do mesmo ID podem levar sufixo: `C01-rua.m4a`.

3. **Conferir** (sem rede) e **medir**:

   ```bash
   python -m src.voz conferir data/raw/voz/cego
   python -m src.voz medir data/raw/voz/cego
   ```

4. **Julgar à mão**, se quiser: abra o CSV indicado no fim, preencha a coluna `julgamento` com `certo` ou `errado` e rode `python -m src.voz julgar <csv>`. O resumo diz onde a pessoa e o veredito automático divergem.

## Conjuntos

| Conjunto | O que é | Serve para medir acerto? |
|---|---|---|
| `gabarito` | 17 frases de disponibilidade de 05/11 ([frases.jsonl](../interpretador/frases.jsonl)) | Não mais: as regras foram corrigidas olhando para elas |
| `desenvolvimento` | 24 frases coloquiais ([horarios_fala.jsonl](../interpretador/horarios_fala.jsonl)) | Não |
| `cego` | Falas livres gravadas **depois** de congelar o interpretador (commit `2b90167`) | **Sim.** Ainda vazio |
| `falha` | Silêncio, ruído, instrução falada, outro idioma, fala sem horário | Só para as falhas |

Se uma frase do conjunto cego levar a mudar uma regra, ela passa para `desenvolvimento` e outra fala entra no lugar.

## O que vai para o git

Só `eval/resultados/voz-*.json`, com números e o veredito de cada ID, **sem o que foi dito**. Áudios e CSV com transcrição ficam em `data/raw/voz/`.

## Vereditos

| Veredito | Significado |
|---|---|
| `certo` | Janelas iguais ao gabarito, ou a pergunta esperada |
| `perguntou` | O app não entendeu e perguntou: incômodo, mas seguro |
| `erro_silencioso` | Entendeu outra coisa e não perguntou: o erro que importa |
| `sem_transcricao` | A transcrição falhou |
