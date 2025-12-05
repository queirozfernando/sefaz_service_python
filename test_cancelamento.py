# test_cancelamento.py

from sefaz_service.core.nfe_evento import EventoRequest, sefaz_enviar_evento


def main():
    # ============================
    # CONFIGURAÇÃO — AJUSTE AQUI
    # ============================
    UF = "AC"                               # Sigla da UF
    cOrgao = "12"                           # Código da UF (AC = 12)
    CNPJ = "12251136400633"                 # CNPJ do emitente (só números)
    CH_NFE = "35141225113640063300013550010000064741361285178"  # chave da NFe a cancelar
    PROTOCOLO_AUT = "123456789012345"       # protocolo de autorização da NFe

    PFX_PATH = r"C:\certificados\meucertificado.pfx"
    PFX_PASSWORD = "senha_do_certificado"

    JUSTIFICATIVA = "Cancelamento de teste na homologacao"

    # ============================
    # MONTAR REQUEST
    # ============================
    req = EventoRequest(
        tpAmb="2",                    # 2 = homologação, 1 = produção
        cOrgao=cOrgao,
        CNPJ=CNPJ,
        chNFe=CH_NFE,
        tpEvento="110111",            # cancelamento
        nSeqEvento=1,                 # normalmente 1 no primeiro cancelamento
        xJust=JUSTIFICATIVA,
        nProt=PROTOCOLO_AUT,
    )

    # ============================
    # ENVIAR EVENTO
    # ============================
    print(">>> Enviando evento de CANCELAMENTO...\n")

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
