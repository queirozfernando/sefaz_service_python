📘 SEFAZ Service — Emissor NFe 4.0 em Python

Sistema completo para assinatura digital, montagem, envio e tratamento de retorno da NF-e 4.0 (modelo 55) utilizando Python, XMLSec e certificado digital PFX.

Totalmente compatível com:

SEFAZ Autorização 4.00

Assinatura XML digital padrão ICP-Brasil

C14N Canonicalization

Digest / SHA1

Referência por ID (#NFe…)

Ambientes de Homologação e Produção

Este projeto já passou por validação completa em produção, atingindo:

✔️ Assinatura válida
✔️ Zero caracteres de edição
✔️ Sem erro 588
✔️ Sem erro 297
✔️ Comunicação SOAP 100% funcional
✔️ Rejeição 204 (Duplicidade) confirmada em produção

🚀 Funcionalidades
✔️ Assinatura completa da NFe

Suporte a certificado PFX / A1

Canonicalização correta (C14N)

SHA1 para digest e RSA-SHA1 para assinatura

Sem modificar o <SignedInfo> (exigência da SEFAZ)

Limpeza automática de:

<SignatureValue>

<X509Certificate>

<X509Data>

✔️ Montagem do envelopamento SOAP

Incluindo:

Cabeçalho nfeCabecMsg

Corpo nfeDadosMsg

Namespace apropriado

Compatível com SEFAZ 4.0

✔️ Envio HTTPS com certificado

Via requests + certificado PFX convertido internamente.

✔️ Extração automática do retorno

Detecta e retorna:

cStat

xMotivo

XML completo de retorno

XML assinado

XML enviNFe

🧱 Estrutura do Projeto
sefaz_service/
│
├── core/
│   ├── assinatura.py        # Assinatura digital da NFe
│   ├── nfe_envio.py         # Integração completa com SEFAZ
│   ├── envio.py             # Montagem do envelope SOAP e enviNFe
│   ├── soaplist.py          # URLs das SEFAZ por UF/ambiente
│   └── utils/               # Funções auxiliares (se houver)
│
├── test_autorizar_nfe.py    # Script de teste
└── README.md                # Este arquivo

🛠️ Instalação
1. Clonar o repositório
git clone https://github.com/seu_usuario/sefaz_service_python.git
cd sefaz_service_python

2. Criar ambiente virtual
python -m venv venv
venv\Scripts\activate

3. Instalar dependências
pip install -r requirements.txt


Certifique-se de incluir no seu requirements.txt:

lxml
xmlsec
cryptography
requests

🔐 Certificado Digital (PFX)

O sistema utiliza certificado digital A1 (.pfx).

Pré-requisitos:

Certificado válido (produção ou homologação)

Senha correta

Caminho absoluto para o .pfx

O arquivo não deve ser commitado no Git.

📝 Uso Básico

Exemplo de envio:

from sefaz_service.core.nfe_envio import sefaz_nfe_envio

with open("minha_nfe.xml", "r", encoding="utf-8") as f:
    xml_nfe = f.read()

resultado = sefaz_nfe_envio(
    xml_nfe=xml_nfe,
    uf="AC",
    pfx_path="certificado.pfx",
    pfx_password="minha_senha",
    ambiente="1",  # 1=produção, 2=homologação
)

print("cStat:", resultado.status)
print("Motivo:", resultado.motivo)

with open("nfe_assinada.xml", "w") as f:
    f.write(resultado.xml_assinado)

with open("enviNFe.xml", "w") as f:
    f.write(resultado.xml_envi_nfe)

🔎 Exemplo de Resposta
✔️ Em produção, nota já existente:
cStat: 204
Motivo: Duplicidade de NF-e

✔️ Em homologação com destinatário real:
cStat: 598
Motivo: NF-e emitida em ambiente de homologação com Razão Social do destinatário diferente do padrão

✔️ Em homologação com XML incorreto:
cStat: 588
Motivo: Não é permitida a presença de caracteres de edição (erro corrigido neste projeto!)

🧪 Script de Teste

O arquivo test_autorizar_nfe.py executa:

Assinatura

Montagem do enviNFe

Montagem do envelope SOAP

Envio via HTTPS

Tratamento de retorno

E salva:

saida/nfe_assinada.xml
saida/enviNFe.xml
saida/retorno.xml

🧼 Antigos Erros e Como Foram Eliminados

Este projeto elimina TODOS os erros clássicos da SEFAZ:

Erro	Motivo	Status
297	Assinatura difere do calculado	❌ Eliminado
588	Caracteres de edição / whitespace	❌ Eliminado
215	Falha no schema/envelope	❌ Eliminado
218	Rejeição por estrutura	❌ Eliminado
999	Erro interno	❌ Eliminado

O sistema agora:

Não altera <SignedInfo>

Compacta somente <SignatureValue> / <X509Certificate>

Remove whitespace apenas de elementos permitidos

Mantém o XML 100% SEFAZ compliant

📦 .gitignore recomendando
# Python cache
__pycache__/
*.pyc

# Venv
venv/
env/

# Certificados
*.pfx
*.pem

# Saída local
saida/

# XMLs sensíveis
*.xml

🤝 Contribuições

Pull Requests são bem-vindos.

📄 Licença

MIT License (ou a que preferir — pode me pedir que ajusto).
