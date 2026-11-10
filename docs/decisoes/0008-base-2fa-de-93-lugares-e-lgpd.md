# 0008 — Base oficial de 93 lugares (validação em 2 fatores) e conformidade com a LGPD

- **Status:** aceita (decisão do grupo registrada no [guia oficial](../../GUIA_OFICIAL_PROJETO.md) de 10/11). As medidas de LGPD da seção "Decisão" são proposta deste ADR e precisam da revisão do grupo
- **Data:** 2026-11-10
- **Semana do roadmap:** 3 — Comparação RAG × LLM pura
- **Substitui:** o [ADR 0005](0005-coleta-automatica-e-base-vetorial.md) (coleta nos sites oficiais com Overture, Postgres com pgvector e BGE-M3) e o que ainda valia do [ADR 0004](0004-fonte-e-manutencao-da-base.md) sobre fontes (Overture como candidatos, conferência na Google Places). O código de `src/base/` saiu do repositório
- **Requisitos:** RF-16, RF-17, RF-11 · RNF-01, RNF-02, RNF-03, RNF-13

## Contexto

A coleta do ADR 0005 não fechou uma base usável: depois de varrer 811 sites, ficaram 11 lugares, 9 no Centro, porque a maioria dos sites da Overture estava fora do ar e quase nenhum publicava preço em texto ([resultado do piloto](0005-coleta-automatica-e-base-vetorial.md#resultado-do-piloto-0311)).

Em paralelo, a Letícia montou a base da semana 2 a partir de vídeos de um perfil público de rolês no TikTok (`@rolezandoembrasilia`). O fluxo, em `src/rag/coletor_tiktok_2fa.py`:

1. catalogou 164 vídeos publicados entre jan. e out. de 2026;
2. extraiu nome, tipo, vibes, preço, horário e endereço da legenda e da transcrição do áudio, com LLMs (Groq `qwen3.8-27b` em 66 lugares, `gpt-oss-120b` em 19, Gemini `3-flash-preview` em 8);
3. aplicou duas travas (o "2FA"): **localização** confirmada no DF e **preço** citado no vídeo;
4. mandou 71 vídeos para a quarentena: 47 descartados por não serem rolê e 24 retidos por falta de um dos dois fatores;
5. gerou vetores de 3072 dimensões (`gemini-embedding-001`) para os 93 aprovados.

O grupo decidiu em 10/11 que essa é a base oficial do app ([guia oficial](../../GUIA_OFICIAL_PROJETO.md), seção 1, item 4). Faltava registrar a decisão, os riscos e o que a LGPD exige dela e do app que a usa.

## Opções consideradas

1. **Continuar o ADR 0005 (sites oficiais):** dados de primeira mão e termos mais claros, mas 11 lugares em 811 tentativas e quase nada fora do Centro. Não dá uma semana 3 nem um app.
2. **Base 2FA do TikTok (escolhida):** 93 lugares com preço e quase todos com endereço, já usados na entrega da semana 2. Depende de uma fonte só e dos termos de uma plataforma.
3. **Google Places ou Tripadvisor como base:** os termos proíbem guardar os dados ou usá-los com IA ([ADR 0004](0004-fonte-e-manutencao-da-base.md) e estudo de 05/11 no ADR 0005).

## Decisão

A base oficial é `data/banco_aprovado_2fa.json` (93 lugares), com `data/banco_vetorial_embeddings.json` para a busca. Toda sugestão do app sai dela (RF-16), e quem monta os cartões é código (`src/salas/sugestoes.py`), não o LLM.

Regras de uso da base no app:

- **Fonte em todo cartão:** link do vídeo, autor e data de publicação. O preço e o horário são "segundo o vídeo".
- **Sem republicar o conteúdo:** o app mostra fatos curtos (nome, endereço, faixa de preço, horário) e o link; a legenda e a transcrição completas não aparecem na interface.
- **Horário lido por código, com cautela:** `src/salas/horario_lugar.py` classifica cada lugar em aberto, provável, incerto, fechado ou encerrado para a janela do grupo. Eventos com datas passadas saem da sugestão (RNF-03). "Consultar no local" (21 lugares) entra com aviso para confirmar.
- **Remoção a pedido:** se o autor do perfil ou um estabelecimento pedir, o item sai da base na rodada seguinte.

Medidas de LGPD para os dados das pessoas (proposta):

| Dado | Medida |
|---|---|
| Os 4 campos da Tela 2 | Só a interpretação fica guardada (RA, janelas, teto, tags); o texto digitado não é persistido. Origem é a RA, nunca o endereço. Nada disso vai para LLM externo, exceto o texto de horários quando as regras não o entendem ([ADR 0009](0009-entrada-pelos-4-campos-de-texto.md)) |
| Teto de gasto (RNF-02) | Só o dono vê. O painel do grupo, os cartões e as explicações nunca o mostram nem atribuem descarte a alguém ("fora do orçamento do grupo"). Teste automático procura o valor na resposta pública |
| Idade | Declaração de 18 anos ou mais; quem declara menos não tem nada guardado (RF-01) |
| Tokens de acesso | Só o hash SHA-256 fica no banco |
| Banco na nuvem (Supabase) | Região São Paulo (`sa-east-1`), chave só no `.env`, salas apagadas 30 dias depois do rolê (prazo a confirmar com o grupo) |
| Foto da nota fiscal e chave Pix (semana 5) | Consentimento separado (RF-02) e tratamento definido no ADR da semana 5 |

## Justificativa e evidências

- Cobertura: 93 lugares em 21 grafias de RA, contra 11 lugares da coleta do ADR 0005. Fora do Plano Piloto há 51 (Taguatinga 13, Águas Claras 11, Vicente Pires 8 e outras).
- Preço: 100% dos 93 têm `custo_medio_rs`, que é a trava 2 do 2FA. O ADR 0005 não achou preço em texto em nenhum site da amostra inicial.
- Rastreabilidade: cada item guarda o link do vídeo, a legenda e a transcrição, o que permite auditar o preço e o horário (RNF-03) e é o que a comparação RAG × LLM pura da semana 3 usa como gabarito.

## Riscos e limitações

- **Termos do TikTok e direito autoral:** a coleta automática de vídeos e a reprodução de legendas e falas podem violar os termos da plataforma e os direitos do autor. Por isso o app mostra só fatos curtos e o link. Para uso além do acadêmico, é preciso pedir permissão por escrito ao autor do perfil. **Risco aberto.**
- **Fonte única e viés:** os 93 lugares vêm de um só criador de conteúdo. A escolha dele concentra a base no Plano Piloto (42 de 93) e em restaurantes (61 de 93), e pode incluir conteúdo patrocinado sem marcação. A ampliação nas RAs periféricas (guia, tarefa da Samara e da Letícia) reduz, mas não elimina, esse viés (RNF-13).
- **Dados envelhecem:** preço e horário valem para a data do vídeo (jan. a out. de 2026). Sem reconferência periódica, o "aproximado" do RF-16 vira a regra.
- **Coordenadas:** 47 lugares usam o centroide da RA, 41 foram geocodificados pelo OpenStreetMap e 5 não tiveram correspondência exata. Os 2 eventos marcados como Gama têm coordenadas no Plano Piloto, e o lugar de Planaltina não tem coordenadas. O tempo de deslocamento desses lugares sai errado ou não sai, até a revisão da base.
- **Horário em texto livre:** 14 itens são eventos ou promoções já encerrados e 21 dizem só "Consultar no local". A leitura por código erra em frases com exceções ("segunda-feira apenas no jantar").
- **Extração por LLM:** os campos foram preenchidos por três modelos diferentes. A trava 2FA confere a presença de localização e preço, não se o valor extraído é o do vídeo.

## Como vamos validar

- **RNF-03:** 100% dos lugares dos cartões existem na base (teste automático em `tests/test_salas.py`); amostra de 30 itens conferida à mão contra o vídeo, com meta de pelo menos 95% de preço e horário corretos. A mesma amostra entra na comparação RAG × LLM pura da semana 3.
- **Sigilo (RNF-02):** a bateria de testes da API procura o teto de cada participante nas respostas públicas. Meta: nenhum vazamento.
- **Cobertura (RNF-13):** proporção de lugares fora do Plano Piloto antes e depois da ampliação, e tempo máximo de deslocamento nas salas de teste com pessoas de Ceilândia e Samambaia.
- **Atualidade:** quantos cartões saem com horário "incerto" ou evento encerrado por rodada de teste.
