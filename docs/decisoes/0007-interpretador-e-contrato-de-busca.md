# 0007 — Interpretador de mensagens e contrato da busca usada pelos agentes

- **Status:** proposta
- **Data:** 2026-11-05
- **Semana do roadmap:** 2 (preparação). Os agentes são entrega da semana 4 (RNF-12)
- **Requisitos:** RF-05, RF-07, RF-08, RF-11, RF-18, RF-30, RF-39 · RNF-01, RNF-02, RNF-04, RNF-08, RNF-11, RNF-12, RNF-14
- **Completa o [ADR 0005](0005-coleta-automatica-e-base-vetorial.md):** define o contrato da busca que ele deixou "para outro ADR". Não muda nada da Parte B (filtros duros em SQL, busca híbrida por RRF, 20 candidatos, BGE-M3)
- **Relacionado:** [ADR 0006](0006-transcricao-de-fala.md), que entrega o texto transcrito

## Contexto

Toda mensagem do chat, digitada ou transcrita, precisa virar algo que o sistema saiba executar: abrir um rolê, registrar janelas de disponibilidade, guardar um teto de gasto, lançar um gasto ou buscar lugares. As mensagens chegam em português coloquial ("partiu barzinho sexta?", "tô liso, no máximo 30 conto", "paguei 23 e 40 do Uber").

Regras que não mudam, definidas no pedido de 05/11:

- **O LLM não escreve SQL.** Ele preenche um esquema validado por código, e o código monta a consulta (RNF-04, RNF-11).
- **Orçamento e conversa privada não saem do agente do membro com identificação** (RNF-02).
- **Ambiguidade vira pergunta de confirmação, com valor explícito:** "de tarde" vira 13h–18h (RF-08).
- **Provedores trocáveis por configuração** (RNF-12) e resposta em até 5 s no p90 (RNF-14).

## Opções consideradas

### Divisão entre LLM e código

| Opção | Prós | Contras |
|---|---|---|
| **A. Híbrido:** o LLM classifica e preenche campos normalizados; o código resolve datas, converte valores e valida | Datas relativas e valores ficam deterministas e testáveis sem LLM (RNF-04); o LLM faz o que faz bem, que é entender gíria | Dois lugares para manter (prompt e resolvedor) |
| B. Só LLM: ele já devolve datas absolutas e valores numéricos | Simples | Erra datas relativas ("sexta" dita numa quinta, "semana que vem"); fere o RNF-04 ("nenhum valor em reais vem de texto gerado pelo modelo") |
| C. Regras primeiro, LLM de reserva | Rápido e barato nas frases comuns | Frágil com gíria e frases compostas; muito código de regra |

**Escolha: A** (05/11).

### Provedor do LLM

O grupo já tem créditos na OpenRouter. O modelo pedido é o `deepseek/deepseek-v4.1-flash-1017`, a US$ 0,15 por milhão de tokens de entrada e US$ 0,60 de saída, com saída estruturada (catálogo público consultado em 05/11). Cerca de 50 provedores o servem, com quantizações de fp4 a fp8 e políticas de dados diferentes. O endpoint da própria DeepSeek não tem saída estruturada.

**Escolha:** OpenRouter, com o roteamento restrito na configuração:

- `zdr: true` e `data_collection: "deny"`: só provedores sem retenção nem treino com os dados (RNF-01);
- `quantizations: fp8, fp16, bf16, fp32`: sem fp4 nem quantização desconhecida, porque a qualidade com gíria cai e a medição deixa de ser reproduzível;
- `require_parameters: true`: só provedores que aceitam o esquema JSON estrito;
- `sort: "latency"` (RNF-14);
- `reasoning: {enabled: false}`: sem raciocínio antes da resposta. Medido em 05/11: com raciocínio, o p90 foi 6,4 s e houve respostas sem JSON (ver Resultados).

O modelo não é fixo. Se nenhum provedor do DeepSeek passar nesses filtros ou na meta de latência, entra outro modelo da OpenRouter, pela lista `reservas` da configuração.

### Forma do contrato da busca

| Opção | Prós | Contras |
|---|---|---|
| **A. Função Python tipada** (Pydantic): `buscar(ConsultaBusca) → ResultadoBusca` | Nasce testável; o mesmo esquema vira a definição da ferramenta para o LLM; uma API HTTP pode envolvê-la depois sem mudar o contrato | Só serve a quem roda no mesmo processo até existir o backend |
| B. API HTTP (FastAPI) já | Adianta o backend | Cria serviço, autenticação e implantação antes de o canal (ADR 0003) e o backend serem decididos |
| C. Servidor MCP | Ferramenta pronta para agentes | Amarra a um framework de agentes que ainda está "a decidir" |

**Escolha: A** (05/11).

## Decisão

### 1. Intenções

Uma mensagem pode ter **várias intenções** ("sexta depois das 19h e no máximo 50 conto" tem duas). São seis:

| Intenção | Exemplo | Campos |
|---|---|---|
| `pedido_role` | "bora sair semana que vem?" | dias, tipo de rolê, convidados (vazio = sala toda), texto de busca |
| `disponibilidade` | "sexta depois das 19h ou sábado o dia todo" | janelas (dias, período, depois de, até, disponível ou não) |
| `orcamento` | "consigo gastar uns 80 no máximo" | valor (trecho literal) |
| `gasto` | "o Caio pagou 90 do Uber" | valor (trecho literal), quem pagou, descrição |
| `busca_lugar` | "tem bar tranquilo em Taguatinga até 50 por pessoa?" | tipo de rolê, lugares citados, teto (trecho literal), atributos exigidos, dias e horário, texto de busca |
| `outra` | "kkkkk", "valeu, gente" | nenhum |

A confirmação ("isso", "não, até as 22h") não é uma intenção. O app mostra os botões **Confirmar** e **Corrigir**, e a correção é uma mensagem nova, interpretada de novo.

### 2. O que o LLM devolve e o que o código faz

O LLM devolve um JSON num esquema estrito (`src/interpretador/esquema.py`). Daí em diante, só código:

| Campo | O LLM devolve | O código faz |
|---|---|---|
| Dias | Fichas de um vocabulário fechado: `seg` a `dom`, `hoje`, `amanha`, `depois_de_amanha`, `fim_de_semana`, `esta_semana`, `semana_que_vem`, `dd` ou `dd/mm`, e o sinal `proxima_semana` ("sábado da semana que vem") | Resolve para datas a partir da data e hora da mensagem, no fuso America/Sao_Paulo. Dia da semana = próxima ocorrência, contando hoje |
| Horário | `periodo` (`manha`, `tarde`, `noite`, `dia_todo`), `apos` e `ate` em `HH:MM` | Aplica a tabela de convenções e valida os limites |
| Valores em reais | O **trecho literal** da mensagem ("47,50", "120 conto", "cento e vinte", "23 e 40") | Confere se o trecho está na mensagem e converte para número. Valor sem trecho, ou trecho que não está na mensagem, é descartado (mesma trava da evidência literal do ADR 0005) |
| Pessoas | Marcadores `@m1`, `@m2`… ou `eu` | Desfaz a pseudonimização |
| Lugares | Os nomes como foram ditos ("Asa Sul", "lá pros lados de Ceilândia") | Casa com as 35 RAs e as 6 regiões de `data/base/regioes.csv`, com apelidos ("Asa Sul" vira Plano Piloto, "Taguá" vira Taguatinga). O que não casa vai para o texto de busca |
| Atributos exigidos | Enumeração fechada do esquema da base (`alim_vegano`, `acess_entrada_sem_degrau`…) | Repassa como filtro duro |

**Tabela de convenções** (em `src/interpretador/config.toml`, mostrada na confirmação):

| Expressão | Intervalo |
|---|---|
| manhã | 08h–12h |
| tarde | 13h–18h (RF-08) |
| noite | 19h–24h |
| dia todo, qualquer hora | 08h–24h |
| depois das X, a partir das X | X–24h |
| até as X, sem período | 08h–X |
| fim de semana | sábado e domingo seguintes |
| semana que vem | segunda a domingo da próxima semana |

**Pergunta quando faltar o dia.** "De tarde", sem dia, vira a pergunta "De qual dia você está falando?", em vez de valer para todos os dias do rolê (escolha de 05/11). Também viram pergunta, com texto montado por código:

- um gasto sem valor;
- um valor que não se consegue converter;
- uma hora inválida;
- um "depois das 22h até as 20h".

### 3. Confirmação

- `disponibilidade`, `orcamento` e `gasto` **sempre** saem com `requer_confirmacao` e com a frase de confirmação montada por código: "sex 06/11, 19h–24h; sáb 07/11, 8h–24h. Está certo?" (RF-08, RF-11, RF-30).
- Gasto lançado por outra pessoa pede a confirmação de quem pagou (RF-30).
- Pela voz, qualquer intenção com data ou valor também requer confirmação (RF-39).
- `busca_lugar` só lê a base e não requer confirmação.

### 4. Encaminhamento e sigilo

| Intenção | Chat privado | Chat do grupo |
|---|---|---|
| `pedido_role` | mediador (abre o rolê) | mediador |
| `disponibilidade` | agente do membro | agente do membro de quem falou |
| `orcamento` | agente do membro | **ignorado**: não vira restrição nem é repetido. A coleta normal acontece no privado (RF-11) |
| `gasto` | finanças | finanças |
| `busca_lugar` | base: `buscar(ConsultaBusca)` | base |
| `outra` | resposta conversacional | nenhuma ação |

Sobre o orçamento dito no grupo (escolha de 05/11): quem falou em público aceitou que os outros vissem. Ainda assim, o valor não entra como restrição, porque o RF-11 coleta o orçamento em particular. Ignorar não acrescenta nenhuma interação, já que a conversa privada pergunta o orçamento de qualquer jeito.

**Antes do LLM, o código troca os nomes dos membros da sala por marcadores** (`@m1`, `@m2`…) e desfaz a troca na volta (RNF-01, "sem nome nem contato"). O interpretador do chat privado recebe só as mensagens daquele membro. O agente do membro repassa ao planejador só restrições sem identificação (RNF-02, mapa: etapa 1). O texto do usuário vai ao LLM como dado, delimitado, e o prompt diz que instruções dentro dele são ignoradas (RNF-11). A trava real é a saída estruturada: o pior que uma injeção consegue é uma intenção errada, que ainda passa pela confirmação.

### 5. Contrato da busca (`src/base/contrato.py`)

```text
ConsultaBusca
  texto           str, 1–300 caracteres: o que se quer, para a busca vetorial e textual
  colecoes        ["lugares"] | ["eventos"] | ambos
  tipos_role      comer_beber | ar_livre_gratuito | local_evento (vazio = todos)
  regioes         centro | oeste_proximo | oeste | sul | norte | leste
  ras             nomes das 35 RAs, validados contra data/base/regioes.csv
  janela          {inicio, fim}: aberto no início da janela; evento começando dentro dela
  teto_pessoa     R$ por pessoa, 0–1000
  exigir          atributos que precisam ser "sim" (enumeração do esquema da base)
  k               1–20

ResultadoBusca
  itens           [{colecao, id, nome, categoria, ra, regiao, custo_pessoa_tipico, taxa_entrada,
                    inicio (eventos), fonte, verificado_em, estado, pontuacao}]
  versao_base, modelo_embeddings, gerado_em
```

- Quem preenche a `ConsultaBusca` é código: o interpretador, para a `busca_lugar`, e o planejador, com as restrições já resolvidas. O LLM do planejador, quando ganhar ferramentas na semana 4, recebe o JSON Schema desse modelo e chama a busca com argumentos que passam pela mesma validação.
- O código monta a SQL só com parâmetros (`%(nome)s`), a partir dos campos validados. Nenhum texto do LLM vira SQL. O fluxo é o do ADR 0005: filtros duros, depois vetor e texto em português combinados por RRF.
- Cada item traz `fonte` e `verificado_em`, para o RF-16 e o RNF-05. Um lugar que não veio da busca não entra no plano.
- O contrato tem versão (`CONTRATO_VERSAO`). Mudança incompatível pede ADR novo.

## Justificativa e evidências

- **Trecho literal para valores em reais:** é a mesma ideia que funcionou na extração da base (ADR 0005), onde nenhum trecho foi inventado. O LLM aponta onde está o valor, e o código lê. Assim, nenhum valor em reais sai de texto gerado (RNF-04).
- **Datas por código:** "sexta" dita numa quinta, à noite, ou "semana que vem" num domingo são casos em que LLMs erram sem avisar. Uma função de 100 linhas com testes acerta sempre e mostra a convenção na confirmação.
- **Pseudonimização antes do LLM:** é barata e reduz o dado pessoal enviado ao provedor ao mínimo necessário (RNF-01).
- **Roteamento restrito na OpenRouter:** a configuração de provedor da OpenRouter permite exigir retenção zero, recusar coleta de dados, filtrar quantizações e exigir os parâmetros enviados ([documentação](https://openrouter.ai/docs/guides/routing/provider-selection), consultada em 05/11/2026).

## Riscos e limitações

| Risco | Ligação | Mitigação |
|---|---|---|
| O LLM classifica errado ou esquece um campo | R-09, RNF-08 | Confirmação obrigatória nas intenções que gravam dado; medição com o conjunto de 50 frases; cada erro vira exemplo no prompt ou regra |
| Provedor da OpenRouter lento ou fora do ar | RNF-14, RNF-15 | `sort: latency`, `timeout`, lista de modelos de reserva; o estado do rolê não depende do interpretador. Falhou, a IA pede para repetir |
| Texto da conversa privada sai para o provedor | RNF-01, RNF-02 | Pseudonimização; retenção zero exigida no roteamento; só a mensagem atual e o contexto mínimo vão ao LLM |
| Injeção de instrução pelo chat | RNF-11 | Saída estruturada; nenhuma ação sem confirmação; nenhuma consulta livre ao banco; a frase de injeção faz parte do conjunto de teste |
| Convenção não bate com a intenção da pessoa ("noite" para alguém que sai às 22h) | RF-08 | A convenção aparece na confirmação, e a pessoa corrige |
| "Sábado que vem" é ambíguo em pt-BR | RNF-08 | Sem `proxima_semana`, vale o próximo sábado; a confirmação mostra a data. Medir se o erro aparece |
| Conjunto de 50 frases é pequeno | — | Acerto reportado com intervalo de Clopper-Pearson; o teste com usuários (RNF-10) mede de novo |
| Horário de funcionamento: a busca filtra "aberto no início da janela", não a janela inteira | RF-17 | Limitação declarada; o planejador confere a duração na etapa 5 |

## Como vamos validar

**Conjunto:** [eval/interpretador/frases.jsonl](../../eval/interpretador/frases.jsonl), 50 frases com a saída esperada (intenções e campos já resolvidos), escritas em 05/11 para a data de referência qui 05/11/2026 10h, e a revisar pelo grupo.

| Métrica | Como medir | Meta |
|---|---|---|
| **RNF-08** | Frases com disponibilidade ou gasto em que todas as intenções e todos os campos batem com o gabarito | ≥ 90%. Com cerca de 34 frases, reportar o acerto observado e o limite inferior de Clopper-Pearson a 95% |
| Acerto da intenção | Conjunto de tipos previsto = conjunto esperado | ≥ 95% |
| Acerto dos campos | Por campo comparado (janelas, valor, pagador, RAs, teto…) | ≥ 90% |
| Perguntas certas | Frases do gabarito que devem virar pergunta e viraram | 100% |
| Sigilo | Orçamento dito no grupo não vira restrição; injeção vira `outra` | 100% |
| Latência | Tempo de `interpretar()` por frase, p50 e p90 | p90 ≤ 2,5 s (a outra metade dos 5 s é da transcrição) |
| Custo | Tokens × preço do modelo, por frase | Registrado |

Como rodar: `python -m interpretador avaliar` ([src/interpretador/README.md](../../src/interpretador/README.md)). Os resultados vão para `eval/resultados/`.

## Resultados

**Condições das medições (05/11):**

- `deepseek/deepseek-v4.1-flash-1017` pela OpenRouter, com o roteamento restrito da configuração;
- data de referência qui 05/11/2026 10h;
- detalhes por frase em [eval/resultados/](../../eval/resultados/);
- os 58 testes sem LLM cobrem o resolvedor, a conversão de valores, a pseudonimização, o encaminhamento e a montagem da SQL.

| Métrica | Texto, com raciocínio | **Texto, sem raciocínio** | Voz sintética → Groq → interpretador | Meta |
|---|---|---|---|---|
| RNF-08 (disponibilidade e gastos) | 33/34 = 97,1% | **33/34 = 97,1%** | 32/34 = 94,1% | ≥ 90% |
| Limite inferior de Clopper-Pearson a 95% | 84,7% | 84,7% | 80,3% | — |
| Intenção certa | 92,0% | **100%** | 98,0% | ≥ 95% |
| Campos certos | 89,5% | **98,1%** | 96,2% | ≥ 90% |
| Frases inteiramente certas | 92,0% | **96,0%** | 92,0% | — |
| Perguntas certas | 3/3 | **3/3** | 2/3 | 100% |
| Sigilo (O04, X02) | 2/2 | **2/2** | 2/2 | 100% |
| Latência p50 / p90 | 1,9 / 6,4 s | **0,9 / 1,6 s** | 1,2 / 2,1 s | p90 ≤ 2,5 s |
| Respostas sem JSON | 2 | **0** | 0 | — |
| Custo por frase | US$ 0,00017 | **US$ 0,00009** | US$ 0,00008 | — |

**O que mudou entre a primeira e a segunda rodada:**

1. **Raciocínio desligado** (`raciocinio = false` na configuração). O DeepSeek V4.1 Flash raciocina antes de responder: em 2 frases gastou os 900 tokens raciocinando e não devolveu o JSON. Sem raciocínio, as falhas sumiram e o p90 caiu de 6,4 s para 1,6 s, sem perder acerto.
2. **Disponibilidades da mesma mensagem juntadas por código.** O modelo separou "sábado não posso, domingo tô livre" em duas intenções, o que geraria duas confirmações.
3. **Regra no prompt:** o preço máximo dentro de uma busca ("até 50 por pessoa") é o teto da busca, não um orçamento. Atenção: essa regra nasceu de um erro deste mesmo conjunto, então a segunda rodada favorece o prompt. As gravações e o teste com usuários servem de conjunto novo.

**Erros que sobraram, em texto:**

- **B03:** perdeu o "às 21h" e buscou o sábado inteiro.
- **M02:** deixou sem dia o "eu posso a partir das 20h", dito logo depois de "bora no sábado". O código perguntou "de qual dia?", que é o comportamento seguro. Ainda assim, conta como erro.

**Erros que a voz acrescentou:**

- **"Aza Sul":** com a grafia errada da transcrição, o lugar não casou com nenhuma RA.
- **"Só de noite?":** a interrogação acrescentada pela transcrição fez a frase virar conversa, em vez da pergunta "de qual dia?".

**Voz real (05/11):** com 22 gravações de uma pessoa, transcritas pelo Groq, o interpretador acertou 13 de 13 frases de disponibilidade e gastos e 21 de 22 no total, com p90 de 1,9 s. O único erro foi a RA de "Itaguatinga", que veio da transcrição (detalhes no [ADR 0006](0006-transcricao-de-fala.md#gravações-da-equipe-0511-primeira-parte)).

**Leitura:**

- A meta de 90% do RNF-08 é cumprida pelo acerto observado, tanto em texto quanto pela voz.
- Com 34 frases, nem 34 de 34 provariam 90% pelo limite inferior (ficaria em 89,7%). Para isso, o conjunto precisa crescer para cerca de 60 frases de disponibilidade e gastos.
- A latência cabe no orçamento do RNF-14: no pior caso, 1 s da transcrição pelo Groq mais 2,1 s da interpretação, abaixo dos 5 s.

## Mudanças em outros documentos

- ADR 0005: o contrato da busca fica neste ADR.
- `src/base/buscar.py` passa a usar o contrato.
- Mapa da arquitetura: cards do agente do membro, do multimodal, das etapas 1 a 3 e da base.

## Histórico

- 2026-11-05: proposta, depois de três rodadas de perguntas com o Cauan (divisão LLM e código, provedor, contrato, sigilo, intenções, horários, orçamento no grupo, conjunto de teste).
- 2026-11-05: primeiras medições. Raciocínio do modelo desligado, junção das disponibilidades por código e regra do teto da busca no prompt.
