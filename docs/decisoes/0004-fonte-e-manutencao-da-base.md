# 0004 — Fonte e manutenção da base de lugares e eventos

- **Status:** aceita (versão 2, depois da [crítica](revisoes/0004-critica.md)); **parcialmente substituída pelo [ADR 0005](0005-coleta-automatica-e-base-vetorial.md)** (proposta), que troca a curadoria humana por coleta automática e decide a base vetorial. Continuam valendo daqui: Overture como fonte de candidatos, Google só na hora do plano com as cinco condições, estados e limites, filtros, teste de cobertura, amostra de validação e LGPD.
- **Data:** 2026-11-03
- **Semana do roadmap:** 2 — Base de conhecimento e recuperação
- **Fecha:** a questão em aberto 4 dos [requisitos](../produto/requisitos.md#6-questões-em-aberto) e o limite "a definir" do RF-16
- **Documentos operacionais:** [esquema da base](../dados/esquema-base.md) e [guia de curadoria](../dados/guia-curadoria.md)
- **Fica para outros ADRs:** banco vetorial, embeddings, framework do RAG e contrato da API de busca; mapas e rotas, que precisam respeitar a condição 1 da Pergunta 2

## Contexto

Em 29/10 o grupo combinou que os planos seriam montados a partir de uma **base curada pelo grupo, indexada no RAG, mais uma API para conferir se o lugar existe e está aberto**. Este ADR detalha esse combinado em quatro perguntas:

1. De quais fontes sai a base?
2. Qual API confere se o lugar existe e está aberto?
3. Com que frequência os dados são reverificados, e quando um preço ou horário passa a aparecer como "aproximado" (RF-16)?
4. Quantos lugares a base terá no MVP, e como se dividem entre os tipos de rolê?

| Requisito | O que exige da base |
|---|---|
| RF-01, RF-17 | Restrições alimentares e de acessibilidade e horário de funcionamento como filtros duros |
| RF-15 | Custo por pessoa (atividade e comida) e itens para levar |
| RF-16 | Só lugares e eventos da base, com fonte e data da última verificação por item; dado antigo como "aproximado" |
| RF-20 (Should) | Lista de compras com custo estimado para o rolê em casa |
| RF-27 | Link do mapa no resumo compartilhado |
| RF-37, RF-38 (Should) | Avaliação depois do rolê, que pode alimentar a base |
| RF-40 (Should) | Mensagens lidas em voz alta |
| RF-44 (Should) | Ruído, ambiente, faixa de preço e "sem informação" quando faltar o dado |
| RF-46 (Could) | Alternativas cobertas e próximas para imprevistos |
| RNF-03 | 100% dos lugares dos planos existem; pelo menos 95% dos preços e horários corretos |
| RNF-04 | Custo por pessoa calculado por código |
| RNF-13 | Planos viáveis para quem mora longe e para quem tem menos dinheiro |
| RNF-15, P12, P16 | Testes dentro das cotas gratuitas; cache só do que os termos permitem |
| RNF-16 | Opção sem foco em álcool sempre que houver uma viável |

**Restrições do projeto:** cinco pessoas com cerca de 20 h semanais cada (P08, P11), custo perto de zero (P12, P15, P16) e LGPD (RNF-01).

**Horizonte:** o MVP termina na semana 7 (entrega em 11/12/2026). A base é montada entre as semanas 2 e 5, então nenhum dado terá mais de cerca de seis semanas durante o projeto. Regras que só fazem efeito depois disso estão marcadas como **pós-MVP**.

## Princípios

1. **A base é nossa.** Cada campo guardado vem de uma fonte que permite guardá-lo: o próprio lugar, dados abertos de licença permissiva ou observação da equipe.
2. **Conteúdo da Google não entra na base.** Os termos proíbem guardar, indexar, copiar nomes e endereços e criar conteúdo a partir dele ([Termos, 3.2.3(a) a (c)](https://cloud.google.com/maps-platform/terms)). Do Google guardamos só o place ID, que a [política da Places API](https://developers.google.com/maps/documentation/places/web-service/policies) libera sem prazo. Nada vindo da Google é mostrado ao usuário, lido em voz alta (3.2.3(a)(iv)) ou usado para avaliar modelos de IA (3.2.3(c)(vii)).
3. **Só uma pessoa atualiza a verificação.** A data `verificado_em` de um campo só muda quando um curador confere na fonte primária. A API decide se o lugar entra *naquele* plano; não renova a base.
4. **Coleta humana, não raspagem.** Onde os termos proíbem coleta automatizada, uma pessoa lê e registra o fato. Não copiamos texto, fotos nem avaliações.
5. **O critério é o resultado, não o insumo.** A base é aceita quando salas simuladas de todas as regiões e faixas de orçamento recebem planos viáveis, não quando atinge percentuais por região.

## Pergunta 1: fontes da base

### Opções consideradas

| Opção | Prós | Contras |
|---|---|---|
| A. Curadoria manual sem lista de candidatos | Controle total; sem custo | Depende da memória e do gosto da equipe; cobre mal as RAs que a equipe não frequenta |
| B. Importar de API comercial (Google, Foursquare) | Rápida e ampla | Termos proíbem guardar o conteúdo; custo acima da cota |
| C. Dados abertos para os candidatos e curadoria humana dos campos voláteis | Licenças permitem guardar; cobre todas as RAs; a curadoria foca no que importa | Horário e preço quase não existem nos dados abertos; dados com duplicatas e lixo |
| D. Raspar Instagram, iFood, Sympla, TripAdvisor | Volume | Viola termos (o do [Instagram](https://help.instagram.com/581066165581870) proíbe coleta automatizada); traz dados pessoais |
| E. Retorno dos usuários depois do rolê ("estava aberto? o preço bateu?") | Conferência grátis no uso real | Depende de haver uso; amostra enviesada pelos lugares escolhidos |
| F. Formulário para os próprios lugares atualizarem os dados | Dado direto da fonte | Exige contato e manutenção da relação; fora do alcance de 7 semanas |
| G. Leitura de cardápio em PDF ou foto pela IA, confirmada por uma pessoa | Reduz o tempo de digitação dos preços | Depende da multimodalidade da semana 5; erros de leitura |

### Decisão

**Opção C como base, com E e G como complementos.** D está descartada, e F fica para depois do MVP.

- **Descoberta de candidatos:** [Overture Maps Places](https://docs.overturemaps.org/guides/places/) é a fonte principal. Ela é baixada por recorte geográfico do DF, sem conta, e cada registro tem licença permissiva conforme a origem (CDLA-Permissive-2.0, Apache-2.0 ou CC0; ver [atribuição](https://docs.overturemaps.org/attribution/)). As duplicatas e o lixo são filtrados pela própria curadoria, porque só entra o que um curador confirmar.
- **OpenStreetMap:** é consultado à mão para achar lacunas, mas nenhum campo do OSM é importado. Isso evita a obrigação da [ODbL](https://opendatacommons.org/licenses/odbl/1-0/) de oferecer a base derivada quando um resultado dela é usado publicamente (seções 4.4 e 4.6).
- **FSQ OS Places** (Apache 2.0, exige conta no portal da Foursquare): só entra se o piloto mostrar regiões com poucos candidatos na Overture.
- **Retorno dos usuários (E):** pergunta opcional dentro da avaliação do RF-37. Uma divergência relatada só põe o lugar na fila de reconferência, sem registrar quem respondeu.
- **Leitura de cardápio (G):** automação Could a partir da semana 5. A IA propõe os itens de referência, e o curador confirma.

### Fontes por tipo de dado

| Dado | Fonte primária (o que guardamos) | Observação |
|---|---|---|
| Candidatos, nome, categoria e coordenadas | Overture Places | Lugar fora da Overture: coordenada a partir do endereço publicado pelo próprio lugar, marcada como manual. Nunca da Google |
| Endereço legível e site | Site ou perfil oficial do lugar | Não copiar do app Google Maps ([Termos, 3.2.3(a)(iii)](https://cloud.google.com/maps-platform/terms)) |
| Horário de funcionamento | Site oficial, perfil oficial lido por uma pessoa, placa ou canal comercial do lugar | Horário de feriado entra como exceção datada |
| Preço por pessoa | Cardápio publicado pelo lugar | Itens de referência mais couvert e taxa de serviço; o custo por pessoa é calculado por código com a fórmula do guia. Preço de app de delivery não vale |
| Eventos | Página oficial do evento ou do espaço (CCBB, Caixa Cultural, Sesc-DF, Complexo Cultural da República, Cine Brasília, Clube do Choro e similares) e páginas públicas de venda, lidas por uma pessoa | A [API do Sympla](https://developers.sympla.com.br/api-docs) é só para produtores, e não encontramos API de agenda cultural do DF |
| Parques e áreas protegidas | [Tabela de unidades de conservação do Ibram](https://www.ibram.df.gov.br/unidades-de-conservacao) e sites de cada parque | O horário vem do site de cada parque |
| Atributos (ruído, foco em álcool, acessibilidade, restrições alimentares e outros) | Observação da equipe a partir do site, do cardápio e das fotos do próprio lugar | Definições fechadas no guia; cada atributo pode ficar "sem informação" |
| Rolê em casa (RF-20, Should) | Faixas de preço por item, sempre exibidas como estimativa | Fora da base do MVP; sem coleta mensal |
| Fotos | Não guardamos | O plano leva ao site do lugar ou ao Google Maps por link |
| Link do mapa | Montado na hora com as [Maps URLs](https://developers.google.com/maps/documentation/urls/get-started) (`query` + `query_place_id`) | Não exige chave nem chamada à API |

### O que fica de fora

- Avaliações, notas, fotos, nomes e endereços copiados da Google ou de outras plataformas.
- Raspagem automatizada de qualquer site ou rede.
- Telefone, e-mail e redes sociais dos dados abertos: a importação usa uma lista fechada de campos permitidos. Em pequenos negócios e MEIs esses contatos costumam ser pessoais.
- O número usado num contato direto com o lugar: guardamos só o fato apurado e o canal ("WhatsApp comercial, 05/11").

## Pergunta 2: API de conferência

### Opções comparadas com os mesmos critérios

| Critério | Google Places (New) | TomTom Search | Foursquare Places | OSM (Overpass) | Conferência manual |
|---|---|---|---|---|---|
| Status do negócio | `businessStatus` (Pro) | A medir | Data de fechamento | Não | Sim |
| Horário | `regularOpeningHours` e `currentOpeningHours` (Enterprise) | Horário dos próximos 7 dias na [busca de POI](https://docs.tomtom.com/search-api/documentation/search-service/points-of-interest-search) | Premium, sem faixa gratuita ([campos](https://docs.foursquare.com/fsq-developers-places/reference/response-fields)) | Tag irregular | Sim |
| O que pode ser guardado | Só o place ID | Termos não encontrados | Só o ID no pay-as-you-go ([diretrizes](https://docs.foursquare.com/fsq-developers-places/reference/usage-guidelines)) | Tudo, em ODbL | Tudo |
| Faixa gratuita por mês | IDs ilimitado; Essentials 10.000; Pro 5.000; Enterprise 1.000 ([preços](https://developers.google.com/maps/billing-and-pricing/pricing)) | 2.500 na Search API ([preços](https://docs.tomtom.com/pricing)) | Contraditória na própria página (500 ou 10.000) | Grátis | Grátis |
| Exige cartão | Sim (conta de faturamento) | Não | A conferir | Não | Não |
| Restrição de mapa | Proibido usar com mapa não Google (3.2.3(e) e [termos específicos 14.2](https://cloud.google.com/maps-platform/terms/maps-service-terms)); sem mapa é permitido (14.1) | A conferir | A conferir | Nenhuma | Nenhuma |
| Cobertura no DF | Medir no piloto | Medir no piloto | Não medida | Baixa para horário | Total, mas lenta |

### Decisão

**Google Places API (New), usada só para casar o place ID na curadoria e para conferir os finalistas na hora do plano, sob as cinco condições abaixo.**

- **TomTom** é medida no mesmo piloto e assume se a Google falhar no critério de validação ou se o grupo não abrir a conta de faturamento.
- **Conferência manual** é o último recurso.
- **Foursquare** está descartada: horário só no plano Premium e faixa gratuita contraditória.
- O provedor fica atrás de uma interface trocável (RNF-12).

**Condições de uso da Google:**

1. **Nenhum mapa não Google no app.** No MVP, o plano não tem mapa embutido e leva ao Google Maps por link (Maps URLs). O ADR de mapas e rotas precisa respeitar isso ou trocar o provedor de conferência.
2. **Nada além do place ID é guardado.** A resposta é usada na hora e descartada, inclusive a coordenada. O cache de 30 dias permitido para latitude e longitude (14.3) não é usado.
3. **Nada da Google aparece para o usuário nem é lido em voz.** A conferência só decide se o lugar entra no plano. O texto mostrado vem da base.
4. **Nada da Google entra na avaliação LLM × RAG** nem em qualquer teste de modelo (3.2.3(c)(vii)).
5. **Nenhuma comparação de exatidão da Google é publicada.** Se for publicada, precisa trazer tudo o que permite reproduzi-la (3.2.4). A medição do piloto fica interna.

**Risco residual:** a cláusula 3.2.3(d)(iii) proíbe usar os serviços principais "em um serviço de listagem ou diretório". Nossa leitura é que um planejador de encontros, que usa a API só para descartar finalistas fechados, não é um diretório. A cláusula, porém, é ampla, e este ADR não é parecer jurídico. Se o grupo considerar o risco alto, a TomTom assume.

### Chamadas, projetos e travas

As cotas do Google Cloud são **por método e por projeto**. A cobrança é **pelo SKU mais alto** entre os campos pedidos, e o uso gratuito soma por conta de faturamento ([uso e cobrança](https://developers.google.com/maps/documentation/places/web-service/usage-and-billing); [controle de custos](https://developers.google.com/maps/billing-and-pricing/manage-costs)). Por isso, cada SKU sai de um único projeto, com cota diária igual ou menor que a faixa gratuita dividida por 31:

| Uso | Chamada e campos | SKU | Grátis por mês | Projeto | Cota diária |
|---|---|---|---|---|---|
| Casar o lugar (uma vez, na curadoria) | Text Search com `places.id` e `places.movedPlaceId` | Text Search Essentials (IDs Only) | Ilimitado | curadoria | Text Search: 161 (protege contra máscara errada, que cairia em Text Search Pro) |
| Confirmar o casamento | Place Details com `formattedAddress` | Essentials | 10.000 | curadoria | Place Details: 322 |
| Status dos finalistas | Place Details com `businessStatus` e `movedPlaceId` | Pro | 5.000 | plano | Place Details: 161 |
| Horário dos finalistas quando a data do plano é feriado | Place Details com `currentOpeningHours` | Enterprise | 1.000 | feriado | Place Details: 32 |

- O casamento só é aceito quando o endereço devolvido bate com o endereço publicado pelo lugar. Se não bater, o curador decide. O endereço da Google não é gravado.
- Não há lote mensal pela Google. Isso tira o maior consumo e o maior risco de uso indevido.
- Desenvolvimento e testes de carga (RNF-14) usam um **provedor falso** pela mesma interface. Só os testes do MVP e a demonstração chamam a Google.
- Com 2 ou 3 finalistas por rolê, a cota do projeto "plano" comporta cerca de 50 rolês por dia, bem acima dos testes e da demonstração.
- Orçamento e alerta de faturamento **só avisam** e podem atrasar até 48 h. A proteção real são as cotas diárias. A cota reinicia à meia-noite do Pacífico, 5h em Brasília em novembro.
- **Alternativa ao cartão:** o [Free Trial do Google Cloud](https://docs.cloud.google.com/free/docs/free-cloud-features) fecha a conta sem cobrança se ninguém fizer upgrade. Se ele cobrir a Maps Platform (a conferir), é a opção preferida.

### O que acontece na hora do plano

| Resposta da API | Comportamento |
|---|---|
| `OPERATIONAL` | O lugar segue no plano, que mostra a data da verificação humana (RF-16) |
| `CLOSED_TEMPORARILY` ou `CLOSED_PERMANENTLY` | O lugar sai do plano e vai para a fila do curador, só com o nosso ID e "reconferir" |
| `movedPlaceId` preenchido | Repete a conferência com o ID novo e manda o lugar para a fila |
| `NOT_FOUND` | O lugar sai do plano e vai para a fila: pode ser ID obsoleto ou lugar fechado |
| Erro, tempo esgotado ou cota acabada | O plano segue com o dado da base e o rótulo "não conferido agora", mais a data da verificação humana (RNF-15) |
| Evento (nenhuma API cobre) | O plano mostra "confirme no link oficial", com o link da página do evento |

## Pergunta 3: reverificação e "aproximado"

Cada campo volátil guarda `fonte` e `verificado_em`, e o estado depende da idade da verificação humana. Os limites ficam num arquivo de configuração, não no código.

| Dado | Exato | Aproximado (aparece com a data) | Vencido (sai dos planos) |
|---|---|---|---|
| Status do lugar | Verificação humana até 60 dias. Na hora do plano, ganha "conferido agora" ou "não conferido agora" | — | Mais de 60 dias sem verificação humana |
| Horário regular | até 30 dias | 31 a 90 dias | mais de 90 dias |
| Horário em feriado | Exceção registrada para a data, ou conferência dos finalistas pela API | — | Sem conferência: o plano mostra "horário de feriado não confirmado" |
| Preço de comer e beber fora | até 60 dias | 61 a 180 dias | mais de 180 dias |
| Taxa de entrada | até 90 dias | 91 a 365 dias | mais de 365 dias |
| Evento (data, horário, local, preço, esgotado) | até 7 dias | 8 a 14 dias | mais de 14 dias, ou evento realizado ou cancelado |
| Atributos | até 180 dias | 181 a 365 dias | Mais de 365 dias: passam a "sem informação" |
| Itens do rolê em casa | — | Sempre "estimativa" | — |

### O que acontece dentro do MVP

- Horários curados na semana 2 passam a "aproximado" nas semanas 6 e 7. A reconferência da semana 6 (abaixo) evita isso nos lugares mais usados.
- Eventos mudam de estado toda semana.
- Preço, taxa de entrada e atributos **não saem de "exato" no MVP**. Esses limites valem para depois dele e não podem ser calibrados com dados do projeto.

### Justificativa e calibração

- Não encontramos estudo sobre com que frequência horários e cardápios mudam no DF. Os limites são hipóteses ligadas à cadência que a equipe consegue manter: horário mensal, preço trimestral e evento semanal.
- **Calibração possível no MVP:** na semana 6, reconferir 40 lugares do piloto da semana 2, já com cerca de quatro semanas de idade, e medir a taxa de erro por tipo de dado. Se o horário "exato" errar mais de 5%, o limite de 30 dias cai.

### Rotinas

Donos propostos pelos papéis da [ata de 29/10](../atas/2026-10-29.md); o grupo confirma.

| Rotina | Quando | Dono proposto | Tempo estimado |
|---|---|---|---|
| Pipeline: importar candidatos da Overture, validar o esquema, exportar o CSV, gerar o índice | semana 2 | Samara e Maria Carolina (engenharia de dados) | 6 a 8 h |
| Guia de curadoria e pedidos de teste | semana 2 | Cauan (arquitetura) e Letícia (ciência de dados) | 6 h |
| Curadoria inicial | semanas 2 a 5 | Todos, por região | Tempo por lugar medido no piloto |
| Eventos dos próximos 14 dias: novos e recheque | semanal | Rodízio | 2 a 3 h |
| Horário antes de feriado: lugares mais usados nos planos | antes de 15/11, 20/11 e 30/11 (a conferir no calendário do GDF) | Curador da semana | 1 h |
| Fila de divergências (API e retorno dos usuários) | semanal | Curador da semana | 1 h |
| Amostra de validação e calibração | semanas 3 e 6 | Letícia (ciência de dados) | 6 h por rodada |
| Rodada de preços por região | trimestral, pós-MVP | — | — |

## Pergunta 4: tamanho e divisão da base

### Meta

A meta sai das horas, não o contrário: **lugares = horas de curadoria disponíveis ÷ tempo medido por lugar no piloto**.

- **Orçamento proposto:** 20 h por semana da equipe nas semanas 2 a 5, um quinto da capacidade (P08), num total de 80 h.
- **Tarefas fixas, cerca de 30 h:** pipeline, guia, pedidos de teste, eventos, dupla leitura e primeira amostra.
- **Para os lugares, cerca de 50 h:** dá 200 lugares a 15 minutos cada, ou 120 a 25 minutos.
- **Limites:** no mínimo 60 lugares (o necessário para a semana 3) e no máximo 200.

| Marco | Lugares | Para quê |
|---|---|---|
| Semana 2 | Piloto de 20, com o esquema provisório; 20 a 30 pedidos de teste escritos antes | Medir o tempo por lugar e a cobertura da Overture por região; comparar Google e TomTom |
| Semana 3 | 60, com versão congelada por tag no git | Comparação LLM × RAG sobre a mesma base; primeira amostra de validação |
| Semana 4 | 120 | Agentes da semana 4 com cobertura de todas as regiões |
| Semana 5 | até 200, conforme as horas | Testes do MVP |
| Semana 6 | — | Reconferência de calibração e segunda amostra |

### Divisão por tipo (para 200 lugares; proporcional se a meta for menor)

| Tipo | Lugares | Composição | Regras |
|---|---|---|---|
| Comer e beber fora | 100 | cerca de 40 restaurantes, 30 bares e 30 cafés, lanchonetes e sorveterias | Pelo menos 30% com custo típico até R$ 40 por pessoa, valor a substituir pelo dado do formulário de hábitos |
| Ao ar livre ou gratuitos | 50 | parques, mirantes, feiras, museus e centros culturais gratuitos | Pelo menos 60% gratuitos; cada um marcado como coberto ou descoberto (RF-46) |
| Eventos com data | 30 locais, com eventos dos próximos 14 dias | teatros, centros culturais, casas de show e feiras | Pelo menos um terço dos eventos gratuitos ou até R$ 30 |
| Reserva | 20 | lugares para os estratos que falharem no teste de cobertura | — |
| Em casa de alguém (Should) | 0 | faixas de preço por item, como estimativa | Fora da base do MVP |

### Distribuição pelo DF

As 35 RAs ficam em seis regiões, agrupadas por proximidade e eixo de transporte. A proposta é do autor; o grupo pode ajustar.

| Região | RAs |
|---|---|
| Centro | Plano Piloto, Cruzeiro, Sudoeste/Octogonal, Lago Sul, Lago Norte, Varjão, Park Way, Candangolândia, SIA |
| Oeste próximo | Taguatinga, Águas Claras, Vicente Pires, Arniqueira, Guará, SCIA/Estrutural, Núcleo Bandeirante, Riacho Fundo, Riacho Fundo II |
| Oeste | Ceilândia, Sol Nascente/Pôr do Sol, Samambaia, Brazlândia |
| Sul | Gama, Santa Maria, Recanto das Emas, Água Quente |
| Norte | Sobradinho, Sobradinho II, Planaltina, Arapoanga, Fercal |
| Leste | Paranoá, Itapoã, São Sebastião, Jardim Botânico |

- **Ponto de partida da curadoria:** cotas por região proporcionais à população das RAs na [PDAD-A 2024](https://www.ipe.df.gov.br/pdad/), com piso de 15 lugares por região e teto de 40% para o Centro em comer e beber e ao ar livre. O teto não vale para locais de eventos, que são de fato concentrados no Centro. Em cada região entram as feiras e os eventos das administrações regionais que existirem.
- **Escolha dos candidatos:** sorteio dentro de cada estrato (região × categoria), com critérios de exclusão escritos no guia, para que o gosto da equipe não decida o que entra. A descrição segue um modelo fixo.
- **Critério de aceite:** são as cotas que se ajustam ao resultado, não o contrário. A base é aceita pelo teste de cobertura por estrato ("Como vamos validar"), e os 20 lugares de reserva vão para os estratos que falharem.

## Esquema, filtros e texto para o RAG

O esquema completo está em [esquema-base.md](../dados/esquema-base.md). As decisões que ele implementa:

- **Proveniência por campo:** horário, preço, status e atributos têm cada um a sua `fonte` e o seu `verificado_em`.
- **Filtros com "sem informação" (RF-17):**

  | Restrição declarada pela pessoa | Atributo "sim" | "Sem informação" | "Não" |
  |---|---|---|---|
  | Acessibilidade (entrada sem degrau, banheiro adaptado) | Entra | Não entra | Não entra |
  | Alimentar (vegetariano, vegano, sem glúten, sem lactose; lista igual à do perfil) | Entra | Não entra | Não entra |
  | Alergia grave | O app não promete atender: o plano sempre diz "confirme com o lugar" | — | — |

  O horário "aproximado" entra no filtro, com aviso e data; o "vencido" não entra.
- **Texto do embedding:** gerado por modelo a partir dos atributos estruturados mais a descrição curta da equipe. Quando o texto e o atributo divergem, vale o atributo.
- **Onde fica:**
  - A curadoria é feita numa planilha da equipe.
  - Um script valida os campos e barra contatos pessoais. Ele exporta um CSV versionado no repositório, com algumas centenas de linhas, sem dados pessoais, curadores identificados por iniciais e sem o place ID.
  - Os IDs da Google ficam num arquivo separado, fora de qualquer versão que venha a ser publicada.
  - O índice é gerado pelo script e fica fora do git.

## Justificativa e evidências

| Pergunta | Por que esta escolha | Evidência |
|---|---|---|
| 1. Fontes | Guardar só o que a licença permite. A Overture tem licença permissiva por registro e download sem conta. A ODbL e os termos da Google tornariam a base inutilizável fora da equipe | [Termos da Google, 3.2.3](https://cloud.google.com/maps-platform/terms); [ODbL 4.4 e 4.6](https://opendatacommons.org/licenses/odbl/1-0/); [Overture: atribuição](https://docs.overturemaps.org/attribution/); [Termos do Instagram](https://help.instagram.com/581066165581870) |
| 2. API | Status e horário em campos padrão e faixa gratuita suficiente para conferir só os finalistas. As condições evitam as proibições conhecidas, e a TomTom é medida no piloto para evitar dependência | [Preços](https://developers.google.com/maps/billing-and-pricing/pricing); [Termos específicos, 14](https://cloud.google.com/maps-platform/terms/maps-service-terms); [Text Search](https://developers.google.com/maps/documentation/places/web-service/text-search); [Preços da TomTom](https://docs.tomtom.com/pricing) |
| 3. Limites | Hipóteses ligadas à cadência viável; sem evidência externa. Calibração parcial na semana 6 | Medição própria (semana 6) |
| 4. Tamanho | Meta derivada das horas e do tempo medido; distribuição pelo resultado (RNF-13), com a população da PDAD como ponto de partida | [PDAD-A 2024](https://www.ipe.df.gov.br/pdad/); piloto da semana 2 |

## Riscos e limitações

| Risco | Ligação | Mitigação |
|---|---|---|
| Os termos da Google são interpretados contra o nosso uso (diretório, conferência) | R-07 | Condições 1 a 5; nada guardado além do place ID; TomTom e conferência manual prontas pela interface |
| O ADR de mapas escolhe um mapa não Google embutido | R-07 | Condição 1; nesse caso a conferência passa para a TomTom ou para a conferência manual |
| Cobrança no cartão de um membro | R-07, P16 | Cotas diárias por projeto; provedor falso em desenvolvimento; Free Trial, se cobrir a Maps Platform |
| Cota esgotada na demonstração | R-07, RNF-15 | Cota do projeto "plano" folgada; nada de testes na API no dia; o plano segue como "não conferido agora" |
| Preço ou horário errado apresentado como certo | R-03, RNF-03 | Estados por idade; conferência dos finalistas; amostra de 125 itens com intervalo de confiança |
| Evento cancelado ou esgotado depois do último recheque | R-03 | Recheque semanal dos próximos 14 dias; "confirme no link oficial" no plano |
| Base que não atende quem mora longe ou tem pouco dinheiro | R-02, RNF-13 | Teste de cobertura por estrato como critério de aceite; reserva para os estratos que falharem |
| Viés da equipe na escolha e na descrição | R-02 | Sorteio de candidatos por estrato; modelo fixo de descrição; dupla leitura de 10% |
| Dados abertos com cobertura desigual entre RAs | R-02 | Medir candidatos por RA no piloto; completar com OSM consultado à mão e com FSQ OS, se preciso |
| Contatos pessoais vindos dos dados abertos ou do contato direto | R-01, RNF-01 | Lista fechada de campos na importação; guardar só o fato e o canal; curador por iniciais |
| A curadoria consome o tempo do desenvolvimento | P08 | Orçamento de 20 h por semana; meta derivada do tempo medido |
| Restrições alimentares e de acessibilidade com pouca informação | RF-17 | Atributos preenchidos a partir do cardápio; o teste de cobertura inclui salas com essas restrições |

**O que este ADR não resolve:**

- Lotação em tempo real (RF-44 fica "sem informação").
- Fontes de clima e de alertas de transporte (RF-46).
- O GTFS do DF (questão em aberto 8).
- A regra de justiça do ranqueamento (questão 3).

## Como vamos validar

| O que | Como medir | Critério |
|---|---|---|
| Existência (RNF-03) | Lugares de todos os planos dos testes com status ativo por verificação humana de até 60 dias | 100% |
| Exatidão (RNF-03) | Cerca de 125 itens exibidos (horário no dia e na janela do plano, custo por pessoa, status, dados de evento), estratificados por tipo e região. Rodada 1 na semana 3, com as respostas aos pedidos de teste; rodada 2 na semana 6, com os planos dos testes. Conferência na fonte primária, nunca na Google | ≥ 95%, afirmado só se o limite inferior do intervalo de Clopper-Pearson (95%) ficar acima de 95% (125 itens com até 2 erros). Senão, reportar o acerto observado com o intervalo |
| Definição de "correto" | Horário: a resposta do filtro ("aberto em toda a janela do plano?") é a mesma com a fonte primária. Custo: o custo por pessoa exibido fica a até 10% do recalculado com o cardápio vigente. Status: igual ao apurado. Evento: data, horário, local e situação (esgotado, cancelado) iguais | — |
| Calibração | Reconferência de 40 lugares do piloto na semana 6 | Rever um limite se a taxa de erro do estado "exato" passar de 5% |
| Frescor | Itens exibidos nos planos dos testes no estado "exato" | ≥ 90% |
| Cobertura (RF-15, RF-17, RNF-13, RNF-16) | 30 salas simuladas, estratificadas por região e por três faixas de orçamento, algumas com restrições alimentares e de acessibilidade | Em cada estrato, ≥ 70% das salas com pelo menos 2 planos viáveis e nenhum participante com mais de 60 minutos de deslocamento (provisório, alinhar com o ADR de justiça). Em ≥ 90% das salas, pelo menos um candidato viável sem foco em álcool |
| Provedor da API | 20 lugares do piloto conferidos pela Google e pela TomTom, comparados à fonte primária | A Google fica se acertar status e horário em ≥ 80%; senão, a TomTom, se atingir os 80% |
| Custo | Consumo por SKU e por projeto (RNF-15) | Zero cobrança |
| Esforço | Tempo cronometrado por lugar e horas semanais na base | Dentro do orçamento de 20 h por semana |
| Dados pessoais | O script de validação barra campos de contato | Zero campos de contato no CSV |

## Mudanças em outros documentos

- [Requisitos](../produto/requisitos.md) (v0.3.1):
  - **RNF-15:** cache só do que os termos de cada provedor permitem;
  - **RF-37:** pergunta opcional "o lugar estava aberto? o preço bateu?", que só alimenta a fila de reconferência;
  - **questão em aberto 4:** fechada.
- [Mapa da arquitetura](../arquitetura/index.html), aqui e no repositório público: trocar "Respostas de APIs ficam em cache" pela regra acima; registrar a Overture como fonte de candidatos, a Google como conferência sob condições e a curadoria em fases. **Pendente.**
- AGENTS.md: nova pasta `docs/dados/`, com o esquema e o guia de curadoria.
- Futuro ADR de mapas e rotas: respeitar a condição 1 ou trocar o provedor de conferência.

## Perguntas para o grupo

1. Quem cria a conta de faturamento da Google (exige cartão)? Ou o grupo tenta o Free Trial, se ele cobrir a Maps Platform?
2. O grupo aceita o plano sem mapa embutido no MVP, com link para o Google Maps?
3. O grupo aceita 20 h por semana para a base nas semanas 2 a 5, e os donos propostos para cada rotina?
4. O agrupamento das 35 RAs em seis regiões faz sentido?
5. O formulário de hábitos tem dado para definir o que é "barato"? Enquanto não tiver, vale R$ 40 por pessoa.
6. Os testes do MVP terão pessoas de fora da equipe? A base será publicada no fim? (Isso não muda as licenças escolhidas, mas define a atribuição exibida.)

## Referências

- DIEESE. **Pesquisa nacional da cesta básica de alimentos**. Disponível em: https://www.dieese.org.br/cesta/. Acesso em: 3 nov. 2026. (Considerada e descartada para o rolê em casa.)
- FOURSQUARE. **Pricing**; **Places API response fields**; **Usage guidelines**. Disponível em: https://foursquare.com/pricing/ e https://docs.foursquare.com/. Acesso em: 3 nov. 2026.
- GOOGLE. **Google Maps Platform Terms of Service**. Disponível em: https://cloud.google.com/maps-platform/terms. Acesso em: 3 nov. 2026.
- GOOGLE. **Google Maps Platform Service Specific Terms**. Disponível em: https://cloud.google.com/maps-platform/terms/maps-service-terms. Acesso em: 3 nov. 2026.
- GOOGLE. **Google Maps Platform pricing**; **Manage costs**; **Places API usage and billing**; **Place Details (New)**; **Text Search (New)**; **Places API policies**; **Maps URLs**. Disponível em: https://developers.google.com/maps. Acesso em: 3 nov. 2026.
- IBRAM. **Unidades de conservação**. Disponível em: https://www.ibram.df.gov.br/unidades-de-conservacao. Acesso em: 3 nov. 2026.
- INSTAGRAM. **Termos de Uso**. Disponível em: https://help.instagram.com/581066165581870. Acesso em: 3 nov. 2026.
- IPEDF. **Pesquisa Distrital por Amostra de Domicílios (PDAD)**. Disponível em: https://www.ipe.df.gov.br/pdad/. Acesso em: 3 nov. 2026.
- OPEN DATA COMMONS. **Open Database License (ODbL) v1.0**. Disponível em: https://opendatacommons.org/licenses/odbl/1-0/. Acesso em: 3 nov. 2026.
- OVERTURE MAPS FOUNDATION. **Places guide**; **Attribution**. Disponível em: https://docs.overturemaps.org/. Acesso em: 3 nov. 2026.
- SYMPLA. **API docs**. Disponível em: https://developers.sympla.com.br/api-docs. Acesso em: 3 nov. 2026.
- TOMTOM. **Pricing**; **Points of interest search**. Disponível em: https://docs.tomtom.com/. Acesso em: 3 nov. 2026.

## Histórico

| Data | Mudança |
|---|---|
| 2026-11-03 | Versão 1, para crítica |
| 2026-11-03 | Versão 2, aceita. Incorpora a [crítica](revisoes/0004-critica.md): Google só na hora do plano e sob condições, sem lote mensal; projetos e cotas por SKU; casamento confirmado por endereço; Overture como fonte única de candidatos, sem campos do OSM; horizonte do MVP; estados sem lacunas; amostra de 125 itens com intervalo de confiança; meta derivada das horas; cobertura por estrato como critério de aceite; TomTom no piloto; retorno dos usuários e leitura de cardápio como complementos; esquema e guia em documentos próprios |
