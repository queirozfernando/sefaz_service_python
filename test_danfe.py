# test_danfe.py
import os
from lxml import etree
from sefaz_service.danfe.danfe_html import gerar_danfe_html_automatico

NFE_NS = "http://www.portalfiscal.inf.br/nfe"


def salvar(caminho: str, conteudo: str) -> None:
    """Salva o conteúdo em um arquivo, criando a pasta se não existir."""
    pasta = os.path.dirname(caminho)
    if pasta:
        os.makedirs(pasta, exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(conteudo)
    print(f">> salvo: {caminho}")


def extrair_chave(xml_str: str) -> str:
    """Extrai a chave de acesso (44 dígitos) do XML nfeProc ou NFe."""
    root = etree.fromstring(xml_str.encode("utf-8"))
    nfe = root.find(f".//{{{NFE_NS}}}NFe")
    if nfe is None:
        nfe = root

    inf_nfe = nfe.find(f".//{{{NFE_NS}}}infNFe")
    if inf_nfe is None:
        return "nota"

    chave = (inf_nfe.get("Id") or "").replace("NFe", "").strip()
    return chave if len(chave) >= 44 else "nota"


def main():
    # Caminho do XML autorizado
    xml_path = "saida/12251236400633000134650010000709661526183562.xml"

    print(f"Lendo XML autorizado: {xml_path}")

    with open(xml_path, "r", encoding="utf-8") as f:
        xml_nfe_proc = f.read()

    # Extrair chave de acesso
    chave = extrair_chave(xml_nfe_proc)

    # Gerar automaticamente DANFE ou CUPOM
    html = gerar_danfe_html_automatico(
        xml_or_path=xml_nfe_proc,
        logo_url=None,
    )

    # Salvar arquivo HTML usando a chave
    html_path = f"saida/{chave}.html"
    salvar(html_path, html)

    # Tentar gerar PDF também com o nome da chave
    try:
        from weasyprint import HTML

        pdf_path = f"saida/{chave}.pdf"
        HTML(string=html).write_pdf(pdf_path)
        print(f">> salvo: {pdf_path}")
    except Exception as e:
        print("\n-----")
        print("Não foi possível gerar o PDF com o WeasyPrint.")
        print("Motivo técnico:", e)
        print(f"O HTML foi gerado normalmente em '{html_path}'.")
        print("-----\n")


if __name__ == "__main__":
    main()
