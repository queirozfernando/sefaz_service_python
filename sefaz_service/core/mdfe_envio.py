from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from lxml import etree
import requests_pkcs12

from sefaz_service.core.assinatura import assinar_mdfe_xml
from sefaz_service.core.uf_utils import uf_to_cuf, mdfe_url_recepcao_sinc

MDFe_NS = "http://www.portalfiscal.inf.br/mdfe"
SOAP_ENV_NS = "http://www.w3.org/2003/05/soap-envelope"
MDFe_WSDL_RECEP_SINC = "http://www.portalfiscal.inf.br/mdfe/wsdl/MDFeRecepcaoSinc"


@dataclass
class MDFeResultadoEnvio:
    status: str
    motivo: str
    xml_envio: str
    xml_retorno: str
    xml_autorizado: str | None = None  # mdfeProc, se autorizado


def _monta_envi_mdfe(xml_assinado: str, id_lote: str = "1") -> str:
    root = etree.Element(
        "enviMDFe",
        nsmap={None: MDFe_NS},
        versao="3.00",
    )
    etree.SubElement(root, "idLote").text = id_lote

    mdfe_root = etree.fromstring(xml_assinado.encode("utf-8"))
    root.append(mdfe_root)

    xml_bytes = etree.tostring(
        root, encoding="utf-8", xml_declaration=True, pretty_print=False
    )
    return xml_bytes.decode("utf-8")


def _monta_envelope_soap(xml_envi_mdfe: str, uf: str) -> str:
    cuf = uf_to_cuf(uf)

    nsmap_env = {
        "soap12": SOAP_ENV_NS,
        "xsi": "http://www.w3.org/2001/XMLSchema-instance",
        "xsd": "http://www.w3.org/2001/XMLSchema",
    }
    envelope = etree.Element(etree.QName(SOAP_ENV_NS, "Envelope"), nsmap=nsmap_env)

    header = etree.SubElement(envelope, etree.QName(SOAP_ENV_NS, "Header"))
    cabec = etree.SubElement(header, "mdfeCabecMsg", xmlns=MDFe_WSDL_RECEP_SINC)
    etree.SubElement(cabec, "cUF").text = cuf
    etree.SubElement(cabec, "versaoDados").text = "3.00"

    body = etree.SubElement(envelope, etree.QName(SOAP_ENV_NS, "Body"))
    dados_msg = etree.SubElement(body, "mdfeDadosMsg", xmlns=MDFe_WSDL_RECEP_SINC)

    envi_root = etree.fromstring(xml_envi_mdfe.encode("utf-8"))
    dados_msg.append(envi_root)

    xml_bytes = etree.tostring(
        envelope, encoding="utf-8", xml_declaration=True, pretty_print=False
    )
    return xml_bytes.decode("utf-8")


def _extrai_status_motivo_e_proc(xml_retorno: str) -> tuple[str, str, str | None]:
    try:
        root = etree.fromstring(xml_retorno.encode("utf-8"))
    except Exception:
        return "", "", None

    cstat = ""
    xmotivo = ""
    mdfe_proc_xml: str | None = None

    for el in root.iter():
        tag = etree.QName(el).localname
        if tag == "cStat" and not cstat:
            cstat = (el.text or "").strip()
        elif tag == "xMotivo" and not xmotivo:
            xmotivo = (el.text or "").strip()

    # Tenta localizar mdfeProc
    mdfe_proc = root.find(".//{http://www.portalfiscal.inf.br/mdfe}mdfeProc")
    if mdfe_proc is not None:
        mdfe_proc_xml_bytes = etree.tostring(
            mdfe_proc,
            encoding="utf-8",
            xml_declaration=True,
            pretty_print=False,
        )
        mdfe_proc_xml = mdfe_proc_xml_bytes.decode("utf-8")

    return cstat, xmotivo, mdfe_proc_xml


def sefaz_mdfe_envio(
    xml: str,
    uf: str,
    ambiente: Literal["1", "2"],
    certificado: str,
    senha_certificado: str,
) -> MDFeResultadoEnvio:
    """
    Envia um MDFe via RecepcaoSinc:
    - Assina <infMDFe> com o PFX.
    - Envolve em enviMDFe/idLote.
    - Envia via SOAP 1.2 para MDFeRecepcaoSinc.
    - Se cStat=100 e mdfeProc presente, devolve em xml_autorizado.
    """
    # 1) Assinar o XML do MDF-e (infMDFe)
    xml_assinado = assinar_mdfe_xml(
        xml,
        pfx_path=certificado,
        pfx_password=senha_certificado,
    )

    # 2) Monta enviMDFe
    xml_envi_mdfe = _monta_envi_mdfe(xml_assinado)

    # 3) Monta envelope SOAP
    xml_envelope = _monta_envelope_soap(xml_envi_mdfe, uf=uf)

    # 4) URL do serviço
    url = mdfe_url_recepcao_sinc(ambiente)

    headers = {
        "Content-Type": 'application/soap+xml; charset="utf-8"',
    }

    resp = requests_pkcs12.post(
        url,
        data=xml_envelope.encode("utf-8"),
        headers=headers,
        pkcs12_filename=certificado,
        pkcs12_password=senha_certificado,
        timeout=30,
    )

    xml_retorno = resp.text
    cstat, xmotivo, mdfe_proc_xml = _extrai_status_motivo_e_proc(xml_retorno)

    return MDFeResultadoEnvio(
        status=cstat or str(resp.status_code),
        motivo=xmotivo or f"Retorno HTTP {resp.status_code}",
        xml_envio=xml_envelope,
        xml_retorno=xml_retorno,
        xml_autorizado=mdfe_proc_xml,
    )
