import tkinter as tk
from tkinter import ttk, messagebox
from config import THEME, FONT
from core.session import Session


class AbaAdmins(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg=THEME["bg"])
        self.pack(fill="both", expand=True)
        self._build()
        self._carregar()

    # ── Layout ────────────────────────────────────────────────────

    def _build(self):
        # Toolbar
        bar = tk.Frame(self, bg=THEME["bg"], padx=16, pady=12)
        bar.pack(fill="x")

        tk.Button(bar, text="+ Novo Admin",
                  font=FONT["bold"], bg=THEME["primary"], fg="white",
                  relief="flat", cursor="hand2", padx=14, pady=6,
                  command=self._novo).pack(side="left")

        tk.Button(bar, text="🔑  Alterar Senha",
                  font=FONT["sm"], bg=THEME["bg_card"], fg=THEME["fg"],
                  relief="flat", cursor="hand2", padx=12, pady=6,
                  command=self._alterar_senha).pack(side="left", padx=(8, 0))

        tk.Button(bar, text="✏  Renomear",
                  font=FONT["sm"], bg=THEME["bg_card"], fg=THEME["fg"],
                  relief="flat", cursor="hand2", padx=12, pady=6,
                  command=self._renomear).pack(side="left", padx=(8, 0))

        tk.Button(bar, text="⟳  Atualizar",
                  font=FONT["sm"], bg=THEME["bg_card"], fg=THEME["fg"],
                  relief="flat", cursor="hand2", padx=12, pady=6,
                  command=self._carregar).pack(side="right")

        self._btn_toggle = tk.Button(
            bar, text="Desativar",
            font=FONT["sm"], bg=THEME["danger_light"], fg=THEME["danger"],
            relief="flat", cursor="hand2", padx=12, pady=6,
            command=self._toggle_ativo,
        )
        self._btn_toggle.pack(side="right", padx=(0, 8))

        # Tabela
        outer = tk.Frame(self, bg=THEME["border"])
        outer.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        cols = ("nome", "login", "status", "criado_em")
        self._tree = ttk.Treeview(outer, columns=cols, show="headings",
                                  selectmode="browse")
        vsb = ttk.Scrollbar(outer, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self._tree.pack(fill="both", expand=True)

        self._tree.heading("nome",      text="Nome")
        self._tree.heading("login",     text="Login")
        self._tree.heading("status",    text="Status")
        self._tree.heading("criado_em", text="Criado em")

        self._tree.column("nome",      width=200)
        self._tree.column("login",     width=140)
        self._tree.column("status",    width=90,  anchor="center")
        self._tree.column("criado_em", width=150, anchor="center")

        style = ttk.Style()
        style.configure("Treeview", rowheight=30, font=FONT["sm"],
                        background="white", fieldbackground="white")
        style.configure("Treeview.Heading", font=FONT["bold"])
        style.map("Treeview", background=[("selected", THEME["primary_light"])],
                  foreground=[("selected", THEME["fg"])])

        self._tree.tag_configure("inativo", foreground=THEME["fg_light"])
        self._tree.tag_configure("eu",      foreground=THEME["primary"])

        self._tree.bind("<<TreeviewSelect>>", self._on_select)
        self._tree.bind("<Double-1>",         lambda _: self._alterar_senha())

        # Rodapé
        self._lbl_info = tk.Label(self, text="", font=FONT["sm"],
                                  bg=THEME["bg"], fg=THEME["fg_light"])
        self._lbl_info.pack(pady=(0, 8))

    # ── Dados ─────────────────────────────────────────────────────

    def _carregar(self):
        from models.admin_global import AdminGlobal
        self._admins = AdminGlobal.listar()
        self._tree.delete(*self._tree.get_children())

        eu_login = Session.usuario().get("login", "")
        for a in self._admins:
            status = "Ativo" if a["ativo"] else "Inativo"
            nome   = a["nome"] or "—"
            dt     = (a["criado_em"] or "")[:16].replace("T", " ")
            tag    = "eu" if a["login"] == eu_login else ("inativo" if not a["ativo"] else "")
            self._tree.insert("", "end", iid=str(a["id"]),
                              values=(nome, a["login"], status, dt),
                              tags=(tag,))

        ativos = sum(1 for a in self._admins if a["ativo"])
        total  = len(self._admins)
        self._lbl_info.configure(text=f"{total} administrador(es)  •  {ativos} ativo(s)")
        self._atualizar_botao_toggle()

    def _selecionado(self) -> dict | None:
        sel = self._tree.selection()
        if not sel:
            return None
        admin_id = int(sel[0])
        return next((a for a in self._admins if a["id"] == admin_id), None)

    def _on_select(self, _event=None):
        self._atualizar_botao_toggle()

    def _atualizar_botao_toggle(self):
        admin = self._selecionado()
        if admin and admin["ativo"]:
            self._btn_toggle.configure(
                text="Desativar", bg=THEME["danger_light"], fg=THEME["danger"])
        else:
            self._btn_toggle.configure(
                text="Reativar", bg=THEME["success_light"], fg=THEME["success"])

    # ── Ações ─────────────────────────────────────────────────────

    def _novo(self):
        _DialogNovoAdmin(self, on_salvo=self._carregar)

    def _alterar_senha(self):
        admin = self._selecionado()
        if not admin:
            messagebox.showwarning("Seleção", "Selecione um administrador.", parent=self)
            return
        _DialogAlterarSenha(self, admin, on_salvo=self._carregar)

    def _renomear(self):
        admin = self._selecionado()
        if not admin:
            messagebox.showwarning("Seleção", "Selecione um administrador.", parent=self)
            return
        _DialogRenomear(self, admin, on_salvo=self._carregar)

    def _toggle_ativo(self):
        from models.admin_global import AdminGlobal, AdminGlobalError
        admin = self._selecionado()
        if not admin:
            messagebox.showwarning("Seleção", "Selecione um administrador.", parent=self)
            return

        eu_login = Session.usuario().get("login", "")
        if admin["login"] == eu_login and admin["ativo"]:
            messagebox.showwarning(
                "Operação inválida",
                "Você não pode desativar sua própria conta.",
                parent=self,
            )
            return

        acao = "desativar" if admin["ativo"] else "reativar"
        nome = admin["nome"] or admin["login"]
        if not messagebox.askyesno("Confirmar", f"Deseja {acao} o admin '{nome}'?",
                                   parent=self):
            return
        try:
            if admin["ativo"]:
                AdminGlobal.desativar(admin["id"])
            else:
                AdminGlobal.reativar(admin["id"])
            self._carregar()
        except AdminGlobalError as e:
            messagebox.showerror("Erro", str(e), parent=self)


# ── Diálogo: Novo Admin ───────────────────────────────────────────

class _DialogNovoAdmin(tk.Toplevel):
    def __init__(self, master, on_salvo):
        super().__init__(master)
        self.title("Novo Administrador Global")
        self.configure(bg=THEME["bg"])
        self.resizable(False, False)
        self.grab_set()
        self._on_salvo = on_salvo
        self._build()
        self._centralizar(400, 460)

    def _centralizar(self, w, h):
        self.update_idletasks()
        x = (self.winfo_screenwidth()  - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _build(self):
        pad = tk.Frame(self, bg=THEME["bg"], padx=28, pady=24)
        pad.pack(fill="both", expand=True)

        tk.Label(pad, text="Novo Administrador Global",
                 font=("Segoe UI", 13, "bold"),
                 bg=THEME["bg"], fg=THEME["fg"]).pack(anchor="w", pady=(0, 20))

        self._var_nome  = tk.StringVar()
        self._var_login = tk.StringVar()
        self._var_senha = tk.StringVar()
        self._var_conf  = tk.StringVar()
        self._var_erro  = tk.StringVar()

        for label, var, show in [
            ("Nome de exibição", self._var_nome,  ""),
            ("Login",           self._var_login, ""),
            ("Senha",           self._var_senha, "•"),
            ("Confirmar senha", self._var_conf,  "•"),
        ]:
            tk.Label(pad, text=label, font=FONT["sm"],
                     bg=THEME["bg"], fg=THEME["fg"]).pack(anchor="w")
            tk.Entry(pad, textvariable=var, show=show, font=FONT["md"],
                     relief="flat", bg="white", highlightthickness=1,
                     highlightbackground=THEME["border"],
                     highlightcolor=THEME["primary"]).pack(fill="x", ipady=7, pady=(2, 10))

        tk.Label(pad, textvariable=self._var_erro, font=FONT["sm"],
                 bg=THEME["bg"], fg=THEME["danger"]).pack()

        tk.Button(pad, text="Criar administrador",
                  font=FONT["bold"], bg=THEME["primary"], fg="white",
                  relief="flat", cursor="hand2", pady=9,
                  command=self._salvar).pack(fill="x", pady=(8, 0))

        self.bind("<Return>", lambda _: self._salvar())

    def _salvar(self):
        from models.admin_global import AdminGlobal, AdminGlobalError
        nome  = self._var_nome.get().strip()
        login = self._var_login.get().strip()
        senha = self._var_senha.get()
        conf  = self._var_conf.get()

        if not login:
            self._var_erro.set("O login é obrigatório."); return
        if senha != conf:
            self._var_erro.set("As senhas não coincidem."); return

        try:
            AdminGlobal.criar(login, nome, senha)
            self._on_salvo()
            self.destroy()
        except AdminGlobalError as e:
            self._var_erro.set(str(e))


# ── Diálogo: Alterar Senha ────────────────────────────────────────

class _DialogAlterarSenha(tk.Toplevel):
    def __init__(self, master, admin: dict, on_salvo):
        super().__init__(master)
        self.title("Alterar Senha")
        self.configure(bg=THEME["bg"])
        self.resizable(False, False)
        self.grab_set()
        self._admin    = admin
        self._on_salvo = on_salvo
        self._build()
        self._centralizar(380, 350)

    def _centralizar(self, w, h):
        self.update_idletasks()
        x = (self.winfo_screenwidth()  - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _build(self):
        pad = tk.Frame(self, bg=THEME["bg"], padx=28, pady=24)
        pad.pack(fill="both", expand=True)

        nome = self._admin.get("nome") or self._admin["login"]
        tk.Label(pad, text=f"Alterar senha de: {nome}",
                 font=("Segoe UI", 12, "bold"),
                 bg=THEME["bg"], fg=THEME["fg"]).pack(anchor="w", pady=(0, 18))

        self._var_nova  = tk.StringVar()
        self._var_conf  = tk.StringVar()
        self._var_erro  = tk.StringVar()

        for label, var in [("Nova senha", self._var_nova), ("Confirmar senha", self._var_conf)]:
            tk.Label(pad, text=label, font=FONT["sm"],
                     bg=THEME["bg"], fg=THEME["fg"]).pack(anchor="w")
            e = tk.Entry(pad, textvariable=var, show="•", font=FONT["md"],
                         relief="flat", bg="white", highlightthickness=1,
                         highlightbackground=THEME["border"],
                         highlightcolor=THEME["primary"])
            e.pack(fill="x", ipady=7, pady=(2, 10))

        tk.Label(pad, textvariable=self._var_erro, font=FONT["sm"],
                 bg=THEME["bg"], fg=THEME["danger"]).pack()

        tk.Button(pad, text="Salvar senha",
                  font=FONT["bold"], bg=THEME["primary"], fg="white",
                  relief="flat", cursor="hand2", pady=9,
                  command=self._salvar).pack(fill="x", pady=(8, 0))

        self.bind("<Return>", lambda _: self._salvar())

    def _salvar(self):
        from models.admin_global import AdminGlobal, AdminGlobalError
        nova = self._var_nova.get()
        conf = self._var_conf.get()

        if nova != conf:
            self._var_erro.set("As senhas não coincidem."); return

        try:
            AdminGlobal.alterar_senha(self._admin["id"], nova)
            self._on_salvo()
            self.destroy()
        except AdminGlobalError as e:
            self._var_erro.set(str(e))


# ── Diálogo: Renomear ─────────────────────────────────────────────

class _DialogRenomear(tk.Toplevel):
    def __init__(self, master, admin: dict, on_salvo):
        super().__init__(master)
        self.title("Renomear Administrador")
        self.configure(bg=THEME["bg"])
        self.resizable(False, False)
        self.grab_set()
        self._admin    = admin
        self._on_salvo = on_salvo
        self._build()
        self._centralizar(360, 220)

    def _centralizar(self, w, h):
        self.update_idletasks()
        x = (self.winfo_screenwidth()  - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _build(self):
        pad = tk.Frame(self, bg=THEME["bg"], padx=28, pady=24)
        pad.pack(fill="both", expand=True)

        tk.Label(pad, text=f"Login: {self._admin['login']}",
                 font=FONT["sm"], bg=THEME["bg"], fg=THEME["fg_light"]).pack(anchor="w")
        tk.Label(pad, text="Nome de exibição", font=FONT["sm"],
                 bg=THEME["bg"], fg=THEME["fg"]).pack(anchor="w", pady=(12, 0))

        self._var_nome = tk.StringVar(value=self._admin.get("nome") or "")
        self._var_erro = tk.StringVar()

        e = tk.Entry(pad, textvariable=self._var_nome, font=FONT["md"],
                     relief="flat", bg="white", highlightthickness=1,
                     highlightbackground=THEME["border"],
                     highlightcolor=THEME["primary"])
        e.pack(fill="x", ipady=7, pady=(4, 0))
        e.focus_set()
        e.select_range(0, tk.END)

        tk.Label(pad, textvariable=self._var_erro, font=FONT["sm"],
                 bg=THEME["bg"], fg=THEME["danger"]).pack()

        tk.Button(pad, text="Salvar",
                  font=FONT["bold"], bg=THEME["primary"], fg="white",
                  relief="flat", cursor="hand2", pady=9,
                  command=self._salvar).pack(fill="x", pady=(10, 0))

        self.bind("<Return>", lambda _: self._salvar())

    def _salvar(self):
        from models.admin_global import AdminGlobal
        AdminGlobal.alterar_nome(self._admin["id"], self._var_nome.get())
        self._on_salvo()
        self.destroy()
