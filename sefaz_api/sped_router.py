# sefaz_api/sped_router.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from sefaz_service.sped import xml_to_doc, doc_sped_to_dict

router = APIRouter(
    prefix="/sped",
    tags=["SPED"],
)


class XmlToDocRequest(BaseModel):
    xml: str


class XmlToDocResponse(BaseModel):
    data: dict  # DocSped convertido para dict


@router.post("/xmltodoc", response_model=XmlToDocResponse)
def convert_xml_to_doc(payload: XmlToDocRequest):
    """
    Recebe XML (NFe, por enquanto) e devolve a estrutura DocSped em JSON.
    """
    try:
        doc = xml_to_doc(payload.xml)
        return XmlToDocResponse(data=doc_sped_to_dict(doc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erro ao processar XML: {exc}")
