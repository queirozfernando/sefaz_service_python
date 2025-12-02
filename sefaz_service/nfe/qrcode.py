# nfe/qrcode.py

def gerar_qrcode(
    xml_assinado: str,
    csc_id: str,
    csc_token: str,
    versao_qrcode: str = "2.00",
) -> str:
    """
    Stub de geração de QRCode para NFC-e.

    Neste momento APENAS devolve o xml_assinado sem alteração.
    Depois implementamos a lógica completa:
    - montar URL da consulta
    - calcular hash com CSC
    - incluir infNFeSupl / qrCode / urlChave.
    """
    # TODO: implementar geração real do QRCode NFC-e
    return xml_assinado
