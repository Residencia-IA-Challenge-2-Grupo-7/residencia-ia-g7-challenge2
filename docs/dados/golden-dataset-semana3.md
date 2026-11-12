# Golden Dataset da Semana 3 (RAG vs. IA Pura)

Arquivo: `data/golden_dataset_semana3.json`
Testes: `tests/test_golden_dataset.py` (rodam no CI)
Origem: issue #31 (parte 1: `golden_01` a `golden_10`)

Conjunto de perguntas com gabarito ancorado na base oficial
`data/banco_aprovado_2fa.json`. Usado na comparação A/B entre a LLM pura e o
nosso RAG (#32), para medir alucinação, precisão de preço e horário (RNF-03) e
cobertura fora do Plano Piloto (RNF-13).

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

## Categorias

| Categoria | Parte 1 | O que testa |
|---|---|---|
| `geoespacial_ra_fora_centro` | 5 | Encontrar lugares reais fora do Plano Piloto (RNF-13) |
| `janela_horario` | 3 | Respeitar horários reais (madrugada depois da 1h, domingo) |
| `fora_de_escopo_df` | 2 | Recusar perguntas sobre outras cidades |

Comportamento esperado em `fora_de_escopo_df`: o RAG **recusa** e informa que
o app cobre só o DF. Recomendar qualquer lugar, inclusive do DF, conta como erro.

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

## Como adicionar casos (parte 2: `golden_11` a `golden_20`)

1. Continue a sequência de IDs a partir de `golden_11`, no fim da lista.
2. Novas categorias são permitidas; só `fora_de_escopo_df` aceita `null`.
3. Siga as regras acima, principalmente a 1: copie nome, RA e preço da base.
4. Rode antes de commitar:

   ```bash
   PYTHONPATH=. pytest -v tests/test_golden_dataset.py
   ```

   Os testes de campos e de evidência rodam em todos os casos, inclusive nos
   novos. Se um caso falhar, o nome do teste mostra qual (`[golden_XX]`).