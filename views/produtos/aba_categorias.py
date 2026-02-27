import tkinter as tk
from tkinter import messagebox
from config import THEME, FONT
from views.widgets.tabela import Tabela


class AbaCategorias(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg=THEME["bg"])
        self._build()
        self._carregar()

    def _build(self):
        barra = tk.Frame(self, bg=THEME["bg"], padx=16, pady=12)
        barra.pack(fill="x")

        tk.Button(barra, text="+ Nova Categoria", font=FONT["bold"],
                  bg=THEME["primary"], fg="white", relief="flat",
                  cursor="hand2", padx=14, pady=6,
                  command=self._nova).pack(side="left")
        tk.Button(barra, text="✏  Editar", font=FONT["sm"],
                  bg=THEME["bg_card"], fg=THEME["fg"], relief="flat",
                  cursor="hand2", padx=12, pady=6,
                  command=self._editar).pack(side="left", padx=(8, 0))
        tk.Button(barra, text="🗑  Excluir", font=FONT["sm"],
                  bg=THEME["bg_card"], fg=THEME["danger"], relief="flat",
                  cursor="hand2", padx=12, pady=6,
                  command=self._excluir).pack(side="left", padx=(8, 0))

        self._tabela = Tabela(self, colunas=[
            ("ID",   60),
            ("Nome", 300),
        ])
        self._tabela.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        self._tabela.ao_duplo_clique = lambda _: self._editar()

    def _carregar(self):
        from models.produto import Categoria
        self._tabela.limpar()
        for c in Categoria.listar():
            self._tabela.inserir([c["id"], c["nome"]])

    def _selecionado(self) -> tuple | None:
        sel = self._tabela.selecionado()
        return (int(sel[0]), sel[1]) if sel else None

    def _nova(self):
        from views.produtos.form_categoria import FormCategoria
        FormCategoria(self, None, self._carregar)

    def _editar(self):
        sel = self._selecionado()
        if not sel:
            messagebox.showwarning("Atenção", "Selecione uma categoria.", parent=self)
            return
        from views.produtos.form_categoria import FormCategoria
        FormCategoria(self, sel, self._carregar)

    def _excluir(self):
        sel = self._selecionado()
        if not sel:
            messagebox.showwarning("Atenção", "Selecione uma categoria.", parent=self)
            return
        from models.produto import Categoria
        if Categoria.em_uso(sel[0]):
            messagebox.showerror("Erro",
                "Esta categoria está em uso por produtos ativos.", parent=self)
            return
        if messagebox.askyesno("Confirmar", "Excluir esta categoria?", parent=self):
            Categoria.desativar(sel[0])
            self._carregar()