import tkinter as tk
from tkinter import messagebox
from config import THEME, FONT
from views.widgets.tabela import Tabela


class AbaEmpresas(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg=THEME["bg"])
        self._empresa_id: int | None = None
        self._build()
        self._carregar()

    def _build(self):
        # Barra de ações
        barra = tk.Frame(self, bg=THEME["bg"], padx=16, pady=12)
        barra.pack(fill="x")

        tk.Button(barra, text="+ Nova Empresa", font=FONT["bold"],
                  bg=THEME["primary"], fg="white", relief="flat",
                  cursor="hand2", padx=14, pady=6,
                  command=self._nova).pack(side="left")

        tk.Button(barra, text="✏  Editar", font=FONT["sm"],
                  bg=THEME["bg_card"], fg=THEME["fg"], relief="flat",
                  cursor="hand2", padx=12, pady=6,
                  command=self._editar).pack(side="left", padx=(8, 0))

        tk.Button(barra, text="🗑  Desativar", font=FONT["sm"],
                  bg=THEME["bg_card"], fg=THEME["danger"], relief="flat",
                  cursor="hand2", padx=12, pady=6,
                  command=self._desativar).pack(side="left", padx=(8, 0))

        tk.Button(barra, text="↺  Atualizar", font=FONT["sm"],
                  bg=THEME["bg_card"], fg=THEME["fg_light"], relief="flat",
                  cursor="hand2", padx=12, pady=6,
                  command=self._carregar).pack(side="right")

        # Tabela
        self._tabela = Tabela(self, colunas=[
            ("ID",           50),
            ("Nome",        220),
            ("Razão Social", 220),
            ("CNPJ",        140),
            ("Criado em",   140),
        ])
        self._tabela.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        self._tabela.ao_duplo_clique = lambda _: self._editar()

    def _carregar(self):
        from models.empresa import Empresa
        self._tabela.limpar()
        for emp in Empresa.listar():
            self._tabela.inserir([
                emp["id"], emp["nome"],
                emp.get("razao_social") or "—",
                emp.get("cnpj") or "—",
                (emp.get("criado_em") or "")[:10],
            ])

    def _selecionado_id(self) -> int | None:
        sel = self._tabela.selecionado()
        return int(sel[0]) if sel else None

    def _nova(self):
        from views.admin.form_empresa import FormEmpresa
        FormEmpresa(self, None, self._carregar)

    def _editar(self):
        id_ = self._selecionado_id()
        if not id_:
            messagebox.showwarning("Atenção", "Selecione uma empresa.", parent=self)
            return
        from views.admin.form_empresa import FormEmpresa
        FormEmpresa(self, id_, self._carregar)

    def _desativar(self):
        id_ = self._selecionado_id()
        if not id_:
            messagebox.showwarning("Atenção", "Selecione uma empresa.", parent=self)
            return
        if messagebox.askyesno("Confirmar", "Desativar esta empresa?", parent=self):
            from models.empresa import Empresa
            Empresa.desativar(id_)
            self._carregar()