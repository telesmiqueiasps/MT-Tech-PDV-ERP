import tkinter as tk
from config import THEME, FONT
from views.base_view import BaseView


class FormSenha(BaseView):
    def __init__(self, master, usuario_id: int):
        super().__init__(master, "Alterar Senha", 380, 380, modal=True)
        self.resizable(True, True)
        self._usuario_id = usuario_id
        self._build()

    def _build(self):
        body = tk.Frame(self, bg=THEME["bg"], padx=35, pady=25)
        body.pack(fill="both", expand=True)

        tk.Label(body, text="Alterar Senha", font=FONT["title"],
                 bg=THEME["bg"], fg=THEME["fg"]).pack(anchor="w", pady=(0, 18))

        self._campo(body, "Nova Senha *",       "senha")
        self._campo(body, "Confirmar Senha *",  "senha2")

        self._var_erro = tk.StringVar()
        tk.Label(body, textvariable=self._var_erro, font=FONT["sm"],
                 bg=THEME["bg"], fg=THEME["danger"]).pack(anchor="w", pady=(8, 0))

        tk.Button(body, text="Alterar", font=FONT["bold"],
                  bg=THEME["primary"], fg="white", relief="flat",
                  cursor="hand2", pady=9,
                  command=self._salvar).pack(fill="x", pady=(12, 0))

    def _campo(self, parent, label: str, attr: str):
        tk.Label(parent, text=label, font=FONT["sm"],
                 bg=THEME["bg"], fg=THEME["fg"]).pack(anchor="w", pady=(10, 2))
        var = tk.StringVar()
        tk.Entry(parent, textvariable=var, font=FONT["md"], show="•",
                 relief="flat", bg="white", fg=THEME["fg"],
                 highlightthickness=1,
                 highlightbackground=THEME["border"],
                 highlightcolor=THEME["primary"]).pack(fill="x", ipady=7)
        setattr(self, f"_var_{attr}", var)

    def _salvar(self):
        senha  = self._var_senha.get()
        senha2 = self._var_senha2.get()

        if not senha:
            self._var_erro.set("Digite a nova senha.")
            return
        if senha != senha2:
            self._var_erro.set("As senhas não coincidem.")
            return
        if len(senha) < 6:
            self._var_erro.set("Mínimo 6 caracteres.")
            return

        from models.usuario import Usuario
        Usuario.alterar_senha(self._usuario_id, senha)
        self.sucesso("Senha alterada com sucesso!")
        self.destroy()