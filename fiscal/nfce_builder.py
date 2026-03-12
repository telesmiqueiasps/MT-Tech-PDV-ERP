"""Construtor do XML da NFC-e (layout 4.00) para Simples Nacional."""
import re
import random
import hashlib
from datetime import datetime


_FORMA_PAG_MAP = {
    "DINHEIRO": "01",
    "CHEQUE":   "02",
    "CREDITO":  "03",
    "DEBITO":   "04",
    "VA":       "10",  # Vale Alimentação
    "VR":       "13",  # Vale Refeição
    "BOLETO":   "15",
    "PIX":      "17",
    "OUTROS":   "99",
    "SEMVALOR": "90",
}


class NfceBuilder:
    NS = "http://www.portalfiscal.inf.br/nfe"

    def construir(self, venda: dict, itens: list, pagamentos: list,
                  config: dict, empresa: dict) -> str:
        """Retorna XML não assinado da NFC-e."""
        numero   = config["proximo_numero_usado"]  # já reservado antes de chamar
        serie    = config.get("serie", 1)
        ambiente = config.get("ambiente", 2)
        cnpj     = re.sub(r"\D", "", empresa.get("cnpj", ""))
        c_nf     = str(random.randint(10000000, 99999999))
        c_uf     = "25"  # PB
        mod      = "65"
        serie_str = str(serie).zfill(3)
        n_nf_str  = str(numero).zfill(9)
        tp_emis   = "1"
        dh_emi    = datetime.now().strftime("%Y-%m-%dT%H:%M:%S-03:00")
        c_mun_fg  = empresa.get("cod_municipio_ibge", "2507507")  # Campina Grande/PB default

        # Chave de acesso
        aamm = datetime.now().strftime("%y%m")
        chave_sem_dv = f"{c_uf}{aamm}{cnpj}{mod}{serie_str}{n_nf_str}{tp_emis}{c_nf}"
        c_dv = self._calcular_dv(chave_sem_dv)
        chave = chave_sem_dv + str(c_dv)

        # Totais
        v_prod = sum(float(i.get("subtotal", 0)) for i in itens)
        v_desc = float(venda.get("desconto_valor", 0) or 0)
        v_nf   = float(venda.get("total", v_prod - v_desc))

        # QR Code URL (SVRS homologação PB)
        qr_url = self._gerar_qrcode_url(chave, ambiente, config, dh_emi, v_nf)
        url_consulta = "https://www.sefaz.rs.gov.br/NFCE/NFCE-COM.aspx"

        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<nfeProc versao="4.00" xmlns="{self.NS}">
<NFe xmlns="{self.NS}">
<infNFe versao="4.00" Id="NFe{chave}">
<ide>
  <cUF>{c_uf}</cUF>
  <cNF>{c_nf}</cNF>
  <natOp>VENDA AO CONSUMIDOR</natOp>
  <mod>{mod}</mod>
  <serie>{serie}</serie>
  <nNF>{numero}</nNF>
  <dhEmi>{dh_emi}</dhEmi>
  <tpNF>1</tpNF>
  <idDest>1</idDest>
  <cMunFG>{c_mun_fg}</cMunFG>
  <tpImp>4</tpImp>
  <tpEmis>{tp_emis}</tpEmis>
  <cDV>{c_dv}</cDV>
  <tpAmb>{ambiente}</tpAmb>
  <finNFe>1</finNFe>
  <indFinal>1</indFinal>
  <indPres>1</indPres>
  <verProc>MTTech PDV 1.0</verProc>
</ide>
<emit>
  <CNPJ>{cnpj}</CNPJ>
  <xNome>{self._esc(empresa.get("razao_social") or empresa.get("nome", ""))[:60]}</xNome>
  <xFant>{self._esc(empresa.get("nome", ""))[:60]}</xFant>
  <enderEmit>
    <xLgr>{self._esc(empresa.get("endereco", "RUA") or "RUA")[:60]}</xLgr>
    <nro>{self._esc(empresa.get("numero", "S/N") or "S/N")[:60]}</nro>
    <xBairro>{self._esc(empresa.get("bairro", "CENTRO") or "CENTRO")[:60]}</xBairro>
    <cMun>{c_mun_fg}</cMun>
    <xMun>{self._esc(empresa.get("cidade", "CAMPINA GRANDE") or "CAMPINA GRANDE")[:60]}</xMun>
    <UF>{empresa.get("estado", "PB")}</UF>
    <CEP>{re.sub(r"\D", "", empresa.get("cep", "58400000") or "58400000")}</CEP>
    <cPais>1058</cPais>
    <xPais>BRASIL</xPais>
  </enderEmit>
  <IE>{re.sub(r"\D", "", empresa.get("inscricao_estadual", "ISENTO") or "ISENTO")}</IE>
  <CRT>1</CRT>
</emit>
<dest>
  <xNome>NF-E EMITIDA EM AMBIENTE DE HOMOLOGACAO - SEM VALOR FISCAL</xNome>
  <indIEDest>9</indIEDest>
</dest>
{self._itens_xml(itens)}
<total>
  <ICMSTot>
    <vBC>0.00</vBC><vICMS>0.00</vICMS><vICMSDeson>0.00</vICMSDeson>
    <vFCP>0.00</vFCP><vBCST>0.00</vBCST><vST>0.00</vST>
    <vFCPST>0.00</vFCPST><vFCPSTRet>0.00</vFCPSTRet>
    <vProd>{v_prod:.2f}</vProd><vFrete>0.00</vFrete><vSeg>0.00</vSeg>
    <vDesc>{v_desc:.2f}</vDesc><vII>0.00</vII><vIPI>0.00</vIPI>
    <vIPIDevol>0.00</vIPIDevol><vPIS>0.00</vPIS><vCOFINS>0.00</vCOFINS>
    <vOutro>0.00</vOutro><vNF>{v_nf:.2f}</vNF>
  </ICMSTot>
</total>
<transp><modFrete>9</modFrete></transp>
{self._pag_xml(pagamentos, v_nf)}
<infAdic>
  <infCpl>DOCUMENTO EMITIDO POR ME OU EPP OPTANTE PELO SIMPLES NACIONAL</infCpl>
</infAdic>
<infNFeSupl>
  <qrCode>{self._esc(qr_url)}</qrCode>
  <urlChave>{url_consulta}</urlChave>
</infNFeSupl>
</infNFe>
</NFe>
</nfeProc>"""
        return xml

    def _itens_xml(self, itens: list) -> str:
        partes = []
        for n, item in enumerate(itens, 1):
            cod    = self._esc(str(item.get("codigo") or item.get("produto_id", n)))[:60]
            ean    = self._esc(str(item.get("ean") or "SEM GTIN"))
            xprod  = self._esc(str(item.get("produto_nome", ""))[:120])
            ncm    = re.sub(r"\D", "", str(item.get("ncm") or "00000000")).zfill(8)[:8]
            qtd    = float(item.get("quantidade", 1))
            v_unit = float(item.get("preco_unitario", 0))
            v_prod = float(item.get("subtotal", qtd * v_unit))
            unid   = self._esc(str(item.get("unidade", "UN") or "UN"))[:6]
            partes.append(f"""<det nItem="{n}">
<prod>
  <cProd>{cod}</cProd>
  <cEAN>{ean}</cEAN>
  <xProd>{xprod}</xProd>
  <NCM>{ncm}</NCM>
  <CFOP>5102</CFOP>
  <uCom>{unid}</uCom>
  <qCom>{qtd:.4f}</qCom>
  <vUnCom>{v_unit:.10f}</vUnCom>
  <vProd>{v_prod:.2f}</vProd>
  <cEANTrib>{ean}</cEANTrib>
  <uTrib>{unid}</uTrib>
  <qTrib>{qtd:.4f}</qTrib>
  <vUnTrib>{v_unit:.10f}</vUnTrib>
  <indTot>1</indTot>
</prod>
<imposto>
  <ICMS>
    <ICMSSN400><orig>0</orig><CSOSN>400</CSOSN></ICMSSN400>
  </ICMS>
  <PIS>
    <PISAliq><CST>07</CST><vBC>0.00</vBC><pPIS>0.00</pPIS><vPIS>0.00</vPIS></PISAliq>
  </PIS>
  <COFINS>
    <COFINSAliq><CST>07</CST><vBC>0.00</vBC><pCOFINS>0.00</pCOFINS><vCOFINS>0.00</vCOFINS></COFINSAliq>
  </COFINS>
</imposto>
</det>""")
        return "\n".join(partes)

    def _pag_xml(self, pagamentos: list, v_nf: float) -> str:
        if not pagamentos:
            return f"<pag><detPag><tPag>01</tPag><vPag>{v_nf:.2f}</vPag></detPag></pag>"
        partes = ["<pag>"]
        for p in pagamentos:
            forma = _FORMA_PAG_MAP.get(str(p.get("forma", "")).upper(), "99")
            valor = float(p.get("valor", 0))
            partes.append(f"<detPag><tPag>{forma}</tPag><vPag>{valor:.2f}</vPag></detPag>")
        partes.append("</pag>")
        return "\n".join(partes)

    def _gerar_qrcode_url(self, chave: str, ambiente: int,
                           config: dict, dh_emi: str, v_nf: float) -> str:
        csc_id    = config.get("id_csc") or config.get("csc_id") or "000001"
        csc_token = config.get("csc_token") or ""
        base_url  = "https://www.sefaz.rs.gov.br/NFCE/NFCE-COM.aspx"
        # Hash SHA-1: chave + tpAmb + cIdToken + csc_token
        c_hash_str = f"{chave}|{ambiente}|{csc_id}|{csc_token}"
        c_hash = hashlib.sha1(c_hash_str.encode()).hexdigest().upper()
        return f"{base_url}?p={chave}|{ambiente}|{csc_id}|{c_hash}"

    @staticmethod
    def _calcular_dv(chave_sem_dv: str) -> int:
        """Calcula o dígito verificador da chave de acesso NF-e (módulo 11)."""
        pesos  = [2, 3, 4, 5, 6, 7, 8, 9]
        soma   = 0
        p_idx  = 0
        for dig in reversed(chave_sem_dv):
            soma  += int(dig) * pesos[p_idx % len(pesos)]
            p_idx += 1
        resto = soma % 11
        return 0 if resto < 2 else 11 - resto

    @staticmethod
    def _esc(s: str) -> str:
        """Escapa caracteres especiais XML."""
        return (s.replace("&", "&amp;")
                 .replace("<", "&lt;")
                 .replace(">", "&gt;")
                 .replace('"', "&quot;")
                 .replace("'", "&apos;"))
