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
    win.geometry("300x200")
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
            self._tree.insert("","end",tags=(tag,),values=(c["numero"],c["nome"] or "",c["operador_nome"] or "",c["status"],"R$ {:.2f}".format(float(c["valor_abertura"] or 0)),"R$ {:.2f}".format(saldo)))

    def _caixa_selecionado(self):
        sel = self._tree.selection()
        if not sel: messagebox.showwarning("Aviso","Selecione um caixa."); return None
        num = self._tree.item(sel[0])["values"][0]
        from models.caixa import Caixa
        for c in Caixa.listar():
            if c["numero"] == num: return c
        return None

    def _abrir(self):
        from models.caixa import Caixa
        sess = Session.usuario()
        if Caixa.aberto_do_operador(sess.get("id")):
            messagebox.showwarning("Aviso","Voce ja tem um caixa aberto."); return
        num = simpledialog.askinteger("Abrir caixa","Numero do caixa:",minvalue=1)
        if not num: return
        nome = simpledialog.askstring("Abrir caixa","Nome do caixa:",initialvalue="Caixa {}".format(num))
        val = simpledialog.askfloat("Abertura","Valor de abertura (fundo de troco):",initialvalue=0,minvalue=0)
        if val is None: return
        Caixa.abrir(num, nome or "", sess.get("id"), sess.get("nome", ""), val)
        self.atualizar()

    def _fechar(self):
        caixa = self._caixa_selecionado()
        if not caixa or caixa["status"]!="ABERTO": messagebox.showwarning("Aviso","Selecione um caixa aberto."); return
        from models.caixa import Caixa
        saldo = Caixa.saldo_atual(caixa["id"])
        if not messagebox.askyesno("Fechar caixa","Saldo sistema: R$ {:.2f}\nFechar o caixa?".format(saldo)): return
        val = simpledialog.askfloat("Fechamento","Valor contado em caixa:",initialvalue=round(saldo,2),minvalue=0)
        if val is None: return
        sess = Session.usuario()
        obs = simpledialog.askstring("Observacao","Observacao (opcional):") or ""
        Caixa.fechar(caixa["id"],val,sess.get("id"),sess.get("nome", ""),obs)
        self.atualizar(); self._relatorio_por_id(caixa["id"])

    def _sangria(self):
        caixa = self._caixa_selecionado()
        if not caixa or caixa["status"]!="ABERTO": return
        val = simpledialog.askfloat("Sangria","Valor da sangria:",minvalue=0.01)
        if not val: return
        desc = simpledialog.askstring("Sangria","Motivo:") or "Sangria"
        sess = Session.usuario()
        from models.caixa import Caixa; Caixa.sangria(caixa["id"],val,desc,sess.get("id"),sess.get("nome", ""))
        self.atualizar()

    def _suprimento(self):
        caixa = self._caixa_selecionado()
        if not caixa or caixa["status"]!="ABERTO": return
        val = simpledialog.askfloat("Suprimento","Valor do suprimento:",minvalue=0.01)
        if not val: return
        desc = simpledialog.askstring("Suprimento","Descricao:") or "Suprimento"
        sess = Session.usuario()
        from models.caixa import Caixa; Caixa.suprimento(caixa["id"],val,desc,sess.get("id"),sess.get("nome", ""))
        self.atualizar()

    def _relatorio(self):
        caixa = self._caixa_selecionado()
        if not caixa: return
        self._relatorio_por_id(caixa["id"])

    def _relatorio_por_id(self, caixa_id):
        from models.caixa import Caixa
        r = Caixa.resumo_fechamento(caixa_id)
        win = tk.Toplevel(self); win.title("Relatorio de Caixa"); win.geometry("420x500"); win.grab_set()
        tk.Label(win, text="RELATORIO DE CAIXA", font=FONT["title"]).pack(pady=10)
        c = r["caixa"]
        tk.Label(win, text="Caixa {} — {}".format(c.get("numero",""), c.get("nome","")), font=FONT["bold"]).pack()
        tk.Label(win, text="Operador: {}".format(c.get("operador_nome",""))).pack()
        ttk.Separator(win, orient="horizontal").pack(fill="x", padx=16, pady=8)
        tv = r["total_vendas"]
        tk.Label(win, text="Vendas: {}  |  Total: R$ {:.2f}".format(tv["qtd"],float(tv["total"])), font=FONT["md"]).pack()
        tk.Label(win, text="Canceladas: {}".format(r["qtd_canceladas"])).pack()
        tk.Label(win, text="Descontos: R$ {:.2f}".format(r["total_descontos"])).pack()
        ttk.Separator(win, orient="horizontal").pack(fill="x", padx=16, pady=8)
        tk.Label(win, text="Por forma de pagamento:", font=FONT["bold"]).pack()
        for pf in r["por_forma"]:
            tk.Label(win, text="  {:<20s} R$ {:>9.2f}  ({} vendas)".format(pf["forma"],float(pf["total"]),pf["qtd"])).pack(anchor="w", padx=24)
        ttk.Separator(win, orient="horizontal").pack(fill="x", padx=16, pady=8)
        for mv in r["movimentos"]:
            tk.Label(win, text="{}: R$ {:.2f}".format(mv["tipo"],abs(float(mv["total"])))).pack()
        tk.Label(win, text="SALDO SISTEMA: R$ {:.2f}".format(r["saldo_sistema"]), font=FONT["xl_bold"]).pack(pady=8)
        tk.Button(win, text="Fechar", command=win.destroy, bg=THEME["primary"], fg="white", font=FONT["bold"], relief="flat", padx=20).pack(pady=8)