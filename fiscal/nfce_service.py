"""Orquestrador principal da emissão de NFC-e."""
from core.database import DatabaseManager
from core.session import Session


class NfceService:
    def emitir(self, venda_id: int) -> dict:
        """
        Fluxo completo de emissão de NFC-e.
        Nunca bloqueia a venda — retorna sempre um dict com resultado.
        """
        db = DatabaseManager.empresa()

        # 1. Carregar venda, itens e pagamentos
        from models.venda import Venda
        venda    = Venda.buscar_por_id(venda_id)
        itens    = Venda.itens(venda_id)
        pagtos   = Venda.pagamentos(venda_id)
        if not venda:
            return {"autorizada": False, "motivo": "Venda não encontrada"}

        # 2. Carregar config NFC-e
        from fiscal.nfce_config_model import NfceConfig
        config = NfceConfig.carregar()
        if not config or not config.get("cert_path"):
            return {"autorizada": False, "motivo": "NFC-e não configurada"}

        # 3. Carregar dados da empresa
        empresa = DatabaseManager.master().fetchone(
            "SELECT * FROM empresas WHERE id=?", (Session.empresa()["id"],)
        ) or {}

        # 4. Obter próximo número (atômico)
        numero = NfceConfig.proximo_numero()
        config["proximo_numero_usado"] = numero

        # 5. Construir XML
        from fiscal.nfce_builder import NfceBuilder
        xml_nao_assinado = NfceBuilder().construir(venda, itens, pagtos, config, empresa)

        # DEBUG: salvar XML não assinado para inspeção (na raiz do projeto)
        import pathlib
        _dbg_dir = pathlib.Path(__file__).parent.parent
        (_dbg_dir / "debug_nfce_nao_assinado.xml").write_text(xml_nao_assinado, encoding="utf-8")

        # 6. Assinar XML
        from fiscal.certificado import Certificado, CertificadoError
        try:
            xml_assinado = Certificado.assinar_xml(
                xml_nao_assinado, config["cert_path"], config.get("cert_senha", "")
            )
        except CertificadoError as e:
            return {"autorizada": False, "motivo": f"Erro no certificado: {e}"}

        # DEBUG: salvar XML assinado
        (_dbg_dir / "debug_nfce_assinado.xml").write_text(xml_assinado, encoding="utf-8")

        # 7. Salvar documento como PENDENTE
        from datetime import datetime
        chave = self._extrair_chave(xml_assinado)
        doc_id = db.execute(
            """INSERT INTO nfce_documentos
               (venda_id, numero, serie, chave_acesso, ambiente, status,
                xml_envio, data_emissao, valor_total)
               VALUES (?, ?, ?, ?, ?, 'PENDENTE', ?, ?, ?)""",
            (venda_id, numero, config.get("serie", 1), chave,
             config.get("ambiente", 2), xml_assinado,
             datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
             float(venda.get("total", 0))),
        )

        # 8. Enviar para SEFAZ
        from fiscal.nfce_sefaz import NfceSefaz
        sefaz = NfceSefaz(config["cert_path"], config.get("cert_senha", ""),
                          config.get("ambiente", 2))
        resultado = sefaz.autorizar(xml_assinado)

        # Log da comunicação
        db.execute(
            """INSERT INTO nfce_log (documento_id, operacao, request_xml, response_xml, erro)
               VALUES (?, 'AUTORIZAR', ?, ?, ?)""",
            (doc_id, xml_assinado, resultado.get("xml_retorno", ""),
             None if resultado["autorizada"] else resultado["motivo"]),
        )

        # 9. Atualizar status
        if resultado["autorizada"]:
            from datetime import datetime as dt
            xml_prot = resultado.get("xml_retorno", "")
            qr_url   = self._extrair_qrcode_url(xml_assinado)
            db.execute(
                """UPDATE nfce_documentos
                   SET status='AUTORIZADA', protocolo=?, xml_protocolo=?,
                       qrcode_url=?, url_consulta=?, data_autorizacao=?,
                       atualizado_em=datetime('now','localtime')
                   WHERE id=?""",
                (resultado["protocolo"], xml_prot, qr_url,
                 "http://www.sefaz.pb.gov.br/nfce",
                 dt.now().strftime("%Y-%m-%d %H:%M:%S"), doc_id),
            )
            # 9a. Gerar DANFE
            try:
                from fiscal.danfe_nfce import DanfeNfce
                danfe_path = DanfeNfce().gerar(doc_id, venda, itens, pagtos,
                                               config, empresa, resultado["protocolo"],
                                               chave, qr_url)
                db.execute("UPDATE nfce_documentos SET danfe_path=? WHERE id=?",
                           (danfe_path, doc_id))
                resultado["danfe_path"] = danfe_path
            except Exception as e:
                resultado["danfe_path"] = None
                resultado["danfe_erro"] = str(e)
        else:
            db.execute(
                """UPDATE nfce_documentos
                   SET status='REJEITADA', motivo_rejeicao=?,
                       atualizado_em=datetime('now','localtime')
                   WHERE id=?""",
                (resultado["motivo"], doc_id),
            )

        resultado["doc_id"]  = doc_id
        resultado["chave"]   = chave
        resultado["numero"]  = numero
        return resultado

    def cancelar(self, documento_id: int, motivo: str) -> dict:
        """Envia evento de cancelamento para a SEFAZ."""
        db  = DatabaseManager.empresa()
        doc = db.fetchone("SELECT * FROM nfce_documentos WHERE id=?", (documento_id,))
        if not doc:
            return {"ok": False, "motivo": "Documento não encontrado"}
        if doc["status"] != "AUTORIZADA":
            return {"ok": False, "motivo": "Apenas documentos AUTORIZADOS podem ser cancelados"}

        from fiscal.nfce_config_model import NfceConfig
        config = NfceConfig.carregar()
        if not config:
            return {"ok": False, "motivo": "Config NFC-e não encontrada"}

        from fiscal.nfce_sefaz import NfceSefaz
        from datetime import datetime
        sefaz    = NfceSefaz(config["cert_path"], config.get("cert_senha", ""),
                             config.get("ambiente", 2))
        chave    = doc["chave_acesso"]
        n_seq_ev = "1"
        dh_ev    = datetime.now().strftime("%Y-%m-%dT%H:%M:%S-03:00")
        xml_ev   = f"""<envEvento versao="1.00" xmlns="http://www.portalfiscal.inf.br/nfe">
  <idLote>1</idLote>
  <evento versao="1.00">
    <infEvento versao="1.00" Id="ID11011{chave}01">
      <cOrgao>91</cOrgao>
      <tpAmb>{config.get('ambiente', 2)}</tpAmb>
      <CNPJ>{doc.get('cnpj','')}</CNPJ>
      <chNFe>{chave}</chNFe>
      <dhEvento>{dh_ev}</dhEvento>
      <tpEvento>110111</tpEvento>
      <nSeqEvento>{n_seq_ev}</nSeqEvento>
      <verEvento>1.00</verEvento>
      <detEvento versao="1.00">
        <descEvento>Cancelamento</descEvento>
        <nProt>{doc.get('protocolo','')}</nProt>
        <xJust>{motivo[:255]}</xJust>
      </detEvento>
    </infEvento>
  </evento>
</envEvento>"""
        from fiscal.certificado import Certificado
        xml_ev_ass = Certificado.assinar_xml(
            xml_ev, config["cert_path"], config.get("cert_senha", "")
        )
        url = sefaz.URLS_SVRS[sefaz._amb_key]["NFeRecepcaoEvento"]
        try:
            resp_xml = sefaz._post(url, sefaz._montar_envelope_soap(xml_ev_ass, "NfceRecepcaoEvento4"))
            db.execute(
                "UPDATE nfce_documentos SET status='CANCELADA', atualizado_em=datetime('now','localtime') WHERE id=?",
                (documento_id,),
            )
            db.execute(
                "INSERT INTO nfce_log (documento_id, operacao, request_xml, response_xml) VALUES (?, 'CANCELAR', ?, ?)",
                (documento_id, xml_ev_ass, resp_xml),
            )
            return {"ok": True, "motivo": "Cancelamento enviado"}
        except Exception as e:
            return {"ok": False, "motivo": str(e)}

    def consultar_status_sefaz(self) -> dict:
        from fiscal.nfce_config_model import NfceConfig
        config = NfceConfig.carregar()
        if not config:
            return {"online": False, "motivo": "Config NFC-e não encontrada"}
        try:
            from fiscal.nfce_sefaz import NfceSefaz
            sefaz  = NfceSefaz(config["cert_path"], config.get("cert_senha", ""),
                               config.get("ambiente", 2))
            return sefaz.consultar_servico()
        except Exception as e:
            return {"online": False, "motivo": str(e)}

    @staticmethod
    def _extrair_chave(xml: str) -> str:
        import re
        m = re.search(r'Id="NFe(\d{44})"', xml)
        return m.group(1) if m else ""

    @staticmethod
    def _extrair_qrcode_url(xml: str) -> str:
        import re
        m = re.search(r"<qrCode>(.*?)</qrCode>", xml, re.DOTALL)
        return m.group(1) if m else ""
