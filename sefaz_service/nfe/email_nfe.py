# sefaz_service/nfe/email_nfe.py

import os
import smtplib
from email.message import EmailMessage
from typing import Optional, List

import pdfkit
from dotenv import load_dotenv
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import EmailStr
from lxml import etree

from sefaz_service.danfe.danfe_html import nfe_xml_to_html
from sefaz_service.danfe.nfce_html import nfce_xml_to_html

load_dotenv()

router = APIRouter()

# -------------------------------------------------------------------
# CONFIG PDFKIT / WKHTMLTOPDF
# -------------------------------------------------------------------

WKHTMLTOPDF_PATH = os.getenv(
    "WKHTMLTOPDF_PATH",
    r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe",  # padrão Windows
)

pdfkit_config = pdfkit.configuration(wkhtmltopdf=WKHTMLTOPDF_PATH)

NFE_NS = "http://www.portalfiscal.inf.br/nfe"


def _q(tag: str) -> str:
    return f"{{{NFE_NS}}}{tag}"


# -------------------------------------------------------------------
# HELPERS
# -------------------------------------------------------------------

def html_to_pdf_bytes(html: str) -> bytes:
    """
    Converte HTML em PDF (bytes) usando pdfkit/wkhtmltopdf.
    """
    try:
        pdf_bytes = pdfkit.from_string(
            html,
            False,  # False = retorna bytes em memória
            configuration=pdfkit_config,
            options={
                "enable-local-file-access": None,
            },
        )
        return pdf_bytes
    except Exception as exc:
        raise RuntimeError(f"Erro gerando PDF a partir do HTML: {exc}") from exc


def parse_nfe_basic_info(xml_bytes: bytes) -> dict:
    """
    Extrai informações básicas da NFe a partir do XML:
    - xFant, xNome, CNPJ emitente
    - série, número, destinatário, CNPJ/CPF, valor, chave de acesso
    """
    try:
        parser = etree.XMLParser(remove_blank_text=False, recover=True)
        root = etree.fromstring(xml_bytes, parser=parser)
    except Exception as exc:
        raise RuntimeError(f"XML inválido para leitura de dados da NF-e: {exc}") from exc

    inf_nfe = root.find(f".//{_q('infNFe')}")
    if inf_nfe is None:
        raise RuntimeError("Não foi encontrado o nó <infNFe> no XML.")

    # Chave de acesso
    chave = inf_nfe.get("Id") or ""
    if chave.upper().startswith("NFE"):
        chave = chave[3:]

    # IDE
    ide_el = inf_nfe.find(_q("ide"))
    serie = ide_el.findtext(_q("serie"), default="") if ide_el is not None else ""
    nNF = ide_el.findtext(_q("nNF"), default="") if ide_el is not None else ""

    # Emitente
    emit_el = inf_nfe.find(_q("emit"))
    emit_xFant = emit_el.findtext(_q("xFant"), default="") if emit_el is not None else ""
    emit_xNome = emit_el.findtext(_q("xNome"), default="") if emit_el is not None else ""
    emit_CNPJ = ""
    if emit_el is not None:
        emit_CNPJ = (
            emit_el.findtext(_q("CNPJ"))
            or emit_el.findtext(_q("CPF"))
            or ""
        )

    # Destinatário
    dest_el = inf_nfe.find(_q("dest"))
    dest_xNome = dest_el.findtext(_q("xNome"), default="") if dest_el is not None else ""
    dest_CNPJ = ""
    if dest_el is not None:
        dest_CNPJ = (
            dest_el.findtext(_q("CNPJ"))
            or dest_el.findtext(_q("CPF"))
            or ""
        )

    # Totais (vNF)
    total_el = inf_nfe.find(_q("total"))
    vNF = ""
    if total_el is not None:
        icmstot_el = total_el.find(_q("ICMSTot"))
        if icmstot_el is not None:
            vNF = icmstot_el.findtext(_q("vNF"), default="")

    return {
        "emit_xFant": emit_xFant,
        "emit_xNome": emit_xNome,
        "emit_CNPJ": emit_CNPJ,
        "serie": serie,
        "nNF": nNF,
        "dest_xNome": dest_xNome,
        "dest_CNPJ": dest_CNPJ,
        "vNF": vNF,
        "chave": chave,
    }


def build_html_email_body(info: dict, mensagem_extra: Optional[str] = None) -> str:
    """
    Monta o corpo HTML no mesmo padrão do Harbour.
    """
    xf = info.get("emit_xFant", "") or info.get("emit_xNome", "")
    xn = info.get("emit_xNome", "")
    cnpj_emit = info.get("emit_CNPJ", "")
    serie = info.get("serie", "")
    nnf = info.get("nNF", "")
    dest_nome = info.get("dest_xNome", "")
    dest_cnpj = info.get("dest_CNPJ", "")
    vnf = info.get("vNF", "")
    chave = info.get("chave", "")

    # Formata número da NF (9 dígitos com zero à esquerda)
    try:
        nnf_int = int(nnf)
        nnf_fmt = f"{nnf_int:09d}"
    except Exception:
        nnf_fmt = nnf

    # Valor formatado R$ 999.999,99 (bem simples)
    vnf_fmt = vnf.replace(".", ",") if vnf else ""

    mensagem_html = ""
    if mensagem_extra:
        mensagem_html = f"<p>{mensagem_extra}</p>"

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{xf} - Nota Fiscal Eletrônica</title>
    <style>
        body {{ font-family: Arial, sans-serif; color: #333; }}
        .container {{
            width: 100%;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f9f9f9;
            border: 1px solid #ddd;
            border-radius: 8px;
        }}
        .block {{
            padding: 15px;
            background-color: #fff;
            border: 1px solid #ccc;
            border-radius: 8px;
            margin-bottom: 20px;
        }}
        h1 {{ font-size: 18px; color: #0056b3; }}
        p {{ margin: 10px 0; }}
        strong {{ color: #000; }}
        footer {{
            font-size: 12px;
            color: #777;
            margin-top: 20px;
            text-align: center;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="block">
            <h1>NF-e - Nota Fiscal Eletrônica</h1>
            {mensagem_html}
        </div>
        <div class="block">
            <h1>Emitida por:</h1>
            <p>
                <strong>Nome Fantasia:</strong> {xf}<br>
                <strong>Razão Social:</strong> {xn}<br>
                <strong>CPF/CNPJ:</strong> {cnpj_emit}
            </p>
        </div>
        <div class="block">
            <h1>Destinatário:</h1>
            <p><strong>Nota Fiscal Eletrônica Nr.:</strong> {serie}/{nnf_fmt}</p>
            <p><strong>Nome:</strong> {dest_nome}</p>
            <p><strong>CPF/CNPJ:</strong> {dest_cnpj}</p>
            <p><strong>Valor:</strong> R$ {vnf_fmt}</p>
            <p><strong>Chave de Acesso:</strong> {chave}</p>
        </div>
        <footer>
            <em>Obs: E-mail enviado automaticamente por <strong>SGC Sistemas</strong>, por favor, não responda.</em>
        </footer>
    </div>
</body>
</html>
"""
    return html


def send_email_with_attachments(
    to_email: str,
    subject: str,
    body_html: str,
    attachments: List[tuple[str, bytes, str]],
):
    """
    Envia e-mail usando SMTP com anexos.

    attachments: lista de tuplas (nome_arquivo, conteudo_bytes, mimetype)
    """
    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")
    use_tls = os.getenv("SMTP_USE_TLS", "true").lower() == "true"

    if not host or not user or not password:
        raise RuntimeError("Configuração SMTP não encontrada nas variáveis de ambiente.")

    msg = EmailMessage()
    msg["From"] = user
    msg["To"] = to_email
    msg["Subject"] = subject

    # Texto simples (fallback) + HTML principal
    msg.set_content("Segue em anexo o documento fiscal eletrônico (XML e PDF).")
    msg.add_alternative(body_html, subtype="html")

    for filename, content, mimetype in attachments:
        maintype, subtype = mimetype.split("/", 1)
        msg.add_attachment(
            content,
            maintype=maintype,
            subtype=subtype,
            filename=filename,
        )

    with smtplib.SMTP(host, port) as smtp:
        if use_tls:
            smtp.starttls()
        smtp.login(user, password)
        smtp.send_message(msg)


# -------------------------------------------------------------------
# ROTA
# -------------------------------------------------------------------

@router.post("/enviar-email")
async def enviar_email_nfe(
    destinatario: EmailStr = Form(...),
    assunto: Optional[str] = Form("Documento fiscal eletrônico"),
    mensagem: Optional[str] = Form("Segue em anexo o XML e o PDF."),
    modelo: int = Form(55),  # 55 = NFe, 65 = NFCe
    xml_file: UploadFile = File(...),
):
    """
    Recebe um XML de NFe/NFCe, gera o PDF (DANFE) a partir do HTML
    e envia por e-mail o XML + PDF anexados.
    """

    xml_bytes = await xml_file.read()
    if not xml_bytes:
        raise HTTPException(status_code=400, detail="Arquivo XML vazio.")

    # Extrai informações básicas para montar assunto/corpo HTML
    try:
        info = parse_nfe_basic_info(xml_bytes)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Erro lendo dados básicos da NF-e para o corpo do e-mail: {exc}",
        )

    # Se o assunto for o padrão, monta igual ao Harbour
    xf = info.get("emit_xFant") or info.get("emit_xNome") or ""
    if assunto == "Documento fiscal eletrônico" and xf:
        assunto_final = f"{xf} - NOTA FISCAL ELETRÔNICA NF-e"
    else:
        assunto_final = assunto or "Documento fiscal eletrônico"

    # Gera HTML (DANFE) a partir do XML
    try:
        if modelo == 55:
            html_danfe = nfe_xml_to_html(xml_bytes)
            pdf_name = "danfe_nfe.pdf"
        elif modelo == 65:
            html_danfe = nfce_xml_to_html(xml_bytes)
            pdf_name = "danfe_nfce.pdf"
        else:
            raise HTTPException(
                status_code=400,
                detail="Modelo inválido. Use 55 para NFe ou 65 para NFCe.",
            )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Erro gerando HTML da DANFE: {exc}",
        )

    # Converte HTML em PDF
    try:
        pdf_bytes = html_to_pdf_bytes(html_danfe)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )

    # Monta corpo HTML do e-mail (igual ao Harbour)
    body_html = build_html_email_body(info, mensagem_extra=mensagem)

    # Monta anexos: XML + PDF
    attachments = [
        (xml_file.filename or "nfe.xml", xml_bytes, "application/xml"),
        (pdf_name, pdf_bytes, "application/pdf"),
    ]

    # Envia o e-mail
    try:
        send_email_with_attachments(
            to_email=destinatario,
            subject=assunto_final,
            body_html=body_html,
            attachments=attachments,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Erro enviando e-mail: {exc}",
        )

    return {"ok": True, "message": "E-mail enviado com sucesso."}
