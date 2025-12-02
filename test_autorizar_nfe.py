# test_autorizar_nfe.py

from pathlib import Path
from sefaz_service.nfe.workflow import autorizar_nfe


def test_autorizar_nfe():
    """
    Teste completo da função autorizar_nfe:
      - Carrega XML de entrada
      - Assina
      - Envia para SEFAZ
      - Gera nfeProc
      - Salva enviados e retornos p/ depuração
    """

    # 🟦 Ajuste conforme sua máquina
    XML_PATH = r"exemplos/nfe_teste.xml"
    PFX_PATH = r"C:\PROJETOS\certificados\36400633000134 - BENE DO CAVACO COMERCIO DE PRODUTOS ALIMENTICIOS.pfx"
    PFX_PASSWORD = "12345678"

    # garante pastas
    Path("saida").mkdir(exist_ok=True)
    Path("exemplos").mkdir(exist_ok=True)

    # Carrega XML original
    with open(XML_PATH, "r", encoding="utf-8") as f:
        xml = f.read()

    # Executa o fluxo completo
    res = autorizar_nfe(
        xml_nfe=xml,
        uf="AC",                 # mude se necessário
        pfx_path=PFX_PATH,
        pfx_password=PFX_PASSWORD,
        ambiente="1",           # 1 = produção, 2 = homologação
    )

    print("\n===== RESULTADO DO TESTE =====")
    print("Autorizado:", res.autorizado)
    print("cStat     :", res.status)
    print("Motivo    :", res.motivo)

    # ----------------------------------------------------------------------
    # SALVAR ARQUIVOS PARA INSPEÇÃO
    # ----------------------------------------------------------------------

    # XML assinado
    if res.xml_assinado:
        Path("saida/nfe_assinada.xml").write_text(res.xml_assinado, encoding="utf-8")
        print(">> salvo: saida/nfe_assinada.xml")

    # enviNFe enviado para o SOAP
    if res.xml_envi_nfe:
        Path("saida/enviNFe.xml").write_text(res.xml_envi_nfe, encoding="utf-8")
        print(">> salvo: saida/enviNFe.xml")

    # SOAP completo (se workflow gerar)
    if getattr(res, "xml_soap", None):
        Path("saida/soap.xml").write_text(res.xml_soap, encoding="utf-8")
        print(">> salvo: saida/soap.xml")

    # Se autorizado → salva o nfeProc final
    if res.autorizado and res.xml_nfe_proc:
        Path("saida/nfe_autorizada.xml").write_text(res.xml_nfe_proc, encoding="utf-8")
        print(">> salvo: saida/nfe_autorizada.xml")

    # ----------------------------------------------------------------------
    # ASSERTS (mantidos)
    # ----------------------------------------------------------------------

    assert res.status is not None, "cStat não foi retornado"
    assert res.motivo is not None, "xMotivo não foi retornado"

    # fluxo geral precisa ter gerado esses 3 itens sem erro:
    assert res.xml_envi_nfe, "enviNFe não foi gerado"
    assert res.xml_assinado, "XML assinado não foi gerado"
    assert res.xml_retorno, "Não houve retorno da SEFAZ"


if __name__ == "__main__":
    test_autorizar_nfe()
