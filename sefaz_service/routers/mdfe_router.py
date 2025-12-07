# sefaz_service/routers/mdfe_router.py
from __future__ import annotations

from pathlib import Path
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from sefaz_service.core.mdfe_status import sefaz_mdfe_status
from sefaz_service.core.mdfe_consulta import (
    sefaz_mdfe_consulta,
    MDFeConsultaResult,
)

router = APIRouter()


# -------- STATUS -------- #

class MDFeStatusRequest(BaseModel):
    uf: str = Field(
        ...,
        min_length=2,
        max_length=2,
        description="UF do emitente (por ex.: 'AC')",
    )
    ambiente: Literal["1", "2"] = Field(
        "2",
        description="1=Produção, 2=Homologação",
    )
    certificado: str = Field(
        ...,
        description=(
            "Caminho completo do certificado A1 (.pfx). "
            "Ex.: 'c:\\\\certs\\\\bene.pfx'"
        ),
    )
    senha: str = Field(
        ...,
        description="Senha do certificado A1 (.pfx)",
    )


class MDFeStatusResponse(BaseModel):
    status: Optional[int]
    motivo: Optional[str]
    xml_envio: str
    xml_retorno: str


@router.post("/status", response_model=MDFeStatusResponse)
def mdfe_status(payload: MDFeStatusRequest):
    """
    Consulta STATUS do serviço de MDF-e (MDFeStatusServico).
    """
    cert_path = Path(payload.certificado)

    if not cert_path.is_file():
        raise HTTPException(
            status_code=400,
            detail=(
                "Caminho do certificado inválido ou arquivo não encontrado: "
                f"{cert_path}"
            ),
        )

    try:
        result = sefaz_mdfe_status(
            uf=payload.uf,
            pfx_path=str(cert_path),
            pfx_password=payload.senha,
            ambiente=payload.ambiente,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao consultar status do serviço MDF-e: {exc!s}",
        ) from exc

    return MDFeStatusResponse(
        status=result.status,
        motivo=result.motivo,
        xml_envio=result.xml_envio,
        xml_retorno=result.xml_retorno,
    )


# -------- CONSULTA POR CHAVE -------- #

class MDFeConsultaRequest(BaseModel):
    uf: str = Field(
        ...,
        min_length=2,
        max_length=2,
        description="UF do emitente (por ex.: 'AC')",
    )
    ambiente: Literal["1", "2"] = Field(
        "2",
        description="1=Produção, 2=Homologação",
    )
    certificado: str = Field(
        ...,
        description=(
            "Caminho completo do certificado A1 (.pfx). "
            "Ex.: 'c:\\\\certs\\\\bene.pfx'"
        ),
    )
    senha: str = Field(
        ...,
        description="Senha do certificado A1 (.pfx)",
    )
    chave: str = Field(
        ...,
        min_length=44,
        max_length=44,
        pattern=r"^\d{44}$",
        description="Chave completa do MDF-e (44 dígitos numéricos)",
    )


class MDFeConsultaResponse(BaseModel):
    status: Optional[int]
    motivo: Optional[str]
    xml_envio: str
    xml_retorno: str


@router.post("/consulta", response_model=MDFeConsultaResponse)
def mdfe_consulta(payload: MDFeConsultaRequest):
    """
    Consulta situação de um MDF-e pela chave de acesso (MDFeConsultaMDF).
    """
    cert_path = Path(payload.certificado)

    if not cert_path.is_file():
        raise HTTPException(
            status_code=400,
            detail=(
                "Caminho do certificado inválido ou arquivo não encontrado: "
                f"{cert_path}"
            ),
        )

    try:
        result: MDFeConsultaResult = sefaz_mdfe_consulta(
            uf=payload.uf,
            chave_mdfe=payload.chave,
            pfx_path=str(cert_path),
            pfx_password=payload.senha,
            ambiente=payload.ambiente,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao consultar MDF-e: {exc!s}",
        ) from exc

    return MDFeConsultaResponse(
        status=result.status,
        motivo=result.motivo,
        xml_envio=result.xml_envio,
        xml_retorno=result.xml_retorno,
    )
