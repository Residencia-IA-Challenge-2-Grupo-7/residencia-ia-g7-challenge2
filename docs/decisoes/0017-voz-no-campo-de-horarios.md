# 0017 — Voz no campo de horários, com o Whisper pela OpenRouter

- **Status:** proposta, falta o acordo do grupo. O [guia oficial](../../GUIA_OFICIAL_PROJETO.md) ainda diz "sem voz" e só muda depois desse acordo
- **Data:** 2026-11-24
- **Semana do roadmap:** 5 — Agentes multimodais
- **Substitui, se aceita:** do [ADR 0009](0009-entrada-pelos-4-campos-de-texto.md), só a parte "sem voz". Os 4 campos e a leitura por regras continuam. Do [ADR 0006](0006-transcricao-de-fala.md), retoma o modelo e as medições; muda o caminho (OpenRouter no lugar da chave da Groq) e o alcance (um campo, e não toda conversa)
- **Requisitos:** RF-47 (novo), RF-02, RF-08 · RNF-01, RNF-02, RNF-04, RNF-07, RNF-10, RNF-11, RNF-12, RNF-14, RNF-15

## Contexto

A semana 5 pede um assistente que processe pelo menos duas modalidades. O plano do guia era a foto da nota fiscal, mas nada dela existe ainda, e o trabalho da semana ficou com uma pessoa, porque as demais cuidam do design e da usabilidade. A transcrição de fala já tinha sido implementada e medida em 05/11 e saiu do repositório em 10/11.

O ADR 0009 tirou a voz por escopo, não por resultado ruim. Ele também registrou a perda: quem tem pouca fluência para digitar ficou sem uma forma de entrada (RNF-07).

## Opções consideradas

1. **Foto da nota fiscal com texto:** é o previsto no guia e tem mais integração, mas exige envio de imagem, modelo de visão, conferência, confirmação e a Tela 4 (18 a 24 h). Nenhuma medição existe.
2. **Voz em toda a Tela 2:** origem, teto e preferências iriam em áudio a terceiros. Isso contraria os ADRs 0008 e 0009: localização e dinheiro não saem do servidor, e as preferências podem trazer dado de saúde.
3. **Voz só no campo de horários (escolhida):** é o campo mais longo de digitar, o único que já podia ir a um modelo externo (ADR 0009) e o que mais depende de como se fala.
4. **Reconhecimento do navegador (`SpeechRecognition`):** sem servidor, mas o áudio vai ao fabricante do navegador sem controle de retenção, e o comportamento varia entre aparelhos. Já descartado no ADR 0006.

Para o provedor:

| Opção | Resultado em 24/11 | Decisão |
|---|---|---|
| Whisper `large-v3-turbo` da Groq **pela OpenRouter** | 10 pedidos entre 0,73 e 1,01 s; US$ 0,00011 cada; `zdr` por pedido, com a chave do projeto | **Principal** |
| O mesmo modelo na DeepInfra, pela OpenRouter | Mesma transcrição; 2,5 s em 1 pedido; cerca de um quinto do preço | **Reserva** |
| Groq com chave própria | Funciona, mas a retenção zero é uma opção da conta, não do pedido | Descartada |
| Modelo local | Na CPU, erra demais ou passa de 3 s (ADR 0006) | Descartado |

## Decisão

1. Microfone **só no campo 2** da Tela 2. O texto transcrito vai para o campo, editável, e segue o caminho de quem digitou: interpretação por regras, resumo e "Confirmar em Segredo". Nada é enviado sozinho.
2. Whisper `large-v3-turbo` pela OpenRouter, com `zdr: true` e `data_collection: deny` em todo pedido. Ordem: Groq, depois DeepInfra. Tudo em `src/voz/config.toml` (RNF-12).
3. O áudio existe **só na memória** do servidor durante o pedido. Não vai para disco, banco, log nem Langfuse. O texto volta só a quem falou e não é guardado pela rota.
4. Consentimento separado (RF-02): o app explica antes da primeira gravação, e o servidor recusa pedido sem o cabeçalho de consentimento.
5. Limites: 30 s no app, 1 MB, formato conferido pela assinatura do arquivo, cota por sala, teto diário e limite de pedidos ao mesmo tempo.
6. A trava do interpretador vale para texto e voz: hora não entendida vira pergunta ([experimento](../experimentos/2026-11-24-horarios-fala.md)).

## Justificativa e evidências

- **Duas modalidades com a mesma regra:** áudio e texto chegam ao mesmo interpretador, e o RNF-04 se mantém. O Whisper só devolve texto; as janelas saem do código.
- **Formatos:** webm/opus (Android e Chrome), mp4/aac (iPhone), m4a, ogg e wav foram aceitos sem conversão no servidor, com áudio sintético.
- **ZDR conferido:** um modelo sem provedor ZDR é recusado com HTTP 404.
- **O gargalo era a leitura, não a transcrição:** com as regras antigas, 4 de 6 frases reais certas e 2 erros silenciosos; com as novas, 6 de 6. São as mesmas frases usadas na correção, então falta o conjunto cego.
- **Voz real (05/11, uma pessoa, 22 frases):** 5,9% de erro nos termos críticos, acima da meta de 5%; p90 de 0,8 s.

## Riscos e limitações

| Risco | Mitigação |
|---|---|
| Silêncio vira "E aí" (medido) | O app mede o volume e não envia gravação muda; o servidor recusa resposta vazia; "E aí" não tem dia, e o campo pergunta |
| Voz é dado pessoal e sai do país | ZDR por pedido, só memória, aviso antes de gravar e alternativa por texto em tudo. A OpenRouter anunciou triagem de segurança que pode alcançar tráfego ZDR |
| A pessoa diz endereço ou valor no microfone | Aviso ao lado do botão. Não há filtro: o áudio já foi ouvido pelo provedor |
| A rota não exige token, porque a pessoa ainda não entrou na sala | Sala válida, cotas e teto diário. As cotas ficam em memória: zeram no reinício e não valem entre processos |
| Transcrição errada com aparência de certa | Texto editável, resumo e confirmação; trava do interpretador |
| Sotaque, ruído e poucas vozes medidas | Conjunto de teste aberto a novas gravações; resultado com intervalo de confiança |
| Falar em voz alta expõe a agenda a quem está perto | O botão é opcional; o campo aceita texto |
| Instrução falada ("ignore as instruções…") | O texto é dado: o campo 2 só reconhece dias e horas |

## Como vamos validar

Critérios fixados antes de medir. A medição com áudios fica na branch `feat/semana5-voz` até o acordo do grupo.

| Métrica | Meta |
|---|---|
| Erro nos termos críticos, voz real | ≤ 5% |
| Janelas certas no conjunto cego | ≥ 90% |
| Erro silencioso no conjunto cego | 0; qualquer um é relatado |
| Silêncio e ruído que viram janela | 0 |
| p90 da transcrição | ≤ 3 s |
| Custo por áudio | ≤ US$ 0,001 |
| Áudio ou texto em disco, log ou trace | 0 (teste automático) |
