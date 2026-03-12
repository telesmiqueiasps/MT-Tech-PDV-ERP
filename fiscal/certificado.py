"""Gerenciamento de certificado digital A1 (.pfx) para NFC-e."""
import os
import re
from datetime import date
from pathlib import Path

# SEFAZ NF-e usa RSA-SHA1 — garantir habilitado mesmo se importado fora do main
os.environ.setdefault("OPENSSL_CONF", "")
os.environ.setdefault("CRYPTOGRAPHY_ALLOW_SHA1_SIGNING", "1")


class CertificadoError(Exception):
    pass


class Certificado:
    @staticmethod
    def carregar(pfx_path: str, senha: str):
        """Carrega o .pfx e retorna (cert, key) da biblioteca cryptography."""
        try:
            from cryptography.hazmat.primitives.serialization.pkcs12 import load_key_and_certificates
            from cryptography.hazmat.backends import default_backend
            dados = Path(pfx_path).read_bytes()
            senha_bytes = senha.encode() if isinstance(senha, str) else senha
            key, cert, _ = load_key_and_certificates(dados, senha_bytes, default_backend())
            if cert is None or key is None:
                raise CertificadoError("Certificado ou chave não encontrados no arquivo .pfx")
            return cert, key
        except CertificadoError:
            raise
        except Exception as e:
            raise CertificadoError(f"Erro ao carregar certificado: {e}") from e

    @staticmethod
    def assinar_xml(xml_str: str, cert, key) -> str:
        """
        Assina o XML usando signxml com RSA-SHA1 (padrão SEFAZ NF-e 4.00).
        Retorna o XML assinado como string.
        """
        try:
            from lxml import etree
            from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat
            import signxml

            # Serializar cert e key para PEM
            key_pem = key.private_bytes(Encoding.PEM, PrivateFormat.TraditionalOpenSSL, NoEncryption())
            cert_pem = cert.public_bytes(Encoding.PEM)

            root = etree.fromstring(xml_str.encode("utf-8"))

            signer = signxml.XMLSigner(
                method=signxml.methods.enveloped,
                signature_algorithm="rsa-sha1",
                digest_algorithm="sha1",
                c14n_algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315",
            )

            # O elemento a ser referenciado é infNFe com Id
            ns = "http://www.portalfiscal.inf.br/nfe"
            inf_nfe = root.find(f"{{{ns}}}infNFe")
            if inf_nfe is None:
                raise CertificadoError("Elemento infNFe não encontrado no XML")

            signed_root = signer.sign(
                root,
                key=key_pem,
                cert=cert_pem,
                reference_uri=f"#{inf_nfe.get('Id')}",
            )
            return etree.tostring(signed_root, encoding="unicode")
        except CertificadoError:
            raise
        except Exception as e:
            raise CertificadoError(f"Erro ao assinar XML: {e}") from e

    @staticmethod
    def validade(pfx_path: str, senha: str) -> date:
        """Retorna a data de vencimento do certificado."""
        cert, _ = Certificado.carregar(pfx_path, senha)
        return cert.not_valid_after_utc.date()

    @staticmethod
    def cnpj_certificado(pfx_path: str, senha: str) -> str:
        """Extrai o CNPJ embutido no Subject do certificado."""
        cert, _ = Certificado.carregar(pfx_path, senha)
        subject = cert.subject.rfc4514_string()
        # CNPJ geralmente aparece como CNPJ=XXXXXXXXXXXXXXXXXX ou no CN
        match = re.search(r"(\d{14})", subject)
        return match.group(1) if match else ""
