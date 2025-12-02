from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .enums import Ambiente, Projeto
from .soap_client import SoapClient


@dataclass
class SefazBaseService:
    """
    Base para todos os serviços de comunicação com a SEFAZ.

    - uf: UF ou "AN" (Ambiente Nacional)
    - ambiente: 1 = produção, 2 = homologação
    - versao: versão do serviço (ex.: "4.00" NFe, "1.00" evento)
    - projeto: NFe, CTe, MDFe, etc (apenas informativo por enquanto)
    """
    uf: str
    ambiente: Ambiente
    versao: str
    projeto: Projeto
    soap_client: SoapClient
    soap_url: Optional[str] = None
    soap_action: Optional[str] = None

    def __post_init__(self) -> None:
        self.uf = self.uf.upper()

    @staticmethod
    def build_soap_envelope(body_xml: str) -> str:
        """Monta Envelope SOAP 1.2 com o XML no Body."""
        return f"""<?xml version="1.0" encoding="utf-8"?>
<soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                 xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                 xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
  <soap12:Body>
    {body_xml}
  </soap12:Body>
</soap12:Envelope>"""

    def enviar_soap(self, xml_corpo: str, *, url: Optional[str] = None,
                    action: Optional[str] = None, timeout: int = 30) -> str:
        """
        Envia o XML já no formato de mensagem da SEFAZ
        (enviNFe, envEvento, distDFeInt, etc) dentro de um Envelope SOAP.
        """
        url = url or self.soap_url
        action = action or self.soap_action

        if not url:
            raise ValueError("URL do webservice SOAP não definida.")
        envelope = self.build_soap_envelope(xml_corpo)
        return self.soap_client.post(url=url, action=action or "", xml=envelope, timeout=timeout)
