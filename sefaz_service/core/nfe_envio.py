# sefaz_service/core/nfe_envio.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
import re

from lxml import etree

from .assinatura import assinar_nfe_xml
from .envio import (
    montar_envi_nfe_xml,
    montar_soap_envelope,
    enviar_soap_com_pfx,
    extrair_xml_resultado,
    EndpointInfo,
)
from .soaplist import get_nfe_autorizacao4_endpoint


@dataclass
class NFeEnvioResult:
    xml_assinado: str
    xml_envi_nfe: str
    xml_retorno: str
    status: Optional[int]
    motivo: Optional[str]


def _resolver_cuf(xml_nfe: str, uf: str) -> str:
    m = re.search(r"<cUF>(\d{2})</cUF>", xml_nfe)
    if m:
        return m.group(1)

    UF_TO_CUF = {
        "RO": "11", "AC": "12", "AM": "13", "RR": "14", "PA": "15", "AP": "16", "TO": "17",
        "MA": "21", "PI": "22", "CE": "23", "RN": "24", "PB": "25", "PE": "26", "AL": "27",
        "SE": "28", "BA": "29", "MG": "31", "ES": "32", "RJ": "33", "SP": "35", "PR": "41",
        "SC": "42", "RS": "43", "MS": "50", "MT": "51", "GO": "52", "DF": "53",
    }

    return UF_TO_CUF.get(uf.upper(), "")


def _obter_status_motivo(xml_retorno: str):
    try:
        root = etree.fromstring(xml_retorno.encode("utf-8"))
    except:
        return None, None

    cstat = root.find(".//cStat")
    xmot = root.find(".//xMotivo")

    return (
        int(cstat.text.strip()) if cstat is not None else None,
        xmot.text.strip() if xmot is not None else None,
    )


def sefaz_nfe_envio(
    xml_nfe: str,
    uf: str,
    pfx_path: str,
    pfx_password: str,
    ambiente: str = "2",
    versao: str = "4.00",
    id_lote: str = "1",
    envio_sinc: Optional[bool] = None,
    **kwargs,
) -> NFeEnvioResult:

    # 1) Assinar
    xml_assinado = assinar_nfe_xml(xml_nfe, pfx_path, pfx_password)

    if not xml_assinado.strip():
        raise RuntimeError("Falha ao assinar NFe.")

    # 2) Montar enviNFe — incorporando o XML assinado INTACTO
    xml_envi_nfe = montar_envi_nfe_xml(
        nfe_assinada=xml_assinado,
        versao=versao,
        id_lote=id_lote,
        ind_sinc=True,
    )

    # ❗ NÃO modificar assinatura
    # (compactar_assinatura_no_envio foi removido)

    # 3) Endpoint
    endpoint: EndpointInfo = get_nfe_autorizacao4_endpoint(uf=uf, ambiente=ambiente)

    # 4) cUF
    c_uf = _resolver_cuf(xml_nfe, uf)

    # 5) SOAP
    soap_xml = montar_soap_envelope(
        envi_nfe_xml=xml_envi_nfe,
        c_uf=c_uf,
        versao_dados=versao,
    )

    # 6) Enviar
    resp = enviar_soap_com_pfx(
        endpoint=endpoint,
        soap_xml=soap_xml,
        pfx_path=pfx_path,
        pfx_password=pfx_password,
    )

    # 7) Extrair retorno
    xml_retorno = extrair_xml_resultado(resp.text)

    status, motivo = _obter_status_motivo(xml_retorno)

    return NFeEnvioResult(
        xml_assinado=xml_assinado,
        xml_envi_nfe=xml_envi_nfe,
        xml_retorno=xml_retorno,
        status=status,
        motivo=motivo,
    )
