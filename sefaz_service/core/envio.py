# sefaz_service/core/envio.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

import tempfile

import requests
from lxml import etree

from .assinatura import assinar_nfe_xml, _load_pfx

NFE_NS = "http://www.portalfiscal.inf.br/nfe"
WSDL_NS = "http://www.portalfiscal.inf.br/nfe/wsdl/NFeAutorizacao4"


@dataclass
class EndpointInfo:
    url: str
    soap_action: str


def strip_xml_declaration(xml: str) -> str:
    """
    Remove a declaração XML (<?xml ...?>) se existir.
    Útil para embutir a <NFe> dentro de <enviNFe> ou do SOAP.
    """
    xml = xml.lstrip()
    if xml.startswith("<?xml"):
        end = xml.find("?>")
        if end != -1:
            return xml[end + 2 :].lstrip()
    return xml


def montar_envi_nfe_xml(
    nfe_assinada: str,
    versao: str = "4.00",
    id_lote: str = "1",
    ind_sinc: bool = True,
) -> str:
    """
    Monta o XML <enviNFe> com a NFe assinada dentro.
    nfe_assinada: XML completo da <NFe> assinada (com ou sem declaração).
    """
    nfe_sem_decl = strip_xml_declaration(nfe_assinada)
    ind_sinc_val = "1" if ind_sinc else "0"

    envi = (
        f'<enviNFe versao="{versao}" xmlns="{NFE_NS}">'
        f"<idLote>{id_lote}</idLote>"
        f"<indSinc>{ind_sinc_val}</indSinc>"
        f"{nfe_sem_decl}"
        f"</enviNFe>"
    )
    return envi


def _extrair_cuf_da_nfe(xml_nfe: str) -> str:
    """
    Lê o cUF (código numérico da UF) da tag <ide><cUF> da NFe.
    Retorna, por exemplo, '12' para AC.
    """
    parser = etree.XMLParser(remove_blank_text=True)
    root = etree.fromstring(xml_nfe.encode("utf-8"), parser=parser)

    # Se vier nfeProc, pega a <NFe>
    if root.tag.endswith("nfeProc"):
        ns = {"nfe": NFE_NS}
        nfe_el = root.find("nfe:NFe", ns)
        if nfe_el is None:
            raise ValueError("XML nfeProc sem nó <NFe>")
        root = nfe_el

    ns = {"nfe": NFE_NS}
    ide = root.find("nfe:ide", ns)
    if ide is None:
        raise ValueError("Não encontrado nó <ide> na NFe")

    cuf_el = ide.find("nfe:cUF", ns)
    if cuf_el is None or not (cuf_el.text or "").strip():
        raise ValueError("Não encontrado valor de <cUF> na NFe")

    return cuf_el.text.strip()


def montar_soap_envelope(
    envi_nfe_xml: str,
    c_uf: str,
    versao_dados: str = "4.00",
) -> str:
    """
    Monta o envelope SOAP 1.2 no padrão usado pelo Harbour:

    <soap12:Envelope xmlns:xsi=... xmlns:xsd=... xmlns:soap12=...>
      <soap12:Header>
        <nfeCabecMsg xmlns="...NFeAutorizacao4">
          <cUF>12</cUF>
          <versaoDados>4.00</versaoDados>
        </nfeCabecMsg>
      </soap12:Header>
      <soap12:Body>
        <nfeDadosMsg xmlns="...NFeAutorizacao4">
          {envi_nfe_xml}
        </nfeDadosMsg>
      </soap12:Body>
    </soap12:Envelope>
    """
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<soap12:Envelope
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xmlns:xsd="http://www.w3.org/2001/XMLSchema"
    xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
  <soap12:Header>
    <nfeCabecMsg xmlns="{WSDL_NS}">
      <cUF>{c_uf}</cUF>
      <versaoDados>{versao_dados}</versaoDados>
    </nfeCabecMsg>
  </soap12:Header>
  <soap12:Body>
    <nfeDadosMsg xmlns="{WSDL_NS}">
      {envi_nfe_xml}
    </nfeDadosMsg>
  </soap12:Body>
</soap12:Envelope>"""


def enviar_soap_com_pfx(
    endpoint: EndpointInfo,
    soap_xml: str,
    pfx_path: str,
    pfx_password: str,
    timeout: int = 30,
) -> requests.Response:
    """
    Envia o SOAP 1.2 usando TLS com certificado de cliente extraído do PFX.
    """
    pem_key, pem_cert = _load_pfx(pfx_path, pfx_password)

    # requests espera caminhos de arquivos PEM (cert, key). Criamos temporários.
    with tempfile.NamedTemporaryFile("wb", delete=False) as f_key, tempfile.NamedTemporaryFile(
        "wb", delete=False
    ) as f_cert:
        f_key.write(pem_key)
        f_cert.write(pem_cert)
        f_key.flush()
        f_cert.flush()

        headers = {
            # Igual ao MicrosoftXmlSoapPost do Harbour:
            "Content-Type": "application/soap+xml; charset=utf-8",
            "SOAPAction": endpoint.soap_action,
        }

        resp = requests.post(
            endpoint.url,
            data=soap_xml.encode("utf-8"),
            headers=headers,
            timeout=timeout,
            cert=(f_cert.name, f_key.name),
            verify=False,  # ⚠ manter False enquanto não tiver cadeia da SEFAZ instalada
        )

    resp.raise_for_status()
    return resp


def extrair_xml_resultado(resp_xml: str) -> str:
    """
    A partir do SOAP de resposta, extrai o XML que a SEFAZ retorna
    dentro de <nfeResultMsg><retEnviNFe>...</retEnviNFe></nfeResultMsg>.
    Se não encontrar, devolve o próprio SOAP para inspeção.
    """
    root = etree.fromstring(resp_xml.encode("utf-8"))

    # Procura o elemento nfeResultMsg no namespace do WSDL
    ns = {"ws": WSDL_NS}

    nfe_result = root.find(".//ws:nfeResultMsg", ns)
    if nfe_result is None or len(nfe_result) == 0:
        # Não achou, devolve o SOAP inteiro pra debug
        return resp_xml

    # Normalmente o primeiro filho é o <retEnviNFe> (ou outro XML de retorno)
    payload = nfe_result[0]
    return etree.tostring(payload, encoding="utf-8", xml_declaration=True).decode("utf-8")


def enviar_nfe(
    xml_nfe: str,
    pfx_path: str,
    pfx_password: str,
    endpoint: EndpointInfo,
    *,
    versao: str = "4.00",
    id_lote: str = "1",
    ind_sinc: bool = True,
) -> Tuple[str, str]:
    """
    Fluxo completo:
      1. Assina a <NFe>;
      2. Monta <enviNFe>;
      3. Monta SOAP no padrão SEFAZ/Harbour;
      4. Envia via SOAP 1.2 para o endpoint informado;
      5. Extrai o XML de retorno (<retEnviNFe>...).

    Retorna (xml_enviNFe, xml_retorno).

    - xml_nfe: XML da NFe sem assinatura (pode ter ou não declaração).
    - endpoint: EndpointInfo(url, soap_action) para o serviço NFeAutorizacao4.
    """

    # 1) Assinar NFe (usa o módulo assinatura.py)
    nfe_assinada = assinar_nfe_xml(xml_nfe, pfx_path, pfx_password)

    # 2) Montar <enviNFe>
    envi_nfe_xml = montar_envi_nfe_xml(
        nfe_assinada=nfe_assinada,
        versao=versao,
        id_lote=id_lote,
        ind_sinc=ind_sinc,
    )

    # 3) Extrair cUF da NFe original para o cabeçalho SOAP
    c_uf = _extrair_cuf_da_nfe(xml_nfe)

    # 4) Montar SOAP (igual XmlSoapPost/Harbour)
    soap_xml = montar_soap_envelope(
        envi_nfe_xml=envi_nfe_xml,
        c_uf=c_uf,
        versao_dados=versao,
    )

    # 5) Enviar via HTTPS com certificado
    resp = enviar_soap_com_pfx(endpoint, soap_xml, pfx_path, pfx_password)

    # 6) Extrair XML de retorno
    xml_retorno = extrair_xml_resultado(resp.text)

    return envi_nfe_xml, xml_retorno
