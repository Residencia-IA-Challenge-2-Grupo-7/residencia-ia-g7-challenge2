# Crítica do ADR 0004 — Fonte e manutenção da base de lugares e eventos

- **ADR revisado:** [0004-fonte-e-manutencao-da-base.md](../0004-fonte-e-manutencao-da-base.md), versão de 2026-11-03
- **Revisor:** agente Claude (Claude Code), a partir do [prompt de crítica](0004-prompt-critica.md)
- **Data:** 2026-11-03. Fontes externas consultadas nesta data.
- **Escopo:** só aponta problemas. Não reescreve nem defende a decisão. Leitura de termos e licenças não é parecer jurídico.

## 1. Resumo

O ADR está bem estruturado: responde às quatro perguntas com números, separa fonte primária de conferência e trata LGPD e justiça como requisitos. Os números de cota e SKU da Google estão certos, mas o uso que o ADR faz deles não está. Três pontos impedem aceitar o ADR como está. (1) Guardar o resultado da Google e usá-lo para manter o horário "exato" esbarra nos termos da Google Maps Platform, e o ADR não analisa isso. (2) Os termos proíbem usar a Places API junto com um mapa não Google, e o mapa ainda está "a decidir". (3) As travas de custo descritas não existem: as cotas são por método, não por SKU, e alerta de orçamento não limita gasto. Também é grave que a amostra de 30 lugares não sustente a meta de 95% do RNF-03, e que os limites de "aproximado" e a calibração não caibam nas 7 semanas do projeto.

**Cobertura dos itens pedidos**

| Item | Cobertura | Achados |
|---|---|---|
| A1. Decisão clara, com números | Cobre mal: há números, mas os da Pergunta 3 e da Pergunta 4 não têm evidência | C-06, C-13, C-24 |
| A2. Alternativas com critérios iguais; alternativas que faltam | Cobre mal | C-17, C-18, C-19 |
| B1. Cotas e SKUs da Google | Cobre os números; erra o uso (travas, casamento, cobrança por SKU mais alto) | C-03, C-08 |
| B2. Cache e atribuição da Google | Cobre mal | C-01, C-02, C-21 |
| B3. Licenças OSM, Overture, FSQ | Cobre mal | C-09, C-19 |
| B4. Faixa gratuita da Foursquare | Cobre: a incerteza é real | C-17 |
| B5. Termos de Instagram, Sympla, iFood | Cobre; só o do Instagram pôde ser confirmado | Tabela de fatos |
| B6. Agenda cultural e parques do DF | Cobre mal | C-18, tabela de fatos |
| C1. Contradições com requisitos, ADRs, premissas e mapa | Cobre mal | C-01, C-02, C-03, C-12 |
| C2. Requisitos esquecidos | Não cobre | C-10, C-15, C-18 |
| D1. Definição de "correto" | Cobre mal | C-05 |
| D2. Amostra de 30 lugares | Não sustenta a meta | C-04 |
| D3. Deduplicação, place ID, sem cadastro, horários especiais, eventos | Cobre mal | C-07, C-08, C-16, C-19 |
| D4. Limites exato / aproximado / vencido | Cobre mal | C-06 |
| E1. Consumo de chamadas | Cobre mal | C-03 |
| E2. Cota acabando na demonstração | Cobre mal | C-03, C-06 |
| E3. Esforço e donos das rotinas | Cobre mal | C-12 |
| E4. Automatizar ou cortar | Não cobre | C-18, C-19, C-22 |
| F1. Distribuição por região e preço | Cobre mal | C-13 |
| F2. Viés da equipe | Cobre mal | C-13 |
| F3. Dados pessoais | Cobre mal | C-14 |
| F4. RNF-16 (álcool) | Cobre mal | C-20 |
| G1. Esquema para RAG, semana 3 e semana 4 | Cobre mal | C-11, C-15 |
| G2. Campos que faltam | Não cobre | C-15 |
| H1. Template e restrições do desafio | Cobre mal | C-24 |
| H2. Trechos para documento à parte | Não cobre | C-24 |

## 2. Achados

### C-01 · Guardar o resultado da Google e usá-lo como verificação pode violar os termos

- **Gravidade:** bloqueante
- **Seção:** Princípios; Pergunta 2 ("O que guardamos da Google"); Pergunta 3 (justificativa do horário e cadência)
- **Problema:** o ADR afirma que guardar "data e confere/diverge" é compatível com os termos, mas não mostra a análise.
  - Os [Termos da Google Maps Platform](https://cloud.google.com/maps-platform/terms), seção 3.2.3, proíbem: guardar, indexar ou rehospedar conteúdo fora dos serviços (a); qualquer cache além do que os termos específicos permitem (b); e criar conteúdo a partir do conteúdo da Google (c).
  - Os [termos específicos](https://cloud.google.com/maps-platform/terms/maps-service-terms) liberam só o place ID sem prazo (seção A.3) e latitude/longitude por até 30 dias (seção 14.3).
  - O ADR vai além de "conferir". A justificativa dos 30 dias diz que o horário fica "exato" porque o lote mensal da Google o reconfere. Ou seja, a frescura da base passa a derivar da Google. Isso se aproxima do que a seção 3.2.3(c) veda. Nenhum trecho dos termos trata de "verificar a própria base", então a leitura otimista não resolve o risco.
  - Há contradição com o RNF-15 ("guardar em cache as respostas de APIs externas") e com o [mapa da arquitetura](../../arquitetura/index.html) ("Respostas de APIs ficam em cache"). Isso não vale para a Google. Também não vale para a Foursquare em pay-as-you-go, cujas [diretrizes de uso](https://docs.foursquare.com/fsq-developers-places/reference/usage-guidelines) só permitem guardar o `fsq_place_id` e IDs de fotos.
- **Sugestão:**
  1. Tratar a resposta da Google como efêmera: usar na hora do plano e, no lote, só para montar a fila do curador. Não gravar nada além do place ID.
  2. `verificado_em` só muda quando uma pessoa confere na fonte primária (ver C-07).
  3. Se o grupo quiser guardar "confere/diverge", registrar a leitura dos termos no ADR e pedir confirmação ao suporte da Google Maps Platform.
  4. Propor a mudança do RNF-15 e do mapa: cache só do que cada termo permite.
  5. No guia de curadoria, proibir copiar horário, nome ou endereço do app Google Maps. A seção 3.2.3(a)(iii) cita copiar e salvar nomes e endereços como exemplo de violação.

### C-02 · A Places API não pode conviver com um mapa não Google

- **Gravidade:** bloqueante
- **Seção:** Pergunta 2 (decisão); Pergunta 1 (coordenadas de dados abertos)
- **Problema:** a seção 3.2.3(e) dos [Termos](https://cloud.google.com/maps-platform/terms) proíbe usar os serviços principais da Google com ou perto de um mapa não Google no mesmo aplicativo. O exemplo dado é mostrar ou usar conteúdo de Places num mapa não Google. A seção 14.2 dos [termos específicos](https://cloud.google.com/maps-platform/terms/maps-service-terms) repete a regra; a 14.1 permite usar a Places API sem mapa. O [mapa da arquitetura](../../arquitetura/index.html) ainda lista "Mapas e rotas: Google Maps ou OpenStreetMap, a decidir". Se o grupo escolher OpenStreetMap, a conferência pela Google fica em conflito com os termos. A Pergunta 2 depende de uma decisão que ainda não foi tomada, e o ADR não cita essa dependência.
- **Sugestão:** decidir o mapa antes de aceitar a Pergunta 2, ou registrar a regra "se houver mapa não Google, a conferência sai da Google". Uma saída sem conflito é o plano sem mapa embutido, com link para o Google Maps (C-21). Se o mapa for Google, somar o custo dele ao orçamento de cotas.

### C-03 · As travas de custo não funcionam como descritas

- **Gravidade:** bloqueante
- **Seção:** Pergunta 2 ("Como usar a Google dentro da faixa gratuita" e "Travas"); Riscos (cobrança no cartão); Perguntas para o grupo, item 1
- **Problema:**
  - As cotas são por método da API e por projeto, não por SKU ([usage and billing](https://developers.google.com/maps/documentation/places/web-service/usage-and-billing)). Pro e Enterprise saem do mesmo Place Details. A [página de controle de custos](https://developers.google.com/maps/billing-and-pricing/manage-costs) manda basear o limite no SKU de menor cota gratuita e dividir por 31. Para Place Details, isso dá 1.000 ÷ 31 = 32 chamadas por dia no total. A trava "Enterprise em 30 e Pro em 150" não existe.
  - Com uma cota única de cerca de 32 por dia, o lote de 200 leva pelo menos 7 dias, e a conferência na hora do plano disputa a mesma cota. Um teste de carga com 20 salas (RNF-14), a 3 chamadas por plano, já gasta 60.
  - Mesmo com as cotas que o ADR imagina, um lote de 200 num dia estoura as travas de 30 e 150. O ADR não diz como espalhar o lote.
  - Orçamento e alerta de faturamento não limitam o gasto, e o painel pode atrasar até 48 h ([controle de custos](https://developers.google.com/maps/billing-and-pricing/manage-costs)). O "alerta de US$ 1" está listado como trava, mas só avisa.
  - Campos de SKUs diferentes na mesma chamada são cobrados uma vez, no SKU mais alto. Pedir `businessStatus` e `regularOpeningHours` juntos custa 200 Enterprise no lote, e não 200 Pro + 200 Enterprise.
  - Rodar o script do lote algumas vezes durante o desenvolvimento gasta a cota Enterprise do mês: 1.000 chamadas são 5 lotes.
  - A cota diária reinicia à meia-noite do horário do Pacífico, que em novembro é 5h em Brasília. Isso afeta testes feitos à noite.
  - Uma cobrança no cartão de um membro fere a P16 (até R$ 20 por membro).
- **Sugestão:**
  1. Dois projetos na mesma conta de faturamento. Projeto do lote: Place Details travado em 32 por dia, com status e horário num só pedido Enterprise. Projeto da conferência do plano: só campos Pro, travado em 161 por dia (5.000 ÷ 31). Como o uso soma por conta de faturamento ([preços](https://developers.google.com/maps/billing-and-pricing/pricing)), Enterprise só sai do primeiro e Pro só do segundo.
  2. Travar também o Text Search nos dois projetos. Uma máscara de campos errada faz a chamada sair do SKU gratuito de IDs e cair em Text Search Pro (US$ 32 por mil acima da cota).
  3. Provedor falso (mock) no desenvolvimento e nos testes de carga, aproveitando a interface trocável.
  4. Reservar cota para o dia da demonstração e dizer o que a tela mostra quando a cota acaba (ver C-06).
  5. Avaliar o Free Trial do Google Cloud: pela [página oficial](https://docs.cloud.google.com/free/docs/free-cloud-features), a conta é encerrada sem cobrança se ninguém fizer upgrade. A página não confirma que o crédito cobre a Maps Platform. Conferir antes de contar com isso.

### C-04 · A amostra de 30 lugares não sustenta "≥ 95% corretos"

- **Gravidade:** importante
- **Seção:** Como vamos validar (exatidão de horário e preço); RNF-03
- **Problema:**
  - Com 30 itens e nenhum erro, o limite inferior de confiança é 90,5% (binomial exato, 95%, unilateral). Com 1 erro, 85,1%. Nem 30 de 30 permite afirmar 95%.
  - Para afirmar ≥ 95% com 95% de confiança são precisos 59 itens sem erro, 93 com até 1 erro, 124 com até 2 ou 153 com até 3 (cálculo do revisor, Clopper-Pearson).
  - A unidade é "lugar", mas um lugar tem 7 horários e 3 a 5 preços. Erros do mesmo lugar andam juntos, e a amostra efetiva é menor.
  - O RNF-03 fala dos preços e horários apresentados. A amostra sai da base inteira, sem peso para o que aparece nos planos.
  - "Mensal" dá uma ou duas rodadas no projeto todo.
- **Sugestão:** unidade = item exibido num plano (horário no dia e na janela do plano; custo por pessoa). Amostra de cerca de 125 itens, estratificada por tipo e região, numa rodada na semana 3 (que também serve à comparação LLM × RAG) e outra na semana 6. Reportar o acerto com o intervalo de confiança. Se não houver tempo para 125, dizer que a meta é de acerto observado, não garantido.

### C-05 · As definições de "correto" não medem o erro que o usuário sofre

- **Gravidade:** importante
- **Seção:** Como vamos validar (critérios de horário e preço)
- **Problema:**
  - Tolerância de 30 minutos na abertura e no fechamento é larga para um filtro duro (RF-17). Se o lugar fecha às 22h e a base diz 22h30, um plano até 22h15 passa no filtro, e o dado ainda conta como "correto".
  - "Item de referência com até 10%" mede o item. O plano mostra custo por pessoa, calculado de vários itens e somado ao transporte.
  - Não há critério para status, evento (data, horário, preço, cancelamento) nem atributos.
  - A fórmula do custo típico por pessoa não está escrita (quais itens, couvert, taxa de serviço), embora o RNF-04 exija cálculo determinístico.
- **Sugestão:** horário correto = a resposta do filtro ("aberto em toda a janela do plano?") é a mesma com a fonte primária. Preço correto = custo por pessoa exibido a até 10% do recalculado com o cardápio vigente. Definir critérios para status e evento. Escrever a fórmula do custo por pessoa no guia de curadoria.

### C-06 · Os limites de "aproximado" e a calibração não cabem nas 7 semanas

- **Gravidade:** importante
- **Seção:** Pergunta 3 (tabela de estados, justificativa e cadência); Como vamos validar (calibração e frescor)
- **Problema:**
  - Um dado curado entre as semanas 2 e 5 terá no máximo cerca de 5 semanas na semana 7. Preço (exato até 60 dias), taxa de parque (90) e atributos (180) nunca saem do "exato" durante o projeto. A calibração por idade não terá dado velho para medir, e a rodada trimestral de preços nunca acontece.
  - Depois do MVP, a meta "frescor ≥ 85% em qualquer momento" conflita com a cadência: preço exato por 60 dias, numa rodada a cada 90, fica exato só 2/3 do tempo.
  - A tabela tem um buraco: status conferido entre 31 e 60 dias não está em nenhum estado.
  - "Exato" para status exige conferência na hora do plano. Se a API falhar ou a cota acabar (caso previsto no ADR), o status também não tem estado, e o ADR não diz o que a tela mostra.
  - Nenhum limite tem fonte. "Cardápio muda em degraus" é plausível, mas não tem evidência.
- **Sugestão:** declarar o horizonte do MVP e marcar como pós-MVP o que não acontece nele. Para calibrar, reconferir na semana 6 uma parte dos 60 lugares da semana 2: isso mede o erro com cerca de 4 semanas de idade. Preencher o estado do status entre 31 e 60 dias e o caso "sem resposta da API" (por exemplo, "não conferido agora", visível ao usuário). Trocar a meta de frescor por uma compatível com a cadência.

### C-07 · O horário não tem rotina humana e ignora horários especiais

- **Gravidade:** importante
- **Seção:** Pergunta 3 (cadência); Fontes por tipo de dado (horário)
- **Problema:** na cadência, ninguém reconfere horário na fonte primária; só existem o lote da Google e a fila de divergências. Se a C-01 levar a não usar a Google como verificação, o horário vence aos 90 dias sem dono. "Horário especial entra como exceção datada", mas ninguém tem a tarefa de registrar feriados, e há feriado dentro das 7 semanas (20/11, por exemplo). A conferência na hora do plano olha só o status (Pro). O campo que traz dias especiais, `currentOpeningHours`, é Enterprise ([campos por SKU](https://developers.google.com/maps/documentation/places/web-service/data-fields)).
- **Sugestão:** criar a rotina de horário (quem, quando, quanto tempo). Antes de cada feriado, conferir os lugares que mais entram em planos. Quando a data do plano for feriado, conferir o horário dos finalistas (poucas chamadas Enterprise).

### C-08 · O casamento com o place ID é cego, e ID obsoleto vira "a API falhou"

- **Gravidade:** importante
- **Seção:** Pergunta 2 (linha "Casar o lugar com um place ID"; "Mudança de horário entre a verificação e o rolê")
- **Problema:**
  - Text Search só com `places.id` não devolve nome nem endereço ([Text Search](https://developers.google.com/maps/documentation/places/web-service/text-search)). Sem outra chamada, não dá para saber se o ID é do lugar certo. Redes com várias unidades e nomes parecidos geram casamento errado, e a conferência passa a validar o lugar errado.
  - A Google avisa que place IDs mudam e recomenda atualizar os que têm mais de 12 meses. Um ID obsoleto devolve `NOT_FOUND` ([Place IDs](https://developers.google.com/maps/documentation/places/web-service/place-id)). Pelo ADR, falha da API mantém o lugar no plano. Um lugar que mudou ou fechou continua aparecendo.
- **Sugestão:** casar com Text Search (IDs) e confirmar com Place Details Essentials (`formattedAddress` e `location`, 10.000 grátis por mês), comparando com a coordenada aberta. A coordenada da Google é descartada na hora (C-01). Guardar a confiança do casamento. Tratar `NOT_FOUND` como "vai para o curador", não como falha. Usar `movedPlace` e `movedPlaceId`, que vêm no SKU gratuito de IDs.

### C-09 · A leitura da ODbL está incompleta

- **Gravidade:** importante
- **Seção:** Fontes por tipo de dado (licenças); Riscos (base derivada do OSM)
- **Problema:**
  - O ADR diz "compartilhar a base derivada se ela for publicada". A [ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/) vai além. Pelas seções 4.4(c) e 4.6, quem usa publicamente um resultado (Produced Work) gerado de uma base derivada deve oferecer a base derivada, ou um arquivo com as alterações e os dados acrescentados. "Publicamente" é para qualquer pessoa fora da equipe.
  - Se a base mistura coordenadas do OSM com horários e preços da equipe, os testes do MVP com amigos e a demonstração já podem acionar essa obrigação.
  - Se a mesma base tiver `google_place_id`, oferecê-la sob ODbL redistribui conteúdo da Google, o que a seção 3.2.3(a) dos [Termos](https://cloud.google.com/maps-platform/terms) veda.
  - A atribuição precisa dizer que o dado está sob a ODbL, não só citar o OSM ([copyright do OSM](https://www.openstreetmap.org/copyright)).
- **Sugestão:** escolher e registrar uma saída. (a) OSM só para descobrir candidatos, sem guardar campo do OSM; a coordenada vem de fonte permissiva (Overture ou FSQ OS Places). (b) Aceitar a ODbL e separar as tabelas, com os IDs externos fora da parte oferecida, conferindo as diretrizes da OSMF sobre base coletiva e sobre parte "substancial". Corrigir o texto de atribuição nos dois casos.

### C-10 · Filtros duros sem regra para "sem informação" e com atributos pobres

- **Gravidade:** importante
- **Seção:** Esquema mínimo (`atributos`); Fontes por tipo de dado (atributos); tabela de requisitos do Contexto (RF-17)
- **Problema:**
  - O RF-17 trata horário, restrições alimentares e acessibilidade como filtros duros. O esquema só tem `vegetariano` e `acessível` (sim ou não), e cada atributo pode ficar "sem informação" (RF-44).
  - O ADR não diz o que o filtro faz com "sem informação" nem com horário "aproximado". Excluir encolhe a base; incluir viola a restrição declarada.
  - "Acessível" não diz se há entrada sem degrau, banheiro adaptado ou lugar para sentar.
  - Vegano, sem glúten, sem lactose e alergias não têm campo. O RF-01 coleta essas restrições no perfil, mas a base não tem como atendê-las.
- **Sugestão:** regra por restrição. Exemplo: quem declarou necessidade de acessibilidade só recebe lugares confirmados; os demais veem "não confirmado". Lista fechada de restrições alimentares igual à do perfil (RF-01). Acessibilidade em subcampos. A Google tem `accessibilityOptions` no SKU Pro, útil para conferir, mas não para guardar (C-01).

### C-11 · A base não está ligada à comparação LLM × RAG da semana 3

- **Gravidade:** importante
- **Seção:** Pergunta 4 (marcos); Como vamos validar; Esquema
- **Problema:**
  - O [mapa da arquitetura](../../arquitetura/index.html) prevê de 20 a 30 pedidos de teste com resposta esperada, escritos antes de montar a base, para mostrar que dados ela precisa ter. O ADR não cita esses pedidos e define a composição da base sem eles.
  - Na comparação, o LLM puro vai sugerir lugares fora da base. Medir se existem exige conferência, e o ADR não diz como nem quanto custa.
  - A seção 3.2.3(c)(vii) dos [Termos da Google](https://cloud.google.com/maps-platform/terms) proíbe usar o conteúdo da Google para testar ou validar modelos de IA. A Google não pode ser o juiz dessa comparação.
  - Falta congelar uma versão da base para comparar LLM e RAG sobre o mesmo dado.
- **Sugestão:** escrever os pedidos de teste agora e derivar deles a cobertura mínima por tipo e região. Protocolo manual para julgar os lugares do LLM puro (fonte primária, dois avaliadores). Marcar no git a versão do CSV usada na semana 3.

### C-12 · O esforço está subestimado e as rotinas não têm dono

- **Gravidade:** importante
- **Seção:** Esforço estimado; Pergunta 3 (cadência); Riscos (curadoria consome tempo)
- **Problema:**
  - O corte não reduz o esforço: 150 lugares × 25 min = 62,5 h, mais que as 50 h do plano. Para caber em 50 h a 25 min por lugar, a meta seria 120.
  - Ficam fora da conta: escrever a `descricao`, montar o pipeline de dados abertos e a deduplicação, a dupla leitura de 10%, a amostra de validação (C-04), os eventos (C-16), o catálogo do rolê em casa e o próprio guia de curadoria.
  - "Cada membro responde por um grupo de RAs", mas são cerca de seis regiões para cinco pessoas.
  - A curadoria inicial (semanas 2 a 5) coincide com RAG, comparação, multiagentes e multimodalidade ([roadmap](../../desafio/challenge-2.md)). As horas saem das cerca de 100 h semanais da equipe (P08), sem dizer de qual entrega.
  - Nenhuma rotina tem dono com nome, embora a [ata de 29/10](../../atas/2026-10-29.md) tenha duas engenheiras de dados.
- **Sugestão:** orçamento de horas por semana para a base, com o dono de cada rotina. Meta derivada: lugares = horas disponíveis ÷ tempo medido no piloto. Pôr as tarefas omitidas na conta.

### C-13 · A distribuição "justa" não tem justificativa e mede o insumo, não o resultado

- **Gravidade:** importante
- **Seção:** Divisão por tipo; Distribuição pelo DF; Riscos (base concentrada; viés da equipe); Como vamos validar (cobertura)
- **Problema:**
  - O teto de 40% para o Plano Piloto e os Lagos, o piso de 15 por região e o corte de R$ 40 por pessoa não têm fonte nem conta.
  - O teto vale para a base toda. Os locais de evento citados (CCBB, Caixa Cultural, Complexo Cultural da República, Cine Brasília, Clube do Choro) ficam quase todos no Plano Piloto. Não há regra por tipo.
  - A justiça do RF-19 é sobre o tempo e o custo de cada pessoa. Um lugar central pode ser o mais justo para um grupo de Samambaia e Planaltina. Percentual de lugares por região não garante isso.
  - O orçamento do RF-11 inclui transporte. Quem paga ônibus de ida e volta tem menos de R$ 40 para comer. O corte de "barato" não usa os dados do formulário de hábitos.
  - O agrupamento de exemplo deixa de fora RAs como São Sebastião, Itapoã, SCIA/Estrutural, Sol Nascente/Pôr do Sol e Jardim Botânico.
  - A edição mais recente da PDAD é a PDAD-A 2024 ([IPEDF](https://www.ipe.df.gov.br/pdad/)); o ADR diz "a conferir".
  - "≥ 80% das salas com 2 planos viáveis" é uma média. Pode esconder 0% nas salas de baixo orçamento da periferia.
  - Viés: começar pelos dados abertos ajuda, mas a escolha entre candidatos e a `descricao` continuam com o gosto da equipe. "Registrar quem curou" rastreia, não mitiga. A cobertura dos dados abertos pode também ser desigual entre RAs, e isso não é medido.
- **Sugestão:** trocar os percentuais por uma meta de resultado: em cada estrato região × faixa de orçamento, pelo menos N planos viáveis com tempo máximo de deslocamento X, fixados no teste de cobertura. Usar a PDAD-A 2024 para população e renda. Medir no piloto quantos candidatos abertos existem por RA. Sortear candidatos dentro de cada estrato, com critérios de exclusão escritos, e escrever as descrições a partir de um modelo fixo.

### C-14 · Os dados abertos trazem contatos pessoais

- **Gravidade:** importante
- **Seção:** O que fica de fora (dados pessoais); Riscos (MEIs)
- **Problema:**
  - O [esquema do FSQ OS Places](https://docs.foursquare.com/data-products/docs/places-os-data-schema) tem telefone, e-mail, Instagram, Facebook e Twitter. O [guia de Places da Overture](https://docs.overturemaps.org/guides/places/) cita telefones, e-mails e redes sociais.
  - Em pequenos negócios e MEIs, o telefone costuma ser o celular do dono, e o nome comercial pode ser o nome da pessoa.
  - O ADR promete "só nome comercial e canal público", mas não diz como o pipeline barra esses campos.
  - "Contato direto" como fonte de horário implica falar com o dono por WhatsApp, sem regra sobre o que se guarda.
  - `curador` e `conferido_por` põem nomes da equipe num CSV versionado.
- **Sugestão:** lista de campos permitidos na importação; nunca importar telefone, e-mail ou rede social. Regra para o "contato direto": só canal comercial, sem guardar o número. Iniciais ou pseudônimo em `curador`. Incluir tudo isso no checklist de LGPD do RNF-01.

### C-15 · O esquema não sustenta o custo real nem a busca

- **Gravidade:** importante
- **Seção:** Esquema mínimo de um lugar
- **Problema:** faltam campos que os requisitos pedem.
  - Endereço legível e link público do lugar. O plano diz "onde", e o RF-27 pede link do mapa.
  - `fsq_place_id` em `ids_externos`, embora a FSQ seja fonte de candidatos e a Foursquare seja a reserva.
  - Couvert artístico, taxa de serviço e consumação mínima, que mudam o custo por pessoa em bares (RF-15).
  - Meia-entrada e ingresso esgotado nos eventos.
  - Itens para levar (RF-15), por tipo de lugar. Exemplo: água e protetor no parque.
  - Formato dos horários: intervalos que passam da meia-noite e fuso.
  - Para o RAG, o texto do embedding é só a `descricao`. Se ela disser "animado" e o atributo disser "ruído baixo", não há regra de precedência.
  - Estacionamento, distância da estação e capacidade podem ser calculados (GTFS, coordenada) ou ficar para depois. O ADR não diz.
- **Sugestão:** completar o esquema e levá-lo para um documento próprio (C-24). Gerar o texto do embedding a partir de um modelo com atributos e descrição; atributo estruturado vence o texto.

### C-16 · Eventos: rotina subestimada e estados faltando

- **Gravidade:** importante
- **Seção:** Pergunta 3 (evento: 7 e 21 dias; cadência de 2 h); Pergunta 4 (40 a 80 eventos)
- **Problema:**
  - "Exato até 7 dias" com rodada semanal deixa o estoque no limite. Qualquer atraso na rodada põe os eventos em "aproximado".
  - Para manter 40 a 80 eventos exatos, cada um é rechecado toda semana até acontecer. Com 60 eventos e 2 minutos por recheque, as 2 h da cadência acabam só no recheque, antes de cadastrar os novos.
  - Não há estado para ingresso esgotado, troca de lote ou mudança de local.
  - Cancelamento depende só do recheque semanal. A Google não cobre eventos, então não há conferência na hora do plano.
- **Sugestão:** rechecar só os eventos dos próximos 10 a 14 dias. Conferir à mão o evento finalista antes de mostrar o plano, ou exibir "confirme no link". Campos `esgotado` e `lote`. Medir o tempo no piloto.

### C-17 · As APIs alternativas não foram comparadas com os mesmos critérios nem medidas

- **Gravidade:** importante
- **Seção:** Pergunta 2 (opções e decisão)
- **Problema:**
  - "Melhor cobertura de status e horário no Brasil (a medir)" é a razão da escolha, mas a medição não está em "Como vamos validar".
  - A Foursquare é uma reserva fraca. Na [página de preços](https://foursquare.com/pricing/), a faixa gratuita do Pro aparece como 500 e como 10.000 chamadas. Pelos [campos de resposta](https://docs.foursquare.com/fsq-developers-places/reference/response-fields), horário (`hours`) é Premium, sem faixa gratuita. Em pay-as-you-go, só o ID pode ser guardado (C-01).
  - Faltou a TomTom. A [tabela de preços](https://docs.tomtom.com/pricing) dá 2.500 chamadas grátis por mês na Search API e 5.000 no Places Search, sem cartão. A [busca de POI](https://docs.tomtom.com/search-api/documentation/search-service/points-of-interest-search) devolve horário dos próximos 7 dias. Os termos de cache não foram encontrados.
  - O FSQ OS Places, aberto, já traz `date_closed` e `unresolved_flags` (inclusive "fechado"), úteis para status sem API.
  - Se o relatório publicar uma comparação de exatidão da Google, a seção 3.2.4 dos [Termos](https://cloud.google.com/maps-platform/terms) exige publicar o necessário para reproduzir o teste.
- **Sugestão:** uma tabela com os mesmos critérios para todas: cobertura medida em 20 lugares do piloto, campos de status e horário, o que pode ser guardado, faixa gratuita, cartão e regra de mapa. Medir Google e TomTom no piloto. Usar o `date_closed` da FSQ como primeiro filtro de status.

### C-18 · Faltam alternativas para manter a base viva

- **Gravidade:** importante
- **Seção:** Pergunta 1 (opções); Pergunta 3 (cadência)
- **Problema:** o ADR só considera a curadoria da equipe e APIs. Ficaram de fora:
  - retorno dos usuários no fluxo pós-rolê (RF-36 e RF-37): "o lugar estava aberto? o preço bateu?". É conferência grátis e liga a base ao RF-38;
  - contato com alguns lugares parceiros, com um formulário para o próprio estabelecimento atualizar horário e preço;
  - agendas institucionais (Sesc-DF, CCBB, Caixa Cultural) como fonte de eventos com rotina própria. Não foi possível confirmar se existe uma instância de Mapas Culturais do DF com API (tabela de fatos);
  - a multimodalidade da semana 5 aplicada à curadoria: ler o cardápio em PDF ou foto e propor os itens de referência para o curador confirmar.
- **Sugestão:** incluir essas opções na Pergunta 1, com prós e contras. No mínimo, adotar o retorno dos usuários como sinal para a fila do curador (sem dados pessoais) e a leitura de cardápio como automação.

### C-19 · Três fontes abertas multiplicam o trabalho sem ganho claro

- **Gravidade:** importante
- **Seção:** Fontes por tipo de dado (lista de candidatos); Pergunta 1 (opção C)
- **Problema:**
  - OSM, Overture e FSQ OS Places juntos exigem deduplicar e casar registros de três esquemas.
  - A [documentação da Overture](https://docs.overturemaps.org/guides/places/) avisa que o tema Places tem duplicatas, muito lixo e baixa completude dos atributos.
  - O FSQ OS Places agora exige conta no Places Portal e acesso por catálogo Iceberg ([acesso](https://docs.foursquare.com/data-products/docs/access-fsq-os-places)).
  - A Overture tem licença por fonte (CDLA-Permissive-2.0, Apache-2.0 e CC0), cada uma com atribuição própria ([atribuição](https://docs.overturemaps.org/attribution/)).
  - Para 200 lugares, o custo de juntar três fontes é alto. A opção D foi descartada também por "não ter registro auditável", mas o "contato direto" volta como fonte primária.
- **Sugestão:** uma fonte principal de descoberta (FSQ OS Places, pelo `date_closed`, ou OSM, pelas tags) e as outras só para cobrir buracos, sem merge automático. Decidir no piloto, contando quantos candidatos úteis cada fonte dá por RA.

### C-20 · A regra de 40% sem foco em álcool não garante o RNF-16

- **Gravidade:** importante
- **Seção:** Divisão por tipo (comer e beber fora)
- **Problema:** o RNF-16 pede uma opção sem foco em álcool sempre que houver uma viável, plano a plano. Um percentual na base não garante isso num sábado à noite numa região com poucos lugares. "Foco em álcool" não tem definição (boteco com cozinha conta?). Eventos e casas de show não têm o atributo.
- **Sugestão:** definir o atributo no guia. Medir no teste de cobertura em quantas salas simuladas existe pelo menos um plano viável sem foco em álcool. Aplicar o atributo também a eventos.

### C-21 · Link do mapa e atribuição

- **Gravidade:** menor
- **Seção:** Fontes por tipo de dado (fotos); Pergunta 2 (exibição)
- **Problema:** `googleMapsUri` é campo Pro e não pode ser guardado. Mostrá-lo em todo plano exige uma chamada por lugar. As [Maps URLs](https://developers.google.com/maps/documentation/urls/get-started) não exigem chave e aceitam `query_place_id`. A [política da Places API](https://developers.google.com/maps/documentation/places/web-service/policies) pede o logo do Google Maps sempre que possível e aceita o texto só quando falta espaço. O ADR prevê só o texto.
- **Sugestão:** montar o link com Maps URLs (`query` + `query_place_id`). Usar o logo onde aparecer conteúdo da Google.

### C-22 · Rolê em casa: a cesta do DIEESE não serve

- **Gravidade:** menor
- **Seção:** Fontes por tipo de dado (itens do rolê em casa); Pergunta 3 (itens: 30 e 90 dias)
- **Problema:** a [cesta básica do DIEESE](https://www.dieese.org.br/cesta/) é de alimentos básicos (carne, leite, feijão, arroz, pão, café e outros). Não tem bebida, carvão, petisco nem descartáveis. Na consulta, Brasília aparece com a marca "(11/2012)", e não ficou claro se a série continua. O catálogo exige coleta mensal de preços, que não está na cadência. O RF-20 é Should.
- **Sugestão:** tirar o catálogo da base do MVP, ou usar faixas de preço por item sem coleta mensal, sempre marcadas como estimativa.

### C-23 · O marco da semana 2 depende de coisas que ainda não existem

- **Gravidade:** menor
- **Seção:** Pergunta 4 (marcos)
- **Problema:** 60 lugares no fim da semana 2 pressupõem esquema, guia de curadoria e conta da Google prontos. O ADR ainda é proposta, o guia não existe e a conta de faturamento está em aberto. O piloto que mede o tempo por lugar é o mesmo que precisa entregar os 60.
- **Sugestão:** piloto de 20 lugares com o esquema provisório, medir o tempo e ajustar. Os 60 passam a ser meta da semana 3.

### C-24 · Forma do ADR

- **Gravidade:** menor
- **Seção:** documento inteiro
- **Problema:**
  - Falta a seção "Justificativa e evidências" do [template](../0000-template.md). As justificativas estão espalhadas, e várias decisões não citam evidência: os números da Pergunta 4, os limites da Pergunta 3 e a "melhor cobertura no Brasil".
  - As referências só cobrem a Google. Licenças, termos de plataformas, PDAD e DIEESE ficam sem referência.
  - A nota "a versão vigente das regras de cache de coordenadas ainda precisa ser conferida" já pode ser fechada: são 30 dias (seção 14.3 dos termos específicos).
  - Esquema, cadência e regras de curadoria são operação, não decisão, e incham o ADR (251 linhas).
  - O ADR diz que fecha a questão em aberto 4, mas implica mudanças no RNF-15 e no mapa da arquitetura que não lista.
- **Sugestão:** seção de justificativa com fontes por pergunta. Mover o esquema e o guia de curadoria para documentos próprios (por exemplo, `docs/dados/esquema-base.md` e `docs/dados/guia-curadoria.md`, com a tabela do AGENTS.md atualizada). Listar os requisitos e documentos que mudam.

## 3. Tabela de fatos verificados

Consulta em 03/11/2026. "Confirmado" quer dizer que a fonte diz o mesmo que o ADR; "divergente", que diz outra coisa; "não verificável", que a fonte não abriu ou não responde.

| Fato | O que o ADR diz | O que a fonte diz | Link | Situação |
|---|---|---|---|---|
| Cota de Text Search Essentials (IDs Only) | Ilimitada | Ilimitada | [Preços](https://developers.google.com/maps/billing-and-pricing/pricing) | Confirmado |
| Cota de Place Details Pro | 5.000 por mês | 5.000 por mês; US$ 17 por mil acima | [Preços](https://developers.google.com/maps/billing-and-pricing/pricing) | Confirmado |
| Cota de Place Details Enterprise | 1.000 por mês | 1.000 por mês; US$ 20 por mil acima | [Preços](https://developers.google.com/maps/billing-and-pricing/pricing) | Confirmado |
| SKU de `businessStatus` e `displayName` | Pro | Pro | [Campos por SKU](https://developers.google.com/maps/documentation/places/web-service/data-fields) | Confirmado |
| SKU de `regularOpeningHours` | Enterprise | Enterprise; `currentOpeningHours` também | [Campos por SKU](https://developers.google.com/maps/documentation/places/web-service/data-fields) | Confirmado |
| Chamada com campos de SKUs diferentes | Lote tratado como 200 Pro + 200 Enterprise | Cobrada uma vez, no SKU mais alto | [Usage and billing](https://developers.google.com/maps/documentation/places/web-service/usage-and-billing) | Divergente |
| O que o Text Search só com ID devolve | Basta para "casar o lugar" | Só ID, nome de recurso, atribuições, alerta e `movedPlace`; nome e endereço exigem SKU Pro | [Text Search](https://developers.google.com/maps/documentation/places/web-service/text-search) | Divergente |
| Cota diária por SKU | "Enterprise em 30 e Pro em 150 por dia" | Cota por método e por projeto; limite baseado no SKU de menor cota | [Controle de custos](https://developers.google.com/maps/billing-and-pricing/manage-costs) | Divergente |
| Alerta de faturamento como trava | "Alerta de US$ 1" listado como trava | Orçamento e alerta não limitam o uso; atraso de até 48 h | [Controle de custos](https://developers.google.com/maps/billing-and-pricing/manage-costs) | Divergente |
| Cache do place ID | Sem prazo | Sem prazo; recomenda atualizar IDs com mais de 12 meses (grátis só com o campo ID); ID obsoleto dá `NOT_FOUND` | [Termos específicos](https://cloud.google.com/maps-platform/terms/maps-service-terms), [Place IDs](https://developers.google.com/maps/documentation/places/web-service/place-id) | Confirmado |
| Cache de latitude e longitude | "Ainda precisa ser conferida" | Até 30 dias corridos (seção 14.3) | [Termos específicos](https://cloud.google.com/maps-platform/terms/maps-service-terms) | Confirmado (fecha a pendência) |
| Guardar "data e confere/diverge" da Google | Compatível com a política | Termos proíbem guardar fora dos serviços, cache não previsto e criar conteúdo a partir do conteúdo da Google; nada explícito sobre verificar base própria | [Termos, 3.2.3](https://cloud.google.com/maps-platform/terms) | Não verificável (risco alto) |
| Places com mapa não Google | Não trata | Proibido (3.2.3(e) e 14.2); sem mapa é permitido (14.1) | [Termos](https://cloud.google.com/maps-platform/terms), [Termos específicos](https://cloud.google.com/maps-platform/terms/maps-service-terms) | Fato novo, não tratado |
| Conteúdo da Google para testar modelos de IA | Não trata | Proibido testar, validar ou ajustar modelos de IA com o conteúdo (3.2.3(c)(vii)) | [Termos](https://cloud.google.com/maps-platform/terms) | Fato novo, não tratado |
| Atribuição | Texto "Google Maps" | Logo sempre que possível; texto só sem espaço; crédito ao autor em fotos e avaliações | [Políticas da Places API](https://developers.google.com/maps/documentation/places/web-service/policies) | Divergente (parcial) |
| Link do mapa | `googleMapsUri` | Campo Pro; Maps URLs não exigem chave e aceitam `query_place_id` | [Campos por SKU](https://developers.google.com/maps/documentation/places/web-service/data-fields), [Maps URLs](https://developers.google.com/maps/documentation/urls/get-started) | Confirmado, com alternativa melhor |
| Free Trial do Google Cloud | Não trata | US$ 300 por 90 dias; sem upgrade manual a conta fecha sem cobrança; a página não confirma cobertura da Maps Platform | [Free Trial](https://docs.cloud.google.com/free/docs/free-cloud-features) | Não verificável (cobertura de Maps) |
| ODbL (OSM) | Citar a fonte; compartilhar a base derivada se publicada | Uso público de resultado de base derivada já obriga a oferecer a base (4.4(c), 4.6); aviso deve citar a ODbL | [ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/), [Copyright OSM](https://www.openstreetmap.org/copyright) | Divergente |
| Licença de Overture Places | CDLA-Permissive-2.0 | CDLA-Permissive-2.0 na maior parte, Apache-2.0 (Foursquare) e CC0 (AllThePlaces) conforme a fonte; sem dados do OSM; aviso de duplicatas e baixa completude | [Guia de Places](https://docs.overturemaps.org/guides/places/), [Atribuição](https://docs.overturemaps.org/attribution/) | Divergente (parcial) |
| Licença de FSQ OS Places | Apache 2.0 | Apache 2.0; exige conta no Places Portal; tem telefone, e-mail e redes; não tem horário | [Esquema](https://docs.foursquare.com/data-products/docs/places-os-data-schema), [Acesso](https://docs.foursquare.com/data-products/docs/access-fsq-os-places) | Confirmado |
| Faixa gratuita da Foursquare Places API | Incerta, entre 500 e 10.000 | A mesma página mostra 0 a 500 na tabela e "até 10.000" no texto; horário é Premium, sem faixa grátis; em pay-as-you-go só o ID pode ser guardado | [Preços](https://foursquare.com/pricing/), [Campos](https://docs.foursquare.com/fsq-developers-places/reference/response-fields), [Diretrizes](https://docs.foursquare.com/fsq-developers-places/reference/usage-guidelines) | Confirmado (a contradição é da fonte) |
| Faixa gratuita da TomTom | Não trata | Search API: 2.500 por mês; Places Search: 5.000; sem cartão; horário dos próximos 7 dias na busca de POI | [Preços](https://docs.tomtom.com/pricing), [POI Search](https://docs.tomtom.com/search-api/documentation/search-service/points-of-interest-search) | Fato novo |
| Faixa gratuita da HERE | Não trata | Página de preços só tem "fale conosco" | [Preços HERE](https://www.here.com/get-started/pricing) | Não verificável |
| Termos do Instagram | Proíbem coleta automatizada | Proíbem coletar informações de forma automatizada sem permissão expressa; leitura manual não é vedada no texto | [Termos de Uso](https://help.instagram.com/581066165581870) | Confirmado |
| API da Sympla | Voltada a organizadores | Exposta para produtores, com token gerado na conta do produtor | [Contrato da API](https://developers.sympla.com.br/api-docs) | Confirmado |
| Termos da Sympla sobre coleta automatizada | Proíbem raspagem | Os Termos Gerais definem "Crawler/Spider", mas a cláusula de proibição não foi localizada; a Política de Propriedade Intelectual não foi lida | [Termos Gerais](https://termos-e-politicas.sympla.com.br/hc/pt-br/articles/44293992401300-Termos-de-Uso-Gerais) | Não verificável |
| Termos do iFood | Proíbem raspagem | Página protegida por verificação anti-robô; não foi lida | [Termos](https://www.ifood.com.br/termos) | Não verificável |
| Termos do TripAdvisor | Proíbem raspagem | Não consultado | — | Não verificável |
| API ou dados abertos de agenda cultural do DF | Não encontramos (a confirmar) | Site da Secec sem agenda estruturada nem API; o portal de dados do DF não listou conjuntos (página carregada por script); endereços testados de Mapas Culturais do DF com certificado vencido | [Secec](https://www.cultura.df.gov.br/), [Dados DF](https://dados.df.gov.br/) | Não verificável |
| Lista oficial de parques | Sites do Ibram e outros | O Ibram publica tabela de unidades de conservação para download (agosto de 2026); não há horário por parque | [Ibram](https://www.ibram.df.gov.br/unidades-de-conservacao) | Confirmado (parcial) |
| PDAD | "PDAD, a conferir" | Edição mais recente: PDAD-A 2024; a de 2021 cobriu 33 RAs | [IPEDF](https://www.ipe.df.gov.br/pdad/) | Divergente (atualizar) |
| Cesta básica do DIEESE em Brasília | Fonte de preços do rolê em casa | Cesta de alimentos básicos; Brasília aparece como "(11/2012)" sem explicação | [DIEESE](https://www.dieese.org.br/cesta/) | Não verificável (série ativa?) |

## 4. Perguntas que só o grupo pode responder

1. O app terá mapa embutido? Google ou OpenStreetMap? A resposta decide se a Google pode ser a API de conferência (C-02).
2. Os testes do MVP terão usuários fora da equipe? A base ou o repositório serão públicos no fim? Isso decide a obrigação da ODbL (C-09).
3. Quem assume o risco da conta de faturamento? O grupo aceita o Free Trial, que fecha sem cobrança, se ele cobrir a Maps Platform (C-03)?
4. Quantas horas por semana a equipe aceita tirar do desenvolvimento para a base, e quem é dono de cada rotina (C-12)?
5. A meta de 95% do RNF-03 vale para a base toda ou para o que aparece nos planos? O grupo aceita uma amostra de cerca de 125 itens (C-04)?
6. A base precisa continuar viva depois da semana 7? Se não, as rodadas trimestrais e os limites longos saem do MVP (C-06).
7. Quais restrições alimentares e de acessibilidade o MVP promete filtrar de verdade (C-10)?
8. O que é "barato" para o público? O formulário de hábitos tem dados para isso (C-13)?
9. Quais RAs entram em cada região, e o que justifica o teto de 40% e o piso de 15 (C-13)?
10. O que conta como "foco em álcool" (C-20)?
11. O rolê em casa (RF-20, Should) entra na base do MVP (C-22)?
12. O grupo aceita contatar estabelecimentos ou pedir retorno dos usuários depois do rolê como fonte de conferência (C-18)?

## 5. Respostas do autor

- **Autor:** agente Claude (Claude Code), sessão que escreveu o ADR, em 2026-11-03.
- **Resultado:** a crítica foi incorporada ao [ADR 0004, versão 2](../0004-fonte-e-manutencao-da-base.md), agora com status "aceita". Dos 24 achados, 21 foram aceitos integralmente e 3 em parte. Nenhum foi rejeitado.
- **Documentos novos:** o esquema e o guia saíram do ADR para [esquema-base.md](../../dados/esquema-base.md) e [guia-curadoria.md](../../dados/guia-curadoria.md).

### Conferência dos fatos centrais

Antes de aceitar os três achados bloqueantes, o autor leu os termos vigentes no navegador:
- **[Termos da Google](https://cloud.google.com/maps-platform/terms):** as seções 3.2.3(a)(iii), 3.2.3(c)(vii), 3.2.3(e) e 3.2.4 dizem o que a crítica afirma.
- **[Termos específicos](https://cloud.google.com/maps-platform/terms/maps-service-terms):** as seções 14.1 a 14.3 também confirmam.
- **[Text Search](https://developers.google.com/maps/documentation/places/web-service/text-search):** a página confirma que `movedPlace` e `movedPlaceId` estão no SKU gratuito de IDs.

A leitura trouxe dois pontos que a crítica não levantou:
- **3.2.3(d)(iii):** proíbe usar os serviços principais "em um serviço de listagem ou diretório". Entrou no ADR como risco residual, com a TomTom como saída.
- **3.2.3(a)(iv):** proíbe usar conteúdo da Google com texto para voz, o que afeta o RF-40. Entrou como condição 3 (nada da Google é mostrado nem lido em voz).

### Resposta a cada achado

| Achado | Resposta | O que mudou no ADR |
|---|---|---|
| C-01 | Aceito | Resposta da Google efêmera e só na hora do plano. O lote mensal foi removido. `verificado_em` só muda por verificação humana. Princípio 2 e condições 2 a 4. RNF-15 corrigido nos requisitos |
| C-02 | Aceito | Condição 1: MVP sem mapa embutido, com link para o Google Maps; o ADR de mapas e rotas herda a restrição |
| C-03 | Aceito | Três projetos (curadoria, plano, feriado), um por SKU, com cotas diárias de grátis ÷ 31. Cobrança pelo SKU mais alto e alerta que só avisa estão explicados. Provedor falso em desenvolvimento e testes de carga. Free Trial como opção a conferir |
| C-04 | Aceito | Unidade = item exibido; cerca de 125 itens estratificados nas semanas 3 e 6; meta afirmada só pelo limite inferior de Clopper-Pearson |
| C-05 | Aceito | "Correto" definido pela resposta do filtro (horário) e pelo custo por pessoa (±10%), com critérios para status e evento; fórmula do custo no guia |
| C-06 | Aceito | Horizonte do MVP declarado; limites longos marcados como pós-MVP; estados sem lacunas, incluindo "não conferido agora"; calibração na semana 6 com 40 lugares do piloto; frescor medido sobre os itens exibidos (≥ 90%) |
| C-07 | Aceito | Rotina de horário antes de feriados (15/11, 20/11, 30/11) e conferência de `currentOpeningHours` dos finalistas em feriado, no projeto "feriado" |
| C-08 | Aceito | Casamento confirmado pelo `formattedAddress` (Essentials). A coordenada da Google não é usada, para não cair em 3.2.3(c)(iv). `NOT_FOUND` e `movedPlaceId` mandam o lugar para a fila |
| C-09 | Aceito, saída (a) | OSM só consultado à mão, sem importar campos. Coordenadas da Overture (licenças permissivas) ou manuais a partir do endereço do lugar. IDs da Google em arquivo separado |
| C-10 | Aceito | Tabela de filtros com "sem informação". Acessibilidade em subcampos; lista alimentar igual à do perfil. Alergia grave fora do que o app promete |
| C-11 | Aceito | Pedidos de teste escritos na semana 2, antes da base; versão congelada por tag; julgamento dos lugares do LLM puro na fonte primária, nunca na Google (condição 4) |
| C-12 | Aceito | Meta = horas ÷ tempo medido; orçamento de 20 h por semana nas semanas 2 a 5; tarefas omitidas incluídas; donos propostos pelos papéis da ata de 29/10 |
| C-13 | Aceito em parte | O critério de aceite passou a ser o resultado: teste de cobertura por estrato região × faixa de orçamento, sem média. As cotas por região continuam, mas só como ponto de partida da curadoria. Sem elas o sorteio não tem estratos. O teto do Centro não vale para locais de eventos. As 35 RAs foram distribuídas em seis regiões, e a referência passou a ser a PDAD-A 2024 |
| C-14 | Aceito | Lista fechada de campos na importação; regra do contato direto; curador por iniciais; validação "zero campos de contato" |
| C-15 | Aceito | Esquema completo em documento próprio, com endereço, couvert, taxa de serviço, consumação, meia-entrada, lote, esgotado, local alterado, itens para levar e formato de horário. O texto do embedding é gerado por modelo, e o atributo vence o texto. Estacionamento e distância de estação ficam para o ADR de rotas e GTFS |
| C-16 | Aceito | Recheque só dos eventos dos próximos 14 dias; vencido aos 14 dias; "confirme no link oficial" no plano; campos `esgotado`, `lote` e `local_alterado` |
| C-17 | Aceito em parte | Tabela única de critérios com Google, TomTom, Foursquare, OSM e conferência manual. A TomTom entra no piloto, com critério de troca (≥ 80% de acerto). A Google continua sendo a escolha: tem os campos de status e horário documentados, e a TomTom não teve os termos de cache encontrados. O `date_closed` da FSQ não foi adotado como filtro, porque a FSQ OS deixou de ser a fonte principal (C-19) |
| C-18 | Aceito em parte | Entram o retorno dos usuários (pergunta opcional no RF-37, só para a fila) e a leitura de cardápio pela IA (Could, semana 5). O formulário para os lugares fica para depois do MVP, por esforço e relacionamento |
| C-19 | Aceito | Uma fonte principal: a Overture, por não exigir conta e ter licença por registro. FSQ OS só se o piloto mostrar lacunas; OSM só consultado; sem merge automático |
| C-20 | Aceito | "Foco em álcool" definido no guia e aplicado a eventos; o teste de cobertura mede salas com candidato viável sem foco em álcool |
| C-21 | Aceito | Link montado com Maps URLs (`query` + `query_place_id`). Nenhum conteúdo da Google é exibido, então não há logo a mostrar |
| C-22 | Aceito | Catálogo do rolê em casa fora da base; faixas por item sempre como estimativa; DIEESE descartado |
| C-23 | Aceito | Piloto de 20 lugares na semana 2; 60 na semana 3; 120 na semana 4; até 200 na semana 5 |
| C-24 | Aceito | Seção "Justificativa e evidências" por pergunta; referências completas; nota sobre o cache de coordenadas fechada (30 dias, 14.3); esquema e guia em `docs/dados/`; seção "Mudanças em outros documentos" |

### Perguntas da seção 4

| Pergunta | Encaminhamento |
|---|---|
| 1. Mapa embutido | O autor decidiu "sem mapa embutido no MVP" (condição 1); o grupo confirma |
| 2. Usuários de fora e base pública | A escolha de licenças permissivas tira a obrigação da ODbL; falta saber só a atribuição exibida |
| 3. Conta de faturamento | Continua com o grupo; o Free Trial é a opção preferida, se cobrir a Maps Platform |
| 4. Horas e donos | Proposta de 20 h por semana e donos por papel; o grupo confirma |
| 5. Meta de 95% | Respondida no ADR: vale para os itens exibidos, com cerca de 125 itens por rodada |
| 6. Base viva depois da semana 7 | Respondida: limites longos e rodada trimestral marcados como pós-MVP |
| 7. Restrições prometidas | Respondida: vegetariano, vegano, sem glúten, sem lactose e dois itens de acessibilidade; alergia grave fora |
| 8. O que é "barato" | R$ 40 por pessoa até o formulário de hábitos dar o dado |
| 9. RAs por região | Proposta de seis regiões com as 35 RAs; o grupo confirma |
| 10. Foco em álcool | Respondida no guia de curadoria |
| 11. Rolê em casa na base | Respondida: fora da base do MVP |
| 12. Contato com lugares e retorno dos usuários | Retorno dos usuários adotado; contato com lugares fica para depois do MVP |

