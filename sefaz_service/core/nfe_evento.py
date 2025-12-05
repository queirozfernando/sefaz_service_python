# sefaz_service/core/nfe_evento.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from datetime import datetime
from lxml import etree

from sefaz_service.nfe.assinatura import NFeXmlSigner

from .envio import (
    enviar_soap_com_pfx,
    extrair_xml_resultado,
    EndpointInfo,
)
from .soaplist import get_nfe_autorizacao4_endpoint

NFE_NS = "http://www.portalfiscal.inf.br/nfe"
NSMAP = {"nfe": NFE_NS}


# ----------------------------------------------------------------------
# MODELOS
# ----------------------------------------------------------------------


@dataclass
class EventoRequest:
    """
    Dados para montar um evento de NFe.

    tpEvento:
        - "110110" = Carta de Correcao
        - "110111" = Cancelamento
        - "110112" = Cancelamento por substituição
    """

    tpAmb: str          # "1" produção, "2" homologação
    cOrgao: str        # código da UF (ex.: "12" para AC)
    CNPJ: str
    chNFe: str
    tpEvento: str      # 110110, 110111 ou 110112
    nSeqEvento: int
    # Campos genéricos (usados conforme o tipo de evento)
    xJust: Optional[str] = None       # usado em cancelamentos
    nProt: Optional[str] = None       # obrigatório para cancelamento
    chNFeRef: Optional[str] = None    # usado no cancelamento por substituição
    xCorrecao: Optional[str] = None   # usado na Carta de Correção (110110)


@dataclass
class EventoResult:
    xml_envio: str
    xml_assinado: str
    xml_retorno: str
    cStat_lote: Optional[int]
    xMotivo_lote: Optional[str]
    cStat_evento: Optional[int]
    xMotivo_evento: Optional[str]
    nProt_evento: Optional[str]


# ----------------------------------------------------------------------
# HELPERS
# ----------------------------------------------------------------------


def _only_digits(s: str) -> str:
    return "".join(c for c in s if c.isdigit())


def _dh_evento_now() -> str:
    """
    Gera data/hora no formato aceito pela SEFAZ, ex.: 2025-12-04T05:30:10-03:00
    Você pode ajustar o fuso se quiser.
    """
    # Aqui assumo -03:00; se quiser outro fuso, é só trocar.
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S-03:00")


# ----------------------------------------------------------------------
# MONTAGEM DO XML
# ----------------------------------------------------------------------


def montar_env_evento_xml(req: EventoRequest) -> str:
    """
    Monta o XML <envEvento> para um único evento (lote com 1 evento).
    Versão 1.00, suficiente para:
      - Cancelamento (110111)
      - Cancelamento por substituição (110112)
      - Carta de Correção (110110)
    """
    CNPJ = _only_digits(req.CNPJ).zfill(14)
    chNFe = req.chNFe.strip()
    nSeq = int(req.nSeqEvento)

    # ID = "ID" + tpEvento + chNFe + nSeqEvento(2)
    Id = f"ID{req.tpEvento}{chNFe}{nSeq:02d}"

    env = etree.Element(
        "{http://www.portalfiscal.inf.br/nfe}envEvento",
        versao="1.00",
        nsmap={None: NFE_NS},
    )
    etree.SubElement(env, "{http://www.portalfiscal.inf.br/nfe}idLote").text = "1"

    evento = etree.SubElement(env, "{http://www.portalfiscal.inf.br/nfe}evento")
    evento.set("versao", "1.00")

    inf_evento = etree.SubElement(
        evento,
        "{http://www.portalfiscal.inf.br/nfe}infEvento",
    )
    inf_evento.set("Id", Id)

    etree.SubElement(inf_evento, "{http://www.portalfiscal.inf.br/nfe}cOrgao").text = req.cOrgao
    etree.SubElement(inf_evento, "{http://www.portalfiscal.inf.br/nfe}tpAmb").text = req.tpAmb
    etree.SubElement(inf_evento, "{http://www.portalfiscal.inf.br/nfe}CNPJ").text = CNPJ
    etree.SubElement(inf_evento, "{http://www.portalfiscal.inf.br/nfe}chNFe").text = chNFe
    etree.SubElement(inf_evento, "{http://www.portalfiscal.inf.br/nfe}dhEvento").text = _dh_evento_now()
    etree.SubElement(inf_evento, "{http://www.portalfiscal.inf.br/nfe}tpEvento").text = req.tpEvento
    etree.SubElement(inf_evento, "{http://www.portalfiscal.inf.br/nfe}nSeqEvento").text = str(nSeq)
    etree.SubElement(inf_evento, "{http://www.portalfiscal.inf.br/nfe}verEvento").text = "1.00"

    det = etree.SubElement(
        inf_evento,
        "{http://www.portalfiscal.inf.br/nfe}detEvento",
    )
    det.set("versao", "1.00")

    if req.tpEvento == "110111":
        # Cancelamento
        etree.SubElement(det, "{http://www.portalfiscal.inf.br/nfe}descEvento").text = "Cancelamento"
        etree.SubElement(det, "{http://www.portalfiscal.inf.br/nfe}nProt").text = req.nProt or ""
        etree.SubElement(det, "{http://www.portalfiscal.inf.br/nfe}xJust").text = req.xJust or ""
    elif req.tpEvento == "110112":
        # Cancelamento por substituição
        etree.SubElement(det, "{http://www.portalfiscal.inf.br/nfe}descEvento").text = "Cancelamento por substituicao"
        if req.chNFeRef:
            etree.SubElement(det, "{http://www.portalfiscal.inf.br/nfe}chNFeRef").text = req.chNFeRef
        etree.SubElement(det, "{http://www.portalfiscal.inf.br/nfe}nProt").text = req.nProt or ""
        etree.SubElement(det, "{http://www.portalfiscal.inf.br/nfe}xJust").text = req.xJust or ""
    elif req.tpEvento == "110110":
        # Carta de Correção
        etree.SubElement(det, "{http://www.portalfiscal.inf.br/nfe}descEvento").text = "Carta de Correcao"
        etree.SubElement(det, "{http://www.portalfiscal.inf.br/nfe}xCorrecao").text = req.xCorrecao or ""
        etree.SubElement(
            det,
            "{http://www.portalfiscal.inf.br/nfe}xCondUso",
        ).text = (
            "A Carta de Correcao e disciplinada pelo paragrafo 1o-A do art. 7o do "
            "Convenio S/N, de 15 de dezembro de 1970 e pode ser utilizada para "
            "regularizacao de erros ocorridos na emissao de documentos fiscais, "
            "desde que o erro nao esteja relacionado com: I - as variaveis que "
            "determinam o valor do imposto, tais como: base de calculo, aliquota, "
            "diferenca de preco, quantidade, valor da operacao ou da prestacao; "
            "II - a correcao de dados cadastrais que implique mudanca do remetente "
            "ou do destinatario; III - a data de emissao ou de saida."
        )
    else:
        # Caso queira suportar outros eventos no futuro
        etree.SubElement(det, "{http://www.portalfiscal.inf.br/nfe}descEvento").text = "Evento"
        etree.SubElement(det, "{http://www.portalfiscal.inf.br/nfe}xJust").text = req.xJust or ""

    xml_bytes = etree.tostring(env, encoding="utf-8", xml_declaration=True)
    return xml_bytes.decode("utf-8")


# ----------------------------------------------------------------------
# ASSINATURA COM NFeXmlSigner
# ----------------------------------------------------------------------


def assinar_evento_xml(xml_env: str, pfx_path: str, pfx_password: str) -> str:
    """
    Assina o nó <infEvento> usando o mesmo mecanismo de assinatura
    da NFe (classe NFeXmlSigner).
    """
    signer = NFeXmlSigner(pfx_path=pfx_path, pfx_password=pfx_password)
    return signer.assinar_inf_evento(xml_env)


# ----------------------------------------------------------------------
# ENDPOINT DO SERVIÇO NFeRecepcaoEvento4
# ----------------------------------------------------------------------


def _get_evento_endpoint(uf_sigla: str, ambiente: str) -> EndpointInfo:
    """
    Usa o mesmo mapeamento de UF/ambiente da autorização, trocando apenas
    o caminho para o serviço de eventos (NFeRecepcaoEvento4).
    """
    aut_ep = get_nfe_autorizacao4_endpoint(uf_sigla, ambiente)

    url = aut_ep.url
    # Ajustes típicos – funcionam para a maioria dos estados.
    url = (
        url.replace("NFeAutorizacao4", "NFeRecepcaoEvento4")
           .replace("NFeAutorizacao/NFeAutorizacao4.asmx",
                    "NFeRecepcaoEvento4/NFeRecepcaoEvento4.asmx")
    )

    soap_action = "http://www.portalfiscal.inf.br/nfe/wsdl/NFeRecepcaoEvento4/nfeRecepcaoEvento"
    return EndpointInfo(url=url, soap_action=soap_action)


# ----------------------------------------------------------------------
# ENVIO COMPLETO (equivalente ao sefaz_nfe_envio)
# ----------------------------------------------------------------------


def sefaz_enviar_evento(
    req: EventoRequest,
    uf: str,
    pfx_path: str,
    pfx_password: str,
) -> EventoResult:
    """
    Fluxo completo:
      1) Monta envEvento
      2) Assina (infEvento)
      3) Monta SOAP
      4) Envia com certificado PFX
      5) Extrai e interpreta retorno
    """
    # 1) Montar envEvento
    xml_envio = montar_env_evento_xml(req)

    # 2) Assinar
    xml_assinado = assinar_evento_xml(xml_envio, pfx_path, pfx_password)

    # 3) Endpoint
    endpoint = _get_evento_endpoint(uf_sigla=uf, ambiente=req.tpAmb)

    # 4) SOAP envelope específico para RecepcaoEvento4
    soap_xml = f"""<?xml version="1.0" encoding="utf-8"?>
<soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                 xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                 xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
  <soap12:Body>
    <nfeDadosMsg xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NFeRecepcaoEvento4">
      {xml_assinado}
    </nfeDadosMsg>
  </soap12:Body>
</soap12:Envelope>"""

    # 5) Enviar usando a MESMA função da NFe (enviar_soap_com_pfx)
    resp = enviar_soap_com_pfx(
        endpoint=endpoint,
        soap_xml=soap_xml,
        pfx_path=pfx_path,
        pfx_password=pfx_password,
    )

    # 6) Extrair o XML puro do resultado (igual na NFe)
    xml_retorno = extrair_xml_resultado(resp.text)

    cStat_lote, xMotivo_lote, cStat_evento, xMotivo_evento, nProt_evento = _parse_evento_retorno(
        xml_retorno
    )

    return EventoResult(
        xml_envio=xml_envio,
        xml_assinado=xml_assinado,
        xml_retorno=xml_retorno,
        cStat_lote=cStat_lote,
        xMotivo_lote=xMotivo_lote,
        cStat_evento=cStat_evento,
        xMotivo_evento=xMotivo_evento,
        nProt_evento=nProt_evento,
    )


# ----------------------------------------------------------------------
# PARSE DO RETORNO
# ----------------------------------------------------------------------


def _parse_evento_retorno(xml_retorno: str):
    """
    Extrai:
      - cStat / xMotivo do lote (retEnvEvento)
      - cStat / xMotivo / nProt do evento (infEvento)
    """
    try:
        root = etree.fromstring(xml_retorno.encode("utf-8"))
    except Exception:
        return None, None, None, None, None

    # retEnvEvento
    ret_env = root.find(".//{http://www.portalfiscal.inf.br/nfe}retEnvEvento")
    if ret_env is None:
        return None, None, None, None, None

    cStat_lote_el = ret_env.find("{http://www.portalfiscal.inf.br/nfe}cStat")
    xMotivo_lote_el = ret_env.find("{http://www.portalfiscal.inf.br/nfe}xMotivo")

    cStat_lote = int(cStat_lote_el.text.strip()) if cStat_lote_el is not None else None
    xMotivo_lote = xMotivo_lote_el.text.strip() if xMotivo_lote_el is not None else None

    inf_evento = ret_env.find(".//{http://www.portalfiscal.inf.br/nfe}infEvento")
    if inf_evento is None:
        return cStat_lote, xMotivo_lote, None, None, None

    cStat_evento_el = inf_evento.find("{http://www.portalfiscal.inf.br/nfe}cStat")
    xMotivo_evento_el = inf_evento.find("{http://www.portalfiscal.inf.br/nfe}xMotivo")
    nProt_el = inf_evento.find("{http://www.portalfiscal.inf.br/nfe}nProt")

    cStat_evento = int(cStat_evento_el.text.strip()) if cStat_evento_el is not None else None
    xMotivo_evento = xMotivo_evento_el.text.strip() if xMotivo_evento_el is not None else None
    nProt_evento = nProt_el.text.strip() if nProt_el is not None else None

    return cStat_lote, xMotivo_lote, cStat_evento, xMotivo_evento, nProt_evento
