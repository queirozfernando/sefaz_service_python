from __future__ import annotations

import re
import datetime as _dt          # 👈 ADICIONA ESTA LINHA
from xml.etree import ElementTree as ET
from typing import Optional



def only_digits(value: str | None) -> str:
    """
    Remove tudo que não for número.
    Equivalente ao SoNumero()/SomenteNumero do Harbour.
    """
    if not value:
        return ""
    return re.sub(r"\D+", "", value)


def xml_tag(tag: str, value: Optional[str]) -> str:
    """
    Gera <tag>valor</tag> se tiver valor, senão retorna string vazia.
    """
    if value is None:
        return ""
    value = str(value)
    if value == "":
        return ""
    return f"<{tag}>{value}</{tag}>"


def now_sefaz_datetime() -> str:
    """
    Data/hora no padrão SEFAZ: 2025-01-29T10:35:27-03:00
    Usa o timezone local da máquina.
    """
    dt = _dt.datetime.now(_dt.timezone.utc).astimezone()
    return dt.isoformat(timespec="seconds")


def dfe_emitente_from_chave(chave: str) -> str:
    """
    Equivalente ao DfeEmitente() do Harbour:
    pega o CNPJ/CPF do emitente a partir da chave de acesso (44 dígitos).
    """
    chave = only_digits(chave)
    if len(chave) != 44:
        raise ValueError("Chave de acesso deve ter 44 dígitos")

    ctext = chave[6:6 + 14]  # pos 7 a 20 (1-based)
    # regra original trata caso começando com 000 como possível CPF
    if ctext.startswith("000"):
        # Aqui poderíamos validar CNPJ; por enquanto, se tiver 11 últimos dígitos,
        # assumimos como CPF.
        ctext = ctext[-11:]
    return ctext
