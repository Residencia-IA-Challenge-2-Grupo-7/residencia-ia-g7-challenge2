# Interpretador de mensagens

> **Desde 10/11 (guia oficial):** o app não tem voz nem conversa privada. A Tela 2 usa os **4 campos de texto** em `campos.py` ([ADR 0009](../../docs/decisoes/0009-entrada-pelos-4-campos-de-texto.md)), resolvidos por regras; este interpretador de mensagens livres fica como reserva do campo de horários e para os agentes da semana 4. A opção `--audio` dependia de `src/voz/`, que saiu do repositório.
>
> ```python
> from src.interpretador.campos import interpretar_campos
> p = interpretar_campos("Águas Claras perto da estação", "sexta depois das 19h ou sábado à tarde", "60",
>                        "Barzinho ou café calmo, sou vegetariana, vou de metrô/Uber", agora=datetime.now())
> p.resumo      # "sex 13/11, 19h–24h; sáb 14/11, 13h–18h; saindo de Águas Claras; teto de R$ 60,00 (só você vê); ..."
> p.pendencias  # {} ou {"origem": "Não reconheci essa região do DF...", ...}
> ```

Implementação do [ADR 0007](../../docs/decisoes/0007-interpretador-e-contrato-de-busca.md): texto digitado ou transcrito vira uma lista de intenções estruturadas (`pedido_role`, `disponibilidade`, `orcamento`, `gasto`, `busca_lugar`, `outra`), cada uma com destino, confirmação ou pergunta.

O fluxo:

1. O código troca os nomes dos membros por `@m1`, `@m2`…
2. O LLM preenche um JSON Schema estrito, com fichas de dia, período, `HH:MM` e o **trecho literal** dos valores.
3. O Pydantic valida a saída.
4. O código resolve as datas a partir da hora da mensagem, converte os valores e confere se o trecho está na mensagem.
5. O código casa as RAs, monta a `ConsultaBusca` do [contrato](contrato.py) e decide confirmação, pergunta e destino.

O LLM não vê a data de hoje, não calcula nem escreve SQL.

| Módulo | Papel |
|---|---|
| `campos.py` | Os 4 campos da Tela 2 → RA, janelas, teto, tags e resumo, por regras ([ADR 0009](../../docs/decisoes/0009-entrada-pelos-4-campos-de-texto.md)) |
| `contrato.py` | Contrato tipado da busca (`ConsultaBusca`, `ResultadoBusca`) |
| `config.toml` | Modelo, roteamento da OpenRouter (retenção zero, sem fp4), tabela de horários, apelidos de RAs, pontos de referência e estações |
| `prompts/interpretar.md` | Prompt fixo (sem data nem nomes, para cache e privacidade) |
| `esquema.py` | Esquema do LLM e resultado (`Intencao`, `Interpretacao`) |
| `tempo.py` | Fichas de dia e período → janelas com data e hora |
| `numeros.py` | Valores em reais do português falado ("120 conto", "cento e vinte", "23 e 40") |
| `pseudonimo.py`, `lugares.py` | Nomes ↔ marcadores; lugares citados → RAs |
| `interpretar.py` | Fluxo completo e encaminhamento (orçamento no grupo é ignorado) |
| `llm.py` | Cliente da OpenRouter com saída estruturada |
| `avaliar.py` | Métricas no conjunto de [eval/interpretador/](../../eval/interpretador/) |

## Preparar

`OPENROUTER_API_KEY` no `.env` da raiz (fora do git). O modelo e as reservas ficam em `config.toml`.

## Rodar

Da raiz, com `PYTHONPATH=src`:

```bash
python -m interpretador "sexta depois das 19h e no máximo 50 conto"
python -m interpretador "o Caio pagou 90 do Uber" --contexto grupo --autor Bia
python -m interpretador "tem bar tranquilo em Taguatinga até 50?" --buscar   # precisa do Postgres
python -m interpretador --audio gravacao.m4a                                # transcreve antes (ADR 0006)
python -m interpretador avaliar                                             # 50 frases, texto
python -m interpretador avaliar --transcricoes eval/resultados/transcricoes-<rodada>.json   # a partir da voz
python -m interpretador avaliar --modelo <outro/modelo>                     # comparar modelos
```

`avaliar` grava `eval/resultados/interpretador-*.json` e imprime a tabela: intenção, campos, frases certas, RNF-08 com o limite inferior de Clopper-Pearson, perguntas, sigilo, latência p50/p90 e custo.
