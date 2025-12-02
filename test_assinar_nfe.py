from pathlib import Path

from sefaz_service.nfe.assinatura import NFeXmlSigner


def main():
    # 1) Caminho do XML SEM assinatura
    xml_in_path = Path("exemplos/nfe_teste.xml")

    if not xml_in_path.exists():
        print(f"Arquivo XML não encontrado: {xml_in_path}")
        print("Verifique o caminho e o nome do arquivo.")
        return

    xml_original = xml_in_path.read_text(encoding="utf-8")

    # 2) Configuração do certificado PFX (ajuste para o seu caminho/senha)
    signer = NFeXmlSigner(
        pfx_path=r"C:\certs\meu_certificado.pfx",   # 👉 ajuste aqui
        pfx_password="minha_senha_do_pfx",          # 👉 e aqui
    )

    # 3) Assinar o bloco <infNFe>
    try:
        xml_assinado = signer.assinar_inf_nfe(xml_original)
    except Exception as exc:
        print("Erro ao assinar XML:")
        print(exc)
        return

    # 4) Mostrar no console
    print("=== XML ASSINADO ===")
    print(xml_assinado)
    print("-" * 80)

    # 5) Gravar em arquivo para você abrir no editor
    xml_out_path = Path("exemplos/nfe_assinada_py.xml")
    xml_out_path.write_text(xml_assinado, encoding="utf-8")
    print(f"XML assinado salvo em: {xml_out_path.resolve()}")


if __name__ == "__main__":
    main()
