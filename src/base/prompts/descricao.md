# Descrição curta de lugares, a partir dos fatos validados

Versão do prompt: 0.1 (ADR 0005). Você recebe uma lista JSON de lugares do Distrito Federal, cada um só com fatos já conferidos por código: nome, categoria, RA, dias em que abre, alguns itens do cardápio, atributos e, quando houver, se é gratuito e os próximos eventos. Escreva uma descrição curta para cada um.

## Regras

1. **Só os fatos recebidos.** Não acrescente nada que não esteja no JSON: nem história, nem especialidade, nem ambiente, nem público. Não use o que você sabe sobre o lugar.
2. **Modelo:** `{O que é, em uma frase}. {Para que tipo de rolê serve}. {Uma característica que ajuda a escolher}.` A característica sai dos atributos, dos itens ou dos dias (ex.: "Tem opções veganas.", "Abre aos domingos.", "Cardápio com pizzas e massas.").
3. **Até 300 caracteres**, em português, linguagem neutra.
4. **Sem propaganda:** nada de "melhor", "imperdível", "incrível", "perfeito", "único", "excelente", "delicioso".
5. Sem preços, horários exatos, endereços ou nomes de pessoas: esses dados aparecem em outros campos.

## Saída

Grave um único objeto JSON, em UTF-8, com o `lugar_id` de cada lugar como chave e a descrição como valor:

```json
{"lug-0000aaaa": "Restaurante de comida caseira em Taguatinga. Serve para almoço com amigos ou família. Tem opções vegetarianas."}
```
