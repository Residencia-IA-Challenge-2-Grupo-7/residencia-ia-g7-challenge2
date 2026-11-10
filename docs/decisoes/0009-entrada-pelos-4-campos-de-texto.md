# 0009 — Entrada pelos 4 campos de texto, interpretados por regras (sem voz)

- **Status:** o escopo (4 campos de texto, sem voz) é **aceito**, decidido pelo grupo no [guia oficial](../../GUIA_OFICIAL_PROJETO.md) de 10/11. A forma de interpretar (regras primeiro, LLM só de reserva) é **proposta** deste ADR
- **Data:** 2026-11-10
- **Semana do roadmap:** 3 (o app real das Telas 1 a 3); multimodal na semana 5 passa a ser a foto da nota fiscal
- **Substitui:** o [ADR 0006](0006-transcricao-de-fala.md) (voz com Whisper/Groq), cujo código (`src/voz/`) saiu do repositório. Do [ADR 0007](0007-interpretador-e-contrato-de-busca.md), continua valendo o interpretador de mensagens livres e o contrato da busca; a conversa privada por chat (RF-07, RF-08) dá lugar aos 4 campos
- **Requisitos:** RF-01, RF-08, RF-11, RF-44 · RNF-01, RNF-02, RNF-04, RNF-08 · removidos: RF-39, RF-40

## Contexto

O grupo trocou a conversa com a IA, por texto ou voz, por **4 campos de texto secretos** na Tela 2:

1. De onde você vai sair no DF?
2. Quais dias e horários você pode?
3. Qual seu limite máximo de gasto em R$?
4. O que você anima fazer e como vai?

O interpretador do ADR 0007 já resolve datas, valores e RAs por código, mas manda toda mensagem para um LLM externo (DeepSeek pela OpenRouter) para classificar a intenção. Com os campos separados, a intenção já é conhecida: cada campo só tem um tipo de informação.

## Opções consideradas

1. **Mandar os 4 campos ao LLM do ADR 0007:** reaproveita o que existe e entende frases soltas, mas envia localização e orçamento para fora do servidor, custa uma chamada por pessoa e falha sem chave ou sem rede.
2. **Regras primeiro, LLM só de reserva no campo 2 (escolhida):** campo 1 por apelidos de RA, siglas de quadra (SQN, QNM, SHIS…) e estações de metrô; campo 2 por regras sobre o vocabulário de dias e períodos e pelo `tempo.py`; campo 3 pelo `numeros.py`; campo 4 por um dicionário com os rótulos da base. O LLM só é chamado quando as regras não acham nenhum dia no campo 2 e há um cliente configurado.
3. **Formulário com caixinhas (RA, dias, horários):** o mais preciso, mas o grupo descartou: o DF é falado por RA, quadra e ponto de referência, e muitas caixinhas cansam no celular.

## Decisão

Opção 2, em `src/interpretador/campos.py` (`interpretar_campos`). O resultado vira um resumo que só o dono vê ("sáb 14/11, 18h–23h; saindo de Águas Claras; teto de R$ 60,00 (só você vê)…") e uma lista de pendências por campo. A pessoa só consegue confirmar em segredo quando não há pendência.

## Justificativa e evidências

- **Privacidade (RNF-01, RNF-02):** localização e dinheiro nunca saem do servidor. O campo de horários é o único que pode ir ao LLM, e só no caso de reserva.
- **RNF-04:** nenhum valor, data ou RA vem de texto gerado.
- **Custo e resiliência (RNF-15):** sem chamada externa no caminho comum, a Tela 2 responde na hora e funciona sem chave de API (no Render, por exemplo).
- **Testes:** 34 casos em `tests/test_campos.py`, entre eles os exemplos do guia ("Águas Claras perto da estação", "Asa Norte 408", "sexta depois das 19h ou sábado à tarde", "60", "Barzinho ou café calmo, sou vegetariana, vou de metrô/Uber").

## Riscos e limitações

- **Cobertura das regras:** frases fora do vocabulário ("no dia do aniversário do Caio", "depois do trabalho") viram pergunta ou vão ao LLM. Termos de lugar que não estão na lista viram "Não reconheci essa região". A lista de apelidos fica em `config.toml` e cresce com o uso.
- **Ambiguidades conhecidas:** "das 7 às 11 da noite" vira 7h–23h; "depois das 7" sem "manhã" vira 19h. Horas de 1 a 6 sem "manhã" são lidas como tarde ou noite. A confirmação pela própria pessoa é a proteção.
- **Campo 4 por dicionário:** pega os termos mais comuns, não sinônimos raros nem negações ("não quero bar"). O texto inteiro também vai para a busca da Letícia como texto livre.
- **Sem voz:** pessoas com pouca fluência para digitar perdem uma forma de entrada (RNF-07). O teclado de voz do próprio celular continua disponível.

## Como vamos validar

- Acerto por campo num conjunto de frases reais dos testes com usuários (meta inicial: 90% sem pergunta nos campos 1 e 2 e 100% no campo 3).
- Taxa de chamadas ao LLM de reserva (meta: menos de 10% dos participantes).
- Nenhum teto nem origem nas respostas públicas da API (`tests/test_salas.py`).
