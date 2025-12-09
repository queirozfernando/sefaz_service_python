# sefaz_service/routers/mdfe_router.py
from __future__ import annotations

from typing import Literal, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from sefaz_service.core.mdfe_status import sefaz_mdfe_status
from sefaz_service.core.mdfe_consulta import sefaz_mdfe_consulta
from sefaz_service.core.mdfe_envio import sefaz_mdfe_envio
from sefaz_service.core.mdfe_cancelar import sefaz_mdfe_cancelar
from sefaz_service.core.mdfe_encerrar import sefaz_mdfe_encerrar
from sefaz_service.core.mdfe_incluir_condutor import sefaz_mdfe_inc_condutor
from sefaz_service.core.mdfe_pagamento import sefaz_mdfe_pagamento

router = APIRouter()


# --------------------------- MODELOS DE REQUEST --------------------------- #

class MDFeStatusRequest(BaseModel):
    uf: str = Field(..., min_length=2, max_length=2, description="UF do emitente, ex.: 'AC'")
    ambiente: Literal["1", "2"] = Field("2", description="1=Produção, 2=Homologação")
    certificado: str = Field(..., description="Caminho do .pfx no servidor")
    senha: str = Field(..., description="Senha do certificado PFX")


class MDFeConsultaRequest(BaseModel):
    uf: str = Field(..., min_length=2, max_length=2, description="UF do emitente, ex.: 'AC'")
    ambiente: Literal["1", "2"] = Field("2", description="1=Produção, 2=Homologação")
    chMDFe: str = Field(..., description="Chave completa do MDF-e (44 dígitos)")
    certificado: str = Field(..., description="Caminho do .pfx no servidor")
    senha: str = Field(..., description="Senha do certificado PFX")


class MDFeEnvioRequest(BaseModel):
    uf: str = Field(..., min_length=2, max_length=2, description="UF do emitente, ex.: 'AC'")
    ambiente: Literal["1", "2"] = Field("2", description="1=Produção, 2=Homologação")
    certificado: str = Field(..., description="Caminho do .pfx no servidor")
    senha: str = Field(..., description="Senha do certificado PFX")
    xml: str = Field(..., description="XML do MDFe (sem assinatura; o serviço assina internamente)")


class MDFeCancelamentoRequest(BaseModel):
    uf: str = Field(..., min_length=2, max_length=2, description="UF do emitente, ex.: 'AC'")
    ambiente: Literal["1", "2"] = Field("2", description="1=Produção, 2=Homologação")
    chMDFe: str = Field(..., description="Chave completa do MDF-e (44 dígitos)")
    nProt: str = Field(..., description="Número do protocolo de autorização do MDF-e")
    xJust: str = Field(..., min_length=15, max_length=255, description="Justificativa do cancelamento")
    certificado: str = Field(..., description="Caminho do .pfx no servidor")
    senha: str = Field(..., description="Senha do certificado PFX")
    nSeqEvento: str = Field("1", description="Sequencial do evento (1-99)")


class MDFeEncerramentoRequest(BaseModel):
    uf: str = Field(..., min_length=2, max_length=2, description="UF do emitente, ex.: 'AC'")
    ambiente: Literal["1", "2"] = Field("2", description="1=Produção, 2=Homologação")
    chMDFe: str = Field(..., description="Chave completa do MDF-e (44 dígitos)")
    nProt: str = Field(..., description="Número do protocolo de autorização do MDF-e")
    cMun: str = Field(..., description="Código IBGE do município de encerramento (7 dígitos)")
    certificado: str = Field(..., description="Caminho do .pfx no servidor")
    senha: str = Field(..., description="Senha do certificado PFX")
    nSeqEvento: str = Field("1", description="Sequencial do evento (1-99)")


class MDFeIncCondutorRequest(BaseModel):
    uf: str = Field(..., min_length=2, max_length=2, description="UF do emitente, ex.: 'AC'")
    ambiente: Literal["1", "2"] = Field("2", description="1=Produção, 2=Homologação")
    chMDFe: str = Field(..., description="Chave completa do MDF-e (44 dígitos)")
    cpf: str = Field(..., description="CPF do condutor (11 dígitos)")
    xNome: str = Field(..., description="Nome do condutor")
    nSeqEvento: str = Field("1", description="Sequencial do evento (1-99)")
    certificado: str = Field(..., description="Caminho do .pfx no servidor")
    senha: str = Field(..., description="Senha do certificado PFX")


class MDFePagamentoComp(BaseModel):
    tpComp: str = Field(..., description="Tipo do componente (01,02,03,99)")
    vComp: str = Field(..., description="Valor do componente")
    xComp: str | None = Field(None, description="Descrição quando tpComp=99 (Outros)")


class MDFePagamentoPrazo(BaseModel):
    nParcela: str = Field(..., description="Número da parcela")
    dVenc: str = Field(..., description="Data de vencimento AAAA-MM-DD")
    vParcela: str = Field(..., description="Valor da parcela")


class MDFePagamentoInfBanc(BaseModel):
    codBanco: str = Field(..., description="Código do banco")
    codAgencia: str = Field(..., description="Número da agência")
    CNPJIPEF: str = Field(..., description="CNPJ da IPEF")
    PIX: str | None = Field(None, description="Chave PIX para recebimento do frete")


class MDFePagamentoInfPag(BaseModel):
    xNome: str | None = Field(None, description="Nome/Razão social do responsável pelo pgto")
    CPF: str | None = Field(None, description="CPF do responsável pelo pgto")
    CNPJ: str | None = Field(None, description="CNPJ do responsável pelo pgto")
    idEstrangeiro: str | None = Field(None, description="Identificador do responsável estrangeiro")

    comps: List[MDFePagamentoComp] = Field(..., description="Componentes do pagamento (Comp)")
    vContrato: str = Field(..., description="Valor total do contrato")
    indAltoDesemp: str | None = Field(None, description="Indicador de alto desempenho (opcional)")
    indPag: str = Field(..., description="0=à vista, 1=a prazo")
    vAdiant: str | None = Field(None, description="Valor do adiantamento (se houver)")

    prazos: List[MDFePagamentoPrazo] | None = Field(
        None, description="Parcelas (infPrazo) – obrigatório se indPag=1"
    )
    infBanc: MDFePagamentoInfBanc = Field(..., description="Informações bancárias (infBanc)")


class MDFePagamentoRequest(BaseModel):
    uf: str = Field(..., min_length=2, max_length=2, description="UF do emitente, ex.: 'AC'")
    ambiente: Literal["1", "2"] = Field("2", description="1=Produção, 2=Homologação")
    chMDFe: str = Field(..., description="Chave completa do MDF-e (44 dígitos)")
    nProt: str = Field(..., description="Protocolo de autorização do MDF-e")
    qtdViagens: str = Field("00001", description="Quantidade total de viagens (5 dígitos)")
    nroViagem: str = Field("00001", description="Número de referência da viagem (5 dígitos)")
    nSeqEvento: str = Field("1", description="Sequencial do evento (1-99)")

    infPag: List[MDFePagamentoInfPag] = Field(
        ..., description="Lista de grupos infPag (pagamentos)"
    )

    certificado: str = Field(..., description="Caminho do .pfx no servidor")
    senha: str = Field(..., description="Senha do certificado PFX")


# --------------------------- ENDPOINTS --------------------------- #

@router.post("/status")
def mdfe_status(request: MDFeStatusRequest):
    res = sefaz_mdfe_status(
        uf=request.uf,
        ambiente=request.ambiente,
        certificado=request.certificado,
        senha=request.senha,
    )
    return {
        "status": res.status,
        "motivo": res.motivo,
        "xml_envio": res.xml_envio,
        "xml_retorno": res.xml_retorno,
    }


@router.post("/consulta")
def mdfe_consulta(request: MDFeConsultaRequest):
    res = sefaz_mdfe_consulta(
        uf=request.uf,
        ambiente=request.ambiente,
        chave=request.chMDFe,
        certificado=request.certificado,
        senha=request.senha,
    )
    return {
        "status": res.status,
        "motivo": res.motivo,
        "xml_envio": res.xml_envio,
        "xml_retorno": res.xml_retorno,
    }


@router.post("/envio")  # prefixo /mdfe vem do main.py
def mdfe_envio(request: MDFeEnvioRequest):
    """
    Envia um MDF-e (RecepcaoSinc v3.00).

    - O XML do MDFe é assinado internamente (tag infMDFe) com o PFX.
    - Se não existir <infMDFeSupl>, o QRCode é montado automaticamente.
    - Se cStat = 100, retorna também mdfeProc em `xml_autorizado`.
    """
    try:
        resultado = sefaz_mdfe_envio(
            xml=request.xml,
            uf=request.uf,
            ambiente=request.ambiente,
            certificado=request.certificado,
            senha_certificado=request.senha,
        )
        return resultado
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erro ao enviar MDFe: {exc}")


@router.post("/cancelar")
def mdfe_cancelar(request: MDFeCancelamentoRequest):
    """
    Evento 110111 – Cancelamento do MDF-e.
    """
    try:
        res = sefaz_mdfe_cancelar(
            uf=request.uf,
            ambiente=request.ambiente,
            chave=request.chMDFe,
            nprot=request.nProt,
            xjust=request.xJust,
            certificado=request.certificado,
            senha_certificado=request.senha,
            nseq_evento=request.nSeqEvento,
        )
        return {
            "status": res.status,
            "motivo": res.motivo,
            "xml_envio": res.xml_envio,
            "xml_retorno": res.xml_retorno,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erro ao cancelar MDFe: {exc}")


@router.post("/encerrar")
def mdfe_encerrar(request: MDFeEncerramentoRequest):
    """
    Encerramento de MDF-e autorizado (evento 110112).
    """
    try:
        res = sefaz_mdfe_encerrar(
            uf=request.uf,
            ambiente=request.ambiente,
            chave=request.chMDFe,
            nprot=request.nProt,
            cmun=request.cMun,
            certificado=request.certificado,
            senha_certificado=request.senha,
            nseq_evento=request.nSeqEvento,
        )
        return {
            "status": res.status,
            "motivo": res.motivo,
            "xml_envio": res.xml_envio,
            "xml_retorno": res.xml_retorno,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erro ao encerrar MDFe: {exc}")


@router.post("/incluir-condutor")
def mdfe_incluir_condutor(request: MDFeIncCondutorRequest):
    """
    Inclusão de Condutor em MDF-e (evento 110114).
    """
    try:
        res = sefaz_mdfe_inc_condutor(
            uf=request.uf,
            ambiente=request.ambiente,
            chave=request.chMDFe,
            cpf=request.cpf,
            xnome=request.xNome,
            certificado=request.certificado,
            senha_certificado=request.senha,
            nseq_evento=request.nSeqEvento,
        )
        return {
            "status": res.status,
            "motivo": res.motivo,
            "xml_envio": res.xml_envio,
            "xml_retorno": res.xml_retorno,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erro ao incluir condutor no MDFe: {exc}")


@router.post("/pagamento")
def mdfe_pagamento(request: MDFePagamentoRequest):
    """
    Evento 110116 – Pagamento da Operação de Transporte (evPagtoOperMDFe).
    """
    try:
        inf_pag_list = [ip.model_dump() for ip in request.infPag]

        res = sefaz_mdfe_pagamento(
            uf=request.uf,
            ambiente=request.ambiente,
            chave=request.chMDFe,
            nprot=request.nProt,
            qtd_viagens=request.qtdViagens,
            nro_viagem=request.nroViagem,
            inf_pag_list=inf_pag_list,
            certificado=request.certificado,
            senha_certificado=request.senha,
            nseq_evento=request.nSeqEvento,
        )
        return {
            "status": res.status,
            "motivo": res.motivo,
            "xml_envio": res.xml_envio,
            "xml_retorno": res.xml_retorno,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erro no evento de pagamento do MDFe: {exc}")
