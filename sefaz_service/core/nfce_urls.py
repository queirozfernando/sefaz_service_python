# sefaz_service/core/nfce_urls.py
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class UrlConfig:
    uf: str        # UF (AC, SP, PR...) ou códigos como SVRS, **
    tipo: str      # ex.: "4.00H", "4.00P", "2.00H", "2.00P"
    url: str


# --- NFC-e: URLs de QRCode (equivalente ao WS_NFE_QRCODE) ---

NFE_QRCODE_LIST: List[UrlConfig] = [
    # 3.10 (PR, SE)
    UrlConfig("PR", "3.10H", "http://www.dfeportal.fazenda.pr.gov.br/dfe-portal/rest/servico/consultaNFCe"),
    UrlConfig("SE", "3.10H", "http://www.hom.nfe.se.gov.br/portal/consultarNFCe.jsp"),

    UrlConfig("PR", "3.10P", "http://www.dfeportal.fazenda.pr.gov.br/dfe-portal/rest/servico/consultaNFCe"),
    UrlConfig("SE", "3.10P", "http://www.nfce.se.gov.br/portal/consultarNFCe.jsp"),
    UrlConfig("SP", "3.10P", "https://www.nfce.fazenda.sp.gov.br/NFCeConsultaPublica/Paginas/ConsultaQRCode.aspx"),

    # 4.00 – Homologação (H)
    UrlConfig("AC", "4.00H", "http://www.hml.sefaznet.ac.gov.br/nfce/qrcode"),
    UrlConfig("AL", "4.00H", "http://nfce.sefaz.al.gov.br/QRCode/consultarNFCe.jsp"),
    UrlConfig("AM", "4.00H", "http://homnfce.sefaz.am.gov.br/nfceweb/consultarNFCe.jsp"),
    UrlConfig("AP", "4.00H", "https://www.sefaz.ap.gov.br/nfcehml/nfce.php"),
    UrlConfig("BA", "4.00H", "http://hnfe.sefaz.ba.gov.br/servicos/nfce/modulos/geral/NFCEC_consulta_chave_acesso.aspx"),
    UrlConfig("CE", "4.00H", "http://nfceh.sefaz.ce.gov.br/pages/ShowNFCe.html"),
    UrlConfig("DF", "4.00H", "http://dec.fazenda.df.gov.br/ConsultarNFCe.aspx"),
    UrlConfig("ES", "4.00H", "http://homologacao.sefaz.es.gov.br/ConsultaNFCe/qrcode.aspx"),
    UrlConfig("GO", "4.00H", "https://nfewebhomolog.sefaz.go.gov.br/nfeweb/sites/nfce/danfeNFCe"),
    UrlConfig("MA", "4.00H", "http://homologacao.sefaz.ma.gov.br/portal/consultarNFCe.jsp"),
    UrlConfig("MG", "4.00H", "https://portalsped.fazenda.mg.gov.br/portalnfce/sistema/qrcode.xhtml"),
    UrlConfig("MS", "4.00H", "http://www.dfe.ms.gov.br/nfce/qrcode"),
    UrlConfig("MT", "4.00H", "http://homologacao.sefaz.mt.gov.br/nfce/consultanfce"),
    UrlConfig("PA", "4.00H", "https://appnfc.sefa.pa.gov.br/portal-homologacao/view/consultas/nfce/nfceForm.seam"),
    UrlConfig("PB", "4.00H", "http://www.receita.pb.gov.br/nfcehom"),
    UrlConfig("PR", "4.00H", "http://www.fazenda.pr.gov.br/nfce/qrcode"),
    UrlConfig("PE", "4.00H", "http://nfcehomolog.sefaz.pe.gov.br/nfce/consulta"),
    UrlConfig("PI", "4.00H", "http://webas.sefaz.pi.gov.br/nfceweb-homologacao/consultarNFCe.jsf"),
    UrlConfig("RJ", "4.00H", "http://www4.fazenda.rj.gov.br/consultaNFCe/QRCode"),
    UrlConfig("RN", "4.00H", "http://hom.nfce.set.rn.gov.br/consultarNFCe.aspx"),
    UrlConfig("RO", "4.00H", "http://www.nfce.sefin.ro.gov.br/consultanfce/consulta.jsp"),
    UrlConfig("RR", "4.00H", "https://www.sefaz.rr.gov.br/nfce/servlet/wp_consulta_nfce"),
    UrlConfig("RS", "4.00H", "https://www.sefaz.rs.gov.br/NFCE/NFCE-COM.aspx"),
    UrlConfig("SP", "4.00H", "https://www.homologacao.nfce.fazenda.sp.gov.br/NFCeConsultaPublica/Paginas/ConsultaQRCode.aspx"),
    UrlConfig("TO", "4.00H", "http://apps.sefaz.to.gov.br/portal-nfce-homologacao/qrcodeNFCe"),

    # 4.00 – Produção (P)
    UrlConfig("AC", "4.00P", "http://www.sefaznet.ac.gov.br/nfce/qrcode"),
    UrlConfig("AL", "4.00P", "http://nfce.sefaz.al.gov.br/QRCode/consultarNFCe.jsp"),
    UrlConfig("BA", "4.00P", "http://nfe.sefaz.ba.gov.br/servicos/nfce/modulos/geral/NFCEC_consulta_chave_acesso.aspx"),
    UrlConfig("CE", "4.00H", "http://nfce.sefaz.ce.gov.br/pages/ShowNFCe.html"),  # igual ao macro
    UrlConfig("DF", "4.00P", "http://dec.fazenda.df.gov.br/ConsultarNFCe.aspx"),
    UrlConfig("GO", "4.00P", "https://nfeweb.sefaz.go.gov.br/nfeweb/sites/nfce/danfeNFCe"),
    UrlConfig("MA", "4.00P", "http://www.nfce.sefaz.ma.gov.br/portal/consultarNFCe.jsp"),
    UrlConfig("MG", "4.00P", "https://portalsped.fazenda.mg.gov.br/portalnfce/sistema/qrcode.xhtml"),
    UrlConfig("MS", "4.00P", "http://www.dfe.ms.gov.br/nfce/qrcode"),
    UrlConfig("MT", "4.00P", "http://www.sefaz.mt.gov.br/nfce/consultanfce"),
    UrlConfig("PA", "4.00P", "https://appnfc.sefa.pa.gov.br/portal/view/consultas/nfce/nfceForm.seam"),
    UrlConfig("PB", "4.00P", "http://www.receita.pb.gov.br/nfce"),
    UrlConfig("PE", "4.00P", "http://nfce.sefaz.pe.gov.br/nfce-web/consultarNFCe"),
    UrlConfig("PI", "4.00P", "http://webas.sefaz.pi.gov.br/nfceweb/consultarNFCe.jsf"),
    UrlConfig("PR", "4.00P", "http://www.fazenda.pr.gov.br/nfce/qrcode"),
    UrlConfig("RJ", "4.00P", "http://www4.fazenda.rj.gov.br/consultaNFCe/QRCode"),
    UrlConfig("RN", "4.00P", "http://nfce.set.rn.gov.br/consultarNFCe.aspx"),
    UrlConfig("RS", "4.00P", "https://www.sefaz.rs.gov.br/NFCE/NFCE-COM.aspx"),
    UrlConfig("RO", "4.00P", "http://www.nfce.sefin.ro.gov.br/consultanfce/consulta.jsp"),
    UrlConfig("RR", "4.00P", "https://www.sefaz.rr.gov.br/nfce/servlet/qrcode"),
    UrlConfig("SE", "4.00P", "http://www.nfe.se.gov.br/portal/consultarNFCe.jsp"),
    UrlConfig("SP", "4.00P", "https://www.nfce.fazenda.sp.gov.br/NFCeConsultaPublica/Paginas/ConsultaQRCode.aspx"),
    UrlConfig("TO", "4.00P", "http://apps.sefaz.to.gov.br/portal-nce/qrcodeNFCe"),
]


# --- NFC-e: URLs de consulta pela chave (equivalente a WS_NFE_CHAVE) ---

NFE_CHAVE_LIST: List[UrlConfig] = [
    # 2.00 – Homologação
    UrlConfig("AC", "2.00H", "http://www.sefaznet.ac.gov.br/nfce/consulta"),
    UrlConfig("AL", "2.00H", "http://www.sefaz.al.gov.br/nfce/consulta"),
    UrlConfig("AM", "2.00H", "http://www.sefaz.am.gov.br/nfce/consulta"),
    UrlConfig("AP", "2.00H", "https://www.sefaz.ap.gov.br/nfce/consulta"),
    UrlConfig("BA", "2.00H", "http://hinternet.sefaz.ba.gov.br/nfce/consulta"),
    UrlConfig("CE", "2.00H", "http://www.sefaz.ce.gov.br/nfce/consulta"),
    UrlConfig("DF", "2.00H", "http://www.fazenda.df.gov.br/nfce/consulta"),
    UrlConfig("ES", "2.00H", "http://www.sefaz.es.gov.br/nfce/consulta"),
    UrlConfig("GO", "2.00H", "http://www.sefaz.go.gov.br/nfce/consulta"),
    UrlConfig("MA", "2.00H", "http://www.sefaz.ma.gov.br/nfce/consulta"),
    UrlConfig("MG", "2.00H", " https://hportalsped.fazenda.mg.gov.br/portalnfce"),
    UrlConfig("MS", "2.00H", "http://www.dfe.ms.gov.br/nfce/consulta"),
    UrlConfig("MT", "2.00H", "http://www.sefaz.mt.gov.br/nfce/consultanfce"),
    UrlConfig("PA", "2.00H", "http://www.sefa.pa.gov.br/nfce/consulta"),
    UrlConfig("PE", "2.00H", "http://nfce.sefaz.pe.gov.br/nfce/consulta"),
    UrlConfig("PI", "2.00H", "http://www.sefaz.pi.gov.br/nfce/consulta"),
    UrlConfig("PR", "2.00H", "http://www.fazenda.pr.gov.br/nfce/consulta"),
    UrlConfig("RJ", "2.00H", "http://www.fazenda.rj.gov.br/nfce/consulta"),
    UrlConfig("RR", "2.00H", "http://www.sefaz.rr.gov.br/nfce/consulta"),
    UrlConfig("RS", "2.00H", "http://www.sefaz.rs.gov.br/nfce/consulta"),
    UrlConfig("SP", "2.00H", "https://www.homologacao.nfce.fazenda.sp.gov.br/consulta"),

    # 2.00 – Produção
    UrlConfig("AC", "2.00P", "http://www.sefaznet.ac.gov.br/nfce/consulta"),
    UrlConfig("AL", "2.00P", "http://www.sefaz.al.gov.br/nfce/consulta"),
    UrlConfig("AM", "2.00P", "http://www.sefaz.am.gov.br/nfce/consulta"),
    UrlConfig("AP", "2.00P", "https://www.sefaz.ap.gov.br/nfce/consulta"),
    UrlConfig("BA", "2.00P", "http://www.sefaz.ba.gov.br/nfce/consulta"),
    UrlConfig("CE", "2.00P", "http://www.sefaz.ce.gov.br/nfce/consulta"),
    UrlConfig("DF", "2.00P", "http://www.fazenda.df.gov.br/nfce/consulta"),
    UrlConfig("GO", "2.00P", "http://www.sefaz.go.gov.br/nfce/consulta"),
    UrlConfig("MA", "2.00P", "http://www.sefaz.ma.gov.br/nfce/consulta"),
    UrlConfig("MG", "2.00P", "http://portalsped.fazenda.mg.gov.br/portalnfce"),
    UrlConfig("MS", "2.00P", "http://www.dfe.ms.gov.br/nfce/consulta"),
    UrlConfig("MT", "2.00P", "http://www.sefaz.mt.gov.br/nfce/consultanfce"),
    UrlConfig("PA", "2.00P", "http://www.sefa.pa.gov.br/nfce/consulta"),
    UrlConfig("PE", "2.00P", "http://nfce.sefaz.pe.gov.br/nfce/consulta"),
    UrlConfig("PI", "2.00P", "http://www.sefaz.pi.gov.br/nfce/consulta"),
    UrlConfig("PR", "2.00P", "http://www.fazenda.pr.gov.br/nfce/consulta"),
    UrlConfig("RJ", "2.00P", "http://www.fazenda.rj.gov.br/nfce/consulta"),
    UrlConfig("RR", "2.00P", "http://www.sefaz.rr.gov.br/nfce/consulta"),
    UrlConfig("RS", "2.00P", "http://www.sefaz.rs.gov.br/nfce/consulta"),
    UrlConfig("SP", "2.00P", "https://www.nfce.fazenda.sp.gov.br/consulta"),
]


def _normalizar_ambiente(ambiente: str) -> str:
    ambiente = ambiente.strip().upper()
    if ambiente in ("H", "HOMOLOGACAO", "HOMOLOGAÇÃO", "2"):
        return "H"
    if ambiente in ("P", "PRODUCAO", "PRODUÇÃO", "1"):
        return "P"
    return "P"


def _buscar_url(configs: List[UrlConfig], uf: str, tipo: str) -> Optional[str]:
    uf = uf.strip().upper()
    for cfg in configs:
        if cfg.uf == uf and cfg.tipo == tipo:
            return cfg.url
    return None


def resolver_url_qrcode_nfce(
    uf: str,
    ambiente: str,
    versao_layout: str = "4.00",
) -> str:
    """
    Devolve a URL base do QRCode da NFC-e (equivalente a WS_NFE_QRCODE).

    versao_layout normalmente "4.00".
    """
    amb = _normalizar_ambiente(ambiente)
    tipo = f"{versao_layout}{amb}"

    url = _buscar_url(NFE_QRCODE_LIST, uf, tipo)
    if not url:
        raise ValueError(f"Nenhuma URL de QRCode NFC-e encontrada para UF={uf}, tipo={tipo}")
    return url


def resolver_url_chave_nfce(
    uf: str,
    ambiente: str,
    versao_chave: str = "2.00",
) -> str:
    """
    Devolve a URL de consulta pela chave da NFC-e (equivalente a WS_NFE_CHAVE).

    versao_chave normalmente "2.00".
    """
    amb = _normalizar_ambiente(ambiente)
    tipo = f"{versao_chave}{amb}"

    url = _buscar_url(NFE_CHAVE_LIST, uf, tipo)
    if not url:
        raise ValueError(f"Nenhuma URL de consulta NFC-e encontrada para UF={uf}, tipo={tipo}")
    return url
