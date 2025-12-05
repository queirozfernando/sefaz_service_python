# test_cancelamento_substituicao.py

from sefaz_service.core.nfe_evento import EventoRequest, sefaz_enviar_evento


def main():
    # ============================
    # CONFIGURAÇÃO — AJUSTE AQUI
    # ============================
    UF = "AC"
    cOrgao = "12"                           # AC = 12
    CNPJ = "12251136400633"

    CH_NFE_CANCELADA = "CHAVE_DA_NFE_A_CANCELAR_AQUI"
    CH_NFE_SUBSTITUTA = "CHAVE_DA_NFE_SUBSTITUTA_AQUI"
    PROTOCOLO_AUT = "123456789012345"       # protocolo da NFe que será cancelada

    PFX_PATH = r"C:\certificados\meucertificado.pfx"
    PFX_PASSWORD = "senha_do_certificado"

    JUSTIFICATIVA = "Cancelamento por substituicao em homologacao"

    # ============================
    # MONTAR REQUEST
    # ============================
    req = EventoRequest(
        tpAmb="2",                    # 2 = homologação
        cOrgao=cOrgao,
        CNPJ=CNPJ,
        chNFe=CH_NFE_CANCELADA,
        tpEvento="110112",            # cancelamento por substituição
        nSeqEvento=1,
        xJust=JUSTIFICATIVA,
        nProt=PROTOCOLO_AUT,
        chNFeRef=CH_NFE_SUBSTITUTA,   # chave da NFe que substitui
    )

    # ============================
    # ENVIAR EVENTO
    # ============================
    print(">>> Enviando evento de CANCELAMENTO POR SUBSTITUICAO...\n")

    res = sefaz_enviar_evento(
        req=req,
        uf=UF,
        pfx_path=PFX_PATH,
        pfx_password=PFX_PASSWORD,
    )

    # ============================
    # RESULTADO
    # ============================
    print("------------- RESULTADO -------------")
    print(f"cStat (lote)     : {res.cStat_lote}")
    print(f"Motivo (lote)    : {res.xMotivo_lote}")
    print(f"cStat (evento)   : {res.cStat_evento}")
    print(f"Motivo (evento)  : {res.xMotivo_evento}")
    print(f"Protocolo evento : {res.nProt_evento}")
    print("--------------------------------------\n")

    print("XML RETORNO:\n")
    print(res.xml_retorno)


if __name__ == "__main__":
    main()
