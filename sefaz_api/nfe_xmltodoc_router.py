# sefaz_api/nfe_xmltodoc_router.py
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel, Field

from sefaz_service.sped import xml_to_doc, doc_sped_to_dict

router = APIRouter(
    prefix="/nfe",
    tags=["NFe XMLToDoc"],
)


class XmlToDocRequest(BaseModel):
    xml: str = Field(
        ...,
        description="XML completo da NFe/CTe/MDF-e (ex.: nfeProc, cteProc, mdfeProc) em formato de string JSON.",
    )


@router.post(
    "/xmltodoc",
    summary="Converter XML (enviado como string JSON) para objeto DocSped",
)
def nfe_xmltodoc(payload: XmlToDocRequest):
    """
    Versão que recebe o XML dentro de um JSON:

    {
      "xml": "<nfeProc>...</nfeProc>"
    }

    (necessário escapar aspas internas com \\")
    """
    try:
        doc = xml_to_doc(payload.xml)
        return doc_sped_to_dict(doc)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao processar XML (xmltodoc): {e}",
        )


@router.post(
    "/xmltodoc_raw",
    summary="Converter XML bruto para DocSped (enviar XML puro)",
)
async def nfe_xmltodoc_raw(
    xml: str = Body(
        ...,
        media_type="application/xml",
        description=(
            "XML completo da NFe/CTe/MDF-e **puro**, sem JSON. "
            "Exemplo: <?xml version=\"1.0\" encoding=\"UTF-8\"?><nfeProc>...</nfeProc>"
        ),
    ),
):
    """
    Versão mais prática: recebe **XML puro** no corpo da requisição.

    Exemplo (curl):

        curl -X POST "http://127.0.0.1:8000/nfe/xmltodoc_raw" \\
             -H "Content-Type: application/xml" \\
             --data-binary @nota.xml
    """
    try:
        if not xml or not xml.strip():
            raise HTTPException(
                status_code=400,
                detail="XML vazio ou não informado",
            )

        doc = xml_to_doc(xml)
        return doc_sped_to_dict(doc)
    except HTTPException:
        # Repassa erros de validação
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao processar XML bruto (xmltodoc_raw): {e}",
        )
