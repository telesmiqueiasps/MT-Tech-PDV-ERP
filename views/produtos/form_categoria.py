import tkinter as tk
from config import THEME, FONT
from views.base_view import BaseView


class FormCategoria(BaseView):
    def __init__(self, master, dados: tuple | None, ao_salvar=None):
        titulo = "Editar Categoria" if dados else "Nova Categoria"
        super().__init__(master, titulo, 360, 220, modal=True)
        self.resizable(False, False)
        self._dados    = dados  # (id, nome) ou None
        self._ao_salvar = ao_salvar
        self._build()

    def _build(self):
        body = tk.Frame(self, bg=THEME["bg"], padx=35, pady=25)
        body.pack(fill="both", expand=True)

        titulo = "Editar Categoria" if self._dados else "Nova Categoria"
        tk.Label(body, text=titulo, font=FONT["title"],
                 bg=THEME["bg"], fg=THEME["fg"]).pack(anchor="w", pady=(0, 16))

        tk.Label(body, text="Nome *", font=FONT["sm"],
                 bg=THEME["bg"], fg=THEME["fg"]).pack(anchor="w")
        self._var_nome = tk.StringVar(value=self._dados[1] if self._dados else "")
        tk.Entry(body, textvariable=self._var_nome, font=FONT["md"],
                 relief="flat", bg="white", fg=THEME["fg"],
                 highlightthickness=1,
                 highlightbackground=THEME["border"],
                 highlightcolor=THEME["primary"]).pack(fill="x", ipady=7, pady=(4, 0))

        self._var_erro = tk.StringVar()
        tk.Label(body, textvariable=self._var_erro, font=FONT["sm"],
                 bg=THEME["bg"], fg=THEME["danger"]).pack(anchor="w", pady=(6, 0))

        tk.Button(body, text="Salvar", font=FONT["bold"],
                  bg=THEME["primary"], fg="white", relief="flat",
                  cursor="hand2", pady=9,
                  command=self._salvar).pack(fill="x", pady=(10, 0))

    def _salvar(self):
        nome = self._var_nome.get().strip()
        if not nome:
            self._var_erro.set("O nome é obrigatório.")
            return
        from models.produto import Categoria
        if self._dados:
            Categoria.atualizar(self._dados[0], nome)
        else:
            Categoria.criar(nome)
        if self._ao_salvar:
            self._ao_salvar()
        self.destroy()  