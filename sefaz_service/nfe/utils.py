# nfe/utils.py

from typing import Dict
from lxml import etree
from core.enums import Ambiente


def extrair_tag(xml: str, tag: str) -> str:
    """
    Retorna o texto da primeira ocorrência da tag informada.
    Se não encontrar, devolve string vazia.
    """
    try:
        root = etree.fromstring(xml.encode("utf-8"))
    except Exception:
        return ""

    # procura ignorando namespaces
    xpath_expr = f".//*[local-name()='{tag}']"
    elem = root.find(xpath_expr)
    return elem.text if elem is not None and elem.text is not None else ""


def carregar_urls_autorizacao(uf: str, ambiente: Ambiente) -> Dict[str, str]:
    """
    Retorna URL e SOAPAction para autorização de NFe (4.00).

    Por enquanto coloquei só o cenário típico:
    - AC usa SVRS
    - e alguns exemplos diretos (pode ir expandindo depois).
    """
    uf = uf.upper()

    # Ambiente: "2" homologação, "1" produção
    hom = ambiente == Ambiente.HOMOLOGACAO

    # endpoints básicos (pode ampliar depois)
    if uf in {"AC", "AL", "AP", "DF", "ES", "PB", "PI", "RJ", "RN", "RO", "RR", "SC", "SE", "TO"}:
        # SVRS
        if hom:
            url = "https://nfe-homologacao.svrs.rs.gov.br/ws/NfeAutorizacao/NFeAutorizacao4.asmx"
        else:
            url = "https://nfe.svrs.rs.gov.br/ws/NfeAutorizacao/NFeAutorizacao4.asmx"
    elif uf == "SP":
        url = "https://homologacao.nfe.fazenda.sp.gov.br/ws/nfeautorizacao4.asmx" if hom \
            else "https://nfe.fazenda.sp.gov.br/ws/nfeautorizacao4.asmx"
    elif uf == "RS":
        url = "https://nfe-homologacao.sefazrs.rs.gov.br/ws/NfeAutorizacao/NFeAutorizacao4.asmx" if hom \
            else "https://nfe.sefazrs.rs.gov.br/ws/NfeAutorizacao/NFeAutorizacao4.asmx"
    else:
        # fallback genérico – depois a gente pode completar com a sua SoapList
        url = ""

    soap_action = "http://www.portalfiscal.inf.br/nfe/wsdl/NFeAutorizacao4/nfeAutorizacaoLote"

    return {
        "url": url,
        "action": soap_action,
    }
