# Conjuntos de teste e resultados de medição

| Caminho | Conteúdo |
|---|---|
| `interpretador/frases.jsonl` | 50 frases com a saída esperada (intenções e campos resolvidos), os termos críticos para a voz e o código de quem grava. Data de referência: qui 05/11/2026 10h ([ADR 0007](../docs/decisoes/0007-interpretador-e-contrato-de-busca.md)) |
| `interpretador/sala.json` | Sala fictícia (membros) e data de referência |
| `voz/roteiro.md` | Como a equipe grava as frases, com o termo de consentimento ([ADR 0006](../docs/decisoes/0006-transcricao-de-fala.md)) |
| `comparativo_ab.py` | Roda o comparativo A/B (issue #34) em todos os casos do golden e grava o JSON bruto para a avaliação das issues #36 e #38 ([ADR 0011](../docs/decisoes/0011-comparativo-ab-com-o-mesmo-llm.md)) |
| `llm_pura_raciocinio.py` | Modo A sem raciocínio × raciocínio alto ([experimento](../docs/experimentos/2026-11-10-llm-pura-raciocinio.md)) |
| `resultados/` | Saída de `python -m voz medir` e `python -m interpretador avaliar` (sem áudio) |

O gabarito foi escrito em 05/11 e **precisa da revisão do grupo**. Para mudar uma frase, edite a linha e confira as datas pela data de referência. Os áudios nunca entram aqui: ficam em `data/raw/voz/` (fora do git).
