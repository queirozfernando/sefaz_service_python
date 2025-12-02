from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

# 🔁 IMPORTS RELATIVOS (sobe para sefaz_service/core)
from ...core.enums import Ambiente
from ...core.soap_client import SoapClient
from ...core.xml_utils import xml_tag

from .base import NFeEventoBaseService

TIPO_EVENTO_CANCELAMENTO = "110111"


@dataclass
class NFeEventoCancelamentoService(NFeEventoBaseService):
    """
    Serviço para montar o XML de evento de Cancelamento de NFe.
    (Ainda não envia para a SEFAZ – só gera o XML.)
    """

    def __init__(self, uf: str, ambiente: Ambiente, soap_client: SoapClient):
        super().__init__(uf=uf, ambiente=ambiente, soap_client=soap_client)

    def montar_xml(
        self,
        chave: str,
        n_protocolo: int,
        justificativa: str,
        sequencia: int = 1,
        cnpj: Optional[str] = None,
    ) -> str:
        """
        Retorna o XML completo do envEvento de cancelamento.

        - chave: chave de acesso da NFe
        - n_protocolo: protocolo de autorização
        - justificativa: texto da justificativa
        - sequencia: número sequencial do evento (default 1)
        - cnpj: CNPJ/CPF autor do evento (se None, usa emitente da chave)
        """
        det = '<detEvento versao="1.00">'
        det += xml_tag("descEvento", "Cancelamento")
        det += xml_tag("nProt", str(n_protocolo))
        det += xml_tag("xJust", justificativa)
        det += "</detEvento>"

        evento = self.montar_evento(
            chave=chave,
            tipo_evento=TIPO_EVENTO_CANCELAMENTO,
            sequencia=sequencia,
            xml_det_evento=det,
            cnpj=cnpj,
        )
        return self.montar_envio_lote(chave, evento)
