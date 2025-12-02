# core/enums.py
from enum import Enum


class Ambiente(str, Enum):
    HOMOLOGACAO = "2"
    PRODUCAO = "1"


class Documento(str, Enum):
    NFE = "nfe"
    CTE = "cte"
    MDFE = "mdfe"
    BPE = "bpe"


class Projeto(str, Enum):
    """
    Tipo de projeto/serviço SEFAZ.
    Usado para separar NFe, CTe, MDFe, BP-e, etc.
    """
    NFE = "nfe"
    CTE = "cte"
    MDFE = "mdfe"
    BPE = "bpe"
