from __future__ import annotations

from dataclasses import dataclass

from .base import NFeEventoBaseService

# 🔴 APAGAR estas linhas:
# from sefaz_service.core.enums import Ambiente
# from sefaz_service.core.soap_client import SoapClient
# from sefaz_service.core.xml_utils import xml_tag, only_digits

# ✅ E COLOCAR ESTAS:
from core.enums import Ambiente
from core.soap_client import SoapClient
from core.xml_utils import xml_tag, only_digits



TIPO_EVENTO_AUTOR = "110150"


@dataclass
class NFeEventoAutorService(NFeEventoBaseService):
    """
    Evento "Ator interessado na NF-e" (110150).
    """

    def __init__(self, uf: str, ambiente: Ambiente, soap_client: SoapClient):
        super().__init__(uf=uf, ambiente=ambiente, soap_client=soap_client)

    def montar_xml(
        self,
        chave: str,
        cnpj_autor: str,
        c_orgao_autor: str,
        tp_autor: str,
        ver_aplic: str,
        cnpj_liberado: str,
        tp_autorizacao: str,
        sequencia: int = 1,
    ) -> str:
        """
        Monta o envEvento do tipo 110150 (autorizar terceiro a baixar XML).

        - cnpj_autor: CNPJ/CPF do autor do evento (emitente/destinatário)
        - c_orgao_autor: código do órgão autorizador (UF/AN)
        - tp_autor: 1=Emitente, 2=Destinatário, 3=Transportador
        - ver_aplic: versão do aplicativo
        - cnpj_liberado: CNPJ/CPF que passará a ter acesso ao XML
        - tp_autorizacao: 0=apenas este, 1=permite autorizar outros
        """
        desc_evento = "Ator interessado na NF-e"

        det = '<detEvento versao="1.00">'
        det += xml_tag("descEvento", desc_evento)
        det += xml_tag("cOrgaoAutor", c_orgao_autor)
        det += xml_tag("tpAutor", tp_autor)
        det += xml_tag("verAplic", ver_aplic)

        det += "<autXML>"
        doc_liberado = only_digits(cnpj_liberado)
        tag_doc = "CPF" if len(doc_liberado) == 11 else "CNPJ"
        det += xml_tag(tag_doc, doc_liberado)
        det += xml_tag("tpAutorizacao", tp_autorizacao)

        if tp_autorizacao == "1":
            det += xml_tag(
                "xCondUso",
                (
                    "O emitente ou destinatario da NF-e, declara que permite o "
                    "transportador declarado no campo CNPJ/CPF deste evento a "
                    "autorizar os transportes subcontratados ou redespachados "
                    "a terem acesso ao download da NF-e"
                ),
            )
        det += "</autXML>"
        det += "</detEvento>"

        evento = self.montar_evento(
            chave=chave,
            tipo_evento=TIPO_EVENTO_AUTOR,
            sequencia=sequencia,
            xml_det_evento=det,
            cnpj=cnpj_autor,
        )
        return self.montar_envio_lote(chave, evento)
