# sefaz_service/nfe/workflow.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sefaz_service.core.nfe_envio import sefaz_nfe_envio, NFeEnvioResult
from sefaz_service.core.nfe_autorizado import (
    sefaz_nfe_gera_autorizado,
    NFeAutorizadoResult,
)


@dataclass
class AutorizarNFeResult:
    """
    Resultado completo do fluxo de autorização:

      - autorizado: True se cStat em [100, 101, 150]
      - status: cStat como int (ou None)
      - motivo: xMotivo da SEFAZ

      - xml_original: XML original (sem assinatura) passado na entrada
      - xml_assinado: XML da NFe assinada
      - xml_envi_nfe: XML do <enviNFe> enviado
      - xml_retorno: XML de retorno da SEFAZ (<retEnviNFe> etc)
      - xml_nfe_proc: XML final do <nfeProc> (NFe + protNFe), se autorizado
      - xml_protocolo: XML de protocolo ajustado (infProt Id="ID{nProt}")
    """
    autorizado: bool
    status: Optional[int]
    motivo: Optional[str]

    xml_original: str
    xml_assinado: str
    xml_envi_nfe: str
    xml_retorno: str
    xml_nfe_proc: Optional[str]
    xml_protocolo: str


def autorizar_nfe(
    xml_nfe: str,
    uf: str,
    pfx_path: str,
    pfx_password: str,
    ambiente: str,
    *,
    versao: str = "4.00",
    envio_sinc: Optional[bool] = None,
    envio_zip: Optional[bool] = None,
    # parâmetros usados apenas se for NFC-e (mod=65)
    id_token: Optional[str] = None,
    csc: Optional[str] = None,
    versao_qrcode: str = "2.00",
    url_qrcode_base: Optional[str] = None,
    url_chave: Optional[str] = None,
) -> AutorizarNFeResult:
    """
    Fluxo completo:
      1) Assina a NFe/NFC-e
      2) Envia para SEFAZ (enviNFe)
      3) Gera nfeProc (NFe + protNFe), se autorizado

    Essa função é o equivalente de:
      ze_Sefaz_NFeEnvio() + ze_sefaz_NFeGeraAutorizado()
    em uma única chamada Python.
    """

    # 1) Envio (inclui assinatura e, se NFC-e, QRCode)
    envio_res: NFeEnvioResult = sefaz_nfe_envio(
        xml_nfe=xml_nfe,
        uf=uf,
        pfx_path=pfx_path,
        pfx_password=pfx_password,
        ambiente=ambiente,
        versao=versao,
        envio_sinc=envio_sinc,
        envio_zip=envio_zip,
        id_token=id_token,
        csc=csc,
        versao_qrcode=versao_qrcode,
        url_qrcode_base=url_qrcode_base,
        url_chave=url_chave,
    )

    # 2) Montar nfeProc com base no XML assinado e no retorno da SEFAZ
    aut_res: NFeAutorizadoResult = sefaz_nfe_gera_autorizado(
        xml_assinado=envio_res.xml_assinado,
        xml_protocolo=envio_res.xml_retorno,
        versao=versao,
    )

    return AutorizarNFeResult(
        autorizado=aut_res.autorizado,
        status=aut_res.status,
        motivo=aut_res.motivo,
        xml_original=xml_nfe,
        xml_assinado=envio_res.xml_assinado,
        xml_envi_nfe=envio_res.xml_envi_nfe,
        xml_retorno=envio_res.xml_retorno,
        xml_nfe_proc=aut_res.xml_nfe_proc,
        xml_protocolo=aut_res.xml_protocolo_ajustado,
    )
