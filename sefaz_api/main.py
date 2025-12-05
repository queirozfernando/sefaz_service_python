# sefaz_api/main.py
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel, Field
from lxml import etree

from sefaz_service.core.nfe_envio import sefaz_nfe_envio
from sefaz_service.core.nfe_inutilizacao import (
    InutilizacaoRequest,
    enviar_inutilizacao,
)
from sefaz_service.core.nfe_evento import (
    EventoRequest,
    sefaz_enviar_evento,
)
from sefaz_service.core.nfe_status import sefaz_nfe_status
from sefaz_service.core.nfe_consulta import sefaz_nfe_consulta  # consulta por chave
from sefaz_service.core.nfe_gtin import sefaz_consulta_gtin, GtinResult

# Conversão genérica XML → DocSped
from sefaz_service.sped import xml_to_doc, doc_sped_to_dict

# -------------------------------------------------------------------
# CONFIGURAÇÃO DE CERTIFICADO (PODE VIR DE VARIÁVEL DE AMBIENTE)
# -------------------------------------------------------------------

PFX_PATH = os.getenv("SEFAZ_PFX_PATH", r"C:\certificados\seu_certificado.pfx")
PFX_PASSWORD = os.getenv("SEFAZ_PFX_PASSWORD", "senha_do_certificado")

# Namespace NFe
NFE_NS = "http://www.portalfiscal.inf.br/nfe"


def _q(tag: str) -> str:
    """Monta o nome qualificado com o namespace da NFe."""
    return f"{{{NFE_NS}}}{tag}"


def _parse_xml_root(xml: str) -> etree._Element:
    """Parse robusto do XML bruto, retornando o root."""
    try:
        parser = etree.XMLParser(remove_blank_text=False, recover=True)
        root = etree.fromstring(xml.encode("utf-8"), parser=parser)
        return root
    except Exception as exc:
        raise ValueError(f"XML inválido: {exc}")


def _text(child: Optional[etree._Element]) -> Optional[str]:
    if child is not None and child.text is not None:
        return child.text.strip()
    return None


@dataclass
class XmlInfoResult:
    ide: Optional[Dict[str, Any]]
    emit: Optional[Dict[str, Any]]
    dest: Optional[Dict[str, Any]]
    totais: Dict[str, Any]
    itens: Optional[List[Dict[str, Any]]]


def _extract_xml_info_from_root(root: etree._Element) -> XmlInfoResult:
    """
    Extrai um resumo da NFe diretamente do XML:
    ide, emit, dest, totais, itens.
    Funciona para <nfeProc> ou apenas <NFe>/<infNFe>.
    """
    # Tenta achar infNFe em qualquer profundidade
    inf_nfe = root.find(f".//{_q('infNFe')}")
    if inf_nfe is None:
        raise ValueError("Não foi encontrado o nó <infNFe> no XML.")

    # --- IDE ---
    ide_el = inf_nfe.find(_q("ide"))
    ide: Optional[Dict[str, Any]] = None
    if ide_el is not None:
        ide = {
            "cUF": _text(ide_el.find(_q("cUF"))),
            "cNF": _text(ide_el.find(_q("cNF"))),
            "natOp": _text(ide_el.find(_q("natOp"))),
            "mod": _text(ide_el.find(_q("mod"))),
            "serie": _text(ide_el.find(_q("serie"))),
            "nNF": _text(ide_el.find(_q("nNF"))),
            "dhEmi": _text(ide_el.find(_q("dhEmi"))),
            "tpNF": _text(ide_el.find(_q("tpNF"))),
            "idDest": _text(ide_el.find(_q("idDest"))),
            "finNFe": _text(ide_el.find(_q("finNFe"))),
            "indFinal": _text(ide_el.find(_q("indFinal"))),
            "indPres": _text(ide_el.find(_q("indPres"))),
            "tpAmb": _text(ide_el.find(_q("tpAmb"))),
        }

    # --- EMITENTE ---
    emit_el = inf_nfe.find(_q("emit"))
    emit: Optional[Dict[str, Any]] = None
    if emit_el is not None:
        ender_emit_el = emit_el.find(_q("enderEmit"))
        emit = {
            "CNPJ": _text(emit_el.find(_q("CNPJ"))),
            "CPF": _text(emit_el.find(_q("CPF"))),
            "xNome": _text(emit_el.find(_q("xNome"))),
            "xFant": _text(emit_el.find(_q("xFant"))),
            "IE": _text(emit_el.find(_q("IE"))),
            "CRT": _text(emit_el.find(_q("CRT"))),
            "enderEmit": None,
        }
        if ender_emit_el is not None:
            emit["enderEmit"] = {
                "xLgr": _text(ender_emit_el.find(_q("xLgr"))),
                "nro": _text(ender_emit_el.find(_q("nro"))),
                "xCpl": _text(ender_emit_el.find(_q("xCpl"))),
                "xBairro": _text(ender_emit_el.find(_q("xBairro"))),
                "cMun": _text(ender_emit_el.find(_q("cMun"))),
                "xMun": _text(ender_emit_el.find(_q("xMun"))),
                "UF": _text(ender_emit_el.find(_q("UF"))),
                "CEP": _text(ender_emit_el.find(_q("CEP"))),
                "cPais": _text(ender_emit_el.find(_q("cPais"))),
                "xPais": _text(ender_emit_el.find(_q("xPais"))),
                "fone": _text(ender_emit_el.find(_q("fone"))),
            }

    # --- DESTINATÁRIO ---
    dest_el = inf_nfe.find(_q("dest"))
    dest: Optional[Dict[str, Any]] = None
    if dest_el is not None:
        ender_dest_el = dest_el.find(_q("enderDest"))
        dest = {
            "CNPJ": _text(dest_el.find(_q("CNPJ"))),
            "CPF": _text(dest_el.find(_q("CPF"))),
            "xNome": _text(dest_el.find(_q("xNome"))),
            "IE": _text(dest_el.find(_q("IE"))),
            "indIEDest": _text(dest_el.find(_q("indIEDest"))),
            "email": _text(dest_el.find(_q("email"))),
            "enderDest": None,
        }
        if ender_dest_el is not None:
            dest["enderDest"] = {
                "xLgr": _text(ender_dest_el.find(_q("xLgr"))),
                "nro": _text(ender_dest_el.find(_q("nro"))),
                "xCpl": _text(ender_dest_el.find(_q("xCpl"))),
                "xBairro": _text(ender_dest_el.find(_q("xBairro"))),
                "cMun": _text(ender_dest_el.find(_q("cMun"))),
                "xMun": _text(ender_dest_el.find(_q("xMun"))),
                "UF": _text(ender_dest_el.find(_q("UF"))),
                "CEP": _text(ender_dest_el.find(_q("CEP"))),
                "cPais": _text(ender_dest_el.find(_q("cPais"))),
                "xPais": _text(ender_dest_el.find(_q("xPais"))),
                "fone": _text(ender_dest_el.find(_q("fone"))),
            }

    # --- TOTAIS ---
    totais: Dict[str, Any] = {
        "vProd": "0.00",
        "vNF": "0.00",
        "vDesc": "0.00",
        "vICMS": "0.00",
        "vICMSDeson": "0.00",
        "vST": "0.00",
        "vFrete": "0.00",
        "vSeg": "0.00",
        "vOutro": "0.00",
        "vTotTrib": "0.00",
        "vPIS": "0.00",
        "vCOFINS": "0.00",
    }
    total_el = inf_nfe.find(_q("total"))
    if total_el is not None:
        icmstot_el = total_el.find(_q("ICMSTot"))
        if icmstot_el is not None:
            for campo in [
                "vProd",
                "vNF",
                "vDesc",
                "vICMS",
                "vICMSDeson",
                "vST",
                "vFrete",
                "vSeg",
                "vOutro",
                "vTotTrib",
                "vPIS",
                "vCOFINS",
            ]:
                v = _text(icmstot_el.find(_q(campo)))
                if v is not None:
                    totais[campo] = v

    # --- ITENS ---
    itens_list: List[Dict[str, Any]] = []
    for det_el in inf_nfe.findall(_q("det")):
        n_item = det_el.get("nItem")
        prod_el = det_el.find(_q("prod"))
        imposto_el = det_el.find(_q("imposto"))

        item: Dict[str, Any] = {
            "nItem": int(n_item) if n_item and n_item.isdigit() else None,
        }

        # PROD
        if prod_el is not None:
            item.update(
                {
                    "cProd": _text(prod_el.find(_q("cProd"))),
                    "cEAN": _text(prod_el.find(_q("cEAN"))),
                    "xProd": _text(prod_el.find(_q("xProd"))),
                    "NCM": _text(prod_el.find(_q("NCM"))),
                    "CEST": _text(prod_el.find(_q("CEST"))),
                    "CFOP": _text(prod_el.find(_q("CFOP"))),
                    "uCom": _text(prod_el.find(_q("uCom"))),
                    "qCom": _text(prod_el.find(_q("qCom"))),
                    "vUnCom": _text(prod_el.find(_q("vUnCom"))),
                    "vProd": _text(prod_el.find(_q("vProd"))),
                    "cEANTrib": _text(prod_el.find(_q("cEANTrib"))),
                    "uTrib": _text(prod_el.find(_q("uTrib"))),
                    "qTrib": _text(prod_el.find(_q("qTrib"))),
                    "vUnTrib": _text(prod_el.find(_q("vUnTrib"))),
                    "vDesc": _text(prod_el.find(_q("vDesc"))),
                    "indTot": _text(prod_el.find(_q("indTot"))),
                }
            )
        else:
            item.update(
                {
                    "cProd": None,
                    "cEAN": None,
                    "xProd": None,
                    "NCM": None,
                    "CEST": None,
                    "CFOP": None,
                    "uCom": None,
                    "qCom": None,
                    "vUnCom": None,
                    "vProd": None,
                    "cEANTrib": None,
                    "uTrib": None,
                    "qTrib": None,
                    "vUnTrib": None,
                    "vDesc": None,
                    "indTot": None,
                }
            )

        # IMPOSTOS
        icms_data: Dict[str, Any] = {
            "orig": None,
            "CST": None,
            "CSOSN": None,
            "modBC": None,
            "vBC": None,
            "pICMS": None,
            "vICMS": None,
        }
        pis_data: Dict[str, Any] = {"CST": None, "vBC": None, "pPIS": None, "vPIS": None}
        cofins_data: Dict[str, Any] = {
            "CST": None,
            "vBC": None,
            "pCOFINS": None,
            "vCOFINS": None,
        }

        if imposto_el is not None:
            # ICMS (pega o primeiro ICMS* que encontrar)
            icms_el = imposto_el.find(_q("ICMS"))
            if icms_el is not None:
                icms_any = None
                for child in icms_el:
                    if child.tag.startswith(_q("ICMS")):
                        icms_any = child
                        break
                if icms_any is not None:
                    icms_data["orig"] = _text(icms_any.find(_q("orig")))
                    icms_data["CST"] = _text(icms_any.find(_q("CST")))
                    icms_data["CSOSN"] = _text(icms_any.find(_q("CSOSN")))
                    icms_data["modBC"] = _text(icms_any.find(_q("modBC")))
                    icms_data["vBC"] = _text(icms_any.find(_q("vBC")))
                    icms_data["pICMS"] = _text(icms_any.find(_q("pICMS")))
                    icms_data["vICMS"] = _text(icms_any.find(_q("vICMS")))

            # PIS
            pis_el = imposto_el.find(_q("PIS"))
            if pis_el is not None:
                pis_any = None
                for child in pis_el:
                    pis_any = child
                    break
                if pis_any is not None:
                    pis_data["CST"] = _text(pis_any.find(_q("CST")))
                    pis_data["vBC"] = _text(pis_any.find(_q("vBC")))
                    pis_data["pPIS"] = _text(pis_any.find(_q("pPIS")))
                    pis_data["vPIS"] = _text(pis_any.find(_q("vPIS")))

            # COFINS
            cofins_el = imposto_el.find(_q("COFINS"))
            if cofins_el is not None:
                cof_any = None
                for child in cofins_el:
                    cof_any = child
                    break
                if cof_any is not None:
                    cofins_data["CST"] = _text(cof_any.find(_q("CST")))
                    cofins_data["vBC"] = _text(cof_any.find(_q("vBC")))
                    cofins_data["pCOFINS"] = _text(cof_any.find(_q("pCOFINS")))
                    cofins_data["vCOFINS"] = _text(cof_any.find(_q("vCOFINS")))

        item["ICMS"] = icms_data
        item["PIS"] = pis_data
        item["COFINS"] = cofins_data

        itens_list.append(item)

    return XmlInfoResult(
        ide=ide,
        emit=emit,
        dest=dest,
        totais=totais,
        itens=itens_list or None,
    )


# -------------------------------------------------------------------
# FASTAPI APP
# -------------------------------------------------------------------

app = FastAPI(
    title="SEFAZ Service API",
    version="1.0.0",
    description="API para envio de NFe, inutilização, eventos e consultas.",
)

# -------------------------------------------------------------------
# MODELOS Pydantic PARA REQUESTS/RESPONSES
# -------------------------------------------------------------------


class NFeAutorizarComCertRequest(BaseModel):
    uf: str = Field(..., description="Sigla da UF, ex.: AC, SP, MG")
    ambiente: str = Field("2", description="1=Producao, 2=Homologacao")
    xml_nfe: str = Field(..., description="XML da NFe (sem assinatura)")
    certificado: str = Field(
        ...,
        description="Caminho completo do arquivo .pfx no servidor (ex.: C:\\Certificados\\cert.pfx)",
    )
    senha: str = Field(..., description="Senha do certificado PFX")


class NFeEnvioResponse(BaseModel):
    status: int | None
    motivo: str | None
    xml_assinado: str
    xml_envi_nfe: str
    xml_retorno: str


class InutilizacaoAPIRequest(BaseModel):
    uf: str = Field(..., description="Sigla da UF, ex.: AC")
    cUF: str = Field(..., description="Código numérico da UF, ex.: 12 para AC")
    tpAmb: str = Field("2", description="1=Produção, 2=Homologação")
    ano: str = Field(..., description="Ano com 2 dígitos, ex.: 25")
    CNPJ: str = Field(..., description="CNPJ do emitente (com ou sem máscara)")
    mod: str = Field("55", description="Modelo da NFe: 55 ou 65")
    serie: str = Field(..., description="Série da NFe, ex.: 1")
    nNFIni: str = Field(..., description="Número inicial a inutilizar")
    nNFFin: str = Field(..., description="Número final a inutilizar")
    xJust: str = Field(..., min_length=15, description="Justificativa da inutilização")


class InutilizacaoAPIResponse(BaseModel):
    cStat: str | None
    xMotivo: str | None
    nProt: str | None
    dhRecbto: str | None
    xml_retorno: str | None


class CancelamentoRequest(BaseModel):
    uf: str = Field(..., description="Sigla da UF, ex.: AC")
    cOrgao: str = Field(..., description="Código da UF, ex.: 12 para AC")
    tpAmb: str = Field("2", description="1=Produção, 2=Homologação")
    CNPJ: str = Field(..., description="CNPJ do emitente")
    chNFe: str = Field(..., description="Chave completa da NFe a cancelar")
    nProt: str = Field(..., description="Protocolo de autorização da NFe")
    xJust: str = Field(..., min_length=15, description="Justificativa do cancelamento")
    nSeqEvento: int = Field(1, description="Número sequencial do evento (normalmente 1)")


class CancelamentoSubstRequest(BaseModel):
    uf: str
    cOrgao: str
    tpAmb: str = "2"
    CNPJ: str
    chNFe: str = Field(..., description="Chave da NFe que será cancelada")
    chNFeRef: str = Field(..., description="Chave da NFe substituta")
    nProt: str = Field(..., description="Protocolo de autorização da NFe a cancelar")
    xJust: str = Field(..., min_length=15, description="Justificativa")
    nSeqEvento: int = 1


class CartaCorrecaoRequest(BaseModel):
    uf: str = Field(..., description="Sigla da UF, ex.: AC")
    cOrgao: str = Field(..., description="Código da UF (ex.: 12 para AC)")
    tpAmb: str = Field("2", description="1=Producao, 2=Homologacao")
    CNPJ: str = Field(..., description="CNPJ do emitente")
    chNFe: str = Field(..., description="Chave completa da NFe (44 dígitos)")
    nSeqEvento: int = Field(
        1,
        description="Número sequencial da CC-e (1 para primeira, 2 para segunda, etc.)",
    )
    xCorrecao: str = Field(
        ...,
        min_length=15,
        max_length=1000,
        description="Texto da Carta de Correcao (respeitando as regras da legislação)",
    )


class EventoAPIResponse(BaseModel):
    cStat_lote: int | None
    xMotivo_lote: str | None
    cStat_evento: int | None
    xMotivo_evento: str | None
    nProt_evento: str | None
    xml_envio: str
    xml_assinado: str
    xml_retorno: str


class NFeStatusRequest(BaseModel):
    uf: str = Field(..., description="Sigla da UF, ex.: AC, SP, MG")
    ambiente: str = Field("2", description="1=Producao, 2=Homologacao")
    certificado: str = Field(
        ...,
        description="Caminho completo do arquivo .pfx no servidor (ex.: C:\\Certificados\\cert.pfx)",
    )
    senha: str = Field(..., description="Senha do certificado PFX")


class NFeStatusResponse(BaseModel):
    status: int | None
    motivo: str | None
    xml_envio: str
    xml_retorno: str


class NFeConsultaChaveRequest(BaseModel):
    uf: str = Field(..., description="Sigla da UF, ex.: AC, SP, MG")
    ambiente: str = Field("2", description="1=Producao, 2=Homologacao")
    chNFe: str = Field(..., description="Chave completa da NFe (44 dígitos)")
    certificado: str = Field(
        ...,
        description="Caminho completo do arquivo .pfx no servidor (ex.: C:\\Certificados\\cert.pfx)",
    )
    senha: str = Field(..., description="Senha do certificado PFX")


class NFeConsultaChaveResponse(BaseModel):
    status: int | None
    motivo: str | None
    xml_envio: str
    xml_retorno: str


class NFeGTINRequest(BaseModel):
    gtin: str
    certificado: str
    senha: str


class NFeGTINResponse(BaseModel):
    status: int | None
    motivo: str | None
    xml_envio: str
    xml_retorno: str


# --------- MODELOS PARA XML BRUTO / RESUMO / ANÁLISE ---------


class XmlToDocResponse(BaseModel):
    data: Dict[str, Any]


class XmlInfoResponse(BaseModel):
    ide: Optional[Dict[str, Any]]
    emit: Optional[Dict[str, Any]]
    dest: Optional[Dict[str, Any]]
    totais: Dict[str, Any]
    itens: Optional[List[Dict[str, Any]]]


class NFeAnaliseICMS(BaseModel):
    uf_emit: Optional[str]
    uf_dest: Optional[str]
    operacao_interna: Optional[bool]
    consumidor_final: Optional[bool]
    contribuinte_destinatario: Optional[bool]
    indIEDest: Optional[str]
    regime_emitente: Optional[str]
    possui_st: bool
    possui_icms_proprio: bool
    csts_icms: List[str]
    observacoes: List[str]


class NFeAnalisePisCofins(BaseModel):
    csts_pis: List[str]
    csts_cofins: List[str]
    monofasico_suspeito: bool
    observacoes: List[str]


class NFeAnaliseResponse(BaseModel):
    ok: bool
    mensagens: List[str]
    icms: Optional[NFeAnaliseICMS]
    pis_cofins: Optional[NFeAnalisePisCofins]
    resumo: XmlInfoResponse


# -------------------------------------------------------------------
# ENDPOINTS EXISTENTES
# -------------------------------------------------------------------


@app.post("/nfe/enviar", response_model=NFeEnvioResponse, summary="Enviar NFe (autorização)")
def enviar_nfe(payload: NFeAutorizarComCertRequest):
    """
    Envia uma NFe para a SEFAZ usando
    certificado e senha enviados na requisição.
    """
    try:
        result = sefaz_nfe_envio(
            xml_nfe=payload.xml_nfe,
            uf=payload.uf,
            pfx_path=payload.certificado,
            pfx_password=payload.senha,
            ambiente=payload.ambiente,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao enviar NFe com certificado informado: {e}",
        )

    return NFeEnvioResponse(
        status=result.status,
        motivo=result.motivo,
        xml_assinado=result.xml_assinado,
        xml_envi_nfe=result.xml_envi_nfe,
        xml_retorno=result.xml_retorno,
    )


@app.post("/nfe/inutilizar", response_model=InutilizacaoAPIResponse, summary="Inutilizar numeração de NFe")
def inutilizar_numeracao(payload: InutilizacaoAPIRequest):
    """
    Inutilização de numeração de NFe (NFeInutilizacao4).
    """
    req = InutilizacaoRequest(
        cUF=payload.cUF,
        tpAmb=payload.tpAmb,
        ano=payload.ano,
        CNPJ=payload.CNPJ,
        mod=payload.mod,
        serie=payload.serie,
        nNFIni=payload.nNFIni,
        nNFFin=payload.nNFFin,
        xJust=payload.xJust,
    )

    try:
        resp = enviar_inutilizacao(
            req=req,
            certificado=PFX_PATH,
            senha=PFX_PASSWORD,
            uf_sigla=payload.uf,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao inutilizar: {e}")

    return InutilizacaoAPIResponse(
        cStat=resp.cStat,
        xMotivo=resp.xMotivo,
        nProt=resp.nProt,
        dhRecbto=resp.dhRecbto,
        xml_retorno=resp.raw_xml,
    )


@app.post("/nfe/evento/cancelar", response_model=EventoAPIResponse, summary="Cancelar NFe (evento 110111)")
def cancelar_nfe(payload: CancelamentoRequest):
    """
    Envia evento de CANCELAMENTO (110111).
    """
    req = EventoRequest(
        tpAmb=payload.tpAmb,
        cOrgao=payload.cOrgao,
        CNPJ=payload.CNPJ,
        chNFe=payload.chNFe,
        tpEvento="110111",
        nSeqEvento=payload.nSeqEvento,
        xJust=payload.xJust,
        nProt=payload.nProt,
        chNFeRef=None,
    )

    try:
        res = sefaz_enviar_evento(
            req=req,
            uf=payload.uf,
            pfx_path=PFX_PATH,
            pfx_password=PFX_PASSWORD,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao enviar evento de cancelamento: {e}")

    return EventoAPIResponse(
        cStat_lote=res.cStat_lote,
        xMotivo_lote=res.xMotivo_lote,
        cStat_evento=res.cStat_evento,
        xMotivo_evento=res.xMotivo_evento,
        nProt_evento=res.nProt_evento,
        xml_envio=res.xml_envio,
        xml_assinado=res.xml_assinado,
        xml_retorno=res.xml_retorno,
    )


@app.post(
    "/nfe/evento/cancelar-substituicao",
    response_model=EventoAPIResponse,
    summary="Cancelar NFe por substituição (evento 110112)",
)
def cancelar_nfe_por_substituicao(payload: CancelamentoSubstRequest):
    """
    Envia evento de CANCELAMENTO POR SUBSTITUIÇÃO (110112).
    """
    req = EventoRequest(
        tpAmb=payload.tpAmb,
        cOrgao=payload.cOrgao,
        CNPJ=payload.CNPJ,
        chNFe=payload.chNFe,
        tpEvento="110112",
        nSeqEvento=payload.nSeqEvento,
        xJust=payload.xJust,
        nProt=payload.nProt,
        chNFeRef=payload.chNFeRef,
    )

    try:
        res = sefaz_enviar_evento(
            req=req,
            uf=payload.uf,
            pfx_path=PFX_PATH,
            pfx_password=PFX_PASSWORD,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao enviar evento de cancelamento por substituicao: {e}",
        )

    return EventoAPIResponse(
        cStat_lote=res.cStat_lote,
        xMotivo_lote=res.xMotivo_lote,
        cStat_evento=res.cStat_evento,
        xMotivo_evento=res.xMotivo_evento,
        nProt_evento=res.nProt_evento,
        xml_envio=res.xml_envio,
        xml_assinado=res.xml_assinado,
        xml_retorno=res.xml_retorno,
    )


@app.post(
    "/nfe/evento/carta-correcao",
    response_model=EventoAPIResponse,
    summary="Enviar Carta de Correcao (evento 110110)",
)
def enviar_carta_correcao(payload: CartaCorrecaoRequest):
    """
    Envia uma Carta de Correcao Eletronica (CC-e) para a NFe informada (evento 110110).
    """
    req = EventoRequest(
        tpAmb=payload.tpAmb,
        cOrgao=payload.cOrgao,
        CNPJ=payload.CNPJ,
        chNFe=payload.chNFe,
        tpEvento="110110",
        nSeqEvento=payload.nSeqEvento,
        xCorrecao=payload.xCorrecao,
        xJust=None,
        nProt=None,
        chNFeRef=None,
    )

    try:
        res = sefaz_enviar_evento(
            req=req,
            uf=payload.uf,
            pfx_path=PFX_PATH,
            pfx_password=PFX_PASSWORD,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao enviar carta de correcao: {e}",
        )

    return EventoAPIResponse(
        cStat_lote=res.cStat_lote,
        xMotivo_lote=res.xMotivo_lote,
        cStat_evento=res.cStat_evento,
        xMotivo_evento=res.xMotivo_evento,
        nProt_evento=res.nProt_evento,
        xml_envio=res.xml_envio,
        xml_assinado=res.xml_assinado,
        xml_retorno=res.xml_retorno,
    )


@app.post(
    "/nfe/status",
    response_model=NFeStatusResponse,
    summary="Consultar status do SERVIÇO NFe (NFeStatusServico4)",
)
def consultar_status_servico_nfe(payload: NFeStatusRequest):
    """
    Consulta o STATUS DO SERVIÇO de NFe (NFeStatusServico4).
    Não é status da nota, e sim se o webservice está em operação.
    """
    try:
        res = sefaz_nfe_status(
            uf=payload.uf,
            pfx_path=payload.certificado,
            pfx_password=payload.senha,
            ambiente=payload.ambiente,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao consultar status do servico NFe: {e}",
        )

    return NFeStatusResponse(
        status=res.cStat,
        motivo=res.xMotivo,
        xml_envio=res.xml_envio,
        xml_retorno=res.xml_retorno,
    )


@app.post(
    "/nfe/consulta",
    response_model=NFeConsultaChaveResponse,
    summary="Consultar situação de NFe por CHAVE (NFeConsultaProtocolo4)",
)
def consultar_nfe_por_chave(payload: NFeConsultaChaveRequest):
    """
    Consulta a SITUAÇÃO de uma NFe específica, pela CHAVE.
    """
    try:
        res = sefaz_nfe_consulta(
            uf=payload.uf,
            chave=payload.chNFe,
            pfx_path=payload.certificado,
            pfx_password=payload.senha,
            ambiente=payload.ambiente,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao consultar NFe por chave: {e}",
        )

    return NFeConsultaChaveResponse(
        status=res.cStat,
        motivo=res.xMotivo,
        xml_envio=res.xml_envio,
        xml_retorno=res.xml_retorno,
    )


@app.post(
    "/nfe/gtin",
    response_model=NFeGTINResponse,
    summary="Consultar GTIN (ccgConsGTIN – SVRS)",
)
def consultar_gtin(payload: NFeGTINRequest):
    try:
        resp = sefaz_consulta_gtin(
            gtin=payload.gtin,
            pfx_path=payload.certificado,
            pfx_password=payload.senha,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao consultar GTIN: {e}")

    return NFeGTINResponse(
        status=resp.status,
        motivo=resp.motivo,
        xml_envio=resp.xml_envio,
        xml_retorno=resp.xml_retorno,
    )


# -------------------------------------------------------------------
# NOVOS ENDPOINTS: /nfe/xmltodoc, /nfe/xmlinfo, /nfe/analise
# -------------------------------------------------------------------


@app.post(
    "/nfe/xmltodoc",
    response_model=XmlToDocResponse,
    summary="Converter XML de NFe em DocSped (JSON cru)",
)
def nfe_xml_to_doc(
    xml_body: str = Body(
        ...,
        media_type="application/xml",
        description="XML bruto da NFe (pode ser <nfeProc> ou apenas <NFe>/<infNFe>).",
    )
):
    """
    Converte o XML bruto em DocSped (estrutura genérica), retornando o dict completo.
    """
    try:
        doc = xml_to_doc(xml_body)
        data = doc_sped_to_dict(doc)
        return XmlToDocResponse(data=data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao converter XML em DocSped: {e}")


@app.post(
    "/nfe/xmlinfo",
    response_model=XmlInfoResponse,
    summary="Extrair informações resumidas da NFe (ide, emit, dest, totais, itens)",
)
def nfe_xml_info(
    xml_body: str = Body(
        ...,
        media_type="application/xml",
        description="XML bruto da NFe (pode ser <nfeProc> ou apenas <NFe>/<infNFe>).",
    )
):
    """
    Lê o XML bruto da NFe e devolve um resumo com:
      - ide
      - emit
      - dest
      - totais
      - itens (com ICMS / PIS / COFINS básicos)
    """
    try:
        root = _parse_xml_root(xml_body)
        info = _extract_xml_info_from_root(root)
        return XmlInfoResponse(
            ide=info.ide,
            emit=info.emit,
            dest=info.dest,
            totais=info.totais,
            itens=info.itens,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao ler informações do XML: {e}")


@app.post(
    "/nfe/analise",
    response_model=NFeAnaliseResponse,
    summary="Analisar tributação da NFe (ICMS, PIS/COFINS) a partir do XML bruto",
)
def nfe_analise(
    xml_body: str = Body(
        ...,
        media_type="application/xml",
        description="XML bruto da NFe (pode ser <nfeProc> ou apenas <NFe>/<infNFe>).",
    )
):
    """
    Faz uma análise básica da NFe:
      - ICMS: operação interna/interestadual, consumidor final, ST, ICMS próprio, CRT, etc.
      - PIS/COFINS: CSTs utilizados, possível regime monofásico.
      - Retorna também o resumo de /nfe/xmlinfo.
    """
    try:
        root = _parse_xml_root(xml_body)
        info = _extract_xml_info_from_root(root)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar XML: {e}")

    ide = info.ide or {}
    emit = info.emit or {}
    dest = info.dest or {}
    itens = info.itens or []

    uf_emit = (emit.get("enderEmit") or {}).get("UF")
    uf_dest = (dest.get("enderDest") or {}).get("UF")
    operacao_interna: Optional[bool] = None
    if uf_emit and uf_dest:
        operacao_interna = uf_emit == uf_dest

    consumidor_final: Optional[bool] = None
    if ide.get("indFinal") is not None:
        consumidor_final = ide.get("indFinal") == "1"

    ind_ie_dest = dest.get("indIEDest")
    contribuinte_dest: Optional[bool] = None
    if ind_ie_dest == "1":
        contribuinte_dest = True
    elif ind_ie_dest in ("2", "9"):
        contribuinte_dest = False

    regime_emit = emit.get("CRT")

    # --- ICMS por item ---
    csts_icms: set[str] = set()
    possui_st = False
    possui_icms_proprio = False
    obs_icms: List[str] = []

    for it in itens:
        icms = it.get("ICMS") or {}
        cst = icms.get("CST") or icms.get("CSOSN")
        if cst:
            csts_icms.add(cst)

            # ST (bem simplificado)
            if cst in {"10", "30", "60", "70"} or it.get("CEST"):
                possui_st = True

            # ICMS próprio (simplificado)
            if cst in {"00", "20", "51"}:
                possui_icms_proprio = True

    if operacao_interna is True:
        obs_icms.append("Operação interna (UF emitente = UF destinatário).")
    elif operacao_interna is False:
        obs_icms.append("Operação interestadual (UF emitente ≠ UF destinatário).")

    if consumidor_final is True:
        obs_icms.append("Destinatário é consumidor final (indFinal=1).")
    elif consumidor_final is False:
        obs_icms.append("Destinatário não é consumidor final (indFinal≠1).")

    if contribuinte_dest is True:
        obs_icms.append("Destinatário é contribuinte do ICMS (indIEDest=1).")
    elif contribuinte_dest is False:
        obs_icms.append("Destinatário não contribuinte/isento (indIEDest=2 ou 9).")

    if regime_emit == "1":
        obs_icms.append("Emitente no Simples Nacional (CRT=1).")
    elif regime_emit == "3":
        obs_icms.append("Emitente no regime normal (CRT=3).")

    if possui_st:
        obs_icms.append(
            "Nota com indícios de Substituição Tributária (CST ICMS de ST ou CEST preenchido)."
        )
    else:
        obs_icms.append("Não foram identificados indícios de Substituição Tributária nos itens.")

    if possui_icms_proprio:
        obs_icms.append("Há itens com ICMS próprio destacado (CST 00/20/51).")
    else:
        obs_icms.append("Não foram identificados itens com ICMS próprio clássico (CST 00/20/51).")

    analise_icms = NFeAnaliseICMS(
        uf_emit=uf_emit,
        uf_dest=uf_dest,
        operacao_interna=operacao_interna,
        consumidor_final=consumidor_final,
        contribuinte_destinatario=contribuinte_dest,
        indIEDest=ind_ie_dest,
        regime_emitente=regime_emit,
        possui_st=possui_st,
        possui_icms_proprio=possui_icms_proprio,
        csts_icms=sorted(csts_icms),
        observacoes=obs_icms,
    )

    # --- PIS / COFINS ---
    csts_pis: set[str] = set()
    csts_cof: set[str] = set()
    obs_pis_cof: List[str] = []

    for it in itens:
        pis = it.get("PIS") or {}
        cof = it.get("COFINS") or {}

        cst_pis = pis.get("CST")
        cst_cof = cof.get("CST")
        if cst_pis:
            csts_pis.add(cst_pis)
        if cst_cof:
            csts_cof.add(cst_cof)

    monof_csts = {"04", "06", "07", "08", "09", "49"}
    monofasico_suspeito = bool(
        monof_csts.intersection(csts_pis) or monof_csts.intersection(csts_cof)
    )

    if monofasico_suspeito:
        obs_pis_cof.append(
            "Foram encontrados CSTs de PIS/COFINS que indicam regime monofásico/suspensão/isenção "
            "(ex.: 04, 06, 07, 08, 09, 49)."
        )
    else:
        obs_pis_cof.append("CSTs de PIS/COFINS não indicam regime monofásico típico.")

    if csts_pis:
        obs_pis_cof.append(f"CSTs de PIS encontrados: {', '.join(sorted(csts_pis))}.")
    if csts_cof:
        obs_pis_cof.append(f"CSTs de COFINS encontrados: {', '.join(sorted(csts_cof))}.")

    analise_pis_cof = NFeAnalisePisCofins(
        csts_pis=sorted(csts_pis),
        csts_cofins=sorted(csts_cof),
        monofasico_suspeito=monofasico_suspeito,
        observacoes=obs_pis_cof,
    )

    mensagens: List[str] = []
    mensagens.extend(obs_icms)
    mensagens.extend(obs_pis_cof)

    ok = True

    return NFeAnaliseResponse(
        ok=ok,
        mensagens=mensagens,
        icms=analise_icms,
        pis_cofins=analise_pis_cof,
        resumo=XmlInfoResponse(
            ide=info.ide,
            emit=info.emit,
            dest=info.dest,
            totais=info.totais,
            itens=info.itens,
        ),
    )
