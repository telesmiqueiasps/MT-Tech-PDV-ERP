"""
Parser de XML NF-e (modelo 55 e 65).
Extrai TODOS os campos relevantes para entrada fiscal.
Retorna estrutura completa pronta para uso no wizard de importação.
"""
import xml.etree.ElementTree as ET
from pathlib import Path

NS = {"nfe": "http://www.portalfiscal.inf.br/nfe"}

# Mapeamento CFOP saída → entrada (inversão automática)
CFOP_INVERSO = {
    # Venda → Compra
    "5101": "1101", "5102": "1102", "5103": "1103", "5104": "1104",
    "5105": "1105", "5106": "1106", "5109": "1109", "5110": "1110",
    "5111": "1111", "5112": "1112", "5113": "1113", "5114": "1114",
    "5115": "1115", "5116": "1116", "5117": "1117", "5118": "1118",
    "5119": "1119", "5120": "1120", "5122": "1122", "5123": "1123",
    "5124": "1124", "5125": "1125", "5151": "1151", "5152": "1152",
    "5153": "1153", "5154": "1154", "5155": "1155", "5156": "1156",
    "5401": "1401", "5402": "1402", "5403": "1403", "5405": "1403",
    "5501": "1501", "5502": "1502", "5503": "1503",
    "5551": "1551", "5552": "1552", "5553": "1553",
    "5554": "1554", "5555": "1555", "5556": "1556",
    "5601": "1601", "5602": "1602",
    "5651": "1651", "5652": "1652", "5653": "1653",
    "5667": "1667",
    "5901": "1901", "5902": "1902", "5903": "1903",
    "5904": "1904", "5905": "1905", "5906": "1906",
    "5907": "1907", "5908": "1908", "5909": "1909",
    "5910": "1910", "5911": "1911", "5912": "1912",
    "5913": "1913", "5914": "1914", "5915": "1915",
    "5916": "1916", "5917": "1917", "5918": "1918",
    "5919": "1919", "5920": "1920", "5921": "1921",
    "5922": "1922", "5923": "1923", "5924": "1924",
    "5925": "1925", "5926": "1926", "5927": "1927",
    "5928": "1928",
    # Interestaduais 6xxx → 2xxx
    "6101": "2101", "6102": "2102", "6103": "2103", "6104": "2104",
    "6105": "2105", "6106": "6106", "6109": "2109", "6110": "2110",
    "6111": "2111", "6112": "2112", "6113": "2113", "6116": "2116",
    "6117": "2117", "6118": "2118", "6119": "2119", "6120": "2120",
    "6122": "2122", "6123": "2123", "6124": "2124", "6125": "2125",
    "6151": "2151", "6152": "2152", "6153": "2153", "6154": "2154",
    "6155": "2155", "6156": "2156",
    "6401": "2401", "6402": "2402", "6403": "2403", "6404": "2404",
    "6501": "2501", "6502": "2502", "6503": "2503",
    "6551": "2551", "6552": "2552", "6553": "2553",
    "6554": "2554", "6555": "2555", "6556": "2556",
    "6901": "2901", "6902": "2902", "6903": "2903",
    "6904": "2904", "6905": "2905", "6906": "2906",
    "6907": "2907", "6910": "2910", "6911": "2911",
    "6912": "2912", "6913": "2913", "6914": "2914",
    "6915": "2915", "6916": "2916", "6918": "2918",
}

MODALIDADE_FRETE = {
    "0": "0 — Por conta do emitente (CIF)",
    "1": "1 — Por conta do destinatário (FOB)",
    "2": "2 — Por conta de terceiros",
    "3": "3 — Próprio por conta do remetente",
    "4": "4 — Próprio por conta do destinatário",
    "9": "9 — Sem frete",
}


def _find(root, *tags):
    """Tenta encontrar elemento por vários caminhos."""
    for tag in tags:
        el = root.find(tag, NS)
        if el is not None:
            return el
    return None


def _t(el, tag, default=""):
    if el is None:
        return default
    node = el.find(f"nfe:{tag}", NS)
    return (node.text or "").strip() if node is not None else default


def _f(el, tag, default=0.0):
    try:
        return float(_t(el, tag) or default)
    except (ValueError, TypeError):
        return default


def _get_root_nfe(root):
    """Extrai infNFe de qualquer envelope XML (NFeProc, nfeProc, NFe direto)."""
    # Tenta caminhos comuns
    for path in [
        "nfe:NFe/nfe:infNFe",
        "nfe:nfeProc/nfe:NFe/nfe:infNFe",
        "nfe:infNFe",
        ".//nfe:infNFe",
    ]:
        el = root.find(path, NS)
        if el is not None:
            return el

    # Fallback sem namespace
    el = root.find(".//infNFe")
    return el


def cfop_entrada(cfop_original: str) -> str:
    """Converte CFOP de saída para entrada. Se já for entrada, retorna igual."""
    if not cfop_original:
        return ""
    cfop_str = cfop_original.strip()
    # Se começa com 1 ou 2, já é entrada
    if cfop_str and cfop_str[0] in ("1", "2"):
        return cfop_str
    return CFOP_INVERSO.get(cfop_str, cfop_str)


def parse_nfe_xml(path) -> dict:
    """
    Parseia NF-e completa para importação fiscal.

    Retorna:
    {
        "chave":       str,
        "protocolo":   str | None,
        "nota":        dict,         # campos para notas_fiscais
        "emitente":    dict,         # dados completos do emitente
        "destinatario":dict,         # dados do destinatário
        "transporte":  dict,
        "pagamento":   dict | None,
        "itens":       list[dict],   # campos para notas_fiscais_itens
        "totais":      dict,
        "info_complementar": str,
    }
    """
    try:
        tree = ET.parse(str(path))
        root = tree.getroot()
    except ET.ParseError as e:
        raise ValueError(f"XML inválido ou corrompido: {e}")

    inf_nfe = _get_root_nfe(root)
    if inf_nfe is None:
        raise ValueError(
            "Estrutura XML não reconhecida: elemento 'infNFe' não encontrado.\n"
            "Verifique se o arquivo é uma NF-e válida."
        )

    # ── Identificação ────────────────────────────────────────────
    ide = inf_nfe.find("nfe:ide", NS)

    chave_acesso = inf_nfe.get("Id", "").replace("NFe", "").strip()
    if not chave_acesso:
        # Tenta extrair da chave do protocolo
        prot_el = root.find(".//nfe:infProt", NS)
        if prot_el is not None:
            chave_acesso = _t(prot_el, "chNFe")

    # Protocolo de autorização
    prot_el   = root.find(".//nfe:infProt", NS)
    protocolo = _t(prot_el, "nProt") if prot_el else None
    dt_auth   = _t(prot_el, "dhRecbto") if prot_el else None

    modelo = _t(ide, "mod") or "55"
    serie  = _t(ide, "serie") or "1"
    numero = _t(ide, "nNF")

    data_emissao = _t(ide, "dhEmi") or _t(ide, "dEmi")
    data_entrada = _t(ide, "dhSaiEnt") or _t(ide, "dSaiEnt") or data_emissao

    # Normaliza datas para YYYY-MM-DD
    def _normaliza_data(s):
        if not s:
            return ""
        s = s.strip()
        if "T" in s:
            return s[:10]
        return s[:10]

    data_emissao = _normaliza_data(data_emissao)
    data_entrada = _normaliza_data(data_entrada)

    finalidade = _t(ide, "finNFe") or "1"  # 1=Normal, 2=Complementar, 3=Ajuste, 4=Devolução

    # ── Emitente ────────────────────────────────────────────────
    emit = inf_nfe.find("nfe:emit", NS)
    end_emit = emit.find("nfe:enderEmit", NS) if emit else None

    emitente = {
        "cnpj":       _t(emit, "CNPJ"),
        "cpf":        _t(emit, "CPF"),
        "nome":       _t(emit, "xNome"),
        "fantasia":   _t(emit, "xFant"),
        "ie":         _t(emit, "IE"),
        "iest":       _t(emit, "IEST"),
        "im":         _t(emit, "IM"),
        "cnae":       _t(emit, "CNAE"),
        "crt":        _t(emit, "CRT"),    # regime tributário: 1=Simples, 2=Simples Excesso, 3=Normal
        "logradouro": _t(end_emit, "xLgr"),
        "numero":     _t(end_emit, "nro"),
        "complemento":_t(end_emit, "xCpl"),
        "bairro":     _t(end_emit, "xBairro"),
        "cidade":     _t(end_emit, "xMun"),
        "uf":         _t(end_emit, "UF"),
        "cep":        _t(end_emit, "CEP"),
        "cod_ibge":   _t(end_emit, "cMun"),
        "pais":       _t(end_emit, "xPais"),
        "fone":       _t(end_emit, "fone"),
    }
    # doc principal do emitente
    emitente["doc"] = emitente["cnpj"] or emitente["cpf"]

    # ── Destinatário ────────────────────────────────────────────
    dest    = inf_nfe.find("nfe:dest", NS)
    end_dest= dest.find("nfe:enderDest", NS) if dest else None

    destinatario = {
        "cnpj":       _t(dest, "CNPJ"),
        "cpf":        _t(dest, "CPF"),
        "nome":       _t(dest, "xNome"),
        "ie":         _t(dest, "IE"),
        "email":      _t(dest, "email"),
        "logradouro": _t(end_dest, "xLgr"),
        "numero":     _t(end_dest, "nro"),
        "complemento":_t(end_dest, "xCpl"),
        "bairro":     _t(end_dest, "xBairro"),
        "cidade":     _t(end_dest, "xMun"),
        "uf":         _t(end_dest, "UF"),
        "cep":        _t(end_dest, "CEP"),
        "fone":       _t(end_dest, "fone"),
    }
    destinatario["doc"] = destinatario["cnpj"] or destinatario["cpf"]

    # ── Totais ───────────────────────────────────────────────────
    tot = inf_nfe.find("nfe:total/nfe:ICMSTot", NS)
    totais = {
        "bc_icms":      _f(tot, "vBC"),
        "valor_icms":   _f(tot, "vICMS"),
        "bc_icms_st":   _f(tot, "vBCST"),
        "valor_icms_st":_f(tot, "vST"),
        "total_produtos":_f(tot, "vProd"),
        "total_frete":  _f(tot, "vFrete"),
        "total_seguro": _f(tot, "vSeg"),
        "total_desconto":_f(tot, "vDesc"),
        "total_outros": _f(tot, "vOutro"),
        "total_ipi":    _f(tot, "vIPI"),
        "total_icms":   _f(tot, "vICMS"),
        "total_pis":    _f(tot, "vPIS"),
        "total_cofins": _f(tot, "vCOFINS"),
        "total_nf":     _f(tot, "vNF"),
    }

    # ── Transporte ───────────────────────────────────────────────
    transp = inf_nfe.find("nfe:transp", NS)
    transp_a = transp.find("nfe:transporta", NS) if transp else None
    veic     = transp.find("nfe:veicTransp", NS) if transp else None
    vol_el   = transp.find("nfe:vol", NS) if transp else None

    mod_frete_raw = _t(transp, "modFrete") or "9"
    transporte = {
        "modalidade_cod":   mod_frete_raw,
        "modalidade_label": MODALIDADE_FRETE.get(mod_frete_raw, mod_frete_raw),
        "cnpj":             _t(transp_a, "CNPJ"),
        "cpf":              _t(transp_a, "CPF"),
        "nome":             _t(transp_a, "xNome"),
        "ie":               _t(transp_a, "IE"),
        "endereco":         _t(transp_a, "xEnder"),
        "cidade":           _t(transp_a, "xMun"),
        "uf":               _t(transp_a, "UF"),
        "placa":            _t(veic, "placa"),
        "uf_veiculo":       _t(veic, "UF"),
        "qtd_vol":          _t(vol_el, "qVol"),
        "esp_vol":          _t(vol_el, "esp"),
        "peso_bruto":       _f(vol_el, "pesoB"),
        "peso_liquido":     _f(vol_el, "pesoL"),
    }

    # ── Pagamento ────────────────────────────────────────────────
    cobr = inf_nfe.find("nfe:cobr", NS)
    fat  = cobr.find("nfe:fat", NS) if cobr else None
    pag_el = inf_nfe.find("nfe:pag", NS)
    det_pag = pag_el.find("nfe:detPag", NS) if pag_el else None

    pagamento = None
    if fat or det_pag:
        formas = []
        if pag_el:
            for dp in pag_el.findall("nfe:detPag", NS):
                t_pag = _t(dp, "tPag")
                v_pag = _f(dp, "vPag")
                label_tpag = {
                    "01": "Dinheiro", "02": "Cheque", "03": "Cartão Crédito",
                    "04": "Cartão Débito", "05": "Crédito Loja",
                    "10": "Vale Alimentação", "11": "Vale Refeição",
                    "12": "Vale Presente", "13": "Vale Combustível",
                    "15": "Boleto", "16": "Depósito Bancário",
                    "17": "PIX", "18": "Transferência",
                    "90": "Sem Pagamento", "99": "Outros",
                }.get(t_pag, t_pag)
                formas.append({"tipo": label_tpag, "valor": v_pag})

        duplicatas = []
        if cobr:
            for dup in cobr.findall("nfe:dup", NS):
                duplicatas.append({
                    "numero":     _t(dup, "nDup"),
                    "vencimento": _t(dup, "dVenc"),
                    "valor":      _f(dup, "vDup"),
                })

        pagamento = {
            "formas":      formas,
            "duplicatas":  duplicatas,
            "num_fat":     _t(fat, "nFat") if fat else "",
            "vl_orig":     _f(fat, "vOrig") if fat else 0,
            "vl_desc":     _f(fat, "vDesc") if fat else 0,
            "vl_liq":      _f(fat, "vLiq") if fat else 0,
        }

        # Monta descrição da condição de pagamento
        if duplicatas:
            cond = f"{len(duplicatas)}x parcela(s)"
        elif formas:
            cond = " + ".join(f"{f['tipo']} R${f['valor']:.2f}" for f in formas)
        else:
            cond = ""
        pagamento["descricao"] = cond

    # ── Informações Complementares ───────────────────────────────
    info_el = inf_nfe.find("nfe:infAdic", NS)
    info_complementar = _t(info_el, "infCpl") if info_el else ""
    info_fisco        = _t(info_el, "infAdFisco") if info_el else ""

    # ── Itens ────────────────────────────────────────────────────
    itens = []
    for ordem, det in enumerate(inf_nfe.findall("nfe:det", NS), 1):
        prod    = det.find("nfe:prod", NS)
        imposto = det.find("nfe:imposto", NS)

        # ICMS — pega o primeiro elemento filho do grupo
        icms_grp = imposto.find("nfe:ICMS", NS) if imposto else None
        icms_el  = list(icms_grp)[0] if (icms_grp is not None and len(icms_grp)) else None

        # PIS
        pis_grp = imposto.find("nfe:PIS", NS) if imposto else None
        pis_el  = list(pis_grp)[0] if (pis_grp is not None and len(pis_grp)) else None

        # COFINS
        cof_grp = imposto.find("nfe:COFINS", NS) if imposto else None
        cof_el  = list(cof_grp)[0] if (cof_grp is not None and len(cof_grp)) else None

        # IPI
        ipi_grp = imposto.find("nfe:IPI", NS) if imposto else None
        ipi_el  = (ipi_grp.find("nfe:IPITrib", NS) or
                   ipi_grp.find("nfe:IPINT", NS)) if ipi_grp else None

        cfop_original = _t(prod, "CFOP")
        cfop_conv     = cfop_entrada(cfop_original)

        qtd = _f(prod, "qCom")
        vun = _f(prod, "vUnCom")

        # BC ICMS
        bc_icms = _f(icms_el, "vBC") if icms_el is not None else 0

        # BC ST
        bc_st  = _f(icms_el, "vBCST") if icms_el is not None else 0
        val_st = _f(icms_el, "vICMSST") if icms_el is not None else 0

        # CST ou CSOSN
        cst_icms = ""
        if icms_el is not None:
            cst_icms = _t(icms_el, "CST") or _t(icms_el, "CSOSN")

        itens.append({
            "ordem":            ordem,
            "codigo_fornecedor":_t(prod, "cProd"),   # código do produto NO fornecedor
            "codigo":           "",                    # código interno — a preencher
            "produto_id":       None,                  # a vincular
            "descricao":        _t(prod, "xProd"),
            "ncm":              _t(prod, "NCM"),
            "cest":             _t(prod, "CEST"),
            "cfop_original":    cfop_original,
            "cfop":             cfop_conv,             # cfop de entrada (invertido)
            "unidade":          _t(prod, "uCom"),
            "quantidade":       qtd,
            "valor_unitario":   vun,
            "valor_total":      _f(prod, "vProd"),
            "desconto":         _f(prod, "vDesc"),
            "frete":            _f(prod, "vFrete"),
            "outros":           _f(prod, "vOutro"),
            "origem":           int(_t(icms_el, "orig") or 0) if icms_el is not None else 0,
            "cst_icms":         cst_icms,
            "aliq_icms":        _f(icms_el, "pICMS") if icms_el is not None else 0,
            "valor_icms":       _f(icms_el, "vICMS") if icms_el is not None else 0,
            "bc_icms":          bc_icms,
            "bc_icms_st":       bc_st,
            "valor_icms_st":    val_st,
            "cst_pis":          _t(pis_el, "CST") if pis_el is not None else "99",
            "aliq_pis":         _f(pis_el, "pPIS") if pis_el is not None else 0,
            "valor_pis":        _f(pis_el, "vPIS") if pis_el is not None else 0,
            "cst_cofins":       _t(cof_el, "CST") if cof_el is not None else "99",
            "aliq_cofins":      _f(cof_el, "pCOFINS") if cof_el is not None else 0,
            "valor_cofins":     _f(cof_el, "vCOFINS") if cof_el is not None else 0,
            "cst_ipi":          _t(ipi_el, "CST") if ipi_el is not None else "",
            "aliq_ipi":         _f(ipi_el, "pIPI") if ipi_el is not None else 0,
            "valor_ipi":        _f(ipi_el, "vIPI") if ipi_el is not None else 0,
        })

    return {
        "chave":             chave_acesso,
        "protocolo":         protocolo,
        "dt_autorizacao":    dt_auth,
        "finalidade":        finalidade,
        "nota": {
            "tipo":              "ENTRADA",
            "modelo":            modelo,
            "serie":             int(serie or 1),
            "numero":            int(numero or 0) or None,
            "chave_acesso":      chave_acesso,
            "protocolo":         protocolo,
            "data_emissao":      data_emissao,
            "data_entrada":      data_entrada,
            "status":            "RASCUNHO",
            "terceiro_tipo":     "FORNECEDOR",
            "terceiro_nome":     emitente["nome"],
            "terceiro_doc":      emitente["doc"],
            "frete_modalidade":  int(mod_frete_raw or 9),
            "transp_nome":       transporte["nome"],
            "transp_cnpj":       transporte["cnpj"],
            "transp_placa":      transporte["placa"],
            "transp_uf":         transporte["uf"],
            "cond_pagamento":    pagamento["descricao"] if pagamento else "",
            "info_complementar": info_complementar,
            "total_produtos":    totais["total_produtos"],
            "total_frete":       totais["total_frete"],
            "total_seguro":      totais["total_seguro"],
            "total_desconto":    totais["total_desconto"],
            "total_outros":      totais["total_outros"],
            "total_ipi":         totais["total_ipi"],
            "total_icms":        totais["total_icms"],
            "total_bc_icms":     totais["bc_icms"],
            "total_bc_icms_st":  totais["bc_icms_st"],
            "total_icms_st":     totais["valor_icms_st"],
            "total_pis":         totais["total_pis"],
            "total_cofins":      totais["total_cofins"],
            "total_nf":          totais["total_nf"],
            "xml_entrada":       ET.tostring(root, encoding="unicode"),
        },
        "emitente":          emitente,
        "destinatario":      destinatario,
        "transporte":        transporte,
        "pagamento":         pagamento,
        "totais":            totais,
        "itens":             itens,
        "info_complementar": info_complementar,
        "info_fisco":        info_fisco,
    }