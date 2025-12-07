# sefaz_service/validation/xml_schema.py
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Tuple

from lxml import etree


# __file__ -> sefaz_service/validation/xml_schema.py
ROOT_DIR = Path(__file__).resolve().parent.parent.parent

# ---> caminho simplificado
SCHEMAS_DIR = ROOT_DIR / "schemas" / "PL_010b_NT2025_002_v1.30"

SCHEMA_FILES: Dict[str, str] = {
    "nfe": "nfe_v4.00.xsd",
    "leiauteNFe": "leiauteNFe_v4.00.xsd",
}


class XMLValidationError(Exception):
    pass


@lru_cache
def _get_schema(tipo: str) -> etree.XMLSchema:
    if tipo not in SCHEMA_FILES:
        raise XMLValidationError(f"Tipo de schema desconhecido: {tipo!r}")

    xsd_path = SCHEMAS_DIR / SCHEMA_FILES[tipo]
    if not xsd_path.exists():
        raise FileNotFoundError(f"Arquivo XSD não encontrado: {xsd_path}")

    parser = etree.XMLParser(remove_blank_text=True)
    with xsd_path.open("rb") as f:
        doc = etree.parse(f, parser)

    return etree.XMLSchema(doc)


def validate_xml(xml_bytes: bytes, tipo: str = "nfe") -> Tuple[bool, List[str]]:
    parser = etree.XMLParser(remove_blank_text=True)

    try:
        xml_doc = etree.fromstring(xml_bytes, parser=parser)
    except etree.XMLSyntaxError as exc:
        return False, [f"Erro de sintaxe XML: {exc}"]

    schema = _get_schema(tipo)
    ok = schema.validate(xml_doc)

    if ok:
        return True, []

    erros: List[str] = []
    for e in schema.error_log:
        erros.append(
            f"Linha {e.line}, coluna {e.column}: {e.message} "
            f"(tipo={e.type_name}, nível={e.level_name})"
        )

    return False, erros
