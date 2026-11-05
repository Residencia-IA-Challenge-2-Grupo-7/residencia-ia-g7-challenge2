# Status do projeto

> Arquivo vivo. Toda sessão (humana ou de agente) lê no início e atualiza no fim.
> Mantenha curto: o histórico fica em `docs/semanas/` e no `git log`.

**Atualizado em:** 2026-11-05
**Semana do roadmap:** 2 — Base de conhecimento e recuperação (datas a confirmar)

## Agora

- **Ideia escolhida: Orquestrador de Rolês**, com o Modo Descoberta ([ADR 0001](docs/decisoes/0001-escolha-do-orquestrador-de-roles.md)). Visão, diferenciais, concorrentes, decisões em aberto e riscos: [docs/produto/visao.md](docs/produto/visao.md).
- **Recorte do MVP: só o modo com amigos.** Modo Descoberta, videogames e versão para menores ficam para depois ([ADR 0002](docs/decisoes/0002-recorte-do-mvp.md)). Canal proposto: app web próprio ([ADR 0003](docs/decisoes/0003-canal-app-web.md), a confirmar com o grupo).
- **Requisitos v0.3** em [docs/produto/requisitos.md](docs/produto/requisitos.md): 46 RF e 16 RNF, com cenários no estilo OpenSpec e colunas Persona e Riscos (R-NN) preenchidas. Sincronizados com o documento da equipe em 03/11. Falta a revisão do grupo.
- **Fonte da base do RAG** ([ADR 0004](docs/decisoes/0004-fonte-e-manutencao-da-base.md), aceita na versão 2, depois da [crítica](docs/decisoes/revisoes/0004-critica.md)):
  - candidatos da Overture e curadoria humana de horário e preço;
  - Google Places só para conferir os finalistas na hora do plano, sob cinco condições dos termos: sem mapa não Google, só o place ID guardado, nada exibido nem lido em voz, nada na avaliação LLM × RAG, sem benchmark público;
  - TomTom medida no piloto;
  - meta de lugares derivada das horas, com teto de 200;
  - aceite pelo teste de cobertura por região e por faixa de orçamento.
  Esquema e guia em [docs/dados/](docs/dados/).
- **Coleta automática e base vetorial** ([ADR 0005](docs/decisoes/0005-coleta-automatica-e-base-vetorial.md), proposta): substitui a curadoria humana do ADR 0004.
  - Robô nos sites oficiais e nas agendas, com extração por LLM e evidência literal conferida por código; nenhum campo é digitado por uma pessoa.
  - Rodada semanal (eventos duas vezes por semana).
  - PostgreSQL com pgvector, busca híbrida e embeddings BGE-M3 locais.
  - Limitação principal: lugares sem site ficam fora, o que pode concentrar a base no centro.
- **Pipeline da base implementado** em [src/base/](src/base/README.md) (população a cargo do Cauan):
  - as 10 etapas do ADR 0005, com o Postgres e o pgvector em Docker (`docker-compose.yml`) e embeddings BGE-M3 locais;
  - extração por subagentes Claude Haiku 5.5, conferida por um validador em código;
  - 12 testes.
- **Piloto de 100 candidatos: 0 aprovados.** 52 sites da Overture são domínios mortos, e nenhum dos que responderam publica preço em texto.
- **Varredura ampliada: 811 sorteados (todos os elegíveis fora do Centro e do Oeste próximo) e 10 aprovados.**
  - Dos aprovados, 8 ficam no Centro, e nenhum no Oeste, no Sul ou no Norte.
  - Uma triagem em código manda ao Haiku só os sites com sinais de preço e horário.
  - Depois do OCR, o banco tem 11 lugares, 40 itens com preço e 35 RAs, com vetores BGE-M3 e e5.
  - A busca híbrida com filtros de dia, hora, teto e atributos já funciona (`python -m base buscar`).
- **OCR de cardápio (opção A):**
  - acrescentou 2 lugares;
  - deixou o validador mais rígido, e uma aprovação errada da rodada anterior caiu;
  - **a base tem 11 lugares, 9 no Centro**.
- **Google Places:** a comparação de cobertura Google × OSM × Overture está pronta (`python -m base comparar-google`). Falta a chave no `.env`.
- **Instagram e TikTok:** uma integrante testa a coleta por computer use. Isso contraria o ADR 0005 (termos das plataformas e LGPD) e precisa de um ADR próprio, se o grupo seguir.
- **OpenStreetMap:** tem horário em 12% dos lugares de comer e beber e nenhum preço; usá-lo exige cumprir a ODbL.
- **Google Places:** tem `priceRange`, horários e atributos, mas nada pode ser guardado.
- **Tripadvisor (estudado em 05/11): não serve.**
  - **Site:** os termos vedam robô, "sistema de IA", cópia manual e até link profundo sem permissão por escrito.
  - **API oficial (Terra):** só guarda o ID, veda qualquer uso com IA fora de teste interno e dá o preço em três faixas, sem reais.
  - **Cobertura:** fora do Centro, é pequena e antiga.
  - **Única via:** uma permissão acadêmica por escrito.
- **Detalhes:** a comparação completa e as opções A a D estão no [ADR 0005](docs/decisoes/0005-coleta-automatica-e-base-vetorial.md#resultado-do-piloto-0311).

  **Próximos passos da base:**
  - o grupo escolhe a opção;
  - pedidos de teste;
  - backend de API para a rodada semanal (semana 4);
  - respostas às perguntas dos ADRs 0004 e 0005: conta de faturamento, plano sem mapa embutido, lugares sem site, e-mail do robô.
- **Mapa da arquitetura** atualizado com os ADRs 0004 e 0005 e publicado. Ainda não mostra o pipeline implementado nem o resultado do piloto. Em 05/11 entraram os ADRs 0006 e 0007 (voz, interpretador, contrato da busca, provedores); **falta publicar** com `publicar.sh`.
- **Voz e interpretador** (05/11, decididos em três rodadas de perguntas; [ADR 0006](docs/decisoes/0006-transcricao-de-fala.md) e [ADR 0007](docs/decisoes/0007-interpretador-e-contrato-de-busca.md), propostas):
  - **Interpretador** em [src/interpretador/](src/interpretador/README.md):
    - seis intenções, várias por mensagem;
    - o LLM preenche um JSON Schema estrito, e o código resolve as datas, converte os valores (só do trecho literal), casa as RAs e decide confirmação, pergunta e destino;
    - nomes pseudonimizados antes do LLM; orçamento dito no grupo é ignorado;
    - DeepSeek V4.1 Flash pela OpenRouter, só com provedores sem retenção e sem fp4.
  - **Contrato da busca** em [src/base/contrato.py](src/base/contrato.py): `buscar(ConsultaBusca) → ResultadoBusca`, com SQL só por parâmetros; `base buscar` passou a usá-lo.
  - **Voz** em [src/voz/](src/voz/README.md): Whisper com provedor trocável (faster-whisper, MLX, Groq), áudio em bytes apagado num `finally`, medição de WER, termos críticos, latência e custo.
  - **Prévia de voz com voz sintética (CPU):**
    - `large-v3-turbo`: 3,6% de erro nos termos críticos e 16 s por frase;
    - `small`: 7,2% e cerca de 4 s;
    - "sexta" vira "6." no `small`;
    - nenhum local cumpre o p90 de 2,5 s neste notebook; o modelo grande precisa do M4 ou do Groq;
    - **Groq:** 3,6% de erro nos termos críticos, p90 de 1,0 s e US$ 0,006 pelas 50 frases.
  - **Voz real** (22 gravações de uma pessoa, em `data/raw/voz/equipe/m1/`, fora do git):
    - Groq, com retenção zero: 5,9% de erro nos termos críticos e p90 de 0,8 s;
    - `small` local: 13,2% ("sexta" virou "6º" e "cesta");
    - interpretador sobre a transcrição do Groq: 13/13 frases de disponibilidade e gastos certas.
  - **Interpretador medido em 05/11 (DeepSeek V4.1 Flash, sem raciocínio):**
    - texto: RNF-08 33/34 = 97,1% (meta de 90%), 100% das intenções, 98% dos campos, p90 de 1,6 s;
    - voz sintética pelo Groq: 32/34 = 94,1%, p90 de 2,1 s;
    - com raciocínio ligado, o p90 ia a 6,4 s e 2 respostas vinham sem JSON; por isso ficou desligado.
  - **Conjunto de teste** em [eval/](eval/README.md): 50 frases com gabarito e [roteiro de gravação](eval/voz/roteiro.md) (10 por integrante, com consentimento). 57 testes passam sem LLM e sem rede.
  - **Pendências:**
    - retenção zero do Groq ligada em 05/11; decidir se o Groq vira o padrão depois da rodada no Mac M4 (modelo local grande com GPU);
    - gravar as outras 28 frases, de preferência com a voz de outros integrantes;
    - aumentar o conjunto para cerca de 60 frases de disponibilidade e gastos, para o limite inferior provar 90%;
    - as 50 gravações da equipe;
    - a rodada no Mac M4 (`--provedor mlx_whisper`);
    - revisão do gabarito pelo grupo;
    - a busca de ponta a ponta precisa do Docker ligado.
- **Relatório da semana 1** (até 5 páginas de texto, ABNT): [relatorio-semana-01.docx](docs/entregas/semana-01/relatorio-semana-01.docx) e o [PDF](docs/entregas/semana-01/relatorio-semana-01.pdf), montados conforme o [plano](docs/entregas/semana-01/plano-relatorio.md) e alinhados ao documento da equipe revisado (46 RF, riscos renumerados, sem piloto). 5 páginas de texto, com cerca de 1,5 cm de folga. As partes da equipe estão no [documento do grupo](https://docs.google.com/document/d/1mlxgJ9XoadAl4qKV28bw6qexQxF6xpwcSx5aENsRPF4/edit?tab=t.mm6pfcuj8dpt#heading=h.tyssdhkqxqfd) (Google Docs).
- **Mapa da arquitetura planejada** (pedido do mentor Isaque): [docs/arquitetura/index.html](docs/arquitetura/index.html), publicado em [residencia-ia-challenge-2-grupo-7.github.io/residencia-ia-g7-arquitetura](https://residencia-ia-challenge-2-grupo-7.github.io/residencia-ia-g7-arquitetura/). O site fica num repositório público à parte, porque o plano gratuito da organização não tem Pages em repositório privado. Como editar e publicar: [docs/arquitetura/AGENTS.md](docs/arquitetura/AGENTS.md).
- Formulário curto "Pesquisa de Hábitos Sociais" (15 afirmações) em uso para validar a dor. A versão completa fica como referência em [docs/pesquisa/](docs/pesquisa/).
- Repositório na organização do grupo: [Residencia-IA-Challenge-2-Grupo-7](https://github.com/Residencia-IA-Challenge-2-Grupo-7/residencia-ia-g7-challenge2) (privado).

## Pacote de definição do projeto (entregável da semana 1)

- [x] Cenário escolhido
- [x] Problema
- [x] Essential Question
- [x] Mapa de stakeholders (PDF da equipe; precisa tirar jogos)
- [x] Personas (PDF da equipe; limite de sala a corrigir para 20)
- [ ] Requisitos funcionais e não funcionais (v0.3; falta revisão do grupo e coluna Métrica)
- [x] Riscos (PDF da equipe; R-01 a R-09 na numeração nova, no relatório os 6 de maior P × I)
- [x] Premissas (PDF da equipe)
- [x] Métricas de sucesso (PDF da equipe; 7 métricas, no relatório as 3 de resultado)
- [x] Guiding questions (PDF da equipe)
- [x] Montar o relatório .docx a partir do plano (falta completar os sobrenomes na capa e conferir duas referências)

## Próximos passos dos requisitos

- Revisar a v0.3 com o grupo, principalmente as escolhas de comportamento de 29/10 e a seção "Questões em aberto" do documento.
- Preencher a coluna Métrica (M-NN) quando o plano de métricas fechar. O resultado do formulário ajusta as prioridades, e as métricas dão os números dos RNF.
- No documento final, só os Must, agrupados nas 12 capacidades sugeridas no próprio arquivo.
- Escrever os requisitos das extensões futuras (Modo Descoberta, videogames, versão para menores), se sobrar tempo.
- Quando houver código (semana 2), avaliar `openspec init` e migrar cada capacidade para `openspec/specs/`.

## Em aberto

- Convidar os integrantes do grupo para a organização no GitHub
- Confirmar as datas do roadmap
- Combinar com o grupo a convenção de IDs (RF, RNF, R, M) para a rastreabilidade
- Confirmar com o grupo o canal do MVP (ADR 0003)
- No documento da equipe: criar a P19 e a P20 na guia Premissas e alinhar a numeração das guias à do relatório (4 Stakeholders, 8 Riscos, 9 Métricas, 10 Guiding Questions)
- Decidir se o RF-37 (avaliação) sobe para Must, já que a métrica M-03 depende dele

## Integrantes

Papéis definidos em 29/10 ([ata](docs/atas/2026-10-29.md)); a divisão mais detalhada (DevOps, UX/UI e front-end, back-end, testes, engenharia de IA) segue em discussão.

- Cauan Soares: Arquiteto da Solução
- Letícia Miti: Cientista de Dados
- Maria Carolina: Engenheira de Dados
- Maria Eduarda: ML/LLMOps
- Samara Letícia: Engenheira de Dados
