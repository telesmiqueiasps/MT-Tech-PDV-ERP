import tkinter as tk
from tkinter import ttk
from config import THEME, FONT
from views.base_view import BaseView
from views.widgets.widgets import SecaoForm, CampoEntry, botao
from core.session import Session

MOTIVOS = ["Consumo interno", "Perda / Avaria", "Devolução ao fornecedor",
           "Amostra / Brinde", "Vencimento", "Outro"]


class FormSaida(BaseView):
    def __init__(self, master, sel=None, ao_salvar=None):
        super().__init__(master, "Saída de Estoque", 480, 440, modal=True)
        self.resizable(True, True)
        self._ao_salvar = ao_salvar
        self._produtos  = []
        self._depositos = []
        self._build()
        if sel:
            self._pre_preencher(sel)

    def _build(self):
        P = 24
        tk.Label(self, text="📤  Saída de Estoque", font=FONT["title"],
                 bg=THEME["bg"], fg=THEME["fg"]).pack(anchor="w", padx=P, pady=(20, 16))

        SecaoForm(self, "PRODUTO E DEPÓSITO").pack(fill="x", padx=P)
        c1 = self._card(P)

        tk.Label(c1, text="Produto *", font=FONT["sm"],
                 bg=THEME["bg_card"], fg=THEME["fg"]).pack(anchor="w", pady=(0, 3))
        self._var_produto = tk.StringVar()
        self._combo_prod  = ttk.Combobox(c1, textvariable=self._var_produto,
                                          state="readonly", font=FONT["md"])
        self._combo_prod.pack(fill="x", ipady=4, pady=(0, 10))
        self._combo_prod.bind("<<ComboboxSelected>>", self._atualizar_saldo)

        row = tk.Frame(c1, bg=THEME["bg_card"])
        row.pack(fill="x")
        tk.Label(row, text="Depósito *", font=FONT["sm"],
                 bg=THEME["bg_card"], fg=THEME["fg"]).pack(anchor="w", pady=(0, 3))
        self._var_dep = tk.StringVar()
        self._combo_dep = ttk.Combobox(row, textvariable=self._var_dep,
                                        state="readonly", font=FONT["md"])
        self._combo_dep.pack(fill="x", ipady=4)
        self._combo_dep.bind("<<ComboboxSelected>>", self._atualizar_saldo)

        self._lbl_saldo = tk.Label(c1, text="", font=FONT["sm"],
                                    bg=THEME["bg_card"], fg=THEME["fg_light"])
        self._lbl_saldo.pack(anchor="e", pady=(4, 0))

        SecaoForm(self, "QUANTIDADE E MOTIVO").pack(fill="x", padx=P, pady=(8, 0))
        c2 = self._card(P)

        self._var_qtd = tk.StringVar(value="1")
        CampoEntry(c2, "Quantidade *", self._var_qtd, justify="right").pack(
            fill="x", pady=(0, 10))

        tk.Label(c2, text="Motivo *", font=FONT["sm"],
                 bg=THEME["bg_card"], fg=THEME["fg"]).pack(anchor="w", pady=(0, 3))
        self._var_motivo = tk.StringVar()
        self._combo_motivo = ttk.Combobox(c2, textvariable=self._var_motivo,
                                           values=MOTIVOS, font=FONT["md"])
        self._combo_motivo.current(0)
        self._combo_motivo.pack(fill="x", ipady=4)

        self._var_erro = tk.StringVar()
        tk.Label(self, textvariable=self._var_erro, font=FONT["sm"],
                 bg=THEME["bg"], fg=THEME["danger"]).pack(anchor="w", padx=P, pady=(8, 0))
        botao(self, "💾  Confirmar Saída", tipo="perigo",
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
        self._combo_prod["values"] = [f"{p['nome']} ({p.get('codigo') or '—'})"
                                       for p in self._produtos]
        self._combo_dep["values"]  = [d["nome"] for d in self._depositos]
        if self._depositos: self._combo_dep.current(0)

    def _pre_preencher(self, sel):
        # sel = [codigo, nome, unid, deposito, qtd, ...]
        nome_prod = sel[1] if len(sel) > 1 else ""
        nome_dep  = sel[3] if len(sel) > 3 else ""
        for i, p in enumerate(self._produtos):
            if p["nome"] == nome_prod:
                self._combo_prod.current(i); break
        for i, d in enumerate(self._depositos):
            if d["nome"] == nome_dep:
                self._combo_dep.current(i); break
        self._atualizar_saldo()

    def _atualizar_saldo(self, _=None):
        ip = self._combo_prod.current()
        id_ = self._combo_dep.current()
        if ip < 0 or id_ < 0: return
        from models.estoque import Estoque
        saldo = Estoque.saldo(self._produtos[ip]["id"], self._depositos[id_]["id"])
        self._lbl_saldo.configure(
            text=f"Saldo disponível: {saldo:g} {self._produtos[ip].get('unidade','')}")

    def _salvar(self):
        ip = self._combo_prod.current()
        id_ = self._combo_dep.current()
        if ip < 0:  self._var_erro.set("Selecione um produto."); return
        if id_ < 0: self._var_erro.set("Selecione um depósito."); return
        try:
            qtd = float(self._var_qtd.get().replace(",", "."))
        except ValueError:
            self._var_erro.set("Quantidade inválida."); return

        from models.estoque import Estoque
        try:
            Estoque.saida(
                produto_id   = self._produtos[ip]["id"],
                deposito_id  = self._depositos[id_]["id"],
                quantidade   = qtd,
                motivo       = self._var_motivo.get().strip() or None,
                usuario_id   = Session.usuario_id(),
                usuario_nome = Session.nome(),
            )
        except ValueError as e:
            self._var_erro.set(str(e)); return

        if self._ao_salvar: self._ao_salvar()
        self.destroy()