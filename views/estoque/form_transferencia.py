import tkinter as tk
from tkinter import ttk
from config import THEME, FONT
from views.base_view import BaseView
from views.widgets.widgets import SecaoForm, CampoEntry, botao
from core.session import Session


class FormTransferencia(BaseView):
    def __init__(self, master, sel=None, ao_salvar=None):
        super().__init__(master, "Transferência entre Depósitos", 480, 420, modal=True)
        self.resizable(True, True)
        self._ao_salvar = ao_salvar
        self._produtos  = []
        self._depositos = []
        self._build()
        if sel: self._pre_preencher(sel)

    def _build(self):
        P = 24
        tk.Label(self, text="🔀  Transferência de Estoque", font=FONT["title"],
                 bg=THEME["bg"], fg=THEME["fg"]).pack(anchor="w", padx=P, pady=(20, 16))

        SecaoForm(self, "PRODUTO").pack(fill="x", padx=P)
        c1 = self._card(P)
        tk.Label(c1, text="Produto *", font=FONT["sm"],
                 bg=THEME["bg_card"], fg=THEME["fg"]).pack(anchor="w", pady=(0, 3))
        self._var_produto = tk.StringVar()
        self._combo_prod  = ttk.Combobox(c1, textvariable=self._var_produto,
                                          state="readonly", font=FONT["md"])
        self._combo_prod.pack(fill="x", ipady=4)
        self._combo_prod.bind("<<ComboboxSelected>>", self._atualizar_saldo)

        SecaoForm(self, "DEPÓSITOS").pack(fill="x", padx=P, pady=(8, 0))
        c2 = self._card(P)

        row = tk.Frame(c2, bg=THEME["bg_card"])
        row.pack(fill="x", pady=(0, 10))

        col_orig = tk.Frame(row, bg=THEME["bg_card"])
        col_orig.pack(side="left", fill="x", expand=True, padx=(0, 8))
        tk.Label(col_orig, text="Origem *", font=FONT["sm"],
                 bg=THEME["bg_card"], fg=THEME["fg"]).pack(anchor="w", pady=(0, 3))
        self._var_orig = tk.StringVar()
        self._combo_orig = ttk.Combobox(col_orig, textvariable=self._var_orig,
                                         state="readonly", font=FONT["md"])
        self._combo_orig.pack(fill="x", ipady=4)
        self._combo_orig.bind("<<ComboboxSelected>>", self._atualizar_saldo)

        col_dest = tk.Frame(row, bg=THEME["bg_card"])
        col_dest.pack(side="left", fill="x", expand=True, padx=(8, 0))
        tk.Label(col_dest, text="Destino *", font=FONT["sm"],
                 bg=THEME["bg_card"], fg=THEME["fg"]).pack(anchor="w", pady=(0, 3))
        self._var_dest = tk.StringVar()
        self._combo_dest = ttk.Combobox(col_dest, textvariable=self._var_dest,
                                         state="readonly", font=FONT["md"])
        self._combo_dest.pack(fill="x", ipady=4)

        self._lbl_saldo = tk.Label(c2, text="", font=FONT["sm"],
                                    bg=THEME["bg_card"], fg=THEME["fg_light"])
        self._lbl_saldo.pack(anchor="e")

        SecaoForm(self, "QUANTIDADE").pack(fill="x", padx=P, pady=(8, 0))
        c3 = self._card(P)
        self._var_qtd    = tk.StringVar(value="1")
        self._var_motivo = tk.StringVar()
        CampoEntry(c3, "Quantidade *", self._var_qtd, justify="right").pack(
            fill="x", pady=(0, 10))
        CampoEntry(c3, "Observação", self._var_motivo).pack(fill="x")

        self._var_erro = tk.StringVar()
        tk.Label(self, textvariable=self._var_erro, font=FONT["sm"],
                 bg=THEME["bg"], fg=THEME["danger"]).pack(anchor="w", padx=P, pady=(8, 0))
        botao(self, "💾  Confirmar Transferência", tipo="secundario",
              command=self._salvar).pack(fill="x", padx=P, pady=(8, 20))

        self._carregar_combos()

    def _card(self, P):
        frame = tk.Frame(self, bg=THEME["bg_card"], highlightthickness=1,
                         highlightbackground=THEME["border"])
        frame.pack(fill="x", padx=P, pady=(0, 4))
        inner = tk.Frame(frame, bg=THEME["bg_card"], padx=16, pady=14)
        inner.pack(fill="x")
        return inner

    def _carregar_combos(self):
        from models.produto import Produto
        from models.estoque import Deposito
        self._produtos  = Produto.listar()
        self._depositos = Deposito.listar()
        nomes_dep = [d["nome"] for d in self._depositos]
        self._combo_prod["values"] = [f"{p['nome']} ({p.get('codigo') or '—'})"
                                       for p in self._produtos]
        self._combo_orig["values"] = nomes_dep
        self._combo_dest["values"] = nomes_dep
        if self._depositos:
            self._combo_orig.current(0)
            self._combo_dest.current(min(1, len(self._depositos)-1))

    def _pre_preencher(self, sel):
        nome_prod = sel[1] if len(sel) > 1 else ""
        nome_dep  = sel[3] if len(sel) > 3 else ""
        for i, p in enumerate(self._produtos):
            if p["nome"] == nome_prod: self._combo_prod.current(i); break
        for i, d in enumerate(self._depositos):
            if d["nome"] == nome_dep: self._combo_orig.current(i); break
        self._atualizar_saldo()

    def _atualizar_saldo(self, _=None):
        ip = self._combo_prod.current()
        io = self._combo_orig.current()
        if ip < 0 or io < 0: return
        from models.estoque import Estoque
        saldo = Estoque.saldo(self._produtos[ip]["id"], self._depositos[io]["id"])
        self._lbl_saldo.configure(
            text=f"Saldo em '{self._depositos[io]['nome']}': {saldo:g}")

    def _salvar(self):
        ip = self._combo_prod.current()
        io = self._combo_orig.current()
        id_ = self._combo_dest.current()
        if ip < 0:  self._var_erro.set("Selecione um produto."); return
        if io < 0:  self._var_erro.set("Selecione o depósito de origem."); return
        if id_ < 0: self._var_erro.set("Selecione o depósito de destino."); return
        try:
            qtd = float(self._var_qtd.get().replace(",", "."))
        except ValueError:
            self._var_erro.set("Quantidade inválida."); return

        from models.estoque import Estoque
        try:
            Estoque.transferencia(
                produto_id    = self._produtos[ip]["id"],
                deposito_orig = self._depositos[io]["id"],
                deposito_dest = self._depositos[id_]["id"],
                quantidade    = qtd,
                motivo        = self._var_motivo.get().strip() or None,
                usuario_id    = Session.usuario_id(),
                usuario_nome  = Session.nome(),
            )
        except ValueError as e:
            self._var_erro.set(str(e)); return

        if self._ao_salvar: self._ao_salvar()
        self.destroy()