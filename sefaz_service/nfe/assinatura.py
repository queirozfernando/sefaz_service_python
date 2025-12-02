# sefaz_service/nfe/assinatura.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from lxml import etree as ET
import xmlsec

from sefaz_service.core.xml_utils import only_digits

NFE_NS = "http://www.portalfiscal.inf.br/nfe"
DS_NS = "http://www.w3.org/2000/09/xmldsig#"

NSMAP = {
    "nfe": NFE_NS,
    "ds": DS_NS,
}


@dataclass
class NFeXmlSigner:
    """
    Assinador de XML para NFe / NFC-e (infNFe e infEvento).

    - Usa certificado PFX (A1).
    - Usa xmlsec para gerar a assinatura XML-DSig.
    """

    pfx_path: str
    pfx_password: str

    def _load_pfx_key(self) -> xmlsec.Key:
        """
        Carrega a chave a partir do arquivo PFX.
        """
        with open(self.pfx_path, "rb") as f:
            pfx_data = f.read()

        key = xmlsec.Key.from_memory(
            pfx_data,
            xmlsec.KeyFormat.PKCS12,
            self.pfx_password,
        )
        return key

    @staticmethod
    def _remove_previous_signatures(root: ET._Element) -> None:
        """
        Remove tags <Signature> antigas, se existirem.
        Equivalente ao AssinaRemoveAssinatura() do Harbour.
        """
        for sig in root.xpath("//ds:Signature", namespaces=NSMAP):
            parent = sig.getparent()
            if parent is not None:
                parent.remove(sig)

    def _sign(
        self,
        xml: str,
        referencia_xpath: str,
        id_atributo: str = "Id",
        digest_method=xmlsec.Transform.SHA1,
        sign_method=xmlsec.Transform.RSA_SHA1,
    ) -> str:
        """
        Assina um nó específico identificado por um XPath (ex: //nfe:infNFe).

        - referencia_xpath: XPath do nó a ser assinado (ex.: //nfe:infNFe[1])
        - id_atributo: normalmente 'Id', que já vem no XML (Id="NFe...")
        """
        parser = ET.XMLParser(remove_blank_text=False)
        root = ET.fromstring(xml.encode("utf-8"), parser=parser)

        # Remove assinaturas antigas
        self._remove_previous_signatures(root)

        # Localiza o nó a ser assinado (infNFe, infEvento, etc.)
        nodes = root.xpath(referencia_xpath, namespaces=NSMAP)
        if not nodes:
            raise ValueError(
                f"Nó a ser assinado não encontrado para XPath: {referencia_xpath}"
            )

        node_to_sign = nodes[0]

        node_id = node_to_sign.get(id_atributo)
        if not node_id:
            raise ValueError(
                f"Nó a ser assinado não possui atributo {id_atributo}"
            )

        # A assinatura deve ser filha do elemento pai (ex.: <NFe> ... <Signature /> </NFe>)
        parent = node_to_sign.getparent()
        if parent is None:
            raise ValueError("Nó a ser assinado não possui pai no XML (estrutura inválida).")

        # Cria template de assinatura <Signature>...</Signature>
        sign_node = xmlsec.template.create(
            root,
            xmlsec.Transform.EXCL_C14N,
            sign_method,
            ns="ds",
        )

        # Referência ao nó com Id (URI="#Id...")
        ref = xmlsec.template.add_reference(
            sign_node,
            digest_method,
            uri=f"#{node_id}",
        )

        # Transforms: enveloped + c14n
        xmlsec.template.add_transform(ref, xmlsec.Transform.ENVELOPED)
        xmlsec.template.add_transform(ref, xmlsec.Transform.EXCL_C14N)

        # KeyInfo com X509Data (certificado)
        ki = xmlsec.template.ensure_key_info(sign_node)
        xmlsec.template.add_x509_data(ki)

        # Anexa a assinatura ao XML
        parent.append(sign_node)

        # Contexto de assinatura
        key = self._load_pfx_key()
        ctx = xmlsec.SignatureContext()
        ctx.key = key

        # Executa a assinatura
        ctx.sign(sign_node)

        # Retorna XML assinado
        return ET.tostring(
            root,
            encoding="utf-8",
            xml_declaration=False,
        ).decode("utf-8")

    # ------------------------------------------------------------------
    # Assinaturas específicas para NFe
    # ------------------------------------------------------------------

    def assinar_inf_nfe(self, xml: str) -> str:
        """
        Assina o bloco <infNFe>... da NFe.

        Espera algo como:
        <NFe xmlns="http://www.portalfiscal.inf.br/nfe">
            <infNFe Id="NFe3514..." versao="4.00">
                ...
            </infNFe>
        </NFe>
        """
        return self._sign(
            xml=xml,
            referencia_xpath="//nfe:infNFe[1]",
            id_atributo="Id",
            digest_method=xmlsec.Transform.SHA1,
            sign_method=xmlsec.Transform.RSA_SHA1,
        )

    def assinar_inf_evento(self, xml: str) -> str:
        """
        Assina o bloco <infEvento>... de um EVENTO de NFe.

        Espera algo como:
        <evento versao="1.00" xmlns="http://www.portalfiscal.inf.br/nfe">
            <infEvento Id="ID1101113514...01">
                ...
            </infEvento>
        </evento>
        """
        return self._sign(
            xml=xml,
            referencia_xpath="//nfe:infEvento[1]",
            id_atributo="Id",
            digest_method=xmlsec.Transform.SHA1,
            sign_method=xmlsec.Transform.RSA_SHA1,
        )
