# test_assinatura.py
from pathlib import Path

from sefaz_service.core.assinatura import assinar_nfe_xml

PFX_PATH = r"C:\PROJETOS\certificados\36400633000134 - BENE DO CAVACO COMERCIO DE PRODUTOS ALIMENTICIOS.pfx"
PFX_PASSWORD = "12345678"

def main():
    xml_path = Path("exemplos") / "nfe_teste.xml"
    if not xml_path.exists():
        raise FileNotFoundError(
            f"Arquivo {xml_path} não encontrado. "
            f"Crie esse arquivo com o conteúdo da sua NFe (pode ser o nfeProc inteiro)."
        )

    xml = xml_path.read_text(encoding="utf-8")

    xml_assinado = assinar_nfe_xml(
        xml=xml,
        pfx_path=PFX_PATH,
        pfx_password=PFX_PASSWORD,
    )

    saida_path = Path("exemplos") / "nfe_teste_assinada.xml"
    saida_path.write_text(xml_assinado, encoding="utf-8")

    print("NFe assinada com sucesso!")
    print(f"Arquivo gerado: {saida_path}")

if __name__ == "__main__":
    main()
