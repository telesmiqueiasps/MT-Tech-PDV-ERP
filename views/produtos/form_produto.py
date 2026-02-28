import tkinter as tk
from tkinter import ttk, messagebox
from config import THEME, FONT
from views.base_view import BaseView
from views.widgets.widgets import SecaoForm, CampoEntry, botao
from views.widgets.search_entry import SearchEntry

UNIDADES = ["UN", "KG", "G", "L", "ML", "CX", "PC", "MT", "M2", "M3", "PAR", "DZ"]


class FormProduto(BaseView):
    def __init__(self, master, produto_id: int | None, ao_salvar=None):
        titulo = "Editar Produto" if produto_id else "Novo Produto"
        super().__init__(master, titulo, 620, 820, modal=True)
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
        def _scroll(e): canvas.yview_scroll(int(-1*(e.delta/120)), "units")
        canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", _scroll))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

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

        # ── DADOS FISCAIS ────────────────────────────────────────
        SecaoForm(body, "DADOS FISCAIS").pack(fill="x", padx=P, pady=(8, 0))

        card4 = tk.Frame(body, bg=THEME["bg_card"],
                         highlightthickness=1,
                         highlightbackground=THEME["border"])
        card4.pack(fill="x", padx=P, pady=(0, 4))
        inner4 = tk.Frame(card4, bg=THEME["bg_card"], padx=16, pady=14)
        inner4.pack(fill="x")

        # CEST + Origem
        row_co = tk.Frame(inner4, bg=THEME["bg_card"])
        row_co.pack(fill="x", pady=(0, 10))
        self._var_cest = tk.StringVar()
        CampoEntry(row_co, "CEST", self._var_cest).pack(
            side="left", fill="x", expand=True, padx=(0, 8))
        col_orig = tk.Frame(row_co, bg=THEME["bg_card"])
        col_orig.pack(side="left", fill="x", expand=True, padx=(8, 0))
        tk.Label(col_orig, text="Origem", font=FONT["sm"],
                 bg=THEME["bg_card"], fg=THEME["fg"]).pack(anchor="w", pady=(0, 3))
        self._var_origem = tk.StringVar(value="0 — Nacional")
        ttk.Combobox(col_orig, textvariable=self._var_origem, state="readonly",
                     values=["0 — Nacional",
                             "1 — Estrangeira (import. direta)",
                             "2 — Estrangeira (adquirida merc. interno)",
                             "3 — Nacional c/ >40% conteúdo estrangeiro",
                             "4 — Nacional — processo produtivo básico",
                             "5 — Nacional c/ ≤40% conteúdo estrangeiro",
                             "6 — Estrangeira — import. direta s/ similar",
                             "7 — Estrangeira — adquirida s/ similar",
                             "8 — Nacional — Rec. Básico p/ exportação"],
                     font=FONT["md"]).pack(fill="x", ipady=4)

        # Botão sugerir + label info
        btn_row = tk.Frame(inner4, bg=THEME["bg_card"])
        btn_row.pack(fill="x", pady=(0, 8))
        botao(btn_row, "✨ Sugerir Tributação", tipo="secundario",
              command=self._sugerir_tributacao).pack(side="left")
        self._lbl_sugestao = tk.Label(
            btn_row, text="", font=("TkDefaultFont", 8),
            bg=THEME["bg_card"], fg="#0077cc")
        self._lbl_sugestao.pack(side="left", padx=8)

        # CFOP padrão (SearchEntry)
        tk.Label(inner4, text="CFOP Padrão",
                 font=FONT["sm"], bg=THEME["bg_card"],
                 fg=THEME["fg"]).pack(anchor="w", pady=(0, 3))
        self._cfops_data = []
        self._var_cfop_padrao = tk.StringVar()
        self._se_cfop = SearchEntry(
            inner4,
            placeholder="Buscar CFOP...",
            key_display=lambda d: d["label"],
            key_search=lambda d: d["label"],
            ao_selecionar=lambda d: self._var_cfop_padrao.set(d["codigo"]),
        )
        self._se_cfop.pack(fill="x", pady=(0, 2))
        tk.Label(inner4, textvariable=self._var_cfop_padrao,
                 font=("Consolas", 8), bg=THEME["bg_card"],
                 fg=THEME["fg_light"]).pack(anchor="e", pady=(0, 8))

        # CST ICMS / CSOSN (SearchEntry)
        tk.Label(inner4, text="CST / CSOSN ICMS",
                 font=FONT["sm"], bg=THEME["bg_card"],
                 fg=THEME["fg"]).pack(anchor="w", pady=(0, 3))
        self._cst_icms_data = []
        self._var_cst_icms = tk.StringVar()
        self._se_cst = SearchEntry(
            inner4,
            placeholder="Buscar CST ICMS...",
            key_display=lambda d: d["label"],
            key_search=lambda d: d["label"],
            ao_selecionar=lambda d: self._var_cst_icms.set(d["codigo"]),
        )
        self._se_cst.pack(fill="x", pady=(0, 8))

        # Alíquotas ICMS / IPI na mesma linha
        row_aliq1 = tk.Frame(inner4, bg=THEME["bg_card"])
        row_aliq1.pack(fill="x", pady=(0, 8))
        self._var_aliq_icms = tk.StringVar(value="0.00")
        self._var_aliq_ipi  = tk.StringVar(value="0.00")
        CampoEntry(row_aliq1, "Alíq. ICMS %", self._var_aliq_icms,
                   justify="right").pack(side="left", fill="x", expand=True, padx=(0, 8))
        CampoEntry(row_aliq1, "Alíq. IPI %", self._var_aliq_ipi,
                   justify="right").pack(side="left", fill="x", expand=True)

        # CST PIS (SearchEntry) + alíquota
        tk.Label(inner4, text="CST PIS",
                 font=FONT["sm"], bg=THEME["bg_card"],
                 fg=THEME["fg"]).pack(anchor="w", pady=(0, 3))
        self._cst_pisc_data = []
        self._var_cst_pis = tk.StringVar(value="07")
        self._se_cst_pis = SearchEntry(
            inner4,
            placeholder="Buscar CST PIS...",
            key_display=lambda d: d["label"],
            key_search=lambda d: d["label"],
            ao_selecionar=lambda d: self._var_cst_pis.set(d["codigo"]),
        )
        self._se_cst_pis.pack(fill="x", pady=(0, 2))

        # CST COFINS (SearchEntry) + alíquota
        tk.Label(inner4, text="CST COFINS",
                 font=FONT["sm"], bg=THEME["bg_card"],
                 fg=THEME["fg"]).pack(anchor="w", pady=(0, 3))
        self._var_cst_cofins = tk.StringVar(value="07")
        self._se_cst_cof = SearchEntry(
            inner4,
            placeholder="Buscar CST COFINS...",
            key_display=lambda d: d["label"],
            key_search=lambda d: d["label"],
            ao_selecionar=lambda d: self._var_cst_cofins.set(d["codigo"]),
        )
        self._se_cst_cof.pack(fill="x", pady=(0, 8))

        # Alíquotas PIS / COFINS
        row_aliq2 = tk.Frame(inner4, bg=THEME["bg_card"])
        row_aliq2.pack(fill="x", pady=(0, 4))
        self._var_aliq_pis    = tk.StringVar(value="0.65")
        self._var_aliq_cofins = tk.StringVar(value="3.00")
        CampoEntry(row_aliq2, "Alíq. PIS %", self._var_aliq_pis,
                   justify="right").pack(side="left", fill="x", expand=True, padx=(0, 8))
        CampoEntry(row_aliq2, "Alíq. COFINS %", self._var_aliq_cofins,
                   justify="right").pack(side="left", fill="x", expand=True)

        self._carregar_dados_fiscais()

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

    def _carregar_dados_fiscais(self):
        """Carrega CFOPs, CSTs e PIS/COFINS do banco no SearchEntry."""
        from models.fiscal_config import FiscalConfig
        try:
            self._cfops_data = FiscalConfig.listar_cfop()
            cfop_items = [{"codigo": c["codigo"],
                           "label": f"{c['codigo']} — {c['descricao'][:55]}"}
                          for c in self._cfops_data]
            self._se_cfop.set_items(cfop_items)

            self._cst_icms_data = FiscalConfig.listar_cst_icms()
            cst_items = [{"codigo": c["codigo"],
                          "label": f"{c['codigo']} — {c['descricao'][:50]}  "
                                   f"[{'SN' if c.get('regime')=='S' else 'RN'}]"}
                         for c in self._cst_icms_data]
            self._se_cst.set_items(cst_items)

            self._cst_pisc_data = FiscalConfig.listar_cst_pis_cofins()
            pisc_items = [{"codigo": c["codigo"],
                           "label": f"{c['codigo']} — {c['descricao'][:50]}"}
                          for c in self._cst_pisc_data]
            self._se_cst_pis.set_items(pisc_items)
            self._se_cst_cof.set_items(pisc_items)
        except Exception:
            pass  # banco fiscal não inicializado ainda — campos ficam editáveis

    def _sugerir_tributacao(self):
        """
        Busca a melhor regra fiscal do banco para sugerir
        CFOP, CST e alíquotas automaticamente.
        Usa NCM digitado como ponto de partida, depois fallback
        para a regra padrão de SAIDA intraestadual.
        """
        from models.fiscal_config import FiscalConfig
        try:
            # Tenta a regra padrão de SAIDA intraestadual
            regra = FiscalConfig.regra_para("SAIDA", "A")
            if not regra:
                messagebox.showinfo(
                    "Sem regras cadastradas",
                    "Não há regras fiscais configuradas.\n\n"
                    "Acesse Configurações Fiscais → Regras para criar regras padrão.",
                    parent=self
                )
                return

            aplicados = []

            # CFOP
            if regra.get("cfop_codigo"):
                self._var_cfop_padrao.set(regra["cfop_codigo"])
                for ci in self._se_cfop._items:
                    if ci["codigo"] == regra["cfop_codigo"]:
                        self._se_cfop.set_item(ci)
                        break
                aplicados.append(f"CFOP {regra['cfop_codigo']}")

            # CST ICMS
            if regra.get("cst_icms_codigo"):
                self._var_cst_icms.set(regra["cst_icms_codigo"])
                for ci in self._se_cst._items:
                    if ci["codigo"] == regra["cst_icms_codigo"]:
                        self._se_cst.set_item(ci)
                        break
                aplicados.append(f"CST {regra['cst_icms_codigo']}")

            # Alíquotas
            if regra.get("aliq_icms"):
                self._var_aliq_icms.set(f"{regra['aliq_icms']:.2f}")
                aplicados.append(f"ICMS {regra['aliq_icms']:.2f}%")
            if regra.get("cst_pis_cod"):
                self._var_cst_pis.set(regra["cst_pis_cod"])
                for pi in self._se_cst_pis._items:
                    if pi["codigo"] == regra["cst_pis_cod"]:
                        self._se_cst_pis.set_item(pi)
                        break
            if regra.get("aliq_pis"):
                self._var_aliq_pis.set(f"{regra['aliq_pis']:.2f}")
                aplicados.append(f"PIS {regra['aliq_pis']:.2f}%")
            if regra.get("cst_cofins_cod"):
                self._var_cst_cofins.set(regra["cst_cofins_cod"])
                for ci in self._se_cst_cof._items:
                    if ci["codigo"] == regra["cst_cofins_cod"]:
                        self._se_cst_cof.set_item(ci)
                        break
            if regra.get("aliq_cofins"):
                self._var_aliq_cofins.set(f"{regra['aliq_cofins']:.2f}")
                aplicados.append(f"COFINS {regra['aliq_cofins']:.2f}%")

            if aplicados:
                self._lbl_sugestao.configure(
                    text="Regra aplicada: " + regra.get("nome","") + " | " + " | ".join(aplicados),
                    fg="#1a7a3a"
                )
            else:
                self._lbl_sugestao.configure(
                    text="Regra encontrada, mas sem valores configurados.",
                    fg="#aa6600"
                )
        except Exception as e:
            self._lbl_sugestao.configure(
                text=f"Erro ao buscar regras: {e}", fg=THEME.get("danger", "red")
            )

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

        # ── Dados fiscais ────────────────────────────────────────
        self._var_cest.set(p.get("cest") or "")

        # Origem
        orig_num = int(p.get("origem") or 0)
        orig_vals = [
            "0 — Nacional", "1 — Estrangeira (import. direta)",
            "2 — Estrangeira (adquirida merc. interno)",
            "3 — Nacional c/ >40% conteúdo estrangeiro",
            "4 — Nacional — processo produtivo básico",
            "5 — Nacional c/ ≤40% conteúdo estrangeiro",
            "6 — Estrangeira — import. direta s/ similar",
            "7 — Estrangeira — adquirida s/ similar",
            "8 — Nacional — Rec. Básico p/ exportação",
        ]
        if 0 <= orig_num < len(orig_vals):
            self._var_origem.set(orig_vals[orig_num])

        # CFOP padrão
        cfop_cod = p.get("cfop_padrao") or ""
        self._var_cfop_padrao.set(cfop_cod)
        if cfop_cod:
            for ci in self._se_cfop._items:
                if ci["codigo"] == cfop_cod:
                    self._se_cfop.set_item(ci); break

        # CST ICMS / CSOSN
        cst_cod = p.get("cst_icms") or p.get("csosn") or ""
        self._var_cst_icms.set(cst_cod)
        if cst_cod:
            for ci in self._se_cst._items:
                if ci["codigo"] == cst_cod:
                    self._se_cst.set_item(ci); break

        # Alíquotas
        self._var_aliq_icms.set(f"{float(p.get('aliq_icms') or 0):.2f}")
        self._var_aliq_ipi.set(f"{float(p.get('aliq_ipi') or 0):.2f}")
        self._var_aliq_pis.set(f"{float(p.get('aliq_pis') or 0.65):.2f}")
        self._var_aliq_cofins.set(f"{float(p.get('aliq_cofins') or 3.00):.2f}")

        # CST PIS
        cst_pis = p.get("cst_pis") or "07"
        self._var_cst_pis.set(cst_pis)
        for pi in self._se_cst_pis._items:
            if pi["codigo"] == cst_pis:
                self._se_cst_pis.set_item(pi); break

        # CST COFINS
        cst_cof = p.get("cst_cofins") or "07"
        self._var_cst_cofins.set(cst_cof)
        for ci in self._se_cst_cof._items:
            if ci["codigo"] == cst_cof:
                self._se_cst_cof.set_item(ci); break

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

        def _sf(var):
            try: return float(var.get().replace(",", "."))
            except: return 0.0

        # Origem: pega só o número inicial
        orig_raw = self._var_origem.get()
        orig_num = int(orig_raw[0]) if orig_raw and orig_raw[0].isdigit() else 0

        dados = {
            "codigo":        self._var_codigo.get(),
            "codigo_barras": self._var_codigo_barras.get().strip(),
            "ncm":           self._var_ncm.get().strip(),
            "cest":          self._var_cest.get().strip() or None,
            "unidade":       self._var_unidade.get(),
            "nome":          nome,
            "categoria_id":  cat_id,
            "preco_custo":   custo,
            "margem":        margem,
            "preco_venda":   venda,
            "estoque_min":   e_min,
            "estoque_max":   e_max,
            # Dados fiscais
            "origem":        orig_num,
            "cfop_padrao":   self._var_cfop_padrao.get().strip() or None,
            "cst_icms":      self._var_cst_icms.get().strip() or None,
            "csosn":         self._var_cst_icms.get().strip() or None,
            "aliq_icms":     _sf(self._var_aliq_icms),
            "aliq_ipi":      _sf(self._var_aliq_ipi),
            "cst_pis":       self._var_cst_pis.get().strip() or "07",
            "aliq_pis":      _sf(self._var_aliq_pis),
            "cst_cofins":    self._var_cst_cofins.get().strip() or "07",
            "aliq_cofins":   _sf(self._var_aliq_cofins),
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