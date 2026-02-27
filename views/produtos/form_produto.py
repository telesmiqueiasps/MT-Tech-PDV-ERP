import tkinter as tk
from tkinter import ttk
from config import THEME, FONT
from views.base_view import BaseView
from views.widgets.widgets import SecaoForm, CampoEntry, botao

UNIDADES = ["UN", "KG", "G", "L", "ML", "CX", "PC", "MT", "M2", "M3", "PAR", "DZ"]


class FormProduto(BaseView):
    def __init__(self, master, produto_id: int | None, ao_salvar=None):
        titulo = "Editar Produto" if produto_id else "Novo Produto"
        super().__init__(master, titulo, 580, 680, modal=True)
        self.resizable(True, True)
        self._produto_id = produto_id
        self._ao_salvar  = ao_salvar
        self._categorias: list[dict] = []
        self._build()
        if produto_id:
            self._preencher()
        else:
            self._gerar_codigo()

    def _build(self):
        # Canvas scrollável
        canvas = tk.Canvas(self, bg=THEME["bg"], highlightthickness=0)
        scroll = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True)

        body = tk.Frame(canvas, bg=THEME["bg"])
        win  = canvas.create_window((0, 0), window=body, anchor="nw")

        body.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
            lambda e: canvas.itemconfig(win, width=e.width))
        canvas.bind_all("<MouseWheel>",
            lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

        P = 24  # padding lateral padrão

        # Título
        tk.Label(body, text="Novo Produto" if not self._produto_id else "Editar Produto",
                 font=FONT["title"], bg=THEME["bg"],
                 fg=THEME["fg"]).pack(anchor="w", padx=P, pady=(20, 16))

        # ── IDENTIFICAÇÃO ────────────────────────────────────────
        SecaoForm(body, "IDENTIFICAÇÃO").pack(fill="x", padx=P, pady=(0, 12))

        card1 = tk.Frame(body, bg=THEME["bg_card"],
                         highlightthickness=1,
                         highlightbackground=THEME["border"])
        card1.pack(fill="x", padx=P, pady=(0, 4))
        inner1 = tk.Frame(card1, bg=THEME["bg_card"], padx=16, pady=14)
        inner1.pack(fill="x")

        # Nome — linha inteira
        self._var_nome = tk.StringVar()
        CampoEntry(inner1, "Nome do Produto *", self._var_nome,
                   ).pack(fill="x", pady=(0, 10))

        # Código interno | Código de barras
        row = tk.Frame(inner1, )
        row.pack(fill="x", pady=(0, 10))
        self._var_codigo = tk.StringVar()
        CampoEntry(row, "Código Interno", self._var_codigo,
                   readonly=True, justify="center",
                   ).pack(side="left", fill="x", expand=True, padx=(0, 8))
        self._var_codigo_barras = tk.StringVar()
        CampoEntry(row, "Código de Barras", self._var_codigo_barras,
                   ).pack(side="left", fill="x", expand=True, padx=(8, 0))

        # NCM | Categoria
        row2 = tk.Frame(inner1, )
        row2.pack(fill="x", pady=(0, 10))
        self._var_ncm = tk.StringVar()
        CampoEntry(row2, "NCM", self._var_ncm,
                   ).pack(side="left", fill="x", expand=True, padx=(0, 8))

        col_cat = tk.Frame(row2, )
        col_cat.pack(side="left", fill="x", expand=True, padx=(8, 0))
        tk.Label(col_cat, text="Categoria", font=FONT["sm"],
                 bg=THEME["bg_card"], fg=THEME["fg"]).pack(anchor="w", pady=(0, 3))
        self._var_categoria = tk.StringVar()
        self._combo_cat = ttk.Combobox(col_cat, textvariable=self._var_categoria,
                                        state="readonly", font=FONT["md"])
        self._combo_cat.pack(fill="x", ipady=4)
        self._carregar_categorias()

        # Unidade
        col_und = tk.Frame(inner1, )
        col_und.pack(anchor="w", pady=(0, 4))
        tk.Label(col_und, text="Unidade *", font=FONT["sm"],
                 bg=THEME["bg_card"], fg=THEME["fg"]).pack(anchor="w", pady=(0, 3))
        self._var_unidade = tk.StringVar(value="UN")
        ttk.Combobox(col_und, textvariable=self._var_unidade, values=UNIDADES,
                     state="readonly", font=FONT["md"], width=12).pack(anchor="w", ipady=4)

        # ── PREÇOS ───────────────────────────────────────────────
        SecaoForm(body, "PREÇOS").pack(fill="x", padx=P, pady=(8, 0))

        card2 = tk.Frame(body, bg=THEME["bg_card"],
                         highlightthickness=1,
                         highlightbackground=THEME["border"])
        card2.pack(fill="x", padx=P, pady=(0, 4))
        inner2 = tk.Frame(card2, bg=THEME["bg_card"], padx=16, pady=14)
        inner2.pack(fill="x")

        row3 = tk.Frame(inner2, )
        row3.pack(fill="x", pady=(0, 10))
        self._var_preco_custo = tk.StringVar(value="0.00")
        CampoEntry(row3, "Preço de Custo (R$)", self._var_preco_custo,
                   justify="right", ).pack(
                   side="left", fill="x", expand=True, padx=(0, 8))
        self._var_margem = tk.StringVar(value="0.00")
        CampoEntry(row3, "Margem (%)", self._var_margem,
                   justify="right", ).pack(
                   side="left", fill="x", expand=True, padx=(8, 0))

        row4 = tk.Frame(inner2, )
        row4.pack(fill="x")
        self._var_preco_venda = tk.StringVar(value="0.00")
        CampoEntry(row4, "Preço de Venda (R$)", self._var_preco_venda,
                   justify="right", ).pack(
                   side="left", fill="x", expand=True, padx=(0, 8))
        tk.Frame(row4, ).pack(
                   side="left", fill="x", expand=True, padx=(8, 0))

        self._var_preco_custo.trace_add("write", self._calcular_venda)
        self._var_margem.trace_add("write",      self._calcular_venda)

        # ── ESTOQUE ──────────────────────────────────────────────
        SecaoForm(body, "ESTOQUE").pack(fill="x", padx=P, pady=(8, 0))

        card3 = tk.Frame(body, bg=THEME["bg_card"],
                         highlightthickness=1,
                         highlightbackground=THEME["border"])
        card3.pack(fill="x", padx=P, pady=(0, 4))
        inner3 = tk.Frame(card3, bg=THEME["bg_card"], padx=16, pady=14)
        inner3.pack(fill="x")

        row5 = tk.Frame(inner3, )
        row5.pack(fill="x", pady=(0, 10))

        if not self._produto_id:
            self._var_estoque_atual = tk.StringVar(value="0")
            CampoEntry(row5, "Estoque Inicial", self._var_estoque_atual,
                       justify="right", ).pack(
                       side="left", fill="x", expand=True, padx=(0, 8))
        else:
            tk.Frame(row5, ).pack(
                side="left", fill="x", expand=True, padx=(0, 8))

        self._var_estoque_min = tk.StringVar(value="0")
        CampoEntry(row5, "Estoque Mínimo", self._var_estoque_min,
                   justify="right", ).pack(
                   side="left", fill="x", expand=True, padx=(8, 0))

        row6 = tk.Frame(inner3, )
        row6.pack(fill="x")
        self._var_estoque_max = tk.StringVar(value="0")
        CampoEntry(row6, "Estoque Máximo", self._var_estoque_max,
                   justify="right", ).pack(
                   side="left", fill="x", expand=True, padx=(0, 8))
        tk.Frame(row6, ).pack(
                   side="left", fill="x", expand=True, padx=(8, 0))

        # ── Erro + botão ─────────────────────────────────────────
        self._var_erro = tk.StringVar()
        tk.Label(body, textvariable=self._var_erro, font=FONT["sm"],
                 bg=THEME["bg"], fg=THEME["danger"]).pack(
                 anchor="w", padx=P, pady=(10, 0))

        botao(body, "💾  Salvar Produto", tipo="primario",
              command=self._salvar).pack(fill="x", padx=P, pady=(8, 24))

    def _gerar_codigo(self):
        from models.produto import Produto
        self._var_codigo.set(Produto.proximo_codigo())

    def _carregar_categorias(self):
        from models.produto import Categoria
        self._categorias = Categoria.listar()
        self._combo_cat["values"] = ["(sem categoria)"] + [c["nome"] for c in self._categorias]
        self._combo_cat.current(0)

    def _calcular_venda(self, *_):
        try:
            custo  = float(self._var_preco_custo.get().replace(",", "."))
            margem = float(self._var_margem.get().replace(",", "."))
            self._var_preco_venda.set(f"{custo * (1 + margem / 100):.2f}")
        except (ValueError, AttributeError):
            pass

    def _preencher(self):
        from models.produto import Produto
        p = Produto.buscar_por_id(self._produto_id)
        if not p:
            return
        self._var_nome.set(p.get("nome", ""))
        self._var_codigo.set(p.get("codigo") or "")
        self._var_codigo_barras.set(p.get("codigo_barras") or "")
        self._var_ncm.set(p.get("ncm") or "")
        self._var_unidade.set(p.get("unidade", "UN"))
        self._var_preco_custo.set(f"{p.get('preco_custo', 0):.2f}")
        self._var_margem.set(f"{p.get('margem', 0):.2f}")
        self._var_preco_venda.set(f"{p.get('preco_venda', 0):.2f}")
        self._var_estoque_min.set(f"{p.get('estoque_min', 0):.3f}")
        self._var_estoque_max.set(f"{p.get('estoque_max', 0):.3f}")
        cat_id = p.get("categoria_id")
        if cat_id:
            for i, c in enumerate(self._categorias):
                if c["id"] == cat_id:
                    self._combo_cat.current(i + 1)
                    break

    def _to_float(self, var: tk.StringVar, campo: str) -> float | None:
        try:
            return float(var.get().replace(",", "."))
        except ValueError:
            self._var_erro.set(f"Valor inválido em '{campo}'.")
            return None

    def _salvar(self):
        nome = self._var_nome.get().strip()
        if not nome:
            self._var_erro.set("O nome do produto é obrigatório.")
            return

        custo  = self._to_float(self._var_preco_custo, "Preço de Custo")
        margem = self._to_float(self._var_margem,      "Margem")
        venda  = self._to_float(self._var_preco_venda, "Preço de Venda")
        e_min  = self._to_float(self._var_estoque_min, "Estoque Mínimo")
        e_max  = self._to_float(self._var_estoque_max, "Estoque Máximo")
        if None in (custo, margem, venda, e_min, e_max):
            return

        idx_cat = self._combo_cat.current()
        cat_id  = self._categorias[idx_cat - 1]["id"] if idx_cat > 0 else None

        dados = {
            "codigo":        self._var_codigo.get(),
            "codigo_barras": self._var_codigo_barras.get().strip(),
            "ncm":           self._var_ncm.get().strip(),
            "unidade":       self._var_unidade.get(),
            "nome":          nome,
            "categoria_id":  cat_id,
            "preco_custo":   custo,
            "margem":        margem,
            "preco_venda":   venda,
            "estoque_min":   e_min,
            "estoque_max":   e_max,
        }

        from models.produto import Produto
        if self._produto_id:
            Produto.atualizar(self._produto_id, dados)
        else:
            e_ini = self._to_float(self._var_estoque_atual, "Estoque Inicial")
            if e_ini is None:
                return
            dados["estoque_atual"] = e_ini
            Produto.criar(dados)

        if self._ao_salvar:
            self._ao_salvar()
        self.destroy()