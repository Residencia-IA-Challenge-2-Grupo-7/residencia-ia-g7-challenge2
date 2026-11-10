# Semana 3 — Comparação RAG × LLM pura (e Telas 1 a 3 do app)

**Entregável:** comparação entre respostas da LLM pura e do RAG, com evidências. Em paralelo, o app real ([guia oficial](../../GUIA_OFICIAL_PROJETO.md), seção 4).

## Registro

- 2026-11-10: o grupo publicou o [guia oficial](../../GUIA_OFICIAL_PROJETO.md) na `main`, que passa a ser a fonte da verdade sobre o app: ciclo completo do rolê com pós-rolê e Pix, sem voz, 4 campos de texto secretos, base oficial de 93 lugares do TikTok, transporte pelas 35 RAs com a regra da Menor Miséria e banco no Supabase. `src/base/` e `src/voz/` saíram do repositório.
- 2026-11-10 (Cauan): back-end das Telas 1 a 3 na branch `feat/salas-backend`.
  - Os 4 campos viram perfil por regras (`src/interpretador/campos.py`): RA por apelidos, siglas de quadra e estações de metrô; janelas pelo `tempo.py`; teto pelo `numeros.py`; tags com os rótulos da base. O LLM do ADR 0007 só entra se as regras não acharem nenhum dia.
  - Salas, cruzamento de horários, leitura do horário de funcionamento dos lugares, cartões com Menor Miséria e votação múltipla em `src/salas/`, com o estado em `src/state.py` e as rotas em `/api/salas`.
  - As peças da Eduarda (teto do grupo, Supabase), da Samara (deslocamento, nota de justiça) e da Letícia (busca) entram por `src/salas/integracoes.py`, com uma reserva simples até chegarem.
  - 59 testes novos; 99 no total. O CI passou a rodar todos.
  - ADR 0008 (base de 93 lugares e LGPD) e ADR 0009 (4 campos, sem voz); requisitos v0.4 com a voz removida.
- 2026-11-10: a leitura do horário de funcionamento dos 93 lugares, num sábado à noite, deu 32 abertos, 5 prováveis, 23 incertos, 19 fechados e 14 encerrados (eventos e promoções com datas passadas). Os 2 eventos do Gama têm coordenadas no Plano Piloto, e o lugar de Planaltina não tem coordenadas.

## Decisões da semana

- [ADR 0008](../decisoes/0008-base-2fa-de-93-lugares-e-lgpd.md): base oficial de 93 lugares com validação em 2 fatores e medidas de LGPD (substitui o ADR 0005).
- [ADR 0009](../decisoes/0009-entrada-pelos-4-campos-de-texto.md): entrada pelos 4 campos de texto, interpretados por regras, sem voz (substitui o ADR 0006).

## Aprendizados e dúvidas

- Com os campos separados, a intenção de cada texto já é conhecida, e regras simples resolvem os exemplos do guia sem mandar localização nem dinheiro para um LLM externo.
- Checar o orçamento pelo menor teto do grupo contra o maior gasto descartava lugares demais: misturava o teto de uma pessoa com o transporte de outra. A checagem por pessoa (consumo + transporte dela ≤ teto dela), feita só no servidor, segue o RF-17 sem expor ninguém.
- Quem diz "metrô ou Uber" não deve pagar Uber à toa: o deslocamento escolhe o meio mais barato que chega em até 75 minutos.
