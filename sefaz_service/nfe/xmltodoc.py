# sefaz_api/nfe_xmltodoc_router.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# 👇 agora o import correto, SEM o .nfe
from sefaz_service.sped import xml_to_doc, doc_sped_to_dict


router = APIRouter(
    prefix="/nfe",   # vai gerar /nfe/xmltodoc
    tags=["NFe"],
)


class XmlToDocRequest(BaseModel):
    xml: str


class XmlToDocResponse(BaseModel):
    data: dict


@router.post("/xmltodoc", response_model=XmlToDocResponse)
def convert_xml_to_doc(payload: XmlToDocRequest):
    """
    Recebe XML de NFe e devolve a estrutura DocSped em JSON.
    Endpoint final: /nfe/xmltodoc
    """
    try:
        doc = xml_to_doc(payload.xml)
        return XmlToDocResponse(data=doc_sped_to_dict(doc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erro ao processar XML: {exc}")
