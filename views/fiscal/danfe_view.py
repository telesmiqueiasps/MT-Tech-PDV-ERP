"""
DanfeView — visualização de NF-e no estilo DANFE simplificado.
Abre como janela modal, permite imprimir via ReportLab se disponível,
ou exportar como texto formatado.
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from config import THEME, FONT
from views.base_view import BaseView
from models.nota_fiscal import NotaFiscal, STATUS_LABELS, TIPO_LABELS
from core.session import Session


def _f(v, dec=2):
    try:
        return f"{float(v or 0):,.{dec}f}"
    except (ValueError, TypeError):
        return "0,00"


def _mask_cnpj(s):
    d = "".join(c for c in (s or "") if c.isdigit())
    if len(d) == 14:
        return f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:]}"
    return s or ""


def _mask_cep(s):
    d = "".join(c for c in (s or "") if c.isdigit())
    if len(d) == 8:
        return f"{d[:5]}-{d[5:]}"
    return s or ""


def _fmt_data(s):
    """AAAA-MM-DD → DD/MM/AAAA"""
    if not s:
        return ""
    s = str(s).strip()[:10]
    if len(s) == 10 and s[4] == "-":
        return f"{s[8:10]}/{s[5:7]}/{s[:4]}"
    return s


class DanfeView(BaseView):
    def __init__(self, master, nota_id: int):
        super().__init__(master, "🧾 DANFE — Documento Auxiliar da NF-e", 920, 780, modal=True)
        self.resizable(True, True)
        self._nota_id = nota_id
        self._nota    = NotaFiscal.buscar_por_id(nota_id)
        self._itens   = NotaFiscal.itens(nota_id)
        self._empresa = Session.empresa()
        if not self._nota:
            tk.Label(self, text="Nota não encontrada.", font=FONT["lg"],
                     bg=THEME["bg"], fg=THEME["danger"]).pack(expand=True)
            return
        self._build()

    def _build(self):
        # Toolbar
        tb = tk.Frame(self, bg=THEME["bg_card"], padx=12, pady=8,
                      highlightthickness=1, highlightbackground=THEME["border"])
        tb.pack(fill="x")

        sl, cor = STATUS_LABELS.get(self._nota.get("status",""), ("?","gray"))
        tk.Label(tb, text=sl, font=FONT["bold"],
                 bg=THEME["bg_card"], fg=cor).pack(side="left")
        tk.Label(tb, text=f"  {TIPO_LABELS.get(self._nota.get('tipo',''),'')}", 
                 font=FONT["sm"], bg=THEME["bg_card"],
                 fg=THEME["fg_light"]).pack(side="left")

        from views.widgets.widgets import botao
        botao(tb, "🖨 Imprimir / Exportar PDF", tipo="primario",
              command=self._exportar_pdf).pack(side="right")

        # Canvas scrollável para o DANFE
        canvas = tk.Canvas(self, bg="#f0f0f0", highlightthickness=0)
        vsb = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        hsb = ttk.Scrollbar(self, orient="horizontal", command=canvas.xview)
        canvas.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        canvas.pack(fill="both", expand=True)

        self._danfe_frame = tk.Frame(canvas, bg="white",
                                      highlightthickness=1,
                                      highlightbackground="#999")
        win = canvas.create_window((20, 20), window=self._danfe_frame, anchor="nw")
        self._danfe_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.bind("<MouseWheel>",
            lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

        self._render_danfe()

    # ────────────────────────────────────────────────────────────
    def _render_danfe(self):
        W = 860  # largura fixa em pixels
        f = self._danfe_frame
        nota  = self._nota
        emp   = self._empresa

        # ── Cabeçalho principal ───────────────────────────────────
        hdr = tk.Frame(f, bg="white", padx=0, pady=0)
        hdr.pack(fill="x", padx=8, pady=(10, 0))

        # Logo / razão social empresa
        emp_col = tk.Frame(hdr, bg="white",
                           highlightthickness=1, highlightbackground="#ccc",
                           width=340)
        emp_col.pack(side="left", fill="both", padx=(0, 4))
        emp_col.pack_propagate(False)
        emp_inner = tk.Frame(emp_col, bg="white", padx=8, pady=6)
        emp_inner.pack(fill="both", expand=True)

        tk.Label(emp_inner,
                 text=emp.get("razao_social") or emp.get("nome") or "EMPRESA",
                 font=("Segoe UI", 11, "bold"),
                 bg="white", fg="#111", wraplength=320, justify="left"
                 ).pack(anchor="w")
        end_emp = " ".join(filter(None, [
            emp.get("endereco"),
            emp.get("numero"),
            emp.get("bairro"),
        ]))
        cidade_emp = " — ".join(filter(None, [
            emp.get("cidade") or emp.get("municipio"),
            emp.get("estado"),
            _mask_cep(emp.get("cep")),
        ]))
        for txt in [end_emp, cidade_emp,
                    f"CNPJ: {_mask_cnpj(emp.get('cnpj'))}",
                    f"IE: {emp.get('ie') or '—'}"]:
            if txt.strip():
                tk.Label(emp_inner, text=txt, font=("Segoe UI", 8),
                         bg="white", fg="#333").pack(anchor="w")

        # DANFE label central
        center_col = tk.Frame(hdr, bg="white",
                              highlightthickness=1, highlightbackground="#ccc",
                              width=170)
        center_col.pack(side="left", fill="both", padx=(0, 4))
        center_col.pack_propagate(False)
        ci = tk.Frame(center_col, bg="white", padx=6, pady=6)
        ci.pack(fill="both", expand=True)
        tk.Label(ci, text="DANFE", font=("Segoe UI", 14, "bold"),
                 bg="white", fg="#111").pack()
        tk.Label(ci, text="Documento Auxiliar da\nNota Fiscal Eletrônica",
                 font=("Segoe UI", 7), bg="white", fg="#555",
                 justify="center").pack()

        modelo_txt = "NF-e" if str(nota.get("modelo","55")) == "55" else "NFC-e"
        tk.Label(ci, text=f"Modelo: {nota.get('modelo','55')} — {modelo_txt}",
                 font=("Segoe UI", 8, "bold"), bg="white", fg="#111").pack(pady=(6,0))

        tipo_op = "0 — Entrada" if nota.get("tipo") == "ENTRADA" else "1 — Saída"
        tk.Label(ci, text=f"Tipo de operação: {tipo_op}",
                 font=("Segoe UI", 8), bg="white", fg="#333").pack()

        # Número NF / série / folha
        nf_col = tk.Frame(hdr, bg="white",
                          highlightthickness=1, highlightbackground="#ccc")
        nf_col.pack(side="left", fill="both", expand=True)
        ni = tk.Frame(nf_col, bg="white", padx=8, pady=6)
        ni.pack(fill="both", expand=True)
        num = str(nota.get("numero") or "").zfill(9)
        serie = str(nota.get("serie") or "1")
        tk.Label(ni, text=f"NF-e Nº  {num}", font=("Courier", 11, "bold"),
                 bg="white", fg="#111").pack(anchor="w")
        tk.Label(ni, text=f"SÉRIE: {serie}",
                 font=("Segoe UI", 9), bg="white", fg="#333").pack(anchor="w")
        tk.Label(ni, text=f"Emissão: {_fmt_data(nota.get('data_emissao'))}",
                 font=("Segoe UI", 9), bg="white", fg="#333").pack(anchor="w")
        tk.Label(ni, text=f"Entrada: {_fmt_data(nota.get('data_entrada'))}",
                 font=("Segoe UI", 9), bg="white", fg="#333").pack(anchor="w")
        if nota.get("protocolo"):
            tk.Label(ni, text=f"Protocolo: {nota['protocolo']}",
                     font=("Segoe UI", 8), bg="white", fg="#555").pack(anchor="w")

        # ── Chave de acesso ───────────────────────────────────────
        chave_frame = tk.Frame(f, bg="#1a1a2e", padx=8, pady=5)
        chave_frame.pack(fill="x", padx=8, pady=(4, 0))
        chave = nota.get("chave_acesso") or ""
        chave_fmt = " ".join(chave[i:i+4] for i in range(0, len(chave), 4)) if chave else "—"
        tk.Label(chave_frame,
                 text=f"CHAVE DE ACESSO:  {chave_fmt}",
                 font=("Consolas", 9), bg="#1a1a2e", fg="#7ec8e3"
                 ).pack(side="left")

        # ── Emitente (fornecedor) ────────────────────────────────
        self._secao(f, "EMITENTE (FORNECEDOR)")
        emit_f = tk.Frame(f, bg="white", padx=8)
        emit_f.pack(fill="x")
        self._row_dados(emit_f, [
            ("Razão Social / Nome", nota.get("terceiro_nome") or "—", 3),
            ("CNPJ / CPF",         _mask_cnpj(nota.get("terceiro_doc")), 1),
        ])

        # ── Destinatário (empresa) ───────────────────────────────
        self._secao(f, "DESTINATÁRIO (EMPRESA)")
        dest_f = tk.Frame(f, bg="white", padx=8)
        dest_f.pack(fill="x")
        self._row_dados(dest_f, [
            ("Razão Social / Nome",
             emp.get("razao_social") or emp.get("nome") or "—", 3),
            ("CNPJ", _mask_cnpj(emp.get("cnpj")), 1),
        ])
        self._row_dados(dest_f, [
            ("Endereço", emp.get("endereco") or "—", 2),
            ("Município", emp.get("cidade") or emp.get("municipio") or "—", 1),
            ("UF", emp.get("estado") or "—", 1),
        ])

        # ── Transporte ───────────────────────────────────────────
        mod_frete = {
            "0":"0-Emitente","1":"1-Destinatário","2":"2-Terceiros",
            "9":"9-Sem frete"
        }.get(str(nota.get("frete_modalidade") or "9"), "—")
        self._secao(f, "TRANSPORTE")
        tr_f = tk.Frame(f, bg="white", padx=8)
        tr_f.pack(fill="x")
        self._row_dados(tr_f, [
            ("Modalidade do Frete", mod_frete, 1),
            ("Transportadora", nota.get("transp_nome") or "—", 2),
            ("Placa",          nota.get("transp_placa") or "—", 1),
        ])

        # ── Itens ───────────────────────────────────────────────
        self._secao(f, "DADOS DOS PRODUTOS / SERVIÇOS")

        cols = [
            ("Cód.", 55), ("Descrição", 240), ("NCM", 65),
            ("CFOP", 42), ("Un", 38), ("Qtd.", 60),
            ("V.Unit", 75), ("V.Tot.", 80),
            ("BC ICMS", 72), ("ICMS", 65),
            ("IPI", 55), ("Total", 80),
        ]
        # Cabeçalho tabela
        tab_hdr = tk.Frame(f, bg="#d0d8e8", padx=8, pady=0)
        tab_hdr.pack(fill="x", padx=8, pady=(2, 0))
        for txt, w in cols:
            tk.Label(tab_hdr, text=txt, font=("Segoe UI", 7, "bold"),
                     bg="#d0d8e8", fg="#111",
                     width=w//6, anchor="center").pack(side="left", padx=1)

        # Linhas
        for i, item in enumerate(self._itens):
            bg_row = "white" if i % 2 == 0 else "#f7f9fc"
            row = tk.Frame(f, bg=bg_row, padx=8, pady=1)
            row.pack(fill="x", padx=8)
            vals = [
                item.get("codigo") or item.get("codigo_fornecedor") or "—",
                item.get("descricao") or "—",
                item.get("ncm") or "—",
                item.get("cfop") or "—",
                item.get("unidade") or "—",
                _f(item.get("quantidade"), 3),
                _f(item.get("valor_unitario"), 4),
                _f(item.get("valor_total")),
                _f(item.get("bc_icms")),
                _f(item.get("valor_icms")),
                _f(item.get("valor_ipi")),
                _f(item.get("valor_total")),
            ]
            for (_, w), val in zip(cols, vals):
                tk.Label(row, text=val, font=("Segoe UI", 8),
                         bg=bg_row, fg="#222",
                         width=w//6, anchor="e").pack(side="left", padx=1)

        # ── Totais ────────────────────────────────────────────────
        self._secao(f, "CÁLCULO DO IMPOSTO E TOTAIS")
        tot_f = tk.Frame(f, bg="white", padx=8, pady=4)
        tot_f.pack(fill="x")

        tot_campos = [
            ("BC ICMS R$",      _f(nota.get("total_bc_icms") or nota.get("total_icms"))),
            ("Vlr ICMS R$",     _f(nota.get("total_icms"))),
            ("BC ICMS-ST R$",   _f(nota.get("total_bc_icms_st"))),
            ("ICMS-ST R$",      _f(nota.get("total_icms_st"))),
            ("Produtos R$",     _f(nota.get("total_produtos"))),
            ("Frete R$",        _f(nota.get("total_frete"))),
            ("Seguro R$",       _f(nota.get("total_seguro"))),
            ("Desconto R$",     _f(nota.get("total_desconto"))),
            ("Outras Desp. R$", _f(nota.get("total_outros"))),
            ("IPI R$",          _f(nota.get("total_ipi"))),
            ("PIS R$",          _f(nota.get("total_pis"))),
            ("COFINS R$",       _f(nota.get("total_cofins"))),
        ]
        row_tot = tk.Frame(tot_f, bg="white")
        row_tot.pack(fill="x")
        for i, (lbl, val) in enumerate(tot_campos):
            col = tk.Frame(row_tot, bg="#f0f4fa",
                           highlightthickness=1, highlightbackground="#ccc",
                           padx=6, pady=4)
            col.grid(row=i//4, column=i%4, sticky="nsew", padx=2, pady=2)
            tk.Label(col, text=lbl, font=("Segoe UI", 7),
                     bg="#f0f4fa", fg="#555").pack(anchor="w")
            tk.Label(col, text=val, font=("Segoe UI", 9, "bold"),
                     bg="#f0f4fa", fg="#111").pack(anchor="e")
        row_tot.columnconfigure(0, weight=1)
        row_tot.columnconfigure(1, weight=1)
        row_tot.columnconfigure(2, weight=1)
        row_tot.columnconfigure(3, weight=1)

        # Total NF destacado
        tot_nf_f = tk.Frame(f, bg="#1a3a5c", padx=12, pady=8)
        tot_nf_f.pack(fill="x", padx=8, pady=(4, 0))
        tk.Label(tot_nf_f,
                 text="VALOR TOTAL DA NOTA FISCAL",
                 font=("Segoe UI", 10, "bold"),
                 bg="#1a3a5c", fg="white").pack(side="left")
        tk.Label(tot_nf_f,
                 text=f"R$ {_f(nota.get('total_nf'))}",
                 font=("Segoe UI", 14, "bold"),
                 bg="#1a3a5c", fg="#ffd700").pack(side="right")

        # ── Condição de pagamento ─────────────────────────────────
        if nota.get("cond_pagamento"):
            self._secao(f, "DADOS DA COBRANÇA / PAGAMENTO")
            pg_f = tk.Frame(f, bg="white", padx=8, pady=4)
            pg_f.pack(fill="x")
            tk.Label(pg_f, text=nota["cond_pagamento"],
                     font=("Segoe UI", 9), bg="white", fg="#333").pack(anchor="w")

        # ── Informações Complementares ────────────────────────────
        if nota.get("info_complementar") or nota.get("observacoes"):
            self._secao(f, "INFORMAÇÕES COMPLEMENTARES")
            ic_f = tk.Frame(f, bg="#fffef0", padx=8, pady=6,
                            highlightthickness=1, highlightbackground="#e0d080")
            ic_f.pack(fill="x", padx=8, pady=(2, 0))
            txt_ic = (nota.get("info_complementar") or "") + "\n" + (nota.get("observacoes") or "")
            tk.Label(ic_f, text=txt_ic.strip(),
                     font=("Segoe UI", 8), bg="#fffef0", fg="#444",
                     wraplength=W - 40, justify="left").pack(anchor="w")

        # ── Depósito e usuário ────────────────────────────────────
        rodape_nf = tk.Frame(f, bg="#f0f0f0", padx=8, pady=6)
        rodape_nf.pack(fill="x", pady=(6, 10))
        dep  = nota.get("deposito_nome") or "—"
        usu  = nota.get("usuario_nome") or "—"
        cri  = _fmt_data((nota.get("criado_em") or "")[:10])
        tk.Label(rodape_nf,
                 text=f"Depósito: {dep}  |  Usuário: {usu}  |  Lançado em: {cri}",
                 font=("Segoe UI", 8), bg="#f0f0f0", fg="#666").pack(side="left")

    def _secao(self, parent, titulo: str):
        f = tk.Frame(parent, bg="#2c4a7c", padx=8, pady=3)
        f.pack(fill="x", padx=8, pady=(6, 0))
        tk.Label(f, text=titulo, font=("Segoe UI", 8, "bold"),
                 bg="#2c4a7c", fg="white").pack(anchor="w")

    def _row_dados(self, parent, campos: list):
        """
        campos = [(label, valor, peso), ...]
        """
        row = tk.Frame(parent, bg="white")
        row.pack(fill="x", pady=1)
        for lbl, val, peso in campos:
            col = tk.Frame(row, bg="white",
                           highlightthickness=1, highlightbackground="#ddd")
            col.pack(side="left", fill="both", expand=bool(peso > 1),
                     padx=(0, 2))
            inner = tk.Frame(col, bg="white", padx=5, pady=3)
            inner.pack(fill="both")
            tk.Label(inner, text=lbl, font=("Segoe UI", 7),
                     bg="white", fg="#888").pack(anchor="w")
            tk.Label(inner, text=val or "—", font=("Segoe UI", 9, "bold"),
                     bg="white", fg="#111",
                     wraplength=200 * peso, justify="left").pack(anchor="w")

    # ── Export PDF ────────────────────────────────────────────────
    def _exportar_pdf(self):
        try:
            import reportlab
            self._gerar_pdf()
        except ImportError:
            # Fallback: exportar como texto estruturado
            self._exportar_txt()

    def _gerar_pdf(self):
        """Gera PDF do DANFE via ReportLab."""
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.units import mm
        from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                         Paragraph, Spacer)
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        import io

        path = filedialog.asksaveasfilename(
            title="Salvar DANFE como PDF",
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            initialfile=f"DANFE_NF{self._nota.get('numero') or self._nota_id}.pdf",
            parent=self
        )
        if not path:
            return

        nota   = self._nota
        itens  = self._itens
        emp    = self._empresa
        doc    = SimpleDocTemplate(path, pagesize=A4,
                                    leftMargin=10*mm, rightMargin=10*mm,
                                    topMargin=10*mm, bottomMargin=10*mm)
        styles = getSampleStyleSheet()
        bold   = ParagraphStyle("bold", parent=styles["Normal"],
                                fontName="Helvetica-Bold", fontSize=8)
        normal = ParagraphStyle("normal", parent=styles["Normal"],
                                fontName="Helvetica", fontSize=8)
        small  = ParagraphStyle("small", parent=styles["Normal"],
                                fontName="Helvetica", fontSize=7)

        story = []

        # Cabeçalho
        hdr_data = [
            [
                Paragraph(f"<b>{emp.get('razao_social') or emp.get('nome','')}</b><br/>"
                          f"CNPJ: {_mask_cnpj(emp.get('cnpj'))}<br/>"
                          f"IE: {emp.get('ie') or '—'}", normal),
                Paragraph("<b>DANFE</b><br/>Documento Auxiliar da<br/>Nota Fiscal Eletrônica", bold),
                Paragraph(f"<b>NF-e Nº {str(nota.get('numero') or '').zfill(9)}</b><br/>"
                          f"Série: {nota.get('serie')}<br/>"
                          f"Emissão: {_fmt_data(nota.get('data_emissao'))}<br/>"
                          f"Entrada: {_fmt_data(nota.get('data_entrada'))}", normal),
            ]
        ]
        t_hdr = Table(hdr_data, colWidths=[70*mm, 60*mm, 60*mm])
        t_hdr.setStyle(TableStyle([
            ("BOX", (0,0), (-1,-1), 0.5, colors.grey),
            ("INNERGRID", (0,0), (-1,-1), 0.3, colors.grey),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("ALIGN", (1,0), (1,0), "CENTER"),
        ]))
        story.append(t_hdr)
        story.append(Spacer(1, 3*mm))

        # Chave
        chave = nota.get("chave_acesso") or ""
        chave_fmt = " ".join(chave[i:i+4] for i in range(0, len(chave), 4))
        story.append(Paragraph(f"<b>Chave de Acesso:</b> {chave_fmt}", small))
        story.append(Spacer(1, 3*mm))

        # Fornecedor
        story.append(Paragraph("<b>EMITENTE (FORNECEDOR)</b>", bold))
        story.append(Paragraph(
            f"{nota.get('terceiro_nome') or '—'}  |  "
            f"CNPJ/CPF: {_mask_cnpj(nota.get('terceiro_doc'))}", normal
        ))
        story.append(Spacer(1, 3*mm))

        # Itens
        story.append(Paragraph("<b>PRODUTOS / SERVIÇOS</b>", bold))
        item_hdr = ["Cód", "Descrição", "NCM", "CFOP", "Un", "Qtd",
                    "V.Unit", "V.Tot", "ICMS", "IPI", "Total"]
        item_rows = [item_hdr]
        for item in itens:
            item_rows.append([
                item.get("codigo") or item.get("codigo_fornecedor") or "—",
                item.get("descricao") or "—",
                item.get("ncm") or "—",
                item.get("cfop") or "—",
                item.get("unidade") or "—",
                _f(item.get("quantidade"), 3),
                _f(item.get("valor_unitario"), 4),
                _f(item.get("valor_total")),
                _f(item.get("valor_icms")),
                _f(item.get("valor_ipi")),
                _f(item.get("valor_total")),
            ])
        t_itens = Table(item_rows,
                        colWidths=[14*mm,52*mm,15*mm,12*mm,10*mm,
                                   15*mm,18*mm,18*mm,16*mm,14*mm,18*mm])
        t_itens.setStyle(TableStyle([
            ("BOX", (0,0), (-1,-1), 0.5, colors.grey),
            ("INNERGRID", (0,0), (-1,-1), 0.2, colors.lightgrey),
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#2c4a7c")),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE", (0,0), (-1,-1), 7),
            ("ROWBACKGROUNDS", (0,1), (-1,-1),
             [colors.white, colors.HexColor("#f7f9fc")]),
            ("ALIGN", (5,0), (-1,-1), "RIGHT"),
        ]))
        story.append(t_itens)
        story.append(Spacer(1, 3*mm))

        # Totais
        story.append(Paragraph("<b>TOTAIS</b>", bold))
        tot_rows = [[
            f"Produtos: R$ {_f(nota.get('total_produtos'))}",
            f"Frete: R$ {_f(nota.get('total_frete'))}",
            f"Desconto: R$ {_f(nota.get('total_desconto'))}",
            f"IPI: R$ {_f(nota.get('total_ipi'))}",
            f"ICMS: R$ {_f(nota.get('total_icms'))}",
        ],[
            Paragraph(f"<b>VALOR TOTAL DA NF: R$ {_f(nota.get('total_nf'))}</b>", bold),
            "", "", "", "",
        ]]
        t_tot = Table(tot_rows, colWidths=[38*mm]*5)
        t_tot.setStyle(TableStyle([
            ("BOX", (0,0), (-1,-1), 0.5, colors.grey),
            ("INNERGRID", (0,0), (-1,-1), 0.2, colors.lightgrey),
            ("SPAN", (0,1), (-1,1)),
            ("BACKGROUND", (0,1), (-1,1), colors.HexColor("#1a3a5c")),
            ("TEXTCOLOR", (0,1), (-1,1), colors.HexColor("#ffd700")),
            ("FONTSIZE", (0,0), (-1,-1), 8),
        ]))
        story.append(t_tot)

        if nota.get("info_complementar") or nota.get("observacoes"):
            story.append(Spacer(1, 3*mm))
            story.append(Paragraph("<b>INFORMAÇÕES COMPLEMENTARES</b>", bold))
            story.append(Paragraph(
                (nota.get("info_complementar") or "") + " " +
                (nota.get("observacoes") or ""), small
            ))

        doc.build(story)
        messagebox.showinfo("PDF Gerado",
            f"DANFE exportado com sucesso:\n{path}", parent=self)

        # Tenta abrir automaticamente
        import subprocess, sys
        try:
            if sys.platform == "win32":
                import os; os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.run(["open", path])
            else:
                subprocess.run(["xdg-open", path])
        except Exception:
            pass

    def _exportar_txt(self):
        """Fallback: exporta DANFE como TXT formatado."""
        nota  = self._nota
        emp   = self._empresa
        sep   = "─" * 80

        linhas = [
            sep,
            "DANFE — DOCUMENTO AUXILIAR DA NOTA FISCAL ELETRÔNICA".center(80),
            sep,
            f"EMITENTE : {emp.get('razao_social') or emp.get('nome')}",
            f"CNPJ     : {_mask_cnpj(emp.get('cnpj'))}",
            f"IE       : {emp.get('ie') or '—'}",
            sep,
            f"NF-e Nº  : {str(nota.get('numero') or '').zfill(9)}  Série: {nota.get('serie')}",
            f"Emissão  : {_fmt_data(nota.get('data_emissao'))}   Entrada: {_fmt_data(nota.get('data_entrada'))}",
            f"Status   : {nota.get('status')}",
            f"Chave    : {nota.get('chave_acesso') or '—'}",
            sep,
            f"FORNECEDOR: {nota.get('terceiro_nome') or '—'}",
            f"CNPJ/CPF  : {_mask_cnpj(nota.get('terceiro_doc'))}",
            sep,
            f"{'Cód':<10} {'Descrição':<35} {'Un':<4} {'Qtd':>8} {'V.Unit':>12} {'Total':>12}",
            "─" * 80,
        ]
        for item in self._itens:
            linhas.append(
                f"{(item.get('codigo') or '—'):<10} "
                f"{(item.get('descricao') or '')[:35]:<35} "
                f"{(item.get('unidade') or ''):<4} "
                f"{float(item.get('quantidade') or 0):>8.3f} "
                f"{float(item.get('valor_unitario') or 0):>12.4f} "
                f"{float(item.get('valor_total') or 0):>12.2f}"
            )
        linhas += [
            sep,
            f"{'Produtos':>50}: R$ {_f(nota.get('total_produtos'))}",
            f"{'Frete':>50}: R$ {_f(nota.get('total_frete'))}",
            f"{'Desconto':>50}: R$ {_f(nota.get('total_desconto'))}",
            f"{'IPI':>50}: R$ {_f(nota.get('total_ipi'))}",
            f"{'ICMS':>50}: R$ {_f(nota.get('total_icms'))}",
            f"{'VALOR TOTAL DA NOTA':>50}: R$ {_f(nota.get('total_nf'))}",
            sep,
        ]
        if nota.get("info_complementar"):
            linhas += ["INFORMAÇÕES COMPLEMENTARES:", nota["info_complementar"], sep]

        texto = "\n".join(linhas)

        path = filedialog.asksaveasfilename(
            title="Salvar DANFE como TXT",
            defaultextension=".txt",
            filetypes=[("Texto", "*.txt")],
            initialfile=f"DANFE_NF{nota.get('numero') or self._nota_id}.txt",
            parent=self
        )
        if path:
            with open(path, "w", encoding="utf-8") as fp:
                fp.write(texto)
            messagebox.showinfo("Exportado", f"DANFE exportado:\n{path}", parent=self)