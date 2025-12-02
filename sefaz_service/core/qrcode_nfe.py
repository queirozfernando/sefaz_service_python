# sefaz_service/core/qrcode_nfe.py
from __future__ import annotations

import hashlib
from typing import Optional

from lxml import etree

NFE_NS = "http://www.portalfiscal.inf.br/nfe"
DSIG_NS = "http://www.w3.org/2000/09/xmldsig#"


def _strip_xml_decl(xml: str) -> str:
    xml = xml.lstrip()
    if xml.startswith("<?xml"):
        end = xml.find("?>")
        if end != -1:
            return xml[end + 2 :].lstrip()
    return xml


def _sha1_upper(data: str) -> str:
    return hashlib.sha1(data.encode("utf-8")).hexdigest().upper()


def gerar_qrcode_nfce(
    xml_assinado: str,
    *,
    id_token: str,
    csc: str,
    versao_qrcode: str = "2.00",
    ambiente: str,
    uf: str,
    url_qrcode_base: str,
    url_chave: str,
) -> str:
    """
    Gera a tag <infNFeSupl><qrCode/><urlChave/></infNFeSupl> para NFC-e,
    a partir do XML JÁ ASSINADO da NFe (mod 65).

    Parâmetros:
      - xml_assinado: XML da <NFe> assinada (com ou sem declaração).
      - id_token: Id do CSC (cIdToken) cadastrado na SEFAZ (ex: "000001").
      - csc: Código de Segurança do Contribuinte (CSC) fornecido pela SEFAZ.
      - versao_qrcode: normalmente "2.00" ou "3.00".
      - ambiente: "H", "P", "HOMOLOGACAO", "PRODUCAO", "1", "2"...
      - uf: UF da empresa, ex: "AC", "SP" (aqui é só informativo).
      - url_qrcode_base: URL base da consulta do QRCode (terminando ou não com "?").
      - url_chave: URL da consulta pela chave.

    Retorna:
      XML da <NFe> com o bloco <infNFeSupl> incluído.
    """

    # 1) Parse do XML já assinado (apenas <NFe>...</NFe>)
    xml_sem_decl = _strip_xml_decl(xml_assinado)
    parser = etree.XMLParser(remove_blank_text=True)
    root = etree.fromstring(xml_sem_decl.encode("utf-8"), parser=parser)

    ns = {"nfe": NFE_NS, "ds": DSIG_NS}

    if root.tag != f"{{{NFE_NS}}}NFe":
        raise ValueError("Esperado XML com nó raiz <NFe> para gerar QRCode")

    inf_nfe = root.find("nfe:infNFe", namespaces=ns)
    if inf_nfe is None:
        raise ValueError("Não encontrado nó <infNFe> na NFe")

    # Se já existir infNFeSupl, removemos para recriar
    inf_supl_exist = root.find("nfe:infNFeSupl", namespaces=ns)
    if inf_supl_exist is not None:
        root.remove(inf_supl_exist)

    # 2) Campos básicos para o QRCode
    ide = inf_nfe.find("nfe:ide", namespaces=ns)
    if ide is None:
        raise ValueError("Não encontrado nó <ide> em <infNFe>")

    tp_amb = ide.findtext("nfe:tpAmb", namespaces=ns)
    mod = ide.findtext("nfe:mod", namespaces=ns)
    tp_emis = ide.findtext("nfe:tpEmis", namespaces=ns)
    dh_emi = ide.findtext("nfe:dhEmi", namespaces=ns)

    if mod != "65":
        raise ValueError("gerar_qrcode_nfce: esperado modelo 65 (NFC-e)")

    # chave NFe = atributo Id de infNFe sem o prefixo "NFe"
    inf_id = inf_nfe.get("Id") or ""
    ch_nfe = inf_id[3:] if inf_id.startswith("NFe") else inf_id

    # totais
    icms_tot = inf_nfe.find("nfe:total/nfe:ICMSTot", namespaces=ns)
    v_nf = icms_tot.findtext("nfe:vNF", namespaces=ns) if icms_tot is not None else None
    v_icms = icms_tot.findtext("nfe:vICMS", namespaces=ns) if icms_tot is not None else None

    # DigestValue da assinatura
    signature = root.find("ds:Signature", namespaces=ns)
    if signature is None:
        # tenta localizar por local-name, caso namespace explícito não esteja no root
        signature = root.find(".//*[local-name()='Signature']")
    if signature is None:
        raise ValueError("Não encontrado nó <Signature> para obter DigestValue")

    digest_value_el = signature.find(".//ds:DigestValue", namespaces=ns)
    if digest_value_el is None:
        digest_value_el = signature.find(".//*[local-name()='DigestValue']")
    digest_value = (digest_value_el.text or "").strip()

    if not tp_amb or not ch_nfe or not v_nf or not dh_emi:
        raise ValueError("Dados insuficientes para gerar QRCode (chNFe, tpAmb, vNF, dhEmi, etc.)")

    # Normalizar ambiente
    amb = ambiente.strip().upper()
    if amb in ("H", "HOMOLOGACAO", "HOMOLOGAÇÃO", "2"):
        amb = "2"
    else:
        amb = "1"  # produção

    # Garantir que base termine em "?"
    url_qrcode_base = url_qrcode_base.rstrip()
    if not url_qrcode_base.endswith("?"):
        url_qrcode_base += "?"

    # 3) Montagem do conteúdo do "p=" conforme versão do QRCode
    p_param = ""

    if versao_qrcode == "3.00":
        # Versão 3.00 (simplificada para tpEmis != 9)
        # p = chNFe|nVersao|tpAmb
        n_versao = "3"
        p_param = f"{ch_nfe}|{n_versao}|{amb}"
        # (para tpEmis = 9, tem regras extras com hash; podemos portar depois)
    elif versao_qrcode == "2.00":
        # Versão 2.00 (mais usada atualmente)
        # Cenário normal: tpEmis != 9
        #
        # Especificação:
        #   p = chNFe|nVersao|tpAmb|cIdToken|cHashQRCode
        #
        # cHashQRCode = SHA1(chNFe|nVersao|tpAmb|cIdToken|CSC)
        n_versao = "2"
        c_id_token_num = str(int(id_token))  # o LTrim(Str(Val(..),16,0)) vira um número simples

        base_for_hash = f"{ch_nfe}|{n_versao}|{amb}|{c_id_token_num}|{csc}"
        c_hash_qrcode = _sha1_upper(base_for_hash)

        p_param = f"{ch_nfe}|{n_versao}|{amb}|{c_id_token_num}|{c_hash_qrcode}"
    else:
        raise ValueError(f"Versão de QRCode não suportada: {versao_qrcode}")

    # 4) Montar a URL final do QRCode
    qrcode_url = f"{url_qrcode_base}p={p_param}"

    # 5) Criar <infNFeSupl> com <qrCode> e <urlChave>
    inf_supl = etree.Element(f"{{{NFE_NS}}}infNFeSupl")

    qr_el = etree.SubElement(inf_supl, f"{{{NFE_NS}}}qrCode")
    # Mantemos o conteúdo do QRCode em CDATA
    qr_el.text = etree.CDATA(qrcode_url)

    url_chave_el = etree.SubElement(inf_supl, f"{{{NFE_NS}}}urlChave")
    url_chave_el.text = url_chave

    # Inserir infNFeSupl antes da Signature (como no código Harbour)
    # Se não achar Signature, apenas append no final.
    children = list(root)
    try:
        sig_index = children.index(signature)
        root.insert(sig_index, inf_supl)
    except ValueError:
        root.append(inf_supl)

    # 6) Serializar novamente com a mesma declaração XML padrão
    xml_final_sem_decl = etree.tostring(
        root, encoding="utf-8", xml_declaration=False
    ).decode("utf-8")

    xml_final_sem_decl = xml_final_sem_decl.lstrip()
    declaracao = '<?xml version="1.0" encoding="UTF-8"?>'

    return declaracao + xml_final_sem_decl
