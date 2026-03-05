"""View de caixa - abertura, fechamento, sangria, suprimento, relatorio."""
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from config import THEME, FONT
from core.session import Session


def selecionar_caixa(master) -> dict | None:
    """Dialogo para selecionar um caixa aberto. Retorna dict ou None."""
    from models.caixa import Caixa
    abertos = Caixa.listar(so_abertos=True)
    if not abertos: messagebox.showwarning("Caixa","Nenhum caixa aberto."); return None
    if len(abertos) == 1: return abertos[0]
    win = tk.Toplevel(master); win.title("Selecionar Caixa"); win.grab_set()
    win.transient(master.winfo_toplevel())
    from assets import Assets
    Assets.setup_toplevel(win, 300, 200)
    tk.Label(win, text="Selecione o caixa:", font=FONT["bold"]).pack(pady=12)
    var = tk.StringVar()
    lb = tk.Listbox(win, font=FONT["md"]); lb.pack(fill="both", expand=True, padx=16)
    for c in abertos: lb.insert("end","  Caixa {} - {}".format(c["numero"],c["nome"]))
    lb.selection_set(0)
    resultado = [None]
    def ok():
        idx = lb.curselection()
        if idx: resultado[0] = abertos[idx[0]]
        win.destroy()
    tk.Button(win, text="OK", command=ok, bg=THEME["primary"], fg="white", font=FONT["bold"], relief="flat").pack(pady=8)
    win.wait_window(); return resultado[0]


class CaixaView(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg=THEME["bg"])
        self._build()
        self.atualizar()

    def _build(self):
        top = tk.Frame(self, bg=THEME["bg"]); top.pack(fill="x", padx=16, pady=8)
        tk.Label(top, text="Controle de Caixa", font=FONT["title"], bg=THEME["bg"], fg=THEME["fg"]).pack(side="left")
        tk.Button(top, text="Atualizar", command=self.atualizar, bg=THEME["secondary"], fg="white", font=FONT["sm"], relief="flat", padx=10).pack(side="right")
        # Lista de caixas
        fr = tk.Frame(self, bg=THEME["bg"]); fr.pack(fill="both", expand=True, padx=16, pady=4)
        cols = ("num","nome","operador","status","abertura","saldo")
        self._tree = ttk.Treeview(fr, columns=cols, show="headings", height=12)
        for c,l,w in [("num","Cx",40),("nome","Nome",120),("operador","Operador",140),("status","Status",80),("abertura","Abertura",80),("saldo","Saldo",100)]:
            self._tree.heading(c,text=l); self._tree.column(c,width=w,anchor="e" if c in ("abertura","saldo") else "w")
        self._tree.pack(fill="both", expand=True)
        self._tree.tag_configure("aberto", foreground="#2dce89")
        self._tree.tag_configure("fechado", foreground="#aaa")
        # Botoes de acao
        bar = tk.Frame(self, bg=THEME["bg"]); bar.pack(fill="x", padx=16, pady=8)
        for txt, cor, cmd in [
            ("Abrir caixa", THEME["success"], self._abrir),
            ("Fechar caixa", THEME["danger"], self._fechar),
            ("Sangria", THEME["warning"], self._sangria),
            ("Suprimento", THEME["primary"], self._suprimento),
            ("Relatorio", THEME["secondary"], self._relatorio),
        ]:
            tk.Button(bar, text=txt, command=cmd, bg=cor, fg="white", font=FONT["sm"], relief="flat", padx=10).pack(side="left", padx=4)

    def atualizar(self):
        from models.caixa import Caixa
        self._tree.delete(*self._tree.get_children())
        for c in Caixa.listar():
            saldo = Caixa.saldo_atual(c["id"])
            tag = "aberto" if c["status"]=="ABERTO" else "fechado"
            self._tree.insert("","end",iid=str(c["id"]),tags=(tag,),values=(c["numero"],c["nome"] or "",c["operador_nome"] or "",c["status"],"R$ {:.2f}".format(float(c["valor_abertura"] or 0)),"R$ {:.2f}".format(saldo)))

    def _caixa_selecionado(self):
        sel = self._tree.selection()
        if not sel: messagebox.showwarning("Aviso","Selecione um caixa."); return None
        from models.caixa import Caixa
        return Caixa.buscar_por_id(int(sel[0]))

    def _abrir(self):
        from models.caixa import Caixa
        sess = Session.usuario()
        if Caixa.aberto_do_operador(sess.get("id")):
            messagebox.showwarning("Aviso","Voce ja tem um caixa aberto."); return
        num = simpledialog.askinteger("Abrir caixa","Numero do caixa:",minvalue=1,parent=self)
        if not num: return
        nome = simpledialog.askstring("Abrir caixa","Nome do caixa:",initialvalue="Caixa {}".format(num),parent=self)
        val = simpledialog.askfloat("Abertura","Valor de abertura (fundo de troco):",initialvalue=0,minvalue=0,parent=self)
        if val is None: return
        Caixa.abrir(num, nome or "", sess.get("id"), sess.get("nome", ""), val)
        self.atualizar()

    def _fechar(self):
        caixa = self._caixa_selecionado()
        if not caixa or caixa["status"]!="ABERTO": messagebox.showwarning("Aviso","Selecione um caixa aberto."); return
        from models.caixa import Caixa
        saldo = Caixa.saldo_atual(caixa["id"])
        if not messagebox.askyesno("Fechar caixa","Saldo sistema: R$ {:.2f}\nFechar o caixa?".format(saldo),parent=self): return
        val = simpledialog.askfloat("Fechamento","Valor contado em caixa:",initialvalue=round(saldo,2),minvalue=0,parent=self)
        if val is None: return
        sess = Session.usuario()
        obs = simpledialog.askstring("Observacao","Observacao (opcional):",parent=self) or ""
        Caixa.fechar(caixa["id"],val,sess.get("id"),sess.get("nome", ""),obs)
        self.atualizar(); self._relatorio_por_id(caixa["id"])

    def _sangria(self):
        caixa = self._caixa_selecionado()
        if not caixa or caixa["status"]!="ABERTO": return
        val = simpledialog.askfloat("Sangria","Valor da sangria:",minvalue=0.01,parent=self)
        if not val: return
        desc = simpledialog.askstring("Sangria","Motivo:",parent=self) or "Sangria"
        sess = Session.usuario()
        from models.caixa import Caixa; Caixa.sangria(caixa["id"],val,desc,sess.get("id"),sess.get("nome", ""))
        self.atualizar()

    def _suprimento(self):
        caixa = self._caixa_selecionado()
        if not caixa or caixa["status"]!="ABERTO": return
        val = simpledialog.askfloat("Suprimento","Valor do suprimento:",minvalue=0.01,parent=self)
        if not val: return
        desc = simpledialog.askstring("Suprimento","Descricao:",parent=self) or "Suprimento"
        sess = Session.usuario()
        from models.caixa import Caixa; Caixa.suprimento(caixa["id"],val,desc,sess.get("id"),sess.get("nome", ""))
        self.atualizar()

    def _relatorio(self):
        caixa = self._caixa_selecionado()
        if not caixa: return
        self._relatorio_por_id(caixa["id"])

    def _relatorio_por_id(self, caixa_id):
        from models.caixa import Caixa
        r  = Caixa.resumo_fechamento(caixa_id)
        cx = r["caixa"]
        tv = r["total_vendas"]

        win = tk.Toplevel(self)
        win.title("Relatório de Caixa")
        win.grab_set()
        win.transient(self.winfo_toplevel())
        win.configure(bg=THEME["bg"])
        from assets import Assets
        Assets.setup_toplevel(win, 460, 580)

        # ── Cabeçalho ──────────────────────────────────────────────────────
        hdr = tk.Frame(win, bg=THEME["primary"], pady=14)
        hdr.pack(fill="x")
        tk.Label(hdr, text="RELATÓRIO DE CAIXA",
                 font=FONT["title"], bg=THEME["primary"], fg="white").pack()
        tk.Label(hdr,
                 text="Caixa {}  —  {}".format(cx.get("numero",""), cx.get("nome","")),
                 font=FONT["bold"], bg=THEME["primary"], fg="white").pack()
        tk.Label(hdr, text="Operador: {}".format(cx.get("operador_nome","")),
                 font=FONT["sm"], bg=THEME["primary"], fg="#d0e8ff").pack()

        # ── Área com scroll ─────────────────────────────────────────────────
        canvas = tk.Canvas(win, bg=THEME["bg"], highlightthickness=0)
        vsb    = ttk.Scrollbar(win, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True)
        body = tk.Frame(canvas, bg=THEME["bg"])
        wid  = canvas.create_window((0, 0), window=body, anchor="nw")
        body.bind("<Configure>", lambda _: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(wid, width=e.width))
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

        P = 20

        def secao(titulo, cor=THEME["primary"]):
            fr_t = tk.Frame(body, bg=cor, padx=P, pady=5)
            fr_t.pack(fill="x", padx=P, pady=(14, 0))
            tk.Label(fr_t, text=titulo, font=FONT["bold"],
                     bg=cor, fg="white").pack(anchor="w")
            fr_c = tk.Frame(body, bg=THEME["bg_card"],
                            highlightthickness=1,
                            highlightbackground=THEME["border"])
            fr_c.pack(fill="x", padx=P)
            return fr_c

        def linha(pai, rotulo, valor, fg_valor=THEME["fg"], negrito=False):
            row = tk.Frame(pai, bg=THEME["bg_card"])
            row.pack(fill="x", padx=14, pady=3)
            tk.Label(row, text=rotulo, font=FONT["sm"],
                     bg=THEME["bg_card"], fg=THEME["fg_light"],
                     anchor="w", width=22).pack(side="left")
            tk.Label(row, text=valor,
                     font=FONT["md_bold"] if negrito else FONT["md"],
                     bg=THEME["bg_card"], fg=fg_valor,
                     anchor="e").pack(side="right")

        # ── Resumo de vendas ────────────────────────────────────────────────
        s1 = secao("RESUMO DE VENDAS")
        linha(s1, "Valor de abertura:", "R$ {:,.2f}".format(float(cx.get("valor_abertura") or 0)))
        linha(s1, "Vendas finalizadas:", str(int(tv["qtd"])))
        linha(s1, "Total vendido:", "R$ {:,.2f}".format(float(tv["total"])),
              fg_valor=THEME["success"], negrito=True)
        linha(s1, "Canceladas:", str(int(r["qtd_canceladas"])),
              fg_valor=THEME["danger"] if r["qtd_canceladas"] else THEME["fg"])
        if r["total_descontos"] > 0:
            linha(s1, "Descontos concedidos:", "R$ {:,.2f}".format(r["total_descontos"]),
                  fg_valor=THEME["warning"])
        if r["total_troco"] > 0:
            linha(s1, "Troco total dado:", "R$ {:,.2f}".format(r["total_troco"]),
                  fg_valor=THEME["warning"])

        # ── Por forma de pagamento ──────────────────────────────────────────
        FORMAS_LABEL = {
            "DINHEIRO": "Dinheiro", "DEBITO": "Cartão Débito",
            "CREDITO": "Cartão Crédito", "PIX": "Pix",
            "VR": "Vale-Refeição", "VA": "Vale-Alimentação", "OUTROS": "Outros",
        }
        if r["por_forma"]:
            s2 = secao("FORMAS DE PAGAMENTO", cor=THEME["secondary"])
            for pf in r["por_forma"]:
                nome_forma = FORMAS_LABEL.get(pf["forma"], pf["forma"])
                linha(s2,
                      "{}  ({} lançto{}):".format(nome_forma, pf["qtd"], "s" if pf["qtd"] != 1 else ""),
                      "R$ {:,.2f}".format(float(pf["total"])),
                      fg_valor=THEME["primary"], negrito=True)

        # ── Movimentos individuais (sangria / suprimento) ───────────────────
        movs_ind = [m for m in Caixa.movimentos(caixa_id)
                    if m["tipo"] in ("SANGRIA", "SUPRIMENTO")]
        if movs_ind:
            TIPOS = {"SANGRIA": ("Sangria", THEME["danger"]),
                     "SUPRIMENTO": ("Suprimento", THEME["success"])}
            s3 = secao("MOVIMENTOS DE CAIXA", cor=THEME["warning"])
            for mv in movs_ind:
                label, cor_val = TIPOS.get(mv["tipo"], (mv["tipo"], THEME["fg"]))
                hora = (mv.get("criado_em") or "")[:16]
                desc = mv.get("descricao") or ""
                row = tk.Frame(s3, bg=THEME["bg_card"])
                row.pack(fill="x", padx=14, pady=3)
                tk.Label(row, text=label,
                         font=FONT["sm"], bg=THEME["bg_card"], fg=cor_val,
                         width=10, anchor="w").pack(side="left")
                tk.Label(row, text=desc,
                         font=FONT["sm"], bg=THEME["bg_card"], fg=THEME["fg_light"],
                         anchor="w").pack(side="left", padx=(0, 8))
                tk.Label(row, text=hora,
                         font=FONT["sm"], bg=THEME["bg_card"],
                         fg=THEME["fg_light"]).pack(side="left")
                tk.Label(row, text="R$ {:,.2f}".format(abs(float(mv["valor"]))),
                         font=FONT["md_bold"], bg=THEME["bg_card"],
                         fg=cor_val).pack(side="right")

        # ── Saldo sistema ───────────────────────────────────────────────────
        saldo_fr = tk.Frame(body, bg=THEME["bg_card"],
                            highlightthickness=1, highlightbackground=THEME["border"])
        saldo_fr.pack(fill="x", padx=P, pady=(16, 4))
        tk.Label(saldo_fr, text="SALDO DO SISTEMA",
                 font=FONT["bold"], bg=THEME["bg_card"],
                 fg=THEME["fg_light"]).pack(anchor="w", padx=14, pady=(8, 0))
        tk.Label(saldo_fr,
                 text="R$ {:,.2f}".format(r["saldo_sistema"]),
                 font=FONT["xl_bold"], bg=THEME["bg_card"],
                 fg=THEME["primary"]).pack(anchor="e", padx=14, pady=(0, 8))

        # ── Botões ──────────────────────────────────────────────────────────
        btn_row = tk.Frame(body, bg=THEME["bg"])
        btn_row.pack(pady=16)
        tk.Button(btn_row, text="Imprimir / PDF",
                  command=lambda: self._imprimir_relatorio(r, movs_ind),
                  bg=THEME["secondary"], fg="white",
                  font=FONT["bold"], relief="flat",
                  padx=20, pady=8).pack(side="left", padx=6)
        tk.Button(btn_row, text="Fechar", command=win.destroy,
                  bg=THEME["primary"], fg="white",
                  font=FONT["bold"], relief="flat",
                  padx=20, pady=8).pack(side="left", padx=6)

    def _imprimir_relatorio(self, r: dict, movs_ind: list):
        import tempfile, os, datetime
        from tkinter import messagebox as mb
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib import colors
            from reportlab.lib.styles import ParagraphStyle
            from reportlab.lib.units import mm
            from reportlab.platypus import (SimpleDocTemplate, Paragraph,
                                            Table, TableStyle, Spacer,
                                            HRFlowable)
            from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
        except ImportError:
            mb.showerror("Erro", "reportlab não instalado.\nExecute: pip install reportlab")
            return

        from core.session import Session

        cx   = r["caixa"]
        tv   = r["total_vendas"]
        emp  = Session.empresa() or {}
        agora = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")

        AZUL     = colors.HexColor("#1a237e")
        AZUL_CLR = colors.HexColor("#e8eaf6")
        CINZA    = colors.HexColor("#f5f5f5")
        VERDE    = colors.HexColor("#2e7d32")
        VERMELHO = colors.HexColor("#c62828")
        LARANJA  = colors.HexColor("#e65100")
        BRANCO   = colors.white
        PRETO    = colors.HexColor("#212121")

        W = A4[0] - 28*mm   # largura útil

        def st(name, **kw):
            base = dict(fontName="Helvetica", fontSize=9, textColor=PRETO,
                        leading=13, spaceAfter=0)
            base.update(kw)
            return ParagraphStyle(name, **base)

        sNormal  = st("normal")
        sNegrito = st("negrito",  fontName="Helvetica-Bold")
        sDireita = st("direita",  alignment=TA_RIGHT)
        sCentro  = st("centro",   alignment=TA_CENTER)
        sSmall   = st("small",    fontSize=8, textColor=colors.HexColor("#555555"))
        sSmallR  = st("smallR",   fontSize=8, textColor=colors.HexColor("#555555"),
                      alignment=TA_RIGHT)
        sSaldo   = st("saldo",    fontName="Helvetica-Bold", fontSize=16,
                      textColor=AZUL, alignment=TA_RIGHT)

        def secao_header(texto):
            tbl = Table([[Paragraph(texto, st("sh", fontName="Helvetica-Bold",
                                              fontSize=9, textColor=BRANCO))]], colWidths=[W])
            tbl.setStyle(TableStyle([
                ("BACKGROUND", (0,0), (-1,-1), AZUL),
                ("TOPPADDING",    (0,0), (-1,-1), 5),
                ("BOTTOMPADDING", (0,0), (-1,-1), 5),
                ("LEFTPADDING",   (0,0), (-1,-1), 8),
            ]))
            return tbl

        def tabela_dois_col(linhas, col_esq=None):
            """linhas = [(rotulo, valor, cor_valor_opcional)]"""
            col_esq = col_esq or W * 0.60
            data = []
            styles = [
                ("FONTNAME",      (0,0), (-1,-1), "Helvetica"),
                ("FONTSIZE",      (0,0), (-1,-1), 9),
                ("ROWBACKGROUNDS",(0,0), (-1,-1), [BRANCO, CINZA]),
                ("TOPPADDING",    (0,0), (-1,-1), 4),
                ("BOTTOMPADDING", (0,0), (-1,-1), 4),
                ("LEFTPADDING",   (0,0), (-1,-1), 8),
                ("RIGHTPADDING",  (0,0), (-1,-1), 8),
                ("GRID",          (0,0), (-1,-1), 0.3, colors.HexColor("#e0e0e0")),
                ("ALIGN",         (1,0), (1,-1), "RIGHT"),
            ]
            for i, row in enumerate(linhas):
                rotulo, valor = row[0], row[1]
                cor = row[2] if len(row) > 2 else None
                p_rot = Paragraph(rotulo, sSmall)
                p_val = Paragraph("<b>{}</b>".format(valor) if cor else valor,
                                  ParagraphStyle("v", parent=sDireita,
                                                 fontSize=9,
                                                 textColor=cor or PRETO,
                                                 fontName="Helvetica-Bold" if cor else "Helvetica"))
                data.append([p_rot, p_val])
                if cor:
                    styles.append(("FONTNAME", (1,i), (1,i), "Helvetica-Bold"))
            tbl = Table(data, colWidths=[col_esq, W - col_esq])
            tbl.setStyle(TableStyle(styles))
            return tbl

        FORMAS_LABEL = {
            "DINHEIRO": "Dinheiro", "DEBITO": "Cartão Débito",
            "CREDITO": "Cartão Crédito", "PIX": "Pix",
            "VR": "Vale-Refeição", "VA": "Vale-Alimentação", "OUTROS": "Outros",
        }

        # ── monta o documento ───────────────────────────────────────────────
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        tmp.close()
        path = tmp.name

        doc = SimpleDocTemplate(path, pagesize=A4,
                                leftMargin=14*mm, rightMargin=14*mm,
                                topMargin=14*mm, bottomMargin=14*mm,
                                title="Relatório de Caixa {}".format(cx.get("numero","")))
        story = []

        # ── Cabeçalho empresa ───────────────────────────────────────────────
        nome_emp     = emp.get("nome") or emp.get("razao_social") or "Empresa"
        razao        = emp.get("razao_social") or ""
        cnpj         = emp.get("cnpj") or ""
        end_parts    = [p for p in [
            emp.get("endereco"), emp.get("numero"),
            emp.get("bairro"),   emp.get("cidade"),
            emp.get("estado"),
        ] if p]
        endereco     = ", ".join(end_parts)
        tel          = emp.get("telefone") or ""
        email        = emp.get("email") or ""

        story.append(Paragraph(nome_emp,
                                st("empNome", fontName="Helvetica-Bold",
                                   fontSize=13, textColor=AZUL)))
        if razao and razao != nome_emp:
            story.append(Paragraph(razao, sSmall))
        if cnpj:
            story.append(Paragraph("CNPJ: {}".format(cnpj), sSmall))
        if endereco:
            story.append(Paragraph(endereco, sSmall))
        contato = "  |  ".join(filter(None, [tel, email]))
        if contato:
            story.append(Paragraph(contato, sSmall))

        story.append(Spacer(1, 4*mm))
        story.append(HRFlowable(width=W, thickness=2, color=AZUL))
        story.append(Spacer(1, 3*mm))

        # título do relatório
        story.append(Paragraph("RELATÓRIO DE CAIXA",
                                st("titulo", fontName="Helvetica-Bold",
                                   fontSize=14, textColor=AZUL, alignment=TA_CENTER)))
        story.append(Spacer(1, 2*mm))

        # info do caixa
        info_cx = [
            ["Caixa:", "{}  —  {}".format(cx.get("numero",""), cx.get("nome",""))],
            ["Operador:", cx.get("operador_nome","")],
            ["Status:", cx.get("status","")],
            ["Emitido em:", agora],
        ]
        if cx.get("aberto_em"):
            info_cx.append(["Abertura:", str(cx["aberto_em"])[:16]])
        if cx.get("fechado_em"):
            info_cx.append(["Fechamento:", str(cx["fechado_em"])[:16]])

        tbl_info = Table(
            [[Paragraph(k, sSmall), Paragraph(v, sNegrito)]
             for k, v in info_cx],
            colWidths=[30*mm, W - 30*mm]
        )
        tbl_info.setStyle(TableStyle([
            ("TOPPADDING",    (0,0), (-1,-1), 3),
            ("BOTTOMPADDING", (0,0), (-1,-1), 3),
            ("LEFTPADDING",   (0,0), (-1,-1), 4),
        ]))
        story.append(tbl_info)
        story.append(Spacer(1, 4*mm))

        # ── Resumo de vendas ────────────────────────────────────────────────
        story.append(secao_header("RESUMO DE VENDAS"))
        linhas_resumo = [
            ("Valor de abertura:", "R$ {:,.2f}".format(float(cx.get("valor_abertura") or 0))),
            ("Vendas finalizadas:", str(int(tv["qtd"]))),
            ("Total vendido:", "R$ {:,.2f}".format(float(tv["total"])), VERDE),
            ("Canceladas:", str(int(r["qtd_canceladas"])),
             VERMELHO if r["qtd_canceladas"] else None),
        ]
        if r["total_descontos"] > 0:
            linhas_resumo.append(("Descontos concedidos:",
                                  "R$ {:,.2f}".format(r["total_descontos"]), LARANJA))
        if r["total_troco"] > 0:
            linhas_resumo.append(("Troco total dado:",
                                  "R$ {:,.2f}".format(r["total_troco"]), LARANJA))
        # remove None na cor
        linhas_resumo = [tuple(x for x in l if x is not None)
                         if len(l) == 3 and l[2] is None else l
                         for l in linhas_resumo]
        story.append(tabela_dois_col(linhas_resumo))
        story.append(Spacer(1, 4*mm))

        # ── Formas de pagamento ─────────────────────────────────────────────
        if r["por_forma"]:
            story.append(secao_header("FORMAS DE PAGAMENTO"))
            linhas_forma = [
                ("{} ({} lançto{})".format(
                    FORMAS_LABEL.get(pf["forma"], pf["forma"]),
                    pf["qtd"], "s" if pf["qtd"] != 1 else ""),
                 "R$ {:,.2f}".format(float(pf["total"])),
                 colors.HexColor("#1565c0"))
                for pf in r["por_forma"]
            ]
            story.append(tabela_dois_col(linhas_forma))
            story.append(Spacer(1, 4*mm))

        # ── Movimentos de caixa ─────────────────────────────────────────────
        if movs_ind:
            story.append(secao_header("MOVIMENTOS DE CAIXA"))
            TIPOS_COR = {"SANGRIA": VERMELHO, "SUPRIMENTO": VERDE}
            data_movs = [[
                Paragraph("<b>Tipo</b>",    sSmall),
                Paragraph("<b>Descrição</b>", sSmall),
                Paragraph("<b>Horário</b>", sSmall),
                Paragraph("<b>Valor</b>",   ParagraphStyle("vh", parent=sSmallR,
                                                            fontName="Helvetica-Bold")),
            ]]
            for mv in movs_ind:
                tipo = mv.get("tipo","")
                cor  = TIPOS_COR.get(tipo, PRETO)
                hora = (mv.get("criado_em") or "")[:16]
                desc = mv.get("descricao") or ""
                val  = abs(float(mv.get("valor",0)))
                data_movs.append([
                    Paragraph(tipo.capitalize(),
                               ParagraphStyle("tc", parent=sSmall,
                                              textColor=cor, fontName="Helvetica-Bold")),
                    Paragraph(desc, sSmall),
                    Paragraph(hora, sSmall),
                    Paragraph("R$ {:,.2f}".format(val),
                               ParagraphStyle("vc", parent=sSmallR,
                                              textColor=cor, fontName="Helvetica-Bold")),
                ])
            cw = [25*mm, W-25*mm-35*mm-30*mm, 35*mm, 30*mm]
            tbl_movs = Table(data_movs, colWidths=cw)
            tbl_movs.setStyle(TableStyle([
                ("FONTSIZE",      (0,0), (-1,-1), 9),
                ("ROWBACKGROUNDS",(0,1), (-1,-1), [BRANCO, CINZA]),
                ("BACKGROUND",    (0,0), (-1,0),  AZUL_CLR),
                ("TOPPADDING",    (0,0), (-1,-1), 4),
                ("BOTTOMPADDING", (0,0), (-1,-1), 4),
                ("LEFTPADDING",   (0,0), (-1,-1), 8),
                ("RIGHTPADDING",  (0,0), (-1,-1), 8),
                ("GRID",          (0,0), (-1,-1), 0.3, colors.HexColor("#e0e0e0")),
                ("ALIGN",         (3,0), (3,-1), "RIGHT"),
            ]))
            story.append(tbl_movs)
            story.append(Spacer(1, 4*mm))

        # ── Saldo do sistema ────────────────────────────────────────────────
        story.append(HRFlowable(width=W, thickness=1, color=AZUL))
        story.append(Spacer(1, 3*mm))
        tbl_saldo = Table(
            [[Paragraph("SALDO DO SISTEMA", st("sl", fontName="Helvetica-Bold",
                                                fontSize=11, textColor=AZUL)),
              Paragraph("R$ {:,.2f}".format(r["saldo_sistema"]), sSaldo)]],
            colWidths=[W*0.5, W*0.5]
        )
        tbl_saldo.setStyle(TableStyle([
            ("ALIGN",         (1,0), (1,0), "RIGHT"),
            ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
            ("TOPPADDING",    (0,0), (-1,-1), 4),
            ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ]))
        story.append(tbl_saldo)

        # ── Rodapé ──────────────────────────────────────────────────────────
        story.append(Spacer(1, 6*mm))
        story.append(HRFlowable(width=W, thickness=0.5,
                                 color=colors.HexColor("#bdbdbd")))
        story.append(Paragraph("Documento gerado em {}".format(agora),
                                st("rodape", fontSize=7,
                                   textColor=colors.HexColor("#9e9e9e"),
                                   alignment=TA_RIGHT)))

        doc.build(story)
        os.startfile(path)