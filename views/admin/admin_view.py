import tkinter as tk
from tkinter import ttk
from config import THEME, FONT
from core.session import Session


class AdminView(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg=THEME["bg"])
        self.pack(fill="both", expand=True)
        self._build()

    def _build(self):
        # Cabeçalho
        header = tk.Frame(self, bg=THEME["bg"], padx=28, pady=18)
        header.pack(fill="x")
        tk.Label(header, text="⚙  Administração", font=("Segoe UI", 18, "bold"),
                 bg=THEME["bg"], fg=THEME["fg"]).pack(anchor="w")
        tk.Label(header, text="Gerencie empresas, usuários e perfis de acesso.",
                 font=FONT["sm"], bg=THEME["bg"], fg=THEME["fg_light"]).pack(anchor="w")

        # Abas
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Admin.TNotebook", background=THEME["bg"], borderwidth=0)
        style.configure("Admin.TNotebook.Tab",
                        background=THEME["bg_card"], foreground=THEME["fg"],
                        font=FONT["bold"], padding=(20, 8))
        style.map("Admin.TNotebook.Tab",
                  background=[("selected", THEME["primary"])],
                  foreground=[("selected", "white")])

        self._notebook = ttk.Notebook(self, style="Admin.TNotebook")
        self._notebook.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        # Aba Empresas (só admin global)
        if Session.is_admin_global():
            from views.admin.aba_empresas import AbaEmpresas
            aba_emp = AbaEmpresas(self._notebook)
            self._notebook.add(aba_emp, text="🏢  Empresas")

        # Aba Administradores Globais (só admin global)
        if Session.is_admin_global():
            from views.admin.aba_admins import AbaAdmins
            aba_adm = AbaAdmins(self._notebook)
            self._notebook.add(aba_adm, text="🛡  Administradores")

        # Aba Usuários
        from views.admin.aba_usuarios import AbaUsuarios
        aba_usr = AbaUsuarios(self._notebook)
        self._notebook.add(aba_usr, text="👤  Usuários")

        # Aba Perfis
        from views.admin.aba_perfis import AbaPerfis
        aba_prf = AbaPerfis(self._notebook)
        self._notebook.add(aba_prf, text="🔑  Perfis & Permissões")

        # Aba Licenças (só admin global)
        if Session.is_admin_global():
            from views.admin.aba_licencas import AbaLicencas
            aba_lic = AbaLicencas(self._notebook)
            self._notebook.add(aba_lic, text="📋  Licenças")