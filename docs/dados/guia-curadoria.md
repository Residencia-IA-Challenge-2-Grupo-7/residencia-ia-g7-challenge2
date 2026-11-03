# Guia de curadoria da base

> **Substituído como procedimento pelo [ADR 0005](../decisoes/0005-coleta-automatica-e-base-vetorial.md):** a coleta passou a ser automática e nenhuma pessoa preenche campos. As seções "Regras que não mudam" (exceto a coleta humana), "Definições" e "Modelo de descrição" continuam valendo como **regras do prompt de extração e do validador**. As seções "Fluxo por lugar", "Eventos", "Feriados", "Fila de reconferência" e "Qualidade" ficam só como histórico.

- **Versão:** 0.1 (provisória até o piloto da semana 2), 2026-11-03
- **Decisão de origem:** [ADR 0004](../decisoes/0004-fonte-e-manutencao-da-base.md) · **Campos:** [esquema da base](esquema-base.md)

## Regras que não mudam

1. **Fonte primária sempre.** Horário, preço e atributos vêm do site, do cardápio, do perfil oficial ou do canal comercial do próprio lugar.
2. **Nada do Google Maps.** Não copie horário, nome, endereço, foto nem avaliação do app ou do site do Google Maps (termos da Google, 3.2.3). O casamento com o place ID é feito pelo script, não à mão.
3. **Nada de raspagem.** Instagram, iFood, Sympla e similares só são lidos por uma pessoa.
4. **Nada pessoal.** Não registre telefone, e-mail, rede social nem nome de pessoa. Num contato direto com o lugar, use só o canal comercial, anote o fato e o canal ("WhatsApp comercial, 05/11") e não guarde o número.
5. **Dúvida é "sem informação".** Não estime nem preencha por intuição.
6. **Data em tudo.** Ao conferir um campo, atualize o `verificado_em` dele, mesmo que o valor não tenha mudado.

## Fluxo por lugar

1. **Pegue o próximo candidato sorteado** do seu estrato (região × categoria) na planilha. Não escolha lugares por conta própria. Se quiser incluir um lugar que conhece, ele entra na fila de sugestões e passa pelos mesmos critérios.
2. **Aplique os critérios de exclusão.** Pule o candidato e registre o motivo quando ele:
   - está fechado;
   - não tem nenhuma fonte primária com horário;
   - é só delivery, sem salão;
   - atende só sócios ou convidados;
   - é voltado a menores;
   - é duplicata de outro registro.
3. **Preencha horário, preços e atributos** pela fonte primária, com `fonte` e `verificado_em`.
4. **Escreva a descrição** com o modelo abaixo.
5. **Marque o tempo gasto** na coluna `minutos` (só no piloto e na dupla leitura).

## Definições

**Ruído**
- `baixo`: dá para conversar sem levantar a voz.
- `medio`: há música ambiente ou movimento, mas a conversa flui.
- `alto`: há música ao vivo ou som alto, e é preciso falar alto.
- Sem evidência no site, no cardápio ou nas fotos do próprio lugar: `sem_informacao`.

**Foco em álcool:** a principal oferta é bebida alcoólica (bar, choperia, adega, boate, festa com open bar). Restaurante que também serve bebida **não** tem foco em álcool. Vale também para eventos.

**Acessibilidade**
- `acess_entrada_sem_degrau = sim` só com evidência: foto, informação do lugar ou norma de equipamento público.
- O mesmo vale para `acess_banheiro_adaptado`.

**Restrições alimentares**
- `sim` quando o cardápio tem pelo menos um prato principal que atende à restrição, identificado como tal.
- `nao` quando o cardápio claramente não tem nenhum.
- Nos outros casos, `sem_informacao`.

**Custo por pessoa** (calculado pelo script; o curador só registra os itens com o `papel` certo):

| Categoria | Pedido típico | Pedido mínimo |
|---|---|---|
| Restaurante | 1 `principal` + 1 `bebida_nao_alcoolica` | `principal` mais barato |
| Bar | metade de 1 `porcao` + 2 `bebida` | 1 `bebida` mais barata |
| Café, lanchonete | 1 `principal` (salgado, lanche) + 1 `bebida_nao_alcoolica` | item mais barato que faz sentido sozinho |
| Sorveteria | 1 `principal` | o mesmo |
| Lugar com entrada | `taxa_entrada` | o mesmo |

Ao pedido somam-se o `couvert` por pessoa e a `taxa_servico_pct` sobre o consumo. Registre 3 a 5 itens; quando houver mais de uma opção, use o item mais comum, não o mais barato nem o mais caro.

## Modelo de descrição (até 300 caracteres)

> {O que é, em uma frase}. {Para que tipo de rolê serve}. {Uma característica que ajuda a escolher: espaço, vista, especialidade}.

Use linguagem neutra, sem adjetivos de propaganda ("o melhor", "imperdível") e sem copiar o texto do lugar.

## Eventos

- **Toda semana,** o curador da semana:
  - cadastra os eventos dos próximos 14 dias nos locais da base e nas agendas oficiais;
  - rechecha os que já estão cadastrados: data, horário, local, preço, lote, esgotado e cancelado.
- Evento que não puder ser rechecado passa a "aproximado" depois de 7 dias e sai da base depois de 14.

## Feriados

Antes de cada feriado do período (15/11, 20/11 e 30/11; confira o calendário oficial do GDF), o curador da semana confere o horário dos lugares mais usados nos planos e registra as exceções datadas.

## Fila de reconferência

Entram na fila:
- lugares que a API marcou como fechados, movidos ou não encontrados;
- divergências relatadas pelos usuários na avaliação (RF-37);
- campos vencidos.

O curador da semana confere na fonte primária e atualiza o lugar ou o marca como fechado. A fila guarda só o nosso `id`, o motivo e a data.

## Qualidade

- **Dupla leitura:** 10% dos lugares, sorteados, são curados de novo por outra pessoa sem ver a primeira versão. As divergências viram ajustes neste guia.
- **Piloto da semana 2:** 20 lugares, com tempo cronometrado. O tempo médio define a meta de lugares (ADR 0004, Pergunta 4).
