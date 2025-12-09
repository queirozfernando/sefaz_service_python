from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from lxml import etree
import requests_pkcs12

from sefaz_service.core.uf_utils import uf_to_cuf, mdfe_url_consulta

MDFe_NS = "http://www.portalfiscal.inf.br/mdfe"
SOAP_ENV_NS = "http://www.w3.org/2003/05/soap-envelope"
MDFe_WSDL_CONSULTA = "http://www.portalfiscal.inf.br/mdfe/wsdl/MDFeConsulta"


@dataclass
class MDFeResultado:
    status: str
    motivo: str
    xml_envio: str
    xml_retorno: str


def _monta_xml_consulta(
    uf: str,
    ambiente: Literal["1", "2"],
    chave: str,
) -> str:
    if len(chave) != 44 or not chave.isdigit():
        raise ValueError("chMDFe deve ter 44 dígitos numéricos")

    root = etree.Element(
        "consSitMDFe",
        nsmap={None: MDFe_NS},
        versao="3.00",
    )
    etree.SubElement(root, "tpAmb").text = str(ambiente)
    etree.SubElement(root, "xServ").text = "CONSULTAR"
    etree.SubElement(root, "chMDFe").text = chave

    xml_bytes = etree.tostring(
        root, encoding="utf-8", xml_declaration=True, pretty_print=False
    )
    return xml_bytes.decode("utf-8")


def _monta_envelope_soap(xml_corpo: str, uf: str) -> str:
    cuf = uf_to_cuf(uf)

    nsmap_env = {
        "soap12": SOAP_ENV_NS,
        "xsi": "http://www.w3.org/2001/XMLSchema-instance",
        "xsd": "http://www.w3.org/2001/XMLSchema",
    }
    envelope = etree.Element(etree.QName(SOAP_ENV_NS, "Envelope"), nsmap=nsmap_env)

    header = etree.SubElement(envelope, etree.QName(SOAP_ENV_NS, "Header"))
    cabec = etree.SubElement(header, "mdfeCabecMsg", xmlns=MDFe_WSDL_CONSULTA)
    etree.SubElement(cabec, "cUF").text = cuf
    etree.SubElement(cabec, "versaoDados").text = "3.00"

    body = etree.SubElement(envelope, etree.QName(SOAP_ENV_NS, "Body"))
    dados_msg = etree.SubElement(body, "mdfeDadosMsg", xmlns=MDFe_WSDL_CONSULTA)

    corpo_root = etree.fromstring(xml_corpo.encode("utf-8"))
    dados_msg.append(corpo_root)

    xml_bytes = etree.tostring(
        envelope, encoding="utf-8", xml_declaration=True, pretty_print=False
    )
    return xml_bytes.decode("utf-8")


def _extrai_status_motivo(xml_retorno: str) -> tuple[str, str]:
    try:
        root = etree.fromstring(xml_retorno.encode("utf-8"))
    except Exception:
        return "", ""

    cstat = ""
    xmotivo = ""
    for el in root.iter():
        tag = etree.QName(el).localname
        if tag == "cStat" and not cstat:
            cstat = (el.text or "").strip()
        elif tag == "xMotivo" and not xmotivo:
            xmotivo = (el.text or "").strip()
    return cstat, xmotivo


def sefaz_mdfe_consulta(
    uf: str,
    ambiente: Literal["1", "2"],
    chave: str,
    certificado: str,
    senha: str,
) -> MDFeResultado:
    xml_corpo = _monta_xml_consulta(uf=uf, ambiente=ambiente, chave=chave)
    xml_envelope = _monta_envelope_soap(xml_corpo, uf=uf)

    url = mdfe_url_consulta(ambiente)

    headers = {
        "Content-Type": 'application/soap+xml; charset="utf-8"',
    }

    resp = requests_pkcs12.post(
        url,
        data=xml_envelope.encode("utf-8"),
        headers=headers,
        pkcs12_filename=certificado,
        pkcs12_password=senha,
        timeout=30,
    )

    xml_retorno = resp.text
    cstat, xmotivo = _extrai_status_motivo(xml_retorno)

    return MDFeResultado(
        status=cstat or str(resp.status_code),
        motivo=xmotivo or f"Retorno HTTP {resp.status_code}",
        xml_envio=xml_envelope,
        xml_retorno=xml_retorno,
    )
