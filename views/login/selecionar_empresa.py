import tkinter as tk
from views.base_view import BaseView
from config import THEME, FONT
from assets import Assets


class SelecionarEmpresa(BaseView):
    empresa_selecionada: dict | None = None

    def __init__(self, master):
        super().__init__(master, "MT Tech - Selecionar Empresa", 500, 480, modal=True)
        self.resizable(False, False)
        Assets.icon(self)
        self._build()

    def _build(self):

        # ================= HEADER =================
        header = tk.Frame(self, bg=THEME["primary_dark"], height=130)
        header.pack(fill="x")
        header.pack_propagate(False)

        logo = Assets.logo_branca(altura=42)
        if logo:
            self._logo_img = logo
            tk.Label(
                header,
                image=logo,
                bg=THEME["primary_dark"]
            ).pack(pady=(18, 6))


        tk.Label(
            header,
            text="ERP & PDV",
            font=("Segoe UI", 10),
            bg=THEME["primary_dark"],
            fg=THEME["fg_white"]
        ).pack(pady=(0, 10))

        # ================= BODY =================
        body = tk.Frame(self, bg=THEME["bg"])
        body.pack(fill="both", expand=True, padx=30, pady=25)

        # Card central
        card = tk.Frame(body, bg="white", bd=0)
        card.pack(fill="both", expand=True)
        card.pack_propagate(False)

        # Borda simulada elegante
        card.configure(highlightbackground=THEME["border"],
                       highlightthickness=1)

        tk.Label(
            card,
            text="Selecione uma empresa para continuar",
            font=FONT["bold"],
            bg="white",
            fg=THEME["fg"]
        ).pack(anchor="w", padx=20, pady=(20, 10))

        self._listbox = tk.Listbox(
            card,
            font=FONT["md"],
            relief="flat",
            selectbackground=THEME["primary"],
            selectforeground="white",
            activestyle="none",
            bg="#f9fafb",
            fg=THEME["fg"],
            bd=0,
            highlightthickness=0
        )
        self._listbox.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        self._listbox.bind("<Double-Button-1>", lambda _: self._selecionar())

        self._empresas: list[dict] = []
        self._carregar()

        # ================= FOOTER =================
        footer = tk.Frame(self, bg=THEME["bg"])
        footer.pack(fill="x", padx=30, pady=(0, 20))


        tk.Button(
            footer,
            text="Admin Global",
            font=FONT["sm"],
            bg=THEME["bg"],
            fg=THEME["fg_light"],
            relief="flat",
            cursor="hand2",
            command=self._login_admin
        ).pack(side="right", padx=(8, 0))

        tk.Button(
            footer,
            text="Entrar →",
            font=FONT["bold"],
            bg=THEME["primary"],
            fg=THEME["fg_white"],
            relief="flat",
            cursor="hand2",
            padx=22,
            pady=9,
            command=self._selecionar
        ).pack(side="right")

    # ================= LÓGICA =================

    def _carregar(self):
        from models.empresa import Empresa
        self._empresas = Empresa.listar()
        self._listbox.delete(0, tk.END)
        for emp in self._empresas:
            self._listbox.insert(tk.END, f"   {emp['nome']}")
        if self._empresas:
            self._listbox.selection_set(0)

    def _selecionar(self):
        sel = self._listbox.curselection()
        if not sel:
            self.erro("Selecione uma empresa.")
            return
        self.empresa_selecionada = self._empresas[sel[0]]
        self.destroy()

    def _login_admin(self):
        self.empresa_selecionada = {
            "id": 0,
            "nome": "Admin Global",
            "db_path": ""
        }
        self.destroy()
