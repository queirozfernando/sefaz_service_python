# test_inutiliza.py
from sefaz_service.core.nfe_inutilizacao import (
    InutilizacaoRequest,
    enviar_inutilizacao,
)

def main():
    # =============================================
    # CONFIGURAÇÃO — AJUSTE AQUI
    # =============================================
    UF = "AC"                     # Sigla da UF
    CNPJ = "12251136400633"      # CNPJ do emitente (somente números)
    SERIE = "1"                  # Série
    NUM_INI = "100"              # Número inicial
    NUM_FIM = "100"              # Número final (pode ser igual)
    ANO = "25"                   # Ano da inutilização (dois dígitos)

    PFX_PATH = r"C:\PROJETOS\certificados\36400633000134 - BENE DO CAVACO COMERCIO DE PRODUTOS ALIMENTICIOS.pfx"
    PFX_PASSWORD = "12345678"

    JUSTIFICATIVA = "Inutilizacao de teste emitida pelo sefaz_service"

    # =============================================
    # MONTAR REQUEST
    # =============================================
    req = InutilizacaoRequest(
        cUF="12",            # AC = 12
        tpAmb="2",           # 2 = homologação / 1 = produção
        ano=ANO,
        CNPJ=CNPJ,
        mod="55",            # NFe = 55
        serie=SERIE,
        nNFIni=NUM_INI,
        nNFFin=NUM_FIM,
        xJust=JUSTIFICATIVA,
    )

    # =============================================
    # ENVIAR INUTILIZAÇÃO
    # =============================================
    print(">>> Enviando inutilização...\n")

    resp = enviar_inutilizacao(
        req=req,
        certificado=PFX_PATH,
        senha=PFX_PASSWORD,
        uf_sigla=UF,
    )

    # =============================================
    # RESULTADOS
    # =============================================
    print("------------- RESULTADO -------------")
    print(f"cStat      : {resp.cStat}")
    print(f"Motivo     : {resp.xMotivo}")
    print(f"Protocolo  : {resp.nProt}")
    print(f"Recebido em: {resp.dhRecbto}")
    print("--------------------------------------\n")

    # XML completo do retorno
    print("XML RETORNO:\n")
    print(resp.raw_xml)


if __name__ == "__main__":
    main()
