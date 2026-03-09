"""View de pedido/comanda - adicionar itens, imprimir cozinha, fechar."""
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from config import THEME, FONT
from core.session import Session

class PedidoView(tk.Toplevel):
    def __init__(self, master, mesa: dict, pedido: dict, on_close=None):
        super().__init__(master)
        self.mesa    = mesa
        self.pedido  = pedido
        self.on_close = on_close
        self.title("Mesa {} — Pedido #{}".format(mesa["nome"], pedido["numero"]))
        self.protocol("WM_DELETE_WINDOW", self._fechar)
        self._build()
        self._atualizar()
        from assets import Assets
        Assets.setup_toplevel(self, 900, 650)

    def _build(self):
        self.configure(bg=THEME["bg"])
        esq = tk.Frame(self, bg=THEME["bg"]); esq.pack(side="left", fill="both", expand=True, padx=8, pady=8)
        dir_ = tk.Frame(self, bg=THEME["bg_card"], width=280); dir_.pack(side="right", fill="y", padx=8, pady=8); dir_.pack_propagate(False)
        self._build_busca(esq)
        self._build_itens(esq)
        self._build_acoes(dir_)

    def _build_busca(self, pai):
        tk.Label(pai, text="Adicionar item:", bg=THEME["bg"], font=FONT["bold"], fg=THEME["fg"]).pack(anchor="w")
        row = tk.Frame(pai, bg=THEME["bg"]); row.pack(fill="x", pady=(0,4))
        self._busca_var = tk.StringVar()
        e = tk.Entry(row, textvariable=self._busca_var, font=FONT["md"], relief="solid", bd=1)
        e.pack(side="left", fill="x", expand=True, ipady=5)
        e.bind("<Return>", lambda ev: self._buscar())
        tk.Button(row, text="Buscar", command=self._buscar, bg=THEME["primary"], fg="white", font=FONT["sm"], relief="flat", padx=8).pack(side="left", padx=4)
        self._lista = tk.Listbox(pai, height=4, font=FONT["sm"], selectbackground=THEME["primary"])
        self._lista.pack(fill="x")
        self._lista.bind("<Double-Button-1>", lambda e: self._add_selecionado())
        self._prods = []
        self._saldos = []

    def _buscar(self):
        from models.produto import Produto
        from models.estoque import Estoque
        self._prods = Produto.listar(busca=self._busca_var.get().strip())[:15]
        self._saldos = [Estoque.saldo_total_produto(p["id"]) for p in self._prods]
        self._lista.delete(0, "end")
        for i, p in enumerate(self._prods):
            saldo = self._saldos[i]
            label = "  [{}]  {:<28s}  R$ {:>7.2f}   Estoque: {:g}".format(
                p.get("codigo", ""), p.get("nome", "")[:28],
                float(p.get("preco_venda", 0)), saldo)
            self._lista.insert("end", label)
            if saldo <= 0:
                self._lista.itemconfig(i, fg="#f5365c")
        if len(self._prods) == 1: self._add_selecionado()
        elif self._prods: self._lista.selection_set(0); self._lista.focus()

    def _add_selecionado(self):
        idx = self._lista.curselection()
        if not idx: return
        prod = self._prods[idx[0]]
        saldo = self._saldos[idx[0]] if idx[0] < len(self._saldos) else 0.0
        qtd = simpledialog.askfloat(
            "Quantidade",
            "Quantidade:  (estoque: {:g})".format(saldo),
            initialvalue=1, minvalue=0.001)
        if not qtd: return
        if qtd > saldo:
            messagebox.showwarning(
                "Estoque insuficiente",
                "Produto '{}': saldo disponível {:g}, solicitado {:g}.".format(
                    prod.get("nome", ""), saldo, qtd))
            return
        obs = simpledialog.askstring("Observacao","Obs para cozinha (opcional):") or ""
        from models.mesa import Pedido
        Pedido.adicionar_item(self.pedido["id"], prod, qtd, obs)
        self._busca_var.set(""); self._lista.delete(0,"end"); self._atualizar()

    def _build_itens(self, pai):
        tk.Label(pai, text="Itens do pedido:", bg=THEME["bg"], font=FONT["bold"], fg=THEME["fg"]).pack(anchor="w", pady=(8,0))
        cols = ("nome","qtd","preco","subtotal","obs","status")
        self._tree = ttk.Treeview(pai, columns=cols, show="headings", height=14)
        for c,l,w in [("nome","Produto",220),("qtd","Qtd",55),("preco","Preco",75),("subtotal","Total",80),("obs","Obs",120),("status","Status",80)]:
            self._tree.heading(c,text=l); self._tree.column(c,width=w,anchor="w" if c in ("nome","obs") else "e")
        self._tree.pack(fill="both",expand=True)
        fr = tk.Frame(pai,bg=THEME["bg"]); fr.pack(fill="x",pady=4)
        tk.Button(fr,text="Remover",command=self._remover,bg=THEME["danger"],fg="white",font=FONT["sm"],relief="flat",padx=8).pack(side="left")
        tk.Button(fr,text="Alterar qtd",command=self._alt_qtd,bg=THEME["warning"],fg="white",font=FONT["sm"],relief="flat",padx=8).pack(side="left",padx=4)

    def _build_acoes(self, pai):
        tk.Label(pai, text="Pedido #{}".format(self.pedido["numero"]), bg=THEME["bg_card"], font=FONT["bold"], fg=THEME["fg"]).pack(pady=(12,4))
        tk.Label(pai, text="Mesa: {}".format(self.mesa["nome"]), bg=THEME["bg_card"], font=FONT["md"], fg=THEME["fg"]).pack()
        garcom = self.pedido.get("garcom_nome", "") or ""
        if garcom:
            tk.Label(pai, text="Garçom: {}".format(garcom), bg=THEME["bg_card"], font=FONT["sm"], fg=THEME["secondary"]).pack()
        self._lbl_total = tk.Label(pai, text="Total: R$ 0,00", bg=THEME["bg_card"], font=FONT["xl_bold"], fg=THEME["primary"])
        self._lbl_total.pack(pady=8)
        tk.Button(pai, text="Imprimir cozinha", command=self._imprimir_cozinha, bg=THEME["warning"], fg="white", font=FONT["sm"], relief="flat").pack(fill="x", padx=10, pady=4)
        tk.Button(pai, text="Imprimir conta", command=self._imprimir_conta, bg=THEME["secondary"], fg="white", font=FONT["sm"], relief="flat").pack(fill="x", padx=10, pady=2)
        tk.Button(pai, text="Desconto no pedido", command=self._desconto, bg=THEME["secondary"], fg="white", font=FONT["sm"], relief="flat").pack(fill="x", padx=10, pady=2)
        tk.Button(pai, text="Dividir conta", command=self._dividir, bg=THEME["secondary"], fg="white", font=FONT["sm"], relief="flat").pack(fill="x", padx=10, pady=2)
        tk.Button(pai, text="FECHAR E PAGAR", command=self._fechar_pedido, bg=THEME["success"], fg="white", font=FONT["bold"], relief="flat", pady=8).pack(fill="x", padx=10, pady=(12,4))
        tk.Button(pai, text="Cancelar pedido", command=self._cancelar, bg=THEME["danger"], fg="white", font=FONT["sm"], relief="flat").pack(fill="x", padx=10, pady=2)

    def _atualizar(self):
        from models.mesa import Pedido
        itens = Pedido.itens(self.pedido["id"])
        ped   = Pedido.buscar_por_id(self.pedido["id"]) or {}
        self._tree.delete(*self._tree.get_children())
        for it in itens:
            tag = "novo" if not it["impresso"] else ""
            self._tree.insert("","end", tags=(tag,), values=(it["produto_nome"],"{:.3f}".format(float(it["quantidade"])),"R$ {:.2f}".format(float(it["preco_unitario"])),"R$ {:.2f}".format(float(it["subtotal"])),it.get("obs",""),it["status"]))
        self._tree.tag_configure("novo", background="#fffbe6")
        self._lbl_total.config(text="Total: R$ {:.2f}".format(float(ped.get("total",0))))

    def _remover(self):
        sel = self._tree.selection()
        if not sel: return
        vals = self._tree.item(sel[0])["values"]
        from core.database import DatabaseManager
        db = DatabaseManager.empresa()
        r = db.fetchone("SELECT id FROM pedido_itens WHERE pedido_id=? AND produto_nome=? LIMIT 1",(self.pedido["id"],vals[0]))
        if r:
            from models.mesa import Pedido; Pedido.remover_item(r["id"]); self._atualizar()

    def _alt_qtd(self):
        sel = self._tree.selection()
        if not sel: return
        nova = simpledialog.askfloat("Qtd","Nova quantidade:",minvalue=0.001)
        if not nova: return
        vals = self._tree.item(sel[0])["values"]
        from core.database import DatabaseManager
        db = DatabaseManager.empresa()
        r = db.fetchone("SELECT id FROM pedido_itens WHERE pedido_id=? AND produto_nome=? LIMIT 1",(self.pedido["id"],vals[0]))
        if r:
            from models.mesa import Pedido; Pedido.alterar_quantidade(r["id"],nova); self._atualizar()

    def _imprimir_cozinha(self):
        from models.mesa import Pedido, Mesa
        novos = Pedido.itens_novos(self.pedido["id"])
        if not novos: messagebox.showinfo("Cozinha","Nenhum item novo para imprimir."); return
        from services.cupom import gerar_comanda_cozinha
        import subprocess, sys
        path = gerar_comanda_cozinha(self.pedido, novos, self.mesa)
        if sys.platform=="win32": subprocess.Popen(["start","",path],shell=True)
        elif sys.platform=="darwin": subprocess.Popen(["open",path])
        else: subprocess.Popen(["xdg-open",path])
        Pedido.marcar_impresso(self.pedido["id"])
        self._atualizar()

    def _imprimir_conta(self):
        from models.mesa import Pedido
        itens = Pedido.itens(self.pedido["id"])
        if not itens:
            messagebox.showinfo("Conta", "Pedido sem itens para imprimir.")
            return
        ped = Pedido.buscar_por_id(self.pedido["id"]) or self.pedido
        try:
            from core.database import DatabaseManager
            from core.session import Session
            empresa = DatabaseManager.master().fetchone(
                "SELECT * FROM empresas WHERE id=?", (Session.empresa()["id"],)) or {}
        except Exception:
            empresa = {}
        try:
            from services.cupom import gerar_conta_mesa
            import subprocess, sys
            path = gerar_conta_mesa(ped, itens, self.mesa, empresa)
            if sys.platform == "win32": subprocess.Popen(["start", "", path], shell=True)
            elif sys.platform == "darwin": subprocess.Popen(["open", path])
            else: subprocess.Popen(["xdg-open", path])
        except Exception as e:
            messagebox.showerror("Erro ao imprimir conta", str(e))

    def _desconto(self):
        val = simpledialog.askfloat("Desconto","Desconto em R$:",minvalue=0)
        if val:
            from models.mesa import Pedido; Pedido.aplicar_desconto(self.pedido["id"],val); self._atualizar()

    def _dividir(self):
        ped = __import__("models.mesa",fromlist=["Pedido"]).Pedido.buscar_por_id(self.pedido["id"]) or {}
        pessoas = simpledialog.askinteger("Dividir","Dividir entre quantas pessoas?",initialvalue=int(ped.get("pessoas",2)),minvalue=2,maxvalue=20)
        if not pessoas: return
        from models.mesa import Pedido
        divisao = Pedido.calcular_divisao(self.pedido["id"],pessoas)
        msg = "\n".join(["Pessoa {}: R$ {:.2f}".format(d["pessoa"],d["total"]) for d in divisao])
        messagebox.showinfo("Divisao de conta",msg)

    def _fechar_pedido(self):
        from models.mesa import Pedido
        itens = Pedido.itens(self.pedido["id"])
        if not itens: messagebox.showwarning("Aviso","Pedido sem itens."); return
        Pedido.fechar(self.pedido["id"])
        from views.pdv.caixa_view import selecionar_caixa
        caixa = selecionar_caixa(self)
        if not caixa:
            # Desfaz o fechar se o operador cancelou a seleção de caixa
            from core.database import DatabaseManager
            DatabaseManager.empresa().execute(
                "UPDATE pedidos SET status='ABERTO', fechado_em=NULL WHERE id=?",
                (self.pedido["id"],))
            return
        sess = Session.usuario()
        venda_id = Pedido.converter_para_venda(
            self.pedido["id"], caixa["id"], sess.get("id"), sess.get("nome", ""))
        Pedido.pagar(self.pedido["id"])
        master = self.master
        self.destroy()
        if self.on_close: self.on_close()
        # Abre o PDV diretamente com a venda já montada para pagamento
        from views.pdv.pdv_view import PDVView
        PDVView(master, caixa, venda_id=venda_id)

    def _cancelar(self):
        if not messagebox.askyesno("Cancelar","Cancelar o pedido desta mesa?"): return
        from models.mesa import Pedido; Pedido.cancelar(self.pedido["id"],"Cancelado pelo operador")
        self.destroy()
        if self.on_close: self.on_close()

    def _fechar(self):
        self.destroy()
        if self.on_close: self.on_close()