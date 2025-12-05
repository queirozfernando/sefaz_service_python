# sefaz_service/core/nfe_gtin.py
from __future__ import annotations

from dataclasses import dataclass
from lxml import etree

from .envio import enviar_soap_com_pfx, extrair_xml_resultado, EndpointInfo


# Endpoint único (SVRS) – igual ao Harbour
GTIN_ENDPOINT = EndpointInfo(
    url="https://dfe-servico.svrs.rs.gov.br/ws/ccgConsGTIN/ccgConsGTIN.asmx",
    soap_action="http://www.portalfiscal.inf.br/nfe/wsdl/ccgConsGtin/ccgConsGTIN",
)


@dataclass
class GtinResult:
    status: int | None
    motivo: str | None
    xml_envio: str
    xml_retorno: str


# ----------------------------------------------------------------------
# Montagem do XML <consGTIN>
# ----------------------------------------------------------------------
def montar_xml_gtin(gtin: str) -> str:
    root = etree.Element(
        "consGTIN",
        versao="1.00",
        xmlns="http://www.portalfiscal.inf.br/nfe",
    )
    etree.SubElement(root, "GTIN").text = gtin

    xml_bytes = etree.tostring(root, encoding="utf-8", xml_declaration=True)
    return xml_bytes.decode("utf-8")


# ----------------------------------------------------------------------
# SOAP envelope (ccgConsGTIN)
# ----------------------------------------------------------------------
def montar_soap_gtin(xml_envio: str) -> str:
    return f"""<?xml version="1.0" encoding="utf-8"?>
<soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                 xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                 xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
  <soap12:Body>
    <ccgConsGTIN xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/ccgConsGtin">
      <nfeDadosMsg>
        {xml_envio}
      </nfeDadosMsg>
    </ccgConsGTIN>
  </soap12:Body>
</soap12:Envelope>"""


# ----------------------------------------------------------------------
# Envio completo + parse **super seguro**
# ----------------------------------------------------------------------
def sefaz_consulta_gtin(gtin: str, pfx_path: str, pfx_password: str) -> GtinResult:
    # 1) XML de envio
    xml_envio = montar_xml_gtin(gtin)

    # 2) SOAP
    soap_xml = montar_soap_gtin(xml_envio)

    # 3) Envio
    resp = enviar_soap_com_pfx(
        endpoint=GTIN_ENDPOINT,
        soap_xml=soap_xml,
        pfx_path=pfx_path,
        pfx_password=pfx_password,
    )

    # 4) Tentar extrair XML limpo; se der erro, cai pro texto bruto
    try:
        xml_ret = extrair_xml_resultado(resp.text)
    except Exception:
        xml_ret = resp.text or ""

    status: int | None = None
    motivo: str | None = None

    # Se não tiver nada, apenas devolve o texto bruto pra debug
    if not xml_ret or not xml_ret.strip():
        return GtinResult(
            status=None,
            motivo=None,
            xml_envio=xml_envio,
            xml_retorno=xml_ret,
        )

    # Se não parece XML (ex.: HTML de erro), não tenta parsear
    if not xml_ret.lstrip().startswith("<"):
        return GtinResult(
            status=None,
            motivo=None,
            xml_envio=xml_envio,
            xml_retorno=xml_ret,
        )

    # 5) Tentar interpretar cStat / xMotivo – se falhar, ignora e devolve bruto
    try:
        root = etree.fromstring(xml_ret.encode("utf-8"))

        ns = {"nfe": "http://www.portalfiscal.inf.br/nfe"}
        cstat_el = root.find(".//nfe:cStat", ns)
        xmot_el = root.find(".//nfe:xMotivo", ns)

        if cstat_el is not None and cstat_el.text:
            status = int(cstat_el.text.strip())
        if xmot_el is not None and xmot_el.text:
            motivo = xmot_el.text.strip()
    except Exception:
        status = None
        motivo = None

    return GtinResult(
        status=status,
        motivo=motivo,
        xml_envio=xml_envio,
        xml_retorno=xml_ret,
    )
