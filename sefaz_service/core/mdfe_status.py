# sefaz_service/core/mdfe_status.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from lxml import etree
from requests_pkcs12 import post

# Namespace MDF-e
MDFE_NS = "http://www.portalfiscal.inf.br/mdfe"

# Namespace base do WSDL de status MDF-e
MDFE_WSDL_NS = "http://www.portalfiscal.inf.br/mdfe/wsdl/MDFeStatusServico"

# códigos de UF (IBGE)
UF_CODIGOS = {
    "RO": "11",
    "AC": "12",
    "AM": "13",
    "RR": "14",
    "PA": "15",
    "AP": "16",
    "TO": "17",
    "MA": "21",
    "PI": "22",
    "CE": "23",
    "RN": "24",
    "PB": "25",
    "PE": "26",
    "AL": "27",
    "SE": "28",
    "BA": "29",
    "MG": "31",
    "ES": "32",
    "RJ": "33",
    "SP": "35",
    "PR": "41",
    "SC": "42",
    "RS": "43",
    "MS": "50",
    "MT": "51",
    "GO": "52",
    "DF": "53",
}


@dataclass
class MDFeStatusResult:
    status: Optional[int]
    motivo: Optional[str]
    xml_envio: str
    xml_retorno: str


def _resolver_url_mdfe_status(uf: str, ambiente: str) -> str:
    """
    Resolve o endpoint do MDFeStatusServico (SVRS para AC e demais UFs atendidas).
    """
    uf = (uf or "").upper()

    if uf in {
        "AC", "AL", "AP", "DF", "ES", "PB", "PI",
        "RJ", "RN", "RO", "RR", "SC", "SE", "TO",
        "BA", "PA",
    }:
        return (
            "https://mdfe.svrs.rs.gov.br/ws/MDFeStatusServico/MDFeStatusServico.asmx"
            if ambiente == "1"
            else "https://mdfe-homologacao.svrs.rs.gov.br/ws/MDFeStatusServico/MDFeStatusServico.asmx"
        )

    # fallback: usa SVRS também
    return (
        "https://mdfe.svrs.rs.gov.br/ws/MDFeStatusServico/MDFeStatusServico.asmx"
        if ambiente == "1"
        else "https://mdfe-homologacao.svrs.rs.gov.br/ws/MDFeStatusServico/MDFeStatusServico.asmx"
    )


def _montar_xml_mdfe(tp_amb: str) -> str:
    """
    Layout 3.00 do consStatServMDFe **sem cUF no corpo**:

        <consStatServMDFe versao="3.00" xmlns="http://www.portalfiscal.inf.br/mdfe">
            <tpAmb>1</tpAmb>
            <xServ>STATUS</xServ>
        </consStatServMDFe>
    """
    return (
        f'<consStatServMDFe versao="3.00" xmlns="{MDFE_NS}">'
        f"<tpAmb>{tp_amb}</tpAmb>"
        "<xServ>STATUS</xServ>"
        "</consStatServMDFe>"
    )


def sefaz_mdfe_status(
    uf: str,
    pfx_path: str,
    pfx_password: str,
    ambiente: str = "2",
) -> MDFeStatusResult:
    """
    Consulta STATUS do serviço de MDF-e (MDFeStatusServico),
    usando certificado A1 (arquivo .pfx) via SOAP 1.2.
    """
    tp_amb = "1" if ambiente == "1" else "2"
    uf = (uf or "").upper()
    cuf = UF_CODIGOS.get(uf, uf)

    # XML interno, SEM cUF
    xml_envio = _montar_xml_mdfe(tp_amb=tp_amb)

    # Envelope SOAP 1.2 com mdfeCabecMsg (cUF/versaoDados) + mdfeDadosMsg
    envelope = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope"
               xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
               xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <soap:Header>
    <mdfeCabecMsg xmlns="{MDFE_WSDL_NS}">
      <cUF>{cuf}</cUF>
      <versaoDados>3.00</versaoDados>
    </mdfeCabecMsg>
  </soap:Header>
  <soap:Body>
    <mdfeDadosMsg xmlns="{MDFE_WSDL_NS}">
      {xml_envio}
    </mdfeDadosMsg>
  </soap:Body>
</soap:Envelope>
"""

    url = _resolver_url_mdfe_status(uf=uf, ambiente=ambiente)

    resp = post(
        url,
        data=envelope.encode("utf-8"),
        pkcs12_filename=pfx_path,
        pkcs12_password=pfx_password,
        headers={
            # SOAP 1.2: Content-Type application/soap+xml (sem SOAPAction separado)
            "Content-Type": 'application/soap+xml; charset="utf-8"',
        },
        timeout=30,
        verify=False,
    )

    xml_retorno = resp.text

    status_int: Optional[int] = None
    motivo_str: Optional[str] = None

    try:
        root = etree.fromstring(xml_retorno.encode("utf-8"))
        ns = {"mdfe": MDFE_NS}

        cstat_el = root.find(".//mdfe:cStat", namespaces=ns)
        xmot_el = root.find(".//mdfe:xMotivo", namespaces=ns)

        if cstat_el is not None and cstat_el.text:
            try:
                status_int = int(cstat_el.text.strip())
            except ValueError:
                status_int = None

        if xmot_el is not None and xmot_el.text:
            motivo_str = xmot_el.text.strip()
    except Exception:
        # Se der erro de parse, não estoura exceção aqui
        pass

    return MDFeStatusResult(
        status=status_int,
        motivo=motivo_str,
        xml_envio=xml_envio,
        xml_retorno=xml_retorno,
    )
