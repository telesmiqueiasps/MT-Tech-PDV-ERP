import tkinter as tk
from tkinter import ttk
from config import THEME, FONT
from views.widgets.widgets import PageHeader


class ProdutosView(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg=THEME["bg"])
        self.pack(fill="both", expand=True)
        try:
            from core.database import DatabaseManager
            DatabaseManager.empresa()
        except Exception:
            tk.Label(self, text="⚠  Selecione uma empresa para acessar os produtos.",
                     font=FONT["lg"], bg=THEME["bg"],
                     fg=THEME["warning"]).pack(expand=True)
            return
        self._build()

    def _build(self):
        PageHeader(self, "📦", "Produtos",
                   "Gerencie o catálogo de produtos e categorias."
                   ).pack(fill="x", padx=20, pady=(16, 0))

        style = ttk.Style()
        style.configure("Prod.TNotebook",
                        background=THEME["bg"], borderwidth=0)
        style.configure("Prod.TNotebook.Tab",
                        background=THEME["bg_card"],
                        foreground=THEME["fg"],
                        font=FONT["bold"],
                        padding=(20, 8))
        style.map("Prod.TNotebook.Tab",
                  background=[("selected", THEME["primary_dark"])],
                  foreground=[("selected", "white")])

        nb = ttk.Notebook(self, style="Prod.TNotebook")
        nb.pack(fill="both", expand=True, padx=20, pady=12)

        from views.produtos.aba_produtos   import AbaProdutos
        from views.produtos.aba_categorias import AbaCategorias

        nb.add(AbaProdutos(nb),   text="  📦  Produtos  ")
        nb.add(AbaCategorias(nb), text="  🏷  Categorias  ")