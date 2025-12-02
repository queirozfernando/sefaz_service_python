# test_autorizar_nfe.py
import os
from sefaz_service.nfe.workflow import autorizar_nfe

def salvar(nome, conteudo):
    os.makedirs("saida", exist_ok=True)
    with open(f"saida/{nome}", "w", encoding="utf-8") as f:
        f.write(conteudo)
    print(f">> salvo: saida/{nome}")

def test_autorizar_nfe():
    # Carrega o XML original
    with open("xml_nfe.xml", "r", encoding="utf-8") as f:
        xml_nfe = f.read()

    # ENVIO
    res = autorizar_nfe(
        xml_nfe=xml_nfe,
        uf="AC",
        pfx_path="certificado.pfx",
        pfx_password="SENHA",
        ambiente="1",  # 1 = produção / 2 = homologação
    )

    print("\n===== RESULTADO DO ENVIO =====")
    print("Autorizado:", res.autorizado)
    print("cStat     :", res.status)
    print("Motivo    :", res.motivo)
    print()

    # Salvar sempre
    salvar("nfe_assinada.xml", res.xml_assinado)
    salvar("enviNFe.xml", res.xml_envi_nfe)
    salvar("retorno.xml", res.xml_retorno)
    salvar("protocolo.xml", res.xml_protocolo)

    # Se autorizado (100 ou 150), salvar nfeProc
    if res.xml_nfe_proc:
        salvar("nfeProc_autorizada.xml", res.xml_nfe_proc)
        print("XML AUTORIZADO GERADO COM SUCESSO!")

    # ===== VARIÁVEIS DISPONÍVEIS PARA FUTURO USO =====
    xml_assinado = res.xml_assinado
    xml_enviNFe = res.xml_envi_nfe
    xml_retorno = res.xml_retorno
    xml_protocolo = res.xml_protocolo
    xml_nfe_proc = res.xml_nfe_proc  # pode ser None

    # Exemplo de uso futuro (apenas mostrando que agora é fácil)
    print("\n===== VARIÁVEIS CARREGADAS =====")
    print("xml_assinado.....:", "OK" if xml_assinado else "ERRO")
    print("xml_enviNFe......:", "OK" if xml_enviNFe else "ERRO")
    print("xml_retorno......:", "OK" if xml_retorno else "ERRO")
    print("xml_protocolo....:", "OK" if xml_protocolo else "ERRO")
    print("xml_nfe_proc.....:", "OK" if xml_nfe_proc else "NÃO GERADO")

    return res  # permite uso programático (ex: dentro de outro script)


if __name__ == "__main__":
    test_autorizar_nfe()
