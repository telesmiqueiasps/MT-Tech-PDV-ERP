import tkinter as tk
from tkinter import ttk
from config import THEME, FONT
from views.widgets.widgets import PageHeader


class EstoqueView(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg=THEME["bg"])
        self.pack(fill="both", expand=True)
        try:
            from core.database import DatabaseManager
            DatabaseManager.empresa()
        except Exception:
            tk.Label(self, text="⚠  Selecione uma empresa.",
                     font=FONT["lg"], bg=THEME["bg"],
                     fg=THEME["warning"]).pack(expand=True)
            return
        self._build()

    def _build(self):
        PageHeader(self, "📦", "Estoque",
                   "Movimentações, posição e inventário."
                   ).pack(fill="x", padx=20, pady=(16, 0))

        style = ttk.Style()
        style.configure("Est.TNotebook",
                        background=THEME["bg"], borderwidth=0)
        style.configure("Est.TNotebook.Tab",
                        background=THEME["bg_card"],
                        foreground=THEME["fg"],
                        font=FONT["bold"],
                        padding=(18, 8))
        style.map("Est.TNotebook.Tab",
                  background=[("selected", THEME["primary_dark"])],
                  foreground=[("selected", "white")])

        nb = ttk.Notebook(self, style="Est.TNotebook")
        nb.pack(fill="both", expand=True, padx=20, pady=12)

        from views.estoque.aba_posicao     import AbaPosicao
        from views.estoque.aba_movimentos  import AbaMovimentos
        from views.estoque.aba_inventario  import AbaInventario
        from views.estoque.aba_depositos   import AbaDepositos

        self._aba_posicao = AbaPosicao(nb)
        nb.add(self._aba_posicao,               text="  📊  Posição  ")
        nb.add(AbaMovimentos(nb),               text="  🔄  Movimentos  ")
        nb.add(AbaInventario(nb),               text="  📋  Inventário  ")
        nb.add(AbaDepositos(nb),                text="  🏭  Depósitos  ")