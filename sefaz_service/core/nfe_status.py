# sefaz_service/core/nfe_status.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from lxml import etree

from .envio import (
    enviar_soap_com_pfx,
    EndpointInfo,
)
from .soaplist import get_nfe_status_servico4_endpoint

# Namespaces
NFE_NS = "http://www.portalfiscal.inf.br/nfe"
STATUS_WSDL_NS = "http://www.portalfiscal.inf.br/nfe/wsdl/NFeStatusServico4"

# Mapa de UF -> cUF
UF_TO_CUF = {
    "RO": "11", "AC": "12", "AM": "13", "RR": "14", "PA": "15", "AP": "16", "TO": "17",
    "MA": "21", "PI": "22", "CE": "23", "RN": "24", "PB": "25", "PE": "26", "AL": "27",
    "SE": "28", "BA": "29", "MG": "31", "ES": "32", "RJ": "33", "SP": "35", "PR": "41",
    "SC": "42", "RS": "43", "MS": "50", "MT": "51", "GO": "52", "DF": "53",
}


def _resolver_cuf(uf: str) -> str:
    """
    Converte sigla da UF para código numérico cUF.
    Equivalente ao ::UFCodigo( ::cUF ) da rotina Harbour.
    """
    return UF_TO_CUF.get((uf or "").upper(), "")


@dataclass
class NFeStatusResult:
    """
    Resultado da consulta de status do serviço de NFe.
    """
    cStat: Optional[int]
    xMotivo: Optional[str]
    xml_envio: str
    xml_retorno: str


def _montar_cons_stat_serv(uf: str, ambiente: str = "2", versao: str = "4.00") -> tuple[str, str]:
    """
    Monta o XML <consStatServ> da NFe:

    <consStatServ versao="4.00" xmlns="http://www.portalfiscal.inf.br/nfe">
        <tpAmb>2</tpAmb>
        <cUF>12</cUF>
        <xServ>STATUS</xServ>
    </consStatServ>

    Retorna (xml, cUF).
    """
    c_uf = _resolver_cuf(uf)
    if not c_uf:
        raise ValueError(f"UF inválida para cUF: {uf!r}")

    xml = (
        f'<consStatServ versao="{versao}" xmlns="{NFE_NS}">'
        f"<tpAmb>{ambiente}</tpAmb>"
        f"<cUF>{c_uf}</cUF>"
        f"<xServ>STATUS</xServ>"
        f"</consStatServ>"
    )
    return xml, c_uf


def _montar_soap_status(cons_stat_serv_xml: str, c_uf: str, versao_dados: str = "4.00") -> str:
    """
    Monta o envelope SOAP 1.2 para o serviço NFeStatusServico4
    no mesmo padrão do envio da NFe: Header + nfeDadosMsg no Body.
    """
    envelope = f"""<?xml version="1.0" encoding="UTF-8"?>
<soap12:Envelope
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xmlns:xsd="http://www.w3.org/2001/XMLSchema"
    xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
  <soap12:Header>
    <nfeCabecMsg xmlns="{STATUS_WSDL_NS}">
      <cUF>{c_uf}</cUF>
      <versaoDados>{versao_dados}</versaoDados>
    </nfeCabecMsg>
  </soap12:Header>
  <soap12:Body>
    <nfeDadosMsg xmlns="{STATUS_WSDL_NS}">
      {cons_stat_serv_xml}
    </nfeDadosMsg>
  </soap12:Body>
</soap12:Envelope>"""
    return envelope



def _extrair_xml_status(resp_xml: str) -> str:
    """
    Extrai o <retConsStatServ> de dentro do SOAP de resposta do
    NFeStatusServico4. Se não encontrar, devolve o SOAP inteiro.
    """
    try:
        root = etree.fromstring(resp_xml.encode("utf-8"))
    except Exception:
        return resp_xml

    ns = {
        "soap": "http://www.w3.org/2003/05/soap-envelope",
        "ws": STATUS_WSDL_NS,
    }

    # <soap:Body><ws:nfeResultMsg>...</ws:nfeResultMsg></soap:Body>
    result = root.find(".//ws:nfeResultMsg", ns)
    if result is None or len(result) == 0:
        return resp_xml

    payload = result[0]  # normalmente <retConsStatServ>
    return etree.tostring(payload, encoding="utf-8", xml_declaration=True).decode("utf-8")


def _obter_status_motivo(xml_retorno: str) -> tuple[Optional[int], Optional[str]]:
    """
    Lê <cStat> e <xMotivo> do retorno da SEFAZ (retConsStatServ),
    independente de namespace.
    """
    try:
        root = etree.fromstring(xml_retorno.encode("utf-8"))
    except Exception:
        return None, None

    # Busca por local-name() para não depender de namespace
    cstat_nodes = root.xpath("//*[local-name()='cStat']")
    xmot_nodes = root.xpath("//*[local-name()='xMotivo']")

    cstat_val = None
    xmot_val = None

    if cstat_nodes and cstat_nodes[0].text:
        try:
            cstat_val = int(cstat_nodes[0].text.strip())
        except ValueError:
            cstat_val = None

    if xmot_nodes and xmot_nodes[0].text:
        xmot_val = xmot_nodes[0].text.strip()

    return cstat_val, xmot_val


def sefaz_nfe_status(
    uf: str,
    pfx_path: str,
    pfx_password: str,
    ambiente: str = "2",
    versao: str = "4.00",
) -> NFeStatusResult:
    """
    Consulta o STATUS do serviço de NFe (NFeStatusServico4),
    usando certificado A1 (PFX), seguindo a ideia do ze_Sefaz_NFeStatus.

    - uf: sigla da UF (ex.: "AC")
    - ambiente: "1" produção, "2" homologação
    """
    # 1) Montar <consStatServ> e obter cUF
    xml_envio, c_uf = _montar_cons_stat_serv(uf=uf, ambiente=ambiente, versao=versao)

    # 2) Descobrir endpoint correto (SP, PR, MG, GO, etc. ou SVRS)
    endpoint: EndpointInfo = get_nfe_status_servico4_endpoint(uf=uf, ambiente=ambiente)

    # 3) Montar SOAP no padrão NFeStatusServico4
    soap_xml = _montar_soap_status(xml_envio, c_uf=c_uf, versao_dados=versao)

    # 4) Enviar via HTTPS com certificado PFX
    resp = enviar_soap_com_pfx(
        endpoint=endpoint,
        soap_xml=soap_xml,
        pfx_path=pfx_path,
        pfx_password=pfx_password,
    )

    # 5) Extrair o XML retConsStatServ do SOAP
    xml_retorno = _extrair_xml_status(resp.text)

    # 6) Pegar cStat / xMotivo
    cstat, xmot = _obter_status_motivo(xml_retorno)

    return NFeStatusResult(
        cStat=cstat,
        xMotivo=xmot,
        xml_envio=xml_envio,
        xml_retorno=xml_retorno,
    )
