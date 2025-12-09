from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from lxml import etree
import requests_pkcs12

from sefaz_service.core.assinatura import assinar_mdfe_evento_xml
from sefaz_service.core.uf_utils import uf_to_cuf, mdfe_url_recepcao_evento

MDFe_NS = "http://www.portalfiscal.inf.br/mdfe"
SOAP_ENV_NS = "http://www.w3.org/2003/05/soap-envelope"
MDFe_WSDL_EVENTO = "http://www.portalfiscal.inf.br/mdfe/wsdl/MDFeRecepcaoEvento"


@dataclass
class MDFeResultado:
    status: str
    motivo: str
    xml_envio: str
    xml_retorno: str


def _monta_xml_evento_inc_condutor(
    uf: str,
    ambiente: Literal["1", "2"],
    ch_mdfe: str,
    cpf: str,
    xnome: str,
    nseq_evento: str = "1",
) -> str:
    """
    Evento 110114 – Inclusão de Condutor em MDF-e (evIncCondutorMDFe).
    """
    if len(ch_mdfe) != 44 or not ch_mdfe.isdigit():
        raise ValueError("chMDFe deve ter 44 dígitos numéricos")

    if len(cpf) != 11 or not cpf.isdigit():
        raise ValueError("CPF deve ter 11 dígitos numéricos")

    cuf = uf_to_cuf(uf)
    cnpj_emit = ch_mdfe[6:20]

    tp_evento = "110114"
    n_seq_evento = nseq_evento or "1"
    id_evento = f"ID{tp_evento}{ch_mdfe}{int(n_seq_evento):02d}"

    dh_evento = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S-00:00")

    nsmap = {None: MDFe_NS}
    root = etree.Element("eventoMDFe", nsmap=nsmap, versao="3.00")

    inf_evento = etree.SubElement(root, "infEvento", Id=id_evento)
    etree.SubElement(inf_evento, "cOrgao").text = cuf
    etree.SubElement(inf_evento, "tpAmb").text = str(ambiente)
    etree.SubElement(inf_evento, "CNPJ").text = cnpj_emit
    etree.SubElement(inf_evento, "chMDFe").text = ch_mdfe
    etree.SubElement(inf_evento, "dhEvento").text = dh_evento
    etree.SubElement(inf_evento, "tpEvento").text = tp_evento
    etree.SubElement(inf_evento, "nSeqEvento").text = n_seq_evento
    etree.SubElement(inf_evento, "verEvento").text = "3.00"

    det = etree.SubElement(inf_evento, "detEvento", versaoEvento="3.00")
    ev = etree.SubElement(det, "evIncCondutorMDFe")
    etree.SubElement(ev, "descEvento").text = "Inclusao de Condutor"
    condutor = etree.SubElement(ev, "condutor")
    etree.SubElement(condutor, "xNome").text = xnome
    etree.SubElement(condutor, "CPF").text = cpf

    xml_bytes = etree.tostring(
        root,
        encoding="utf-8",
        xml_declaration=True,
        pretty_print=False,
    )
    return xml_bytes.decode("utf-8")


def _assinar_evento_mdfe(xml_evento: str, certificado: str, senha_certificado: str) -> str:
    """
    Assina o XML do evento (infEvento) usando o PFX informado.
    """
    return assinar_mdfe_evento_xml(
        xml_evento,
        pfx_path=certificado,
        pfx_password=senha_certificado,
    )


def _monta_envelope_soap(xml_evento_assinado: str, uf: str) -> str:
    """
    Monta o envelope SOAP 1.2 para MDFeRecepcaoEvento.
    """
    cuf = uf_to_cuf(uf)

    nsmap_env = {
        "soap12": SOAP_ENV_NS,
        "xsi": "http://www.w3.org/2001/XMLSchema-instance",
        "xsd": "http://www.w3.org/2001/XMLSchema",
    }
    envelope = etree.Element(etree.QName(SOAP_ENV_NS, "Envelope"), nsmap=nsmap_env)

    header = etree.SubElement(envelope, etree.QName(SOAP_ENV_NS, "Header"))
    cabec = etree.SubElement(header, "mdfeCabecMsg", xmlns=MDFe_WSDL_EVENTO)
    etree.SubElement(cabec, "cUF").text = cuf
    etree.SubElement(cabec, "versaoDados").text = "3.00"

    body = etree.SubElement(envelope, etree.QName(SOAP_ENV_NS, "Body"))
    dados_msg = etree.SubElement(body, "mdfeDadosMsg", xmlns=MDFe_WSDL_EVENTO)

    evento_root = etree.fromstring(xml_evento_assinado.encode("utf-8"))
    dados_msg.append(evento_root)

    xml_bytes = etree.tostring(
        envelope,
        encoding="utf-8",
        xml_declaration=True,
        pretty_print=False,
    )
    return xml_bytes.decode("utf-8")


def _extrai_status_motivo(xml_retorno: str) -> tuple[str, str]:
    """
    Extrai cStat / xMotivo do XML de retorno.
    """
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


def sefaz_mdfe_inc_condutor(
    uf: str,
    ambiente: Literal["1", "2"],
    chave: str,
    cpf: str,
    xnome: str,
    certificado: str,
    senha_certificado: str,
    nseq_evento: str = "1",
) -> MDFeResultado:
    """
    Inclusão de Condutor em MDF-e (evento 110114).
    """
    # 1) Monta XML do evento
    xml_evento = _monta_xml_evento_inc_condutor(
        uf=uf,
        ambiente=ambiente,
        ch_mdfe=chave,
        cpf=cpf,
        xnome=xnome,
        nseq_evento=nseq_evento,
    )

    # 2) Assina o evento
    xml_evento_assinado = _assinar_evento_mdfe(
        xml_evento,
        certificado=certificado,
        senha_certificado=senha_certificado,
    )

    # 3) Monta envelope SOAP
    xml_envelope = _monta_envelope_soap(xml_evento_assinado, uf=uf)

    # 4) URL do serviço
    url = mdfe_url_recepcao_evento(ambiente)

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
    cstat, xmotivo = _extrai_status_motivo(xml_retorno)

    return MDFeResultado(
        status=cstat or str(resp.status_code),
        motivo=xmotivo or f"Retorno HTTP {resp.status_code}",
        xml_envio=xml_envelope,
        xml_retorno=xml_retorno,
    )
