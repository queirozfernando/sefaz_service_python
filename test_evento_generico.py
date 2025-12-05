# test_evento_generico.py

from sefaz_service.core.nfe_evento import EventoRequest, sefaz_enviar_evento


def main():
    # ============================
    # CONFIGURAÇÃO — AJUSTE AQUI
    # ============================
    UF = "AC"
    cOrgao = "12"                       # código da UF (AC = 12)
    CNPJ = "12251136400633"

    CH_NFE = "CHAVE_DA_NFE_AQUI"
    TP_EVENTO = "110111"                # 110111 = cancelamento, 110112 = canc. substituição
    N_SEQ_EVENTO = 1

    PROTOCOLO_AUT = "123456789012345"   # obrigatório p/ cancelamento
    CH_NFE_REF = ""                     # se for 110112, colocar chave da NFe substituta

    PFX_PATH = r"C:\certificados\meucertificado.pfx"
    PFX_PASSWORD = "senha_do_certificado"

    JUSTIFICATIVA = "Teste de envio de evento generico na homologacao"

    # ============================
    # MONTAR REQUEST
    # ============================
    req = EventoRequest(
        tpAmb="2",                    # 2 = homologação
        cOrgao=cOrgao,
        CNPJ=CNPJ,
        chNFe=CH_NFE,
        tpEvento=TP_EVENTO,
        nSeqEvento=N_SEQ_EVENTO,
        xJust=JUSTIFICATIVA,
        nProt=PROTOCOLO_AUT if TP_EVENTO in ("110111", "110112") else None,
        chNFeRef=CH_NFE_REF or None,
    )

    # ============================
    # ENVIAR EVENTO
    # ============================
    print(f">>> Enviando evento tipo {TP_EVENTO}...\n")

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
