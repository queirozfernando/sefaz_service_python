# sefaz_api/main.py
from __future__ import annotations

import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

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
from sefaz_service.core.nfe_gtin import sefaz_consulta_gtin

# Conversão XML → DocSped
from sefaz_service.sped import xml_to_doc, doc_sped_to_dict

# -------------------------------------------------------------------
# CONFIGURAÇÃO DE CERTIFICADO (PODE VIR DE VARIÁVEL DE AMBIENTE)
# -------------------------------------------------------------------

PFX_PATH = os.getenv("SEFAZ_PFX_PATH", r"C:\certificados\seu_certificado.pfx")
PFX_PASSWORD = os.getenv("SEFAZ_PFX_PASSWORD", "senha_do_certificado")

app = FastAPI(
    title="SEFAZ Service API",
    version="1.0.0",
    description="API para envio de NFe, inutilização, eventos, consultas e análise de XML.",
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


# 👉 XML → DocSped básicos

class XmlToDocRequest(BaseModel):
    xml: str = Field(
        ...,
        description="XML completo da NFe (pode ser <nfeProc> ou apenas <NFe>/<infNFe>).",
    )


class XmlToDocResponse(BaseModel):
    data: dict


# 👉 XMLINFO

class NFeXmlInfoRequest(BaseModel):
    xml: str = Field(
        ...,
        description="XML completo da NFe (pode ser <nfeProc> ou apenas <NFe>/<infNFe>).",
    )


class NFeXmlInfoResponse(BaseModel):
    ide: dict | None = None
    emit: dict | None = None
    dest: dict | None = None
    totais: dict | None = None
    itens: list[dict] | None = None


# 👉 ANÁLISE

class NFeAnaliseRequest(BaseModel):
    xml: str = Field(
        ...,
        description="XML completo da NFe (pode ser <nfeProc> ou apenas <NFe>/<infNFe>).",
    )


class CstResumo(BaseModel):
    cst: str
    qtd_itens: int


class NFeAnaliseResponse(BaseModel):
    # Informações gerais
    tipo_operacao: str = Field(
        ...,
        description="ENTRADA ou SAIDA, com base em ide.tpNF (0=entrada,1=saída).",
    )
    destino_operacao: str = Field(
        ...,
        description="INTERNA, INTERESTADUAL ou EXTERIOR (ide.idDest ou UF emit/dest).",
    )
    consumidor_final: bool = Field(
        ...,
        description="True se ide.indFinal == '1'.",
    )
    contribuinte_destinatario: str = Field(
        ...,
        description="CONTRIBUINTE_ICMS / CONTRIBUINTE_ISENTO / NAO_CONTRIBUINTE / DESCONHECIDO.",
    )
    regime_emitente: str = Field(
        ...,
        description="SIMPLES_NACIONAL / SIMPLES_EXCESSO / REGIME_NORMAL / DESCONHECIDO.",
    )

    # Flags de análise tributária
    possui_st: bool = Field(
        ...,
        description="True se houver ICMS com CST típico de ST (ex.: 10,30,60,70,90).",
    )
    possui_monofasico: bool = Field(
        ...,
        description="True se houver PIS/COFINS com CST monofásico (04,05,06,07,08,09).",
    )

    # Resumo de CST por imposto
    cst_icms_resumo: list[CstResumo]
    cst_pis_resumo: list[CstResumo]
    cst_cofins_resumo: list[CstResumo]


# -------------------------------------------------------------------
# HELPERS DE ANÁLISE
# -------------------------------------------------------------------


def _analisar_dados_nfe(data: dict) -> NFeAnaliseResponse:
    ide = data.get("ide", {}) or {}
    emit = data.get("emit", {}) or {}
    dest = data.get("dest", {}) or {}
    itens = data.get("itens", []) or []

    # tipo_operacao (ENTRADA/SAIDA)
    tpNF = (ide.get("tpNF") or "").strip()
    if tpNF == "0":
        tipo_operacao = "ENTRADA"
    elif tpNF == "1":
        tipo_operacao = "SAIDA"
    else:
        tipo_operacao = "DESCONHECIDO"

    # destino_operacao
    idDest = (ide.get("idDest") or "").strip()
    if idDest == "1":
        destino_operacao = "INTERNA"
    elif idDest == "2":
        destino_operacao = "INTERESTADUAL"
    elif idDest == "3":
        destino_operacao = "EXTERIOR"
    else:
        uf_emit = ((emit.get("enderEmit") or {}).get("UF") or "").strip()
        uf_dest = ((dest.get("enderDest") or {}).get("UF") or "").strip()
        if uf_emit and uf_dest:
            destino_operacao = "INTERNA" if uf_emit == uf_dest else "INTERESTADUAL"
        else:
            destino_operacao = "DESCONHECIDO"

    # consumidor_final
    consumidor_final = (ide.get("indFinal") or "").strip() == "1"

    # contribuinte_destinatario
    indIEDest = (dest.get("indIEDest") or "").strip()
    if indIEDest == "1":
        contribuinte_destinatario = "CONTRIBUINTE_ICMS"
    elif indIEDest == "2":
        contribuinte_destinatario = "CONTRIBUINTE_ISENTO"
    elif indIEDest == "9":
        contribuinte_destinatario = "NAO_CONTRIBUINTE"
    else:
        contribuinte_destinatario = "DESCONHECIDO"

    # regime_emitente (CRT)
    crt = (emit.get("CRT") or "").strip()
    if crt == "1":
        regime_emitente = "SIMPLES_NACIONAL"
    elif crt == "2":
        regime_emitente = "SIMPLES_EXCESSO"
    elif crt == "3":
        regime_emitente = "REGIME_NORMAL"
    else:
        regime_emitente = "DESCONHECIDO"

    # Resumos de CST e flags ST / monofásico
    from collections import Counter

    cst_icms_counter: Counter[str] = Counter()
    cst_pis_counter: Counter[str] = Counter()
    cst_cofins_counter: Counter[str] = Counter()

    possui_st = False
    possui_monofasico = False

    cst_st_set = {"10", "30", "60", "70", "90"}
    cst_monofasico_set = {"04", "05", "06", "07", "08", "09"}

    for item in itens:
        icms = item.get("ICMS") or {}
        pis = item.get("PIS") or {}
        cofins = item.get("COFINS") or {}

        cst_icms = (icms.get("CST") or icms.get("CSOSN") or "").strip()
        cst_pis = (pis.get("CST") or "").strip()
        cst_cofins = (cofins.get("CST") or "").strip()

        if cst_icms:
            cst_icms_counter[cst_icms] += 1
            if cst_icms in cst_st_set:
                possui_st = True

        if cst_pis:
            cst_pis_counter[cst_pis] += 1
            if cst_pis in cst_monofasico_set:
                possui_monofasico = True

        if cst_cofins:
            cst_cofins_counter[cst_cofins] += 1
            if cst_cofins in cst_monofasico_set:
                possui_monofasico = True

    cst_icms_resumo = [
        CstResumo(cst=k, qtd_itens=v) for k, v in sorted(cst_icms_counter.items())
    ]
    cst_pis_resumo = [
        CstResumo(cst=k, qtd_itens=v) for k, v in sorted(cst_pis_counter.items())
    ]
    cst_cofins_resumo = [
        CstResumo(cst=k, qtd_itens=v) for k, v in sorted(cst_cofins_counter.items())
    ]

    return NFeAnaliseResponse(
        tipo_operacao=tipo_operacao,
        destino_operacao=destino_operacao,
        consumidor_final=consumidor_final,
        contribuinte_destinatario=contribuinte_destinatario,
        regime_emitente=regime_emitente,
        possui_st=possui_st,
        possui_monofasico=possui_monofasico,
        cst_icms_resumo=cst_icms_resumo,
        cst_pis_resumo=cst_pis_resumo,
        cst_cofins_resumo=cst_cofins_resumo,
    )


# -------------------------------------------------------------------
# ENDPOINTS
# -------------------------------------------------------------------


@app.post("/nfe/enviar", response_model=NFeEnvioResponse, summary="Enviar NFe (autorização)")
def enviar_nfe(payload: NFeAutorizarComCertRequest):
    """
    Envia uma NFe para a SEFAZ usando certificado e senha enviados na requisição.
    - Recebe XML da NFe sem assinatura.
    - Usa o PFX informado (caminho + senha).
    - Assina, monta enviNFe, envia via SOAP e retorna o resultado.
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
    Consulta o STATUS DO SERVIÇO de NFe (NFeStatusServico4) para a UF/ambiente informados.
    Não é status da nota, e sim se o webservice está em operação (cStat 107/108 etc.).
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
    Consulta a SITUAÇÃO de uma NFe específica, pela CHAVE (consSitNFe / NFeConsultaProtocolo4).
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


# 👉 /nfe/xmltodoc – devolve o DocSped inteiro em dict

@app.post(
    "/nfe/xmltodoc",
    response_model=XmlToDocResponse,
    summary="Converter XML de NFe em estrutura DocSped (JSON completo)",
)
def nfe_xml_to_doc(payload: XmlToDocRequest):
    """
    Converte o XML de NFe em uma estrutura DocSped, retornando em JSON completo.
    - Aceita tanto <nfeProc> quanto apenas <NFe>/<infNFe>.
    """
    try:
        doc = xml_to_doc(payload.xml)
        return XmlToDocResponse(data=doc_sped_to_dict(doc))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao converter XML: {e}")


# 👉 /nfe/xmlinfo – resumo (ide, emit, dest, totais, itens)

@app.post(
    "/nfe/xmlinfo",
    response_model=NFeXmlInfoResponse,
    summary="Extrair informações principais da NFe (ide/emit/dest/totais/itens)",
)
def nfe_xml_info(payload: NFeXmlInfoRequest):
    """
    Converte o XML de NFe em DocSped e devolve apenas as informações principais,
    úteis para front ou análise rápida.
    """
    try:
        doc = xml_to_doc(payload.xml)
        data = doc_sped_to_dict(doc)

        ide = data.get("ide") or {}
        emit = data.get("emit") or {}
        dest = data.get("dest") or {}
        totais = data.get("totais") or data.get("total") or {}
        itens = data.get("itens") or []

        return NFeXmlInfoResponse(
            ide=ide,
            emit=emit,
            dest=dest,
            totais=totais,
            itens=itens,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao extrair info do XML: {e}")


# 👉 /nfe/analise – análise fiscal básica

@app.post(
    "/nfe/analise",
    response_model=NFeAnaliseResponse,
    summary="Análise fiscal básica da NFe (regime, ST, monofásico, CST etc.)",
)
def nfe_analise(payload: NFeAnaliseRequest):
    """
    Recebe o XML da NFe, converte para DocSped e devolve um resumo analítico:

    - Entrada/Saída (ide.tpNF)
    - Interna / Interestadual / Exterior (ide.idDest ou UF emit/dest)
    - Consumidor final
    - Situação do destinatário (indIEDest)
    - Regime do emitente (CRT)
    - Flags: possui ST, possui PIS/COFINS monofásico
    - Resumo de CST de ICMS, PIS e COFINS
    """
    try:
        doc = xml_to_doc(payload.xml)
        data = doc_sped_to_dict(doc)
        return _analisar_dados_nfe(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao analisar XML: {e}")
