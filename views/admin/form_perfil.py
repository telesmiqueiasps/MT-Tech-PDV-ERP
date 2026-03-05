import tkinter as tk
from config import THEME, FONT
from views.base_view import BaseView


class FormPerfil(BaseView):
    def __init__(self, master, ao_salvar=None):
        super().__init__(master, "Novo Perfil", 380, 340, modal=True)
        self.resizable(False, False)
        self._ao_salvar = ao_salvar
        self._build()

    def _build(self):
        body = tk.Frame(self, bg=THEME["bg"], padx=35, pady=25)
        body.pack(fill="both", expand=True)

        tk.Label(body, text="Novo Perfil", font=FONT["title"],
                 bg=THEME["bg"], fg=THEME["fg"]).pack(anchor="w", pady=(0, 18))

        self._campo(body, "Nome do Perfil *", "nome")
        self._campo(body, "Descrição",        "descricao")

        self._var_erro = tk.StringVar()
        tk.Label(body, textvariable=self._var_erro, font=FONT["sm"],
                 bg=THEME["bg"], fg=THEME["danger"]).pack(anchor="w", pady=(8, 0))

        tk.Button(body, text="Criar Perfil", font=FONT["bold"],
                  bg=THEME["primary"], fg="white", relief="flat",
                  cursor="hand2", pady=9,
                  command=self._salvar).pack(fill="x", pady=(12, 0))

    def _campo(self, parent, label: str, attr: str):
        tk.Label(parent, text=label, font=FONT["sm"],
                 bg=THEME["bg"], fg=THEME["fg"]).pack(anchor="w", pady=(10, 2))
        var = tk.StringVar()
        tk.Entry(parent, textvariable=var, font=FONT["md"],
                 relief="flat", bg="white", fg=THEME["fg"],
                 highlightthickness=1,
                 highlightbackground=THEME["border"],
                 highlightcolor=THEME["primary"]).pack(fill="x", ipady=7)
        setattr(self, f"_var_{attr}", var)

    def _salvar(self):
        nome = self._var_nome.get().strip()
        if not nome:
            self._var_erro.set("O nome é obrigatório.")
            return
        from models.perfil import Perfil
        Perfil.criar(nome, self._var_descricao.get().strip())
        if self._ao_salvar:
            self._ao_salvar()
        self.destroy()