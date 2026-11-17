# Golden Dataset da Semana 3 (RAG vs. IA Pura)

Arquivo: `data/golden_dataset_semana3.json`
Testes: `tests/test_golden_dataset.py` (rodam no CI)
Origem: issues #31 (parte 1: `golden_01` a `golden_10`) e #32 (parte 2: `golden_11` a `golden_20`)

Conjunto de perguntas com gabarito ancorado na base oficial
`data/banco_aprovado_2fa.json`. Usado na comparação A/B entre a LLM pura e o
nosso RAG (#34, tela `/comparacao`), para medir alucinação, precisão de preço e
horário (RNF-03), cobertura fora do Plano Piloto (RNF-13) e compreensão de
expressões de Brasília (RNF-08).

## Campos

| Campo | Tipo | Significado |
|---|---|---|
| `id` | texto | `golden_XX`, único e em sequência |
| `pergunta` | texto | Pergunta como um usuário faria |
| `categoria` | texto | Ver tabela de categorias abaixo |
| `ra_esperada` | texto ou `null` | `regiao_administrativa` **exata** do registro de evidência |
| `locais_gabarito` | lista de textos | `nome` **exato** do registro de evidência; `[]` fora do DF |
| `preco_maximo_gabarito` | número ou `null` | `custo_medio_rs` **exato** do registro de evidência |
| `horario_gabarito` | texto ou `null` | Horário reescrito a partir de `horario_funcionamento`, com o mesmo sentido |
| `evidencia_id_tiktok` | texto ou `null` | `id` do registro na base (`tiktok_<video_id>`) |
| `armadilha_llm_pura` | texto | Erro que esperamos da LLM pura (e, quando houver, do RAG) |

## Regras (o teste verifica as marcadas com ✔)

1. ✔ **Nome, RA e preço são copiados da base, sem arredondar nem corrigir.**
   Assim o teste confere automaticamente que o gabarito bate com a evidência.
   Se o preço da base estiver errado, corrija a base, não o gabarito.
2. ✔ **`null` só na categoria `fora_de_escopo_df`.** Nela, `ra_esperada`,
   `preco_maximo_gabarito`, `horario_gabarito` e `evidencia_id_tiktok` são
   `null` (não se aplica) e `locais_gabarito` é `[]`. Em qualquer outra
   categoria, todos os campos são obrigatórios.
3. ✔ **Toda evidência existe na base 2FA.**
4. **Um local por pergunta.** A pergunta deve ser específica o suficiente para
   ter uma única resposta certa na base (ex.: "rodízio de mini hambúrguer **e
   pão de queijo**", e não só "hambúrguer").
5. **Horário pode ser reescrito, nunca inventado.** Pode resumir ou reordenar o
   `horario_funcionamento`; não pode acrescentar nada que não esteja na base ou
   no vídeo. Este campo não é verificado automaticamente.
6. **Não usar como gabarito:**
   - eventos encerrados e promoções vencidas;
   - registros com `custo_medio_rs = 50.0` sem preço citado no vídeo (valor
     padrão);
   - registros cuja RA o próprio vídeo contradiz (ex.: Hamburgueria Espacial,
     marcada como Taguatinga mas o vídeo diz Sobradinho; Feira Noturna
     Candangolândia, marcada como Vicente Pires);
   - outliers de preço (Nosso Quintal, Peixe na Rede, Golden Black).
7. ✔ **Exatamente 20 casos**, `golden_01` a `golden_20`, nessa ordem e sem IDs
   repetidos. O dataset está fechado (ver "Como mudar o dataset").
8. ✔ **6 categorias, com a distribuição da tabela abaixo**, e nenhuma outra. Um
   nome de categoria digitado errado quebra o teste.
9. ✔ **Cada caso aponta para um registro diferente da base.** São 18 lugares
   para 20 perguntas (os 2 casos fora do DF não têm evidência).
10. **A pergunta não promete mais do que a evidência.** Se o vídeo diz "sem
    trigo", a pergunta não fala em celíacos: sem trigo não é sem glúten.

## Categorias

| Categoria | Parte | Casos | O que testa |
|---|---|---|---|
| `geoespacial_ra_fora_centro` | 1 | 5 | Encontrar lugares reais fora do Plano Piloto (RNF-13) |
| `janela_horario` | 1 | 3 | Respeitar horários reais (madrugada depois da 1h, domingo) |
| `fora_de_escopo_df` | 1 | 2 | Recusar perguntas sobre outras cidades |
| `precisao_financeira` | 2 | 5 | Preço exato em reais: rodízio, ingresso de parque infantil, teto estrito de R$ 30 (RNF-03) |
| `vibes_e_restricoes` | 2 | 3 | Ambiente e restrição alimentar descritos só no vídeo: Kid Friendly, sem trigo/lactose/açúcar refinado, romântico |
| `conflito_e_girias` | 2 | 2 | Pedido que parece impossível, mas tem saída na base; pergunta em candanguês (RNF-08) |

A issue #32 fala em "5 categorias", mas a parte 1 já tinha 3 e a parte 2
acrescenta outras 3. O teste exige as 6.

Comportamento esperado em `fora_de_escopo_df`: o RAG **recusa** e informa que
o app cobre só o DF. Recomendar qualquer lugar, inclusive do DF, conta como erro.

Comportamento esperado em `conflito_e_girias`: o RAG **explica a condição**
(`golden_19`: só o aniversariante não paga, e só com 10 convidados) ou
**entende as gírias** (`golden_20`). Responder só "sim" ou só "não" conta
como erro.

## Catálogo das 20 perguntas

Gerado a partir do JSON. Horário e armadilha completos estão em cada caso do arquivo.

| ID | Categoria | Pergunta | Gabarito | RA | R$ |
|---|---|---|---|---|---|
| `golden_01` | `geoespacial_ra_fora_centro` | Onde tem rodízio de mini hambúrguer e pão de queijo em Taguatinga para ir com amigos? | Filomenambúrguer | Taguatinga | 49,99 |
| `golden_02` | `geoespacial_ra_fora_centro` | Onde tem rodízio de caldos ou de pizza com brinquedoteca em Águas Claras? | Restaurante Dona Cleide | Águas Claras | 54,90 |
| `golden_03` | `geoespacial_ra_fora_centro` | Onde comer churrasco americano defumado no Guará? | Santo Bifidele | Guará | 39,90 |
| `golden_04` | `geoespacial_ra_fora_centro` | Onde tem rodízio de almoço barato com parmegiana no Riacho Fundo? | Royal Burger | Riacho Fundo | 29,90 |
| `golden_05` | `geoespacial_ra_fora_centro` | Onde comer rodízio de pizza e sushi à noite em Samambaia com a família? | VBQ | Samambaia | 44,90 |
| `golden_06` | `janela_horario` | Onde dá para comer e beber com os amigos depois da 1h da manhã num sábado? | New Mercadito | Plano Piloto (Asa Sul) | 54,99 |
| `golden_07` | `janela_horario` | Onde tem buffet de almoço à vontade por menos de R$ 30 no domingo em Taguatinga? | Casa Bar | Taguatinga | 29,99 |
| `golden_08` | `janela_horario` | Quero ir num pizza bar com drinks no domingo à tarde. Qual abre e a partir de que horas? | Spelunca DF | Plano Piloto (Asa Sul) | 65,50 |
| `golden_09` | `fora_de_escopo_df` | Quais são os melhores bares em Copacabana, no Rio de Janeiro, para ir com amigos numa sexta à noite? | — (recusar) | — | — |
| `golden_10` | `fora_de_escopo_df` | Onde comer hambúrguer artesanal em Pinheiros, São Paulo, gastando até R$ 50? | — (recusar) | — | — |
| `golden_11` | `precisao_financeira` | Onde tem rodízio de churrasco japonês na Asa Sul e quanto custa por pessoa, sem bebida? | Yaki Nikuya | Plano Piloto (Asa Sul) | 124,90 |
| `golden_12` | `precisao_financeira` | Quanto custa, num sábado, o rodízio de pizza com buffet de mini burger em Taguatinga? | Casa Bari | Taguatinga | 69,90 |
| `golden_13` | `precisao_financeira` | Quero levar as crianças num parque de Natal com neve artificial e túnel de luzes em Taguatinga. Quanto custa o ingresso? | Vale Encantado | Taguatinga | 19,90 |
| `golden_14` | `precisao_financeira` | Moro em Samambaia e posso gastar no máximo R$ 30, nem um centavo a mais. Onde almoçar um prato executivo numa sexta? | Saguari Gastro House | Samambaia | 24,90 |
| `golden_15` | `precisao_financeira` | Tenho só R$ 30, nem um centavo a mais. Dá para almoçar no buffet à vontade com tempero nordestino em Vicente Pires numa terça-feira? | Restaurante do Daniel | Vicente Pires | 32,99 |
| `golden_16` | `vibes_e_restricoes` | Quero uma gelateria ou doceria aconchegante em Brasília onde tudo seja sem trigo, sem lactose e sem açúcar refinado. Qual é e em que horário abre? | Lefit Gelatos e Doces Saudáveis | Plano Piloto (Asa Sul) | 28,00 |
| `golden_17` | `vibes_e_restricoes` | Quero comer feijoada à vontade num sábado em Águas Claras com as crianças, num lugar com brinquedoteca e monitora. Onde é e quanto custa? | Vila Carioca | Águas Claras | 59,97 |
| `golden_18` | `vibes_e_restricoes` | Quero um jantar romântico a dois num restaurante chique ao lado da Torre de TV numa terça, com buffet de massas frescas. Onde é e quanto custa por pessoa? | Lucca Restaurante | Plano Piloto (Asa Sul) | 89,00 |
| `golden_19` | `conflito_e_girias` | Quero comemorar meu aniversário num rodízio japonês completo na Asa Norte, mas sem pagar nada. Existe rodízio caro totalmente de graça? | Blue Sushi | Plano Piloto (Asa Norte) | 109,99 |
| `golden_20` | `conflito_e_girias` | Saindo do trampo na Asa Norte, ali perto da tesourinha, bora num rolê baratinho de espetinho na brasa no Noroeste numa segunda? Coisa de uns 30 conto. | Brasa Meat Burger | Plano Piloto (Noroeste) | 30,00 |

## Decisões da parte 1

- **Samambaia no lugar de Ceilândia (`golden_05`).** Os dois registros de
  Ceilândia têm preço de promoção vencida. Samambaia também é RA de renda baixa
  e tem preço regular (VBQ).
- **`golden_01` usa o vídeo de 08/04/2026 do Filomenambúrguer**
  (`tiktok_7626405885388197128`). O vídeo de 23/09/2026 não cita preço e tem o
  valor padrão de R$ 50. O exemplo da issue era ilustrativo.
- **Só existe um lugar aberto depois da 1h na base** (New Mercadito), por isso
  há 1 caso de madrugada e 2 de domingo.
- **Limitação conhecida (`golden_06`):** o `custo_medio_rs` do New Mercadito é
  o do buffet de almoço, embora a pergunta seja sobre a madrugada. A regra 1
  garante que o preço é verificável, mas não que ele corresponde à situação da
  pergunta. Vale citar no relatório da Semana 3.

## Decisões da parte 2

- **Sem `null` em `conflito_e_girias`.** Os dois casos apontam lugar real, então
  a regra 2 continua valendo só para `fora_de_escopo_df`. O exemplo da issue
  ("restaurante de luxo totalmente grátis") virou o `golden_19`, que tem uma
  saída parcial na base.
- **Só 2 rodízios em `precisao_financeira`.** Uzuki, Carmelita e Nicolândia
  ficaram de fora por promoção vencida, e o Omura porque o `custo_medio_rs`
  (R$ 70) é o do festival Hot Roll, não o do rodízio completo (R$ 140).
- **Teto de R$ 30 cercado pelos dois lados.** O `golden_14` fica abaixo
  (R$ 24,90) e o `golden_15` logo acima (R$ 32,99), porque o erro mais provável
  está perto do limite.
- **Limitação conhecida (`golden_15`):** a resposta certa é "não cabe", mas o
  schema não tem campo para isso. O lugar fica em `locais_gabarito` e a resposta
  esperada fica em `armadilha_llm_pura`. Na auditoria, dizer que o buffet cabe
  em R$ 30 conta como erro.
- **Limitação conhecida (`golden_13`):** o Vale Encantado é o único ingresso de
  parque infantil em cartaz na base, mas os R$ 19,90 são do lote de pré-venda
  de 20/10. O valor atual pode ser outro.
- **Limitação conhecida (`golden_16`):** o vídeo da Lefit não cita preço, mas a
  base tem `custo_medio_rs = 28.0` e `trava_2_preco_ok = true`. O valor foi
  copiado para cumprir a regra 1. Não use este caso para medir precisão de
  preço. A correção é na base, não no gabarito.
- **`golden_14`:** o `horario_funcionamento` do Saguari na base guarda o horário
  do happy hour. O horário de abertura veio da legenda do vídeo (regra 5).
- **Pares de distratores de propósito.** `golden_12` (Casa Bari) e `golden_01`
  (Filomenambúrguer) são de Taguatinga e têm mini hambúrguer. `golden_17` (Vila
  Carioca) e `golden_02` (Dona Cleide) são de Águas Claras e têm brinquedoteca.
  Os pares medem se o RAG distingue lugares parecidos.
- **Carne na brasa foi para o `golden_20`.** Eram 4 temas para as 3 vagas de
  `vibes_e_restricoes`. O distrator da base, Dom Frangão, não abre às segundas.
- **"Tesourinha" entra como ponto de partida do usuário** (`golden_20`), não
  como local do gabarito, para não afirmar um dado geográfico que a base não tem.

## Como mudar o dataset

O dataset está fechado em 20 casos, e o teste falha se esse número mudar. Para
trocar ou acrescentar um caso:

1. Siga as regras acima, principalmente a 1: copie nome, RA e preço da base.
2. Se mudar o total ou a distribuição, atualize `IDS_ESPERADOS` e
   `DISTRIBUICAO_PARTE_*` em `tests/test_golden_dataset.py` e o catálogo deste
   documento no mesmo commit.
3. Se um colega corrigir um preço na base, o teste quebra no caso
   correspondente. Copie o preço novo para o gabarito.
4. Rode antes de commitar:

   ```bash
   PYTHONPATH=. pytest -v tests/test_golden_dataset.py
   ```

   Se um caso falhar, o nome do teste mostra qual (`[golden_XX]`).
