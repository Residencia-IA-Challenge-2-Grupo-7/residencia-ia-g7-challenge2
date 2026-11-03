# Prompt para a crítica do ADR 0004

Cole o bloco abaixo num chat novo, de preferência com outro modelo ou outro agente. A crítica sai em `docs/decisoes/revisoes/0004-critica.md`. Depois, o agente que escreveu o ADR responde a cada ponto nesse mesmo arquivo e ajusta o ADR.

````text
Você vai revisar criticamente uma decisão técnica do projeto Orquestrador de Rolês: um app web em que uma IA ajuda grupos de amigos do Distrito Federal a organizar encontros. Seu papel é encontrar lacunas, contradições e afirmações frágeis. Não reescreva a decisão e não a defenda.

## Leia antes

1. AGENTS.md e STATUS.md (contexto e restrições do projeto).
2. docs/decisoes/0004-fonte-e-manutencao-da-base.md: o ADR a revisar.
3. docs/produto/requisitos.md, sobretudo RF-15, RF-16, RF-17, RF-20, RF-44, RF-46, RNF-01, RNF-03, RNF-04, RNF-12, RNF-13, RNF-15 e RNF-16, a seção "Questões em aberto" e "Riscos referenciados".
4. docs/decisoes/0001 a 0003 e docs/arquitetura/index.html (procure por "base", "curadoria" e "fontes").
5. docs/desafio/challenge-2.md (roadmap de 7 semanas e restrições do desafio).

O ADR responde a quatro perguntas: (1) de quais fontes sai a base; (2) qual API confere se o lugar existe e está aberto; (3) com que frequência os dados são reverificados e quando um preço ou horário vira "aproximado"; (4) quantos lugares a base terá e como se dividem entre os quatro tipos de rolê.

## O que procurar

Para cada item, diga se o ADR cobre, cobre mal ou não cobre.

**A. Resposta às quatro perguntas**
- Cada pergunta tem uma decisão clara, com números, e não só opções?
- As alternativas descartadas foram comparadas com critérios iguais? Falta alguma alternativa relevante (outras APIs de lugares, fontes de eventos do DF, parcerias com os lugares, contribuição dos próprios usuários)?

**B. Fatos verificáveis (confira nas fontes oficiais, não confie no ADR)**
- Cotas gratuitas e preços por SKU da Google Places API (New) e qual SKU cada campo usado aciona.
- Regras de cache e de atribuição da Google: o que pode ser guardado, por quanto tempo, e se o uso "só para conferir, guardando o resultado" é compatível com os termos.
- Licenças de OpenStreetMap (ODbL), Overture Maps e FSQ OS Places, e o que cada uma exige se a base for publicada.
- Faixa gratuita real da Foursquare Places API.
- Termos de uso de Instagram, Sympla e iFood sobre coleta manual e automatizada.
- Existência de API ou dados abertos de agenda cultural e de parques do DF.
Marque cada fato como confirmado, divergente (com a fonte certa) ou não verificável.

**C. Consistência com o resto do projeto**
- Contradições com os requisitos, com os ADRs anteriores, com as premissas de custo (P12, P16) e de capacidade (P08) e com o mapa da arquitetura.
- Requisitos que dependem da base e foram esquecidos (por exemplo restrições alimentares e de acessibilidade do RF-17, itens para levar do RF-15, imprevistos do RF-46, aprendizado com avaliações do RF-38).

**D. Qualidade dos dados e medição**
- As definições de "correto" (tolerância de horário e preço) são mensuráveis e razoáveis?
- O tamanho da amostra mensal (30 lugares) permite afirmar 95% de acerto com alguma confiança? Proponha um tamanho defensável.
- Como tratar deduplicação, casamento errado de place ID, lugares sem cadastro, horários especiais e sazonais, eventos cancelados e lotes de ingresso?
- Os limites de "exato / aproximado / vencido" têm justificativa ou plano de calibração suficiente? Há dados que deveriam ter outro limite?

**E. Custo, operação e esforço**
- O consumo estimado de chamadas está certo para os cenários de uso (lote mensal, conferência na hora do plano, testes de carga com salas de 20 pessoas, demonstração final)?
- O que acontece se a cota acabar no meio de uma demonstração?
- A estimativa de 15 minutos por lugar e a cadência de manutenção cabem em 5 pessoas × 20 h por semana junto com o desenvolvimento? Quem é o dono de cada rotina?
- Há passos que deveriam ser automatizados ou que não precisam existir no MVP?

**F. Justiça, ética e LGPD**
- A distribuição por região e por faixa de preço protege quem mora longe e quem tem menos dinheiro (RNF-13, R-02)? O teto de 40% e o piso de 15 por região são defensáveis?
- Há viés da equipe na curadoria, e a mitigação proposta resolve?
- Algum dado pessoal pode entrar na base sem querer (MEIs, fotos, avaliações, contatos)?
- A regra de 40% sem foco em álcool atende o RNF-16?

**G. Ligação com as próximas etapas**
- O esquema serve para o RAG (o que vira filtro estruturado e o que vira embedding), para a comparação LLM × RAG da semana 3 e para os agentes da semana 4?
- Falta algo no esquema (por exemplo capacidade, faixa etária, estacionamento, distância de estação, cobertura contra chuva)?

**H. Forma do ADR**
- Segue o template (docs/decisoes/0000-template.md) e as restrições do desafio (justificar, explicitar riscos, validar com métricas, citar evidências)?
- Há trechos longos que deveriam virar documento à parte (guia de curadoria, esquema)?

## Formato da resposta

Crie docs/decisoes/revisoes/0004-critica.md com:

1. **Resumo**: 3 a 5 frases com a avaliação geral e os pontos mais graves.
2. **Achados**, numerados (C-01, C-02…), cada um com:
   - gravidade: bloqueante (impede aceitar o ADR), importante (deve ser resolvido antes da semana 3) ou menor;
   - seção do ADR a que se refere;
   - o problema, com a evidência (link da fonte oficial quando for fato externo);
   - sugestão concreta de correção.
3. **Tabela de fatos verificados**: fato, o que o ADR diz, o que a fonte diz, link, situação.
4. **Perguntas que só o grupo pode responder.**
5. Uma seção vazia chamada "Respostas do autor", que o autor do ADR vai preencher.

Regras:
- Em português do Brasil, frases curtas e diretas.
- Não edite o ADR nem outros arquivos além do 0004-critica.md.
- Não invente números. Se não conseguir verificar um fato, diga isso.
- Priorize: no máximo 25 achados, os mais graves primeiro.
- Não faça commit nem push.
````
