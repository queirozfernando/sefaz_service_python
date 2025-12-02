# test_danfe.py
import os
from sefaz_service.danfe.danfe_html import gerar_danfe_html


def salvar(caminho: str, conteudo: str) -> None:
    """Salva o conteúdo em um arquivo, criando a pasta se não existir."""
    pasta = os.path.dirname(caminho)
    if pasta:
        os.makedirs(pasta, exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(conteudo)
    print(f">> salvo: {caminho}")


def main():
    # Caminho do XML autorizado (nfeProc) que você colocou
    xml_path = "saida/12251236400633000134550010000064771752004482.XML"

    print(f"Lendo XML autorizado: {xml_path}")

    # 1) Ler o nfeProc autorizado
    with open(xml_path, "r", encoding="utf-8") as f:
        xml_nfe_proc = f.read()

    # 2) Gerar DANFE HTML
    danfe_html = gerar_danfe_html(
        xml_nfe_proc=xml_nfe_proc,
        logo_url=None,  # coloque "logo.png" se quiser exibir o logo
    )

    # 3) Salvar o HTML do DANFE
    salvar("saida/danfe_teste.html", danfe_html)

    # 4) Tentar gerar PDF (opcional)
    try:
        from weasyprint import HTML

        HTML(string=danfe_html).write_pdf("saida/danfe_teste.pdf")
        print(">> salvo: saida/danfe_teste.pdf")
    except Exception as e:
        print("\n-----")
        print("Não foi possível gerar o PDF com o WeasyPrint.")
        print("Motivo técnico:", e)
        print("O DANFE em HTML foi gerado normalmente em 'saida/danfe_teste.html'.")
        print("Se quiser PDF depois, instale/configure o WeasyPrint corretamente.")
        print("-----\n")


if __name__ == "__main__":
    main()
