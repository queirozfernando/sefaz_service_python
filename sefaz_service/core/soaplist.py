# sefaz_service/core/soaplist.py
from __future__ import annotations

from .envio import EndpointInfo


# UFs atendidas pelo ambiente virtual SVRS para NFeAutorizacao4
# (lista pode ser ajustada depois, o importante agora é AC funcionar)
SVRS_UFS = {
    "AC", "AL", "AP", "DF", "ES", "PB", "PI",
    "RJ", "RN", "RO", "RR", "SC", "SE", "TO",
    "RS",
}


def get_nfe_autorizacao4_endpoint(uf: str, ambiente: str = "2") -> EndpointInfo:
    """
    Retorna o endpoint (URL + SOAPAction) do serviço NFeAutorizacao4
    para a UF e ambiente informados.

    - uf: sigla da UF (ex.: "AC", "SP", "PR")
    - ambiente: "1" = produção, "2" = homologação
    """
    uf = (uf or "").upper()
    ambiente = (ambiente or "2").strip()

    # SOAPAction é a mesma para todos os servidores NFeAutorizacao4
    soap_action = "http://www.portalfiscal.inf.br/nfe/wsdl/NFeAutorizacao4/nfeAutorizacaoLote"

    # ============================
    # 1) UFs atendidas pela SVRS
    # ============================
    if uf in SVRS_UFS:
        if ambiente == "1":  # produção
            url = "https://nfe.svrs.rs.gov.br/ws/NfeAutorizacao/NFeAutorizacao4.asmx"
        else:  # "2" homologação (default)
            url = "https://nfe-homologacao.svrs.rs.gov.br/ws/NfeAutorizacao/NFeAutorizacao4.asmx"
        return EndpointInfo(url=url, soap_action=soap_action)

    # ============================
    # 2) SP
    # ============================
    if uf == "SP":
        if ambiente == "1":
            url = "https://nfe.fazenda.sp.gov.br/ws/nfeautorizacao4.asmx"
        else:
            url = "https://homologacao.nfe.fazenda.sp.gov.br/ws/nfeautorizacao4.asmx"
        return EndpointInfo(url=url, soap_action=soap_action)

    # ============================
    # 3) PR
    # ============================
    if uf == "PR":
        if ambiente == "1":
            url = "https://nfe.sefa.pr.gov.br/nfe/NFeAutorizacao4"
        else:
            url = "https://homologacao.nfe.sefa.pr.gov.br/nfe/NFeAutorizacao4"
        return EndpointInfo(url=url, soap_action=soap_action)

    # ============================
    # 4) MG
    # ============================
    if uf == "MG":
        if ambiente == "1":
            url = "https://nfe.fazenda.mg.gov.br/nfe2/services/NFeAutorizacao4"
        else:
            url = "https://hnfe.fazenda.mg.gov.br/nfe2/services/NFeAutorizacao4"
        return EndpointInfo(url=url, soap_action=soap_action)

    # ============================
    # 5) GO
    # ============================
    if uf == "GO":
        if ambiente == "1":
            url = "https://nfe.sefaz.go.gov.br/nfe/services/NFeAutorizacao4"
        else:
            url = "https://homolog.sefaz.go.gov.br/nfe/services/NFeAutorizacao4"
        return EndpointInfo(url=url, soap_action=soap_action)

    # ============================
    # 6) MT
    # ============================
    if uf == "MT":
        if ambiente == "1":
            url = "https://nfe.sefaz.mt.gov.br/nfews/v2/services/NfeAutorizacao4"
        else:
            url = "https://homologacao.sefaz.mt.gov.br/nfews/v2/services/NfeAutorizacao4"
        return EndpointInfo(url=url, soap_action=soap_action)

    # ============================
    # 7) MS
    # ============================
    if uf == "MS":
        if ambiente == "1":
            url = "https://nfe.sefaz.ms.gov.br/ws/NFeAutorizacao4"
        else:
            url = "https://hom.nfe.sefaz.ms.gov.br/ws/NFeAutorizacao4"
        return EndpointInfo(url=url, soap_action=soap_action)

    # ============================
    # 8) BA
    # ============================
    if uf == "BA":
        if ambiente == "1":
            url = "https://nfe.sefaz.ba.gov.br/webservices/NFeAutorizacao4/NFeAutorizacao4.asmx"
        else:
            url = "https://hnfe.sefaz.ba.gov.br/webservices/NFeAutorizacao4/NFeAutorizacao4.asmx"
        return EndpointInfo(url=url, soap_action=soap_action)

    # ============================
    # 9) AM
    # ============================
    if uf == "AM":
        if ambiente == "1":
            url = "https://nfe.sefaz.am.gov.br/services2/services/NfeAutorizacao4"
        else:
            url = "https://homnfe.sefaz.am.gov.br/services2/services/NfeAutorizacao4"
        return EndpointInfo(url=url, soap_action=soap_action)

    # ============================
    # 10) PE
    # ============================
    if uf == "PE":
        if ambiente == "1":
            url = "https://nfe.sefaz.pe.gov.br/nfe-service/services/NFeAutorizacao4"
        else:
            url = "https://nfehomolog.sefaz.pe.gov.br/nfe-service/services/NFeAutorizacao4"
        return EndpointInfo(url=url, soap_action=soap_action)

    # ============================
    # 11) Fallback
    # ============================
    # Se cair aqui, vamos usar SVRS como "curinga",
    # só pra não quebrar. Você pode ir refinando depois.
    if ambiente == "1":
        url = "https://nfe.svrs.rs.gov.br/ws/NfeAutorizacao/NFeAutorizacao4.asmx"
    else:
        url = "https://nfe-homologacao.svrs.rs.gov.br/ws/NfeAutorizacao/NFeAutorizacao4.asmx"

    return EndpointInfo(url=url, soap_action=soap_action)
