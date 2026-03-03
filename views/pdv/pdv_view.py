"""Tela PDV Varejo - venda rapida com busca de produto e pagamento misto."""
import tkinter as tk
from tkinter import ttk, messagebox
from config import THEME, FONT
from core.session import Session

class PDVView(tk.Toplevel):
    """Janela fullscreen de PDV varejo."""

    def __init__(self, master, caixa: dict):
        super().__init__(master)
        self.caixa  = caixa
        self.venda_id = None
        self.itens    = []
        self._criar_venda()
        self._build()
        self.state("zoomed")
        self.title("PDV — Caixa {} | {}".format(caixa["numero"], caixa["nome"]))
        self.protocol("WM_DELETE_WINDOW", self._fechar)
        self._busca_entry.focus()

    def _criar_venda(self):
        from models.venda import Venda
        sess = Session.usuario()
        self.venda_id = Venda.criar(
            caixa_id=self.caixa["id"],
            operador_id=sess.get("id"),
            operador_nome=sess.get("nome", ""))

    def _build(self):
        self.configure(bg=THEME["bg"])
        # Layout: esquerda=busca+itens | direita=totais+pagamento
        esq = tk.Frame(self, bg=THEME["bg"])
        esq.pack(side="left", fill="both", expand=True, padx=8, pady=8)
        dir_ = tk.Frame(self, bg=THEME["bg_card"], width=320)
        dir_.pack(side="right", fill="y", padx=8, pady=8)
        dir_.pack_propagate(False)
        self._build_busca(esq)
        self._build_itens(esq)
        self._build_totais(dir_)
        self._build_pagamento(dir_)
        self._build_botoes(dir_)

    def _build_busca(self, pai):
        fr = tk.Frame(pai, bg=THEME["bg"])
        fr.pack(fill="x", pady=(0,6))
        tk.Label(fr, text="Buscar produto (codigo ou nome):", bg=THEME["bg"],
                 font=FONT["bold"], fg=THEME["fg"]).pack(anchor="w")
        row = tk.Frame(fr, bg=THEME["bg"])
        row.pack(fill="x")
        self._busca_var = tk.StringVar()
        self._busca_entry = tk.Entry(row, textvariable=self._busca_var,
                                     font=FONT["lg"], relief="solid", bd=1)
        self._busca_entry.pack(side="left", fill="x", expand=True, ipady=6)
        self._busca_entry.bind("<Return>", lambda e: self._buscar())
        self._busca_entry.bind("<KP_Enter>", lambda e: self._buscar())
        tk.Button(row, text="Buscar", command=self._buscar,
                  bg=THEME["primary"], fg="white", font=FONT["bold"],
                  relief="flat", padx=12).pack(side="left", padx=(4,0))

        # Lista de resultados
        self._lista_res = tk.Listbox(fr, height=5, font=FONT["sm"],
                                     selectbackground=THEME["primary"])
        self._lista_res.pack(fill="x", pady=(4,0))
        self._lista_res.bind("<Double-Button-1>", lambda e: self._selecionar_produto())
        self._lista_res.bind("<Return>", lambda e: self._selecionar_produto())
        self._produtos_encontrados = []

    def _buscar(self):
        termo = self._busca_var.get().strip()
        if not termo: return
        from models.produto import Produto
        self._produtos_encontrados = Produto.listar(busca=termo)[:20]
        self._lista_res.delete(0, "end")
        for p in self._produtos_encontrados:
            self._lista_res.insert("end", "  [{}]  {}  —  R$ {:.2f}".format(
                p.get("codigo",""), p.get("nome",""), float(p.get("preco_venda",0))))
        if len(self._produtos_encontrados) == 1:
            self._selecionar_produto()
        elif self._produtos_encontrados:
            self._lista_res.selection_set(0)
            self._lista_res.focus()

    def _selecionar_produto(self):
        idx = self._lista_res.curselection()
        if not idx: return
        prod = self._produtos_encontrados[idx[0]]
        self._adicionar_item(prod, 1)
        self._busca_var.set("")
        self._lista_res.delete(0, "end")
        self._busca_entry.focus()

    def _build_itens(self, pai):
        tk.Label(pai, text="Itens da venda:", bg=THEME["bg"], font=FONT["bold"], fg=THEME["fg"]).pack(anchor="w")
        cols = ("nome","qtd","preco","desc","subtotal")
        self._tree = ttk.Treeview(pai, columns=cols, show="headings", height=16)
        for c,l,w in [("nome","Produto",280),("qtd","Qtd",60),("preco","Preco",80),("desc","Desc",70),("subtotal","Subtotal",90)]:
            self._tree.heading(c, text=l); self._tree.column(c, width=w, anchor="e" if c!="nome" else "w")
        self._tree.pack(fill="both", expand=True)
        fr = tk.Frame(pai, bg=THEME["bg"]); fr.pack(fill="x", pady=4)
        tk.Button(fr, text="Remover item", command=self._remover_item, bg=THEME["danger"], fg="white", font=FONT["sm"], relief="flat", padx=8).pack(side="left")
        tk.Button(fr, text="Alt. quantidade", command=self._alterar_qtd, bg=THEME["warning"], fg="white", font=FONT["sm"], relief="flat", padx=8).pack(side="left", padx=4)
        tk.Button(fr, text="Desconto item", command=self._desconto_item, bg=THEME["secondary"], fg="white", font=FONT["sm"], relief="flat", padx=8).pack(side="left")

    def _build_totais(self, pai):
        tk.Label(pai, text="TOTAIS", bg=THEME["bg_card"], font=FONT["bold"], fg=THEME["fg"]).pack(pady=(12,4))
        self._lbl_subtotal = tk.Label(pai, text="Subtotal: R$ 0,00", bg=THEME["bg_card"], font=FONT["md"], fg=THEME["fg"])
        self._lbl_subtotal.pack(anchor="w", padx=10)
        self._lbl_desconto = tk.Label(pai, text="Desconto: R$ 0,00", bg=THEME["bg_card"], font=FONT["md"], fg=THEME["danger"])
        self._lbl_desconto.pack(anchor="w", padx=10)
        self._lbl_total = tk.Label(pai, text="TOTAL: R$ 0,00", bg=THEME["bg_card"], font=FONT["xl_bold"], fg=THEME["primary"])
        self._lbl_total.pack(anchor="w", padx=10, pady=(4,8))
        tk.Button(pai, text="Desconto no total", command=self._desconto_total, bg=THEME["secondary"], fg="white", font=FONT["sm"], relief="flat").pack(fill="x", padx=10, pady=2)

    def _build_pagamento(self, pai):
        tk.Label(pai, text="PAGAMENTO", bg=THEME["bg_card"], font=FONT["bold"], fg=THEME["fg"]).pack(pady=(12,4))
        fr = tk.Frame(pai, bg=THEME["bg_card"]); fr.pack(fill="x", padx=10)
        self._forma_var = tk.StringVar(value="DINHEIRO")
        formas = ["DINHEIRO","DEBITO","CREDITO","PIX","VR","VA","OUTROS"]
        ttk.Combobox(fr, textvariable=self._forma_var, values=formas, state="readonly", width=16).pack(side="left")
        self._valor_pag_var = tk.StringVar(value="0.00")
        tk.Entry(fr, textvariable=self._valor_pag_var, width=10, font=FONT["md"], justify="right").pack(side="left", padx=4)
        tk.Button(fr, text="+", command=self._adicionar_pagamento, bg=THEME["success"], fg="white", font=FONT["bold"], relief="flat", padx=8).pack(side="left")
        self._lbl_pago = tk.Label(pai, text="Pago: R$ 0,00", bg=THEME["bg_card"], font=FONT["md"], fg=THEME["success"])
        self._lbl_pago.pack(anchor="w", padx=10, pady=(4,0))
        self._lbl_troco = tk.Label(pai, text="Troco: R$ 0,00", bg=THEME["bg_card"], font=FONT["md_bold"], fg=THEME["warning"])
        self._lbl_troco.pack(anchor="w", padx=10)
        self._lbl_falta = tk.Label(pai, text="Falta: R$ 0,00", bg=THEME["bg_card"], font=FONT["md_bold"], fg=THEME["danger"])
        self._lbl_falta.pack(anchor="w", padx=10)
        self._tree_pag = ttk.Treeview(pai, columns=("forma","valor"), show="headings", height=4)
        self._tree_pag.heading("forma", text="Forma"); self._tree_pag.column("forma", width=130)
        self._tree_pag.heading("valor", text="Valor");  self._tree_pag.column("valor", width=90, anchor="e")
        self._tree_pag.pack(fill="x", padx=10, pady=4)
        tk.Button(pai, text="Remover pagamento", command=self._remover_pagamento, bg=THEME["danger"], fg="white", font=FONT["sm"], relief="flat").pack(fill="x", padx=10, pady=2)

    def _build_botoes(self, pai):
        tk.Button(pai, text="FINALIZAR VENDA [F12]", command=self._finalizar,
                  bg=THEME["success"], fg="white", font=FONT["xl_bold"],
                  relief="flat", pady=10).pack(fill="x", padx=10, pady=(12,4))
        tk.Button(pai, text="Cancelar venda", command=self._cancelar,
                  bg=THEME["danger"], fg="white", font=FONT["sm"],
                  relief="flat").pack(fill="x", padx=10, pady=2)
        self.bind("<F12>", lambda e: self._finalizar())

    def _adicionar_item(self, produto, quantidade):
        from models.venda import Venda
        Venda.adicionar_item(self.venda_id, produto, quantidade)
        self._atualizar_tela()

    def _remover_item(self):
        sel = self._tree.selection()
        if not sel: return
        item_id = self._tree.item(sel[0])["values"][5]
        from models.venda import Venda
        Venda.remover_item(item_id)
        self._atualizar_tela()

    def _alterar_qtd(self):
        sel = self._tree.selection()
        if not sel: return
        vals = self._tree.item(sel[0])["values"]
        item_id = vals[5]
        qtd_atual = vals[1]
        nova = tk.simpledialog.askfloat("Quantidade", "Nova quantidade:", initialvalue=qtd_atual, minvalue=0.001)
        if nova:
            from models.venda import Venda
            Venda.alterar_quantidade(item_id, nova)
            self._atualizar_tela()

    def _desconto_item(self):
        sel = self._tree.selection()
        if not sel: return
        item_id = self._tree.item(sel[0])["values"][5]
        pct = tk.simpledialog.askfloat("Desconto", "Desconto em % (0-100):", minvalue=0, maxvalue=100)
        if pct is not None:
            from core.database import DatabaseManager
            _db = DatabaseManager.empresa()
            r = _db.fetchone("SELECT venda_id,preco_unitario,quantidade FROM venda_itens WHERE id=?", (item_id,))
            if r:
                desc = round(float(r["preco_unitario"])*float(r["quantidade"])*pct/100, 2)
                sub  = round(float(r["preco_unitario"])*float(r["quantidade"])-desc, 2)
                _db.execute("UPDATE venda_itens SET desconto_pct=?,desconto_valor=?,subtotal=? WHERE id=?", (pct, desc, sub, item_id))
                from models.venda import Venda; Venda._recalcular(r["venda_id"])
                self._atualizar_tela()

    def _desconto_total(self):
        pct = tk.simpledialog.askfloat("Desconto Total", "Desconto em %:", minvalue=0, maxvalue=100)
        if pct is not None:
            from models.venda import Venda
            Venda.aplicar_desconto_total(self.venda_id, desconto_pct=pct)
            self._atualizar_tela()

    def _adicionar_pagamento(self):
        try: valor = float(self._valor_pag_var.get().replace(",","."))
        except: return
        if valor <= 0: return
        from models.venda import Venda
        Venda.adicionar_pagamento(self.venda_id, self._forma_var.get(), valor)
        self._valor_pag_var.set("0.00")
        self._atualizar_tela()

    def _remover_pagamento(self):
        sel = self._tree_pag.selection()
        if not sel: return
        pag_id = self._tree_pag.item(sel[0])["values"][2]
        from models.venda import Venda
        Venda.remover_pagamento(pag_id)
        self._atualizar_tela()

    def _atualizar_tela(self):
        from models.venda import Venda
        venda = Venda.buscar_por_id(self.venda_id) or {}
        itens = Venda.itens(self.venda_id)
        pagtos = Venda.pagamentos(self.venda_id)
        self._tree.delete(*self._tree.get_children())
        for it in itens:
            self._tree.insert("", "end", values=(
                it["produto_nome"], "{:.3f}".format(float(it["quantidade"])),
                "R$ {:.2f}".format(float(it["preco_unitario"])),
                "R$ {:.2f}".format(float(it.get("desconto_valor",0))),
                "R$ {:.2f}".format(float(it["subtotal"])), it["id"]))
        sub = float(venda.get("subtotal",0)); desc = float(venda.get("desconto_valor",0)); tot = float(venda.get("total",0))
        pago = float(venda.get("total_pago",0)); troco = float(venda.get("troco",0))
        self._lbl_subtotal.config(text="Subtotal: R$ {:.2f}".format(sub))
        self._lbl_desconto.config(text="Desconto: R$ {:.2f}".format(desc))
        self._lbl_total.config(text="TOTAL: R$ {:.2f}".format(tot))
        self._lbl_pago.config(text="Pago: R$ {:.2f}".format(pago))
        self._lbl_troco.config(text="Troco: R$ {:.2f}".format(troco))
        falta = max(0, tot-pago)
        self._lbl_falta.config(text="Falta: R$ {:.2f}".format(falta))
        self._tree_pag.delete(*self._tree_pag.get_children())
        FORMAS = {"DINHEIRO":"Dinheiro","DEBITO":"Deb","CREDITO":"Cred","PIX":"Pix","VR":"VR","VA":"VA","OUTROS":"Outros"}
        for pg in pagtos:
            self._tree_pag.insert("", "end", values=(FORMAS.get(pg["forma"],pg["forma"]), "R$ {:.2f}".format(float(pg["valor"])), pg["id"]))

    def _finalizar(self):
        from models.venda import Venda
        try:
            Venda.finalizar(self.venda_id)
        except ValueError as e:
            messagebox.showwarning("Atencao", str(e)); return
        from services.cupom import gerar_cupom_pdf
        from core.database import DatabaseManager
        db = DatabaseManager.empresa()
        empresa = db.fetchone("SELECT * FROM empresa LIMIT 1") or {}
        venda = Venda.buscar_por_id(self.venda_id)
        try:
            path = gerar_cupom_pdf(venda, Venda.itens(self.venda_id), Venda.pagamentos(self.venda_id), empresa)
            import subprocess, sys
            if sys.platform == "win32": subprocess.Popen(["start","",path], shell=True)
            elif sys.platform == "darwin": subprocess.Popen(["open", path])
            else: subprocess.Popen(["xdg-open", path])
        except Exception: pass
        messagebox.showinfo("Venda finalizada", "Venda #{} concluida!".format(venda["numero"]))
        self._criar_venda()
        self._atualizar_tela()
        self._busca_entry.focus()

    def _cancelar(self):
        if not messagebox.askyesno("Cancelar", "Cancelar a venda atual?"): return
        from models.venda import Venda
        Venda.cancelar(self.venda_id, motivo="Cancelado pelo operador")
        self._criar_venda()
        self._atualizar_tela()

    def _fechar(self):
        from models.venda import Venda
        venda = Venda.buscar_por_id(self.venda_id)
        if venda and not Venda.itens(self.venda_id):
            Venda.cancelar(self.venda_id, "Fechado sem itens")
        self.destroy()