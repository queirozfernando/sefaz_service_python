# sefaz_service/danfe/nfce_html.py

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional

from lxml import etree

NFE_NS = "http://www.portalfiscal.inf.br/nfe"
NSMAP = {"nfe": NFE_NS}


def _get_text(elem, path: str, ns: dict = NSMAP, default: str = "") -> str:
    """Helper pra pegar texto de um caminho XPath simples."""
    if elem is None:
        return default
    node = elem.find(path, ns)
    if node is not None and node.text:
        return node.text.strip()
    return default


def _format_number(value: Decimal | float | str, casas: int) -> str:
    if value is None:
        value = Decimal("0")
    if not isinstance(value, Decimal):
        value = Decimal(str(value or "0"))
    q = Decimal("1").scaleb(-casas)  # 10^-casas
    return str(value.quantize(q, rounding=ROUND_HALF_UP))


def _format_cnpj_cpf(doc: str) -> str:
    d = "".join(c for c in (doc or "") if c.isdigit())
    if len(d) == 14:
        return f"{d[0:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:14]}"
    if len(d) == 11:
        return f"{d[0:3]}.{d[3:6]}.{d[6:9]}-{d[9:11]}"
    return doc or ""


def _make_qrcode_base64(text: str) -> Optional[str]:
    """Gera QRCode em base64 (PNG). Se falhar, retorna None."""
    if not text:
        return None

    import qrcode
    import base64
    from io import BytesIO

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=3,
        border=1,
    )
    qr.add_data(text)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


@dataclass
class ItemNfce:
    cProd: str
    xProd: str
    qCom: Decimal
    uCom: str
    vUnCom: Decimal
    vProd: Decimal


@dataclass
class NfceData:
    ide: dict
    emit: dict
    dest: dict
    icms_tot: dict
    inf_prot: dict
    inf_adic: dict
    chave: str
    qrcode: str
    url_chave: str
    itens: List[ItemNfce] = field(default_factory=list)
    formas_pagto: List[tuple] = field(default_factory=list)  # (descricao, Decimal)
    v_troco: Decimal = Decimal("0.00")


def _parse_nfce_xml(xml_str: str) -> NfceData:
    root = etree.fromstring(xml_str.encode("utf-8"))

    # Pode vir como <nfeProc><NFe>... ou direto <NFe>
    nfe = root.find(".//nfe:NFe", NSMAP) or root
    inf_nfe = nfe.find(".//nfe:infNFe", NSMAP)

    ide = inf_nfe.find("nfe:ide", NSMAP)
    emit = inf_nfe.find("nfe:emit", NSMAP)
    dest = inf_nfe.find("nfe:dest", NSMAP)
    total = inf_nfe.find("nfe:total/nfe:ICMSTot", NSMAP)
    inf_adic = inf_nfe.find("nfe:infAdic", NSMAP)
    inf_prot = root.find(".//nfe:infProt", NSMAP)

    # ⚠️ infNFeSupl é filho de NFe, não de infNFe
    inf_supl = nfe.find("nfe:infNFeSupl", NSMAP)

    chave = (inf_nfe.get("Id") or "").replace("NFe", "").strip()

    ide_dict = {
        "tpAmb": _get_text(ide, "nfe:tpAmb"),
        "cUF": _get_text(ide, "nfe:cUF"),
        "serie": _get_text(ide, "nfe:serie"),
        "nNF": _get_text(ide, "nfe:nNF"),
        "dhEmi": _get_text(ide, "nfe:dhEmi"),
        "tpEmis": _get_text(ide, "nfe:tpEmis"),
    }

    emit_dict = {
        "CNPJ": _get_text(emit, "nfe:CNPJ"),
        "CPF": _get_text(emit, "nfe:CPF"),
        "IE": _get_text(emit, "nfe:IE"),
        "xNome": _get_text(emit, "nfe:xNome"),
        "xLgr": _get_text(emit, "nfe:enderEmit/nfe:xLgr"),
        "nro": _get_text(emit, "nfe:enderEmit/nfe:nro"),
        "xBairro": _get_text(emit, "nfe:enderEmit/nfe:xBairro"),
        "xMun": _get_text(emit, "nfe:enderEmit/nfe:xMun"),
        "UF": _get_text(emit, "nfe:enderEmit/nfe:UF"),
    }
    if not emit_dict["CNPJ"]:
        emit_dict["CNPJ"] = emit_dict["CPF"]

    dest_dict = {
        "CNPJ": _get_text(dest, "nfe:CNPJ"),
        "CPF": _get_text(dest, "nfe:CPF"),
        "xNome": _get_text(dest, "nfe:xNome"),
        "xLgr": _get_text(dest, "nfe:enderDest/nfe:xLgr"),
        "nro": _get_text(dest, "nfe:enderDest/nfe:nro"),
        "xBairro": _get_text(dest, "nfe:enderDest/nfe:xBairro"),
        "xMun": _get_text(dest, "nfe:enderDest/nfe:xMun"),
        "UF": _get_text(dest, "nfe:enderDest/nfe:UF"),
    }
    if not dest_dict["CNPJ"]:
        dest_dict["CNPJ"] = dest_dict["CPF"]

    icms_tot_dict = {
        "vProd": _get_text(total, "nfe:vProd"),
        "vFrete": _get_text(total, "nfe:vFrete"),
        "vSeg": _get_text(total, "nfe:vSeg"),
        "vOutro": _get_text(total, "nfe:vOutro"),
        "vDesc": _get_text(total, "nfe:vDesc"),
        "vNF": _get_text(total, "nfe:vNF"),
        "vTotTrib": _get_text(total, "nfe:vTotTrib"),
    }

    inf_prot_dict = {
        "nProt": _get_text(inf_prot, "nfe:nProt"),
        "dhRecbto": _get_text(inf_prot, "nfe:dhRecbto"),
    }

    inf_adic_dict = {
        "infAdFisco": _get_text(inf_adic, "nfe:infAdFisco"),
        "infCpl": _get_text(inf_adic, "nfe:infCpl"),
    }

    qrcode = ""
    url_chave = ""
    if inf_supl is not None:
        qrcode = _get_text(inf_supl, "nfe:qrCode")
        url_chave = _get_text(inf_supl, "nfe:urlChave")

    # Itens
    itens: List[ItemNfce] = []
    for det in inf_nfe.findall("nfe:det", NSMAP):
        prod = det.find("nfe:prod", NSMAP)
        if prod is None:
            continue
        itens.append(
            ItemNfce(
                cProd=_get_text(prod, "nfe:cProd"),
                xProd=_get_text(prod, "nfe:xProd"),
                qCom=Decimal(_get_text(prod, "nfe:qCom") or "0"),
                uCom=_get_text(prod, "nfe:uCom"),
                vUnCom=Decimal(_get_text(prod, "nfe:vUnCom") or "0"),
                vProd=Decimal(_get_text(prod, "nfe:vProd") or "0"),
            )
        )

    # Pagamentos
    formas_pagto: List[tuple] = []
    v_troco = Decimal("0.00")

    for det_pag in inf_nfe.findall("nfe:pag/nfe:detPag", NSMAP):
        tPag = _get_text(det_pag, "nfe:tPag")
        vPag = Decimal(_get_text(det_pag, "nfe:vPag") or "0")
        formas_pagto.append((tPag, vPag))

    troco_node = inf_nfe.find("nfe:pag/nfe:vTroco", NSMAP)
    if troco_node is not None and troco_node.text:
        v_troco = Decimal(troco_node.text.strip())

    return NfceData(
        ide=ide_dict,
        emit=emit_dict,
        dest=dest_dict,
        icms_tot=icms_tot_dict,
        inf_prot=inf_prot_dict,
        inf_adic=inf_adic_dict,
        chave=chave,
        qrcode=qrcode,
        url_chave=url_chave,
        itens=itens,
        formas_pagto=formas_pagto,
        v_troco=v_troco,
    )


def nfce_xml_to_html(
    xml_or_path: str,
    logo_data_uri: Optional[str] = None,
    desenvolvedor: str = "",
) -> str:
    """
    Gera HTML do DANFE NFC-e em formato de cupom (80mm).
    xml_or_path: XML em string OU caminho para arquivo XML.
    logo_data_uri: se quiser um <img src="data:image/png;base64,..."> no topo.
    """

    # Carrega XML (string ou arquivo)
    if len(xml_or_path) < 100 and not xml_or_path.strip().startswith("<"):
        with open(xml_or_path, "r", encoding="utf-8") as f:
            xml_str = f.read()
    else:
        xml_str = xml_or_path

    data = _parse_nfce_xml(xml_str)

    emit = data.emit
    dest = data.dest
    icms = data.icms_tot

    # Prepara campos numéricos
    v_prod = Decimal(icms.get("vProd") or "0")
    v_nf = Decimal(icms.get("vNF") or "0")
    v_frete = Decimal(icms.get("vFrete") or "0")
    v_seg = Decimal(icms.get("vSeg") or "0")
    v_outro = Decimal(icms.get("vOutro") or "0")
    v_desc = Decimal(icms.get("vDesc") or "0")
    v_tot_trib = Decimal(icms.get("vTotTrib") or "0")

    acresc_desc = v_frete + v_seg + v_outro - v_desc

    doc_emit = _format_cnpj_cpf(emit.get("CNPJ") or emit.get("CPF") or "")
    end_emit = (
        f"{emit.get('xLgr','')}, {emit.get('nro','')}, "
        f"{emit.get('xBairro','')}, {emit.get('xMun','')}-{emit.get('UF','')}"
    )

    doc_dest_raw = dest.get("CNPJ") or dest.get("CPF") or ""
    doc_dest_fmt = _format_cnpj_cpf(doc_dest_raw) if doc_dest_raw else ""
    tipo_doc_dest = "CPF" if len("".join(filter(str.isdigit, doc_dest_raw))) == 11 else "CNPJ"

    # Ambiente / contingência
    tp_amb = data.ide.get("tpAmb")
    tp_emis = data.ide.get("tpEmis")

    homologacao_msg = ""
    if tp_amb == "2":  # homologação
        homologacao_msg = """
        <div class="section center">
            <div><strong>EMITIDA EM AMBIENTE DE HOMOLOGAÇÃO</strong></div>
            <div><strong>SEM VALOR FISCAL</strong></div>
        </div>
        <hr>
        """

    contingencia_msg = ""
    if tp_emis == "9":
        contingencia_msg = """
        <div class="section center">
            <div><strong>EMITIDA EM CONTINGÊNCIA</strong></div>
            <div>PENDENTE DE AUTORIZAÇÃO</div>
        </div>
        <hr>
        """

    # Mensagens adicionais
    def _split_msg(msg: str) -> List[str]:
        if not msg:
            return []
        msg = msg.replace(";;", "\n").replace(";", "\n").replace("|", "\n")
        linhas = []
        for linha in msg.splitlines():
            linha = linha.strip()
            if linha:
                linhas.append(linha)
        return linhas

    inf_fisco_lines = _split_msg(data.inf_adic.get("infAdFisco") or "")
    inf_cpl_lines = _split_msg(data.inf_adic.get("infCpl") or "")

    # Mapeia tPag para descrição
    def _descricao_pag(tpag: str) -> str:
        mapa = {
            "01": "Dinheiro",
            "02": "Cheque",
            "03": "Cartão de Crédito",
            "04": "Cartão de Débito",
            "05": "Crédito Loja",
            "10": "Vale Alimentação",
            "11": "Vale Refeição",
            "12": "Vale Presente",
            "13": "Vale Combustível",
            "15": "Boleto Bancário",
            "16": "Depósito Bancário",
            "17": "PIX",
            "18": "Transferência Bancária",
            "19": "Programa de Fidelidade",
            "20": "Carteira Digital",
            "90": "Sem Pagamento",
            "99": "Outros",
        }
        return mapa.get(tpag, tpag)

    # QRCode
    c_qr = data.qrcode or ""
    if c_qr.startswith("<![CDATA["):
        c_qr = c_qr[9:-3].strip()

    qr_b64 = None
    if c_qr:
        try:
            qr_b64 = _make_qrcode_base64(c_qr)
        except Exception as e:
            print("ERRO GERANDO QRCODE NFC-e:", e)
            qr_b64 = None

    # URL de consulta (fallback padrão nacional se vier vazio)
    url_consulta = data.url_chave or "http://www.nfe.fazenda.gov.br/portal"

    # HTML
    html = [
        "<!DOCTYPE html>",
        "<html>",
        "<head>",
        '<meta charset="utf-8">',
        "<title>DANFE NFC-e</title>",
        """
        <style>
            body {
                font-family: Arial, Helvetica, sans-serif;
                font-size: 9px;
                margin: 0;
                padding: 0;
            }
            .cupom {
                width: 280px; /* ~80mm */
                margin: 0 auto;
                padding: 4px;
            }
            .center { text-align: center; }
            .right { text-align: right; }
            .left { text-align: left; }
            .bold { font-weight: bold; }
            hr {
                border: 0;
                border-top: 1px dashed #000;
                margin: 4px 0;
            }
            table {
                width: 100%;
                border-collapse: collapse;
            }
            th, td {
                padding: 2px 0;
                vertical-align: top;
            }
            th {
                font-size: 9px;
                border-bottom: 1px solid #000;
            }
            .small { font-size: 8px; }
            .line { border-top: 1px dashed #000; margin: 4px 0; }
            .footer-dev {
                font-size: 7px;
                text-align: right;
                margin-top: 6px;
            }
            .wrap {
                word-wrap: break-word;
                white-space: normal;
            }
        </style>
        """,
        "</head>",
        "<body>",
        '<div class="cupom">',
    ]

    # LOGO + emitente
    html.append('<div class="section center">')
    if logo_data_uri:
        html.append(
            f'<div><img src="{logo_data_uri}" '
            'style="max-width:60px; max-height:60px;"></div>'
        )
    html.append(f'<div class="bold">{emit.get("xNome","")}</div>')
    if doc_emit:
        html.append(f'<div>CNPJ/CPF: {doc_emit} IE: {emit.get("IE","")}</div>')
    html.append(f'<div class="wrap">{end_emit}</div>')
    html.append("</div>")
    html.append("<hr>")
    html.append(
        '<div class="section center small">'
        '<div class="bold">DANFE NFC-e - Documento Auxiliar</div>'
        '<div class="bold">da Nota Fiscal de Consumidor Eletrônica</div>'
        "<div>Não permite aproveitamento de crédito do ICMS</div>"
        "</div>"
    )
    html.append("<hr>")

    # Mensagens de homologação / contingência
    html.append(homologacao_msg)
    html.append(contingencia_msg)

    # Tabela de itens
    html.append('<div class="section">')
    html.append("<table>")
    html.append(
        "<tr>"
        '<th class="left">CÓDIGO</th>'
        '<th class="left">DESCRIÇÃO</th>'
        "</tr>"
    )
    html.append(
        "<tr>"
        '<th class="right small" style="width:25%;">QTD</th>'
        '<th class="left small" style="width:15%;">UN</th>'
        '<th class="right small" style="width:30%;">VL.UNIT</th>'
        '<th class="right small" style="width:30%;">VL.TOTAL</th>'
        "</tr>"
    )

    for it in data.itens:
        # Linha código + descrição (ocupando 4 colunas)
        html.append(
            "<tr>"
            f'<td colspan="4" class="wrap small">'
            f'<span class="bold">{it.cProd}</span> - {it.xProd}'
            "</td>"
            "</tr>"
        )

        qtd_str = _format_number(it.qCom, 3)
        vl_unit_str = _format_number(it.vUnCom, 4)  # 4 casas decimais
        vl_total_str = _format_number(it.vProd, 2)

        html.append(
            "<tr>"
            f'<td class="right small">{qtd_str}</td>'
            f'<td class="left small">{it.uCom}</td>'
            f'<td class="right small">{vl_unit_str}</td>'
            f'<td class="right small">{vl_total_str}</td>'
            "</tr>"
        )

    html.append("</table>")
    html.append("</div>")
    html.append("<hr>")

    # Totais
    html.append('<div class="section small">')
    html.append(
        '<div><span class="bold">QTD. TOTAL DE ITENS</span>'
        f'<span class="right" style="float:right;">{len(data.itens)}</span></div>'
    )
    html.append(
        '<div><span class="bold">VALOR TOTAL R$</span>'
        f'<span class="right" style="float:right;">{_format_number(v_prod, 2)}</span></div>'
    )

    if acresc_desc != 0:
        if acresc_desc > 0:
            label = "Acréscimos"
            valor = acresc_desc
        else:
            label = "Descontos"
            valor = -acresc_desc
        html.append(
            f'<div><span class="bold">{label}</span>'
            f'<span class="right" style="float:right;">{_format_number(valor, 2)}</span></div>'
        )

    html.append(
        '<div><span class="bold">VALOR A PAGAR R$</span>'
        f'<span class="right" style="float:right;">{_format_number(v_nf, 2)}</span></div>'
    )
    html.append("<br>")

    # Formas de pagamento
    html.append(
        '<div><span class="bold">FORMA DE PAGAMENTO</span>'
        '<span class="bold" style="float:right;">VALOR PAGO R$</span></div>'
    )
    for cod, valor in data.formas_pagto:
        desc = _descricao_pag(cod)
        html.append(
            f"<div><span>{desc}</span>"
            f'<span style="float:right;">{_format_number(valor, 2)}</span></div>'
        )

    if data.v_troco:
        html.append(
            '<div><span>Troco R$</span>'
            f'<span style="float:right;">{_format_number(data.v_troco, 2)}</span></div>'
        )

    html.append("</div>")
    html.append("<hr>")

    # Info tributos
    html.append(
        '<div class="section small">'
        '<div class="bold">Informação dos Tributos Totais Incidentes (Fonte: IBPT)</div>'
        f'<div class="right">{_format_number(v_tot_trib, 2)}</div>'
        "<div>(Lei Federal 12.741 / 2012)</div>"
        "</div>"
    )
    html.append("<hr>")

    # Bloco "Consulte pela Chave de Acesso"
    html.append('<div class="section center small">')
    html.append("<div>Consulte pela Chave de Acesso em:</div>")
    html.append(f'<div>{url_consulta}</div>')
    html.append("<br>")
    html.append('<div class="bold">CHAVE DE ACESSO</div>')
    html.append(f'<div class="wrap">{data.chave}</div>')
    html.append("</div>")
    html.append("<hr>")

    # QRCode + Consumidor lado a lado
    html.append('<div class="section small">')
    html.append("<table>")
    html.append("<tr>")

    # Coluna esquerda: QRCode ou texto
    html.append('<td class="center" style="width: 45%;">')
    if qr_b64:
        html.append(
            f'<img src="data:image/png;base64,{qr_b64}" '
            'alt="QRCode" style="width:120px; height:120px;">'
        )
    else:
        html.append(
            "<div style='border:1px dashed #000; padding:8px;'>"
            "[ QR CODE NÃO DISPONÍVEL ]"
            "</div>"
        )
    html.append("</td>")

    # Coluna direita: dados do consumidor
    html.append('<td class="small" style="width: 55%;">')
    if doc_dest_fmt:
        html.append(
            f'<div class="bold">CONSUMIDOR {tipo_doc_dest}: {doc_dest_fmt}</div>'
        )
    else:
        html.append('<div class="bold">CONSUMIDOR NÃO IDENTIFICADO</div>')

    ide = data.ide
    prot = data.inf_prot

    n_nf = ide.get("nNF") or "0"
    serie = ide.get("serie") or "0"
    try:
        n_nf_fmt = f"{int(n_nf):09d}"
    except ValueError:
        n_nf_fmt = n_nf
    try:
        serie_fmt = f"{int(serie):03d}"
    except ValueError:
        serie_fmt = serie

    html.append(
        f"<div>Número: <span class='bold'>{n_nf_fmt}</span> - "
        f"Série: <span class='bold'>{serie_fmt}</span></div>"
    )

    dh_emi = ide.get("dhEmi") or ""
    if len(dh_emi) >= 19:
        data_emi = f"{dh_emi[8:10]}/{dh_emi[5:7]}/{dh_emi[0:4]} {dh_emi[11:19]}"
        html.append(f"<div>Emissão: <span class='bold'>{data_emi}</span></div>")

    if prot.get("nProt"):
        html.append(
            "<div>Protocolo de autorização: "
            f"<span class='bold'>{prot['nProt']}</span></div>"
        )

    dh_recb = prot.get("dhRecbto") or ""
    if len(dh_recb) >= 19:
        data_aut = f"{dh_recb[8:10]}/{dh_recb[5:7]}/{dh_recb[0:4]} {dh_recb[11:19]}"
        html.append(
            " <div>Data de autorização: "
            f"<span class='bold'>{data_aut}</span></div>"
        )

    html.append("</td>")
    html.append("</tr>")
    html.append("</table>")
    html.append("</div>")
    html.append("<hr>")

    # Mensagens fiscais e do contribuinte
    if inf_fisco_lines:
        html.append('<div class="section small">')
        for linha in inf_fisco_lines:
            html.append(f'<div class="wrap">{linha}</div>')
        html.append("</div>")
        html.append("<hr>")

    if inf_cpl_lines:
        html.append('<div class="section small">')
        for linha in inf_cpl_lines:
            html.append(f'<div class="wrap">{linha}</div>')
        html.append("</div>")
        html.append("<hr>")

    # Desenvolvedor
    if desenvolvedor:
        html.append(f'<div class="footer-dev">{desenvolvedor}</div>')

    html.append("</div>")  # .cupom
    html.append("</body></html>")

    return "\n".join(html)
