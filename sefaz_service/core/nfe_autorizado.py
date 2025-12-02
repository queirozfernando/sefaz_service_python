# sefaz_service/core/nfe_autorizado.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from lxml import etree

from .assinatura import NFE_NS


@dataclass
class NFeAutorizadoResult:
    """
    Resultado da geração do XML autorizado (nfeProc) e do protocolo.

    - autorizado:
        True se cStat em [100, 101, 150] (autorizada/denegada/cancelada com protNFe válido)
    - status:
        cStat retornado pela SEFAZ (ou None se não encontrado)
    - motivo:
        xMotivo retornado pela SEFAZ (ou None)
    - xml_nfe_proc:
        XML do <nfeProc> (NFe + protNFe), se houve <protNFe> válido; caso contrário, None.
    - xml_protocolo_ajustado:
        XML de <protNFe> com ajuste em infProt/Id (Id="ID{nProt}"), se encontrado.
        Se não houver <protNFe>, retorna o xml_protocolo original.
    """
    autorizado: bool
    status: Optional[int]
    motivo: Optional[str]
    xml_nfe_proc: Optional[str]
    xml_protocolo_ajustado: str


def _extrair_status_motivo(xml: str) -> tuple[Optional[int], Optional[str]]:
    """
    Extrai cStat e xMotivo de qualquer XML de retorno da SEFAZ
    (retEnviNFe, retConsReciNFe, retConsSitNFe, etc).
    """
    try:
        root = etree.fromstring(xml.encode("utf-8"))
    except Exception:
        return None, None

    # Não usamos namespace aqui porque alguns retornos não vêm com o NFE_NS,
    # ou vêm com prefixo diferente. Buscamos por nome local.
    cstat_el = root.find(".//cStat")
    xmot_el = root.find(".//xMotivo")

    status: Optional[int] = None
    motivo: Optional[str] = None

    if cstat_el is not None and (cstat_el.text or "").strip():
        try:
            status = int(cstat_el.text.strip())
        except ValueError:
            status = None

    if xmot_el is not None and (xmot_el.text or "").strip():
        motivo = xmot_el.text.strip()

    return status, motivo


def sefaz_nfe_gera_autorizado(
    xml_assinado: str,
    xml_protocolo: str,
    versao: str = "4.00",
) -> NFeAutorizadoResult:
    """
    Gera o XML autorizado (nfeProc) a partir de:

      - xml_assinado : XML da NFe assinada (<NFe>...</NFe>)
      - xml_protocolo: XML de retorno da SEFAZ (retEnviNFe, retConsReciNFe,
                       retConsSitNFe ou mesmo um <protNFe> isolado).

    Passos:

      1) Extrai cStat e xMotivo do XML de protocolo.
      2) Procura <protNFe>. Se não encontrar, retorna sem nfeProc.
      3) Ajusta infProt/Id para o formato "ID{nProt}".
      4) Monta:

         <nfeProc versao="4.00" xmlns="http://www.portalfiscal.inf.br/nfe">
           <NFe>...</NFe>
           <protNFe>...</protNFe>
         </nfeProc>

    Obs: este XML NÃO é enviado à SEFAZ; é apenas para armazenamento e DANFE.
    """

    status, motivo = _extrair_status_motivo(xml_protocolo)

    # Consideramos "autorizado" quando há status que representem
    # autorização ou situação com protocolo vinculável.
    # (ajuste conforme sua regra de negócio)
    autorizado = status in (100, 101, 150)

    parser = etree.XMLParser(remove_blank_text=True)

    # Parse da NFe assinada
    try:
        nfe_root = etree.fromstring(xml_assinado.encode("utf-8"), parser=parser)
    except Exception:
        # Se der erro aqui, não tem como gerar nfeProc
        return NFeAutorizadoResult(
            autorizado=False,
            status=status,
            motivo=motivo,
            xml_nfe_proc=None,
            xml_protocolo_ajustado=xml_protocolo,
        )

    # Parse do XML de protocolo (retEnviNFe / retConsReciNFe / retConsSitNFe / protNFe)
    try:
        proto_root = etree.fromstring(xml_protocolo.encode("utf-8"), parser=parser)
    except Exception:
        return NFeAutorizadoResult(
            autorizado=False,
            status=status,
            motivo=motivo,
            xml_nfe_proc=None,
            xml_protocolo_ajustado=xml_protocolo,
        )

    ns = {"nfe": NFE_NS}

    # Pode ser que o root já seja <protNFe>, ou que esteja dentro de retEnviNFe / retConsReciNFe etc.
    if proto_root.tag.endswith("protNFe"):
        prot_el = proto_root
    else:
        prot_el = proto_root.find(".//nfe:protNFe", ns)

    if prot_el is None:
        # Não há protocolo, então não há nfeProc. Mas devolvemos status/motivo.
        return NFeAutorizadoResult(
            autorizado=autorizado,
            status=status,
            motivo=motivo,
            xml_nfe_proc=None,
            xml_protocolo_ajustado=xml_protocolo,
        )

    # Fazemos uma cópia de protNFe para não modificarmos o XML de entrada
    prot_el = etree.fromstring(
        etree.tostring(prot_el, encoding="utf-8", xml_declaration=False)
    )

    # Ajustar infProt/Id = "ID{nProt}", conforme prática comum
    inf_prot = prot_el.find("nfe:infProt", ns)
    if inf_prot is not None:
        nprot_el = inf_prot.find("nfe:nProt", ns)
        if nprot_el is not None and (nprot_el.text or "").strip():
            nprot = nprot_el.text.strip()
            # Se ainda não começa com "ID", ajustamos:
            cur_id = inf_prot.get("Id") or ""
            if not cur_id or not cur_id.startswith("ID"):
                inf_prot.set("Id", f"ID{nprot}")

    # Serializa o protocolo ajustado em string
    proto_bytes = etree.tostring(
        prot_el,
        encoding="UTF-8",
        xml_declaration=True,
        pretty_print=False,
    )
    xml_protocolo_ajustado = proto_bytes.decode("utf-8")

    # Monta o nfeProc
    nsmap = {None: NFE_NS}
    nfe_proc_root = etree.Element(f"{{{NFE_NS}}}nfeProc", nsmap=nsmap)
    nfe_proc_root.set("versao", versao)

    # Garante que nfe_root é realmente <NFe>; se vier nfeProc (caso raro), pega o NFe interno
    if nfe_root.tag.endswith("nfeProc"):
        nfe_inner = nfe_root.find("nfe:NFe", ns)
        if nfe_inner is not None:
            nfe_root = nfe_inner

    nfe_proc_root.append(nfe_root)
    nfe_proc_root.append(prot_el)

    nfe_proc_bytes = etree.tostring(
        nfe_proc_root,
        encoding="UTF-8",
        xml_declaration=True,
        pretty_print=False,
    )
    xml_nfe_proc = nfe_proc_bytes.decode("utf-8")

    return NFeAutorizadoResult(
        autorizado=autorizado,
        status=status,
        motivo=motivo,
        xml_nfe_proc=xml_nfe_proc,
        xml_protocolo_ajustado=xml_protocolo_ajustado,
    )
