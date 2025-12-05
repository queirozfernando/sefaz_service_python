# sefaz_service/sped/xml_to_doc.py
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Optional

from lxml import etree

NFE_NS = "http://www.portalfiscal.inf.br/nfe"
NSMAP = {"nfe": NFE_NS}


def _get_text(elem: Optional[etree._Element], xpath: str, default: str = "") -> str:
    """
    Helper para pegar texto com XPath relativo, usando o namespace da NFe.
    """
    if elem is None:
        return default
    node = elem.find(xpath, NSMAP)
    if node is not None and node.text:
        return node.text.strip()
    return default


def _to_float(text: str | None) -> float:
    if text is None:
        return 0.0
    text = text.strip()
    if not text:
        return 0.0
    try:
        # NFe sempre usa ponto como separador decimal
        return float(text.replace(",", "."))
    except ValueError:
        return 0.0


# -------------------------------------------------------------------
# DATACLASSES (modelo DocSped simplificado)
# -------------------------------------------------------------------


@dataclass
class Pessoa:
    nome: str = ""
    cnpj_cpf: str = ""
    ie: str = ""
    im: str = ""
    cnae: str = ""
    endereco: str = ""
    numero: str = ""
    complemento: str = ""
    bairro: str = ""
    cidade: str = ""
    cidade_ibge: str = ""
    uf: str = ""
    cep: str = ""
    pais: str = ""
    telefone: str = ""


@dataclass
class Produto:
    codigo: str = ""
    nome: str = ""
    cfop: str = ""
    ncm: str = ""
    gtin: str = ""
    gtin_trib: str = ""
    cest: str = ""
    unidade: str = ""
    unid_trib: str = ""
    quantidade: float = 0.0
    quantidade_trib: float = 0.0
    valor_unitario: float = 0.0
    valor_unit_trib: float = 0.0
    valor_total: float = 0.0
    desconto: float = 0.0
    inf_adicional: str = ""


@dataclass
class Totais:
    icm_base: float = 0.0
    icm_valor: float = 0.0
    sub_base: float = 0.0
    sub_valor: float = 0.0
    mon_base: float = 0.0
    mon_valor: float = 0.0
    ipi_valor: float = 0.0
    ii_valor: float = 0.0
    iss_valor: float = 0.0
    pis_valor: float = 0.0
    cofins_valor: float = 0.0
    valor_produtos: float = 0.0
    valor_seguro: float = 0.0
    valor_frete: float = 0.0
    valor_desconto: float = 0.0
    valor_outros: float = 0.0
    valor_nota: float = 0.0
    valor_tributos: float = 0.0


@dataclass
class Pagamento:
    tipo_pagamento: str = ""
    valor_pagamento: float = 0.0
    integracao: str = ""
    cnpj_operadora: str = ""
    bandeira: str = ""
    autorizacao: str = ""


@dataclass
class Duplicata:
    fatura: str = ""
    numero: str = ""
    vencimento: str = ""
    valor: float = 0.0


@dataclass
class DocSped:
    # Cabeçalho
    chave: str = ""
    mod_fis: str = ""
    tipo_nfe: str = ""
    tipo_emissao: str = ""
    evento: str = ""  # p/ futuro (110100, 110111 etc.)
    protocolo: str = ""
    numero: str = ""
    serie: str = ""
    data_emissao: Optional[str] = None  # ISO
    data_saida: Optional[str] = None    # ISO
    ambiente: str = ""
    natureza_operacao: str = ""

    # Participantes
    emitente: Pessoa = field(default_factory=Pessoa)
    destinatario: Pessoa = field(default_factory=Pessoa)

    # Detalhes
    produtos: List[Produto] = field(default_factory=list)
    totais: Totais = field(default_factory=Totais)
    pagamentos: List[Pagamento] = field(default_factory=list)
    duplicatas: List[Duplicata] = field(default_factory=list)

    # Outros
    inf_adicionais: str = ""
    assinatura: str = ""
    status: str = ""
    erro: str = ""


# -------------------------------------------------------------------
# FUNÇÃO PRINCIPAL: XML → DocSped
# -------------------------------------------------------------------


def xml_to_doc(xml_input: str) -> DocSped:
    """
    Converte XML de NFe em DocSped.
    Suporta:
      - <nfeProc> (XML de NFe processada)
      - <NFe>
      - <infNFe>
    Se não for NFe, levanta ValueError por enquanto.
    """
    if not xml_input or not xml_input.strip():
        raise ValueError("XML vazio")

    try:
        root = etree.fromstring(xml_input.encode("utf-8"))
    except Exception as exc:
        raise ValueError(f"XML inválido: {exc}") from exc

    tag = etree.QName(root.tag).localname

    # Localizar infNFe dependendo do root
    if tag == "nfeProc":
        inf_nfe = root.find(".//nfe:infNFe", NSMAP)
    elif tag == "NFe":
        inf_nfe = root.find("nfe:infNFe", NSMAP)
        if inf_nfe is None:
            # alguns layouts tem infNFe direto como filho com tag local
            inf_nfe = root.find(".//nfe:infNFe", NSMAP)
    elif tag == "infNFe":
        inf_nfe = root
    else:
        raise ValueError("Por enquanto só é suportado XML de NFe (nfeProc / NFe / infNFe).")

    if inf_nfe is None:
        raise ValueError("Tag <infNFe> não encontrada no XML.")

    doc = DocSped()

    # ------------------ Cabeçalho / Ide ------------------
    # Chave (Id da infNFe)
    id_attr = inf_nfe.get("Id") or inf_nfe.get("id")
    if id_attr:
        if id_attr.upper().startswith("NFE"):
            doc.chave = id_attr[3:]
        else:
            doc.chave = id_attr

    ide = inf_nfe.find("nfe:ide", NSMAP)
    if ide is not None:
        doc.numero = _get_text(ide, "nfe:nNF")
        doc.serie = _get_text(ide, "nfe:serie")
        doc.tipo_nfe = _get_text(ide, "nfe:tpNF")
        doc.tipo_emissao = _get_text(ide, "nfe:tpEmis")
        doc.natureza_operacao = _get_text(ide, "nfe:natOp")
        doc.ambiente = _get_text(ide, "nfe:tpAmb")

        dh_emi = _get_text(ide, "nfe:dhEmi")
        d_emi = _get_text(ide, "nfe:dEmi")
        dh_sai = _get_text(ide, "nfe:dhSaiEnt")
        d_sai = _get_text(ide, "nfe:dSaiEnt")

        def _parse_date(dt: str) -> Optional[str]:
            if not dt:
                return None
            # tenta ISO direto (2024-01-01T12:00:00-03:00)
            try:
                return datetime.fromisoformat(dt.replace("Z", "+00:00")).isoformat()
            except Exception:
                # tenta AAAA-MM-DD
                try:
                    return datetime.strptime(dt[:10], "%Y-%m-%d").date().isoformat()
                except Exception:
                    return None

        doc.data_emissao = _parse_date(dh_emi or d_emi)
        doc.data_saida = _parse_date(dh_sai or d_sai) or doc.data_emissao

    # Modelo fiscal vem dos 2 dígitos da chave ou da tag mod
    if doc.chave and len(doc.chave) == 44:
        doc.mod_fis = doc.chave[20:22]
        if not doc.serie:
            doc.serie = doc.chave[22:25]

    if not doc.mod_fis and ide is not None:
        doc.mod_fis = _get_text(ide, "nfe:mod")

    # ------------------ Emitente ------------------
    emit = inf_nfe.find("nfe:emit", NSMAP)
    if emit is not None:
        ender_emit = emit.find("nfe:enderEmit", NSMAP)
        doc.emitente = Pessoa(
            nome=_get_text(emit, "nfe:xNome"),
            cnpj_cpf=_get_text(emit, "nfe:CNPJ") or _get_text(emit, "nfe:CPF"),
            ie=_get_text(emit, "nfe:IE"),
            im=_get_text(emit, "nfe:IM"),
            cnae=_get_text(emit, "nfe:CNAE"),
            endereco=_get_text(ender_emit, "nfe:xLgr"),
            numero=_get_text(ender_emit, "nfe:nro"),
            complemento=_get_text(ender_emit, "nfe:xCpl"),
            bairro=_get_text(ender_emit, "nfe:xBairro"),
            cidade=_get_text(ender_emit, "nfe:xMun"),
            cidade_ibge=_get_text(ender_emit, "nfe:cMun"),
            uf=_get_text(ender_emit, "nfe:UF"),
            cep=_get_text(ender_emit, "nfe:CEP"),
            pais=_get_text(ender_emit, "nfe:xPais"),
            telefone=_get_text(ender_emit, "nfe:fone"),
        )

    # ------------------ Destinatário ------------------
    dest = inf_nfe.find("nfe:dest", NSMAP)
    if dest is not None:
        ender_dest = dest.find("nfe:enderDest", NSMAP)
        doc.destinatario = Pessoa(
            nome=_get_text(dest, "nfe:xNome"),
            cnpj_cpf=_get_text(dest, "nfe:CNPJ") or _get_text(dest, "nfe:CPF"),
            ie=_get_text(dest, "nfe:IE"),
            endereco=_get_text(ender_dest, "nfe:xLgr"),
            numero=_get_text(ender_dest, "nfe:nro"),
            complemento=_get_text(ender_dest, "nfe:xCpl"),
            bairro=_get_text(ender_dest, "nfe:xBairro"),
            cidade=_get_text(ender_dest, "nfe:xMun"),
            cidade_ibge=_get_text(ender_dest, "nfe:cMun"),
            uf=_get_text(ender_dest, "nfe:UF"),
            cep=_get_text(ender_dest, "nfe:CEP"),
            pais=_get_text(ender_dest, "nfe:xPais"),
            telefone=_get_text(ender_dest, "nfe:fone"),
        )

    # ------------------ InfAdicionais ------------------
    inf_adic = inf_nfe.find("nfe:infAdic", NSMAP)
    if inf_adic is not None:
        doc.inf_adicionais = _get_text(inf_adic, "nfe:infCpl")

    # ------------------ Totais ------------------
    total = inf_nfe.find("nfe:total", NSMAP)
    if total is not None:
        icms_tot = total.find("nfe:ICMSTot", NSMAP)
        if icms_tot is not None:
            doc.totais = Totais(
                icm_base=_to_float(_get_text(icms_tot, "nfe:vBC")),
                icm_valor=_to_float(_get_text(icms_tot, "nfe:vICMS")),
                sub_base=_to_float(_get_text(icms_tot, "nfe:vBCST")),
                sub_valor=_to_float(_get_text(icms_tot, "nfe:vST")),
                ipi_valor=_to_float(_get_text(icms_tot, "nfe:vIPI")),
                ii_valor=_to_float(_get_text(icms_tot, "nfe:vII")),
                pis_valor=_to_float(_get_text(icms_tot, "nfe:vPIS")),
                cofins_valor=_to_float(_get_text(icms_tot, "nfe:vCOFINS")),
                valor_produtos=_to_float(_get_text(icms_tot, "nfe:vProd")),
                valor_seguro=_to_float(_get_text(icms_tot, "nfe:vSeg")),
                valor_frete=_to_float(_get_text(icms_tot, "nfe:vFrete")),
                valor_desconto=_to_float(_get_text(icms_tot, "nfe:vDesc")),
                valor_outros=_to_float(_get_text(icms_tot, "nfe:vOutro")),
                valor_nota=_to_float(_get_text(icms_tot, "nfe:vNF")),
                valor_tributos=_to_float(_get_text(icms_tot, "nfe:vTotTrib")),
            )

    # ------------------ Produtos ------------------
    for det in inf_nfe.findall("nfe:det", NSMAP):
        prod = det.find("nfe:prod", NSMAP)
        if prod is None:
            continue

        p = Produto(
            codigo=_get_text(prod, "nfe:cProd"),
            nome=_get_text(prod, "nfe:xProd"),
            cfop=_get_text(prod, "nfe:CFOP"),
            ncm=_get_text(prod, "nfe:NCM"),
            gtin=_get_text(prod, "nfe:cEAN"),
            gtin_trib=_get_text(prod, "nfe:cEANTrib"),
            cest=_get_text(prod, "nfe:CEST"),
            unidade=_get_text(prod, "nfe:uCom"),
            unid_trib=_get_text(prod, "nfe:uTrib"),
            quantidade=_to_float(_get_text(prod, "nfe:qCom")),
            quantidade_trib=_to_float(_get_text(prod, "nfe:qTrib")),
            valor_unitario=_to_float(_get_text(prod, "nfe:vUnCom")),
            valor_unit_trib=_to_float(_get_text(prod, "nfe:vUnTrib")),
            valor_total=_to_float(_get_text(prod, "nfe:vProd")),
            desconto=_to_float(_get_text(prod, "nfe:vDesc")),
        )

        # infAdProd
        inf_ad_prod = det.find("nfe:infAdProd", NSMAP)
        if inf_ad_prod is not None and inf_ad_prod.text:
            p.inf_adicional = inf_ad_prod.text.strip()

        doc.produtos.append(p)

    # ------------------ Duplicatas ------------------
    cobr = inf_nfe.find("nfe:cobr", NSMAP)
    if cobr is not None:
        n_fat = _get_text(cobr, "nfe:fat/nfe:nFat")
        for dup in cobr.findall("nfe:dup", NSMAP):
            d = Duplicata(
                fatura=n_fat,
                numero=_get_text(dup, "nfe:nDup"),
                vencimento=_get_text(dup, "nfe:dVenc"),
                valor=_to_float(_get_text(dup, "nfe:vDup")),
            )
            doc.duplicatas.append(d)

    # ------------------ Pagamentos ------------------
    for pag in inf_nfe.findall("nfe:pag", NSMAP):
        det_pag = pag.find("nfe:detPag", NSMAP) or pag
        pay = Pagamento(
            tipo_pagamento=_get_text(det_pag, "nfe:tPag"),
            valor_pagamento=_to_float(_get_text(det_pag, "nfe:vPag")),
            integracao=_get_text(det_pag, "nfe:tpIntegra"),
            cnpj_operadora=_get_text(det_pag, "nfe:CNPJ"),
            bandeira=_get_text(det_pag, "nfe:tBand"),
            autorizacao=_get_text(det_pag, "nfe:cAut"),
        )
        doc.pagamentos.append(pay)

    # ------------------ Protocolo / Status / Assinatura ------------------
    # Se for nfeProc, tenta pegar infProt
    if tag == "nfeProc":
        inf_prot = root.find(".//nfe:infProt", NSMAP)
        if inf_prot is not None:
            doc.protocolo = _get_text(inf_prot, "nfe:nProt")
            doc.status = _get_text(inf_prot, "nfe:cStat")

    # Assinatura
    # (Signature está em outro namespace, então usamos wildcard)
    signature = root.find(".//{*}Signature")
    if signature is not None:
        doc.assinatura = etree.tostring(signature, encoding="unicode")

    return doc


# -------------------------------------------------------------------
# Conversor para dict (para API)
# -------------------------------------------------------------------


def doc_sped_to_dict(doc: DocSped) -> dict:
    """
    Converte DocSped (dataclass) em dict pronto para JSON.
    """
    return asdict(doc)
