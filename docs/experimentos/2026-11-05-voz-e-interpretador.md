# Experimentos de 05/11: entrada por voz e interpretador de mensagens

Resumo de uma sessão de trabalho com o Claude Code, para o relatório da semana e para quem for continuar. As decisões ficam nos ADRs [0006](../decisoes/0006-transcricao-de-fala.md) (voz) e [0007](../decisoes/0007-interpretador-e-contrato-de-busca.md) (interpretador e contrato da busca). Os números por frase ficam em [eval/resultados/](../../eval/resultados/).

## 1. O que foi feito

| Etapa | Resultado |
|---|---|
| **Rodadas de perguntas antes de decidir** | Três rodadas, com opções e viabilidade, sobre candidatos de fala, gravações, provedor do LLM, divisão entre LLM e código, roteamento, contrato, sigilo, intenções, horários, orçamento no grupo e tamanho do conjunto |
| **ADRs** | 0006 (transcrição) e 0007 (interpretador e contrato da busca, que o ADR 0005 tinha deixado em aberto) |
| **Código** | [src/voz/](../../src/voz/README.md): interface única com três provedores (faster-whisper, MLX, Groq). [src/interpretador/](../../src/interpretador/README.md): texto → intenções. [src/base/contrato.py](../../src/base/contrato.py): `buscar(ConsultaBusca) → ResultadoBusca` |
| **Conjunto de teste** | 50 frases com gabarito ([eval/interpretador/frases.jsonl](../../eval/interpretador/frases.jsonl)): 17 de disponibilidade, 14 de gastos, 4 de orçamento, 5 de pedido de rolê, 5 de busca, 2 de outra e 3 com várias intenções. Cada frase traz os termos críticos para a voz |
| **Gravações** | [Roteiro](../../eval/voz/roteiro.md) com consentimento. 22 gravações reais de uma pessoa, fora do git, e 50 frases em voz sintética (Windows e macOS) |
| **Testes** | 58 testes automatizados, sem LLM e sem rede |
| **Medições** | 15 rodadas de transcrição (Windows CPU, Mac M4 GPU e CPU, Groq) e 7 do interpretador |

## 2. Como funciona o interpretador

1. O código troca os nomes dos membros da sala por marcadores (`@m1`, `@m2`…).
2. O LLM preenche um JSON Schema estrito. Ele não recebe a data de hoje. Devolve fichas de dia ("sex", "semana_que_vem"), período ("tarde"), horas em `HH:MM` e, para valores em reais, **o trecho literal da mensagem** ("23 e 40", "120 conto").
3. O código valida a saída e faz o resto:
   - resolve as datas;
   - aplica a tabela de horários ("tarde" = 13h–18h);
   - converte os valores e confere se o trecho está na mensagem;
   - casa as RAs;
   - monta a consulta à base;
   - decide confirmação, pergunta e destino.
4. Orçamento dito no grupo é ignorado. "De tarde" sem dia vira a pergunta "de qual dia?".

O LLM usado é o `deepseek/deepseek-v4.1-flash-1017`, pela OpenRouter, só com provedores sem retenção nem coleta de dados e sem quantização fp4.

## 3. Resultados

### 3.1 Interpretador (meta do RNF-08: 90% das frases de disponibilidade e gastos)

| Entrada | RNF-08 | Limite inferior 95% | Intenção | Campos | p50 / p90 | Custo por frase |
|---|---|---|---|---|---|---|
| Texto, com raciocínio do modelo | 33/34 = 97,1% | 84,7% | 92,0% | 89,5% | 1,9 / 6,4 s | US$ 0,00017 |
| **Texto, sem raciocínio** | **33/34 = 97,1%** | 84,7% | **100%** | **98,1%** | **0,9 / 1,6 s** | **US$ 0,00009** |
| Voz sintética → Groq | 32/34 = 94,1% | 80,3% | 98,0% | 96,2% | 1,2 / 2,1 s | US$ 0,00008 |
| Voz real (22) → Groq | 13/13 | 75,3% | 100% | 98,0% | 1,2 / 1,9 s | US$ 0,00008 |
| Voz real → MLX `medium` (M4) | 13/13 | 75,3% | 100% | 98,0% | 1,2 / 1,8 s | — |
| Voz real → faster-whisper `small` (CPU do M4) | 12/13 | 64,0% | 95,5% | 88,0% | 1,2 / 2,0 s | — |

Perguntas certas: 3/3 em texto. Sigilo (orçamento no grupo e tentativa de injeção): 2/2 em todas as rodadas.

### 3.2 Transcrição (critério principal: erro nos termos críticos, meta de 5%)

**Gravações reais (22, uma voz):**

| Onde | Modelo | Termos críticos | WER | p90 |
|---|---|---|---|---|
| M4, GPU | MLX `whisper-medium` | **2,9%** | 7,3% | 0,88 s |
| **API** | **Groq `whisper-large-v3-turbo` (escolhido)** | 5,9% | 11,5% | **0,80 s** |
| M4, GPU | MLX `whisper-large-v3-turbo` | 5,9% | 12,0% | 0,98 s |
| M4, CPU | faster-whisper `large-v3-turbo` | 7,4% | 12,6% | 3,76 s |
| M4, GPU | MLX `whisper-medium`, sem prompt | 7,4% | 9,4% | 0,86 s |
| M4, GPU | MLX `whisper-small` | 11,8% | 16,2% | 0,30 s |
| Windows, CPU | faster-whisper `small` | 13,2% | 15,7% | 2,1 s |
| M4, CPU | faster-whisper `small` | 14,7% | 15,2% | 0,91 s |

**Voz sintética (50 frases):**

| Modelo | Termos críticos | WER | p90 |
|---|---|---|---|
| Groq `large-v3-turbo` | 3,6% | 3,8% | 0,96 s |
| MLX `large-v3-turbo` (M4) | 3,6% | 6,0% | 1,00 s |
| faster-whisper `large-v3-turbo` (Windows, CPU) | 3,6% | 4,1% | 17,5 s |
| faster-whisper `medium` (Windows, CPU) | 5,0% | 7,3% | 11,0 s |
| MLX `medium` (M4) | 6,5% | 7,9% | 0,86 s |
| faster-whisper `small` (Windows, CPU) | 7,2% | 5,1% | 5,5 s |
| faster-whisper `small` sem prompt (Windows, CPU) | 10,8% | 7,6% | 3,8 s |

**Custo do Groq:** US$ 0,04 por hora de áudio, com mínimo de 10 s por pedido. Saiu cerca de US$ 0,0001 por frase.

## 4. Achados

1. **"Sexta" vira "6", "6º" ou "cesta"** nos modelos pequenos. O WER conta isso como uma palavra, mas a ação muda de dia. Por isso o critério principal é o erro nos termos críticos, e a confirmação do RF-39 continua obrigatória.
2. **A voz real é bem mais difícil que a sintética.** O WER do Groq foi de 3,8% para 11,5%. A voz sintética serve para testar o pipeline, não para escolher modelo.
3. **Na CPU, o Whisper tem um piso de latência.** Ele sempre codifica uma janela de 30 s, então uma frase curta custa quase o mesmo que uma longa. Nenhum modelo bom cabe em 2,5 s sem GPU.
4. **Na GPU do Apple Silicon, um modelo local alcança a API**, com p90 abaixo de 1 s. Só que o MLX roda apenas em Mac.
5. **O prompt de vocabulário** (gírias, RAs, "Pix", "Uber") **reduz o erro nos termos críticos**: de 10,8% para 7,2% no `small` com voz sintética, e de 7,4% para 2,9% no `medium` com voz real.
6. **O raciocínio do modelo atrapalhou.** O DeepSeek V4.1 Flash raciocina antes de responder. Em 2 de 50 frases, gastou todos os tokens sem devolver o JSON, e o p90 foi a 6,4 s. Desligado, o acerto ficou igual e o p90 caiu para 1,6 s.
7. **A regra do trecho literal funcionou.** "23 e 40", "312 reais e 90 centavos", "cento e vinte" e "1.200" foram convertidos por código, e nenhum valor veio de texto gerado.
8. **O LLM é robusto a erros de transcrição:** entendeu "livre de todo" como "dia todo". Não resolve nomes errados ("Itaguatinga", "Aza Sul"), que não casam com as RAs.
9. **Problemas de infraestrutura resolvidos:**
   - o faster-whisper 1.2 é incompatível com o PyAV 19, e o áudio passou a ser decodificado pelo nosso código;
   - chamar o ffmpeg como processo custava mais de 1 s por frase no Windows, contra cerca de 15 ms com o PyAV no mesmo processo;
   - o plano gratuito do Groq recusa pedidos depois de uns 20 seguidos, e a transcrição agora tenta de novo respeitando o tempo pedido;
   - outra sessão usando a CPU inflou as latências do Windows: o `small` levou 2,5 s com a máquina livre e 4,2 s com ela ocupada.
10. **Cuidado metodológico:** uma regra do prompt (o teto de preço dentro de uma busca) nasceu de um erro deste mesmo conjunto, então a segunda rodada do interpretador o favorece. As gravações dos outros integrantes e o teste com usuários servem de conjunto novo.

## 5. Decisões tomadas

| Decisão | Onde |
|---|---|
| Transcrição pelo **Groq** (`whisper-large-v3-turbo`), com retenção zero; MLX `medium` como opção local no Mac; faster-whisper na CPU descartado; sem reserva local automática (se o Groq falhar, a pessoa repete ou digita) | ADR 0006 |
| Interpretador **híbrido**: o LLM preenche o esquema e o código resolve datas, valores, RAs e consulta | ADR 0007 |
| **DeepSeek V4.1 Flash pela OpenRouter**, sem raciocínio, só com provedores sem retenção e sem fp4 | ADR 0007 |
| **Contrato da busca** como função Python tipada, com SQL só por parâmetros | ADR 0007 |
| Nomes pseudonimizados antes do LLM; orçamento dito no grupo ignorado; "de tarde" sem dia vira pergunta | ADR 0007 |

## 6. Impactos no projeto

**Requisitos:**

- **RNF-08:** a meta de 90% é cumprida pelo acerto observado: 97% em texto e 94% a 100% pela voz. Ela ainda não é provada estatisticamente. Com 34 frases, nem 100% de acerto daria limite inferior acima de 90% (ficaria em 89,7%), e para isso o conjunto precisa de cerca de 60 frases de disponibilidade e gastos.
- **RNF-14 (5 s na conversa):** o caminho da voz fica em cerca de 1 s de transcrição mais cerca de 2 s de interpretação no p90. Sobra margem para a resposta.
- **RNF-04:** nenhum valor em reais nem data absoluta sai do LLM.
- **RNF-01:** o texto e o áudio passam por dois terceiros nos EUA (OpenRouter e Groq), ambos sem retenção, com os nomes pseudonimizados e o áudio apagado logo depois. O **aviso de privacidade** precisa dizer isso.
- **RNF-02 e RNF-11:** o orçamento dito no grupo não vira restrição, e a tentativa de injeção vira "outra" sem nenhuma ação. É o começo da bateria adversarial.
- **RNF-12:** a troca de provedor por configuração foi exercitada de fato: três provedores de fala e a troca de modelo do LLM pela linha de comando.
- **RNF-15 e P12:**
  - **custo:** cerca de US$ 0,0002 por mensagem de voz (transcrição e interpretação), ou cerca de US$ 0,20 a cada mil mensagens;
  - **falha:** sem reserva local, a resposta é pedir para repetir ou digitar.

**Arquitetura e roadmap:**

- **Hospedagem:** o servidor do MVP não precisa de GPU.
- **Dependências externas:** o MVP passa a depender de duas APIs, OpenRouter e Groq.
- **Agentes (semana 4):** partem do interpretador e do contrato da busca já testados. O agente do membro e o de finanças recebem intenções prontas, e o planejador chama `buscar(ConsultaBusca)`.
- **Entrada por voz:** é entrega da semana 5 e já existe como protótipo medido. Falta a interface no app.
- **ADR 0005:** a pendência do contrato da busca está fechada.

## 7. Pendências

- Gravar as outras 28 frases, de preferência com a voz de outros integrantes.
- Revisão do gabarito e dos ADRs 0006 e 0007 pelo grupo.
- Aumentar o conjunto para cerca de 60 frases de disponibilidade e gastos.
- Erros do interpretador ainda abertos:
  - B03: perde o "às 21h" numa busca;
  - M02: "eu posso a partir das 20h" sem herdar o dia do pedido;
  - casamento de RAs com grafia errada ("Itaguatinga", "Aza Sul").
- Aviso de privacidade com o Groq e a OpenRouter.
- Testar a busca de ponta a ponta com o Postgres ligado (Docker).
- Publicar o mapa da arquitetura (`publicar.sh`).
