# 0013 — Deslocamento no DF e nota de justiça da Menor Miséria

- **Status:** proposta
- **Data:** 2026-11-12
- **Semana do roadmap:** 3 — Telas 1 a 3 do app em paralelo à comparação RAG × LLM pura
- **Origem:** issue #44. O número 0011 está reservado para o ADR do comparativo A/B (branch `feat/34-comparador-ab`)
- **Requisitos:** RF-19, RF-21, RNF-02, RNF-04, RNF-13, RNF-15

## Contexto

Os cartões da Tela 3 precisam do tempo e do custo de ida e volta de cada pessoa até cada lugar (RF-21) e de uma nota que proteja quem mora longe (RNF-13), calculados em código, sem LLM (RNF-04) e sem API paga (guia oficial, seção 1).

O que já existia:

- `src/salas/integracoes.py` procura pelo nome as funções `estimar_deslocamento` e `nota_menor_miseria` em `src/logistica/transporte_df.py` e, sem elas, usa uma reserva: linha reta × 1,3, velocidades fixas e R$ 5,50 a passagem.
- Os pontos das RAs vinham da média das coordenadas da base: só 11 das 35 RAs tinham ponto, e o "centro" do Gama caía no Plano Piloto (31,8 km de erro), porque os 2 eventos do Gama na base têm coordenadas do Plano.
- Na base de 93, 47 lugares estão marcados como "Centróide Oficial": a coordenada é o centro da RA, e não o endereço.
- `requisitos.md` e o mapa da arquitetura deixam a regra de justiça como "menor miséria, ADR pendente".

## Opções consideradas

**Distância**

1. **API de rotas (Google Maps, Mapbox):** tempo real de trânsito, mas paga, com cartão e chave, e sai do RNF-04.
2. **Roteador próprio (OSRM, GraphHopper):** rota de verdade, mas exige servidor e mapa do DF atualizado.
3. **Haversine × fator de rota (escolhida):** linha reta sobre a esfera, multiplicada por 1,3. Grátis, determinística e testável; erra mais em trajetos com rodovia ou desvio grande.

**Regra de justiça**

1. **Média dos trajetos:** é o que um LLM faz sem regra explícita (visão do produto), e não enxerga quem fica longe: para Samambaia + Plano Piloto, a média fica entre 11,7 e 12,4 km em qualquer lugar entre os dois.
2. **Só o pior trajeto (minimax puro):** protege quem fica pior, mas empata lugares com o mesmo pior trajeto.
3. **Pior trajeto + um peso menor na desigualdade (escolhida):** a fórmula que a reserva das salas já usava; o segundo termo desempata.

**Como a penalidade vira nota**

1. **`100 − penalidade`, presa entre 0 e 100:** a da reserva. Zera quando alguém mora muito longe.
2. **`100 × 100 / (100 + penalidade)`:** nunca zera e sempre ordena pelo pior trajeto.

## Decisão

- **`data/regioes_df_gps.json`:** um ponto por RA (RA I a XXXV), sempre o centro urbano:
  - 18 do `COORDENADAS_RAS_DF` do coletor 2FA (os mesmos gravados nos lugares "Centróide Oficial");
  - 12 da Wikipédia;
  - 5 do OpenStreetMap (© colaboradores do OpenStreetMap, ODbL).
- **`src/logistica/transporte_df.py`:**
  - `calcular_distancia_km(origem_ra, local_gps)`: Haversine do ponto da RA até o lugar;
  - caminho por rua = linha reta × 1,3, com piso de 2 km para trajetos dentro da mesma RA;
  - tempo de ida = tempo fixo + caminho ÷ velocidade média, nos 6 meios do campo 4: ônibus/metrô 18 km/h + 15 min; carro, app e carona 30 km/h + 5 min; bike 12 km/h; a pé 4,5 km/h;
  - custo de ida e volta em `Decimal`: ônibus/metrô 2 × R$ 5,50; app (R$ 5 + R$ 2,20/km) × 2; carro R$ 0,90/km × 2; carona, a pé e bike R$ 0;
  - `estimar_deslocamento` e `nota_menor_miseria`: os encaixes das salas, com os mesmos números da reserva (o PR não muda nenhum cartão além do piso de 2 km);
  - `calcular_score_justica_espacial(membros_ras, local_candidato)`: a nota pela distância, com a curva que não zera.
- **Penalidade (as duas notas):**
  - por tempo: 0,8 ponto por minuto do pior trajeto acima de 20 min + 0,3 ponto por minuto entre o pior e o melhor;
  - por distância: os mesmos pesos convertidos para quem vai de ônibus/metrô (1 km em linha reta ≈ 4,3 min): 3,5 pontos por km acima de 1,2 km + 1,3 ponto por km de diferença.
- **Nota por tempo (cartões):** fica com `100 − penalidade` presa em 0, como a reserva, até o grupo decidir a troca (riscos, abaixo).

## Justificativa e evidências

- **Haversine contra a geodésica WGS84** (`geographiclib`): −0,04% (Samambaia → Plano), −0,08% (Águas Claras → Plano), +0,07% (Samambaia → Águas Claras). O erro da esfera é muito menor que o de usar o centro da RA no lugar do endereço.
- **Cenário da issue**, Samambaia + Plano Piloto, nota por distância:

  | Lugar | Pior trajeto | Média | Nota |
  |---|---|---|---|
  | Plano Piloto | 23,5 km | 11,7 km | 48,1 |
  | Samambaia | 23,5 km | 11,7 km | 48,1 |
  | Taguatinga | 19,1 km | 12,4 km | 55,7 |
  | Águas Claras | 16,0 km | 11,9 km | 61,6 |
  | Guará | 12,6 km | 11,8 km | 70,4 |

- **Grupo espalhado**, Planaltina + Santa Maria + Plano Piloto, todos de ônibus: a nota por tempo dá 0 em todos os lugares acima. A nota por distância ainda ordena: Plano 40,6 (pior trajeto de 31,5 km), Guará 35,5 (41,9 km), Samambaia 30,1 (54,5 km).
- **Sem conflito com as salas:** um teste roda os 35 × 92 × 6 pares RA × lugar × meio contra a reserva real e só acha diferença nos 53 de 3.220 trajetos RA → lugar com menos de 2 km por rua. As notas por tempo saem iguais às da reserva em 8 grupos de teste.
- **Desempenho:** com cache no nome da RA, de 52 µs para 0,09 µs por chamada (as salas chamam milhares de vezes por sala).
- 224 testes em `tests/test_transporte_df.py`, sem rede.

## Riscos e limitações

- **Velocidades não calibradas.** Samambaia → Plano dá 66 min de carro e 117 de ônibus/metrô, acima do que a equipe vive no dia a dia. A ordem dos lugares sai certa (o modelo é linear na distância), mas o "tempo médio de chegada" dos cartões e o limite de 75 min do `sugestoes.py` sofrem.
- **A nota por tempo zera em grupos espalhados.** Com gente de RAs distantes, vários lugares empatam em 0 e a Menor Miséria deixa de proteger justamente esse grupo. A troca para a curva da nota por distância é uma linha, mas muda o valor da nota em todos os cartões (ela pesa 35% na pontuação) e precisa do aceite do grupo.
- **As duas notas não estão na mesma escala:** uma é linear e presa em 0, a outra é a curva. Não somar nem comparar uma com a outra.
- **Centro da RA no lugar do endereço:** quem mora na ponta de uma RA grande (Ceilândia, Planaltina) é tratado como se morasse no centro. O Plano Piloto é um ponto só, perto da Rodoviária: quem sai da Asa Sul ou da Asa Norte é tratado como se saísse dali, a 3 ou 4 km das duas pontas.
- **Tarifa:** R$ 5,50 é a tarifa do metrô e o teto da integração, não a média (trechos curtos custam R$ 2,70 ou R$ 3,80). Está congelada até 31/12/2026. Aos domingos e feriados o Vai de Graça zera a tarifa, o que o cálculo não sabe, porque o contrato com as salas não recebe a data: num domingo, cobra R$ 11 de quem não vai pagar.
- **Fora do escopo:** horário do dia e pico, volta depois que o metrô fecha, ônibus e metrô separados (o `campos.py` entrega um meio só), rateio da carona (fica R$ 0).
- **Privacidade (RNF-02):** a origem é um dos 4 campos secretos. As notas devolvem só um número, sem dizer quem é o mais prejudicado, e as mensagens de erro não repetem o que a pessoa digitou.

## Como vamos validar

- **Calibração:** medir de 5 a 10 trajetos reais da equipe (RA de origem, lugar, meio, minutos) e ajustar `VELOCIDADE_KMH` e `ESPERA_MIN` até o erro mediano ficar abaixo de 25%. Mudar os dois lados juntos: o teste `test_usa_os_mesmos_numeros_da_reserva_das_salas` trava a igualdade.
- **Justiça:** os testes do cenário da issue (Águas Claras acima dos extremos), do grupo espalhado (nota nunca zera e segue o pior trajeto) e da periferia (Ceilândia + Samambaia + Plano não ficam com o Plano) precisam continuar verdes.
- **Continuações propostas:**
  1. ~~nota por tempo com a curva que não zera~~: **feito em 12/11** (Cauan). `nota_menor_miseria` e a reserva das salas usam `100 × 100 / (100 + penalidade)`; grupos espalhados deixam de empatar em 0;
  2. ~~data no contrato do deslocamento, para o Vai de Graça~~: **feito em 12/11** (Cauan). `estimar_deslocamento(..., quando=)` recebe o início do rolê, e ônibus e metrô custam zero aos domingos e nos feriados nacionais e do DF (`tarifa_zero`; Carnaval e Corpus Christi, pontos facultativos, ficam de fora);
  3. sub-áreas do Plano Piloto (Asa Sul, Asa Norte, Noroeste), se o interpretador passar a devolvê-las (Cauan);
  4. ~~`ra_do_lugar` lê "Plano Piloto (Sudoeste)" como Plano Piloto~~: **feito em 12/11** (Cauan). O texto entre parênteses vale quando corresponde a uma RA só;
  5. calibração das velocidades (Samara).
