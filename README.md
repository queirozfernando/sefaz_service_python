# SEFAZ Service API

API em Python (FastAPI) para comunicação com a SEFAZ e utilitários fiscais relacionados à NF-e:

- Autorização de NF-e
- Inutilização de numeração
- Eventos (cancelamento, carta de correção, cancelamento por substituição)
- Consulta de status de serviço e situação da NF-e
- Consulta de GTIN (SVRS)
- Leitura e análise de XML de NF-e (resumo, DocSped e análise tributária)

---

## Requisitos

- Python 3.11+ (recomendado)
- `pip` para instalar dependências
- Certificado digital A1 em arquivo `.pfx` (para os serviços que exigem certificado)

---

## Instalação

1. Clone o repositório:

   ```bash
   git clone https://github.com/seu-usuario/sefaz_service.git
   cd sefaz_service

2. (Opcional, mas recomendado) Crie e ative um ambiente virtual:

python -m venv venv
venv\Scripts\activate

3. Instale as dependências:

pip install -r requirements.txt

Configuração do certificado (opcional)

Algumas rotas usam um certificado padrão definido por variáveis de ambiente:

SEFAZ_PFX_PATH – caminho completo do arquivo .pfx

SEFAZ_PFX_PASSWORD – senha do certificado

Você pode defini-las no Windows, por exemplo:

set SEFAZ_PFX_PATH=C:\certificados\seu_certificado.pfx
set SEFAZ_PFX_PASSWORD=suasenha

Em várias rotas você também pode enviar o caminho do .pfx e a senha direto no JSON da requisição, sem depender das variáveis de ambiente.

Como iniciar a API

Na raiz do projeto existe o script:

start_sefaz_service.bat

Ele já chama o Uvicorn com a aplicação sefaz_api.main:app.

1. Via duplo clique

Dê dois cliques em start_sefaz_service.bat.

Uma janela de terminal será aberta com o servidor rodando.

A API ficará disponível, por padrão, em:

http://127.0.0.1:8000

Documentação Swagger: http://127.0.0.1:8000/docs

2. Via prompt de comando

Abra o Prompt de Comando na pasta do projeto e rode:

start_sefaz_service.bat

Rotas disponíveis
1. Autorização de NF-e

POST /nfe/enviar

Envia uma NF-e para autorização na SEFAZ.

Body (JSON):

{
  "uf": "AC",
  "ambiente": "2",
  "xml_nfe": "<NFe>...</NFe>",
  "certificado": "C:\\certificados\\certificado.pfx",
  "senha": "senha_do_certificado"
}


Retorno: status da SEFAZ, XML assinado, envio e retorno completos.

2. Inutilização de numeração

POST /nfe/inutilizar

Body (JSON):

{
  "uf": "AC",
  "cUF": "12",
  "tpAmb": "2",
  "ano": "25",
  "CNPJ": "12345678000199",
  "mod": "55",
  "serie": "1",
  "nNFIni": "100",
  "nNFFin": "120",
  "xJust": "Justificativa com pelo menos 15 caracteres"
}


Retorno: cStat, xMotivo, nProt, dhRecbto, XML bruto de retorno.

3. Eventos de NF-e
3.1 Cancelamento

POST /nfe/evento/cancelar

Body (JSON):

{
  "uf": "AC",
  "cOrgao": "12",
  "tpAmb": "2",
  "CNPJ": "12345678000199",
  "chNFe": "CHAVE_DA_NFE",
  "nProt": "PROTOCOLO_AUTORIZACAO",
  "xJust": "Justificativa do cancelamento...",
  "nSeqEvento": 1
}

3.2 Cancelamento por substituição (110112)

POST /nfe/evento/cancelar-substituicao

{
  "uf": "AC",
  "cOrgao": "12",
  "tpAmb": "2",
  "CNPJ": "12345678000199",
  "chNFe": "CHAVE_CANCELADA",
  "chNFeRef": "CHAVE_SUBSTITUTA",
  "nProt": "PROTOCOLO_AUTORIZACAO",
  "xJust": "Justificativa...",
  "nSeqEvento": 1
}

3.3 Carta de Correção (CC-e – 110110)

POST /nfe/evento/carta-correcao

{
  "uf": "AC",
  "cOrgao": "12",
  "tpAmb": "2",
  "CNPJ": "12345678000199",
  "chNFe": "CHAVE_DA_NFE",
  "nSeqEvento": 1,
  "xCorrecao": "Texto da correção, respeitando legislação..."
}

4. Status do serviço NFe

POST /nfe/status

Verifica se o serviço da SEFAZ está operacional (não é o status de uma nota específica).

{
  "uf": "AC",
  "ambiente": "2",
  "certificado": "C:\\certificados\\certificado.pfx",
  "senha": "senha_do_certificado"
}

5. Consulta de situação da NFe por chave

POST /nfe/consulta

{
  "uf": "AC",
  "ambiente": "2",
  "chNFe": "CHAVE_DA_NFE",
  "certificado": "C:\\certificados\\certificado.pfx",
  "senha": "senha_do_certificado"
}

6. Consulta de GTIN (SVRS)

POST /nfe/gtin

{
  "gtin": "7897062500066",
  "certificado": "C:\\certificados\\certificado.pfx",
  "senha": "senha_do_certificado"
}


Retorna status, motivo, XML de envio e retorno.

Rotas de XML bruto (sem JSON)

As rotas abaixo recebem XML puro no corpo da requisição, com Content-Type: application/xml.
Não é necessário escapar com \" nem envolver em JSON.

Você pode enviar, por exemplo, um <nfeProc>...</nfeProc> ou <NFe>...</NFe> inteiro.

7. Converter XML de NFe em DocSped

POST /nfe/xmltodoc

Body: XML bruto da NFe

Header: Content-Type: application/xml

Exemplo com curl:

curl -X POST "http://127.0.0.1:8000/nfe/xmltodoc" ^
  -H "Content-Type: application/xml" ^
  --data-binary "@nota.xml"


Retorno: objeto data com o DocSped convertido em dict (JSON).

8. Resumo do XML da NFe

POST /nfe/xmlinfo

Extrai informações resumidas da NFe diretamente do XML:

ide

emit

dest

totais

itens (com ICMS, PIS e COFINS básicos por item)

Exemplo:

curl -X POST "http://127.0.0.1:8000/nfe/xmlinfo" ^
  -H "Content-Type: application/xml" ^
  --data-binary "@nota.xml"


Retorno (exemplo simplificado):

{
  "ide": {
    "cUF": "12",
    "cNF": "78853377",
    "natOp": "Venda Mercadoria...",
    "mod": "55",
    "serie": "1",
    "nNF": "6491",
    "dhEmi": "2025-12-04T10:53:56-05:00",
    "tpNF": "1",
    "idDest": "1",
    "finNFe": "1",
    "indFinal": "1",
    "indPres": "1",
    "tpAmb": "1"
  },
  "emit": { "...": "..." },
  "dest": { "...": "..." },
  "totais": {
    "vProd": "1625.00",
    "vNF": "1576.25",
    "vDesc": "48.75",
    "vICMS": "0.00",
    "vST": "0.00",
    "vPIS": "26.01",
    "vCOFINS": "119.80",
    "vTotTrib": "574.93"
  },
  "itens": [
    {
      "nItem": 1,
      "cProd": "11395",
      "xProd": "COPO DESC...",
      "NCM": "39241000",
      "CEST": "1400300",
      "CFOP": "5405",
      "ICMS": { "CST": "60", "orig": "0", "...": null },
      "PIS": { "CST": "01", "vBC": "1576.25", "vPIS": "26.01" },
      "COFINS": { "CST": "01", "vBC": "1576.25", "vCOFINS": "119.80" }
    }
  ]
}

9. Análise tributária da NFe

POST /nfe/analise

Faz uma análise básica da NF-e a partir do XML:

ICMS:

operação interna/interestadual

consumidor final

contribuinte ou não

presença de ST

ICMS próprio

CSTs/CSOSN usados

PIS/COFINS:

CSTs utilizados

suspeita de regime monofásico/suspensão

Devolve também o resumo igual ao /nfe/xmlinfo.

Exemplo:

curl -X POST "http://127.0.0.1:8000/nfe/analise" ^
  -H "Content-Type: application/xml" ^
  --data-binary "@nota.xml"


Retorno (exemplo resumido):

{
  "ok": true,
  "mensagens": [
    "Operação interna (UF emitente = UF destinatário).",
    "Destinatário é consumidor final (indFinal=1).",
    "Emitente no regime normal (CRT=3).",
    "Nota com indícios de Substituição Tributária (CST ICMS de ST ou CEST preenchido).",
    "CSTs de PIS/COFINS não indicam regime monofásico típico.",
    "CSTs de PIS encontrados: 01.",
    "CSTs de COFINS encontrados: 01."
  ],
  "icms": {
    "uf_emit": "AC",
    "uf_dest": "AC",
    "operacao_interna": true,
    "consumidor_final": true,
    "contribuinte_destinatario": false,
    "indIEDest": "2",
    "regime_emitente": "3",
    "possui_st": true,
    "possui_icms_proprio": false,
    "csts_icms": ["60"],
    "observacoes": [ "... mesmos textos de cima ..." ]
  },
  "pis_cofins": {
    "csts_pis": ["01"],
    "csts_cofins": ["01"],
    "monofasico_suspeito": false,
    "observacoes": [ "... textos sobre PIS/COFINS ..." ]
  },
  "resumo": { "... mesmo formato do /nfe/xmlinfo ..." }
}

Documentação interativa (Swagger)

Depois de subir a API com start_sefaz_service.bat, acesse:

Swagger UI: http://127.0.0.1:8000/docs

Redoc: http://127.0.0.1:8000/redoc

Lá você pode testar todas as rotas, inclusive:

/nfe/xmltodoc

/nfe/xmlinfo

/nfe/analise

bastando colar o XML bruto no body (em application/xml).



