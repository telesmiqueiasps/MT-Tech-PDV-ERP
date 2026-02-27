import tkinter as tk
from tkinter import ttk
from config import THEME, FONT
from views.base_view import BaseView


class FormUsuario(BaseView):
    def __init__(self, master, usuario_id: int | None, ao_salvar=None):
        titulo = "Editar Usuário" if usuario_id else "Novo Usuário"
        super().__init__(master, titulo, 420, 720, modal=True)
        self.resizable(True, True)
        self._usuario_id = usuario_id
        self._ao_salvar  = ao_salvar
        self._perfis: list[dict] = []
        self._build()
        if usuario_id:
            self._preencher()

    def _build(self):
        body = tk.Frame(self, bg=THEME["bg"], padx=35, pady=25)
        body.pack(fill="both", expand=True)

        titulo = "Novo Usuário" if not self._usuario_id else "Editar Usuário"
        tk.Label(body, text=titulo, font=FONT["title"],
                 bg=THEME["bg"], fg=THEME["fg"]).pack(anchor="w", pady=(0, 18))

        self._campo(body, "Nome completo *", "nome")
        self._campo(body, "Login *",         "login")

        if not self._usuario_id:
            self._campo(body, "Senha *",          "senha",  show="•")
            self._campo(body, "Confirmar Senha *", "senha2", show="•")

        # Seletor de perfil
        tk.Label(body, text="Perfil *", font=FONT["sm"],
                 bg=THEME["bg"], fg=THEME["fg"]).pack(anchor="w", pady=(10, 2))

        self._var_perfil = tk.StringVar()
        self._combo_perfil = ttk.Combobox(body, textvariable=self._var_perfil,
                                           state="readonly", font=FONT["md"])
        self._combo_perfil.pack(fill="x", ipady=4)
        self._carregar_perfis()

        self._var_erro = tk.StringVar()
        tk.Label(body, textvariable=self._var_erro, font=FONT["sm"],
                 bg=THEME["bg"], fg=THEME["danger"]).pack(anchor="w", pady=(8, 0))

        tk.Button(body, text="Salvar", font=FONT["bold"],
                  bg=THEME["primary"], fg="white", relief="flat",
                  cursor="hand2", pady=9,
                  command=self._salvar).pack(fill="x", pady=(10, 0))

    def _campo(self, parent, label: str, attr: str, show: str = ""):
        tk.Label(parent, text=label, font=FONT["sm"],
                 bg=THEME["bg"], fg=THEME["fg"]).pack(anchor="w", pady=(10, 2))
        var = tk.StringVar()
        tk.Entry(parent, textvariable=var, font=FONT["md"], show=show,
                 relief="flat", bg="white", fg=THEME["fg"],
                 highlightthickness=1,
                 highlightbackground=THEME["border"],
                 highlightcolor=THEME["primary"]).pack(fill="x", ipady=7)
        setattr(self, f"_var_{attr}", var)

    def _carregar_perfis(self):
        from models.perfil import Perfil
        self._perfis = Perfil.listar()
        self._combo_perfil["values"] = [p["nome"] for p in self._perfis]
        if self._perfis:
            self._combo_perfil.current(0)

    def _preencher(self):
        from models.usuario import Usuario
        u = Usuario.buscar_por_id(self._usuario_id)
        if not u:
            return
        self._var_nome.set(u["nome"])
        self._var_login.set(u["login"])
        for i, p in enumerate(self._perfis):
            if p["id"] == u["perfil_id"]:
                self._combo_perfil.current(i)
                break

    def _salvar(self):
        nome  = self._var_nome.get().strip()
        login = self._var_login.get().strip()
        idx   = self._combo_perfil.current()

        if not nome or not login or idx < 0:
            self._var_erro.set("Preencha todos os campos obrigatórios.")
            return

        perfil_id = self._perfis[idx]["id"]

        from models.usuario import Usuario
        if Usuario.login_existe(login, ignorar_id=self._usuario_id):
            self._var_erro.set("Este login já está em uso.")
            return

        if self._usuario_id:
            Usuario.atualizar(self._usuario_id, nome, login, perfil_id)
        else:
            senha  = self._var_senha.get()
            senha2 = self._var_senha2.get()
            if not senha:
                self._var_erro.set("A senha é obrigatória.")
                return
            if senha != senha2:
                self._var_erro.set("As senhas não coincidem.")
                return
            if len(senha) < 6:
                self._var_erro.set("Mínimo 6 caracteres.")
                return
            Usuario.criar(nome, login, senha, perfil_id)

        if self._ao_salvar:
            self._ao_salvar()
        self.destroy()