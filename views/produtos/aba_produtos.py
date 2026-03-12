import tkinter as tk
from tkinter import messagebox, ttk
from config import THEME, FONT
from views.widgets.tabela import Tabela
from views.widgets.widgets import botao


class AbaProdutos(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg=THEME["bg"])
        self._build()
        self._carregar()

    def _build(self):
        # Barra de ferramentas
        toolbar = tk.Frame(self, bg=THEME["bg_card"],
                           highlightthickness=1,
                           highlightbackground=THEME["border"],
                           padx=14, pady=10)
        toolbar.pack(fill="x", pady=(0, 1))

        # Busca
        busca_frame = tk.Frame(toolbar, bg=THEME["bg_card"])
        busca_frame.pack(side="left")
        tk.Label(busca_frame, text="🔍", font=("Segoe UI", 11),
                 bg=THEME["bg_card"], fg=THEME["fg_light"]).pack(side="left", padx=(0, 4))
        self._var_busca = tk.StringVar()
        self._var_busca.trace_add("write", lambda *_: self._carregar())
        tk.Entry(busca_frame, textvariable=self._var_busca, font=FONT["md"],
                 relief="flat", bg=THEME["bg"], fg=THEME["fg"],
                 highlightthickness=1,
                 highlightbackground=THEME["border"],
                 highlightcolor=THEME["primary"],
                 width=24).pack(side="left", ipady=5)

        # Separador
        tk.Frame(toolbar, bg=THEME["border"], width=1).pack(
            side="left", fill="y", padx=14)

        # Filtro categoria
        tk.Label(toolbar, text="Categoria:", font=FONT["sm"],
                 bg=THEME["bg_card"], fg=THEME["fg_light"]).pack(side="left")
        self._var_cat = tk.StringVar()
        self._combo_cat = ttk.Combobox(toolbar, textvariable=self._var_cat,
                                        state="readonly", font=FONT["md"], width=20)
        self._combo_cat.pack(side="left", padx=(6, 0), ipady=3)
        self._combo_cat.bind("<<ComboboxSelected>>", lambda _: self._carregar())
        self._carregar_categorias()

        # Botões à direita
        from core.session import Session
        if Session.pode("produtos", "editar"):
            botao(toolbar, "✏  Editar", tipo="secundario",
                  command=self._editar).pack(side="right", padx=(6, 0))
        if Session.pode("produtos", "deletar"):
            botao(toolbar, "🗑  Desativar", tipo="perigo",
                  command=self._desativar).pack(side="right", padx=(6, 0))
        if Session.pode("produtos", "criar"):
            tk.Frame(toolbar, bg=THEME["border"], width=1).pack(
                side="right", fill="y", padx=6)
            botao(toolbar, "+ Novo Produto", tipo="primario",
                  command=self._novo).pack(side="right")

        # Tabela
        self._tabela = Tabela(self, colunas=[
            ("ID",        48),
            ("Código",   100),
            ("Nome",     280),
            ("Categoria",150),
            ("Unid.",     60),
            ("Custo",    110),
            ("Venda",    110),
            ("Margem %",  90),
            ("Estoque",   90),
        ])
        self._tabela.pack(fill="both", expand=True, padx=0, pady=0)
        if Session.pode("produtos", "editar"):
            self._tabela.ao_duplo_clique = lambda _: self._editar()

        # Rodapé
        rodape = tk.Frame(self, bg=THEME["bg_card"],
                          highlightthickness=1,
                          highlightbackground=THEME["border"],
                          padx=14, pady=6)
        rodape.pack(fill="x")
        self._lbl_total = tk.Label(rodape, text="", font=FONT["sm"],
                                    bg=THEME["bg_card"], fg=THEME["fg_light"])
        self._lbl_total.pack(side="right")

    def _carregar_categorias(self):
        from models.produto import Categoria
        self._categorias = Categoria.listar()
        self._combo_cat["values"] = ["Todas"] + [c["nome"] for c in self._categorias]
        self._combo_cat.current(0)

    def _categoria_id_selecionada(self) -> int | None:
        idx = self._combo_cat.current()
        return self._categorias[idx - 1]["id"] if idx > 0 else None

    def _carregar(self):
        from models.produto import Produto
        produtos = Produto.listar(self._var_busca.get().strip(),
                                   self._categoria_id_selecionada())
        self._tabela.limpar()
        for p in produtos:
            self._tabela.inserir([
                p["id"],
                p.get("codigo") or "—",
                p["nome"],
                p.get("categoria_nome") or "—",
                p.get("unidade", "UN"),
                f"R$ {p.get('preco_custo', 0):,.2f}",
                f"R$ {p.get('preco_venda', 0):,.2f}",
                f"{p.get('margem', 0):.1f}%",
                f"{p.get('estoque_atual', 0):g}",
            ])

        alerta = sum(1 for p in produtos
                     if p.get("estoque_min", 0) > 0
                     and p.get("estoque_atual", 0) <= p.get("estoque_min", 0))
        txt = f"{len(produtos)} produto(s)"
        if alerta:
            txt += f"   ⚠ {alerta} com estoque baixo"
        self._lbl_total.configure(text=txt)

    def _selecionado_id(self) -> int | None:
        sel = self._tabela.selecionado()
        return int(sel[0]) if sel else None

    def _novo(self):
        from core.session import Session
        if not Session.pode("produtos", "criar"):
            messagebox.showwarning("Sem Permissão", "Você não tem permissão para criar produtos.", parent=self); return
        from views.produtos.form_produto import FormProduto
        FormProduto(self, None, self._carregar)

    def _editar(self):
        from core.session import Session
        if not Session.pode("produtos", "editar"):
            messagebox.showwarning("Sem Permissão", "Você não tem permissão para editar produtos.", parent=self); return
        id_ = self._selecionado_id()
        if not id_:
            messagebox.showwarning("Atenção", "Selecione um produto.", parent=self)
            return
        from views.produtos.form_produto import FormProduto
        FormProduto(self, id_, self._carregar)

    def _desativar(self):
        from core.session import Session
        if not Session.pode("produtos", "deletar"):
            messagebox.showwarning("Sem Permissão", "Você não tem permissão para desativar produtos.", parent=self); return
        id_ = self._selecionado_id()
        if not id_:
            messagebox.showwarning("Atenção", "Selecione um produto.", parent=self)
            return
        if messagebox.askyesno("Confirmar", "Desativar este produto?", parent=self):
            from models.produto import Produto
            Produto.desativar(id_)
            self._carregar()