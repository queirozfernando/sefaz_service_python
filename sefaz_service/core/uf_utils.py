# sefaz_service/core/uf_utils.py

# -----------------------------------------------------------
# Tabela UF → cUF (válida para NFe, NFCe, CTe, MDFe etc.)
# -----------------------------------------------------------

def uf_to_cuf(uf: str) -> str:
    """
    Converte UF (AC, AL, ...) para código numérico cUF (12, 27, ...),
    usado em NFe, CTe, MDFe e eventos.
    """
    uf = (uf or "").upper()

    mapa = {
        "RO": "11",
        "AC": "12",
        "AM": "13",
        "RR": "14",
        "PA": "15",
        "AP": "16",
        "TO": "17",
        "MA": "21",
        "PI": "22",
        "CE": "23",
        "RN": "24",
        "PB": "25",
        "PE": "26",
        "AL": "27",
        "SE": "28",
        "BA": "29",
        "MG": "31",
        "ES": "32",
        "RJ": "33",
        "SP": "35",
        "PR": "41",
        "SC": "42",
        "RS": "43",
        "MS": "50",
        "MT": "51",
        "GO": "52",
        "DF": "53",
    }

    try:
        return mapa[uf]
    except KeyError:
        raise ValueError(f"UF não mapeada para cUF: {uf}")


# -----------------------------------------------------------
# URLs de serviços MDFe — ambiente nacional (SVRS)
# -----------------------------------------------------------

def mdfe_url_status(ambiente: str) -> str:
    """URL do serviço MDFeStatusServico (SVRS)."""
    if ambiente == "1":
        return "https://mdfe.svrs.rs.gov.br/ws/MDFeStatusServico/MDFeStatusServico.asmx"
    return "https://mdfe-homologacao.svrs.rs.gov.br/ws/MDFeStatusServico/MDFeStatusServico.asmx"


def mdfe_url_consulta(ambiente: str) -> str:
    """URL do serviço MDFeConsulta (SVRS)."""
    if ambiente == "1":
        return "https://mdfe.svrs.rs.gov.br/ws/MDFeConsulta/MDFeConsulta.asmx"
    return "https://mdfe-homologacao.svrs.rs.gov.br/ws/MDFeConsulta/MDFeConsulta.asmx"


def mdfe_url_recepcao(ambiente: str) -> str:
    """URL do serviço MDFeRecepcaoEvento (geral)."""
    if ambiente == "1":
        return "https://mdfe.svrs.rs.gov.br/ws/MDFeRecepcao/MDFeRecepcao.asmx"
    return "https://mdfe-homologacao.svrs.rs.gov.br/ws/MDFeRecepcao/MDFeRecepcao.asmx"


def mdfe_url_recepcao_sinc(ambiente: str) -> str:
    """URL para envio síncrono do MDFe (modelo 58)."""
    if ambiente == "1":
        return "https://mdfe.svrs.rs.gov.br/ws/MDFeRecepcaoSinc/MDFeRecepcaoSinc.asmx"
    return "https://mdfe-homologacao.svrs.rs.gov.br/ws/MDFeRecepcaoSinc/MDFeRecepcaoSinc.asmx"


def mdfe_url_recepcao_evento(ambiente: str) -> str:
    """URL do serviço MDFeRecepcaoEvento (pagamento, cancelamento, encerramento etc.)."""
    if ambiente == "1":
        return "https://mdfe.svrs.rs.gov.br/ws/MDFeRecepcaoEvento/MDFeRecepcaoEvento.asmx"
    return "https://mdfe-homologacao.svrs.rs.gov.br/ws/MDFeRecepcaoEvento/MDFeRecepcaoEvento.asmx"
