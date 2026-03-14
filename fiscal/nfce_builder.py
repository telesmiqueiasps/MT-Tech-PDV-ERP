"""Construtor do XML da NFC-e (layout 4.00) para Simples Nacional."""
import re
import random
import hashlib
from datetime import datetime


_UF_COD_SIGLA = {
    "11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA",
    "16": "AP", "17": "TO", "21": "MA", "22": "PI", "23": "CE",
    "24": "RN", "25": "PB", "26": "PE", "27": "AL", "28": "SE",
    "29": "BA", "31": "MG", "32": "ES", "33": "RJ", "35": "SP",
    "41": "PR", "42": "SC", "43": "RS", "50": "MS", "51": "MT",
    "52": "GO", "53": "DF",
}

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
        """Retorna XML não assinado da NFC-e (compacto, sem whitespace entre tags)."""
        from fiscal.nfce_uf_config import NfceUfConfig

        numero    = config["proximo_numero_usado"]
        serie     = config.get("serie", 1)
        ambiente  = config.get("ambiente", 2)
        cnpj      = re.sub(r"\D", "", empresa.get("cnpj", ""))
        c_nf      = str(random.randint(10000000, 99999999))

        # UF e parâmetros via tabela nfce_uf_config
        uf_raw   = str(empresa.get("estado", "PB") or "PB").strip()
        uf_sigla = _UF_COD_SIGLA.get(uf_raw, uf_raw) if uf_raw.isdigit() else uf_raw
        c_uf     = NfceUfConfig.c_uf(uf_sigla)
        fuso     = NfceUfConfig.fuso_horario(uf_sigla)

        mod       = "65"
        serie_str = str(serie).zfill(3)
        n_nf_str  = str(numero).zfill(9)
        tp_emis   = "1"
        dh_emi    = datetime.now().strftime(f"%Y-%m-%dT%H:%M:%S{fuso}")
        c_mun_fg  = empresa.get("cod_municipio_ibge") or ""

        # Chave de acesso 44 dígitos
        aamm = datetime.now().strftime("%y%m")
        chave_sem_dv = f"{c_uf}{aamm}{cnpj}{mod}{serie_str}{n_nf_str}{tp_emis}{c_nf}"
        c_dv  = self._calcular_dv(chave_sem_dv)
        chave = chave_sem_dv + str(c_dv)

        # Totais
        v_prod = sum(float(i.get("subtotal", 0)) for i in itens)
        v_desc = float(venda.get("desconto_valor", 0) or 0)
        v_nf   = float(venda.get("total", v_prod - v_desc))

        # QR Code e URL de consulta lidos da tabela por UF e ambiente
        qr_url       = self._gerar_qrcode_url(chave, ambiente, config, uf_sigla)
        url_consulta = NfceUfConfig.url_qrcode(uf_sigla, ambiente) or ""

        # Inscrição Estadual — campo "ie" na tabela empresas
        ie_raw = (empresa.get("ie") or empresa.get("inscricao_estadual") or "").strip()
        ie = re.sub(r"\D", "", ie_raw) if ie_raw.upper() != "ISENTO" else "ISENTO"
        if not ie:
            ie = "ISENTO"

        x_nome = self._esc(empresa.get("razao_social") or empresa.get("nome", ""))[:60]
        x_fant = self._esc(empresa.get("nome", "") or "")[:60]
        x_fant_xml = f"<xFant>{x_fant}</xFant>" if x_fant else ""

        # ── XML compacto (sem indentação — SEFAZ rejeita whitespace entre tags) ──
        # Nota: infNFeSupl é filho de NFe, NÃO de infNFe (schema 4.00)
        xml = (
            f'<?xml version="1.0" encoding="UTF-8"?>'
            f'<NFe xmlns="{self.NS}">'
            f'<infNFe versao="4.00" Id="NFe{chave}">'
            f'<ide>'
            f'<cUF>{c_uf}</cUF>'
            f'<cNF>{c_nf}</cNF>'
            f'<natOp>VENDA AO CONSUMIDOR</natOp>'
            f'<mod>{mod}</mod>'
            f'<serie>{serie}</serie>'
            f'<nNF>{numero}</nNF>'
            f'<dhEmi>{dh_emi}</dhEmi>'
            f'<tpNF>1</tpNF>'
            f'<idDest>1</idDest>'
            f'<cMunFG>{c_mun_fg}</cMunFG>'
            f'<tpImp>4</tpImp>'
            f'<tpEmis>{tp_emis}</tpEmis>'
            f'<cDV>{c_dv}</cDV>'
            f'<tpAmb>{ambiente}</tpAmb>'
            f'<finNFe>1</finNFe>'
            f'<indFinal>1</indFinal>'
            f'<indPres>1</indPres>'
            f'<procEmi>0</procEmi>'
            f'<verProc>MTTech PDV 1.0</verProc>'
            f'</ide>'
            f'<emit>'
            f'<CNPJ>{cnpj}</CNPJ>'
            f'<xNome>{x_nome}</xNome>'
            f'{x_fant_xml}'
            f'<enderEmit>'
            f'<xLgr>{self._esc(empresa.get("endereco", "RUA") or "RUA")[:60]}</xLgr>'
            f'<nro>{self._esc(empresa.get("numero", "S/N") or "S/N")[:60]}</nro>'
            f'<xBairro>{self._esc(empresa.get("bairro", "CENTRO") or "CENTRO")[:60]}</xBairro>'
            f'<cMun>{c_mun_fg}</cMun>'
            f'<xMun>{self._esc(empresa.get("cidade", "CAMPINA GRANDE") or "CAMPINA GRANDE")[:60]}</xMun>'
            f'<UF>{uf_sigla}</UF>'
            f'<CEP>{re.sub(r"[^0-9]", "", empresa.get("cep", "58400000") or "58400000")}</CEP>'
            f'<cPais>1058</cPais>'
            f'<xPais>BRASIL</xPais>'
            f'</enderEmit>'
            f'<IE>{ie}</IE>'
            f'<CRT>1</CRT>'
            f'</emit>'
            # Homologação: dest obrigatório no schema SVRS (NT 2019.001)
            + (
                '<dest>'
                '<idEstrangeiro/>'
                '<xNome>NF-E EMITIDA EM AMBIENTE DE HOMOLOGACAO - SEM VALOR FISCAL</xNome>'
                '<indIEDest>9</indIEDest>'
                '</dest>'
                if ambiente == 2 else ''
            ) +
            f'{self._itens_xml(itens, ambiente)}'
            f'<total><ICMSTot>'
            f'<vBC>0.00</vBC><vICMS>0.00</vICMS><vICMSDeson>0.00</vICMSDeson>'
            f'<vFCP>0.00</vFCP><vBCST>0.00</vBCST><vST>0.00</vST>'
            f'<vFCPST>0.00</vFCPST><vFCPSTRet>0.00</vFCPSTRet>'
            f'<vProd>{v_prod:.2f}</vProd><vFrete>0.00</vFrete><vSeg>0.00</vSeg>'
            f'<vDesc>{v_desc:.2f}</vDesc><vII>0.00</vII><vIPI>0.00</vIPI>'
            f'<vIPIDevol>0.00</vIPIDevol><vPIS>0.00</vPIS><vCOFINS>0.00</vCOFINS>'
            f'<vOutro>0.00</vOutro><vNF>{v_nf:.2f}</vNF>'
            f'</ICMSTot></total>'
            f'<transp><modFrete>9</modFrete></transp>'
            f'{self._pag_xml(pagamentos, v_nf)}'
            f'<infAdic>'
            f'<infCpl>DOCUMENTO EMITIDO POR ME OU EPP OPTANTE PELO SIMPLES NACIONAL</infCpl>'
            f'</infAdic>'
            f'</infNFe>'
            # infNFeSupl é filho de NFe (fora de infNFe) — obrigatório no schema 4.00
            f'<infNFeSupl>'
            f'<qrCode>{self._esc(qr_url)}</qrCode>'
            f'<urlChave>{url_consulta}</urlChave>'
            f'</infNFeSupl>'
            f'</NFe>'
        )
        return xml

    def _itens_xml(self, itens: list, ambiente: int = 1) -> str:
        partes = []
        for n, item in enumerate(itens, 1):
            cod   = self._esc(str(item.get("codigo") or item.get("produto_id", n)))[:60]
            ean   = self._esc(str(item.get("ean") or "SEM GTIN"))
            # Homologação: xProd do primeiro item obrigatório pela NT
            if ambiente == 2 and n == 1:
                xprod = "NOTA FISCAL EMITIDA EM AMBIENTE DE HOMOLOGACAO - SEM VALOR FISCAL"
            else:
                xprod = self._esc(str(item.get("produto_nome", ""))[:120])
            ncm   = re.sub(r"\D", "", str(item.get("ncm") or "00000000")).zfill(8)[:8]
            qtd   = float(item.get("quantidade", 1))
            v_uni = float(item.get("preco_unitario", 0))
            v_prd = float(item.get("subtotal", qtd * v_uni))
            unid  = self._esc(str(item.get("unidade", "UN") or "UN"))[:6]
            # CST 07 = não tributado → usar PISNT / COFINSNT (não PISAliq/COFINSAliq)
            partes.append(
                f'<det nItem="{n}">'
                f'<prod>'
                f'<cProd>{cod}</cProd>'
                f'<cEAN>{ean}</cEAN>'
                f'<xProd>{xprod}</xProd>'
                f'<NCM>{ncm}</NCM>'
                f'<CFOP>5102</CFOP>'
                f'<uCom>{unid}</uCom>'
                f'<qCom>{qtd:.4f}</qCom>'
                f'<vUnCom>{v_uni:.10f}</vUnCom>'
                f'<vProd>{v_prd:.2f}</vProd>'
                f'<cEANTrib>{ean}</cEANTrib>'
                f'<uTrib>{unid}</uTrib>'
                f'<qTrib>{qtd:.4f}</qTrib>'
                f'<vUnTrib>{v_uni:.10f}</vUnTrib>'
                f'<indTot>1</indTot>'
                f'</prod>'
                f'<imposto>'
                f'<ICMS><ICMSSN102><orig>0</orig><CSOSN>400</CSOSN></ICMSSN102></ICMS>'
                f'<PIS><PISNT><CST>07</CST></PISNT></PIS>'
                f'<COFINS><COFINSNT><CST>07</CST></COFINSNT></COFINS>'
                f'</imposto>'
                f'</det>'
            )
        return "".join(partes)

    def _pag_xml(self, pagamentos: list, v_nf: float) -> str:
        if not pagamentos:
            return f"<pag><detPag><tPag>01</tPag><vPag>{v_nf:.2f}</vPag></detPag></pag>"
        partes = ["<pag>"]
        for p in pagamentos:
            forma = _FORMA_PAG_MAP.get(str(p.get("forma", "")).upper(), "99")
            valor = float(p.get("valor", 0))
            partes.append(f"<detPag><tPag>{forma}</tPag><vPag>{valor:.2f}</vPag></detPag>")
        partes.append("</pag>")
        return "".join(partes)

    def _gerar_qrcode_url(self, chave: str, ambiente: int, config: dict, uf: str = "PB") -> str:
        from fiscal.nfce_uf_config import NfceUfConfig
        # cIdToken como inteiro (sem zeros à esquerda) — padrão XSD: (0|[1-9]{1,6})
        csc_id_raw = config.get("id_csc") or config.get("csc_id") or "1"
        csc_id    = int(str(csc_id_raw).strip() or "1")
        csc_token = (config.get("csc_token") or "").replace("-", "")  # SEFAZ armazena sem traços
        base_url  = NfceUfConfig.url_qrcode(uf, ambiente) or ""
        # Hash V2: SHA-1(chave + csc_token_sem_traços) — NT 2015.002
        c_hash = hashlib.sha1(
            f"{chave}{csc_token}".encode()
        ).hexdigest().upper()
        # Formato V2 ONLINE: URL?p=chave|2|tpAmb|cIdToken|cHashQRCode
        return f"{base_url}?p={chave}|2|{ambiente}|{csc_id}|{c_hash}"

    @staticmethod
    def _calcular_dv(chave_sem_dv: str) -> int:
        """Dígito verificador da chave de acesso — módulo 11."""
        pesos = [2, 3, 4, 5, 6, 7, 8, 9]
        soma  = 0
        for i, dig in enumerate(reversed(chave_sem_dv)):
            soma += int(dig) * pesos[i % len(pesos)]
        resto = soma % 11
        return 0 if resto < 2 else 11 - resto

    @staticmethod
    def _esc(s: str) -> str:
        return (s.replace("&", "&amp;")
                 .replace("<", "&lt;")
                 .replace(">", "&gt;")
                 .replace('"', "&quot;")
                 .replace("'", "&apos;"))
