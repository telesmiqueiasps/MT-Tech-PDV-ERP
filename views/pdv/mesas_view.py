"""Mapa visual de mesas para restaurante/lanchonete."""
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from config import THEME, FONT
from core.session import Session


def _pedir_pessoas(master) -> int | None:
    """Diálogo customizado para número de pessoas (com ícone e foco corretos)."""
    resultado = [None]
    win = tk.Toplevel(master)
    win.title("Abrir mesa")
    win.resizable(False, False)
    tk.Label(win, text="Quantas pessoas?", font=FONT["bold"]).pack(pady=(18, 8))
    var = tk.StringVar(value="1")
    sp = tk.Spinbox(win, from_=1, to=20, textvariable=var, width=6, font=FONT["md"], justify="center")
    sp.pack()
    def ok():
        try: resultado[0] = max(1, int(var.get()))
        except ValueError: resultado[0] = 1
        win.destroy()
    sp.bind("<Return>", lambda _: ok())
    tk.Button(win, text="OK", command=ok, bg=THEME["primary"], fg="white",
              font=FONT["bold"], relief="flat", padx=20).pack(pady=14)
    from assets import Assets; Assets.setup_toplevel(win, 220, 155)
    win.grab_set()
    win.wait_window()
    return resultado[0]


class MesasView(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg=THEME["bg"])
        self._build()
        self.atualizar()

    def _build(self):
        top = tk.Frame(self, bg=THEME["bg"]); top.pack(fill="x", padx=16, pady=8)
        tk.Label(top, text="Mapa de Mesas", font=FONT["title"], bg=THEME["bg"], fg=THEME["fg"]).pack(side="left")
        tk.Button(top, text="Atualizar", command=self.atualizar, bg=THEME["secondary"], fg="white", font=FONT["sm"], relief="flat", padx=10).pack(side="right")
        tk.Button(top, text="Gerenciar mesas", command=self._gerenciar_mesas, bg=THEME["primary"], fg="white", font=FONT["sm"], relief="flat", padx=10).pack(side="right", padx=4)
        # Legenda
        leg = tk.Frame(self, bg=THEME["bg"]); leg.pack(fill="x", padx=16, pady=(0, 8))
        for status, cor in [("Livre", "#2dce89"), ("Ocupada", "#f5365c"), ("Reservada", "#f4b942"), ("Inativa", "#aaa")]:
            tk.Label(leg, text="  ", bg=cor, width=2).pack(side="left")
            tk.Label(leg, text=status, bg=THEME["bg"], fg=THEME["fg"], font=FONT["sm"]).pack(side="left", padx=(0, 12))
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
                         bg=THEME["bg"], fg=THEME["fg"]).pack(anchor="w", pady=(8, 2))
                linha = tk.Frame(self._canvas_frame, bg=THEME["bg"]); linha.pack(anchor="w")
            cor = {"LIVRE": "#2dce89", "OCUPADA": "#f5365c", "RESERVADA": "#f4b942", "INATIVA": "#aaa"}.get(mesa["status"], "#aaa")
            self._criar_botao_mesa(linha, mesa, cor)

    def _criar_botao_mesa(self, pai, mesa, cor):
        fr = tk.Frame(pai, bg=cor, bd=2, relief="raised", width=110, height=95)
        fr.pack(side="left", padx=6, pady=6); fr.pack_propagate(False)
        pedido = None
        if mesa["status"] == "OCUPADA":
            from models.mesa import Mesa
            pedido = Mesa.pedido_aberto(mesa["id"])
        tk.Label(fr, text=mesa["nome"], bg=cor, fg="white", font=FONT["bold"]).pack(pady=(8, 0))
        tk.Label(fr, text=mesa["status"], bg=cor, fg="white", font=FONT["sm"]).pack()
        if pedido:
            from core.database import DatabaseManager
            tot = DatabaseManager.empresa().fetchone(
                "SELECT COALESCE(SUM(subtotal),0) AS t FROM pedido_itens WHERE pedido_id=?", (pedido["id"],))
            tk.Label(fr, text="R$ {:.2f}".format(float(tot["t"])), bg=cor, fg="white", font=FONT["sm"]).pack()
        if mesa["status"] == "RESERVADA" and mesa.get("reserva_obs"):
            tk.Label(fr, text=mesa["reserva_obs"][:16], bg=cor, fg="white", font=FONT["sm"], wraplength=100).pack()
        fr.bind("<Button-1>", lambda e, m=mesa: self._clicar_mesa(m))
        for child in fr.winfo_children(): child.bind("<Button-1>", lambda e, m=mesa: self._clicar_mesa(m))

    def _clicar_mesa(self, mesa):
        if mesa["status"] == "INATIVA": return
        if mesa["status"] == "OCUPADA":
            self._gerenciar_pedido(mesa)
        elif mesa["status"] == "LIVRE":
            self._menu_livre(mesa)
        elif mesa["status"] == "RESERVADA":
            self._menu_reservada(mesa)

    def _menu_livre(self, mesa):
        win = tk.Toplevel(self); win.title(mesa["nome"]); win.resizable(False, False)
        tk.Label(win, text=mesa["nome"], font=FONT["bold"]).pack(pady=(16, 4))
        cap = mesa.get("capacidade") or ""
        tk.Label(win, text="Capacidade: {} pessoas".format(cap) if cap else "Mesa livre", font=FONT["sm"]).pack()
        btn_fr = tk.Frame(win); btn_fr.pack(pady=14)
        def abrir(): win.destroy(); self._abrir_pedido(mesa)
        def reservar(): win.destroy(); self._reservar_mesa(mesa)
        tk.Button(btn_fr, text="Abrir pedido", command=abrir, bg=THEME["success"], fg="white", font=FONT["sm"], relief="flat", padx=10).pack(side="left", padx=4)
        tk.Button(btn_fr, text="Reservar", command=reservar, bg=THEME["warning"], fg="white", font=FONT["sm"], relief="flat", padx=10).pack(side="left", padx=4)
        tk.Button(win, text="Cancelar", command=win.destroy, bg=THEME["secondary"], fg="white", font=FONT["sm"], relief="flat", padx=10).pack()
        from assets import Assets; Assets.setup_toplevel(win, 260, 155)
        win.grab_set()

    def _menu_reservada(self, mesa):
        obs = mesa.get("reserva_obs", "") or ""
        win = tk.Toplevel(self); win.title(mesa["nome"]); win.resizable(False, False)
        tk.Label(win, text=mesa["nome"], font=FONT["bold"]).pack(pady=(16, 2))
        tk.Label(win, text="Reservada" + (" — {}".format(obs) if obs else ""), font=FONT["sm"], fg="#c8951f").pack()
        btn_fr = tk.Frame(win); btn_fr.pack(pady=14)
        def abrir():
            from models.mesa import Mesa
            Mesa.liberar(mesa["id"])
            win.destroy()
            m = Mesa.buscar_por_id(mesa["id"])
            self._abrir_pedido(m)
        def liberar():
            from models.mesa import Mesa
            if messagebox.askyesno("Liberar", "Liberar a reserva de '{}'?".format(mesa["nome"])):
                Mesa.liberar(mesa["id"]); win.destroy(); self.atualizar()
        tk.Button(btn_fr, text="Abrir pedido", command=abrir, bg=THEME["success"], fg="white", font=FONT["sm"], relief="flat", padx=10).pack(side="left", padx=4)
        tk.Button(btn_fr, text="Liberar reserva", command=liberar, bg=THEME["danger"], fg="white", font=FONT["sm"], relief="flat", padx=10).pack(side="left", padx=4)
        tk.Button(win, text="Cancelar", command=win.destroy, bg=THEME["secondary"], fg="white", font=FONT["sm"], relief="flat", padx=10).pack()
        from assets import Assets; Assets.setup_toplevel(win, 290, 165)
        win.grab_set()

    def _reservar_mesa(self, mesa):
        obs = simpledialog.askstring("Reservar", "Nome / observação da reserva (opcional):") or ""
        from models.mesa import Mesa
        Mesa.reservar(mesa["id"], obs)
        self.atualizar()

    def _abrir_pedido(self, mesa):
        from models.mesa import Mesa, Pedido
        sess = Session.usuario()
        pessoas = _pedir_pessoas(self)
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

    def _gerenciar_mesas(self):
        _GerenciarMesasDialog(self, on_close=self.atualizar)


class _GerenciarMesasDialog(tk.Toplevel):
    def __init__(self, master, on_close=None):
        super().__init__(master)
        self.title("Gerenciar Mesas")
        self._on_close = on_close
        self._mesas = []
        self._build()
        self._carregar()
        self.protocol("WM_DELETE_WINDOW", self._fechar)
        from assets import Assets; Assets.setup_toplevel(self, 620, 440)
        self.grab_set()

    def _build(self):
        tk.Label(self, text="Gerenciar Mesas", font=FONT["bold"]).pack(anchor="w", padx=12, pady=(10, 4))
        cols = ("nome", "setor", "capacidade", "status", "ativo")
        self._tree = ttk.Treeview(self, columns=cols, show="headings", height=14)
        for c, l, w in [("nome", "Nome", 130), ("setor", "Setor", 110), ("capacidade", "Cap.", 55),
                         ("status", "Status", 100), ("ativo", "Ativo", 55)]:
            self._tree.heading(c, text=l); self._tree.column(c, width=w, anchor="w")
        self._tree.pack(fill="both", expand=True, padx=12)
        self._tree.tag_configure("inativo", foreground="#aaa")
        bar = tk.Frame(self); bar.pack(fill="x", padx=12, pady=8)
        for txt, cor, cmd in [
            ("Nova mesa", THEME["primary"], self._nova),
            ("Editar", THEME["secondary"], self._editar),
            ("Ativar / Desativar", THEME["warning"], self._toggle_ativo),
            ("Excluir", THEME["danger"], self._excluir),
        ]:
            tk.Button(bar, text=txt, command=cmd, bg=cor, fg="white", font=FONT["sm"], relief="flat", padx=10).pack(side="left", padx=4)
        tk.Button(bar, text="Fechar", command=self._fechar, bg=THEME["secondary"], fg="white", font=FONT["sm"], relief="flat", padx=10).pack(side="right")

    def _carregar(self):
        from models.mesa import Mesa
        self._mesas = Mesa.listar(so_ativas=False)
        self._tree.delete(*self._tree.get_children())
        for m in self._mesas:
            ativo = "Sim" if m.get("ativo", 1) else "Não"
            tag = () if m.get("ativo", 1) else ("inativo",)
            self._tree.insert("", "end", tags=tag, values=(
                m.get("nome", ""), m.get("setor", ""), m.get("capacidade", ""),
                m.get("status", ""), ativo))

    def _selecionada(self):
        sel = self._tree.selection()
        if not sel:
            messagebox.showwarning("Aviso", "Selecione uma mesa."); return None
        idx = self._tree.index(sel[0])
        return self._mesas[idx]

    def _nova(self):
        _FormMesaDialog(self, on_save=self._carregar)

    def _editar(self):
        mesa = self._selecionada()
        if mesa: _FormMesaDialog(self, mesa=mesa, on_save=self._carregar)

    def _toggle_ativo(self):
        mesa = self._selecionada()
        if not mesa: return
        from models.mesa import Mesa
        if mesa.get("ativo", 1):
            if mesa["status"] == "OCUPADA":
                messagebox.showwarning("Aviso", "Não é possível desativar uma mesa com pedido aberto."); return
            if messagebox.askyesno("Desativar", "Desativar '{}'?".format(mesa["nome"])):
                Mesa.inativar(mesa["id"]); self._carregar()
        else:
            Mesa.ativar(mesa["id"]); self._carregar()

    def _excluir(self):
        mesa = self._selecionada()
        if not mesa: return
        if mesa["status"] == "OCUPADA":
            messagebox.showwarning("Aviso", "Não é possível excluir uma mesa com pedido aberto."); return
        if messagebox.askyesno("Excluir", "Excluir '{}'? Esta ação não pode ser desfeita.".format(mesa["nome"])):
            from models.mesa import Mesa
            Mesa.deletar(mesa["id"]); self._carregar()

    def _fechar(self):
        if self._on_close: self._on_close()
        self.destroy()


class _FormMesaDialog(tk.Toplevel):
    def __init__(self, master, mesa=None, on_save=None):
        super().__init__(master)
        self._mesa = mesa
        self._on_save = on_save
        self.title("Editar mesa" if mesa else "Nova mesa")
        self.resizable(False, False)
        self._build()
        from assets import Assets; Assets.setup_toplevel(self, 320, 240)
        self.grab_set()

    def _build(self):
        pad = {"padx": 16, "pady": 3}
        tk.Label(self, text="Nome:", font=FONT["sm"]).pack(anchor="w", **pad)
        self._nome = tk.Entry(self, font=FONT["md"]); self._nome.pack(fill="x", **pad)

        tk.Label(self, text="Setor:", font=FONT["sm"]).pack(anchor="w", **pad)
        self._setor = tk.Entry(self, font=FONT["md"]); self._setor.pack(fill="x", **pad)

        tk.Label(self, text="Capacidade (pessoas):", font=FONT["sm"]).pack(anchor="w", **pad)
        self._cap = tk.Entry(self, font=FONT["md"]); self._cap.pack(fill="x", **pad)

        if self._mesa:
            self._nome.insert(0, self._mesa.get("nome", ""))
            self._setor.insert(0, self._mesa.get("setor", ""))
            self._cap.insert(0, str(self._mesa.get("capacidade", 4)))

        bar = tk.Frame(self); bar.pack(pady=14)
        tk.Button(bar, text="Salvar", command=self._salvar, bg=THEME["primary"], fg="white", font=FONT["sm"], relief="flat", padx=14).pack(side="left", padx=4)
        tk.Button(bar, text="Cancelar", command=self.destroy, bg=THEME["secondary"], fg="white", font=FONT["sm"], relief="flat", padx=14).pack(side="left", padx=4)

    def _salvar(self):
        nome = self._nome.get().strip()
        setor = self._setor.get().strip() or "Salão"
        try: cap = int(self._cap.get())
        except ValueError: cap = 4
        if not nome:
            messagebox.showwarning("Aviso", "Informe o nome da mesa."); return
        from models.mesa import Mesa
        if self._mesa:
            Mesa.editar(self._mesa["id"], self._mesa["numero"], nome, cap, setor)
        else:
            try:
                Mesa.criar(Mesa.proximo_numero(), nome, cap, setor)
            except Exception as e:
                messagebox.showerror("Erro", "Erro ao criar mesa: {}".format(e)); return
        if self._on_save: self._on_save()
        self.destroy()
