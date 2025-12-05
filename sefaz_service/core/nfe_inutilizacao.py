# sefaz_service/core/nfe_inutilizacao.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

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
class InutilizacaoRequest:
    cUF: str          # código numérico da UF (ex.: "12" para AC)
    tpAmb: str        # "1" = produção, "2" = homologação
    ano: str          # "25" para 2025
    CNPJ: str
    mod: str          # "55" ou "65"
    serie: str        # "1", "2", etc.
    nNFIni: str       # número inicial
    nNFFin: str       # número final
    xJust: str        # justificativa (mínimo 15 caracteres)


@dataclass
class InutilizacaoResponse:
    cStat: Optional[str]
    xMotivo: Optional[str]
    nProt: Optional[str] = None
    dhRecbto: Optional[str] = None
    raw_xml: Optional[str] = None


# ----------------------------------------------------------------------
# HELPERS
# ----------------------------------------------------------------------


def _only_digits(s: str) -> str:
    return "".join(c for c in (s or "") if c.isdigit())


# ----------------------------------------------------------------------
# MONTAGEM DO XML inutNFe
# ----------------------------------------------------------------------


def montar_xml_inutilizacao(req: InutilizacaoRequest) -> str:
    """
    Monta o XML <inutNFe> 4.00 (não assinado).
    """
    cUF = req.cUF.zfill(2)
    CNPJ = _only_digits(req.CNPJ).zfill(14)
    mod = req.mod.zfill(2)
    serie = req.serie.zfill(3)
    nNFIni = req.nNFIni.zfill(9)
    nNFFin = req.nNFFin.zfill(9)

    # ID = "ID" + cUF + ano + CNPJ + mod + serie + nNFIni + nNFFin
    Id = f"ID{cUF}{req.ano}{CNPJ}{mod}{serie}{nNFIni}{nNFFin}"

    root = etree.Element(
        "{http://www.portalfiscal.inf.br/nfe}inutNFe",
        versao="4.00",
        nsmap={None: NFE_NS},
    )

    inf_inut = etree.SubElement(root, "{http://www.portalfiscal.inf.br/nfe}infInut")
    inf_inut.set("Id", Id)

    etree.SubElement(inf_inut, "{http://www.portalfiscal.inf.br/nfe}tpAmb").text = req.tpAmb
    etree.SubElement(inf_inut, "{http://www.portalfiscal.inf.br/nfe}xServ").text = "INUTILIZAR"
    etree.SubElement(inf_inut, "{http://www.portalfiscal.inf.br/nfe}cUF").text = cUF
    etree.SubElement(inf_inut, "{http://www.portalfiscal.inf.br/nfe}ano").text = req.ano
    etree.SubElement(inf_inut, "{http://www.portalfiscal.inf.br/nfe}CNPJ").text = CNPJ
    etree.SubElement(inf_inut, "{http://www.portalfiscal.inf.br/nfe}mod").text = mod
    etree.SubElement(inf_inut, "{http://www.portalfiscal.inf.br/nfe}serie").text = serie
    etree.SubElement(inf_inut, "{http://www.portalfiscal.inf.br/nfe}nNFIni").text = nNFIni
    etree.SubElement(inf_inut, "{http://www.portalfiscal.inf.br/nfe}nNFFin").text = nNFFin
    etree.SubElement(inf_inut, "{http://www.portalfiscal.inf.br/nfe}xJust").text = req.xJust

    xml_bytes = etree.tostring(root, encoding="utf-8", xml_declaration=True)
    return xml_bytes.decode("utf-8")


# ----------------------------------------------------------------------
# ASSINATURA com NFeXmlSigner
# ----------------------------------------------------------------------


def assinar_xml_inutilizacao(xml_inut: str, pfx_path: str, pfx_password: str) -> str:
    """
    Assina o nó <infInut> usando o mesmo mecanismo da NFe (NFeXmlSigner).

    OBS: usamos o método interno _sign com XPath específico para infInut.
    """
    signer = NFeXmlSigner(pfx_path=pfx_path, pfx_password=pfx_password)
    # Reutiliza o método genérico interno para o nó infInut
    return signer._sign(  # noqa: SLF001 (sabemos que é "privado" só por convenção)
        xml=xml_inut,
        referencia_xpath="//nfe:infInut[1]",
        id_atributo="Id",
    )


# ----------------------------------------------------------------------
# ENDPOINT do serviço NFeInutilizacao4
# ----------------------------------------------------------------------


def _get_inutilizacao_endpoint(uf_sigla: str, ambiente: str) -> EndpointInfo:
    """
    Usa o mesmo mapeamento de UF/ambiente da autorização, trocando apenas
    o caminho para o serviço de inutilização (NFeInutilizacao4).
    """
    aut_ep = get_nfe_autorizacao4_endpoint(uf_sigla, ambiente)

    url = aut_ep.url
    # Ajustes típicos – funcionam para a maioria dos estados.
    url = (
        url.replace("NFeAutorizacao4", "NFeInutilizacao4")
           .replace("NFeAutorizacao/NFeAutorizacao4.asmx",
                    "NFeInutilizacao4/NFeInutilizacao4.asmx")
    )

    soap_action = "http://www.portalfiscal.inf.br/nfe/wsdl/NFeInutilizacao4/nfeInutilizacaoNF"
    return EndpointInfo(url=url, soap_action=soap_action)


# ----------------------------------------------------------------------
# ENVIO COMPLETO
# ----------------------------------------------------------------------


def enviar_inutilizacao(
    req: InutilizacaoRequest,
    certificado: str,
    senha: str,
    uf_sigla: str,
) -> InutilizacaoResponse:
    """
    Fluxo completo:
      1) monta inutNFe
      2) assina infInut
      3) monta envelope SOAP
      4) envia via enviar_soap_com_pfx
      5) extrai e interpreta retorno
    """
    # 1) monta
    xml_inut = montar_xml_inutilizacao(req)

    # 2) assina
    xml_assinado = assinar_xml_inutilizacao(
        xml_inut,
        pfx_path=certificado,
        pfx_password=senha,
    )

    # 3) endpoint
    ep = _get_inutilizacao_endpoint(uf_sigla=uf_sigla, ambiente=req.tpAmb)

    # 4) envelope SOAP
    soap_xml = f"""<?xml version="1.0" encoding="utf-8"?>
<soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                 xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                 xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
  <soap12:Body>
    <nfeDadosMsg xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NFeInutilizacao4">
      {xml_assinado}
    </nfeDadosMsg>
  </soap12:Body>
</soap12:Envelope>"""

    # 5) enviar usando MESMO fluxo da NFe
    resp = enviar_soap_com_pfx(
        endpoint=ep,
        soap_xml=soap_xml,
        pfx_path=certificado,
        pfx_password=senha,
    )

    # 6) extrair XML "limpo" da resposta
    xml_retorno = extrair_xml_resultado(resp.text)

    # 7) interpretar
    return _parse_inutilizacao_response(xml_retorno)


# ----------------------------------------------------------------------
# PARSE DO RETORNO
# ----------------------------------------------------------------------


def _parse_inutilizacao_response(xml_retorno: str) -> InutilizacaoResponse:
    """
    Extrai cStat, xMotivo, nProt e dhRecbto do retorno de inutilização.
    """
    try:
        root = etree.fromstring(xml_retorno.encode("utf-8"))
    except Exception:
        return InutilizacaoResponse(
            cStat=None,
            xMotivo="Falha ao parsear XML de retorno da inutilizacao",
            raw_xml=xml_retorno,
        )

    inf_inut = root.find(".//{http://www.portalfiscal.inf.br/nfe}infInut")
    if inf_inut is None:
        return InutilizacaoResponse(
            cStat=None,
            xMotivo="Retorno de inutilizacao sem infInut",
            raw_xml=xml_retorno,
        )

    cStat = inf_inut.findtext("{http://www.portalfiscal.inf.br/nfe}cStat", default=None)
    xMotivo = inf_inut.findtext("{http://www.portalfiscal.inf.br/nfe}xMotivo", default=None)
    nProt = inf_inut.findtext("{http://www.portalfiscal.inf.br/nfe}nProt", default=None)
    dhRecbto = inf_inut.findtext("{http://www.portalfiscal.inf.br/nfe}dhRecbto", default=None)

    return InutilizacaoResponse(
        cStat=cStat,
        xMotivo=xMotivo,
        nProt=nProt,
        dhRecbto=dhRecbto,
        raw_xml=xml_retorno,
    )
