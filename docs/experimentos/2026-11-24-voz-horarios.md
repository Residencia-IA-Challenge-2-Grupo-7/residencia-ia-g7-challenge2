# Experimento de 24/11: voz no campo de horários

Medições do [ADR 0017](../decisoes/0017-voz-no-campo-de-horarios.md), com **voz sintética** (Microsoft Maria, Windows). Serve para comparar configurações e achar defeitos, não para afirmar acerto com pessoas: em 05/11 a voz real errou bem mais que a sintética (WER de 11,5% contra 3,8%).

## Ponta a ponta: áudio → texto → janelas

46 gravações: 17 do gabarito, 24 de desenvolvimento e 5 de falha (silêncio, ruído, instrução falada, frase em inglês, fala sem horário). As regras do campo 2 foram corrigidas olhando para as 41 primeiras.

| Modelo | Certos | Perguntou | Erro silencioso | WER | Termos críticos | p50 / p90 | Custo das 46 |
|---|---|---|---|---|---|---|---|
| **Whisper large-v3-turbo** (Groq) | 46 | 0 | 0 | 2,4% | 0,0% | 1,00 / 1,23 s | US$ 0,0050 |
| Whisper large-v3 | 45 | 1 | 0 | 1,3% | 0,0% | 1,86 / 3,13 s | US$ 0,0015 |
| Voxtral Mini Transcribe 3.0 | 45 | 1 | 0 | 2,0% | 0,0% | 1,17 / 1,72 s | US$ 0,0092 |

- Resultados por ID, sem o que foi dito: `eval/resultados/voz-sintetico-*-2026-11-24.json`.
- A diferença entre os modelos é de 1 áudio em 46: não sustenta dizer que um acerta mais. O `turbo` fica por ser o mais rápido. O `large-v3` estourou a meta de 3 s no p90.
- Todos pela OpenRouter, com `zdr` e `data_collection: deny`.

## O vocabulário induzia a hora

O `prompt` do Whisper, usado para gírias, tinha o exemplo "sexta depois das 19h". No áudio "sexta depois das **nove**":

| Vocabulário | O que ouviu (2 rodadas) | Resultado |
|---|---|---|
| Com "sexta depois das 19h" | "sexta depois das **19h**" (2 de 2) | erro silencioso |
| Sem vocabulário | "sexta depois das nove" (2 de 2) | perguntou se é manhã ou noite |
| Gírias, sem dias nem horas (**adotado**) | "sexta depois das nove" (2 de 2) | perguntou se é manhã ou noite |

Sem vocabulário, o ruído virou "Obrigado."; com o adotado, voltou vazio. Um teste impede que dias ou horas voltem ao vocabulário.

## Silêncio

4 s de silêncio viram "E aí" nos três vocabulários. Três barreiras: o app não envia gravação sem volume de fala, o servidor recusa resposta vazia e, se "E aí" passar, o campo pergunta o dia.

## No navegador

Chromium 156 do painel, tamanho de celular, com a voz sintética no lugar do microfone: webm/opus de 25 KB para 6,7 s, resposta em 1,2 s, texto no campo. Também testados: silêncio, cancelar, desfazer, microfone negado, sem microfone, sem rede, trocar de aba, clique duplo, enviar o formulário durante a transcrição, retirar o consentimento e sala DEMO.

## Demonstração com os agentes

`scripts/demo_multimodal.py`, [log](../entregas/semana-05/DEMO_MULTIMODAL_LOG.txt). Com só a fala de uma pessoa trocada, a janela do grupo passou de sábado 14h–18h para domingo 13h–24h, e os cartões mudaram.

- A voz levou cerca de 1 s por fala; **os agentes levaram de 44,5 a 64,9 s**, e uma das rodadas passou dos 60 s do RNF-14. Não é da voz: o juiz dos cartões é a etapa lenta, como já registrado em 20/11. Em uma das rodadas, o juiz LLM não respondeu e as regras assumiram.
- No Langfuse, os 6 spans `voz_transcricao` têm entrada e saída vazias, e nenhuma das frases ditas apareceu nas 33 observações do período.

## Falta medir

- **Voz real** com o caminho novo, inclusive as 22 gravações de 05/11: o termo delas não citava a OpenRouter, e a pessoa precisa confirmar.
- **Conjunto cego** e mais pessoas ([como acrescentar](../../eval/voz/README.md)).
- **Aparelhos:** microfone de verdade no Android e no iPhone (Safari grava mp4).
- A troca para a reserva com a Groq realmente fora do ar. Foi testada com provedor inexistente na frente (a DeepInfra atendeu) e com falhas simuladas nos testes.
