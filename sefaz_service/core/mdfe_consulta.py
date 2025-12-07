# sefaz_service/core/mdfe_consulta.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from lxml import etree
from requests_pkcs12 import post  # pacote requests-pkcs12

# Namespace do MDF-e
MDFE_NS = "http://www.portalfiscal.inf.br/mdfe"

# Namespace base do WSDL
MDFE_CONSULTA_WSDL_NS = "http://www.portalfiscal.inf.br/mdfe/wsdl/MDFeConsulta"

# códigos de UF (mesmos da NFe / IBGE)
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
class MDFeConsultaResult:
    status: Optional[int]
    motivo: Optional[str]
    xml_envio: str
    xml_retorno: str


def _resolver_url_mdfe_consulta(ambiente: str) -> str:
    """
    Endpoint do serviço MDFeConsulta (SVRS).
    ambiente: "1"=produção, "2"=homologação.
    """
    ambiente = "1" if ambiente == "1" else "2"

    if ambiente == "1":
        return "https://mdfe.svrs.rs.gov.br/ws/MDFeConsulta/MDFeConsulta.asmx"
    else:
        return "https://mdfe-homologacao.svrs.rs.gov.br/ws/MDFeConsulta/MDFeConsulta.asmx"


def _montar_xml_cons_sit_mdfe(tp_amb: str, chave_mdfe: str, versao: str = "3.00") -> str:
    """
    Monta o XML interno do consSitMDFe:

        <consSitMDFe versao="3.00" xmlns="http://www.portalfiscal.inf.br/mdfe">
            <tpAmb>1</tpAmb>
            <xServ>CONSULTAR</xServ>
            <chMDFe>...</chMDFe>
        </consSitMDFe>
    """
    return (
        f'<consSitMDFe versao="{versao}" xmlns="{MDFE_NS}">'
        f"<tpAmb>{tp_amb}</tpAmb>"
        "<xServ>CONSULTAR</xServ>"
        f"<chMDFe>{chave_mdfe}</chMDFe>"
        "</consSitMDFe>"
    )


def sefaz_mdfe_consulta(
    uf: str,
    chave_mdfe: str,
    pfx_path: str,
    pfx_password: str,
    ambiente: str = "2",
    versao: str = "3.00",
) -> MDFeConsultaResult:
    """
    Consulta situação do MDF-e (MDFeConsultaMDF) usando certificado A1 (.pfx)
    via SOAP 1.2.

    - uf: sigla da UF do emitente (ex.: 'AC')
    - chave_mdfe: chave completa (44 dígitos) do MDF-e
    - ambiente: "1"=produção, "2"=homologação
    """
    tp_amb = "1" if ambiente == "1" else "2"

    uf = (uf or "").upper()
    cuf = UF_CODIGOS.get(uf, "43")  # default RS se vier algo esquisito

    # XML interno (é isso que mostramos no retorno)
    xml_dados = _montar_xml_cons_sit_mdfe(tp_amb=tp_amb, chave_mdfe=chave_mdfe, versao=versao)
    xml_envio = xml_dados

    # ==== SOAP 1.2 ====  (igual ao XML que funciona no seu teste)
    envelope = f"""<?xml version="1.0" encoding="utf-8"?>
    <soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                     xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                     xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
      <soap12:Body>
        <mdfeDadosMsg xmlns="{MDFE_CONSULTA_WSDL_NS}">
          {xml_dados}
        </mdfeDadosMsg>
      </soap12:Body>
    </soap12:Envelope>
    """

    url = _resolver_url_mdfe_consulta(ambiente=ambiente)

    resp = post(
        url,
        data=envelope.encode("utf-8"),
        pkcs12_filename=pfx_path,
        pkcs12_password=pfx_password,
        headers={
            # SOAP 1.2 -> action vai no próprio Content-Type
            "Content-Type": (
                f'application/soap+xml; charset="utf-8"; '
                f'action="{MDFE_CONSULTA_WSDL_NS}/mdfeConsultaMDF"'
            ),
        },
        timeout=30,
        verify=False,  # em produção, o ideal é usar verify=True
    )

    xml_retorno = resp.text

    # Tenta extrair cStat / xMotivo
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
        # se der erro de parse, devolvemos só o XML bruto
        pass

    return MDFeConsultaResult(
        status=status_int,
        motivo=motivo_str,
        xml_envio=xml_envio,
        xml_retorno=xml_retorno,
    )
