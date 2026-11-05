# Relatório da rodada da base — 2026-11-03

Pipeline 0.1.0 (ADR 0005), Overture 2026-10-21.0, extração por claude-haiku-5-5. Gerado por `python -m base relatar`; nenhum número foi digitado.

## Funil

| Etapa | Lugares |
|---|---|
| Candidatos da Overture nos tipos de rolê, dentro do DF | 11255 |
| Com site próprio (sem redes, agregadores e delivery) | 3357 |
| Elegíveis (confiança, um por domínio, sem duplicatas) | 1744 |
| Sorteados (piloto mais reposições) | 811 |
| Site respondeu com conteúdo | 234 |
| Aprovados com os campos obrigatórios | 11 |

## Piloto: 100 primeiros sorteados

Cada célula: aprovados / site respondeu / sorteados.

| Região | restaurante | bar | cafe_lanchonete_sorveteria | ar_livre_gratuito | local_evento | Total |
|---|---|---|---|---|---|---|
| Centro | 0/2/4 | 0/0/3 | 0/2/3 | 0/3/4 | 0/0/3 | 0/7/17 |
| Oeste próximo | 0/1/4 | 0/0/3 | 0/1/3 | 0/2/4 | 0/0/3 | 0/4/17 |
| Oeste | 0/2/4 | 0/0/3 | 0/2/3 | 0/1/4 | 0/1/3 | 0/6/17 |
| Sul | 0/1/4 | 0/0/3 | 0/0/3 | 0/3/4 | 0/1/3 | 0/5/17 |
| Norte | 0/2/4 | 0/0/3 | 0/3/3 | 0/1/4 | 0/1/2 | 0/7/16 |
| Leste | 1/2/5 | 0/1/3 | 0/0/3 | 0/0/3 | 0/1/2 | 1/4/16 |

Situação do site no piloto: dominio_inexistente 52, ok 33, site_fora_do_ar 8, precisa_js 4, bloqueia_robo 2, robots_proibe 1.

## Base: todas as rodadas

| Região | restaurante | bar | cafe_lanchonete_sorveteria | ar_livre_gratuito | local_evento | Total |
|---|---|---|---|---|---|---|
| Centro | 6/33/76 | 1/14/57 | 0/17/57 | 2/36/65 | 0/12/48 | 9/112/303 |
| Oeste próximo | 1/19/76 | 0/9/39 | 0/13/57 | 0/7/19 | 0/3/18 | 1/51/209 |
| Oeste | 0/7/35 | 0/0/6 | 0/4/21 | 0/2/8 | 0/5/13 | 0/18/83 |
| Sul | 0/7/32 | 0/1/10 | 0/6/20 | 0/3/5 | 0/4/16 | 0/21/83 |
| Norte | 0/10/36 | 0/1/9 | 0/4/14 | 0/1/5 | 0/5/14 | 0/21/78 |
| Leste | 1/6/26 | 0/2/7 | 0/2/13 | 0/0/3 | 0/1/6 | 1/11/55 |

## Motivos de reprovação

| Motivo | Lugares |
|---|---|
| dominio_inexistente | 388 |
| triagem_sem_sinal | 146 |
| site_fora_do_ar | 74 |
| precisa_js | 52 |
| sem_horario | 46 |
| menos_de_3_precos | 40 |
| bloqueia_robo | 34 |
| robots_proibe | 23 |
| sem_evento_proximo | 12 |
| sem_entrada_ou_gratuito | 11 |
| site_de_outro_negocio | 8 |
| redireciona_agregador | 5 |
| nao_html | 1 |

## Valores extraídos pelo LLM

237 valores conferidos: 184 aceitos e 53 barrados pelo validador.

| Por que foi barrado | Valores |
|---|---|
| evidencia_ausente | 29 |
| valor_fora_do_trecho | 22 |
| implausivel | 2 |

`evidencia_ausente` é o indicador de alucinação: o trecho citado não existe na página.

## Base gravada

| Coleção | Documentos |
|---|---|
| lugares | 11 |
| eventos | 0 |
| regioes | 35 |

## Consumo da extração

| Rodada | Lotes | Lugares | Texto das páginas (tokens estimados) | Total dos subagentes (tokens medidos) |
|---|---|---|---|---|
| 1 | 6 | 33 | 56274 | 546116 |
| 2 | 7 | 41 | 130318 | 1095959 |
| 3 | 4 | 22 | 48847 | 588492 |

O total medido inclui o prompt, as leituras e as escritas de arquivo de cada subagente.
