# sefaz_service/core/mdfe_envio.py
from __future__ import annotations

from typing import Literal, Optional

from lxml import etree
import requests_pkcs12

from sefaz_service.core.assinatura import assinar_mdfe_xml
from sefaz_service.core.utils import (
    limpar_xml,
    extrair_chave_mdfe,
    obter_url_mdfe_sinc,
    obter_cuf,
)

MDFE_NS = "http://www.portalfiscal.inf.br/mdfe"


def montar_envelope_soap(xml_assinado: str, uf: str, versao: str) -> str:
    cuf = obter_cuf(uf)
    cabec_ns = "http://www.portalfiscal.inf.br/mdfe/wsdl/MDFeRecepcaoSinc"

    envelope = f"""<?xml version="1.0" encoding="utf-8"?>
<soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                 xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                 xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
  <soap12:Header>
    <mdfeCabecMsg xmlns="{cabec_ns}">
      <cUF>{cuf}</cUF>
      <versaoDados>{versao}</versaoDados>
    </mdfeCabecMsg>
  </soap12:Header>
  <soap12:Body>
    <MDFeRecepcaoSinc xmlns="{cabec_ns}">
      <mdfeDadosMsg>
{xml_assinado}
      </mdfeDadosMsg>
    </MDFeRecepcaoSinc>
  </soap12:Body>
</soap12:Envelope>"""
    return envelope


def extrair_retorno_xml(soap_xml: str) -> str:
    """
    Extrai o nó <retMDFe> de dentro do SOAP.
    """
    try:
        root = etree.fromstring(soap_xml.encode("utf-8"))
        nodes = root.xpath(".//*[local-name()='retMDFe']")
        if not nodes:
            return ""
        node = nodes[0]
        return etree.tostring(node, encoding="utf-8", xml_declaration=False).decode(
            "utf-8"
        )
    except Exception:
        return ""


def sefaz_mdfe_envio(
    xml: str,
    uf: str,
    ambiente: Literal["1", "2"],
    certificado: str,
    senha_certificado: Optional[str] = None,
    versao: str = "3.00",
) -> dict:
    """
    Envia o MDFe em modo síncrono (RecepcaoSinc 3.00).
    xml: MDFe SEM assinatura (apenas <MDFe>...</MDFe>).
    """

    # 1) Limpar XML e Assinar
    xml = limpar_xml(xml)
    xml_assinado = assinar_mdfe_xml(xml, certificado, senha_certificado or "")

    # 👉 remover declaração XML interna, se existir
    xml_assinado_strip = xml_assinado.lstrip()
    if xml_assinado_strip.startswith("<?xml"):
        # corta até depois de "?>"
        _, resto = xml_assinado_strip.split("?>", 1)
        xml_assinado = resto.lstrip()
    else:
        xml_assinado = xml_assinado_strip

    # extrair chave
    chave = extrair_chave_mdfe(xml_assinado)

    # 2) Preparar URL
    url = obter_url_mdfe_sinc(ambiente)

    # 3) Montar SOAP (1.2)
    envelope = montar_envelope_soap(xml_assinado, uf=uf, versao=versao)

    # 4) Enviar (com certificado cliente)
    headers = {
        "Content-Type": 'application/soap+xml; charset=utf-8'
    }

    try:
        resp = requests_pkcs12.post(
            url,
            data=envelope.encode("utf-8"),
            headers=headers,
            pkcs12_filename=certificado,
            pkcs12_password=senha_certificado or "",
            timeout=30,
            verify=False,  # em homologação, pra evitar problema de CA do servidor
        )
    except Exception as e:
        return {
            "status": 0,
            "motivo": f"Erro HTTP: {e}",
            "xml_envio": envelope,           # 👈 agora mostramos o SOAP completo
            "xml_retorno": "",
            "autorizado": False,
            "xml_autorizado": None,
            "xml_protocolo": None,
            "chave": chave,
        }

    # Se não for 200, retornar erro bruto
    if resp.status_code != 200:
        return {
            "status": resp.status_code,
            "motivo": f"HTTP {resp.status_code}",
            "xml_envio": envelope,           # 👈 idem aqui
            "xml_retorno": resp.text,
            "autorizado": False,
            "xml_autorizado": None,
            "xml_protocolo": None,
            "chave": chave,
        }

    xml_retorno = extrair_retorno_xml(resp.text)

    # Se não conseguiu extrair nada, é erro de SOAP / estrutura
    if not xml_retorno:
        return {
            "status": 0,
            "motivo": "Falha ao interpretar retorno SOAP",
            "xml_envio": envelope,          # 👈 e aqui também
            "xml_retorno": resp.text,
            "autorizado": False,
            "xml_autorizado": None,
            "xml_protocolo": None,
            "chave": chave,
        }

    # 5) Analisar cStat / xMotivo / protMDFe
    try:
        root = etree.fromstring(xml_retorno.encode("utf-8"))

        cStat = root.xpath("string(.//*[local-name()='cStat'])") or "0"
        xMotivo = (root.xpath("string(.//*[local-name()='xMotivo'])") or "").strip()

        prot_nodes = root.xpath(".//*[local-name()='protMDFe']")
        prot_elem = prot_nodes[0] if prot_nodes else None
        xml_protocolo = (
            etree.tostring(prot_elem, encoding="utf-8", xml_declaration=False).decode(
                "utf-8"
            )
            if prot_elem is not None
            else None
        )
    except Exception:
        return {
            "status": 0,
            "motivo": "Não foi possível interpretar o XML de retorno",
            "xml_envio": envelope,
            "xml_retorno": xml_retorno,
            "autorizado": False,
            "xml_autorizado": None,
            "xml_protocolo": None,
            "chave": chave,
        }

    status = int(cStat)
    autorizado = status == 100

    xml_autorizado = None
    if autorizado and xml_protocolo:
        # Montar mdfeProc com MDFe assinado + protMDFe
        try:
            mdfe_root = etree.fromstring(xml_assinado.encode("utf-8"))
            mdfe_puro = etree.tostring(
                mdfe_root, encoding="utf-8", xml_declaration=False
            ).decode("utf-8")
        except Exception:
            mdfe_puro = xml_assinado

        xml_autorizado = (
            f'<?xml version="1.0" encoding="UTF-8"?>'
            f'<mdfeProc xmlns="{MDFE_NS}" versao="{versao}">'
            f"{mdfe_puro}"
            f"{xml_protocolo}"
            f"</mdfeProc>"
        )

    return {
        "status": status,
        "motivo": xMotivo,
        "xml_envio": envelope,          # 👈 mantemos o SOAP como envio
        "xml_retorno": xml_retorno,
        "autorizado": autorizado,
        "xml_autorizado": xml_autorizado,
        "xml_protocolo": xml_protocolo,
        "chave": chave,
    }
