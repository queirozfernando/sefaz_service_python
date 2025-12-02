# sefaz_service/core/nfe_autorizado.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from lxml import etree

NFE_NS = "http://www.portalfiscal.inf.br/nfe"


@dataclass
class NFeAutorizadoResult:
    """
    Resultado da geração do nfeProc:

      - autorizado: True se cStat em [100, 101, 150]
      - status: cStat como int (ou None)
      - motivo: xMotivo

      - xml_nfe_proc: XML final do <nfeProc> (NFe + protNFe), se autorizado
      - xml_protocolo_ajustado: XML do protocolo com infProt Id="ID{nProt}" (se ajustado)
    """
    autorizado: bool
    status: Optional[int]
    motivo: Optional[str]
    xml_nfe_proc: Optional[str]
    xml_protocolo_ajustado: str


def _ajustar_infprot_id(xml_protocolo: str) -> Tuple[str, Optional[str], Optional[str]]:
    """
    Adiciona Id="ID{nProt}" em <infProt>, se existir nProt
    e retorna:
      - xml_protocolo_ajustado
      - cStat (como string)
      - xMotivo
    """
    root = etree.fromstring(xml_protocolo.encode("utf-8"))
    ns = {"nfe": NFE_NS}

    # 1) Tentar achar <infProt> com namespace
    inf_prot = root.find(".//nfe:infProt", namespaces=ns)

    # 2) Se não achar, fallback: ignorar namespace com xpath
    if inf_prot is None:
        # xpath suporta local-name(), diferente de .find()
        inf_list = root.xpath("//*[local-name()='infProt']")
        if inf_list:
            inf_prot = inf_list[0]

    c_stat_str: Optional[str] = None
    x_motivo: Optional[str] = None

    if inf_prot is not None:
        # nProt com ou sem namespace
        n_prot = (
            inf_prot.findtext("nfe:nProt", namespaces=ns)
            or inf_prot.findtext("nProt")
        )
        if n_prot:
            if not inf_prot.get("Id"):
                inf_prot.set("Id", f"ID{n_prot}")

        # cStat
        c_stat_str = (
            inf_prot.findtext("nfe:cStat", namespaces=ns)
            or inf_prot.findtext("cStat")
        )
        if c_stat_str:
            c_stat_str = c_stat_str.strip()

        # xMotivo
        x_motivo = (
            inf_prot.findtext("nfe:xMotivo", namespaces=ns)
            or inf_prot.findtext("xMotivo")
        )
        if x_motivo:
            x_motivo = x_motivo.strip()
    else:
        # Não achou infProt – tenta pegar cStat/xMotivo direto do root
        c_stat_str = (
            root.findtext(".//nfe:cStat", namespaces=ns)
            or root.findtext(".//cStat")
        )
        if c_stat_str:
            c_stat_str = c_stat_str.strip()

        x_motivo = (
            root.findtext(".//nfe:xMotivo", namespaces=ns)
            or root.findtext(".//xMotivo")
        )
        if x_motivo:
            x_motivo = x_motivo.strip()

    xml_prot_ajustado = etree.tostring(
        root, encoding="utf-8", xml_declaration=True
    ).decode("utf-8")

    return xml_prot_ajustado, c_stat_str, x_motivo


def sefaz_nfe_gera_autorizado(
    xml_assinado: str,
    xml_protocolo: str,
    *,
    versao: str = "4.00",
) -> NFeAutorizadoResult:
    """
    Equivalente em Python de ze_sefaz_NFeGeraAutorizado():

      - Ajusta <infProt Id="ID{nProt}">, se houver nProt.
      - Lê cStat/xMotivo.
      - Se autorizado (100, 101, 150), monta <nfeProc> contendo:
          <NFe> (xml_assinado) + <protNFe> (do protocolo).

    Retorna NFeAutorizadoResult.
    """
    xml_prot_ajustado, c_stat_str, x_motivo = _ajustar_infprot_id(xml_protocolo)

    status_int: Optional[int] = None
    autorizado = False

    if c_stat_str and c_stat_str.isdigit():
        status_int = int(c_stat_str)
        if status_int in (100, 101, 150):
            autorizado = True

    xml_nfe_proc: Optional[str] = None

    if autorizado:
        # Extrai apenas o nó <protNFe> do XML de protocolo
        root_prot = etree.fromstring(xml_prot_ajustado.encode("utf-8"))
        ns = {"nfe": NFE_NS}

        prot_nfe_el = root_prot.find(".//nfe:protNFe", namespaces=ns)
        if prot_nfe_el is None:
            # ignorando namespace
            prot_list = root_prot.xpath("//*[local-name()='protNFe']")
            prot_nfe_el = prot_list[0] if prot_list else None

        if prot_nfe_el is not None:
            prot_nfe_xml = etree.tostring(
                prot_nfe_el, encoding="utf-8", xml_declaration=False
            ).decode("utf-8")
        else:
            # se não achar, usamos o protocolo inteiro mesmo
            prot_nfe_xml = xml_prot_ajustado

        # Monta <nfeProc>
        xml_assinado_sem_decl = xml_assinado.lstrip()
        if xml_assinado_sem_decl.startswith("<?xml"):
            fim = xml_assinado_sem_decl.find("?>")
            if fim != -1:
                xml_assinado_sem_decl = xml_assinado_sem_decl[fim + 2 :].lstrip()

        xml_nfe_proc = (
            f'<?xml version="1.0" encoding="UTF-8"?>'
            f'<nfeProc versao="{versao}" xmlns="{NFE_NS}">'
            f"{xml_assinado_sem_decl}"
            f"{prot_nfe_xml}"
            f"</nfeProc>"
        )

    return NFeAutorizadoResult(
        autorizado=autorizado,
        status=status_int,
        motivo=x_motivo,
        xml_nfe_proc=xml_nfe_proc,
        xml_protocolo_ajustado=xml_prot_ajustado,
    )
