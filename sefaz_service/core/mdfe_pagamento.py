from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, List, Dict, Any

from lxml import etree
import requests_pkcs12

from sefaz_service.core.assinatura import assinar_mdfe_xml  # ou assinar_mdfe_evento_xml
from sefaz_service.core.uf_utils import uf_to_cuf, mdfe_url_recepcao_evento

MDFe_NS = "http://www.portalfiscal.inf.br/mdfe"
SOAP_ENV_NS = "http://www.w3.org/2003/05/soap-envelope"
MDFe_WSDL_EVENTO = "http://www.portalfiscal.inf.br/mdfe/wsdl/MDFeRecepcaoEvento"


@dataclass
class MDFeResultado:
    """
    Resultado padrão dos serviços MDFe (status, consulta, envio, eventos).
    """
    status: str
    motivo: str
    xml_envio: str
    xml_retorno: str


def _monta_xml_evento_pagamento(
    uf: str,
    ambiente: Literal["1", "2"],
    ch_mdfe: str,
    nprot: str,
    qtd_viagens: str,
    nro_viagem: str,
    inf_pag_list: List[Dict[str, Any]],
    nseq_evento: str = "1",
) -> str:
    """
    Monta o XML do evento de Pagamento da Operação de Transporte
    (evPagtoOperMDFe – tipo 110116) dentro de eventoMDFe/infEvento/detEvento.
    """
    if len(ch_mdfe) != 44 or not ch_mdfe.isdigit():
        raise ValueError("chMDFe deve ter 44 dígitos numéricos")

    cuf = uf_to_cuf(uf)

    cnpj_emit = ch_mdfe[6:20]

    tp_evento = "110116"
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

    det_evento = etree.SubElement(inf_evento, "detEvento", versaoEvento="3.00")
    ev_pag = etree.SubElement(det_evento, "evPagtoOperMDFe")

    etree.SubElement(ev_pag, "descEvento").text = "Pagamento Operacao MDF-e"
    etree.SubElement(ev_pag, "nProt").text = nprot

    inf_viagens = etree.SubElement(ev_pag, "infViagens")
    etree.SubElement(inf_viagens, "qtdViagens").text = qtd_viagens
    etree.SubElement(inf_viagens, "nroViagem").text = nro_viagem

    if not inf_pag_list:
        raise ValueError("É obrigatório informar ao menos um infPag")

    for pag in inf_pag_list:
        infPag_el = etree.SubElement(ev_pag, "infPag")

        xNome = pag.get("xNome")
        if xNome:
            etree.SubElement(infPag_el, "xNome").text = xNome

        cpf = pag.get("CPF")
        cnpj = pag.get("CNPJ")
        idEstr = pag.get("idEstrangeiro")

        if cpf:
            etree.SubElement(infPag_el, "CPF").text = cpf
        if cnpj:
            etree.SubElement(infPag_el, "CNPJ").text = cnpj
        if idEstr:
            etree.SubElement(infPag_el, "idEstrangeiro").text = idEstr

        comps = pag.get("comps") or []
        if not comps:
            raise ValueError("infPag.comps deve ter pelo menos um componente (Comp)")
        for comp in comps:
            comp_el = etree.SubElement(infPag_el, "Comp")
            etree.SubElement(comp_el, "tpComp").text = comp.get("tpComp", "")
            etree.SubElement(comp_el, "vComp").text = comp.get("vComp", "")
            xComp = comp.get("xComp")
            if xComp:
                etree.SubElement(comp_el, "xComp").text = xComp

        vContrato = pag.get("vContrato")
        if not vContrato:
            raise ValueError("infPag.vContrato é obrigatório")
        etree.SubElement(infPag_el, "vContrato").text = vContrato

        indAltoDesemp = pag.get("indAltoDesemp")
        if indAltoDesemp:
            etree.SubElement(infPag_el, "indAltoDesemp").text = indAltoDesemp

        indPag = pag.get("indPag")
        if not indPag:
            raise ValueError("infPag.indPag é obrigatório (0=vista, 1=prazo)")
        etree.SubElement(infPag_el, "indPag").text = indPag

        vAdiant = pag.get("vAdiant")
        if vAdiant:
            etree.SubElement(infPag_el, "vAdiant").text = vAdiant

        prazos = pag.get("prazos") or []
        for pz in prazos:
            infPrazo_el = etree.SubElement(infPag_el, "infPrazo")
            etree.SubElement(infPrazo_el, "nParcela").text = pz.get("nParcela", "")
            etree.SubElement(infPrazo_el, "dVenc").text = pz.get("dVenc", "")
            etree.SubElement(infPrazo_el, "vParcela").text = pz.get("vParcela", "")

        inf_banc = pag.get("infBanc") or {}
        if not inf_banc:
            raise ValueError("infPag.infBanc é obrigatório")

        infBanc_el = etree.SubElement(infPag_el, "infBanc")
        etree.SubElement(infBanc_el, "codBanco").text = inf_banc.get("codBanco", "")
        etree.SubElement(infBanc_el, "codAgencia").text = inf_banc.get("codAgencia", "")
        etree.SubElement(infBanc_el, "CNPJIPEF").text = inf_banc.get("CNPJIPEF", "")
        pix = inf_banc.get("PIX")
        if pix:
            etree.SubElement(infBanc_el, "PIX").text = pix

    xml_bytes = etree.tostring(
        root, encoding="utf-8", xml_declaration=True, pretty_print=False
    )
    return xml_bytes.decode("utf-8")


def _assinar_evento_mdfe(xml_evento: str, certificado: str, senha_certificado: str) -> str:
    # ideal: assinar_mdfe_evento_xml; por enquanto usando assinar_mdfe_xml
    return assinar_mdfe_xml(
        xml_evento,
        pfx_path=certificado,
        pfx_password=senha_certificado,
    )


def _monta_envelope_soap(xml_evento_assinado: str, uf: str) -> str:
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


def sefaz_mdfe_pagamento(
    uf: str,
    ambiente: Literal["1", "2"],
    chave: str,
    nprot: str,
    qtd_viagens: str,
    nro_viagem: str,
    inf_pag_list: List[Dict[str, Any]],
    certificado: str,
    senha_certificado: str,
    nseq_evento: str = "1",
) -> MDFeResultado:
    xml_evento = _monta_xml_evento_pagamento(
        uf=uf,
        ambiente=ambiente,
        ch_mdfe=chave,
        nprot=nprot,
        qtd_viagens=qtd_viagens,
        nro_viagem=nro_viagem,
        inf_pag_list=inf_pag_list,
        nseq_evento=nseq_evento,
    )

    xml_evento_assinado = _assinar_evento_mdfe(
        xml_evento,
        certificado=certificado,
        senha_certificado=senha_certificado,
    )

    xml_envelope = _monta_envelope_soap(xml_evento_assinado, uf=uf)

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
        motivo=xmotivo or "Retorno HTTP " + str(resp.status_code),
        xml_envio=xml_envelope,
        xml_retorno=xml_retorno,
    )
