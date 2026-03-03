"""Mapa visual de mesas para restaurante/lanchonete."""
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from config import THEME, FONT
from core.session import Session

class MesasView(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg=THEME["bg"])
        self._build()
        self.atualizar()

    def _build(self):
        top = tk.Frame(self, bg=THEME["bg"]); top.pack(fill="x", padx=16, pady=8)
        tk.Label(top, text="Mapa de Mesas", font=FONT["title"], bg=THEME["bg"], fg=THEME["fg"]).pack(side="left")
        tk.Button(top, text="Atualizar", command=self.atualizar, bg=THEME["secondary"], fg="white", font=FONT["sm"], relief="flat", padx=10).pack(side="right")
        tk.Button(top, text="Nova mesa", command=self._nova_mesa, bg=THEME["primary"], fg="white", font=FONT["sm"], relief="flat", padx=10).pack(side="right", padx=4)
        # Legenda
        leg = tk.Frame(self, bg=THEME["bg"]); leg.pack(fill="x", padx=16, pady=(0,8))
        for status, cor in [("Livre","#2dce89"),("Ocupada","#f5365c"),("Reservada","#f4b942"),("Inativa","#aaa")]:
            tk.Label(leg, text="  ", bg=cor, width=2).pack(side="left")
            tk.Label(leg, text=status, bg=THEME["bg"], fg=THEME["fg"], font=FONT["sm"]).pack(side="left", padx=(0,12))
        self._canvas_frame = tk.Frame(self, bg=THEME["bg"]); self._canvas_frame.pack(fill="both", expand=True, padx=16)

    def atualizar(self):
        for w in self._canvas_frame.winfo_children(): w.destroy()
        from models.mesa import Mesa
        mesas = Mesa.listar()
        setor_atual = None
        linha = None
        for mesa in mesas:
            if mesa["setor"] != setor_atual:
                setor_atual = mesa["setor"]
                tk.Label(self._canvas_frame, text=setor_atual, font=FONT["bold"],
                         bg=THEME["bg"], fg=THEME["fg"]).pack(anchor="w", pady=(8,2))
                linha = tk.Frame(self._canvas_frame, bg=THEME["bg"]); linha.pack(anchor="w")
            cor = {"LIVRE":"#2dce89","OCUPADA":"#f5365c","RESERVADA":"#f4b942","INATIVA":"#aaa"}.get(mesa["status"],"#aaa")
            self._criar_botao_mesa(linha, mesa, cor)

    def _criar_botao_mesa(self, pai, mesa, cor):
        fr = tk.Frame(pai, bg=cor, bd=2, relief="raised", width=110, height=80)
        fr.pack(side="left", padx=6, pady=6); fr.pack_propagate(False)
        pedido = None
        if mesa["status"] == "OCUPADA":
            from models.mesa import Mesa
            pedido = Mesa.pedido_aberto(mesa["id"])
        tk.Label(fr, text=mesa["nome"], bg=cor, fg="white", font=FONT["bold"]).pack(pady=(8,0))
        tk.Label(fr, text=mesa["status"], bg=cor, fg="white", font=FONT["sm"]).pack()
        if pedido:
            from core.database import DatabaseManager
            tot = DatabaseManager.empresa().fetchone("SELECT COALESCE(SUM(subtotal),0) AS t FROM pedido_itens WHERE pedido_id=?", (pedido["id"],))
            tk.Label(fr, text="R$ {:.2f}".format(float(tot["t"])), bg=cor, fg="white", font=FONT["sm"]).pack()
        fr.bind("<Button-1>", lambda e, m=mesa: self._clicar_mesa(m))
        for child in fr.winfo_children(): child.bind("<Button-1>", lambda e, m=mesa: self._clicar_mesa(m))

    def _clicar_mesa(self, mesa):
        if mesa["status"] == "INATIVA": return
        if mesa["status"] == "LIVRE":
            self._abrir_pedido(mesa)
        else:
            self._gerenciar_pedido(mesa)

    def _abrir_pedido(self, mesa):
        from models.mesa import Mesa, Pedido
        sess = Session.usuario()
        pessoas = simpledialog.askinteger("Pessoas", "Quantas pessoas?", initialvalue=1, minvalue=1, maxvalue=20)
        if not pessoas: return
        Pedido.abrir(mesa["id"], sess.get("id"), sess.get("nome", ""), pessoas)
        self.atualizar()
        from views.pdv.pedido_view import PedidoView
        ped = Mesa.pedido_aberto(mesa["id"])
        PedidoView(self, mesa, ped, on_close=self.atualizar)

    def _gerenciar_pedido(self, mesa):
        from models.mesa import Mesa
        pedido = Mesa.pedido_aberto(mesa["id"])
        if not pedido:
            messagebox.showinfo("Mesa", "Nenhum pedido aberto nesta mesa."); return
        from views.pdv.pedido_view import PedidoView
        PedidoView(self, mesa, pedido, on_close=self.atualizar)

    def _nova_mesa(self):
        num = simpledialog.askinteger("Nova mesa", "Numero da mesa:")
        if not num: return
        nome = simpledialog.askstring("Nova mesa", "Nome:", initialvalue="Mesa {}".format(num))
        from models.mesa import Mesa
        Mesa.criar(num, nome or "Mesa {}".format(num))
        self.atualizar()