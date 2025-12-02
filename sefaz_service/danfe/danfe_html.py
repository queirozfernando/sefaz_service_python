# sefaz_service/danfe/danfe_html.py
from __future__ import annotations

from typing import Optional, List
from io import BytesIO
import base64

from lxml import etree

NFE_NS = "http://www.portalfiscal.inf.br/nfe"


def _get_text(elem, path: str, ns: dict, default: str = "") -> str:
    """Helper pra pegar texto de um caminho XPath simples."""
    if elem is None:
        return default
    node = elem.find(path, ns)
    if node is not None and node.text:
        return node.text.strip()
    return default


def _format_cnpj_cpf(doc: str) -> str:
    d = "".join([c for c in (doc or "") if c.isdigit()])
    if len(d) == 14:
        return f"{d[0:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:14]}"
    if len(d) == 11:
        return f"{d[0:3]}.{d[3:6]}.{d[6:9]}-{d[9:11]}"
    return doc or ""


def _format_chave(chave: str) -> str:
    """Formata a chave de acesso em blocos de 4 dígitos."""
    d = "".join([c for c in (chave or "") if c.isdigit()])
    return " ".join(d[i: i + 4] for i in range(0, len(d), 4))


def _format_data_br(iso: str) -> str:
    """
    Converte 'AAAA-MM-DD' ou 'AAAA-MM-DDTHH:MM:SS-03:00'
    para 'DD/MM/AAAA'.
    """
    if not iso:
        return ""
    data = iso.split("T")[0]
    partes = data.split("-")
    if len(partes) != 3:
        return data
    ano, mes, dia = partes
    return f"{dia}/{mes}/{ano}"


def _extrair_icms_info(det, ns) -> dict:
    """
    Extrai CST/CSOSN, vBC, vICMS, pICMS do bloco <imposto><ICMS>.
    Retorna dict com chaves: cst_csosn, vbc, vicms, picms.
    """
    imposto = det.find("nfe:imposto", ns)
    if imposto is None:
        return {"cst_csosn": "", "vbc": "", "vicms": "", "picms": ""}

    icms = imposto.find("nfe:ICMS", ns)
    if icms is None:
        return {"cst_csosn": "", "vbc": "", "vicms": "", "picms": ""}

    icms_child = None
    for child in icms:
        icms_child = child
        break

    if icms_child is None:
        return {"cst_csosn": "", "vbc": "", "vicms": "", "picms": ""}

    cst = _get_text(icms_child, "nfe:CST", ns)
    csosn = _get_text(icms_child, "nfe:CSOSN", ns)
    cst_csosn = csosn or cst

    vbc = _get_text(icms_child, "nfe:vBC", ns)
    vicms = _get_text(icms_child, "nfe:vICMS", ns)
    picms = _get_text(icms_child, "nfe:pICMS", ns)

    return {
        "cst_csosn": cst_csosn,
        "vbc": vbc,
        "vicms": vicms,
        "picms": picms,
    }


def _gerar_barcode_base64(chave: str) -> Optional[str]:
    """
    Gera um código de barras Code128 da chave de acesso (44 dígitos)
    e retorna como base64 (PNG). Se não conseguir, retorna None.
    """
    try:
        import barcode
        from barcode.writer import ImageWriter
    except Exception:
        return None

    digits = "".join(c for c in (chave or "") if c.isdigit())
    if not digits:
        return None

    try:
        code128 = barcode.get("code128", digits, writer=ImageWriter())
        buf = BytesIO()
        code128.write(
            buf,
            options={
                "module_height": 18.0,
                "module_width": 0.35,
                "font_size": 0,
            },
        )
        return base64.b64encode(buf.getvalue()).decode("ascii")
    except Exception:
        return None


def gerar_danfe_html(
    xml_nfe_proc: str,
    logo_url: Optional[str] = None,
) -> str:
    """
    Gera um DANFE (layout retrato) em HTML a partir do XML nfeProc.

    - 1ª folha: canhoto + cabeçalho completo + FATURA/DUPLICATAS +
      TRANSPORTADOR + itens + INF. COMPL./PAGAMENTO.
    - Demais folhas: cabeçalho até NATUREZA DA OPERAÇÃO + itens.
    """
    parser = etree.XMLParser(remove_blank_text=True)
    root = etree.fromstring(xml_nfe_proc.encode("utf-8"), parser=parser)

    ns = {"nfe": NFE_NS}

    nfe_el = root.find("nfe:NFe", ns)
    prot_el = root.find("nfe:protNFe", ns)

    if nfe_el is None:
        raise ValueError("nfeProc sem nó <NFe>")

    inf_nfe = nfe_el.find("nfe:infNFe", ns)
    if inf_nfe is None:
        raise ValueError("NFe sem <infNFe>")

    ide = inf_nfe.find("nfe:ide", ns)
    emit = inf_nfe.find("nfe:emit", ns)
    dest = inf_nfe.find("nfe:dest", ns)
    total = inf_nfe.find("nfe:total", ns)
    transp = inf_nfe.find("nfe:transp", ns)
    pag = inf_nfe.find("nfe:pag", ns)
    inf_adic = inf_nfe.find("nfe:infAdic", ns)

    # ----- CABEÇALHO / DADOS PRINCIPAIS -----
    n_nf = _get_text(ide, "nfe:nNF", ns)
    serie = _get_text(ide, "nfe:serie", ns)
    dh_emi = _get_text(ide, "nfe:dhEmi", ns)
    dh_saida = _get_text(ide, "nfe:dhSaiEnt", ns)
    nat_op = _get_text(ide, "nfe:natOp", ns)
    tp_amb = _get_text(ide, "nfe:tpAmb", ns)
    tp_nf = _get_text(ide, "nfe:tpNF", ns)

    def _so_data(iso: str) -> str:
        if "T" in iso:
            return iso.split("T")[0]
        return iso

    data_emi_iso = _so_data(dh_emi)
    data_emi_br = _format_data_br(dh_emi)
    data_saida_br = _format_data_br(dh_saida)

    chave_acesso = (inf_nfe.get("Id") or "").replace("NFe", "")
    chave_formatada = _format_chave(chave_acesso)

    # código de barras da chave
    barcode_b64 = _gerar_barcode_base64(chave_acesso)
    barcode_img_html = ""
    if barcode_b64:
        barcode_img_html = (
            f'<img src="data:image/png;base64,{barcode_b64}" '
            f'style="margin-top:3px;height:45px;display:block;'
            f'margin-left:auto;margin-right:auto;" '
            f'alt="Código de barras" />'
        )

    # ----- EMITENTE -----
    emit_xnome = _get_text(emit, "nfe:xNome", ns)
    emit_xfant = _get_text(emit, "nfe:xFant", ns)
    emit_cnpj = _format_cnpj_cpf(_get_text(emit, "nfe:CNPJ", ns))
    emit_ie = _get_text(emit, "nfe:IE", ns)
    emit_fone = _get_text(emit, "nfe:fone", ns)

    ender_emit = emit.find("nfe:enderEmit", ns) if emit is not None else None
    emit_log = emit_nro = emit_bai = emit_mun = emit_uf = emit_cep = ""
    if ender_emit is not None:
        emit_log = _get_text(ender_emit, "nfe:xLgr", ns)
        emit_nro = _get_text(ender_emit, "nfe:nro", ns)
        emit_bai = _get_text(ender_emit, "nfe:xBairro", ns)
        emit_mun = _get_text(ender_emit, "nfe:xMun", ns)
        emit_uf = _get_text(ender_emit, "nfe:UF", ns)
        emit_cep = _get_text(ender_emit, "nfe:CEP", ns)

    # ----- DESTINATÁRIO -----
    dest_xnome = _get_text(dest, "nfe:xNome", ns)
    dest_cnpj = _format_cnpj_cpf(
        _get_text(dest, "nfe:CNPJ", ns) or _get_text(dest, "nfe:CPF", ns)
    )
    dest_ie = _get_text(dest, "nfe:IE", ns)
    dest_fone = _get_text(dest, "nfe:fone", ns)
    dest_im = _get_text(dest, "nfe:IM", ns)

    ender_dest = dest.find("nfe:enderDest", ns) if dest is not None else None
    dest_log = dest_nro = dest_bai = dest_mun = dest_uf = dest_cep = ""
    if ender_dest is not None:
        dest_log = _get_text(ender_dest, "nfe:xLgr", ns)
        dest_nro = _get_text(ender_dest, "nfe:nro", ns)
        dest_bai = _get_text(ender_dest, "nfe:xBairro", ns)
        dest_mun = _get_text(ender_dest, "nfe:xMun", ns)
        dest_uf = _get_text(ender_dest, "nfe:UF", ns)
        dest_cep = _get_text(ender_dest, "nfe:CEP", ns)

    # ----- TOTAIS -----
    icmstot = total.find("nfe:ICMSTot", ns) if total is not None else None
    v_bc = _get_text(icmstot, "nfe:vBC", ns)
    v_icms = _get_text(icmstot, "nfe:vICMS", ns)
    v_bc_st = _get_text(icmstot, "nfe:vBCST", ns)
    v_st = _get_text(icmstot, "nfe:vST", ns)
    v_prod = _get_text(icmstot, "nfe:vProd", ns)
    v_frete = _get_text(icmstot, "nfe:vFrete", ns)
    v_seg = _get_text(icmstot, "nfe:vSeg", ns)
    v_desc = _get_text(icmstot, "nfe:vDesc", ns)
    v_outro = _get_text(icmstot, "nfe:vOutro", ns)
    v_ipi = _get_text(icmstot, "nfe:vIPI", ns)
    v_nf = _get_text(icmstot, "nfe:vNF", ns)
    v_tot_trib = _get_text(icmstot, "nfe:vTotTrib", ns)

    # ----- PROTOCOLO -----
    protocolo = ""
    dh_prot = ""
    if prot_el is not None:
        inf_prot = prot_el.find("nfe:infProt", ns)
        if inf_prot is not None:
            protocolo = _get_text(inf_prot, "nfe:nProt", ns)
            dh_prot = _get_text(inf_prot, "nfe:dhRecbto", ns)

    # ----- TRANSPORTE -----
    mod_frete = _get_text(transp, "nfe:modFrete", ns)
    mod_frete_map = {
        "0": "0-EMITENTE",
        "1": "1-DEST/REM",
        "2": "2-TERCEIROS",
        "9": "9-SEM FRETE",
    }
    mod_frete_desc = mod_frete_map.get(mod_frete, mod_frete)

    transp_nome = ""
    transp_cnpj = ""
    transp_ie = ""
    transp_ender = ""
    transp_mun = ""
    transp_uf = ""
    vol_qtd = vol_peso_b = vol_peso_l = ""
    transporta = transp.find("nfe:transporta", ns) if transp is not None else None
    if transporta is not None:
        transp_nome = _get_text(transporta, "nfe:xNome", ns)
        transp_cnpj = _format_cnpj_cpf(
            _get_text(transporta, "nfe:CNPJ", ns) or _get_text(transporta, "nfe:CPF", ns)
        )
        transp_ie = _get_text(transporta, "nfe:IE", ns)
        transp_ender = _get_text(transporta, "nfe:xEnder", ns)
        transp_mun = _get_text(transporta, "nfe:xMun", ns)
        transp_uf = _get_text(transporta, "nfe:UF", ns)

    vol = transp.find("nfe:vol", ns) if transp is not None else None
    if vol is not None:
        vol_qtd = _get_text(vol, "nfe:qVol", ns)
        vol_peso_b = _get_text(vol, "nfe:pesoB", ns)
        vol_peso_l = _get_text(vol, "nfe:pesoL", ns)

    # ----- PAGAMENTO -----
    t_pag = ""
    v_pag = ""
    if pag is not None:
        det_pag = pag.find("nfe:detPag", ns)
        if det_pag is not None:
            t_pag = _get_text(det_pag, "nfe:tPag", ns)
            v_pag = _get_text(det_pag, "nfe:vPag", ns)

    # Tabela atualizada de formas de pagamento
    t_pag_map = {
        "01": "DINHEIRO",
        "02": "CHEQUE",
        "03": "CARTÃO DE CRÉDITO",
        "04": "CARTÃO DE DÉBITO",
        "05": "CRÉDITO LOJA - FATURADO",
        "10": "VALE ALIMENTAÇÃO",
        "11": "VALE REFEIÇÃO",
        "12": "VALE PRESENTE",
        "13": "VALE COMBUSTÍVEL",
        "15": "BOLETO BANCÁRIO",
        "16": "DEPÓSITO BANCÁRIO",
        "17": "PAGAMENTO INSTANTÂNEO (PIX)",
        "18": "TRANSFERÊNCIA BANCÁRIA",
        "19": "PROGRAMA DE FIDELIDADE",
        "20": "PAG. INSTANTÂNEO (PIX) ESTÁTICO",
        "90": "SEM PAGAMENTO",
        "99": "OUTROS",
    }
    t_pag_desc = t_pag_map.get(t_pag, t_pag)

    # ----- FATURA / DUPLICATAS -----
    duplicatas: List[dict] = []
    cobr = inf_nfe.find("nfe:cobr", ns)
    if cobr is not None:
        for dup in cobr.findall("nfe:dup", ns):
            n_dup = _get_text(dup, "nfe:nDup", ns)
            d_venc = _get_text(dup, "nfe:dVenc", ns)
            v_dup = _get_text(dup, "nfe:vDup", ns)
            duplicatas.append(
                {
                    "nDup": n_dup,
                    "dVenc": _format_data_br(d_venc),
                    "vDup": v_dup,
                }
            )

    # ----- INF. ADICIONAIS -----
    inf_cpl_raw = _get_text(inf_adic, "nfe:infCpl", ns)
    inf_cpl = _format_inf_cpl(inf_cpl_raw)


    # ----- ITENS -----
    itens: List[dict] = []
    for det in inf_nfe.findall("nfe:det", ns):
        prod = det.find("nfe:prod", ns)
        if prod is None:
            continue
        n_item = det.get("nItem", "")
        c_prod = _get_text(prod, "nfe:cProd", ns)
        x_prod = _get_text(prod, "nfe:xProd", ns)
        ncm = _get_text(prod, "nfe:NCM", ns)
        cfop = _get_text(prod, "nfe:CFOP", ns)
        u_com = _get_text(prod, "nfe:uCom", ns)
        q_com = _get_text(prod, "nfe:qCom", ns)
        v_un_com = _get_text(prod, "nfe:vUnCom", ns)
        v_prod_item = _get_text(prod, "nfe:vProd", ns)
        cean = _get_text(prod, "nfe:cEAN", ns)

        icms_info = _extrair_icms_info(det, ns)

        itens.append(
            {
                "nItem": n_item,
                "cProd": c_prod,
                "xProd": x_prod,
                "NCM": ncm,
                "CFOP": cfop,
                "uCom": u_com,
                "qCom": q_com,
                "vUnCom": v_un_com,
                "vProd": v_prod_item,
                "cEAN": cean,
                "CST_CSOSN": icms_info["cst_csosn"],
                "vBC": icms_info["vbc"],
                "vICMS": icms_info["vicms"],
                "pICMS": icms_info["picms"],
            }
        )

    texto_ambiente = "PRODUÇÃO" if tp_amb == "1" else "HOMOLOGAÇÃO"

    # ---------- PAGINAÇÃO DOS ITENS ----------
    # Menos itens na 1ª página por causa de FATURA/DUPLICATAS + rodapé
    MAX_ITENS_PRIMEIRA = 23
    MAX_ITENS_DEMAIS = 50

    pages_itens: List[List[dict]] = []
    if len(itens) <= MAX_ITENS_PRIMEIRA:
        pages_itens.append(itens)
    else:
        pages_itens.append(itens[:MAX_ITENS_PRIMEIRA])
        restante = itens[MAX_ITENS_PRIMEIRA:]
        for i in range(0, len(restante), MAX_ITENS_DEMAIS):
            pages_itens.append(restante[i: i + MAX_ITENS_DEMAIS])

    total_paginas = len(pages_itens)

    # ---------- HTML / CSS ----------
    css = """
    <style>
        body {
            font-family: Arial, sans-serif;
            font-size: 9px;
            margin: 0;
            padding: 0;
            background-color: #cccccc;
        }
        .page {
            width: 794px;
            min-height: 1123px;
            margin: 8px auto;
            background-color: #ffffff;
            padding: 6px;
            box-sizing: border-box;
        }
        .danfe-container {
            border: 1px solid #000;
            padding: 4px;
        }
        .linha {
            display: flex;
            flex-direction: row;
            margin-bottom: 2px;
        }
        .box {
            border: 1px solid #000;
            padding: 2px 3px;
            margin-right: 2px;
            flex-grow: 1;
        }
        .box:last-child {
            margin-right: 0;
        }
        .titulo {
            font-weight: bold;
            font-size: 8px;
        }
        .conteudo {
            font-size: 9px;
        }
        .centro {
            text-align: center;
        }
        .direita {
            text-align: right;
        }
        .itens table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 2px;
        }
        .itens th, .itens td {
            border: 1px solid #000;
            padding: 2px;
            font-size: 8px;
        }
        .itens th {
            background-color: #f5f5f5;
        }
        .dup-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 2px;
        }
        .dup-table th, .dup-table td {
            border: 1px solid #000;
            padding: 2px;
            font-size: 8px;
        }
        .chave-acesso {
            font-size: 8px;
            font-weight: bold;
            letter-spacing: 0.5px;
            white-space: nowrap;
        }
        .ambiente {
            font-size: 8px;
            font-weight: bold;
        }
        .small {
            font-size: 7px;
        }
        .danfe-title {
            font-size: 13px;
            font-weight: bold;
        }
        .danfe-subtitle {
            font-size: 9px;
        }
        .tpnf-quadro {
            border: 1px solid #000;
            width: 20px;
            height: 20px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-size: 11px;
            margin-left: 8px;
        }
        .canhoto {
            border: 1px solid #000;
            padding: 3px;
            margin-bottom: 4px;
        }
        .canhoto-top {
            display: flex;
            flex-direction: row;
        }
        .canhoto-text {
            flex: 4;
            font-size: 8px;
            line-height: 1.2;
        }
        .canhoto-text strong {
            font-weight: bold;
        }
        .canhoto-nfe {
            flex: 1;
            border-left: 1px solid #000;
            text-align: center;
            font-size: 8px;
            padding-left: 4px;
        }
        .canhoto-nfe .titulo {
            font-size: 9px;
        }
        hr.corte {
            border: none;
            border-top: 1px dashed #000;
            margin: 3px 0;
        }
        .rodape {
            margin-top: 4px;
            font-size: 8px;
            text-align: right;
        }
    </style>
    """

    logo_html = ""
    if logo_url:
        logo_html = (
            f'<img src="{logo_url}" alt="Logo" '
            f'style="max-height:60px; max-width:120px; margin-right:4px;" />'
        )

    # ------ funções auxiliares para montar pedaços fixos do layout ------

    def _html_canhoto() -> str:
        return f"""
<div class="canhoto">
    <div class="canhoto-top">
        <div class="canhoto-text">
            <div>
                RECEBEMOS DE <strong>{emit_xnome}</strong> OS PRODUTOS CONSTANTES NA NOTA FISCAL INDICADA AO LADO.
                EMISSÃO: {data_emi_iso}  VALOR TOTAL R$ {v_nf}  DESTINATÁRIO: {dest_xnome}
            </div>
            <div style="margin-top:4px;">
                DATA DE RECEBIMENTO: ____/____/______ &nbsp;&nbsp;&nbsp;
                IDENTIFICAÇÃO E ASSINATURA DO RECEBEDOR
            </div>
        </div>
        <div class="canhoto-nfe">
            <div class="titulo">NF-e</div>
            <div class="conteudo small">
                Nº: {int(n_nf) if n_nf.isdigit() else n_nf}<br/>
                SÉRIE: {serie}
            </div>
        </div>
    </div>
</div>

<hr class="corte" />
"""

    def _html_fatura_dup() -> str:
        # até 6 parcelas, reservando espaço mesmo se não houver dados
        max_parc = 6
        cells = ""
        for i in range(max_parc):
            if i < len(duplicatas):
                d = duplicatas[i]
                cells += f"""
                    <td style="vertical-align:top;min-height:32px;">
                        <div>Nº: {d["nDup"]}</div>
                        <div>Venc: {d["dVenc"]}</div>
                        <div>Valor: {d["vDup"]}</div>
                    </td>
                """
            else:
                cells += """
                    <td style="vertical-align:top;min-height:32px;">
                        <div>&nbsp;</div>
                        <div>&nbsp;</div>
                        <div>&nbsp;</div>
                    </td>
                """

        return f"""
    <div class="linha">
        <div class="box" style="flex: 3;">
            <div class="titulo">FATURA/DUPLICATAS</div>
            <table class="dup-table">
                <tr>
                    {cells}
                </tr>
            </table>
        </div>
    </div>
"""

    def _html_cabecalho(num_folha: int, total_folhas: int, completo: bool) -> str:
        # Linha 1 – Emitente / DANFE / Chave
        h = f"""
<div class="danfe-container">
    <div class="linha">
        <div class="box" style="flex: 2.7;">
            <div class="titulo">IDENTIFICAÇÃO DO EMITENTE</div>
            <div class="conteudo">
                {logo_html}<strong>{emit_xnome}</strong>
            </div>
            <div class="conteudo">
                {emit_log}, {emit_nro} - {emit_bai}
            </div>
            <div class="conteudo">
                {emit_mun} - {emit_uf}  CEP: {emit_cep}  Fone: {emit_fone}
            </div>
            <div class="conteudo">
                CNPJ: {emit_cnpj}  IE: {emit_ie}
            </div>
            {"<div class='conteudo'>Nome Fantasia: " + emit_xfant + "</div>" if emit_xfant else ""}
        </div>

        <div class="box centro" style="flex: 0.8;">
            <div class="danfe-title">DANFE</div>
            <div class="danfe-subtitle">
                Documento Auxiliar da<br/>
                Nota Fiscal Eletrônica
            </div>
            <div class="conteudo ambiente" style="margin-top:2px;">{texto_ambiente}</div>

            <div class="conteudo small"
                 style="margin-top:6px;
                        display:flex;
                        justify-content:space-between;
                        align-items:flex-start;
                        padding:0 36px;">
                <div style="text-align:left;">
                    0 - ENTRADA<br/>
                    1 - SAÍDA
                </div>
                <div class="tpnf-quadro">{tp_nf}</div>
            </div>

            <div class="conteudo" style="margin-top:6px;">
                <strong>Nº: {int(n_nf) if n_nf.isdigit() else n_nf}</strong>
            </div>
            <div class="conteudo">
                <strong>SÉRIE: {serie} - FOLHA {num_folha}/{total_folhas}</strong>
            </div>
        </div>

        <div class="box centro" style="flex: 2.0;">
            <div class="titulo">CHAVE DE ACESSO</div>
            <div class="chave-acesso">{chave_formatada}</div>
            <div class="conteudo small">
                Consulte a autenticidade no portal nacional da NF-e em
                www.nfe.fazenda.gov.br/portal ou no site da SEFAZ Autorizadora.
            </div>
            {barcode_img_html}
            <div class="conteudo small">Protocolo: {protocolo}</div>
            <div class="conteudo small">Recebimento: {dh_prot}</div>
        </div>
    </div>
"""
        # Natureza da operação (sempre)
        h += f"""
    <div class="linha">
        <div class="box" style="flex: 3;">
            <div class="titulo">NATUREZA DA OPERAÇÃO</div>
            <div class="conteudo">{nat_op}</div>
        </div>
    </div>
"""

        if not completo:
            # Nas folhas seguintes paramos aqui
            return h

        # DESTINATÁRIO + datas (apenas na 1ª folha)
        h += f"""
    <div class="linha">
        <div class="box" style="flex: 3;">
            <div class="titulo">DESTINATÁRIO / REMETENTE</div>
            <div class="conteudo"><strong>{dest_xnome}</strong></div>
            <div class="conteudo">
                CNPJ/CPF: {dest_cnpj}  &nbsp;&nbsp; IE: {dest_ie}  &nbsp;&nbsp; IM: {dest_im}
            </div>
            <div class="conteudo">
                Endereço: {dest_log}, {dest_nro} - {dest_bai}
            </div>
            <div class="conteudo">
                Município: {dest_mun}  UF: {dest_uf}  CEP: {dest_cep}  Fone: {dest_fone}
            </div>
        </div>
        <div class="box" style="flex: 1; display:flex; flex-direction:column; justify-content:center;">
            <div class="titulo">DATA DE EMISSÃO</div>
            <div class="conteudo">{data_emi_br}</div>
            <div style="height:8px;"></div>
            <div class="titulo">DATA DE SAÍDA / ENTRADA</div>
            <div class="conteudo">{data_saida_br}</div>
        </div>
    </div>
"""

        # CÁLCULO DO IMPOSTO
        h += f"""
    <div class="linha">
        <div class="box" style="flex: 3;">
            <div class="titulo">CÁLCULO DO IMPOSTO</div>
            <div class="linha">
                <div class="box" style="flex:1;">
                    <div class="titulo">BASE DE CÁLCULO DO ICMS</div>
                    <div class="conteudo">{v_bc}</div>
                </div>
                <div class="box" style="flex:1;">
                    <div class="titulo">VALOR DO ICMS</div>
                    <div class="conteudo">{v_icms}</div>
                </div>
                <div class="box" style="flex:1;">
                    <div class="titulo">BASE CÁLC. ICMS SUBST.</div>
                    <div class="conteudo">{v_bc_st}</div>
                </div>
                <div class="box" style="flex:1;">
                    <div class="titulo">VALOR ICMS SUBST.</div>
                    <div class="conteudo">{v_st}</div>
                </div>
                <div class="box" style="flex:1;">
                    <div class="titulo">VALOR TOTAL DOS PRODUTOS</div>
                    <div class="conteudo">{v_prod}</div>
                </div>
            </div>
            <div class="linha">
                <div class="box" style="flex:1;">
                    <div class="titulo">VALOR DO FRETE</div>
                    <div class="conteudo">{v_frete}</div>
                </div>
                <div class="box" style="flex:1;">
                    <div class="titulo">VALOR DO SEGURO</div>
                    <div class="conteudo">{v_seg}</div>
                </div>
                <div class="box" style="flex:1;">
                    <div class="titulo">DESCONTO</div>
                    <div class="conteudo">{v_desc}</div>
                </div>
                <div class="box" style="flex:1;">
                    <div class="titulo">OUTRAS DESP. ACESSÓRIAS</div>
                    <div class="conteudo">{v_outro}</div>
                </div>
                <div class="box" style="flex:1;">
                    <div class="titulo">VALOR DO IPI</div>
                    <div class="conteudo">{v_ipi}</div>
                </div>
                <div class="box" style="flex:1.1;">
                    <div class="titulo">VALOR TOTAL DA NOTA</div>
                    <div class="conteudo"><strong>{v_nf}</strong></div>
                </div>
            </div>
            <div class="linha">
                <div class="box" style="flex: 1;">
                    <div class="titulo">VALOR APROX. TRIBUTOS (Lei 12.741/2012)</div>
                    <div class="conteudo">{v_tot_trib}</div>
                </div>
            </div>
        </div>
    </div>
"""

        # TRANSPORTADOR / VOLUMES
        h += f"""
    <div class="linha">
        <div class="box" style="flex: 3;">
            <div class="titulo">TRANSPORTADOR / VOLUMES TRANSPORTADOS</div>
            <div class="linha">
                <div class="box" style="flex:2;">
                    <div class="titulo">NOME/RAZÃO SOCIAL</div>
                    <div class="conteudo" style="min-height:14px;">{transp_nome}</div>
                </div>
                <div class="box" style="flex:1;">
                    <div class="titulo">FRETE POR CONTA</div>
                    <div class="conteudo" style="min-height:14px;">{mod_frete_desc}</div>
                </div>
                <div class="box" style="flex:1;">
                    <div class="titulo">CNPJ/CPF</div>
                    <div class="conteudo" style="min-height:14px;">{transp_cnpj}</div>
                </div>
                <div class="box" style="flex:1;">
                    <div class="titulo">INSCRIÇÃO ESTADUAL</div>
                    <div class="conteudo" style="min-height:14px;">{transp_ie}</div>
                </div>
            </div>
            <div class="linha">
                <div class="box" style="flex:2;">
                    <div class="titulo">ENDEREÇO</div>
                    <div class="conteudo" style="min-height:18px;">{transp_ender}</div>
                </div>
                <div class="box" style="flex:1;">
                    <div class="titulo">MUNICÍPIO</div>
                    <div class="conteudo" style="min-height:18px;">{transp_mun}</div>
                </div>
                <div class="box" style="flex:0.5;">
                    <div class="titulo">UF</div>
                    <div class="conteudo" style="min-height:18px;">{transp_uf}</div>
                </div>
                <div class="box" style="flex:0.8;">
                    <div class="titulo">QUANTIDADE</div>
                    <div class="conteudo" style="min-height:18px;">{vol_qtd}</div>
                </div>
                <div class="box" style="flex:0.8;">
                    <div class="titulo">PESO BRUTO</div>
                    <div class="conteudo" style="min-height:18px;">{vol_peso_b}</div>
                </div>
                <div class="box" style="flex:0.8;">
                    <div class="titulo">PESO LÍQUIDO</div>
                    <div class="conteudo" style="min-height:18px;">{vol_peso_l}</div>
                </div>
            </div>
        </div>
    </div>
"""

        # FATURA / DUPLICATAS (apenas na 1ª folha, logo depois do transportador)
        h += _html_fatura_dup()

        return h

    def _html_inf_compl_pagamento() -> str:
        altura = "80px"  # altura dos boxes

        return f"""
        <div class="linha" style="margin-top:6px;">
            <div class="box"
                 style="flex: 2;
                        min-height:{altura};
                        display:flex;
                        flex-direction:column;
                        justify-content:flex-start;">
                <div class="titulo" style="font-size:9px;">INFORMAÇÕES COMPLEMENTARES</div>
                <div class="conteudo" style="font-size:8px; margin-top:4px;">
                    {inf_cpl}
                </div>
            </div>
            <div class="box"
                 style="flex: 1;
                        min-height:{altura};
                        display:flex;
                        flex-direction:column;
                        justify-content:flex-start;">
                <div class="titulo" style="font-size:9px;">PAGAMENTO</div>
                <div class="conteudo" style="font-size:8px; margin-top:4px;">
                    Forma: {t_pag_desc}<br/>
                    Valor: {v_pag}
                </div>
            </div>
        </div>
    """

    def _html_inicio_tabela_itens() -> str:
        return """
    <div class="linha itens">
        <div class="box" style="flex: 3;">
            <div class="titulo">DADOS DOS PRODUTOS / SERVIÇOS</div>
            <table>
                <thead>
                    <tr>
                        <th>ITEM</th>
                        <th>CÓDIGO</th>
                        <th>DESCRIÇÃO DO PRODUTO / SERVIÇO</th>
                        <th>NCM/SH</th>
                        <th>EAN</th>
                        <th>CST/CSOSN</th>
                        <th>CFOP</th>
                        <th>UN</th>
                        <th>QTD</th>
                        <th>VLR UNIT.</th>
                        <th>VLR TOTAL</th>
                        <th>B.CÁLC. ICMS</th>
                        <th>VLR ICMS</th>
                        <th>ALÍQ. ICMS</th>
                    </tr>
                </thead>
                <tbody>
"""

    def _html_fim_tabela_itens() -> str:
        return """
                </tbody>
            </table>
        </div>
    </div>
"""

    # ---------- Montagem final do HTML ----------
    partes: List[str] = []
    partes.append(
        "<!DOCTYPE html>\n<html>\n<head>\n<meta charset='utf-8' />\n"
        f"<title>DANFE - NF-e {n_nf}</title>\n{css}\n</head>\n<body>\n"
    )

    for idx_pagina, itens_pagina in enumerate(pages_itens, start=1):
        partes.append('<div class="page">\n')

        primeira = idx_pagina == 1

        # Canhoto só na 1ª folha
        if primeira:
            partes.append(_html_canhoto())

        # Cabeçalho: completo na 1ª, reduzido nas demais (até natureza)
        partes.append(
            _html_cabecalho(
                num_folha=idx_pagina,
                total_folhas=total_paginas,
                completo=primeira,
            )
        )

        # Tabela de itens
        partes.append(_html_inicio_tabela_itens())

        max_itens_pag = MAX_ITENS_PRIMEIRA if primeira else MAX_ITENS_DEMAIS

        for it in itens_pagina:
            partes.append(
                f"""
                    <tr>
                        <td>{it["nItem"]}</td>
                        <td>{it["cProd"]}</td>
                        <td>{it["xProd"]}</td>
                        <td>{it["NCM"]}</td>
                        <td>{it["cEAN"]}</td>
                        <td>{it["CST_CSOSN"]}</td>
                        <td>{it["CFOP"]}</td>
                        <td>{it["uCom"]}</td>
                        <td class="direita">{it["qCom"]}</td>
                        <td class="direita">{it["vUnCom"]}</td>
                        <td class="direita">{it["vProd"]}</td>
                        <td class="direita">{it["vBC"]}</td>
                        <td class="direita">{it["vICMS"]}</td>
                        <td class="direita">{it["pICMS"]}</td>
                    </tr>
"""
            )

        linhas_vazias = max(0, max_itens_pag - len(itens_pagina))
        for _ in range(linhas_vazias):
            partes.append(
                """
                    <tr>
                        <td>&nbsp;</td>
                        <td>&nbsp;</td>
                        <td>&nbsp;</td>
                        <td>&nbsp;</td>
                        <td>&nbsp;</td>
                        <td>&nbsp;</td>
                        <td>&nbsp;</td>
                        <td>&nbsp;</td>
                        <td>&nbsp;</td>
                        <td>&nbsp;</td>
                        <td>&nbsp;</td>
                        <td>&nbsp;</td>
                        <td>&nbsp;</td>
                        <td>&nbsp;</td>
                    </tr>
"""
            )

        partes.append(_html_fim_tabela_itens())

        # INF. COMPLEMENTARES / PAGAMENTO só na 1ª folha e DEPOIS da tabela
        if primeira:
            partes.append(_html_inf_compl_pagamento())

        # Rodapé em todas as páginas
        partes.append(
            f"""
    <div class="rodape">
        SÉRIE: {serie} &nbsp;&nbsp; FOLHA {idx_pagina}/{total_paginas}
    </div>

</div> <!-- danfe-container -->
</div> <!-- page -->
"""
        )

    partes.append("</body>\n</html>\n")

    return "".join(partes)


def _format_inf_cpl(text: str) -> str:
    """
    Quebra o infCpl a cada ';' e volta como HTML com <br/>.
    Mantém o ';' no final de cada linha.
    """
    if not text:
        return ""

    partes = [p.strip() for p in text.split(";")]
    partes = [p for p in partes if p]  # remove vazias

    if not partes:
        return ""

    # junta de volta, recolocando ';' e quebra de linha
    return ";<br/>".join(partes)

