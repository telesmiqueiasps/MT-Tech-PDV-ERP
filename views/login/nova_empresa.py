import tkinter as tk
from views.base_view import BaseView
from config import THEME, FONT


class NovaEmpresa(BaseView):
    def __init__(self, master):
        super().__init__(master, "Nova Empresa", 400, 320, modal=True)
        self.resizable(False, False)
        self._build()

    def _build(self):
        body = tk.Frame(self, bg=THEME["bg"], padx=35, pady=25)
        body.pack(fill="both", expand=True)

        tk.Label(body, text="Nova Empresa", font=FONT["title"],
                 bg=THEME["bg"], fg=THEME["fg"]).pack(anchor="w", pady=(0, 15))

        self._campo(body, "Nome Fantasia *", "nome")
        self._campo(body, "CNPJ", "cnpj")
        self._campo(body, "Razão Social", "razao")

        self._var_erro = tk.StringVar()
        tk.Label(body, textvariable=self._var_erro, font=FONT["sm"],
                 bg=THEME["bg"], fg=THEME["danger"]).pack(anchor="w", pady=(6, 0))

        tk.Button(body, text="Criar Empresa", font=FONT["bold"],
                  bg=THEME["primary"], fg=THEME["fg_white"], relief="flat",
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
        from database.seeds.seed import criar_empresa
        criar_empresa(nome, self._var_cnpj.get().strip(), self._var_razao.get().strip())
        self.sucesso(f"Empresa '{nome}' criada com sucesso!")
        self.destroy()