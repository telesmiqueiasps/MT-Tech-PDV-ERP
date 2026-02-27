import tkinter as tk
from tkinter import messagebox, ttk
from config import THEME, FONT
from views.widgets.tabela import Tabela
from core.session import Session


class AbaUsuarios(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg=THEME["bg"])
        self._empresas: list[dict] = []
        self._build()
        # Carrega empresas só depois que a tabela já existe
        if Session.is_admin_global():
            self._carregar_empresas()
        else:
            self._carregar()

    def _build(self):
        # Seletor de empresa (só admin global)
        if Session.is_admin_global():
            sel_frame = tk.Frame(self, bg=THEME["bg"], padx=16, pady=12)
            sel_frame.pack(fill="x")
            tk.Label(sel_frame, text="Empresa:", font=FONT["sm"],
                     bg=THEME["bg"], fg=THEME["fg"]).pack(side="left")
            self._var_empresa = tk.StringVar()
            self._combo = ttk.Combobox(sel_frame, textvariable=self._var_empresa,
                                        state="readonly", font=FONT["md"], width=30)
            self._combo.pack(side="left", padx=(8, 0))
            self._combo.bind("<<ComboboxSelected>>", lambda _: self._trocar_empresa())

        # Barra de ações
        barra = tk.Frame(self, bg=THEME["bg"], padx=16, pady=12)
        barra.pack(fill="x")

        tk.Button(barra, text="+ Novo Usuário", font=FONT["bold"],
                  bg=THEME["primary"], fg="white", relief="flat",
                  cursor="hand2", padx=14, pady=6,
                  command=self._novo).pack(side="left")
        tk.Button(barra, text="✏  Editar", font=FONT["sm"],
                  bg=THEME["bg_card"], fg=THEME["fg"], relief="flat",
                  cursor="hand2", padx=12, pady=6,
                  command=self._editar).pack(side="left", padx=(8, 0))
        tk.Button(barra, text="🔑  Senha", font=FONT["sm"],
                  bg=THEME["bg_card"], fg=THEME["fg"], relief="flat",
                  cursor="hand2", padx=12, pady=6,
                  command=self._trocar_senha).pack(side="left", padx=(8, 0))
        tk.Button(barra, text="🗑  Desativar", font=FONT["sm"],
                  bg=THEME["bg_card"], fg=THEME["danger"], relief="flat",
                  cursor="hand2", padx=12, pady=6,
                  command=self._desativar).pack(side="left", padx=(8, 0))
        tk.Button(barra, text="↺  Atualizar", font=FONT["sm"],
                  bg=THEME["bg_card"], fg=THEME["fg_light"], relief="flat",
                  cursor="hand2", padx=12, pady=6,
                  command=self._carregar).pack(side="right")

        # Tabela — criada aqui para existir antes de qualquer _carregar
        self._tabela = Tabela(self, colunas=[
            ("ID",       50),
            ("Nome",    200),
            ("Login",   140),
            ("Perfil",  160),
            ("Criado em", 120),
        ])
        self._tabela.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        self._tabela.ao_duplo_clique = lambda _: self._editar()

    def _carregar_empresas(self):
        from models.empresa import Empresa
        self._empresas = Empresa.listar()
        nomes = [e["nome"] for e in self._empresas]
        self._combo["values"] = nomes
        if nomes:
            self._combo.current(0)
            self._trocar_empresa()

    def _trocar_empresa(self):
        idx = self._combo.current()
        if idx < 0:
            return
        emp = self._empresas[idx]
        from pathlib import Path
        from core.database import DatabaseManager
        DatabaseManager.conectar_empresa(Path(emp["db_path"]))
        self._carregar()

    def _carregar(self):
        self._tabela.limpar()
        try:
            from models.usuario import Usuario
            for u in Usuario.listar():
                self._tabela.inserir([
                    u["id"], u["nome"], u["login"],
                    u.get("perfil_nome") or "—",
                    (u.get("criado_em") or "")[:10],
                ])
        except Exception:
            pass

    def _selecionado_id(self) -> int | None:
        sel = self._tabela.selecionado()
        return int(sel[0]) if sel else None

    def _novo(self):
        from views.admin.form_usuario import FormUsuario
        FormUsuario(self, None, self._carregar)

    def _editar(self):
        id_ = self._selecionado_id()
        if not id_:
            messagebox.showwarning("Atenção", "Selecione um usuário.", parent=self)
            return
        from views.admin.form_usuario import FormUsuario
        FormUsuario(self, id_, self._carregar)

    def _trocar_senha(self):
        id_ = self._selecionado_id()
        if not id_:
            messagebox.showwarning("Atenção", "Selecione um usuário.", parent=self)
            return
        from views.admin.form_senha import FormSenha
        FormSenha(self, id_)

    def _desativar(self):
        id_ = self._selecionado_id()
        if not id_:
            messagebox.showwarning("Atenção", "Selecione um usuário.", parent=self)
            return
        if messagebox.askyesno("Confirmar", "Desativar este usuário?", parent=self):
            from models.usuario import Usuario
            Usuario.desativar(id_)
            self._carregar()