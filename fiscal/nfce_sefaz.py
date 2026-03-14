"""Comunicação com WebService da SEFAZ para NFC-e."""
import re
import requests
from fiscal.nfce_uf_config import NfceUfConfig, SVRS_URLS


class NfceSefaz:
    # Mantido para compatibilidade — código usa self._ws ao invés deste dict
    URLS_SVRS = SVRS_URLS

    def __init__(self, cert_path: str, cert_senha: str, ambiente: int = 2, uf: str = "PB"):
        from fiscal.certificado import Certificado
        self.cert_obj, self.key_obj = Certificado.carregar(cert_path, cert_senha)
        self.ambiente     = ambiente
        self._uf          = uf
        self._amb_key     = "homologacao" if ambiente == 2 else "producao"
        self._cert_path   = cert_path
        self._cert_senha  = cert_senha
        self._pem_cert, self._pem_key = self._exportar_pem()
        # URLs dos WebServices: lidas da tabela nfce_uf_config (fallback SVRS)
        self._ws = NfceUfConfig.ws_urls(uf, ambiente)

    def _exportar_pem(self):
        import tempfile, os
        from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat
        cert_pem = self.cert_obj.public_bytes(Encoding.PEM)
        key_pem  = self.key_obj.private_bytes(Encoding.PEM, PrivateFormat.TraditionalOpenSSL, NoEncryption())
        fd_cert, path_cert = tempfile.mkstemp(suffix=".pem")
        fd_key,  path_key  = tempfile.mkstemp(suffix=".pem")
        os.write(fd_cert, cert_pem)
        os.write(fd_key,  key_pem)
        os.close(fd_cert)
        os.close(fd_key)
        return path_cert, path_key

    @staticmethod
    def _limpar_xml(xml: str) -> str:
        """Remove whitespace entre tags — SEFAZ rejeita caracteres de edição."""
        xml = xml.strip()
        xml = re.sub(r'>\s+<', '><', xml)
        return xml

    def autorizar(self, xml_assinado: str) -> dict:
        """Envia NFC-e para autorização síncrona. Retorna dict com resultado."""
        import random
        NS = "http://www.portalfiscal.inf.br/nfe"
        id_lote = str(random.randint(1, 999_999_999_999_999)).zfill(15)
        # SEFAZ exige <envNFe> como wrapper — enviar NFe puro causa schema error
        env_nfe = (
            f'<enviNFe versao="4.00" xmlns="{NS}">'
            f'<idLote>{id_lote}</idLote>'
            f'<indSinc>1</indSinc>'
            f'{xml_assinado}'
            f'</enviNFe>'
        )
        url = self._ws["NFeAutorizacao"]
        # Não passar xml_assinado por _limpar_xml — removeria whitespace que
        # foi incluído no C14N durante a assinatura, invalidando o digest
        envelope = self._montar_envelope_soap_raw(env_nfe, "NFeAutorizacao4")
        # DEBUG: validar XML localmente contra XSD antes de enviar
        try:
            import pathlib
            from lxml import etree
            _xsd_path = pathlib.Path(__file__).parent.parent
            _schema_dir = None
            try:
                import nfelib
                _schema_dir = pathlib.Path(nfelib.__file__).parent / "nfe" / "schemas" / "v4_0"
            except Exception:
                pass
            if _schema_dir and (_schema_dir / "enviNFe_v4.00.xsd").exists():
                _xsd = etree.XMLSchema(etree.parse(str(_schema_dir / "enviNFe_v4.00.xsd")))
                _doc = etree.fromstring(env_nfe.encode("utf-8"))
                _erros = [f"Linha {e.line}: {e.message}" for e in _xsd.error_log] if not _xsd.validate(_doc) else []
                _relatorio = "\n".join(_erros) if _erros else "enviNFe VALIDO pelo XSD local"
                (_xsd_path / "debug_nfce_xsd_erros.txt").write_text(_relatorio, encoding="utf-8")
        except Exception as _ex:
            try:
                (_xsd_path / "debug_nfce_xsd_erros.txt").write_text(f"Validacao XSD falhou: {_ex}", encoding="utf-8")
            except Exception:
                pass
        # DEBUG: salvar envelope enviado
        try:
            import pathlib
            _dbg = pathlib.Path(__file__).parent.parent
            (_dbg / "debug_nfce_envelope.xml").write_text(envelope, encoding="utf-8")
        except Exception:
            pass
        try:
            response_xml = self._post(url, envelope)
            # DEBUG: salvar resposta
            try:
                import pathlib
                (pathlib.Path(__file__).parent.parent / "debug_nfce_resposta.xml").write_text(response_xml, encoding="utf-8")
            except Exception:
                pass
            return self._parsear_retorno_autorizacao(response_xml)
        except TimeoutError:
            return {"autorizada": False, "motivo": "Timeout — SEFAZ não respondeu",
                    "protocolo": "", "chave": "", "xml_retorno": ""}
        except Exception as e:
            return {"autorizada": False, "motivo": str(e),
                    "protocolo": "", "chave": "", "xml_retorno": ""}

    def consultar(self, chave_acesso: str) -> dict:
        """Consulta situação de uma chave de acesso na SEFAZ."""
        url = self._ws["NFeConsultaProtocolo"]
        envelope = self._montar_envelope_consulta(chave_acesso)
        try:
            response_xml = self._post(url, envelope)
            return self._parsear_retorno_consulta(response_xml)
        except Exception as e:
            return {"status": "ERRO", "motivo": str(e)}

    def consultar_servico(self) -> dict:
        """Consulta status do serviço SEFAZ via NFeStatusServico4."""
        url    = self._ws["NFeStatusServico"]
        c_uf   = NfceUfConfig.c_uf(self._uf)
        xml_cons = self._limpar_xml(
            f'<consStatServ xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00">'
            f'<tpAmb>{self.ambiente}</tpAmb>'
            f'<cUF>{c_uf}</cUF>'
            f'<xServ>STATUS</xServ>'
            f'</consStatServ>'
        )
        envelope = self._montar_envelope_soap(xml_cons, "NFeStatusServico4")
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": "http://www.portalfiscal.inf.br/nfe/wsdl/NFeStatusServico4/nfeStatusServicoNF",
        }
        try:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            resp = requests.post(url, data=envelope.encode("utf-8"), headers=headers,
                                 cert=(self._pem_cert, self._pem_key),
                                 timeout=30, verify=False)
            resp.raise_for_status()
            from lxml import etree
            root   = etree.fromstring(resp.content)
            ns     = "http://www.portalfiscal.inf.br/nfe"
            c_stat = root.findtext(f".//{{{ns}}}cStat") or "999"
            motivo = root.findtext(f".//{{{ns}}}xMotivo") or ""
            online = c_stat == "107"   # 107 = Serviço em Operação
            return {"online": online, "motivo": f"{c_stat} - {motivo}"}
        except Exception as e:
            return {"online": False, "motivo": str(e)}

    def _montar_envelope_soap(self, xml_conteudo: str, servico: str) -> str:
        """Envelope SOAP com _limpar_xml — usar apenas para XML sem assinatura."""
        xml_conteudo = self._limpar_xml(xml_conteudo)
        return self._montar_envelope_soap_raw(xml_conteudo, servico)

    def _montar_envelope_soap_raw(self, xml_conteudo: str, servico: str) -> str:
        """Envelope SOAP sem limpar whitespace — usar quando XML já está assinado."""
        return (
            '<?xml version="1.0" encoding="utf-8"?>'
            '<soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
            'xmlns:xsd="http://www.w3.org/2001/XMLSchema" '
            'xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">'
            '<soap12:Body>'
            f'<nfeDadosMsg xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/{servico}">'
            f'{xml_conteudo}'
            '</nfeDadosMsg>'
            '</soap12:Body>'
            '</soap12:Envelope>'
        )

    def _montar_envelope_consulta(self, chave: str) -> str:
        xml_cons = (
            f'<consSitNFe xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00">'
            f'<tpAmb>{self.ambiente}</tpAmb>'
            f'<xServ>CONSULTAR</xServ>'
            f'<chNFe>{chave}</chNFe>'
            f'</consSitNFe>'
        )
        return self._montar_envelope_soap(xml_cons, "NFeConsultaProtocolo4")

    def _post(self, url: str, envelope: str) -> str:
        headers = {
            "Content-Type": "application/soap+xml; charset=utf-8",
            "SOAPAction": "",
        }
        try:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            resp = requests.post(
                url, data=envelope.encode("utf-8"),
                headers=headers,
                cert=(self._pem_cert, self._pem_key),
                timeout=30,
                verify=False,
            )
            resp.raise_for_status()
            return resp.text
        except requests.Timeout:
            raise TimeoutError("SEFAZ não respondeu em 30 segundos")
        except requests.RequestException as e:
            raise RuntimeError(f"Erro na comunicação com SEFAZ: {e}") from e

    def _parsear_retorno_autorizacao(self, xml_resp: str) -> dict:
        try:
            from lxml import etree
            root = etree.fromstring(xml_resp.encode())
            ns   = "http://www.portalfiscal.inf.br/nfe"
            inf  = root.find(f".//{{{ns}}}infProt")
            if inf is None:
                motivo = root.findtext(f".//{{{ns}}}xMotivo") or "Resposta inválida"
                return {"autorizada": False, "motivo": motivo, "protocolo": "", "chave": "", "xml_retorno": xml_resp}
            c_stat    = inf.findtext(f"{{{ns}}}cStat") or ""
            x_motivo  = inf.findtext(f"{{{ns}}}xMotivo") or ""
            protocolo = inf.findtext(f"{{{ns}}}nProt") or ""
            chave     = inf.findtext(f"{{{ns}}}chNFe") or ""
            autorizada = c_stat in ("100",)
            return {
                "autorizada": autorizada,
                "motivo":     f"{c_stat} - {x_motivo}",
                "protocolo":  protocolo,
                "chave":      chave,
                "xml_retorno": xml_resp,
            }
        except Exception as e:
            return {"autorizada": False, "motivo": f"Erro ao parsear retorno: {e}",
                    "protocolo": "", "chave": "", "xml_retorno": xml_resp}

    def _parsear_retorno_consulta(self, xml_resp: str) -> dict:
        try:
            from lxml import etree
            root = etree.fromstring(xml_resp.encode())
            ns   = "http://www.portalfiscal.inf.br/nfe"
            c_stat   = root.findtext(f".//{{{ns}}}cStat") or "999"
            x_motivo = root.findtext(f".//{{{ns}}}xMotivo") or ""
            return {"status": c_stat, "motivo": f"{c_stat} - {x_motivo}"}
        except Exception as e:
            return {"status": "ERRO", "motivo": str(e)}

    def __del__(self):
        import os
        for path in (getattr(self, "_pem_cert", None), getattr(self, "_pem_key", None)):
            if path:
                try:
                    os.unlink(path)
                except Exception:
                    pass
