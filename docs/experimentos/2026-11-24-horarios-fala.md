# Experimento de 24/11: horários ditos como na fala (campo 2 da Tela 2)

## O que foi medido

O campo 2 ("dias e horários") é lido por regras, sem LLM ([ADR 0009](../decisoes/0009-entrada-pelos-4-campos-de-texto.md)). Não achamos medição registrada da meta do ADR (90% sem pergunta). Antes de ligar a voz, rodamos as regras sobre as frases de disponibilidade do [gabarito](../../eval/README.md) e sobre as transcrições guardadas em 05/11, sem reenviar áudio de ninguém.

O critério que mais importa é o **erro silencioso**: o app entende outra janela e não pergunta nada.

## Resultados

| Entrada | Antes: certas | Antes: silenciosos | Depois: certas | Depois: silenciosos |
|---|---|---|---|---|
| Texto digitado | 16 de 17 | 1 | 17 de 17 | 0 |
| Voz sintética, Whisper turbo (Groq) | 15 de 17 | 2 | 17 de 17 | 0 |
| Voz real de uma pessoa, Whisper turbo (Groq) | 4 de 6 | 2 | 6 de 6 | 0 |

**Como ler:** as regras foram corrigidas olhando estas mesmas frases e mais 24 coloquiais escritas para isso ([horarios_fala.jsonl](../../eval/interpretador/horarios_fala.jsonl)). O "depois" mostra que os erros achados foram corrigidos; não prova acerto em frases novas. Para isso falta o **conjunto cego**: falas livres gravadas com o interpretador congelado.

Com modelos de transcrição piores (Whisper `small`), o que sobrou foi "sexta" virar "6º" ou "sesta", e nesses casos o app pergunta o dia.

## O que mudou

- Horas por extenso ("dezenove horas", "oito e meia da noite") e por fala ("18 horas", "às 20", "lá pelas 18h30").
- "Das duas às seis", "das 7 às 11 da noite": os dois lados na mesma parte do dia. O segundo caso era uma ambiguidade conhecida do ADR 0009.
- "Mas tenho que voltar até as 23h" restringe o que já foi dito, em vez de abrir outra janela.
- "Saio às 18h, depois disso tô livre", "trabalho até as 18h" (livre depois), "aula das 14h às 18h" (não pode).
- "De sexta a domingo", "6ª feira", "qualquer dia menos sexta", "sexta à noite e sábado à tarde" sem vírgula.
- **Trava:** hora que as regras não usaram, "depois do trabalho" sem hora, "cedo", "mais tarde" e "de madrugada" viram pergunta. Antes viravam "dia todo".
- Hora de 8 a 11 dita sem "h" nem parte do dia ("depois das 9") pergunta se é de manhã ou de noite.
- Só negativas ("sexta não posso") pergunta quando a pessoa pode.

## Limitações

- "Sexta à noite, sábado" continua com sábado o dia todo. O resumo mostra, e a pessoa confirma.
- "Depois do almoço" vale 13h, o início da tarde na tabela de períodos.
- "Fim da tarde" vale a tarde inteira (13h às 18h).
- A trava aumenta o número de perguntas. O efeito no uso real ainda não foi medido.
