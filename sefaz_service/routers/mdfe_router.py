# sefaz_service/routers/mdfe_router.py
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Literal

from sefaz_service.core.mdfe_status import sefaz_mdfe_status
from sefaz_service.core.mdfe_consulta import sefaz_mdfe_consulta
from sefaz_service.core.mdfe_envio import sefaz_mdfe_envio  # envio

router = APIRouter()


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
    senha: str = Field(..., description="Senha do certificado PFX")  # 👈 AQUI: nome do campo no JSON é "senha"
    xml: str = Field(..., description="XML do MDFe (sem assinatura; o serviço assina internamente)")


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
            senha_certificado=request.senha,  # 👈 mapeia o campo "senha" do JSON
        )
        return resultado
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erro ao enviar MDFe: {exc}")
