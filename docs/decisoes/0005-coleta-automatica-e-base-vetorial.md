# 0005 — Coleta automática e base vetorial de lugares e eventos

- **Status:** proposta
- **Data:** 2026-11-03
- **Semana do roadmap:** 2 — Base de conhecimento e recuperação
- **Substitui do [ADR 0004](0004-fonte-e-manutencao-da-base.md):** a curadoria humana (Pergunta 1, fontes primárias lidas por pessoas), as rotinas manuais da Pergunta 3, o orçamento de horas da Pergunta 4 e o [guia de curadoria](../dados/guia-curadoria.md) como procedimento
- **Mantém do ADR 0004:**
  - a Overture como fonte de candidatos, sem importar campos do OSM;
  - a Google só na hora do plano, com as cinco condições;
  - os estados exato, aproximado e vencido e seus limites;
  - os filtros com "sem informação";
  - o teste de cobertura por estrato como critério de aceite;
  - a amostra de validação do RNF-03;
  - as regras de LGPD
- **Fica para outro ADR:** o contrato da API de busca usada pelos agentes da semana 4 (aqui só o fluxo de consulta). Definido no [ADR 0007](0007-interpretador-e-contrato-de-busca.md)

## Contexto

O ADR 0004 previa que pessoas da equipe lessem sites e cardápios e preenchessem a base, a cerca de 15 a 25 minutos por lugar. O grupo quer **eliminar a coleta manual**. Também falta decidir **onde e como a base é indexada** para as consultas dos LLMs, que é o "primeiro mecanismo RAG" do roadmap.

Na conversa de 03/11 ficou claro que consultar uma API de lugares na hora da pergunta também é recuperação. Mesmo assim, ela não substitui uma base própria, por três motivos:

- **Exigência dos tutores:** o roadmap pede "base de conhecimento e recuperação" na semana 2 e a comparação LLM × RAG na semana 3 (P14).
- **Termos da Google:** limitam o que pode ser mostrado e lido em voz e proíbem o uso com mapa não Google (ADR 0004).
- **Dados que as APIs não têm:** preço do cardápio por pessoa (RF-15), agenda de eventos do DF e controle da cobertura por região (RNF-13).

## Decisão

1. **Coleta 100% automática, num pipeline reproduzível:**
   - candidatos da Overture, filtrados e sorteados por estrato;
   - robô que lê só o site oficial de cada lugar e as agendas oficiais de eventos;
   - extração dos campos por LLM, com evidência literal;
   - validação por código.

   **Nenhum campo é digitado por uma pessoa.** O que o pipeline não consegue extrair com evidência fica "sem informação". Se faltar um campo obrigatório, o lugar fica fora da base.
2. **Atualização automática:** o pipeline roda de novo toda semana, e duas vezes por semana para eventos. Só reprocessa as páginas que mudaram. A data de verificação do RF-16 passa a ser a data da última extração com evidência.
3. **Base vetorial em PostgreSQL com pgvector:** busca híbrida (vetor e texto em português) com filtros estruturados, e embeddings de um modelo aberto multilíngue rodando localmente, trocável por configuração (RNF-12).
4. **O trabalho humano fica só na medição de qualidade:**
   - a amostra de validação do RNF-03, cerca de 125 itens nas semanas 3 e 6, que mede o pipeline e não preenche dados;
   - a leitura dos relatórios do pipeline.

   Nenhuma pessoa corrige um campo à mão. Um erro encontrado vira ajuste nas regras de extração, e o pipeline roda de novo.

## Parte A — Coleta automática

### Fontes permitidas

| Fonte | Para quê | Regra |
|---|---|---|
| [Overture Maps Places](https://docs.overturemaps.org/guides/places/) | Candidatos, nome, categoria, coordenadas e site (`websites`) | Download por recorte do DF; licença por registro guardada; telefone, e-mail e redes nunca são importados |
| Site oficial do próprio lugar | Horário, cardápio e preços, atributos | Só o domínio do site listado na Overture e páginas desse domínio |
| Cardápio em PDF ou imagem no site oficial | Itens e preços | Leitura multimodal pelo mesmo extrator |
| Agendas oficiais (CCBB, Caixa Cultural, Sesc-DF, Complexo Cultural da República, Cine Brasília, Clube do Choro, Secretaria de Cultura e Economia Criativa do DF, administrações regionais) | Eventos | Lista de URLs semente mantida no repositório; iCal ou RSS quando houver |
| Sites do Ibram, do ICMBio e de cada parque | Parques e áreas protegidas | Lista semente; [tabela de unidades de conservação do Ibram](https://www.ibram.df.gov.br/unidades-de-conservacao) como ponto de partida |
| Google Places, na hora do plano | Status e horário de hoje dos finalistas | Sem guardar nada, nas condições do ADR 0004 |
| Retorno dos usuários (RF-37) | Sinal de divergência | Põe o lugar na fila de reprocessamento prioritário, sem identificar quem respondeu |

**Nunca entram no robô:** Google Maps, Instagram, Facebook, iFood, TripAdvisor, Sympla e outros agregadores. Os termos dessas plataformas proíbem ou limitam a coleta automatizada, ou o conteúdo não é do lugar. O caso do Tripadvisor, inclusive pela API oficial, está em [Tripadvisor](#tripadvisor-estudado-em-0511).

### Regras do robô

- **robots.txt:** é obedecido, e um domínio que proíbe a coleta fica de fora.
- **Ritmo:** no máximo uma requisição a cada 2 segundos por domínio, com até 10 páginas por lugar (início, cardápio, horário, contato, sobre).
- **Identificação:** um user-agent próprio, com o nome do projeto e um e-mail de contato do grupo.
- **Páginas brutas:** ficam fora do git e são apagadas depois de 30 dias. O hash de cada página fica guardado para detectar mudança.
- **Páginas que exigem JavaScript:** são abertas por um navegador sem interface (Playwright) só quando o HTML simples vier vazio.

### Extração por LLM com evidência literal

O extrator recebe o texto da página e devolve um JSON no [esquema](../dados/esquema-base.md). **Cada valor vem acompanhado de `evidencia`**: um trecho copiado da página, de até 200 caracteres, mais a URL.

Um validador em código, não no LLM, aceita o valor só se:

1. o trecho de `evidencia` existe literalmente no texto da página baixada (é isso que barra alucinação);
2. o valor normalizado aparece no trecho, por exemplo "18h às 23h" → `18:00–23:00` e "R$ 39,90" → `39.90`;
3. o valor passa nas regras de plausibilidade:
   - horário bem formado, com no máximo 20 horas abertas por dia;
   - preço de item entre R$ 1 e R$ 500;
   - evento com data futura;
4. não há contradição entre páginas do mesmo site. Se houver, o campo fica "sem informação".

Nos atributos (vegano, ar livre, ruído, foco em álcool, acessibilidade), o extrator só marca "sim" com evidência explícita, como "opções veganas" ou "rampa de acesso". As definições do [guia de curadoria](../dados/guia-curadoria.md) viram as regras do prompt de extração. Ruído e foco em álcool sem frase explícita ficam "sem informação".

**Campos obrigatórios** para o lugar entrar na base:
- **Comer e beber fora:** horário e pelo menos 3 itens com preço.
- **Ao ar livre ou gratuitos:** horário, mais a taxa de entrada ou a indicação de "gratuito".
- **Eventos:** data, horário, local e preço (ou "gratuito").

O custo por pessoa continua calculado por código, com a fórmula do guia (RNF-04).

**Modelo de extração:** um modelo pequeno e barato, com saída estruturada, atrás da mesma interface trocável dos outros provedores (RNF-12). O consumo é registrado (RNF-15). A descrição curta de cada lugar também é gerada pelo LLM, **só a partir dos campos validados**, com o modelo de descrição do guia, sem copiar o texto do site.

### Seleção dos lugares, sem escolha humana

1. Filtrar a Overture: DF, categorias mapeadas para os tipos de rolê, registros com site e com confiança acima de um limite a calibrar no piloto.
2. Deduplicar por domínio do site e por proximidade com nome parecido, em código.
3. Sortear dentro de cada estrato (região × categoria), com as cotas iniciais do ADR 0004.
4. Rodar o robô e a extração. Os lugares sem os campos obrigatórios saem, e o sorteio repõe a vaga no mesmo estrato, até a cota ou até acabarem os candidatos.
5. Gerar o relatório de cobertura: candidatos, lugares aprovados e motivos de falha por estrato.

**Meta:** até 300 lugares, com no mínimo 150. A automação permite passar dos 200 do ADR 0004, e o limite real passa a ser quantos candidatos têm site com dados. O piloto mede essa taxa.

### Cadência

| Rotina | Frequência | Observação |
|---|---|---|
| Descoberta (Overture) | Mensal ou a cada nova versão da Overture | Novos candidatos entram no sorteio dos estratos com falta |
| Robô e extração dos lugares | Semanal | Só reextrai páginas cujo hash mudou; as outras só renovam a data de verificação |
| Robô e extração dos eventos | Duas vezes por semana | Eventos realizados ou cancelados saem automaticamente |
| Fila prioritária | Diária | Lugares fechados ou não encontrados na conferência do plano, ou com divergência relatada no RF-37 |

**Renovar a data de verificação:** é válido quando a página foi baixada de novo, o hash não mudou e a evidência continua lá. O fato foi confirmado na fonte naquela data.

**Efeito nos estados do ADR 0004:** com a rodada semanal, horário e preço ficam "exatos" enquanto o site estiver no ar. Os estados "aproximado" e "vencido" passam a sinalizar sites fora do ar ou páginas que deixaram de ter a informação.

## Parte B — Base vetorial

### Opções consideradas

| Opção | Prós | Contras |
|---|---|---|
| A. PostgreSQL + pgvector | Um só banco para a base e para os dados do app (salas, rolês); filtros em SQL; busca em texto em português nativa (`tsvector`); grátis e local em Docker | Exige operar um Postgres; menos recursos de busca que um banco vetorial dedicado |
| B. Chroma | Simples, embutido em Python | Segundo banco ao lado do do app; filtros mais limitados; busca textual fraca |
| C. Qdrant | Filtros fortes e busca híbrida | Mais um serviço para hospedar |
| D. FAISS ou índice em memória | Zero infraestrutura | Sem filtros nem persistência; tudo à mão |
| E. Gerenciado (Pinecone e similares) | Sem operação | Dependência de fornecedor; dados saem da equipe; faixa gratuita sujeita a mudança |

**Decisão: A, PostgreSQL com pgvector.** Para algumas centenas de documentos, qualquer opção é rápida o bastante. O que decide são filtros duros em SQL (RNF-04), busca textual em português e um banco só para o projeto. Na semana 2 roda localmente em Docker. A hospedagem é decidida com a do app.

### Modelo de embeddings

| Opção | Prós | Contras |
|---|---|---|
| BGE-M3 (BAAI), aberto, rodando localmente | Multilíngue, com bom português; sem custo; nenhum dado sai da equipe | Exige baixar o modelo (alguns GB); um pouco lento em CPU, irrelevante para centenas de documentos |
| multilingual-e5-large, aberto | Mesmo perfil, menor | Recuperação a comparar |
| API de embeddings de um provedor de LLM | Sem infraestrutura | Custo e dependência; texto enviado a terceiros |

**Decisão:** BGE-M3 como padrão e multilingual-e5-large como alternativa. Os dois são comparados no piloto com os pedidos de teste, e fica o de maior recall@10. O modelo e a dimensão ficam na configuração (RNF-12). Trocar de modelo exige regerar todos os vetores, o que leva minutos.

### Documentos indexados

Um documento é uma ficha curta e autossuficiente, gerada por código a partir dos campos validados. Nada é escrito à mão, e nada é copiado do site.

| Coleção | Um documento por | Texto do embedding | Metadados para filtro |
|---|---|---|---|
| `lugares` | lugar | Nome, categoria, RA e região, descrição gerada, ambiente (ruído, ar livre, coberto, foco em álcool), opções alimentares, faixa de custo por pessoa | `tipo_role`, `categoria`, `regiao`, `ra`, `lat`, `lon`, `custo_pessoa_tipico`, `taxa_entrada`, atributos, `horarios` (JSON), `status`, `estado`, `verificado_em`, `fonte` |
| `eventos` | evento | Título, tipo, local, RA, faixa de preço, foco em álcool | `inicio`, `fim`, `preco_min`, `gratuito`, `local_id`, `regiao`, `cancelado`, `esgotado` |
| `regioes` | RA (35) | Nome, região, vizinhança, principais eixos de transporte e estações de metrô (de fontes públicas, quando o GTFS for decidido) | `regiao` |

- Cardápios inteiros não viram documento: os itens ficam em tabela, e o "comida vegana barata" sai dos filtros.
- Os documentos de `regioes` ajudam o LLM a entender pedidos como "perto do metrô" ou "lá pelos lados de Taguatinga".

### Como o banco é populado

O pipeline é idempotente e versionado. Cada etapa grava a sua saída, e uma rodada pode recomeçar de qualquer etapa.

1. **Descobrir:** baixar o recorte do DF da Overture, mapear as categorias e gravar `candidatos`.
2. **Selecionar:** deduplicar e sortear por estrato.
3. **Rastrear:** robô com as regras acima; gravar as páginas e os hashes.
4. **Extrair:** LLM com saída estruturada e evidência.
5. **Validar:** evidência literal, plausibilidade, contradições e campos obrigatórios. Aprovado ou reprovado, com o motivo.
6. **Casar com a Google (opcional):** place ID por Text Search de IDs, confirmado pelo endereço (ADR 0004). Guardado em tabela separada.
7. **Calcular:** custo por pessoa, estados por idade e texto da ficha.
8. **Vetorizar:** gerar o embedding só quando o hash do texto da ficha mudou.
9. **Gravar:** `upsert` nas tabelas e nos vetores, com `versao_base`. Os lugares que saíram ficam marcados como inativos, não são apagados, para manter o histórico dos rolês.
10. **Relatar:** contagens por estrato, taxa de aprovação, motivos de falha, consumo de tokens e resultado do teste de cobertura.

- **Saídas e versões:** o CSV aprovado vai para o git (sem páginas brutas e sem IDs da Google). Uma tag marca a versão usada na comparação LLM × RAG da semana 3.
- **Banco descartável:** o banco é sempre recriável a partir do CSV e da configuração, então os vetores não vão para o git.

### Como os LLMs consultam (resumo; o contrato fica para o próximo ADR)

1. O agente planejador chama a busca com o pedido em texto ("lugar tranquilo para 6 pessoas, sábado à noite") e as restrições já resolvidas: região dos participantes, janela, teto de custo e restrições alimentares e de acessibilidade.
2. **Filtros duros em SQL:** status ativo, estado diferente de vencido, aberto na janela, custo dentro do teto e atributos exigidos iguais a "sim".
3. **Busca híbrida** só entre os que passaram: similaridade vetorial e busca textual em português, combinadas por Reciprocal Rank Fusion. Saem 20 candidatos.
4. O código calcula deslocamento e custo por pessoa (RNF-04). O LLM recebe só as fichas, com fonte e data da verificação, e monta os planos. Lugar que não veio da busca é descartado (RF-16).
5. Na hora de mostrar o plano, os finalistas passam pela conferência da Google (ADR 0004).

## Justificativa e evidências

- **Coleta automática com evidência literal:**
  - tira o trabalho manual sem abrir mão do RNF-03, porque um valor sem trecho correspondente na página é descartado por código, não pelo LLM;
  - faz a extração por LLM servir de leitor, nunca de fonte;
  - é a mesma separação do RNF-04: o LLM interpreta, o código decide.
- **Só o site oficial:** é a fonte que o próprio lugar controla. Agregadores e redes têm termos que proíbem a coleta automatizada; o do [Instagram](https://help.instagram.com/581066165581870), por exemplo, proíbe coleta automatizada sem permissão.
- **pgvector:** escolhido porque o problema é pequeno e filtrado. A vantagem de um banco vetorial dedicado aparece com milhões de vetores, não com centenas.
- **Embedding aberto e local:** custo zero e nenhum dado enviado (P12, RNF-01). O modelo é escolhido por medição nos pedidos de teste, não por reputação.

## Riscos e limitações

| Risco | Ligação | Mitigação |
|---|---|---|
| **Lugares sem site ficam de fora.** Bares e restaurantes pequenos, comuns fora do Plano Piloto, costumam ter só Instagram ou iFood. A base pode ficar mais central e mais cara | R-02, RNF-13 | Medir a taxa de aprovação por região no piloto. Os parques, feiras e eventos públicos das administrações regionais ajudam a cobrir a periferia. Se um estrato falhar no teste de cobertura, o grupo escolhe entre aceitar a limitação, declarada no relatório, ou mudar o RF-16 para permitir candidatos da API na hora do plano, com os limites dos termos |
| Extração errada que passa no validador (trecho certo, interpretação errada, como horário de cozinha tomado por horário da casa) | R-03 | Amostra de validação do RNF-03 com intervalo de confiança; cada erro vira regra no prompt e teste automatizado |
| Site desatualizado (o lugar mudou o horário no Instagram, mas não no site) | R-03 | Conferência dos finalistas pela Google; retorno dos usuários; estado "não conferido agora" |
| Coleta vista como abusiva por algum site | — | robots.txt, ritmo baixo, user-agent com contato; páginas brutas não publicadas |
| Direito autoral sobre o texto do site | — | Guardamos fatos e trechos curtos de evidência, internos e não exibidos; a descrição é gerada a partir dos fatos |
| Dados pessoais em páginas ("fale com a Joana") | R-01, RNF-01 | Lista fechada de campos; os trechos de evidência ficam fora do índice, do CSV público e das respostas |
| Custo de tokens da extração | R-07, P12 | Modelo pequeno; reextrair só páginas que mudaram; consumo registrado; teto por rodada na configuração |
| Overture com poucos sites no DF | — | O piloto mede; FSQ OS Places como fonte adicional de sites, se preciso (Apache 2.0) |

**Limitações declaradas:**
- Lugares sem site oficial não entram no MVP.
- Atributos subjetivos (ruído, foco em álcool) só existem quando o próprio lugar os descreve, então muitos ficam "sem informação".
- Lotação em tempo real continua fora (RF-44).

## Como vamos validar

| O que | Como medir | Critério |
|---|---|---|
| Taxa de aprovação | Lugares aprovados ÷ candidatos rastreados, por estrato, no piloto (100 candidatos sorteados) | Base para a meta; não tem mínimo, mas o teste de cobertura precisa passar |
| Exatidão da extração (RNF-03) | Amostra de cerca de 125 itens exibidos, conferidos por uma pessoa no site de origem, nas semanas 3 e 6. Só mede, não corrige | ≥ 95% pelo limite inferior de Clopper-Pearson; senão, acerto observado com intervalo |
| Alucinação barrada | Valores rejeitados porque a evidência não existia na página | Só monitorado; uma taxa alta indica prompt ou modelo ruim |
| Recuperação | 20 a 30 pedidos de teste com os lugares esperados | recall@10 ≥ 0,8 com o modelo escolhido; comparar BGE-M3 e e5 |
| Cobertura (RNF-13, RNF-16) | Teste por estrato do ADR 0004 | Os mesmos critérios |
| Custo | Tokens por rodada e chamadas à Google | Dentro dos créditos gratuitos (P12) |
| Trabalho manual | Horas gastas em coleta e correção de dados | Zero; a medição de qualidade é contada à parte |

## Plano de execução

| Semana | Entrega |
|---|---|
| 2 | Pedidos de teste escritos; Postgres com pgvector em Docker; etapas 1 a 5 do pipeline com 100 candidatos; taxa de aprovação por estrato; comparação dos dois embeddings |
| 3 | Pipeline completo; base congelada por tag; comparação LLM × RAG; primeira amostra de validação |
| 4 | Rodada semanal automática; fila prioritária; busca usada pelos agentes |
| 5 | Leitura de cardápio em PDF e imagem (multimodal) no extrator; meta de lugares |
| 6 | Segunda amostra de validação; teste de cobertura final |

## Mudanças em outros documentos

- ADR 0004: marcar as partes substituídas.
- [Esquema da base](../dados/esquema-base.md): `curador` sai e entram `evidencia`, `metodo` e `pipeline_versao`.
- [Guia de curadoria](../dados/guia-curadoria.md): deixa de ser procedimento; as definições viram regras de extração.
- Requisitos: a questão em aberto 4 aponta também para este ADR. O RF-16 não muda: a fonte é a URL do site, e a data é a da última extração com evidência.
- Mapa da arquitetura: a curadoria vira pipeline automático; banco vetorial e embeddings decididos (pendente, aqui e no repositório público).

## Resultado do piloto (03/11)

Pipeline implementado em [src/base/](../../src/base/), com extração feita por subagentes Claude Haiku 5.5. Números completos em [data/base/relatorio.md](../../data/base/relatorio.md).

| Etapa | Lugares |
|---|---|
| Candidatos da Overture nos tipos de rolê, no DF | 11.255 |
| Com site próprio (sem redes, agregadores e delivery) | 3.357 |
| Elegíveis (confiança ≥ 0,5, um por domínio) | 1.744 |
| Sorteados no piloto (17 ou 16 por região) | 100 |
| Site respondeu com conteúdo | 33 |
| Aprovados com os campos obrigatórios | **0** |

- **O validador e o LLM funcionaram:** nenhum trecho inventado (zero "evidência ausente"); o Haiku recusou os sites que eram de outro negócio.
- **A fonte não entrega:**
  - **Domínios mortos:** 52 dos 100 sites listados na Overture não existem mais.
  - **Agregadores:** 140 dos elegíveis eram páginas geradas por agregadores (placeweb.site), hoje bloqueadas.
  - **Site de outro negócio:** ao menos 5 dos 33 que responderam eram de outro negócio (uma clínica, o Jardim Botânico do Rio, um domínio revendido).
- **Preço é o gargalo:** nenhum dos 33 sites tem preço em texto. Os cardápios são imagem, PDF sem texto ou JavaScript. Horário apareceu em 4.
- **Bares:** todos os 18 sorteados estavam fora do ar ou sem site.

**Consequência:** com as regras atuais, nem os 1.744 elegíveis chegariam aos 150 lugares da meta. Antes de mais rodadas, o grupo precisa escolher uma das opções:

| Opção | O que muda | Custo e risco |
|---|---|---|
| A. Ler cardápio em imagem e PDF agora, adiantando a semana 5 | O robô baixa as imagens de cardápio; um OCR local gera o texto contra o qual o validador confere; o Haiku extrai desse texto | Mantém a coleta sem pessoas e a conferência em código; erro de OCR vira "sem informação" |
| B. Preço deixa de ser obrigatório em comer e beber | Entra com horário; custo "sem informação" | O lugar some de todo filtro de orçamento (RF-15), justo o diferencial |
| C. Agendas oficiais primeiro | Eventos e equipamentos públicos (CCBB, Sesc, parques), que publicam em texto | Cobre o tipo "ao ar livre ou gratuitos" e eventos, não comer e beber |
| D. Mudar o RF-16 | Candidatos de comer e beber vêm de uma API na hora do plano, com os limites do ADR 0004 | Sai do RAG próprio para esse tipo; os termos da Google limitam o que se mostra |

**Recomendação do autor:** C já, para ter base na semana 3, e A como experimento medido nos 33 sites do piloto. B e D ficam como plano de contingência.

### Varredura ampliada (03/11)

A reposição do sorteio levou o robô a **todos** os elegíveis do Oeste, Sul, Norte e Leste e a parte do Centro e do Oeste próximo. Uma triagem em código passou a mandar ao LLM só os sites com sinais de preço e horário no texto.

| Etapa | Lugares |
|---|---|
| Sorteados (piloto mais reposição) | 811 |
| Site respondeu com conteúdo | 234 (388 domínios mortos) |
| Passaram na triagem | 41 |
| **Aprovados** | **10**: 8 no Centro, 1 no Oeste próximo, 1 no Leste e nenhum no Oeste, Sul ou Norte |

- **Validador:** 172 valores conferidos, 150 aceitos e 22 barrados. Só 1 por evidência inexistente; os outros eram valores que não estavam no trecho citado.
- **Erros que passaram:** são de interpretação e só a amostra humana do RNF-03 mede:
  - pizza inteira contada como prato de uma pessoa;
  - sobremesa classificada como prato principal;
  - horário tirado de um post de blog de 2015.
- **Consumo:** cerca de 1,7 milhão de tokens do Haiku, em 13 lotes de extração e 1 de descrições.
- **Teto da rota:** se a mesma taxa valer para os cerca de 930 elegíveis que faltam, quase todos no Centro e no Oeste próximo, a rota "Overture + site oficial" chega a uns 20 lugares, longe dos 150 da meta. Na periferia, ela não entrega nada.

### Opção A: OCR de cardápio (testada em 03/11)

O OCR roda localmente, com EasyOCR em português, sobre imagens e PDFs escaneados de cardápio achados nas páginas já salvas ([src/base/ocr.py](../../src/base/ocr.py)). O texto entra no manifesto como mais uma página, e o validador confere as evidências contra ele.

| Etapa | Lugares |
|---|---|
| Comer e beber com site no ar, ainda não aprovados | 147 |
| Com imagem ou PDF que parecia cardápio | 43 (159 arquivos) |
| OCR rendeu texto | 17 (33 imagens) |
| Passaram a ter 3 ou mais preços | 9 |
| **Aprovados a mais** | **2**; outros 2 ganharam preços, mas o site não tem horário |

- **Fotos de prato:** muitas imagens chamadas "cardápio" são fotos de prato.
- **Cardápio em colunas:** o OCR embaralha a ordem e separa nome e preço.
- **O Haiku "corrigiu" o OCR:** mesmo instruído a copiar, trocou "rs 34" por "R$ 34".
- **Ajustes no validador:**
  - as confusões típicas do OCR passam a ser normalizadas igual dos dois lados;
  - partes de uma evidência separadas por "..." precisam estar próximas e **sem outro preço no meio**.
  - A segunda regra também derrubou uma aprovação errada da rodada anterior: um hambúrguer pareado com um preço a 3 mil caracteres de distância.
- **Conclusão:** o OCR melhora a precisão do validador, mas acrescenta pouco à cobertura. A base fica com 11 lugares, 9 deles no Centro.

### OpenStreetMap como fonte complementar (medido em 03/11)

A medição foi feita pelo Overpass, como consulta: nada foi importado ([src/base/osm.py](../../src/base/osm.py)). O OSM tem 3.338 lugares com nome no DF nos tipos de rolê (a Overture tem 11.255).

| Dado | Comer e beber (2.668) | Ao ar livre ou gratuitos (567) | Locais de evento (103) |
|---|---|---|---|
| Horário (`opening_hours`) | 316 (12%) | 54 (10%) | 6 |
| Site | 182 | 9 | 10 |
| Cozinha (`cuisine`) | 1.045 (39%) | — | — |
| Vegetariano / vegano | 39 / 26 | — | — |
| Cadeira de rodas | 138 | 13 | 7 |
| Área externa | 121 | — | — |
| Preço | **0** | 6 com `fee` | 0 |

- **Datas de conferência:** só 57 dos 376 horários têm data de conferência (`check_date`), 52 delas de 2025 ou 2026. Os outros não dizem quando foram vistos.
- **Sites vivos:** 80% dos sites do OSM ainda existem, contra cerca de 50% dos da Overture no piloto.
- **Cruzamento:**
  - dos 100 do piloto, 14 estão no OSM e 3 com horário;
  - dos 1.744 elegíveis da Overture, 403 estão no OSM e 59 com horário.
- **Conclusão:** o OSM completa horário e cozinha de uma parte pequena dos lugares e não resolve preço. Usar esses dados obriga a cumprir a ODbL: atribuição e a base derivada publicada na mesma licença (seções 4.4 e 4.6). Isso é viável para um projeto acadêmico, mas exige uma decisão do grupo, porque muda o ADR 0004.

### O que a Google Places (New) entrega, comparado com a base

A comparação é pela documentação dos campos ([recurso Place](https://developers.google.com/maps/documentation/places/web-service/reference/rest/v1/places), [Text Search e SKUs](https://developers.google.com/maps/documentation/places/web-service/text-search)). Não houve chamada à API, porque não existe conta de faturamento.

| Dado do plano | Nossa base (quando o site tem) | Google Places (New) | SKU |
|---|---|---|---|
| Aberto ou fechado | Status pelo site no ar | `businessStatus` | Pro |
| Horário | Por dia, com o trecho do site | `regularOpeningHours`, e `currentOpeningHours` com feriados | Enterprise |
| Preço | Itens com preço e custo por pessoa calculado | `priceRange` (faixa em reais) e `priceLevel` | Enterprise |
| Vegetariano | Sim, com evidência | `servesVegetarianFood` | Enterprise + Atmosphere |
| Vegano, sem glúten, sem lactose | Sim, com evidência | Não existe | — |
| Área externa, música ao vivo | Com evidência | `outdoorSeating`, `liveMusic` | Enterprise + Atmosphere |
| Acessibilidade | Entrada e banheiro | `accessibilityOptions` (entrada, banheiro, assento, estacionamento) | Pro |
| Reserva, grupos | `exige_reserva`, `grupo_max` | `reservable`, `goodForGroups` | Enterprise + Atmosphere |
| Fonte e data verificáveis | URL e data de cada campo | Não informa a origem nem a data | — |

- **Mais completa, mas presa aos termos:** a Google provavelmente cobre muito mais lugares que a nossa base. Só que nada pode ser guardado além do place ID (3.2.3(a)(iii)), mostrado ou lido em voz, nem usado com mapa não Google (ADR 0004).
- **Comparação de exatidão vetada:** comparar a exatidão do nosso extrator com a Google é usar conteúdo da Google para validar IA (3.2.3(c)(vii)), o que os termos proíbem. Dá para medir só a cobertura dos finalistas, internamente.
- **Na hora do plano:** a Google pode filtrar os finalistas por horário e faixa de preço sem que o dado entre na base. O custo é o SKU Enterprise, com 1.000 chamadas gratuitas por mês, contra 5.000 do Pro previsto hoje.

### Tripadvisor (estudado em 05/11)

O estudo leu os termos de uso do site, o robots.txt e a documentação da API oficial (Terra). Nenhuma página de lugar foi aberta, porque os termos proíbem o acesso por sistema de IA. Os indícios de cobertura vêm de resultados de busca.

**Pelo site (robô, raspagem ou computer use): proibido.**
- **Acesso automatizado:** os Termos de Utilização (seção "Atividades interditas", de 16/02/2024) vedam usar robô, aranha, "sistema de inteligência artificial (IA)" ou outro meio automatizado para acessar, copiar, raspar ou agregar conteúdo, salvo permissão por escrito. Um agente de computer use cai nessa regra.
- **Cópia manual:** outro item da mesma seção veda copiar ou explorar o conteúdo "por meio automático ou processo manual" fora do contrato. Uma pessoa transcrevendo o Tripadvisor para a base também fica fora.
- **Links profundos:** fazer link para qualquer parte do site exige autorização por escrito. Nem um botão "ver no Tripadvisor" na ficha é permitido sem ela.
- **robots.txt:** o do .com.br bloqueia por inteiro ClaudeBot, GPTBot, CCBot, Google-Extended e outros robôs de IA.

**Pela API oficial (Terra, pacote Discover):**

| Ponto | O que dizem os termos e a documentação |
|---|---|
| API antiga (Content API) | Desativada em 31/08/2026. O plano de 5.000 chamadas grátis por mês acabou com ela |
| Custo | 1.000 lugares grátis uma única vez por conta; depois, de US$ 0,015 a US$ 0,009 por lugar devolvido. Uma busca por proximidade devolve até 20 lugares e conta 20 |
| Guardar | Só o location ID ([Caching Policy](https://docs.terra.tripadvisor.com/docs/caching-policy)). Nada pode ir para a nossa base |
| Uso com IA | Nenhuma licença para usar o conteúdo com IA ou aprendizado de máquina, incluindo bancos de dados ligados a eles (3.1.2). A única exceção é o grounding por RAG em teste interno, não comercial e sem usuários |
| Exclusividade | Enquanto o contrato valer, o cliente não pode coletar nem exibir conteúdo parecido com o licenciado (3.4.5) |
| Exibição | Tudo como veio, com a marca e link para o Tripadvisor, sem combinar com outro conteúdo (3.4.2) e fora do alcance de buscadores (3.4.3) |
| Quem contrata | Uma entidade constituída (6.1). Um grupo de alunos teria de contratar em nome de uma pessoa ou da universidade |

- **Campos de Location Details:**
  - horário por dia (`opening_hours`) e status (aberto, fechado ou fechado temporariamente);
  - categorias e atributos (comodidades);
  - links do site oficial e do cardápio;
  - nota e ranking;
  - aceita `locale=pt-BR`.
- **O que falta:**
  - preço em reais: a API dá só uma de três faixas (`Cheap Eats`, `Mid Range`, `Fine Dining`);
  - itens com preço;
  - tipo de cozinha: a versão nova não tem mais esse campo.
- **Cobertura no DF** (pelos resultados de busca, não medida): a página de Brasília fala em cerca de 4.400 restaurantes, e a de Ceilândia lista de 30 a 40, com avaliações em geral de 2013 a 2018. O Tripadvisor também se concentra no Centro e envelhece fora dele.
- **Conclusão: o Tripadvisor é mais restritivo que a Google para este projeto.**
  - **Comparado com a Google:** a Google deixa usar o dado na hora do plano, com condições. O Tripadvisor veda qualquer uso com IA no produto e, durante o contrato, impede coletar dado parecido, o que bate de frente com o pipeline.
  - **Nem a base nem o plano:** o Tripadvisor não entra na base nem na hora do plano, e continua na lista "Nunca entram no robô".
  - **Única via:** uma permissão por escrito para uso acadêmico, prevista tanto nos termos da API (3.1.2) quanto nos do site. A resposta pode não chegar a tempo do MVP.

## Perguntas para o grupo

1. Aceitam que lugares sem site oficial fiquem fora do MVP? Se o teste de cobertura falhar numa região, preferem declarar a limitação ou mudar o RF-16?
2. Qual e-mail do grupo vai no user-agent do robô?
3. Qual provedor de LLM, com créditos gratuitos, faz a extração?

## Referências

- GOOGLE. **Google Maps Platform Terms of Service**. Disponível em: https://cloud.google.com/maps-platform/terms. Acesso em: 3 nov. 2026.
- IBRAM. **Unidades de conservação**. Disponível em: https://www.ibram.df.gov.br/unidades-de-conservacao. Acesso em: 3 nov. 2026.
- INSTAGRAM. **Termos de Uso**. Disponível em: https://help.instagram.com/581066165581870. Acesso em: 3 nov. 2026.
- OVERTURE MAPS FOUNDATION. **Places guide**; **Attribution**. Disponível em: https://docs.overturemaps.org/. Acesso em: 3 nov. 2026.
- TRIPADVISOR. **API Master Terms and Conditions**; **Caching Policy**; **Usage-based pricing**; **FAQ** (migração da Content API). Disponível em: https://docs.terra.tripadvisor.com/. Acesso em: 5 nov. 2026.
- TRIPADVISOR. **Termos de Utilização do Tripadvisor**. Disponível em: https://tripadvisor.mediaroom.com/BR-terms-of-use. Acesso em: 5 nov. 2026.
- pgvector. **Open-source vector similarity search for Postgres**. Disponível em: https://github.com/pgvector/pgvector. Acesso em: 3 nov. 2026.
- BAAI. **BGE-M3**. Disponível em: https://huggingface.co/BAAI/bge-m3. Acesso em: 3 nov. 2026.
- CORMACK, G. V.; CLARKE, C. L. A.; BÜTTCHER, S. Reciprocal rank fusion outperforms Condorcet and individual rank learning methods. In: **SIGIR**, 2009.

## Histórico

| Data | Mudança |
|---|---|
| 2026-11-03 | Versão inicial |
| 2026-11-03 | Resultado do piloto e opções para o grupo; pipeline em `src/base/` |
| 2026-11-03 | Varredura ampliada (811 sorteados, 10 aprovados), medição do OSM e comparação com os campos da Google Places |
| 2026-11-03 | Opção A (OCR de cardápio) testada: +2 aprovados, validador mais rígido; base com 11 lugares |
| 2026-11-05 | Estudo do Tripadvisor (site e API Terra): fica fora da base e do plano |
