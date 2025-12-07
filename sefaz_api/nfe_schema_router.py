from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from sefaz_service.validation import validate_xml, XMLValidationError


router = APIRouter(
    prefix="/nfe",
    tags=["NFe - Validação"],
)


class XMLValidationRequest(BaseModel):
    xml: str
    tipo: str = "nfe"


class XMLValidationResponse(BaseModel):
    valido: bool
    erros: list[str]
    tipo: str


@router.post("/validar-schema", response_model=XMLValidationResponse)
async def validar_schema(payload: XMLValidationRequest):
    if not payload.xml.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Campo 'xml' vazio."
        )

    try:
        valido, erros = validate_xml(payload.xml.encode("utf-8"), payload.tipo)
    except XMLValidationError as e:
        raise HTTPException(400, str(e))
    except FileNotFoundError as e:
        raise HTTPException(500, f"Erro interno: {e}")

    return XMLValidationResponse(valido=valido, erros=erros, tipo=payload.tipo)
