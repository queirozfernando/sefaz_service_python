from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

# ⚠️ IMPORT RELATIVO (sobe para sefaz_service/core)
from ...core.base_service import SefazBaseService
from ...core.enums import Ambiente, Projeto
from ...core.xml_utils import (
    xml_tag,
    now_sefaz_datetime,
    only_digits,
    dfe_emitente_from_chave,
)

NFE_EVENTO_NS = "http://www.portalfiscal.inf.br/nfe"
EVENTO_VERSAO = "1.00"


@dataclass
class NFeEventoBaseService(SefazBaseService):
    """
    Base para qualquer EVENTO de NFe (cancelamento, autor, carta, etc).
    Responsável por montar <evento> e <envEvento>.
    """

    def __init__(self, uf: str, ambiente: Ambiente, soap_client):
        super().__init__(
            uf=uf,
            ambiente=ambiente,
            versao="4.00",          # versão da NFe (evento continua 1.00)
            projeto=Projeto.NFE,
            soap_client=soap_client,
        )

    def montar_evento(
        self,
        chave: str,
        tipo_evento: str,
        sequencia: int,
        xml_det_evento: str,
        cnpj: Optional[str] = None,
    ) -> str:
        """
        Monta o XML <evento>...</evento> (sem o envEvento).
        Equivalente ao ze_sefaz_NFeEvento na parte de construção do XML.
        """
        chave = only_digits(chave)
        if len(chave) != 44:
            raise ValueError("Chave de acesso deve ter 44 dígitos")

        if not cnpj:
            cnpj = dfe_emitente_from_chave(chave)

        cnpj_num = only_digits(cnpj)
        tag_cnpj = "CPF" if len(cnpj_num) == 11 else "CNPJ"

        c_orgao = "91" if self.uf == "AN" else chave[:2]
        id_evento = f"ID{tipo_evento}{chave}{sequencia:02d}"

        xml = f'<evento versao="{EVENTO_VERSAO}" xmlns="{NFE_EVENTO_NS}">'
        xml += f'<infEvento Id="{id_evento}">'
        xml += xml_tag("cOrgao", c_orgao)
        xml += xml_tag("tpAmb", self.ambiente.value)
        xml += xml_tag(tag_cnpj, cnpj_num)
        xml += xml_tag("chNFe", chave)
        xml += xml_tag("dhEvento", now_sefaz_datetime())
        xml += xml_tag("tpEvento", tipo_evento)
        xml += xml_tag("nSeqEvento", str(sequencia))
        xml += xml_tag("verEvento", EVENTO_VERSAO)
        xml += xml_det_evento
        xml += "</infEvento></evento>"
        return xml

    @staticmethod
    def _id_lote_from_chave(chave: str) -> str:
        """
        Usa o número da NF (pos 26-34 da chave) como idLote.
        """
        chave = only_digits(chave)
        if len(chave) != 44:
            raise ValueError("Chave de acesso deve ter 44 dígitos")
        numero = chave[25:34]
        return str(int(numero))  # remove zeros à esquerda

    def montar_envio_lote(self, chave: str, evento_xml: str) -> str:
        """
        Monta o <envEvento>...<evento>...</evento>...</envEvento>.
        """
        id_lote = self._id_lote_from_chave(chave)
        xml = f'<envEvento versao="{EVENTO_VERSAO}" xmlns="{NFE_EVENTO_NS}">'
        xml += xml_tag("idLote", id_lote)
        xml += evento_xml
        xml += "</envEvento>"
        return xml
