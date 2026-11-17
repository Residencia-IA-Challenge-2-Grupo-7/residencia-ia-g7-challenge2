# src/financas — orçamento sigiloso, divisão da conta e Pix

Issue #45. Tudo em código, sem modelo de linguagem (RNF-04), e sem dependências novas.

| Arquivo | O que faz | Requisitos |
|---|---|---|
| `orcamento.py` | Teto do grupo e "cabe no orçamento?" sem expor o teto de ninguém | RF-11, RF-17, RNF-02 |
| `divisao_conta.py` | Divide a conta entre os presentes, com itens que só parte consumiu | RF-32 |
| `pix.py` | Código Pix copia e cola estático (BR Code do Banco Central, com CRC16) | RF-33 |

```python
from decimal import Decimal
from src.financas import ItemConta, cabe_no_orcamento, dividir_despesa

cabe_no_orcamento(Decimal("45"), [Decimal("80"), Decimal("60")])        # True

d = dividir_despesa(Decimal("200"), ["rafaela", "bia", "cadu"], pagador="rafaela",
                    exclusoes_por_item=[ItemConta(Decimal("60"), frozenset({"bia"}), "chope")])
d.devidos                     # {"bia": Decimal("46.66"), "cadu": Decimal("76.66")}
d.para_rateios()              # no formato da tabela despesa_rateios (src/db/models.py)
d.codigos_pix(chave="rafaela@email.com", nome="Rafaela Souza")   # {"bia": "000201...", "cadu": "000201..."}
```

## Orçamento (RF-11, RNF-02)

- As funções recebem os tetos como lista, sem nomes. O resultado nunca diz de quem é o teto.
  - `calcular_teto_grupo` devolve o menor teto informado. É o valor exato de uma pessoa, então é só para uso interno do servidor.
  - `cabe_no_orcamento` e `cabe_para_cada_um` respondem só sim ou não. A segunda serve quando o custo muda por pessoa, por exemplo com o transporte de cada uma (RF-17).
- `explicar_descarte()` devolve a frase fixa "fora do orçamento do grupo".
- `teto_de_quem_nao_respondeu` segue o cenário "sem resposta" do RF-11: usa o padrão do perfil ou, se não houver, o menor teto informado no grupo.
- **Encaixe com as salas:** `teto_seguro_grupo` é a função que `src/salas/integracoes.py` procura. Com este módulo na branch, as salas passam a usá-lo sozinhas.

## Divisão da conta (RF-32)

- O que sobra do total, fora os itens com exclusões, é dividido igualmente entre todos os presentes. Cada item é dividido só entre quem o consumiu.
- Os itens aceitam dois formatos: `ItemConta(valor, excluidos, descricao)`, ou o dicionário do banco, com `consumidores`.
- **Centavos:** as contas são feitas com frações exatas, e cada devedor paga a própria parte arredondada para baixo no centavo. A diferença fica com quem pagou (`centavos_do_pagador`), e ninguém paga mais do que a própria parte. Isso é conferido em 300 casos aleatórios nos testes.
- Quem confirmou presença e não foi não deve estar em `participantes_presentes`. Quem pagou precisa estar.

## Pix (RF-33)

- **Formato:** BR Code estático, com campos no formato `ID + tamanho + valor`:

  | Campo | Conteúdo |
  |---|---|
  | 26 | GUI `br.gov.bcb.pix`, a chave e uma descrição opcional |
  | 52, 53, 58 | Categoria, moeda (986, real) e país (BR) |
  | 54 | Valor (fica de fora se não houver valor) |
  | 59, 60 | Nome (até 25 caracteres) e cidade (até 15), sem acento |
  | 62 | Identificador `***` (código sem id de transação) |
  | 63 | CRC16 CCITT-FALSE |

- **Conferência:**
  - o CRC bate com o valor de referência do algoritmo (`"123456789"` → `29B1`);
  - o gerador reproduz, campo a campo e no CRC, um exemplo de código estático que tomamos como sendo do manual do Banco Central (não conferido na fonte original);
  - qualquer alteração no código quebra o CRC, e o banco o recusa.
- **Chave:**
  - CPF e CNPJ têm os dígitos verificadores conferidos;
  - telefone vira `+55DDDNÚMERO`;
  - e-mail e chave aleatória ficam em minúsculas;
  - telefone sem `+55` precisa de `tipo_chave="telefone"`, porque tem os mesmos 11 dígitos de um CPF.
- **Antes de pagar:** o app deve orientar o devedor a conferir no banco o nome de quem recebe e o valor. `ler_campos` separa os campos do código para mostrar isso.

## Privacidade

- Este módulo não guarda nem registra em log a chave Pix nem os tetos.
- A chave Pix é dado pessoal (pode ser CPF, telefone ou e-mail). A criptografia dela no banco (`despesas_pos_role.chave_pix`) ficou registrada para esta issue no PR #50, mas é da camada do banco (`src/db/`) e não está neste módulo.
- Cada código Pix vai só para o próprio devedor: o valor de um não deve aparecer para outro.

## O que falta para a Tela 4

- **Rotas** de lançar gasto, ver a própria dívida e marcar como pago (RF-30, RF-34), usando `dividir_despesa` e `registrar_despesa_pos_role` do banco.
- **Lançamento por foto da nota fiscal** (RF-31).
- **Saldo entre rolês** (RF-35, Could).
