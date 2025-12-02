# sefaz_service/core/protocolo.py
from __future__ import annotations

from lxml import etree

from .assinatura import NFE_NS


def montar_nfe_proc(
    xml_assinado: str,
    xml_retorno: str,
    versao: str = "4.00",
) -> str:
    """
    Monta o XML autorizado (nfeProc) a partir de:

      - xml_assinado: XML da NFe já assinada (<NFe>...</NFe>)
      - xml_retorno : XML de retorno da SEFAZ (ex.: <retEnviNFe>...</retEnviNFe>)
                      que contenha <protNFe>.

    Retorna:

      <nfeProc versao="4.00" xmlns="http://www.portalfiscal.inf.br/nfe">
        <NFe>...</NFe>
        <protNFe>...</protNFe>
      </nfeProc>

    Lança ValueError se não encontrar <protNFe>.
    """

    # 1) Parse da NFe assinada (root = <NFe>)
    parser = etree.XMLParser(remove_blank_text=True)
    nfe_root = etree.fromstring(xml_assinado.encode("utf-8"), parser=parser)

    # 2) Parse do retorno (retEnviNFe, retConsReciNFe, etc.)
    ret_root = etree.fromstring(xml_retorno.encode("utf-8"), parser=parser)

    ns = {"nfe": NFE_NS}

    # Procura <protNFe> em qualquer lugar do retorno
    prot_el = ret_root.find(".//nfe:protNFe", ns)
    if prot_el is None:
        raise ValueError("XML de retorno não contém <protNFe>.")

    # Faz uma cópia profunda do protNFe para não "arrancar" ele do retorno
    prot_el = etree.fromstring(etree.tostring(prot_el, encoding="utf-8"))

    # 3) Monta o nfeProc
    nsmap = {None: NFE_NS}
    nfe_proc = etree.Element(f"{{{NFE_NS}}}nfeProc", nsmap=nsmap)
    nfe_proc.set("versao", versao)

    # Adiciona NFe e protNFe
    nfe_proc.append(nfe_root)
    nfe_proc.append(prot_el)

    # 4) Serializa
    xml_bytes = etree.tostring(
        nfe_proc,
        encoding="UTF-8",
        xml_declaration=True,
        pretty_print=False,
    )
    return xml_bytes.decode("utf-8")
