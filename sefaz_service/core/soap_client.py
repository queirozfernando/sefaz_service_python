# sefaz_service/core/soap_client.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
import requests
from requests_pkcs12 import Pkcs12Adapter


@dataclass
class SoapClient:
    """
    Cliente SOAP com suporte a certificado digital PFX.
    - Envia XML para webservices da SEFAZ (NFe, CTe, MDFe, BPe)
    """

    pfx_path: str               # Caminho do arquivo .pfx
    pfx_password: str           # Senha do PFX
    timeout: int = 30           # Timeout padrão

    def _get_session(self) -> requests.Session:
        """
        Cria uma sessão HTTPS configurada com o PFX.
        """
        session = requests.Session()
        session.mount("https://", Pkcs12Adapter(
            pkcs12_filename=self.pfx_path,
            pkcs12_password=self.pfx_password
        ))
        return session

    def post_xml(self, url: str, xml: str, soap_action: Optional[str] = None) -> str:
        """
        Envia XML via POST SOAP para o endpoint informado.
        """

        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "Content-Length": str(len(xml)),
        }

        if soap_action:
            headers["SOAPAction"] = f'"{soap_action}"'

        session = self._get_session()

        response = session.post(
            url=url,
            data=xml.encode("utf-8"),
            headers=headers,
            timeout=self.timeout,
        )

        # erro HTTP?
        response.raise_for_status()

        return response.text

    # alias opcional
    def post(self, url: str, xml: str, soap_action: Optional[str] = None) -> str:
        return self.post_xml(url, xml, soap_action)
