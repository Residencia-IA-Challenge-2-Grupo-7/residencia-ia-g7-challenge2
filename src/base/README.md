# Pipeline da base de lugares e eventos

Implementação do [ADR 0005](../../docs/decisoes/0005-coleta-automatica-e-base-vetorial.md): candidatos da Overture, robô nos sites oficiais, extração por LLM com evidência literal, validação em código e PostgreSQL com pgvector. Nenhum campo é digitado por uma pessoa.

## Preparar o ambiente

```bash
python -m venv .venv
.venv/Scripts/python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
.venv/Scripts/python -m pip install -r requirements.txt
docker compose up -d --wait
```

O Postgres fica em `127.0.0.1:5434` (ver `docker-compose.yml`). Em outro ambiente, defina `BASE_DSN`.

## Rodar

Rode da raiz do repositório com `PYTHONPATH=src`; cada etapa grava a sua saída e pode ser repetida.

| Etapa | Comando | Saída |
|---|---|---|
| 1. Descobrir | `python -m base descobrir` | `data/processed/candidatos.csv` |
| 2. Selecionar | `python -m base selecionar` (piloto de 100) ou `--repor --n 150` | `sorteio.csv`, `selecionados.csv` |
| 3. Rastrear | `python -m base rastrear` | `data/raw/paginas/<id>/` com manifesto e hashes |
| 3b. OCR | `python -m base ocr` (EasyOCR local; cardápio em imagem e PDF escaneado) | páginas `ocr-*.txt` no manifesto |
| 4. Extrair | `python -m base preparar`, depois um subagente Haiku por lote | `data/processed/extracao/saida/<id>.json` |
| 5. Validar | `python -m base validar` | `validados.json`, `evidencias.jsonl` (interno) |
| 7a. Descrever | `python -m base descrever`, depois um subagente Haiku | `descricao/saida.json` |
| 7. Calcular | `python -m base calcular` | `fichas.json` e os CSVs de `data/base/` |
| 8. Vetorizar | `python -m base vetorizar [--modelo intfloat/multilingual-e5-large]` | `data/processed/vetores/*.npz` |
| 9. Gravar | `python -m base gravar` | tabelas no Postgres |
| 10. Relatar | `python -m base relatar` | `data/base/relatorio.md` |
| Comparar com a Google | `python -m base comparar-google` (chave em `.env`; grava só contagens, nenhum valor da Google) | `data/processed/comparacao_fontes.json` |
| Medir o OSM | `python -m base osm` (consulta pelo Overpass; nada é importado, por causa da ODbL) | `data/processed/osm_medicao.json` |
| Consulta de teste | `python -m base buscar "lugar tranquilo para conversar" --regiao centro --teto 60` (ou `--ra Taguatinga`, `--dia sab --hora 21:00`) | Monta uma `ConsultaBusca` do [contrato](contrato.py) (ADR 0007) |

Os agentes usam a busca pelo contrato de [contrato.py](contrato.py): `buscar.buscar(ConsultaBusca) → ResultadoBusca`. A SQL é montada só com parâmetros, a partir dos campos validados ([ADR 0007](../../docs/decisoes/0007-interpretador-e-contrato-de-busca.md)).

A etapa 6 (casar com a Google) é opcional e depende da conta de faturamento; não está implementada.

## Extração com o Haiku

Antes, uma triagem em código procura no texto sinais dos campos obrigatórios: pelo menos 3 preços e um horário para comer e beber; horário e "gratuito" ou preço para ao ar livre; uma data futura para locais de evento. Quem não passa não vai para o LLM (`extracao/triagem.json`). `preparar` monta um arquivo de texto por lugar que passou e divide os lugares em lotes (`data/processed/extracao/lotes/lote-NN.txt`). Cada lote é lido por um subagente Claude Haiku 5.5, que segue o prompt [prompts/extracao_lugar.md](prompts/extracao_lugar.md), só com leitura e escrita de arquivos. O pipeline não confia na saída: `validar` confere cada valor contra o texto salvo da página. O consumo estimado de cada rodada fica em `data/processed/extracao/consumo.jsonl`.

Para a rodada semanal sem ninguém na frente (semana 4), a mesma entrada e o mesmo prompt podem ir para a API com `claude-haiku-5-5`; esse backend ainda não existe.

## Testes

```bash
PYTHONPATH=src .venv/Scripts/python -m pytest -q tests
```
