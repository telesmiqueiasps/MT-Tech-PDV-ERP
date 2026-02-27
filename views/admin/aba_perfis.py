import tkinter as tk
from tkinter import messagebox
from config import THEME, FONT, PERMISSOES
from views.widgets.tabela import Tabela


class AbaPerfis(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg=THEME["bg"])
        self._perfil_id: int | None = None
        self._checks: dict[str, tk.BooleanVar] = {}
        self._build()
        self._carregar()

    def _build(self):
        # Layout: lista de perfis (esq) | permissões (dir)
        self._frame_esq = tk.Frame(self, bg=THEME["bg"], width=320)
        self._frame_esq.pack(side="left", fill="y", padx=(16, 8), pady=16)
        self._frame_esq.pack_propagate(False)

        self._frame_dir = tk.Frame(self, bg=THEME["bg_card"])
        self._frame_dir.pack(side="left", fill="both", expand=True, padx=(0, 16), pady=16)

        self._build_lista()
        self._build_permissoes()

    def _build_lista(self):
        barra = tk.Frame(self._frame_esq, bg=THEME["bg"])
        barra.pack(fill="x", pady=(0, 8))

        tk.Label(barra, text="Perfis", font=FONT["bold"],
                 bg=THEME["bg"], fg=THEME["fg"]).pack(side="left")

        tk.Button(barra, text="+", font=FONT["bold"],
                  bg=THEME["primary"], fg="white", relief="flat",
                  cursor="hand2", padx=10, pady=3,
                  command=self._novo_perfil).pack(side="right")

        self._tabela = Tabela(self._frame_esq, colunas=[
            ("Nome", 180), ("Descrição", 120)
        ])
        self._tabela.pack(fill="both", expand=True)
        self._tabela.ao_selecionar = self._on_selecionar

    def _build_permissoes(self):
        header = tk.Frame(self._frame_dir, bg=THEME["bg_card"], padx=20, pady=14)
        header.pack(fill="x")

        self._lbl_perfil = tk.Label(header, text="Selecione um perfil",
                                     font=FONT["bold"], bg=THEME["bg_card"], fg=THEME["fg"])
        self._lbl_perfil.pack(side="left")

        tk.Button(header, text="💾  Salvar Permissões", font=FONT["bold"],
                  bg=THEME["success"], fg="white", relief="flat",
                  cursor="hand2", padx=12, pady=5,
                  command=self._salvar_permissoes).pack(side="right")

        tk.Button(header, text="🗑  Excluir Perfil", font=FONT["sm"],
                  bg=THEME["bg_card"], fg=THEME["danger"], relief="flat",
                  cursor="hand2", padx=10, pady=5,
                  command=self._excluir_perfil).pack(side="right", padx=(0, 8))

        tk.Frame(self._frame_dir, bg=THEME["border"], height=1).pack(fill="x")

        # Área de checkboxes com scroll
        canvas = tk.Canvas(self._frame_dir, bg=THEME["bg_card"], highlightthickness=0)
        scroll = tk.Scrollbar(self._frame_dir, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scroll.set)

        scroll.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        self._frame_checks = tk.Frame(canvas, bg=THEME["bg_card"])
        canvas.create_window((0, 0), window=self._frame_checks, anchor="nw")
        self._frame_checks.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        self._build_checks()

    def _build_checks(self):
        self._checks.clear()
        for widget in self._frame_checks.winfo_children():
            widget.destroy()

        for modulo, acoes in PERMISSOES.items():
            bloco = tk.Frame(self._frame_checks, bg=THEME["bg_card"], padx=20, pady=10)
            bloco.pack(fill="x")

            tk.Label(bloco, text=modulo.upper(), font=FONT["bold"],
                     bg=THEME["bg_card"], fg=THEME["primary"]).pack(anchor="w")

            row = tk.Frame(bloco, bg=THEME["bg_card"])
            row.pack(anchor="w", pady=(4, 0))

            for acao in acoes:
                chave = f"{modulo}:{acao}"
                var   = tk.BooleanVar(value=False)
                self._checks[chave] = var
                tk.Checkbutton(row, text=acao, variable=var,
                               font=FONT["sm"], bg=THEME["bg_card"],
                               fg=THEME["fg"], activebackground=THEME["bg_card"],
                               cursor="hand2").pack(side="left", padx=(0, 12))

            tk.Frame(self._frame_checks, bg=THEME["border"], height=1).pack(fill="x", padx=20)

    def _carregar(self):
        self._tabela.limpar()
        self._perfil_id = None
        from models.perfil import Perfil
        for p in Perfil.listar():
            self._tabela.inserir([p["nome"], p.get("descricao") or ""])

    def _on_selecionar(self, dados: list):
        nome = dados[0]
        from models.perfil import Perfil
        perfis = Perfil.listar()
        perfil = next((p for p in perfis if p["nome"] == nome), None)
        if not perfil:
            return

        self._perfil_id = perfil["id"]
        self._lbl_perfil.configure(text=f"Permissões — {perfil['nome']}")

        perms = Perfil.buscar_permissoes(perfil["id"])
        for chave, var in self._checks.items():
            var.set(perms.get(chave, False))

    def _salvar_permissoes(self):
        if not self._perfil_id:
            messagebox.showwarning("Atenção", "Selecione um perfil.", parent=self)
            return
        permissoes = {chave: var.get() for chave, var in self._checks.items()}
        from models.perfil import Perfil
        Perfil.salvar_permissoes(self._perfil_id, permissoes)
        messagebox.showinfo("Sucesso", "Permissões salvas!", parent=self)

    def _novo_perfil(self):
        from views.admin.form_perfil import FormPerfil
        FormPerfil(self, self._carregar)

    def _excluir_perfil(self):
        if not self._perfil_id:
            messagebox.showwarning("Atenção", "Selecione um perfil.", parent=self)
            return
        from models.perfil import Perfil
        if Perfil.em_uso(self._perfil_id):
            messagebox.showerror("Erro", "Este perfil está em uso por usuários ativos.", parent=self)
            return
        if messagebox.askyesno("Confirmar", "Excluir este perfil?", parent=self):
            Perfil.desativar(self._perfil_id)
            self._perfil_id = None
            self._lbl_perfil.configure(text="Selecione um perfil")
            self._carregar()