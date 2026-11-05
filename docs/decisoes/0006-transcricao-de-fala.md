# 0006 — Transcrição de fala (entrada por voz)

- **Status:** proposta (o modelo final depende das gravações da equipe; ver [Como vamos validar](#como-vamos-validar))
- **Data:** 2026-11-05
- **Semana do roadmap:** 2 (preparação). A entrada multimodal é entrega da semana 5 (RNF-12)
- **Requisitos:** RF-39, RF-40 (fora deste ADR), RNF-01, RNF-07, RNF-08, RNF-12, RNF-14, RNF-15
- **Relacionado:** [ADR 0007](0007-interpretador-e-contrato-de-busca.md), que recebe o texto transcrito

## Contexto

O RF-39 pede voz em toda conversa com a IA, pensando principalmente no Márcio, a persona com pouca prática em apps (RNF-07). A transcrição alimenta o interpretador do ADR 0007. Por isso, o que mais importa é acertar os termos que viram ação: dias, horas, valores, nomes, regiões administrativas e gírias ("rolê", "bora", "rachar", "conto", "pila").

Restrições que não mudam:

- **RNF-01:** o áudio é descartado logo depois da transcrição.
- **RF-39:** a transcrição sempre passa por confirmação antes de qualquer ação com data, valor ou presença. Quem confirma é a pessoa, então um erro de transcrição não vira dado sem ser visto.
- **RNF-12:** o provedor é trocável por configuração.
- **RNF-14:** a resposta na conversa sai em até 5 s no p90, o que inclui a transcrição e a interpretação.
- **RNF-15 e P12:** os testes do MVP precisam caber em créditos gratuitos.

**Hardware disponível:**

- notebook Windows com i5-1334U, 16 GB e sem GPU NVIDIA;
- um MacBook M4, acessível ao Cauan;
- o servidor do MVP ainda não foi escolhido.

## Opções consideradas

| Opção | Prós | Contras | Viabilidade |
|---|---|---|---|
| **A. faster-whisper local** (CTranslate2, int8 na CPU): `small`, `medium`, `large-v3-turbo` | Custo zero; o áudio não sai da máquina; roda em Windows, Linux e Mac | Lento em CPU fraca: os modelos maiores podem estourar os 5 s; o servidor do MVP precisaria de CPU boa ou GPU | Alta; mede-se a latência |
| **B. mlx-whisper no Mac M4** (`whisper-large-v3-turbo` em MLX) | Usa a GPU do Apple Silicon, perto do tempo real com o modelo grande; o áudio não sai da máquina | Só roda em Mac; serve para o experimento e as demonstrações, não para um servidor Linux | Alta para medir, baixa como produção |
| **C. Groq, `whisper-large-v3-turbo` por API** | Muito rápido; US$ 0,04 por hora de áudio com cobrança mínima de 10 s por pedido (cerca de US$ 0,0001 por frase); tem faixa gratuita | O áudio vai para terceiros nos EUA; a retenção zero precisa ser ligada nos Data Controls da conta; depende de rede e de chave | Alta |
| D. API da OpenAI (`gpt-4o-transcribe`) | Costuma ter o menor erro em português | Paga, sem crédito gratuito garantido; áudio para terceiros | Média; fora da primeira rodada |
| E. Web Speech API do navegador | Grátis, sem servidor | O Chrome manda o áudio ao Google sem controle de retenção, o Safari no iOS se comporta de outro jeito e a medição não é reproduzível | Baixa |

A primeira rodada mede **A, B e C** (escolha do grupo em 05/11). D fica como reserva se nenhuma passar na meta de erro. E fica fora pelos problemas de privacidade e de reprodutibilidade.

## Decisão

1. **Família Whisper**, atrás de uma interface única (`src/voz/`): `transcrever(áudio) → texto`, com o provedor escolhido em `src/voz/config.toml` (`faster_whisper`, `mlx_whisper` ou `groq`).
2. **Escolha por medição, não por reputação:** fica o provedor e o modelo que cumprirem as metas abaixo nas gravações da equipe, com esta ordem de desempate: (1) erro nos termos críticos, (2) p90 de latência, (3) privacidade (local antes de API) e (4) custo.
3. **Padrão provisório até a medição:** `faster-whisper small` local, o único que roda em qualquer máquina sem chave. Com a chave do Groq no `.env`, ele entra na comparação. Se for o escolhido, a retenção zero precisa estar ligada na conta.
4. **Vocabulário do domínio no prompt inicial** do Whisper: gírias, nomes de RAs e "Pix" e "Uber". O efeito é medido com e sem o prompt, porque o prompt também pode induzir alucinação em trechos de silêncio.
5. **Descarte do áudio:**
   - no fluxo do app, o áudio chega em bytes e vai para um arquivo temporário, apagado num `finally` depois da transcrição, com ou sem erro;
   - nada é registrado com o áudio, nem com o texto transcrito antes da confirmação (RNF-10 guarda só eventos).
6. **Confirmação sempre:** quem chama a transcrição recebe só texto. A ação com data, valor ou presença sai do interpretador marcada como `requer_confirmacao` (ADR 0007).

## Justificativa e evidências

- O Whisper aceita português sem ajuste e tem implementações locais e por API com a mesma família de modelos. Assim, a troca de provedor muda latência, custo e privacidade, mas não o comportamento.
- O WER sozinho engana. "Sexta" trocado por "sesta", ou "90" por "19", vale uma palavra no WER e estraga a ação. Por isso o critério principal é o **erro nos termos críticos**, marcados no gabarito de cada frase. A confirmação do RF-39 é a segunda trava.
- Preços e retenção do Groq foram conferidos em 05/11/2026, na [página de preços](https://groq.com/pricing) e na página [Your Data](https://console.groq.com/docs/your-data). As fontes divergem sobre o padrão de retenção dos endpoints de áudio, então a retenção zero precisa ser ligada explicitamente.

## Riscos e limitações

| Risco | Ligação | Mitigação |
|---|---|---|
| Sotaque, ruído e gíria derrubam o acerto | R-09, RNF-08 | Gravações reais da equipe, em ambiente comum; vocabulário no prompt; confirmação do RF-39; tudo que se faz por voz também se faz por texto (RNF-07) |
| Voz é dado pessoal | RNF-01 | Descarte imediato no app. As gravações de teste só com consentimento escrito, fora do git, apagadas depois da medição final, com os nomes trocados por m1 a m5 nos arquivos |
| Áudio enviado ao Groq | RNF-01 | Retenção zero ligada; a medição diz se o ganho justifica a API; o padrão local continua disponível |
| Latência local em servidor sem GPU | RNF-14 | Medida no notebook (pior caso) e no M4; se nenhum local cumprir a meta, a API vira o padrão e o local a reserva (RNF-15) |
| Medição com só 5 vozes | — | Resultado reportado com intervalo de confiança; o teste com usuários do MVP mede de novo |
| Voz sintética parece mais fácil do que é | — | O TTS (vozes pt-BR do Windows e do macOS) só testa o pipeline e a latência; não entra no WER oficial |

## Como vamos validar

**Conjunto:** as 50 frases de [eval/interpretador/frases.jsonl](../../eval/interpretador/frases.jsonl), 10 lidas por cada um dos 5 integrantes ([roteiro de gravação](../../eval/voz/roteiro.md)). Cada frase tem o texto exato e a lista de termos críticos.

| Métrica | Como medir | Meta |
|---|---|---|
| Erro nos termos críticos | Termos do gabarito ausentes na transcrição normalizada ÷ termos críticos | ≤ 5% |
| WER | Distância de edição por palavra, com texto normalizado (minúsculas, sem pontuação, números por extenso viram dígitos) | ≤ 15% |
| Latência | Tempo da transcrição com o modelo já carregado, p50 e p90 por frase | p90 ≤ 2,5 s, metade do orçamento do RNF-14 |
| Custo | Local: zero. API: preço por hora × duração faturada (mínimo de 10 s) | Dentro dos créditos gratuitos (P12) |
| Acerto da intenção a partir da voz | O interpretador do ADR 0007 aplicado à transcrição | Diferença de no máximo 5 pontos para o acerto com o texto digitado |

Como rodar: `python -m voz medir` ([src/voz/README.md](../../src/voz/README.md)). Os resultados vão para `eval/resultados/`.

## Resultados

### Prévia com voz sintética (05/11, notebook Windows, CPU)

**Condições da prévia:**

- só testa o pipeline e a latência; não é o resultado oficial;
- 50 frases lidas pela voz "Microsoft Maria Desktop" (local);
- faster-whisper com int8, feixe 1, VAD e 8 threads, no i5-1334U sem GPU;
- detalhes por frase em [eval/resultados/](../../eval/resultados/).

| Modelo | Prompt de vocabulário | WER | Erro nos termos críticos | Latência p50 / p90 | Tempo ÷ duração |
|---|---|---|---|---|---|
| `small` | sim | 5,1% | 7,2% (9 frases) | 4,2 / 5,5 s | 1,0 |
| `small` | não | 7,6% | 10,8% (12 frases) | 3,1 / 3,8 s | 0,8 |
| `medium` | sim | 7,3% | 5,0% (7 frases) | 10,4 / 11,0 s | 2,3 |
| `large-v3-turbo` | sim | 4,1% | 3,6% (5 frases) | 16,3 / 17,5 s | 3,6 |
| **Groq** `whisper-large-v3-turbo` | sim | 3,8% | 3,6% (5 frases) | 0,8 / 1,0 s | 0,2 |

O Groq custou US$ 0,0056 pelas 50 frases, porque cada pedido é cobrado por no mínimo 10 s. O plano gratuito devolveu HTTP 429 depois de cerca de 20 pedidos seguidos. Por isso, a transcrição tenta de novo respeitando o `retry-after`, e a medição faz uma pausa de 3,5 s entre os pedidos, fora do tempo medido.

**Caminho completo com voz sintética** (Groq e depois o interpretador do ADR 0007): 32 de 34 frases certas no RNF-08 (94,1%), contra 33 de 34 com o texto digitado. A diferença está dentro da meta de 5 pontos. Os dois erros que a voz acrescentou:

- "Aza Sul": a RA não casou;
- "Só de noite?": a interrogação fez a frase virar conversa.

A transcrição levou até 1 s e a interpretação até 2,1 s, ambas no p90, dentro dos 5 s do RNF-14.

**Leitura:**

- **Nenhum modelo local cumpre a latência neste notebook.** As latências são pessimistas, porque outra sessão usava cerca de um núcleo durante a rodada. Isolado, com a máquina livre, o `small` levou cerca de 2,5 s por frase. O piso vem do Whisper, que sempre codifica uma janela de 30 s: frase curta custa quase o mesmo que frase longa.
- **O `large-v3-turbo` é o único abaixo da meta de 5% nos termos críticos**, mas leva mais de 16 s na CPU. Para usá-lo, ele precisa de GPU (o M4 ou um servidor) ou da API do Groq.
- **"Sexta" virou "6."** no `small` (D01, D16, M01, P02). Some com o `large-v3-turbo`. É um erro que muda o dia da ação e que o WER conta como uma palavra.
- **O prompt de vocabulário ajuda:** sem ele, o `small` perdeu "Ceilândia", "Sudoeste", "Airbnb", "chácara" e "conto". O erro nos termos críticos subiu de 7,2% para 10,8%, e ele fica ligado.
- **Gírias seguem difíceis:** "topa", "vamo", "liso" e "pila" falharam em quase todos. Parte disso é a voz sintética, que pronuncia gíria mal, e as gravações reais vão dizer quanto.
- **Decodificação:** chamar o ffmpeg como processo custava mais de 1 s por frase no Windows. O PyAV no mesmo processo leva cerca de 15 ms, com a mesma saída.

**Consequência provisória:** com voz sintética, o Groq cumpre todas as metas: 3,6% de erro nos termos críticos, p90 de 1,0 s e custo desprezível. O `large-v3-turbo` local só empata no acerto com GPU (M4), e o `small` local fica como reserva sem rede. Trocar o padrão da configuração para o Groq depende de duas coisas:

- a retenção zero ligada na conta;
- a confirmação do resultado com as gravações reais.

### Gravações da equipe (05/11, primeira parte)

**Condições:**

- 22 gravações de **uma só pessoa** (m1), em celular, das 50 frases;
- o Groq já com a retenção zero ligada;
- o `small` no notebook Windows, com a máquina livre;
- falta a voz dos outros integrantes;
- detalhes por frase em [eval/resultados/](../../eval/resultados/).

| Provedor e modelo | WER | Erro nos termos críticos | Latência p50 / p90 | Custo |
|---|---|---|---|---|
| **Groq** `whisper-large-v3-turbo` | 11,5% | 5,9% (4 frases) | 0,7 / 0,8 s | US$ 0,0024 |
| faster-whisper `small` (CPU) | 15,7% | 13,2% (8 frases) | 2,0 / 2,1 s | — |

**Leitura:**

- **A voz real é mais difícil que a sintética.** O WER do Groq subiu de 3,8% para 11,5%, mas o erro nos termos críticos ficou perto da meta (5,9% contra 5%).
- **Erros do Groq que importam:** "Itaguatinga" (Taguatinga) e "livre de todo" (dia todo). "Vamos" e "ignora", no lugar de "vamo" e "ignore", podem ter sido ditos assim e não mudam a ação.
- **O `small` erra o que muda a ação:** "sexta" virou "6º" e "cesta", "Caio" virou "caiu", "cem" virou "sem", "Bia" virou "via". Fica descartado como modelo principal.
- **Caminho completo** (Groq e depois o interpretador do ADR 0007): as 13 frases de disponibilidade e gastos certas. O interpretador entendeu até "livre de todo". O único erro foi "Itaguatinga", que não casou com a RA.

**Pendente:**

- as outras 28 frases e a voz dos demais integrantes;
- a rodada no Mac M4 (`mlx_whisper` e faster-whisper `large-v3-turbo` na CPU do M4), para saber se um modelo local grande fica perto do Groq.

## Histórico

- 2026-11-05: proposta, depois de três rodadas de perguntas com o Cauan (candidatos, conjunto de teste, gravações).
- 2026-11-05: prévia com voz sintética (faster-whisper `small`, `medium` e `large-v3-turbo`, com e sem prompt).
