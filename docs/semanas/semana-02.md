# Semana 2 — Base de conhecimento e recuperação

**Entregável:** Primeiro mecanismo RAG

## Registro

- 2026-11-03: mapa navegável da arquitetura planejada em `docs/arquitetura/index.html`, no formato pedido pelo mentor Isaque, publicado no GitHub Pages pelo repositório público `residencia-ia-g7-arquitetura`. Mostra o que está decidido, o que é proposta e o que falta decidir; nada foi implementado ainda.
- 2026-11-03: requisitos do repositório sincronizados com a v0.3 do documento da equipe (RF-46, coluna Riscos, testes do MVP sem piloto).
- 2026-11-03: ADR 0004 sobre a fonte da base (fontes, API de conferência, reverificação e tamanho). A versão 1 passou por crítica de outro agente, com o prompt em `docs/decisoes/revisoes/`; a versão 2 incorpora a crítica e cria o esquema e o guia de curadoria em `docs/dados/`.
- 2026-11-03: ADR 0005 (proposta): coleta 100% automática (robô nos sites oficiais, extração por LLM com evidência literal validada por código) e base vetorial em PostgreSQL com pgvector, busca híbrida e embeddings BGE-M3 locais. Substitui a curadoria humana do ADR 0004.

- 2026-11-03: mapa atualizado publicado no repositório público.
- 2026-11-03: pipeline da base implementado em `src/base/` (10 etapas do ADR 0005, Postgres com pgvector em Docker, BGE-M3 local, 12 testes). Extração por subagentes Claude Haiku 5.5. Piloto com 100 candidatos sorteados por região e categoria: 33 sites responderam e nenhum lugar foi aprovado ([relatório](../../data/base/relatorio.md)).
- 2026-11-03: varredura ampliada com reposição do sorteio. 811 sorteados, 234 sites responderam, 41 passaram na triagem em código e 10 foram aprovados (8 no Centro). A base está no Postgres com vetores BGE-M3 e e5. O OSM foi medido (horário em 12% de comer e beber, sem preço), e a comparação com os campos da Google Places foi registrada no ADR 0005.
- 2026-11-03: OCR local de cardápio (EasyOCR). Das 43 casas com imagem de cardápio, 17 renderam texto e 2 foram aprovadas a mais. O validador passou a normalizar erros de OCR e a recusar nome e preço com outro preço no meio, o que derrubou uma aprovação errada anterior. A base fechou o dia com 11 lugares.
- 2026-11-05: estudo do Tripadvisor como fonte de enriquecimento (termos do site, robots.txt e API Terra), registrado no ADR 0005. Ele fica fora da base e da hora do plano, e a única via é uma permissão acadêmica por escrito.
- 2026-11-05: entrada por voz e interpretador de mensagens, depois de três rodadas de perguntas (ADRs 0006 e 0007, propostas). Código em `src/voz/` e `src/interpretador/`, contrato da busca em `src/base/contrato.py` e 50 frases com gabarito em `eval/`. 57 testes passam sem LLM. Prévia de voz com voz sintética: o `large-v3-turbo` tem o menor erro nos termos críticos (3,6%), mas leva 16 s por frase na CPU; o `small` erra 7,2% e leva cerca de 4 s. Com as chaves no `.env`, o interpretador acertou 33 de 34 frases de disponibilidade e gastos em texto (97,1%, meta do RNF-08 de 90%) e 32 de 34 pela voz sintética via Groq. O Groq transcreveu com 3,6% de erro nos termos críticos e p90 de 1 s. Desligar o raciocínio do DeepSeek baixou o p90 do interpretador de 6,4 s para 1,6 s e acabou com as respostas sem JSON. Com 22 gravações reais de uma pessoa, o Groq errou 5,9% dos termos críticos e o `small` local 13,2%, e o interpretador acertou as 13 frases de disponibilidade e gastos a partir da transcrição do Groq. No MacBook M4, o MLX `medium` errou 2,9% dos termos críticos e o MLX `large-v3-turbo` 5,9%, ambos com p90 abaixo de 1 s: com GPU, um modelo local alcança a API. O Groq virou o padrão. Resumo completo em [docs/experimentos/2026-11-05-voz-e-interpretador.md](../experimentos/2026-11-05-voz-e-interpretador.md).

## Decisões da semana

- [ADR 0004](../decisoes/0004-fonte-e-manutencao-da-base.md): fonte e manutenção da base de lugares e eventos. Aceito na versão 2, depois da [crítica e respostas](../decisoes/revisoes/0004-critica.md): 21 achados aceitos e 3 aceitos em parte. Consequências nos requisitos v0.3.1 (RNF-15 e RF-37).
- [ADR 0005](../decisoes/0005-coleta-automatica-e-base-vetorial.md): coleta automática e base vetorial (proposta).
- [ADR 0006](../decisoes/0006-transcricao-de-fala.md): transcrição de fala com a família Whisper. Depois das medições, o Groq virou o padrão, com retenção zero, e o MLX `medium` ficou como opção local no Mac (proposta).
- [ADR 0007](../decisoes/0007-interpretador-e-contrato-de-busca.md): interpretador híbrido (o LLM preenche o esquema, o código resolve datas e valores), pela OpenRouter só com provedores sem retenção, e o contrato tipado da busca que o ADR 0005 deixou em aberto (proposta).

## Aprendizados e dúvidas

- O Whisper transcreveu "sexta" como "6." em frases de disponibilidade, mesmo com voz sintética limpa. O WER conta isso como uma palavra errada, mas a ação muda de dia. Por isso o critério principal do ADR 0006 é o erro nos termos críticos, e a confirmação do RF-39 continua obrigatória.
- Na CPU, o Whisper sempre codifica uma janela de 30 s: uma frase de 3 s custa quase o mesmo que uma de 25 s. A latência de uma frase curta tem um piso que depende do modelo e da máquina, e não do tamanho da fala.
- Modelos que raciocinam antes de responder podem estourar o limite de tokens sem entregar o JSON. Para preencher um esquema fechado, o raciocínio não melhorou o acerto e quadruplicou a latência de cauda.
- Subir o ffmpeg como processo custava mais de 1 s por frase no Windows; decodificar com o PyAV no mesmo processo leva cerca de 15 ms, com a mesma saída.

- Os termos da Google Maps Platform restringem muito mais do que a cota sugere. Não se pode guardar o conteúdo (só o place ID), usar a Places API com mapa não Google, ler o conteúdo em voz alta nem usá-lo para testar modelos de IA. Por isso a Google ficou só como conferência na hora do plano.
- A crítica por outro agente, guiada por um prompt com o que procurar, achou três problemas bloqueantes que a primeira versão do ADR não via. Vale repetir nos próximos ADRs.
- O campo de site da Overture envelhece mal no DF: metade dos domínios não existe mais, e muitos levam a agregadores ou a outro negócio. E os restaurantes que têm site publicam o cardápio como imagem. O piloto mostrou isso antes de a base inteira ser montada sobre essa premissa.
- Os termos de plataformas de avaliação já citam IA nominalmente. Os do Tripadvisor vedam o acesso por "sistema de inteligência artificial", e a API dele não licencia nenhum uso com IA fora de teste interno. Coleta por computer use em plataformas assim não é uma brecha.
- A evidência literal funcionou como trava: o Haiku não inventou nenhum trecho, e o validador barrou o único valor que não estava no trecho citado.

## Pendências para a próxima semana

- Escolha do grupo entre as opções A a D do piloto (ADR 0005); depois, nova rodada.
- 20 a 30 pedidos de teste escritos antes da base; comparação BGE-M3 × e5 com eles.
- Respostas do grupo às perguntas dos ADRs 0004 e 0005.
