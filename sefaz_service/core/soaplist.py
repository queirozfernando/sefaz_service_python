# sefaz_service/core/soaplist.py
from __future__ import annotations

from .envio import EndpointInfo

# UFs atendidas pelo SVRS (tanto Autorização, Status quanto Consulta)
SVRS_UFS = {
    "AC", "AL", "AP", "DF", "ES", "PB", "PI",
    "RJ", "RN", "RO", "RR", "SC", "SE", "TO",
    "RS",
}

# ============================================================
# 1) NFeAutorizacao4 (envio de NFe)
# ============================================================

# UFs com endpoint próprio (fora SVRS) para AUTORIZAÇÃO
UF_AUT_ENDPOINTS = {
    "SP": {
        "1": "https://nfe.fazenda.sp.gov.br/ws/nfeautorizacao4.asmx",
        "2": "https://homologacao.nfe.fazenda.sp.gov.br/ws/nfeautorizacao4.asmx",
    },
    "PR": {
        "1": "https://nfe.sefa.pr.gov.br/nfe/NFeAutorizacao4",
        "2": "https://homologacao.nfe.sefa.pr.gov.br/nfe/NFeAutorizacao4",
    },
    "MG": {
        "1": "https://nfe.fazenda.mg.gov.br/nfe2/services/NFeAutorizacao4",
        "2": "https://hnfe.fazenda.mg.gov.br/nfe2/services/NFeAutorizacao4",
    },
    "GO": {
        "1": "https://nfe.sefaz.go.gov.br/nfe/services/NFeAutorizacao4",
        "2": "https://homolog.sefaz.go.gov.br/nfe/services/NFeAutorizacao4",
    },
    "MT": {
        "1": "https://nfe.sefaz.mt.gov.br/nfews/v2/services/NfeAutorizacao4",
        "2": "https://homologacao.sefaz.mt.gov.br/nfews/v2/services/NfeAutorizacao4",
    },
    "MS": {
        "1": "https://nfe.sefaz.ms.gov.br/ws/NFeAutorizacao4",
        "2": "https://hom.nfe.sefaz.ms.gov.br/ws/NFeAutorizacao4",
    },
    "BA": {
        "1": "https://nfe.sefaz.ba.gov.br/webservices/NFeAutorizacao4/NFeAutorizacao4.asmx",
        "2": "https://hnfe.sefaz.ba.gov.br/webservices/NFeAutorizacao4/NFeAutorizacao4.asmx",
    },
    "AM": {
        "1": "https://nfe.sefaz.am.gov.br/services2/services/NfeAutorizacao4",
        "2": "https://homnfe.sefaz.am.gov.br/services2/services/NfeAutorizacao4",
    },
    "PE": {
        "1": "https://nfe.sefaz.pe.gov.br/nfe-service/services/NFeAutorizacao4",
        "2": "https://nfehomolog.sefaz.pe.gov.br/nfe-service/services/NFeAutorizacao4",
    },
}

# SVRS para AUTORIZAÇÃO
SVRS_AUT_ENDPOINTS = {
    "1": "https://nfe.svrs.rs.gov.br/ws/NfeAutorizacao/NFeAutorizacao4.asmx",
    "2": "https://nfe-homologacao.svrs.rs.gov.br/ws/NfeAutorizacao/NFeAutorizacao4.asmx",
}

SOAP_ACTION_AUT = (
    "http://www.portalfiscal.inf.br/nfe/wsdl/NFeAutorizacao4/nfeAutorizacaoLote"
)


def get_nfe_autorizacao4_endpoint(uf: str, ambiente: str = "2") -> EndpointInfo:
    """
    Retorna o endpoint (URL + SOAPAction) do serviço NFeAutorizacao4
    para a UF e ambiente informados.
    """
    uf = (uf or "").upper()
    ambiente = (ambiente or "2").strip()
    if ambiente not in {"1", "2"}:
        ambiente = "2"

    # 1) UF com endpoint próprio
    if uf in UF_AUT_ENDPOINTS:
        url = UF_AUT_ENDPOINTS[uf][ambiente]
        return EndpointInfo(url=url, soap_action=SOAP_ACTION_AUT)

    # 2) UF atendida pela SVRS
    if uf in SVRS_UFS:
        url = SVRS_AUT_ENDPOINTS[ambiente]
        return EndpointInfo(url=url, soap_action=SOAP_ACTION_AUT)

    # 3) Fallback → SVRS
    url = SVRS_AUT_ENDPOINTS[ambiente]
    return EndpointInfo(url=url, soap_action=SOAP_ACTION_AUT)


# ============================================================
# 2) NFeStatusServico4 (consulta status do SERVIÇO)
# ============================================================

SOAP_ACTION_STATUS = (
    "http://www.portalfiscal.inf.br/nfe/wsdl/NFeStatusServico4/nfeStatusServicoNF"
)

# UFs com endpoint próprio para STATUS
UF_STATUS_ENDPOINTS = {
    "SP": {
        "1": "https://nfe.fazenda.sp.gov.br/ws/nfestatusservico4.asmx",
        "2": "https://homologacao.nfe.fazenda.sp.gov.br/ws/nfestatusservico4.asmx",
    },
    "PR": {
        "1": "https://nfe.sefa.pr.gov.br/nfe/NFeStatusServico4",
        "2": "https://homologacao.nfe.sefa.pr.gov.br/nfe/NFeStatusServico4",
    },
    "MG": {
        "1": "https://nfe.fazenda.mg.gov.br/nfe2/services/NFeStatusServico4",
        "2": "https://hnfe.fazenda.mg.gov.br/nfe2/services/NFeStatusServico4",
    },
    "GO": {
        "1": "https://nfe.sefaz.go.gov.br/nfe/services/NFeStatusServico4",
        "2": "https://homolog.sefaz.go.gov.br/nfe/services/NFeStatusServico4",
    },
    "MT": {
        "1": "https://nfe.sefaz.mt.gov.br/nfews/v2/services/NfeStatusServico4",
        "2": "https://homologacao.sefaz.mt.gov.br/nfews/v2/services/NfeStatusServico4",
    },
    "MS": {
        "1": "https://nfe.sefaz.ms.gov.br/ws/NFeStatusServico4",
        "2": "https://hom.nfe.sefaz.ms.gov.br/ws/NFeStatusServico4",
    },
    "BA": {
        "1": "https://nfe.sefaz.ba.gov.br/webservices/NFeStatusServico4/NFeStatusServico4.asmx",
        "2": "https://hnfe.sefaz.ba.gov.br/webservices/NFeStatusServico4/NFeStatusServico4.asmx",
    },
    "AM": {
        "1": "https://nfe.sefaz.am.gov.br/services2/services/NfeStatusServico4",
        "2": "https://homnfe.sefaz.am.gov.br/services2/services/NfeStatusServico4",
    },
    "PE": {
        "1": "https://nfe.sefaz.pe.gov.br/nfe-service/services/NFeStatusServico4",
        "2": "https://nfehomolog.sefaz.pe.gov.br/nfe-service/services/NFeStatusServico4",
    },
}

# SVRS para STATUS
SVRS_STATUS_ENDPOINTS = {
    "1": "https://nfe.svrs.rs.gov.br/ws/NfeStatusServico/NfeStatusServico4.asmx",
    "2": "https://nfe-homologacao.svrs.rs.gov.br/ws/NfeStatusServico/NfeStatusServico4.asmx",
}


def get_nfe_status_servico4_endpoint(uf: str, ambiente: str = "2") -> EndpointInfo:
    """
    Retorna o endpoint (URL + SOAPAction) do serviço NFeStatusServico4
    para a UF e ambiente informados.
    """
    uf = (uf or "").upper()
    ambiente = (ambiente or "2").strip()
    if ambiente not in {"1", "2"}:
        ambiente = "2"

    # 1) UF com endpoint próprio
    if uf in UF_STATUS_ENDPOINTS:
        url = UF_STATUS_ENDPOINTS[uf][ambiente]
        return EndpointInfo(url=url, soap_action=SOAP_ACTION_STATUS)

    # 2) UF atendida pela SVRS
    if uf in SVRS_UFS:
        url = SVRS_STATUS_ENDPOINTS[ambiente]
        return EndpointInfo(url=url, soap_action=SOAP_ACTION_STATUS)

    # 3) Fallback → SVRS
    url = SVRS_STATUS_ENDPOINTS[ambiente]
    return EndpointInfo(url=url, soap_action=SOAP_ACTION_STATUS)


# ============================================================
# 3) NFeConsultaProtocolo4 (consulta SITUAÇÃO por CHAVE)
# ============================================================

# Endpoints SVRS para NFeConsultaProtocolo4 (v4.00)
CONSULTA_SVRS_ENDPOINTS = {
    # Produção
    "1": "https://nfe.svrs.rs.gov.br/ws/NfeConsulta/NfeConsulta4.asmx",
    # Homologação
    "2": "https://nfe-homologacao.svrs.rs.gov.br/ws/NfeConsulta/NfeConsulta4.asmx",
}

SOAP_ACTION_CONSULTA = (
    "http://www.portalfiscal.inf.br/nfe/wsdl/NFeConsultaProtocolo4/nfeConsultaNF"
)

# Se quiser, depois você adiciona endpoints próprios de SP, PR, etc.
CONSULTA_UF_ENDPOINTS = {
    # Exemplo MG (ajuste conforme tabela oficial, se precisar):
    "MG": {
        "1": "https://nfe.fazenda.mg.gov.br/nfe2/services/NFeConsultaProtocolo4",
        "2": "https://hnfe.fazenda.mg.gov.br/nfe2/services/NFeConsultaProtocolo4",
    },
}


def get_nfe_consulta_protocolo4_endpoint(uf: str, ambiente: str = "2") -> EndpointInfo:
    """
    Retorna o endpoint (URL + SOAPAction) do serviço NFeConsultaProtocolo4
    para a UF e ambiente informados.
    """
    uf = (uf or "").upper()
    ambiente = (ambiente or "2").strip()
    if ambiente not in {"1", "2"}:
        ambiente = "2"

    # 1) UF com endpoint próprio
    if uf in CONSULTA_UF_ENDPOINTS:
        url = CONSULTA_UF_ENDPOINTS[uf][ambiente]
        return EndpointInfo(url=url, soap_action=SOAP_ACTION_CONSULTA)

    # 2) UFs atendidas pela SVRS
    if uf in SVRS_UFS:
        url = CONSULTA_SVRS_ENDPOINTS[ambiente]
        return EndpointInfo(url=url, soap_action=SOAP_ACTION_CONSULTA)

    # 3) Fallback → SVRS
    url = CONSULTA_SVRS_ENDPOINTS[ambiente]
    return EndpointInfo(url=url, soap_action=SOAP_ACTION_CONSULTA)


# ============================================================
# 4) Consulta GTIN (ccgConsGTIN)
# ============================================================

GTIN_ENDPOINT = "https://dfe-servico.svrs.rs.gov.br/ws/ccgConsGTIN/ccgConsGTIN.asmx"
GTIN_SOAP_ACTION = "http://www.portalfiscal.inf.br/nfe/wsdl/ccgConsGtin/ccgConsGTIN"


def get_nfe_cons_gtin_endpoint() -> EndpointInfo:
    """
    Endpoint fixo do serviço nacional de GTIN (SVRS).
    Não depende de UF nem de ambiente.
    """
    return EndpointInfo(url=GTIN_ENDPOINT, soap_action=GTIN_SOAP_ACTION)
