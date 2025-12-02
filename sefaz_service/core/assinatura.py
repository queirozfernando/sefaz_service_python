# sefaz_service/core/assinatura.py
from __future__ import annotations

from pathlib import Path
from typing import Tuple

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.serialization.pkcs12 import (
    load_key_and_certificates,
)
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    PrivateFormat,
    NoEncryption,
)
from lxml import etree
import xmlsec

NFE_NS = "http://www.portalfiscal.inf.br/nfe"


def _load_pfx(pfx_path: str, password: str) -> Tuple[bytes, bytes]:
    """
    Carrega chave privada e certificado a partir de um arquivo .pfx.
    Retorna (pem_key_bytes, pem_cert_bytes).
    """
    data = Path(pfx_path).read_bytes()

    key, cert, extra_certs = load_key_and_certificates(
        data,
        password.encode("utf-8") if password else None,
        backend=default_backend(),
    )
    if key is None or cert is None:
        raise ValueError("Não foi possível carregar chave/certificado do PFX")

    # chave privada em PEM
    pem_key = key.private_bytes(
        encoding=Encoding.PEM,
        format=PrivateFormat.PKCS8,
        encryption_algorithm=NoEncryption(),
    )

    # certificado em PEM
    pem_cert = cert.public_bytes(Encoding.PEM)

    return pem_key, pem_cert


def _limpar_whitespace_subarvore(elem: etree._Element) -> None:
    """
    Remove nós de texto/tail que sejam APENAS whitespace em toda a subárvore.
    Usado ANTES da assinatura, para que o template de Signature não tenha
    \n/\r/\t “decorativos”.
    """
    for node in elem.iter():
        if node.text is not None and node.text.strip() == "":
            node.text = ""
        if node.tail is not None and node.tail.strip() == "":
            node.tail = ""


def assinar_nfe_xml(xml: str, pfx_path: str, pfx_password: str) -> str:
    """
    Assina uma NFe (modelo 55 ou 65) usando o PFX informado.
    Retorna o XML da NFe assinada.
    """

    # 0) Remover caracteres de edição básicos no XML antes de assinar
    xml = xml.replace("\r", "").replace("\t", "").replace("\n", "")
    xml = xml.lstrip("\ufeff")

    # 1) Parse do XML
    parser = etree.XMLParser(remove_blank_text=True)
    root = etree.fromstring(xml.encode("utf-8"), parser=parser)

    # Se vier <nfeProc>, pegar apenas <NFe>
    if root.tag.endswith("nfeProc"):
        ns = {"nfe": NFE_NS}
        nfe_el = root.find("nfe:NFe", ns)
        if nfe_el is None:
            raise ValueError("XML nfeProc sem nó <NFe>")
        root = nfe_el

    # 2) Localizar <infNFe> e Id
    ns = {"nfe": NFE_NS}
    inf = root.find("nfe:infNFe", ns)
    if inf is None:
        raise ValueError("Não encontrado <infNFe>")

    inf_id = inf.get("Id")
    if not inf_id:
        raise ValueError("<infNFe> sem atributo Id")

    # 3) Registrar ID
    xmlsec.tree.add_ids(root, ["Id"])

    # 4) Criar template de assinatura
    signature_node = xmlsec.template.create(
        root,
        xmlsec.Transform.C14N,
        xmlsec.Transform.RSA_SHA1,
    )
    root.append(signature_node)

    # Referência ao infNFe
    ref = xmlsec.template.add_reference(
        signature_node,
        xmlsec.Transform.SHA1,
        uri=f"#{inf_id}",
    )
    xmlsec.template.add_transform(ref, xmlsec.Transform.ENVELOPED)
    xmlsec.template.add_transform(ref, xmlsec.Transform.C14N)

    key_info = xmlsec.template.ensure_key_info(signature_node)
    xmlsec.template.add_x509_data(key_info)

    # 4.1) Antes de assinar, limpa whitespace vazio do template
    _limpar_whitespace_subarvore(signature_node)

    # 5) Carregar chave e certificado
    pem_key, pem_cert = _load_pfx(pfx_path, pfx_password)

    ctx = xmlsec.SignatureContext()
    key = xmlsec.Key.from_memory(pem_key, xmlsec.KeyFormat.PEM, None)
    key.load_cert_from_memory(pem_cert, xmlsec.KeyFormat.PEM)
    ctx.key = key

    # 6) Assinar
    ctx.sign(signature_node)

    # 7) Após assinar: limpar apenas SignatureValue e X509Data/X509Certificate
    dsig_ns = "http://www.w3.org/2000/09/xmldsig#"
    signature_el = root.find(f".//{{{dsig_ns}}}Signature")

    if signature_el is not None:
        # 7.1) SignatureValue em uma linha só, sem espaços
        sigval_el = signature_el.find(f".//{{{dsig_ns}}}SignatureValue")
        if sigval_el is not None:
            texto = "".join(sigval_el.itertext())
            texto = "".join(texto.split())  # remove \n, \r, \t, espaços
            sigval_el.text = texto
            if sigval_el.tail is not None and sigval_el.tail.strip() == "":
                sigval_el.tail = ""

        # 7.2) Tratar X509Data e X509Certificate
        x509data_el = signature_el.find(f".//{{{dsig_ns}}}X509Data")
        if x509data_el is not None:
            # remover texto interno de X509Data que seja só \n/espaco
            if x509data_el.text is not None and x509data_el.text.strip() == "":
                x509data_el.text = ""
            if x509data_el.tail is not None and x509data_el.tail.strip() == "":
                x509data_el.tail = ""

            # todos os certificados em uma linha só e sem tail
            for cert_el in x509data_el.findall(f".//{{{dsig_ns}}}X509Certificate"):
                if cert_el.text:
                    texto = "".join(cert_el.itertext())
                    texto = "".join(texto.split())
                    cert_el.text = texto
                if cert_el.tail is not None and cert_el.tail.strip() == "":
                    cert_el.tail = ""

    # 8) Serializar — sem pretty_print
    xml_bytes = etree.tostring(
        root,
        encoding="UTF-8",
        xml_declaration=True,
        pretty_print=False,
    )
    xml_str = xml_bytes.decode("utf-8")

    return xml_str
