import tkinter as tk
from views.base_view import BaseView
from config import THEME, FONT, APP_NAME


class SetupWizard(BaseView):
    def __init__(self, master):
        super().__init__(master, "Configuração Inicial", 460, 500, modal=True)
        self.resizable(True, True)
        self._build()

    def _build(self):
        header = tk.Frame(self, bg=THEME["primary_dark"], height=90)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text=f"⚙️  Configuração Inicial — {APP_NAME}",
                 font=FONT["title"], bg=THEME["primary_dark"],
                 fg=THEME["fg_white"]).pack(expand=True)

        body = tk.Frame(self, bg=THEME["bg"], padx=40, pady=25)
        body.pack(fill="both", expand=True)

        tk.Label(body, text="Bem-vindo! Crie o administrador e a primeira empresa.",
                 font=FONT["sm"], bg=THEME["bg"],
                 fg=THEME["fg_light"]).pack(anchor="w", pady=(0, 20))

        self._campo(body, "Login do Administrador", "admin_login")
        self._campo(body, "Senha (mín. 6 caracteres)", "admin_senha", show="•")
        self._campo(body, "Confirmar Senha", "admin_senha2", show="•")
        self._campo(body, "Nome da Empresa", "empresa_nome")
        self._campo(body, "CNPJ (opcional)", "empresa_cnpj")

        self._var_erro = tk.StringVar()
        tk.Label(body, textvariable=self._var_erro, font=FONT["sm"],
                 bg=THEME["bg"], fg=THEME["danger"]).pack(anchor="w", pady=(8, 0))

        tk.Button(body, text="Criar e Continuar →",
                  font=FONT["bold"], bg=THEME["primary"], fg=THEME["fg_white"],
                  relief="flat", cursor="hand2", pady=10,
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

    def _salvar(self):
        login   = self._var_admin_login.get().strip()
        senha   = self._var_admin_senha.get()
        senha2  = self._var_admin_senha2.get()
        empresa = self._var_empresa_nome.get().strip()
        cnpj    = self._var_empresa_cnpj.get().strip()

        if not login or not senha or not empresa:
            self._var_erro.set("Preencha login, senha e nome da empresa.")
            return
        if senha != senha2:
            self._var_erro.set("As senhas não coincidem.")
            return
        if len(senha) < 6:
            self._var_erro.set("A senha deve ter no mínimo 6 caracteres.")
            return

        try:
            from database.seeds.seed import criar_admin_global, criar_empresa
            criar_admin_global(login, senha)
            criar_empresa(empresa, cnpj)
            # Fecha silenciosamente — main.py continua o fluxo normalmente
            self.destroy()
        except Exception as e:
            self._var_erro.set(f"Erro ao configurar: {e}")