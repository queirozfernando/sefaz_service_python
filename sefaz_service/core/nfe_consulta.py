# sefaz_service/core/nfe_consulta.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from lxml import etree

from .envio import enviar_soap_com_pfx, EndpointInfo
from .soaplist import get_nfe_consulta_protocolo4_endpoint

NFE_NS = "http://www.portalfiscal.inf.br/nfe"
CONSULTA_WSDL_NS = "http://www.portalfiscal.inf.br/nfe/wsdl/NFeConsultaProtocolo4"

# Mesmo mapa de UF -> cUF que usamos em nfe_status.py
UF_TO_CUF = {
    "RO": "11", "AC": "12", "AM": "13", "RR": "14", "PA": "15", "AP": "16", "TO": "17",
    "MA": "21", "PI": "22", "CE": "23", "RN": "24", "PB": "25", "PE": "26", "AL": "27",
    "SE": "28", "BA": "29", "MG": "31", "ES": "32", "RJ": "33", "SP": "35", "PR": "41",
    "SC": "42", "RS": "43", "MS": "50", "MT": "51", "GO": "52", "DF": "53",
}


def _resolver_cuf(uf: str) -> str:
    return UF_TO_CUF.get((uf or "").upper(), "")


@dataclass
class NFeConsultaResult:
    cStat: Optional[int]
    xMotivo: Optional[str]
    xml_envio: str
    xml_retorno: str


def _montar_cons_sit_nfe(
    chave: str,
    uf: str,
    ambiente: str = "2",
    versao: str = "4.00",
) -> tuple[str, str]:
    """
    <consSitNFe versao="4.00" xmlns="http://www.portalfiscal.inf.br/nfe">
       <tpAmb>2</tpAmb>
       <xServ>CONSULTAR</xServ>
       <chNFe>...</chNFe>
    </consSitNFe>
    """
    c_uf = _resolver_cuf(uf)
    if not c_uf:
        raise ValueError(f"UF inválida para cUF: {uf!r}")

    xml = (
        f'<consSitNFe versao="{versao}" xmlns="{NFE_NS}">'
        f"<tpAmb>{ambiente}</tpAmb>"
        f"<xServ>CONSULTAR</xServ>"
        f"<chNFe>{chave}</chNFe>"
        f"</consSitNFe>"
    )
    return xml, c_uf


def _montar_soap_consulta(cons_sit_xml: str, c_uf: str, versao_dados: str = "4.00") -> str:
    """
    Envelope SOAP 1.2 para NFeConsultaProtocolo4.
    """
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<soap12:Envelope
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xmlns:xsd="http://www.w3.org/2001/XMLSchema"
    xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
  <soap12:Header>
    <nfeCabecMsg xmlns="{CONSULTA_WSDL_NS}">
      <cUF>{c_uf}</cUF>
      <versaoDados>{versao_dados}</versaoDados>
    </nfeCabecMsg>
  </soap12:Header>
  <soap12:Body>
    <nfeDadosMsg xmlns="{CONSULTA_WSDL_NS}">
      {cons_sit_xml}
    </nfeDadosMsg>
  </soap12:Body>
</soap12:Envelope>"""


def _extrair_xml_consulta(resp_xml: str) -> str:
    """
    Extrai <retConsSitNFe> do SOAP. Se não achar, devolve o SOAP inteiro.
    """
    try:
        root = etree.fromstring(resp_xml.encode("utf-8"))
    except Exception:
        return resp_xml

    # Procura qualquer nó cujo nome seja retConsSitNFe, ignorando namespace
    nodes = root.xpath("//*[local-name()='retConsSitNFe']")
    if nodes:
        return etree.tostring(nodes[0], encoding="utf-8", xml_declaration=True).decode("utf-8")

    return resp_xml


def _obter_status_motivo(xml_retorno: str) -> tuple[Optional[int], Optional[str]]:
    try:
        root = etree.fromstring(xml_retorno.encode("utf-8"))
    except Exception:
        return None, None

    cstat_nodes = root.xpath("//*[local-name()='cStat']")
    xmot_nodes = root.xpath("//*[local-name()='xMotivo']")

    cstat_val: Optional[int] = None
    xmot_val: Optional[str] = None

    if cstat_nodes and cstat_nodes[0].text:
        try:
            cstat_val = int(cstat_nodes[0].text.strip())
        except ValueError:
            cstat_val = None

    if xmot_nodes and xmot_nodes[0].text:
        xmot_val = xmot_nodes[0].text.strip()

    return cstat_val, xmot_val


def sefaz_nfe_consulta(
    uf: str,
    chave: str,
    pfx_path: str,
    pfx_password: str,
    ambiente: str = "2",
    versao: str = "4.00",
) -> NFeConsultaResult:
    """
    Consulta a SITUAÇÃO da NFe/NFCe pela CHAVE (NFeConsultaProtocolo4).
    """
    # 1) Monta consSitNFe e descobre cUF
    xml_envio, c_uf = _montar_cons_sit_nfe(chave=chave, uf=uf, ambiente=ambiente, versao=versao)

    # 2) Endpoint correto (SVRS ou próprio da UF)
    endpoint: EndpointInfo = get_nfe_consulta_protocolo4_endpoint(uf=uf, ambiente=ambiente)

    # 3) Envelope SOAP
    soap_xml = _montar_soap_consulta(xml_envio, c_uf=c_uf, versao_dados=versao)

    # 4) Envia via HTTPS com certificado
    resp = enviar_soap_com_pfx(
        endpoint=endpoint,
        soap_xml=soap_xml,
        pfx_path=pfx_path,
        pfx_password=pfx_password,
    )

    # 5) Extrai retConsSitNFe
    xml_retorno = _extrair_xml_consulta(resp.text)

    # 6) Pega cStat / xMotivo
    cstat, xmot = _obter_status_motivo(xml_retorno)

    return NFeConsultaResult(
        cStat=cstat,
        xMotivo=xmot,
        xml_envio=xml_envio,
        xml_retorno=xml_retorno,
    )
