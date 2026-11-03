# Mapa da arquitetura: como editar

`index.html` é o mapa navegável da arquitetura, num arquivo só. Esta pasta é a fonte; o site em <https://residencia-ia-challenge-2-grupo-7.github.io/residencia-ia-g7-arquitetura/> é uma cópia, publicada por `publicar.sh` num repositório público à parte (o plano gratuito da organização não tem Pages em repositório privado).

## Quando atualizar

Na mesma sessão em que a mudança acontece, sem esperar alguém pedir. Atualize o mapa quando o seu trabalho:

- decidir algo que está como proposta ou a decidir (um ADR aceito, uma tecnologia escolhida);
- criar, juntar ou remover um componente, um agente, uma tela ou um serviço externo;
- construir algo que estava planejado (a situação passa a `ok`);
- mudar um fluxo, uma regra ou um requisito citado num card.

## O que ler

Só o bloco de dados, entre `/* ===== DADOS DO MAPA` e `/* ===== FIM DOS DADOS`. O estilo acima e o motor do mapa abaixo não precisam ser lidos.

```bash
grep -n "DADOS DO MAPA\|FIM DOS DADOS" docs/arquitetura/index.html
```

Para achar o que mexer, procure pelo id ou pelo requisito (`grep -n "RF-16\|r-base" docs/arquitetura/index.html`).

| Constante | O que é |
|---|---|
| `ATUALIZADO`, `SUBTITULO` | Data e frase do cabeçalho. Atualize a data a cada edição |
| `ZONES` | As áreas do mapa: posição, título e a lista `st` de tecnologias e escolhas (o painel "stack") |
| `CARDS` | Cada caixa do mapa |
| `EDGES` | As setas entre cards |
| `TOURS` | Os fluxos guiados: cada passo destaca cards (`c`) e mostra um texto (`tx`) |
| `DEC` | As decisões do painel "Decisões": grupo `g`, título `t`, origem e situação `s`, texto `tx`, cards `c` |

## Campos de um card

| Campo | Obrigatório | Uso |
|---|---|---|
| `id` | sim | Prefixo da zona: `p-` pessoas, `f-` app, `b-` servidor, `ia-` e `s1`…`s7` agentes, `e-` externos, `i-` segurança, `r-` e `d-` base e avaliação, `c-` motor |
| `k` | sim | Formato: `pessoa`, `tela`, `rota`, `seg`, `regra`, `ia`, `etapa`, `banco`, `dados`, `infra`, `externo` |
| `z`, `x`, `y`, `w` | sim | Zona e posição em px (veja a grade abaixo) |
| `eb`, `t` | sim | Rótulo pequeno de cima e título |
| `st` | quase sempre | Situação: `ok` (pronto), `plan` (nos requisitos), `prop` (proposta), `aberto` (a decidir) |
| `tx`, `ch` | não | Texto curto do card e chips |
| `far` | não | Nome curto que aparece de longe, quando o título é comprido |
| `faz`, `entra`, `sai`, `pq`, `num`, `fora` | não | Painel de detalhes: como funciona, entradas e saídas, por que assim, números, o que falta |
| `rq` | não | Onde está definido (requisitos, ADRs) |
| `tbl`, `flow` | não | Tabela ou fluxo de estados dentro do card |

## Receitas

- **Mudou a situação:** troque `st` e o texto que dizia "a decidir" ou "proposta", inclusive em `fora`, no `st` da zona e na decisão correspondente em `DEC`.
- **Nova decisão:** acrescente um item em `DEC`, com `s` dizendo a origem (ex.: `'ADR 0004 · aceita'`).
- **Novo card:** copie um card do mesmo formato na mesma coluna, troque o `id` e ponha num espaço livre. Ligue com `{a:'origem', b:'destino', k:'interno'}`; os tipos de seta estão em `EDGE_KINDS`.
- **Card removido:** apague também as setas, os passos de fluxo e as decisões que citam o `id`. O `checar.mjs` aponta o que sobrou.
- **Setas:** sem `via`, a seta é desenhada sozinha entre os lados mais próximos. Use `via` (pontos em px, com `s` e `t`) só quando ela atravessar outros cards; copie um exemplo que já existe.

## Grade

Os cards ficam em colunas fixas. As alturas variam com o texto, por isso confira no navegador.

| Zona | Colunas (x, largura) | Linhas (y) | Espaço livre |
|---|---|---|---|
| Pessoas | 70 (260) | 175, 470, 800 | y ≈ 1010 |
| App web | 470 e 820 (245) | 175, 445, 715, 985 | nenhum |
| Servidor | 1280 e 1635 (245) | 175, 445, 750, 1020 · 175, 615, 905 | nenhum |
| Agentes de IA | 2080 (250) · etapas 2400 (300) · 2780 (300) | a cada ~215 · a cada 132 · 175, 435, 695, 955 | nenhum |
| Fora do sistema | 3210 (285) | 175, 375, 575, 775, 1000 | nenhum |
| Segurança, Base e avaliação, Motor | 70 · 470 a 1630, a cada 290 (250) · 2080 a 3160, a cada 360 (330) | 1395, 1660 | nenhum |

Sem espaço: prefira juntar a informação num card que já existe. Se precisar mesmo de uma linha nova, a fileira de baixo pode crescer: some 265 ao `h` das três zonas de baixo e ao `H`, e use y = 1925. Nesse caso, desça também a seta `d-form → d-metricas`, que corre por baixo da zona.

## Conferir e publicar

1. `node docs/arquitetura/checar.mjs`: sintaxe, ids, referências e limites das zonas. Precisa terminar com 0 erro.
2. Se mexeu em posição ou em texto longo, abra o mapa com `?checar` no fim do endereço, servindo a pasta (`python -m http.server` dentro dela) ou no site publicado. Um aviso no canto mostra cards encostados, setas que atravessam cards e rótulos sobre cards.
3. Só quando o usuário pedir para subir: commite no repositório principal e rode `bash docs/arquitetura/publicar.sh "o que mudou"`.

## Cuidados

- O site é público: nada de nomes de integrantes ou mentores, dados pessoais, links de documentos internos ou segredos. As personas (Rafaela, Cadu, Bia, Márcio) são fictícias e podem aparecer.
- Não invente tecnologia: o que não foi decidido continua "a decidir".
- Texto em português, curto e direto. Nas etapas (`k:'etapa'`), o `tx` cabe em uns 115 caracteres.
- Use aspas simples nos textos do JavaScript; não use apóstrofo dentro deles.
