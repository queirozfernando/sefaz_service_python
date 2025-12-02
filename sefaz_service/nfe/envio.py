# sefaz_service/nfe/envio.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from sefaz_service.core.base_service import SefazBaseService
from sefaz_service.core.enums import Ambiente, Projeto
from sefaz_service.core.soap_client import SoapClient
from sefaz_service.core.xml_utils import xml_tag, only_digits

NFE_NS = "http://www.portalfiscal.inf.br/nfe"


# ---------------------------------------------------------------------------
# Tabela de endpoints de AUTORIZAÇÃO (equivalente ao SoapList() do Harbour)
# Código:
#   "4.00H"  -> NFe, Homologação
#   "4.00P"  -> NFe, Produção
#   "4.00HC" -> NFC-e, Homologação
#   "4.00PC" -> NFC-e, Produção
# ---------------------------------------------------------------------------
AUTORIZACAO_URLS: list[tuple[str, str, str, str]] = [
    # --- Homologação NFe (4.00H) ---
    ("AM", "4.00H", "https://homnfe.sefaz.am.gov.br/services2/services/NfeAutorizacao4",
     "http://www.portalfiscal.inf.br/nfe/wsdl/NFeAutorizacao4/nfeAutorizacaoLote"),
    ("BA", "4.00H", "https://hnfe.sefaz.ba.gov.br/webservices/NFeAutorizacao4/NFeAutorizacao4.asmx",
     "http://www.portalfiscal.inf.br/nfe/wsdl/NFeAutorizacao4/nfeAutorizacaoLote"),
    ("CE", "4.00H", "https://nfeh.sefaz.ce.gov.br/nfe4/services/NFeAutorizacao4",
     "http://www.portalfiscal.inf.br/nfe/wsdl/NFeAutorizacao4/nfeAutorizacaoLote"),
    ("GO", "4.00H", "https://homolog.sefaz.go.gov.br/nfe/services/NFeAutorizacao4",
     "http://www.portalfiscal.inf.br/nfe/wsdl/NFeAutorizacao4/nfeAutorizacaoLote"),
    ("MG", "4.00H", "https://hnfe.fazenda.mg.gov.br/nfe2/services/NFeAutorizacao4",
     "http://www.portalfiscal.inf.br/nfe/wsdl/NFeAutorizacao4/nfeAutorizacaoLote"),
    ("MS", "4.00H", "https://hom.nfe.sefaz.ms.gov.br/ws/NFeAutorizacao4",
     "http://www.portalfiscal.inf.br/nfe/wsdl/NFeAutorizacao4/nfeAutorizacaoLote"),
    ("MT", "4.00H", "https://homologacao.sefaz.mt.gov.br/nfews/v2/services/NfeAutorizacao4",
     "http://www.portalfiscal.inf.br/nfe/wsdl/NFeAutorizacao4/nfeAutorizacaoLote"),
    ("PE", "4.00H", "https://nfehomolog.sefaz.pe.gov.br/nfe-service/services/NFeAutorizacao4",
     "http://www.portalfiscal.inf.br/nfe/wsdl/NFeAutorizacao4/nfeAutorizacaoLote"),
    ("PR", "4.00H", "https://homologacao.nfe.sefa.pr.gov.br/nfe/NFeAutorizacao4",
     "http://www.portalfiscal.inf.br/nfe/wsdl/NFeAutorizacao4/nfeAutorizacaoLote"),
    ("RS", "4.00H", "https://nfe-homologacao.sefazrs.rs.gov.br/ws/NfeAutorizacao/NFeAutorizacao4.asmx",
     "http://www.portalfiscal.inf.br/nfe/wsdl/NFeAutorizacao4/nfeAutorizacaoLote"),
    ("SP", "4.00H", "https://homologacao.nfe.fazenda.sp.gov.br/ws/nfeautorizacao4.asmx",
     "http://www.portalfiscal.inf.br/nfe/wsdl/NFeAutorizacao4/nfeAutorizacaoLote"),
    ("SVAN", "4.00H", "https://hom.sefazvirtual.fazenda.gov.br/NFeAutorizacao4/NFeAutorizacao4.asmx",
     "http://www.portalfiscal.inf.br/nfe/wsdl/NFeAutorizacao4/nfeAutorizacaoLote"),
    ("SVCAN", "4.00H", "https://hom.svc.fazenda.gov.br/NFeAutorizacao4/NFeAutorizacao4.asmx",
     "http://www.portalfiscal.inf.br/nfe/wsdl/NFeAutorizacao4/nfeAutorizacaoLote"),
    ("SVCRS", "4.00H", "https://nfe-homologacao.svrs.rs.gov.br/ws/NfeAutorizacao/NFeAutorizacao4.asmx",
     "http://www.portalfiscal.inf.br/nfe/wsdl/NFeAutorizacao4/nfeAutorizacaoLote"),
    ("SVRS", "4.00H", "https://nfe-homologacao.svrs.rs.gov.br/ws/NfeAutorizacao/NFeAutorizacao4.asmx",
     "http://www.portalfiscal.inf.br/nfe/wsdl/NFeAutorizacao4/nfeAutorizacaoLote"),

    # --- Homologação NFC-e (4.00HC) ---
    ("AM", "4.00HC", "https://homnfe.sefaz.am.gov.br/services2/services/NfeAutorizacao4",
     "http://www.portalfiscal.inf.br/nfe/wsdl/NFeAutorizacao4/nfeAutorizacaoLote"),
    ("AM", "4.00HC", "https://homnfce.sefaz.am.gov.br/nfce-services/services/NfeAutorizacao4",
     "http://www.portalfiscal.inf.br/nfe/wsdl/NFeAutorizacao4/nfeAutorizacaoLote"),
    ("GO", "4.00HC", "https://homolog.sefaz.go.gov.br/nfe/services/NFeAutorizacao4",
     "http://www.portalfiscal.inf.br/nfe/wsdl/NFeAutorizacao4/nfeAutorizacaoLote"),
    ("MS", "4.00HC", "https://hom.nfce.sefaz.ms.gov.br/ws/NFeAutorizacao4",
     "http://www.portalfiscal.inf.br/nfe/wsdl/NFeAutorizacao4/nfeAutorizacaoLote"),
    ("MT", "4.00HC", "https://homologacao.sefaz.mt.gov.br/nfcews/services/NfeAutorizacao4",
     "http://www.portalfiscal.inf.br/nfe/wsdl/NFeAutorizacao4/nfeAutorizacaoLote"),
    ("PR", "4.00HC", "https://homologacao.nfce.sefa.pr.gov.br/nfce/NFeAutorizacao4",
     "http://www.portalfiscal.inf.br/nfe/wsdl/NFeAutorizacao4/nfeAutorizacaoLote"),
    ("RS", "4.00HC", "https://nfce-homologacao.sefazrs.rs.gov.br/ws/NfeAutorizacao/NFeAutorizacao4.asmx",
     "http://www.portalfiscal.inf.br/nfe/wsdl/NFeAutorizacao4/nfeAutorizacaoLote"),
    ("SP", "4.00HC", "https://homologacao.nfce.fazenda.sp.gov.br/ws/NFeAutorizacao4.asmx",
     "http://www.portalfiscal.inf.br/nfe/wsdl/NFeAutorizacao4/nfeAutorizacaoLote"),
    ("SVRS", "4.00HC", "https://nfce-homologacao.svrs.rs.gov.br/ws/NfeAutorizacao/NFeAutorizacao4.asmx",
     "http://www.portalfiscal.inf.br/nfe/wsdl/NFeAutorizacao4/nfeAutorizacaoLote"),

    # --- Produção NFe (4.00P) ---
    ("AM", "4.00P", "https://nfe.sefaz.am.gov.br/services2/services/NfeAutorizacao4",
     "http://www.portalfiscal.inf.br/nfe/wsdl/NFeAutorizacao4/nfeAutorizacaoLote"),
    ("BA", "4.00P", "https://nfe.sefaz.ba.gov.br/webservices/NFeAutorizacao4/NFeAutorizacao4.asmx",
     "http://www.portalfiscal.inf.br/nfe/wsdl/NFeAutorizacao4/nfeAutorizacaoLote"),
    ("GO", "4.00P", "https://nfe.sefaz.go.gov.br/nfe/services/NFeAutorizacao4",
     "http://www.portalfiscal.inf.br/nfe/wsdl/NFeAutorizacao4/nfeAutorizacaoLote"),
    ("MG", "4.00P", "https://nfe.fazenda.mg.gov.br/nfe2/services/NFeAutorizacao4",
     "http://www.portalfiscal.inf.br/nfe/wsdl/NFeAutorizacao4/nfeAutorizacaoLote"),
    ("MS", "4.00P", "https://nfe.sefaz.ms.gov.br/ws/NFeAutorizacao4",
     "http://www.portalfiscal.inf.br/nfe/wsdl/NFeAutorizacao4/nfeAutorizacaoLote"),
    ("MT", "4.00P", "https://nfe.sefaz.mt.gov.br/nfews/v2/services/NfeAutorizacao4",
     "http://www.portalfiscal.inf.br/nfe/wsdl/NFeAutorizacao4/nfeAutorizacaoLote"),
    ("PE", "4.00P", "https://nfe.sefaz.pe.gov.br/nfe-service/services/NFeAutorizacao4",
     "http://www.portalfiscal.inf.br/nfe/wsdl/NFeAutorizacao4/nfeAutorizacaoLote"),
    ("PR", "4.00P", "https://nfe.sefa.pr.gov.br/nfe/NFeAutorizacao4",
     "http://www.portalfiscal.inf.br/nfe/wsdl/NFeAutorizacao4/nfeAutorizacaoLote"),
    ("RS", "4.00P", "https://nfe.sefazrs.rs.gov.br/ws/NfeAutorizacao/NFeAutorizacao4.asmx",
     "http://www.portalfiscal.inf.br/nfe/wsdl/NFeAutorizacao4/nfeAutorizacaoLote"),
    ("SP", "4.00P", "https://nfe.fazenda.sp.gov.br/ws/nfeautorizacao4.asmx",
     "http://www.portalfiscal.inf.br/nfe/wsdl/NFeAutorizacao4/nfeAutorizacaoLote"),
    ("SVAN", "4.00P", "https://www.sefazvirtual.fazenda.gov.br/NFeAutorizacao4/NFeAutorizacao4.asmx",
     "http://www.portalfiscal.inf.br/nfe/wsdl/NFeAutorizacao4/nfeAutorizacaoLote"),
    ("SVCAN", "4.00P", "https://www.svc.fazenda.gov.br/NFeAutorizacao4/NFeAutorizacao4.asmx",
     "http://www.portalfiscal.inf.br/nfe/wsdl/NFeAutorizacao4/nfeAutorizacaoLote"),
    ("SVCRS", "4.00P", "https://nfe.svrs.rs.gov.br/ws/NfeAutorizacao/NFeAutorizacao4.asmx",
     "http://www.portalfiscal.inf.br/nfe/wsdl/NFeAutorizacao4/nfeAutorizacaoLote"),
    ("SVRS", "4.00P", "https://nfe.svrs.rs.gov.br/ws/NfeAutorizacao/NFeAutorizacao4.asmx",
     "http://www.portalfiscal.inf.br/nfe/wsdl/NFeAutorizacao4/nfeAutorizacaoLote"),

    # --- Produção NFC-e (4.00PC) ---
    ("AM", "4.00PC", "https://nfce.sefaz.am.gov.br/nfce-services/services/NfeAutorizacao4",
     "http://www.portalfiscal.inf.br/nfe/wsdl/NFeAutorizacao4/nfeAutorizacaoLote"),
    ("GO", "4.00PC", "https://nfe.sefaz.go.gov.br/nfe/services/NFeAutorizacao4",
     "http://www.portalfiscal.inf.br/nfe/wsdl/NFeAutorizacao4/nfeAutorizacaoLote"),
    ("MG", "4.00PC", "https://nfce.fazenda.mg.gov.br/nfce/services/NfeAutorizacao4",
     "http://www.portalfiscal.inf.br/nfe/wsdl/NFeAutorizacao4/nfeAutorizacaoLote"),
    ("MS", "4.00PC", "https://nfce.sefaz.ms.gov.br/ws/NFeAutorizacao4",
     "http://www.portalfiscal.inf.br/nfe/wsdl/NFeAutorizacao4/nfeAutorizacaoLote"),
    ("MT", "4.00PC", "https://nfce.sefaz.mt.gov.br/nfcews/services/NfeAutorizacao4",
     "http://www.portalfiscal.inf.br/nfe/wsdl/NFeAutorizacao4/nfeAutorizacaoLote"),
    ("PR", "4.00PC", "https://nfce.sefa.pr.gov.br/nfce/NFeAutorizacao4",
     "http://www.portalfiscal.inf.br/nfe/wsdl/NFeAutorizacao4/nfeAutorizacaoLote"),
    ("RS", "4.00PC", "https://nfce.sefazrs.rs.gov.br/ws/NfeAutorizacao/NFeAutorizacao4.asmx",
     "http://www.portalfiscal.inf.br/nfe/wsdl/NFeAutorizacao4/nfeAutorizacaoLote"),
    ("SP", "4.00PC", "https://nfce.fazenda.sp.gov.br/ws/NFeAutorizacao4.asmx",
     "http://www.portalfiscal.inf.br/nfe/wsdl/NFeAutorizacao4/nfeAutorizacaoLote"),
    ("SVRS", "4.00PC", "https://nfce.svrs.rs.gov.br/ws/NfeAutorizacao/NFeAutorizacao4.asmx",
     "http://www.portalfiscal.inf.br/nfe/wsdl/NFeAutorizacao4/nfeAutorizacaoLote"),
]


@dataclass
class NFeEnvioService(SefazBaseService):
    """
    Serviço de envio de NFe/NFC-e (autorização).

    OBS:
    - NÃO assina o XML. Espera receber o XML já assinado
      (e com QRCode no caso de NFC-e).
    """

    def __init__(self, uf: str, ambiente: Ambiente, soap_client: SoapClient):
        super().__init__(
            uf=uf,
            ambiente=ambiente,
            versao="4.00",
            projeto=Projeto.NFE,
            soap_client=soap_client,
        )

    # ------------------------ resolução de endpoint ---------------------

    def _codigo_versao(self, modelo: str) -> str:
        """Retorna 4.00H / 4.00P / 4.00HC / 4.00PC conforme modelo+ambiente."""
        sufixo = "H" if self.ambiente == Ambiente.HOMOLOGACAO else "P"
        if modelo == "65":
            sufixo += "C"
        return f"{self.versao}{sufixo}"

    def _resolver_endpoint(self, modelo: str) -> Tuple[str, str]:
        codigo = self._codigo_versao(modelo)

        # 1ª tentativa: UF direta
        for uf, cod, url, action in AUTORIZACAO_URLS:
            if uf == self.uf and cod == codigo:
                return url, action

        # 2ª tentativa: virtuais (SVRS, SVAN, etc.)
        for uf, cod, url, action in AUTORIZACAO_URLS:
            if uf in ("SVRS", "SVAN", "SVCAN", "SVCRS") and cod == codigo:
                return url, action

        raise ValueError(
            f"Nenhum endpoint encontrado para UF={self.uf}, "
            f"modelo={modelo}, codigo={codigo}"
        )

    # ------------------------ montagem do enviNFe ----------------------

    def montar_envi_nfe(
        self,
        xml_assinado: str,
        modelo: str,
        id_lote: str | int = 1,
        envio_sincrono: bool = True,
    ) -> str:
        """
        Monta o XML <enviNFe> com 1 documento.
        """
        id_lote_str = only_digits(str(id_lote)) or "1"
        ind_sinc = "1" if envio_sincrono else "0"

        xml = f'<enviNFe versao="{self.versao}" xmlns="{NFE_NS}">'
        xml += xml_tag("idLote", id_lote_str)
        xml += xml_tag("indSinc", ind_sinc)
        xml += xml_assinado
        xml += "</enviNFe>"
        return xml

    # ---------------------------- envio --------------------------------

    def enviar(
        self,
        xml_assinado: str,
        modelo: str,
        id_lote: str | int = 1,
        envio_sincrono: bool = True,
    ) -> str:
        """
        Monta o enviNFe e envia via SOAP.
        Retorna o XML de resposta da SEFAZ.
        """
        xml_envio = self.montar_envi_nfe(
            xml_assinado=xml_assinado,
            modelo=modelo,
            id_lote=id_lote,
            envio_sincrono=envio_sincrono,
        )

        url, action = self._resolver_endpoint(modelo)
        resposta = self.soap_client.post_xml(url, xml_envio, action)
        return resposta
