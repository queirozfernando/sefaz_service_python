# sefaz_service/core/nfe_gtin.py
from __future__ import annotations

from lxml import etree
from dataclasses import dataclass

from .envio import enviar_soap_com_pfx, extrair_xml_resultado, EndpointInfo

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
# Montagem do XML <consGTIN>  (SEM declaração XML)
# ----------------------------------------------------------------------
def montar_xml_gtin(gtin: str) -> str:
    """
    Gera apenas o bloco <consGTIN>...</consGTIN>, sem <?xml ...?>,
    igual ao envelope que você usa no Harbour.
    """
    root = etree.Element(
        "consGTIN",
        versao="1.00",
        xmlns="http://www.portalfiscal.inf.br/nfe",
    )
    etree.SubElement(root, "GTIN").text = gtin

    # retorna só o elemento, sem xml_declaration
    return etree.tostring(root, encoding="unicode", xml_declaration=False)


# ----------------------------------------------------------------------
# SOAP envelope (ccgConsGTIN) – igual ao Harbour
# ----------------------------------------------------------------------
def montar_soap_gtin(xml_envio: str) -> str:
    xml_envio = xml_envio.strip()

    return f"""<?xml version="1.0" encoding="UTF-8"?>
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
# Helper: pega texto independente de namespace
# ----------------------------------------------------------------------
def _get_text_any_ns(root: etree._Element, local_name: str) -> str | None:
    """
    Tenta encontrar uma tag (ex.: 'cStat', 'xMotivo') considerando:
      - namespace da NFe
      - namespace do WSDL
      - sem namespace
    """
    ns_uris = [
        "http://www.portalfiscal.inf.br/nfe",
        "http://www.portalfiscal.inf.br/nfe/wsdl/ccgConsGtin",
    ]

    # 1) tenta com namespaces conhecidos
    for uri in ns_uris:
        el = root.find(f".//{{{uri}}}{local_name}")
        if el is not None and el.text:
            return el.text.strip()

    # 2) tenta sem namespace
    el = root.find(f".//{local_name}")
    if el is not None and el.text:
        return el.text.strip()

    return None


# ----------------------------------------------------------------------
# Envio completo + parse robusto
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

    # 4) Extrai XML interno do SOAP; se falhar, fica com texto bruto
    try:
        xml_ret = extrair_xml_resultado(resp.text)
    except Exception:
        xml_ret = resp.text or ""

    status: int | None = None
    motivo: str | None = None

    # Se não tiver nada, só devolve pra debug
    if not xml_ret or not xml_ret.strip():
        return GtinResult(
            status=None,
            motivo=None,
            xml_envio=xml_envio,
            xml_retorno=xml_ret,
        )

    # Se não for XML (pode ser HTML de erro, texto, etc.)
    if not xml_ret.lstrip().startswith("<"):
        return GtinResult(
            status=None,
            motivo=None,
            xml_envio=xml_envio,
            xml_retorno=xml_ret,
        )

    # 5) Tentar interpretar cStat / xMotivo com tolerância a namespace
    try:
        root = etree.fromstring(xml_ret.encode("utf-8"))

        cstat_txt = _get_text_any_ns(root, "cStat")
        xmot_txt = _get_text_any_ns(root, "xMotivo")

        if cstat_txt and cstat_txt.isdigit():
            status = int(cstat_txt)
        else:
            status = None

        motivo = xmot_txt
    except Exception:
        status = None
        motivo = None

    return GtinResult(
        status=status,
        motivo=motivo,
        xml_envio=xml_envio,
        xml_retorno=xml_ret,
    )
