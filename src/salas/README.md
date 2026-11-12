# Salas, cartões e votação

Back-end das Telas 1 a 3 do [guia oficial](../../GUIA_OFICIAL_PROJETO.md): criar sala, receber os 4 campos secretos, cruzar os horários, gerar 3 a 4 cartões com lugares da base de 93 e fechar a votação com "🎉 Rolê orquestrado com sucesso!".

Tudo é calculado por código (RNF-04). O LLM só entra como reserva do campo de horários ([ADR 0009](../../docs/decisoes/0009-entrada-pelos-4-campos-de-texto.md)).

## Módulos

| Arquivo | Papel |
|---|---|
| `../interpretador/campos.py` | Os 4 campos → RA, janelas, teto, tags e resumo para confirmar ([ADR 0009](../../docs/decisoes/0009-entrada-pelos-4-campos-de-texto.md)) |
| `../state.py` | Onde as salas ficam (`Repositorio`); hoje em memória, depois no Supabase |
| `modelos.py` | Sala, Participante, Sugestao (cartão), Resultado; o que é segredo está marcado |
| `gerenciador_salas.py` | Regras: 18+, 2 a 20 pessoas, tokens, confirmar, gerar, votar, fechar, resumo para WhatsApp e link da agenda |
| `janelas.py` | Cruzamento das disponibilidades (RF-13): janelas com mais gente, de pelo menos 2 h |
| `horario_lugar.py` | Lê o `horario_funcionamento` da base: aberto, provável, incerto, fechado ou encerrado (RF-17) |
| `sugestoes.py` | Filtro de horário e orçamento, deslocamento, Menor Miséria e pontuação dos cartões |
| `integracoes.py` | Onde entram as peças da Eduarda, da Samara e da Letícia (abaixo) |
| `rotas.py` | Rotas FastAPI em `/api/salas` |

## Rotas

Criar a sala devolve o `token_organizador`; entrar devolve o `token` do participante. Os dois vão no cabeçalho `X-Token`. Documentação interativa em `/docs`.

| Rota | Quem | O que faz |
|---|---|---|
| `POST /api/salas` | qualquer um | `{nome_role, organizador, maior_de_idade}` → código (`ROLE-7KQ2`), link de convite e token do organizador |
| `GET /api/salas/{codigo}` | qualquer um | Painel: quem preencheu, "x de y", cartões, placar, resultado. Nunca mostra teto, origem nem horários |
| `POST /api/salas/{codigo}/participantes` | quem tem o link | `{nome, maior_de_idade, origem, horarios, teto, preferencias}` → token e resumo para confirmar |
| `PUT /api/salas/{codigo}/participantes/{id}` | o participante | Reenvia os 4 campos (resumo errado ou pergunta pendente) |
| `POST /api/salas/{codigo}/participantes/{id}/confirmar` | o participante | "Confirmar em Segredo"; recusa se houver pendência |
| `GET /api/salas/{codigo}/participantes/{id}` | o participante | O próprio perfil (com o teto) e o próprio custo e tempo em cada cartão |
| `POST /api/salas/{codigo}/gerar-sugestoes` | o organizador | Cruza horários e devolve 3 a 4 cartões (precisa de 2 confirmados) |
| `POST /api/salas/{codigo}/votar` | o participante | `{participante_id, opcoes: ["A", "C"]}`; fecha sozinha quando todos votam |
| `POST /api/salas/{codigo}/fechar-votacao` | o organizador | Fecha sem esperar quem não votou |

Exemplo de ponta a ponta:

```bash
curl -s -X POST localhost:8000/api/salas -H 'content-type: application/json' \
  -d '{"nome_role":"Aniversário da Galera","organizador":"Rafaela","maior_de_idade":true}'
curl -s -X POST localhost:8000/api/salas/ROLE-7KQ2/participantes -H 'content-type: application/json' \
  -d '{"nome":"Bia","maior_de_idade":true,"origem":"Águas Claras perto da estação","horarios":"sexta depois das 19h ou sábado à tarde","teto":"60","preferencias":"Barzinho ou café calmo, sou vegetariana, vou de metrô/Uber"}'
```

## Como os cartões são montados

1. **Janela:** as melhores janelas comuns (mais gente, depois a mais próxima). O grupo vê só "4 de 5 podem".
2. **Horário do lugar:** primeira janela em que o lugar não está fechado nem encerrado. Eventos com data passada saem.
3. **Deslocamento:** para cada pessoa, entre os meios que ela disse que usa, o mais barato que chega em até 75 min.
4. **Orçamento:** consumo ≤ teto do grupo, e consumo + transporte de cada pessoa ≤ teto dela. O descarte é "fora do orçamento do grupo".
5. **Pontuação:** 45% aderência ao pedido (tipos, vibes, restrições e a busca da Letícia), 35% nota de justiça (Menor Miséria), 20% certeza do horário. No máximo 2 cartões por RA.
6. **Desempate da votação:** melhor nota de justiça, depois a posição no ranking (RF-25).

## Encaixe das peças das colegas

`integracoes.py` procura as funções abaixo e, se não achar, usa uma reserva simples. Basta criar o módulo com a assinatura indicada; nada mais muda.

| Peça | Dona | Função esperada | Reserva atual |
|---|---|---|---|
| Teto seguro do grupo | Cauan (issue #45) | `src/financas/__init__.py`: `teto_seguro_grupo(tetos: list[Decimal]) -> Decimal` (**pronto**) | o menor teto |
| Deslocamento | Samara | `src/logistica/transporte_df.py`: `estimar_deslocamento(ra_origem: str, lat: float, lng: float, modo: str) -> dict` com `km`, `minutos`, `custo_ida_volta` | linha reta entre centroides × 1,3; ônibus/metrô a 18 km/h + 15 min, carro e app a 30 km/h + 5 min; R$ 5,50 a passagem |
| Nota de justiça | Samara | `src/logistica/transporte_df.py`: `nota_menor_miseria(deslocamentos: list[dict]) -> float` (0 a 100) | 100 − 0,8 × (pior tempo − 20) − 0,3 × (pior − melhor); 30 sem dado |
| Centroides das RAs | Samara | `data/regioes_df_gps.json`, `{ra: {lat, lng}}` ou lista com `ra`, `lat`, `lng` | média das coordenadas da base por RA |
| Aderência ao pedido | Letícia | `src/telemetria/telemetria.py`: `calcular_similaridade_leticia(pergunta, lugar)` (já existe) | contagem de tags |
| Banco das salas | Eduarda | um `Repositorio` (`existe`, `obter`, `salvar`) em `src/db/`, ligado por `ROLES_REPOSITORIO=supabase` em `src/state.py` | memória (perde tudo ao reiniciar) |

`modo` é um de `publico`, `app`, `carro`, `carona`, `a_pe`, `bike`.

## Testes

```bash
python -m pytest tests/test_campos.py tests/test_salas.py tests/test_salas_backend.py
```

Cobrem os exemplos do guia, o cruzamento, o horário dos lugares, o orçamento por pessoa, 18+, limite de 20, tokens, votação múltipla com desempate e uma varredura das respostas públicas atrás do teto de cada um.

## Limitações conhecidas

- O repositório em memória perde as salas quando o servidor reinicia (o Render reinicia sozinho). Falta o Supabase.
- A reserva de deslocamento erra onde a base tem coordenadas erradas (os 2 eventos do Gama estão no Plano Piloto; o lugar de Planaltina não tem coordenadas).
- 21 lugares dizem só "Consultar no local": entram com aviso e pesam menos.
- Prazos de resposta (RF-12), modo "palavra final do organizador" (RF-24), regra de datas do organizador (RF-14) e confirmação de presença (RF-26) ainda não existem.
