import tkinter as tk
from tkinter import ttk
from config import THEME, FONT
from views.base_view import BaseView
from views.widgets.widgets import SecaoForm, CampoEntry, botao
from core.session import Session


class FormEntrada(BaseView):
    def __init__(self, master, ao_salvar=None):
        super().__init__(master, "Entrada de Estoque", 540, 580, modal=True)
        self.resizable(True, True)
        self._ao_salvar  = ao_salvar
        self._produtos   = []
        self._depositos  = []
        self._fornecedores = []
        self._build()

    def _build(self):
        canvas = tk.Canvas(self, bg=THEME["bg"], highlightthickness=0)
        scroll = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True)
        body = tk.Frame(canvas, bg=THEME["bg"])
        win  = canvas.create_window((0, 0), window=body, anchor="nw")
        body.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(win, width=e.width))
        P = 24

        tk.Label(body, text="📥  Entrada de Estoque", font=FONT["title"],
                 bg=THEME["bg"], fg=THEME["fg"]).pack(anchor="w", padx=P, pady=(20, 16))

        # ── PRODUTO E DEPÓSITO ───────────────────────────────────
        SecaoForm(body, "PRODUTO E DEPÓSITO").pack(fill="x", padx=P)
        c1 = self._card(body, P)

        tk.Label(c1, text="Produto *", font=FONT["sm"],
                 bg=THEME["bg_card"], fg=THEME["fg"]).pack(anchor="w", pady=(0, 3))
        self._var_produto = tk.StringVar()
        self._combo_prod  = ttk.Combobox(c1, textvariable=self._var_produto,
                                          state="readonly", font=FONT["md"])
        self._combo_prod.pack(fill="x", ipady=4, pady=(0, 10))

        tk.Label(c1, text="Depósito *", font=FONT["sm"],
                 bg=THEME["bg_card"], fg=THEME["fg"]).pack(anchor="w", pady=(0, 3))
        self._var_dep = tk.StringVar()
        self._combo_dep = ttk.Combobox(c1, textvariable=self._var_dep,
                                        state="readonly", font=FONT["md"])
        self._combo_dep.pack(fill="x", ipady=4)

        # ── QUANTIDADE E CUSTO ───────────────────────────────────
        SecaoForm(body, "QUANTIDADE E CUSTO").pack(fill="x", padx=P, pady=(8, 0))
        c2 = self._card(body, P)

        row1 = tk.Frame(c2, bg=THEME["bg_card"])
        row1.pack(fill="x", pady=(0, 10))
        self._var_qtd   = tk.StringVar(value="1")
        self._var_custo = tk.StringVar(value="0.00")
        CampoEntry(row1, "Quantidade *", self._var_qtd,
                   justify="right").pack(side="left", fill="x", expand=True, padx=(0, 8))
        CampoEntry(row1, "Custo Unitário (R$) *", self._var_custo,
                   justify="right").pack(side="left", fill="x", expand=True, padx=(8, 0))

        # Total calculado
        self._lbl_total = tk.Label(c2, text="Total: R$ 0,00",
                                    font=FONT["bold"], bg=THEME["bg_card"],
                                    fg=THEME["primary"])
        self._lbl_total.pack(anchor="e", pady=(0, 4))
        self._var_qtd.trace_add("write",   self._atualizar_total)
        self._var_custo.trace_add("write", self._atualizar_total)

        # ── NOTA FISCAL E FORNECEDOR ─────────────────────────────
        SecaoForm(body, "NOTA FISCAL E FORNECEDOR").pack(fill="x", padx=P, pady=(8, 0))
        c3 = self._card(body, P)

        row2 = tk.Frame(c3, bg=THEME["bg_card"])
        row2.pack(fill="x", pady=(0, 10))
        self._var_nf = tk.StringVar()
        CampoEntry(row2, "Número da NF", self._var_nf).pack(
            side="left", fill="x", expand=True, padx=(0, 8))

        col_forn = tk.Frame(row2, bg=THEME["bg_card"])
        col_forn.pack(side="left", fill="x", expand=True, padx=(8, 0))
        tk.Label(col_forn, text="Fornecedor", font=FONT["sm"],
                 bg=THEME["bg_card"], fg=THEME["fg"]).pack(anchor="w", pady=(0, 3))
        self._var_forn = tk.StringVar()
        self._combo_forn = ttk.Combobox(col_forn, textvariable=self._var_forn,
                                         state="readonly", font=FONT["md"])
        self._combo_forn.pack(fill="x", ipady=4)

        self._var_motivo = tk.StringVar()
        CampoEntry(c3, "Observação / Motivo", self._var_motivo).pack(fill="x", pady=(0, 4))

        # Erro e botão
        self._carregar_combos()

        self._var_erro = tk.StringVar()
        tk.Label(body, textvariable=self._var_erro, font=FONT["sm"],
                 bg=THEME["bg"], fg=THEME["danger"]).pack(anchor="w", padx=P, pady=(8, 0))
        botao(body, "💾  Confirmar Entrada", tipo="sucesso",
              command=self._salvar).pack(fill="x", padx=P, pady=(8, 24))

    def _card(self, parent, P):
        frame = tk.Frame(parent, bg=THEME["bg_card"], highlightthickness=1,
                         highlightbackground=THEME["border"])
        frame.pack(fill="x", padx=P, pady=(0, 4))
        inner = tk.Frame(frame, bg=THEME["bg_card"], padx=16, pady=14)
        inner.pack(fill="x")
        return inner

    def _carregar_combos(self):
        from models.produto import Produto
        from models.estoque import Deposito
        from models.fornecedor import Fornecedor

        self._produtos   = Produto.listar()
        self._depositos  = Deposito.listar()
        self._fornecedores = Fornecedor.listar()

        self._combo_prod["values"]  = [f"{p['nome']} ({p.get('codigo') or '—'})"
                                        for p in self._produtos]
        self._combo_dep["values"]   = [d["nome"] for d in self._depositos]
        self._combo_forn["values"]  = ["(nenhum)"] + [f["nome"] for f in self._fornecedores]

        if self._depositos:  self._combo_dep.current(0)
        if True:             self._combo_forn.current(0)

    def _atualizar_total(self, *_):
        try:
            qtd   = float(self._var_qtd.get().replace(",", "."))
            custo = float(self._var_custo.get().replace(",", "."))
            self._lbl_total.configure(text=f"Total: R$ {qtd*custo:,.2f}")
        except ValueError:
            self._lbl_total.configure(text="Total: —")

    def _salvar(self):
        idx_prod = self._combo_prod.current()
        idx_dep  = self._combo_dep.current()
        if idx_prod < 0:
            self._var_erro.set("Selecione um produto."); return
        if idx_dep < 0:
            self._var_erro.set("Selecione um depósito."); return

        try:
            qtd   = float(self._var_qtd.get().replace(",", "."))
            custo = float(self._var_custo.get().replace(",", "."))
        except ValueError:
            self._var_erro.set("Quantidade ou custo inválido."); return

        if qtd <= 0:
            self._var_erro.set("Quantidade deve ser maior que zero."); return

        idx_forn   = self._combo_forn.current()
        forn_id    = self._fornecedores[idx_forn-1]["id"] if idx_forn > 0 else None

        from models.estoque import Estoque
        try:
            Estoque.entrada(
                produto_id    = self._produtos[idx_prod]["id"],
                deposito_id   = self._depositos[idx_dep]["id"],
                quantidade    = qtd,
                custo_unitario= custo,
                fornecedor_id = forn_id,
                numero_nf     = self._var_nf.get().strip() or None,
                motivo        = self._var_motivo.get().strip() or None,
                usuario_id    = Session.usuario_id(),
                usuario_nome  = Session.nome(),
            )
        except ValueError as e:
            self._var_erro.set(str(e)); return

        if self._ao_salvar: self._ao_salvar()
        self.destroy()