# sefaz_service/core/utils.py
from __future__ import annotations

from typing import Optional

from lxml import etree

import gzip
import base64

MDFE_NS = "http://www.portalfiscal.inf.br/mdfe"

UF_CODIGOS = {
    "RO": 11,
    "AC": 12,
    "AM": 13,
    "RR": 14,
    "PA": 15,
    "AP": 16,
    "TO": 17,
    "MA": 21,
    "PI": 22,
    "CE": 23,
    "RN": 24,
    "PB": 25,
    "PE": 26,
    "AL": 27,
    "SE": 28,
    "BA": 29,
    "MG": 31,
    "ES": 32,
    "RJ": 33,
    "SP": 35,
    "PR": 41,
    "SC": 42,
    "RS": 43,
    "MS": 50,
    "MT": 51,
    "GO": 52,
    "DF": 53,
}


def limpar_xml(xml: str) -> str:
    """
    Limpa caracteres de edição básicos usados antes da assinatura/envio.
    """
    if not xml:
        return ""
    xml = xml.replace("\r", "").replace("\t", "").replace("\n", "")
    xml = xml.lstrip("\ufeff")
    return xml


def obter_cuf(uf: str) -> int:
    uf = (uf or "").strip().upper()
    if uf not in UF_CODIGOS:
        raise ValueError(f"UF inválida: {uf!r}")
    return UF_CODIGOS[uf]


def obter_url_mdfe_sinc(ambiente: str) -> str:
    """
    Retorna URL da Recepção Síncrona do MDFe (SVRS).
    ambiente: "1" produção / "2" homologação
    """
    if ambiente == "1":
        return "https://mdfe.svrs.rs.gov.br/ws/MDFeRecepcaoSinc/MDFeRecepcaoSinc.asmx"
    else:
        return "https://mdfe-homologacao.svrs.rs.gov.br/ws/MDFeRecepcaoSinc/MDFeRecepcaoSinc.asmx"


def extrair_chave_mdfe(xml: str) -> Optional[str]:
    """
    Tenta extrair a chave do MDFe a partir do atributo Id="MDFeXXXXXXXX..."
    em <infMDFe>.
    """
    try:
        root = etree.fromstring(xml.encode("utf-8"))
    except Exception:
        return None

    inf_list = root.xpath(".//*[local-name()='infMDFe']")
    if not inf_list:
        return None

    inf = inf_list[0]
    id_attr = inf.get("Id") or ""
    if id_attr.startswith("MDFe"):
        return id_attr[4:]
    return id_attr or None


def compactar_gzip_base64(xml: str) -> str:
    """
    Compacta o XML em GZip e retorna em Base64 (string ASCII).
    Este é exatamente o formato esperado em mdfeDadosMsg.
    """
    if not xml:
        return ""
    # sempre UTF-8
    raw = xml.encode("utf-8")
    gz = gzip.compress(raw)
    b64 = base64.b64encode(gz).decode("ascii")
    return b64
