"""Gerenciamento de certificado digital A1 (.pfx) para NFC-e."""
import re
from datetime import date, datetime, timezone
from pathlib import Path


class CertificadoError(Exception):
    pass


class Certificado:

    @staticmethod
    def carregar(pfx_path: str, senha: str):
        """Carrega o .pfx e retorna (cert, key) — mantido para compatibilidade
        com NfceSefaz que usa os objetos para autenticação TLS mútua."""
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
    def assinar_xml(xml_str: str, pfx_path: str, senha: str) -> str:
        """
        Assina o XML com RSA-SHA1 e XMLDSig usando erpbrasil.assinatura.
        Suporta NFe/NFC-e (infNFe) e Eventos (infEvento).
        """
        try:
            from lxml import etree
            from erpbrasil.assinatura import Assinatura
            from erpbrasil.assinatura import certificado as cert_module

            senha_bytes = senha.encode() if isinstance(senha, str) else senha

            # Localizar o Id do elemento assinável (infNFe ou infEvento)
            match = re.search(r'Id="((?:NFe|ID)[^"]+)"', xml_str)
            if not match:
                raise CertificadoError(
                    "Elemento assinável (infNFe ou infEvento com Id) não encontrado no XML"
                )
            ref_id = match.group(1)

            # Parsear para elemento lxml (assina_xml2 exige elemento, não string)
            root = etree.fromstring(xml_str.encode("utf-8"))

            cert_obj = cert_module.Certificado(pfx_path, senha_bytes, raise_expirado=False)
            assinatura = Assinatura(cert_obj)
            # assina_xml2 retorna string; appenda Signature ao pai do elemento assinável
            xml_assinado = assinatura.assina_xml2(root, ref_id)
            return xml_assinado

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
        match = re.search(r"(\d{14})", subject)
        return match.group(1) if match else ""

    @staticmethod
    def info(pfx_path: str, senha: str) -> dict:
        """Retorna dict com cnpj, razao_social, validade, dias_restantes, vencido."""
        try:
            from cryptography import x509
            cert, _ = Certificado.carregar(pfx_path, senha)

            cn = ""
            try:
                cn = cert.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)[0].value
            except Exception:
                pass

            validade = cert.not_valid_after_utc.date()
            hoje = datetime.now(timezone.utc).date()
            dias = (validade - hoje).days
            cnpj = Certificado.cnpj_certificado(pfx_path, senha)

            return {
                "cnpj": cnpj,
                "razao_social": cn.split(":")[0].strip() if ":" in cn else cn,
                "validade": validade.strftime("%d/%m/%Y"),
                "dias_restantes": dias,
                "vencido": dias < 0,
            }
        except CertificadoError:
            raise
        except Exception as e:
            raise CertificadoError(f"Erro ao ler informações do certificado: {e}") from e
