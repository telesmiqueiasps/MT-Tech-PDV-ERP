import tkinter as tk
from tkinter import messagebox
from config import THEME, FONT
from views.widgets.tabela import Tabela
from views.widgets.widgets import botao
from views.base_view import BaseView


class AbaDepositos(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg=THEME["bg"])
        self._build()
        self._carregar()

    def _build(self):
        tb = tk.Frame(self, bg=THEME["bg_card"], highlightthickness=1,
                      highlightbackground=THEME["border"], padx=14, pady=10)
        tb.pack(fill="x", pady=(0, 1))

        tk.Label(tb, text="Depósitos e Almoxarifados", font=FONT["bold"],
                 bg=THEME["bg_card"], fg=THEME["fg"]).pack(side="left")

        botao(tb, "+ Novo Depósito", tipo="primario",   command=self._novo).pack(side="right")
        botao(tb, "✏  Editar",       tipo="secundario", command=self._editar).pack(side="right", padx=(0, 8))
        botao(tb, "🗑  Desativar",   tipo="perigo",     command=self._desativar).pack(side="right", padx=(0, 8))

        self._tabela = Tabela(self, colunas=[
            ("ID", 50), ("Nome", 240), ("Descrição", 400),
        ])
        self._tabela.pack(fill="both", expand=True)
        self._tabela.ao_duplo_clique = lambda _: self._editar()

    def _carregar(self):
        from models.estoque import Deposito
        lista = Deposito.listar()
        self._tabela.limpar()
        for d in lista:
            self._tabela.inserir([d["id"], d["nome"], d.get("descricao") or ""])

    def _sel_id(self):
        sel = self._tabela.selecionado()
        return int(sel[0]) if sel else None

    def _novo(self):      FormDeposito(self, None, self._carregar)
    def _editar(self):
        id_ = self._sel_id()
        if not id_: messagebox.showwarning("Atenção", "Selecione um depósito.", parent=self); return
        FormDeposito(self, id_, self._carregar)
    def _desativar(self):
        id_ = self._sel_id()
        if not id_: messagebox.showwarning("Atenção", "Selecione um depósito.", parent=self); return
        if id_ == 1: messagebox.showerror("Erro", "O depósito principal não pode ser desativado.", parent=self); return
        if messagebox.askyesno("Confirmar", "Desativar este depósito?", parent=self):
            from models.estoque import Deposito
            Deposito.desativar(id_)
            self._carregar()


class FormDeposito(BaseView):
    def __init__(self, master, dep_id, ao_salvar=None):
        titulo = "Editar Depósito" if dep_id else "Novo Depósito"
        super().__init__(master, titulo, 440, 280, modal=True)
        self.resizable(True, True)
        self._dep_id    = dep_id
        self._ao_salvar = ao_salvar
        self._build()
        if dep_id: self._preencher()

    def _build(self):
        P = 24
        tk.Label(self, text="Novo Depósito" if not self._dep_id else "Editar Depósito",
                 font=FONT["title"], bg=THEME["bg"], fg=THEME["fg"]
                 ).pack(anchor="w", padx=P, pady=(20, 16))

        card = tk.Frame(self, bg=THEME["bg_card"], highlightthickness=1,
                        highlightbackground=THEME["border"])
        card.pack(fill="x", padx=P)
        inner = tk.Frame(card, bg=THEME["bg_card"], padx=16, pady=14)
        inner.pack(fill="x")

        self._var_nome = tk.StringVar()
        tk.Label(inner, text="Nome *", font=FONT["sm"],
                 bg=THEME["bg_card"], fg=THEME["fg"]).pack(anchor="w", pady=(0, 3))
        tk.Entry(inner, textvariable=self._var_nome, font=FONT["md"],
                 relief="flat", bg="white", fg=THEME["fg"],
                 highlightthickness=1, highlightbackground=THEME["border"],
                 highlightcolor=THEME["primary"]).pack(fill="x", ipady=7, pady=(0, 10))

        self._var_desc = tk.StringVar()
        tk.Label(inner, text="Descrição", font=FONT["sm"],
                 bg=THEME["bg_card"], fg=THEME["fg"]).pack(anchor="w", pady=(0, 3))
        tk.Entry(inner, textvariable=self._var_desc, font=FONT["md"],
                 relief="flat", bg="white", fg=THEME["fg"],
                 highlightthickness=1, highlightbackground=THEME["border"],
                 highlightcolor=THEME["primary"]).pack(fill="x", ipady=7)

        self._var_erro = tk.StringVar()
        tk.Label(self, textvariable=self._var_erro, font=FONT["sm"],
                 bg=THEME["bg"], fg=THEME["danger"]).pack(anchor="w", padx=P, pady=(8, 0))
        botao(self, "💾  Salvar", tipo="primario",
              command=self._salvar).pack(fill="x", padx=P, pady=(8, 20))

    def _preencher(self):
        from models.estoque import Deposito
        d = Deposito.buscar_por_id(self._dep_id)
        if d:
            self._var_nome.set(d["nome"])
            self._var_desc.set(d.get("descricao") or "")

    def _salvar(self):
        nome = self._var_nome.get().strip()
        if not nome:
            self._var_erro.set("O nome é obrigatório."); return
        from models.estoque import Deposito
        if self._dep_id: Deposito.atualizar(self._dep_id, nome, self._var_desc.get().strip())
        else: Deposito.criar(nome, self._var_desc.get().strip())
        if self._ao_salvar: self._ao_salvar()
        self.destroy()