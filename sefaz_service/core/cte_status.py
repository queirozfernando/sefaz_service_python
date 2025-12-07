# sefaz_service/core/cte_status.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from lxml import etree
from requests_pkcs12 import post  # pacote requests-pkcs12

# Namespace do CT-e (XML de dados)
CTE_NS = "http://www.portalfiscal.inf.br/cte"

# Namespaces base dos WSDLs
CTE_STATUS_WSDL_V3 = "http://www.portalfiscal.inf.br/cte/wsdl/CteStatusServico"
CTE_STATUS_WSDL_V4 = "http://www.portalfiscal.inf.br/cte/wsdl/CTeStatusServicoV4"


@dataclass
class CTeStatusResult:
    status: Optional[int]
    motivo: Optional[str]
    xml_envio: str
    xml_retorno: str


# --- mapa de cUF (mesmo da sua classe Harbour) -------------------------------
MAPA_CUF = {
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


# ---------------------------------------------------------------------------
# Escolha do endpoint (equivalente ao SoapList do Harbour, focado em SVRS)
# ---------------------------------------------------------------------------
def _resolver_url_cte_status(uf: str, ambiente: str, versao: str) -> str:
    """
    Resolve o endpoint do CTeStatusServico, copiando a lógica do SoapList()
    (para o seu caso AC → SVRS).
    """
    uf = (uf or "").upper()
    ambiente = "1" if ambiente == "1" else "2"
    major = (versao or "4.00").split(".", 1)[0]

    # AC é atendido pelo SVRS (linha "RS/SVRS" da sua SoapList)
    # 3.00 → .../CteStatusServico.asmx
    # 4.00 → .../CTeStatusServicoV4/CTeStatusServicoV4.asmx
    if major == "3":
        if ambiente == "1":
            return "https://cte.svrs.rs.gov.br/ws/ctestatusservico/CteStatusServico.asmx"
        else:
            return "https://cte-homologacao.svrs.rs.gov.br/ws/ctestatusservico/CteStatusServico.asmx"
    else:  # 4.00 (padrão)
        if ambiente == "1":
            return "https://cte.svrs.rs.gov.br/ws/CTeStatusServicoV4/CTeStatusServicoV4.asmx"
        else:
            return "https://cte-homologacao.svrs.rs.gov.br/ws/CTeStatusServicoV4/CTeStatusServicoV4.asmx"


# ---------------------------------------------------------------------------
# Montagem do XML de dados (igual ao ze_sefaz_CTeStatus)
# ---------------------------------------------------------------------------
def _montar_xml_cons_stat_serv_cte(tp_amb: str, uf: str, versao: str) -> str:
    """
    Copia a lógica do Harbour:

    IF ::cVersao == "3.00"
       <consStatServCte versao="3.00" xmlns="...">
           <tpAmb>...</tpAmb>
           <xServ>STATUS</xServ>
       </consStatServCte>
    ELSE
       <consStatServCTe versao="4.00" xmlns="...">
           <tpAmb>...</tpAmb>
           <cUF>12</cUF>
           <xServ>STATUS</xServ>
       </consStatServCTe>
    ENDIF
    """
    versao = versao or "4.00"
    major = versao.split(".", 1)[0]

    if major == "3":
        # Layout 3.00 — sem cUF
        return (
            f'<consStatServCte versao="{versao}" xmlns="{CTE_NS}">'
            f"<tpAmb>{tp_amb}</tpAmb>"
            "<xServ>STATUS</xServ>"
            "</consStatServCte>"
        )
    else:
        # Layout 4.00 — com cUF (igual seu ELSE)
        uf = (uf or "").upper()
        cuf = MAPA_CUF.get(uf, uf)  # se já vier "12", mantém

        return (
            f'<consStatServCTe versao="{versao}" xmlns="{CTE_NS}">'
            f"<tpAmb>{tp_amb}</tpAmb>"
            f"<cUF>{cuf}</cUF>"
            "<xServ>STATUS</xServ>"
            "</consStatServCTe>"
        )


# ---------------------------------------------------------------------------
# Função principal chamada pela API
# ---------------------------------------------------------------------------
def sefaz_cte_status(
    uf: str,
    pfx_path: str,
    pfx_password: str,
    ambiente: str = "2",
    versao: str = "4.00",
) -> CTeStatusResult:
    """
    Consulta STATUS do serviço de CT-e.
    Versão pode ser "3.00" (CteStatusServico) ou "4.00" (CTeStatusServicoV4),
    igual à sua classe Harbour.
    """
    tp_amb = "1" if ambiente == "1" else "2"
    versao = versao or "4.00"
    major = versao.split(".", 1)[0]

    # XML interno, igual ao Harbour
    xml_envio = _montar_xml_cons_stat_serv_cte(tp_amb=tp_amb, uf=uf, versao=versao)

    # Escolhe WSDL/namespace SOAP conforme a versão
    if major == "3":
        wsdl_ns = CTE_STATUS_WSDL_V3
    else:
        wsdl_ns = CTE_STATUS_WSDL_V4

    soap_action = f"{wsdl_ns}/cteStatusServicoCT"

    # Envelope SOAP 1.2 com cteDadosMsg (padrão CT-e)
    envelope = f"""<?xml version="1.0" encoding="utf-8"?>
<soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                 xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                 xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
  <soap12:Body>
    <cteStatusServicoCT xmlns="{wsdl_ns}">
      <cteDadosMsg xmlns="{wsdl_ns}">
        {xml_envio}
      </cteDadosMsg>
    </cteStatusServicoCT>
  </soap12:Body>
</soap12:Envelope>
"""

    url = _resolver_url_cte_status(uf=uf, ambiente=ambiente, versao=versao)

    resp = post(
        url,
        data=envelope.encode("utf-8"),
        pkcs12_filename=pfx_path,
        pkcs12_password=pfx_password,
        headers={
            # SOAP 1.2: action no próprio Content-Type
            "Content-Type": (
                f'application/soap+xml; charset="utf-8"; '
                f'action="{soap_action}"'
            ),
        },
        timeout=30,
        verify=False,  # igual você já usou para NFe/GTIN
    )

    xml_retorno = resp.text

    # Extrai cStat/xMotivo de dentro do XML (namespace do CT-e)
    status_int: Optional[int] = None
    motivo_str: Optional[str] = None
    try:
        root = etree.fromstring(xml_retorno.encode("utf-8"))
        ns = {"cte": CTE_NS}

        cstat_el = root.find(".//cte:cStat", namespaces=ns)
        xmot_el = root.find(".//cte:xMotivo", namespaces=ns)

        if cstat_el is not None and cstat_el.text:
            try:
                status_int = int(cstat_el.text.strip())
            except ValueError:
                status_int = None

        if xmot_el is not None and xmot_el.text:
            motivo_str = xmot_el.text.strip()
    except Exception:
        if resp.status_code != 200 and not motivo_str:
            motivo_str = f"HTTP {resp.status_code} - {resp.reason}"

    return CTeStatusResult(
        status=status_int,
        motivo=motivo_str,
        xml_envio=xml_envio,
        xml_retorno=xml_retorno,
    )
