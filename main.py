from pathlib import Path

from sefaz_service.nfe.assinatura import NFeXmlSigner
from sefaz_service.nfe.envio import NFeEnvioService
from sefaz_service.core.enums import Ambiente
from sefaz_service.core.soap_client import SoapClient

def main():
    # 1. Ler XML sem assinatura
    xml_path = Path("exemplos/nfe_teste.xml")
    if not xml_path.exists():
        print(f"Arquivo XML não encontrado: {xml_path}")
        return

    xml_original = xml_path.read_text(encoding="utf-8")

    # 2. Assinar infNFe
    signer = NFeXmlSigner(
        pfx_path=r"C:\certs\meu_certificado.pfx",
        pfx_password="minha_senha_do_pfx",
    )
    xml_assinado = signer.assinar_inf_nfe(xml_original)

    print("=== XML ASSINADO ===")
    print(xml_assinado)
    print("-" * 80)

    # 3. Enviar para SEFAZ (agora de verdade, usando SoapClient com PFX)
    soap = SoapClient(
        pfx_path=r"C:\certs\meu_certificado.pfx",
        pfx_password="minha_senha_do_pfx",
        timeout=30,
    )

    nfe_envio = NFeEnvioService(
        uf="SP",
        ambiente=Ambiente.HOMOLOGACAO,
        soap_client=soap,
    )

    resposta = nfe_envio.enviar(
        xml_assinado=xml_assinado,
        modelo="55",           # 55 = NFe, 65 = NFC-e
        id_lote=1,
        envio_sincrono=True,
    )

    print("=== RESPOSTA DA SEFAZ ===")
    print(resposta)

if __name__ == "__main__":
    main()
