"""Código Pix copia e cola estático (BR Code), no padrão do Banco Central (RF-33, RNF-04).

O BR Code segue o padrão EMV de QR Code para pagamentos (Merchant Presented Mode): uma sequência de campos
`ID (2 dígitos) + tamanho (2 dígitos) + valor`, fechada pelo campo 63 com o CRC16 (CRC-16/CCITT-FALSE:
polinômio 0x1021, valor inicial 0xFFFF) calculado sobre todo o texto anterior, incluindo "6304".

    from src.financas.pix import gerar_pix
    gerar_pix("rafaela@email.com", "Rafaela Souza", Decimal("60.00"), cidade="Brasilia")
    # '00020126...6304ABCD'

Tudo é calculado em código, nunca pelo modelo de linguagem. A chave Pix é um dado pessoal (pode ser CPF,
telefone ou e-mail): este módulo não a registra em log nem a guarda.
"""
from __future__ import annotations

import re
import unicodedata
import uuid
from decimal import Decimal, InvalidOperation

GUI_PIX = "br.gov.bcb.pix"
MCC_NAO_INFORMADO = "0000"
MOEDA_REAL = "986"          # ISO 4217
PAIS = "BR"
TXID_ESTATICO = "***"       # código estático sem identificador de transação
NOME_MAX = 25
CIDADE_MAX = 15
CAMPO_26_MAX = 99
VALOR_MAX_CARACTERES = 13


class ErroPix(ValueError):
    """Dado inválido para gerar o código Pix."""


# ----------------------------------------------------------------------------------------------- CRC16

def crc16_ccitt(texto: str) -> str:
    """CRC-16/CCITT-FALSE do texto (UTF-8), em 4 dígitos hexadecimais maiúsculos."""
    crc = 0xFFFF
    for byte in texto.encode("utf-8"):
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) if crc & 0x8000 else (crc << 1)
            crc &= 0xFFFF
    return f"{crc:04X}"


def crc_confere(payload: str) -> bool:
    """O CRC no fim do código bate com o conteúdo? (o banco faz essa conferência ao colar o código)."""
    return len(payload) > 8 and payload[-8:-4] == "6304" and crc16_ccitt(payload[:-4]) == payload[-4:]


# ----------------------------------------------------------------------------------------------- chave

def _so_digitos(texto: str) -> str:
    return re.sub(r"\D", "", texto)


def _cpf_valido(d: str) -> bool:
    if len(d) != 11 or d == d[0] * 11:
        return False
    for n in (9, 10):
        soma = sum(int(d[i]) * (n + 1 - i) for i in range(n))
        if (soma * 10 % 11) % 10 != int(d[n]):
            return False
    return True


def _cnpj_valido(d: str) -> bool:
    if len(d) != 14 or d == d[0] * 14:
        return False
    for n, pesos in ((12, [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]), (13, [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])):
        resto = sum(int(d[i]) * pesos[i] for i in range(n)) % 11
        if (0 if resto < 2 else 11 - resto) != int(d[n]):
            return False
    return True


def normalizar_chave(chave: str, tipo: str | None = None) -> tuple[str, str]:
    """Chave no formato que o Pix espera e o tipo dela: cpf, cnpj, email, telefone ou aleatoria.

    - CPF e CNPJ: só os dígitos, com os dígitos verificadores conferidos.
    - Telefone: +55, DDD e número (ex.: "+5561999998888").
    - E-mail: em minúsculas.
    - Aleatória: o UUID gerado pelo banco, em minúsculas.
    Sem `tipo`, ele é deduzido; telefone sem "+" é ambíguo com CPF e precisa do tipo explícito.
    """
    bruta = (chave or "").strip()
    if not bruta:
        raise ErroPix("A chave Pix está vazia.")
    tipo = (tipo or "").strip().lower() or None

    if tipo in (None, "aleatoria", "evp"):
        try:
            return str(uuid.UUID(bruta)).lower(), "aleatoria"
        except ValueError:
            if tipo:
                raise ErroPix("A chave aleatória deve ser o código de 36 caracteres que o banco gerou.") from None
    if tipo in (None, "email") and "@" in bruta:
        email = bruta.lower()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email) or len(email) > 77:
            raise ErroPix("E-mail inválido para chave Pix.")
        return email, "email"
    if tipo == "telefone" or (tipo is None and bruta.startswith("+")):
        d = _so_digitos(bruta)
        if not d.startswith("55"):
            d = "55" + d
        if len(d) not in (12, 13):
            raise ErroPix("Telefone inválido: use DDD e número, como +55 61 99999-8888.")
        return "+" + d, "telefone"
    d = _so_digitos(bruta)
    if tipo in (None, "cpf") and len(d) == 11:
        if not _cpf_valido(d):
            raise ErroPix("CPF inválido.")
        return d, "cpf"
    if tipo in (None, "cnpj") and len(d) == 14:
        if not _cnpj_valido(d):
            raise ErroPix("CNPJ inválido.")
        return d, "cnpj"
    raise ErroPix("Não reconheci a chave Pix. Use CPF, CNPJ, e-mail, telefone com +55 ou a chave aleatória.")


# ----------------------------------------------------------------------------------------------- campos

def _ascii(texto: str, maximo: int) -> str:
    """Sem acentos e só caracteres seguros para o BR Code; corta no tamanho máximo do campo."""
    sem_acento = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode()
    limpo = re.sub(r"[^A-Za-z0-9 .,\-/]", "", sem_acento)
    return " ".join(limpo.split())[:maximo].strip()


def _campo(ident: str, valor: str) -> str:
    if len(valor) > 99:
        raise ErroPix(f"O campo {ident} passa de 99 caracteres.")
    return f"{ident}{len(valor):02d}{valor}"


def _valor(valor: Decimal | str | int | float | None) -> str | None:
    if valor is None:
        return None
    try:
        v = Decimal(str(valor)).quantize(Decimal("0.01"))
    except InvalidOperation:
        raise ErroPix(f"Valor inválido: {valor!r}.") from None
    if v <= 0:
        raise ErroPix("O valor do Pix precisa ser maior que zero.")
    texto = f"{v:.2f}"
    if len(texto) > VALOR_MAX_CARACTERES:
        raise ErroPix("Valor alto demais para o código Pix.")
    return texto


# ----------------------------------------------------------------------------------------------- código

def gerar_pix(chave: str, nome_recebedor: str, valor: Decimal | str | int | float | None = None, *,
              cidade: str = "Brasilia", descricao: str | None = None, tipo_chave: str | None = None) -> str:
    """Código Pix copia e cola estático com a chave e o nome de quem recebe e, se houver, o valor.

    `valor`: em reais (Decimal de preferência); None gera um código em que o pagador digita o valor.
    `descricao`: texto curto que aparece no app do banco (ex.: "Rolê de sábado"); entra se couber no campo 26.
    """
    chave_norm, _ = normalizar_chave(chave, tipo_chave)
    nome = _ascii(nome_recebedor, NOME_MAX)
    if not nome:
        raise ErroPix("Informe o nome de quem recebe.")
    cidade_norm = _ascii(cidade, CIDADE_MAX).upper() or "BRASILIA"

    conta = _campo("00", GUI_PIX) + _campo("01", chave_norm)
    if descricao:
        livre = CAMPO_26_MAX - len(conta) - 4
        texto = _ascii(descricao, max(livre, 0))
        if texto:
            conta += _campo("02", texto)

    partes = [
        _campo("00", "01"),                     # versão do payload
        _campo("26", conta),                    # conta Pix: GUI + chave (+ descrição)
        _campo("52", MCC_NAO_INFORMADO),
        _campo("53", MOEDA_REAL),
    ]
    valor_txt = _valor(valor)
    if valor_txt:
        partes.append(_campo("54", valor_txt))
    partes += [
        _campo("58", PAIS),
        _campo("59", nome),
        _campo("60", cidade_norm),
        _campo("62", _campo("05", TXID_ESTATICO)),
    ]
    sem_crc = "".join(partes) + "6304"
    return sem_crc + crc16_ccitt(sem_crc)


def ler_campos(payload: str) -> dict[str, str]:
    """Separa os campos de primeiro nível de um código Pix (útil para conferir valor e nome antes de pagar)."""
    campos, i = {}, 0
    while i + 4 <= len(payload):
        ident, tamanho = payload[i:i + 2], int(payload[i + 2:i + 4])
        campos[ident] = payload[i + 4:i + 4 + tamanho]
        i += 4 + tamanho
    return campos
