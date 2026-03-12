import tkinter as tk
from tkinter import ttk, messagebox
from config import THEME, FONT
from views.widgets.tabela import Tabela
from views.widgets.widgets import botao, SecaoForm


class AbaPosicao(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg=THEME["bg"])
        self._build()
        self._carregar()

    def _build(self):
        # Toolbar
        tb = tk.Frame(self, bg=THEME["bg_card"], highlightthickness=1,
                      highlightbackground=THEME["border"], padx=14, pady=10)
        tb.pack(fill="x", pady=(0, 1))

        tk.Label(tb, text="🔍", font=("Segoe UI", 11),
                 bg=THEME["bg_card"], fg=THEME["fg_light"]).pack(side="left")
        self._var_busca = tk.StringVar()
        self._var_busca.trace_add("write", lambda *_: self._carregar())
        tk.Entry(tb, textvariable=self._var_busca, font=FONT["md"],
                 relief="flat", bg=THEME["bg"], fg=THEME["fg"],
                 highlightthickness=1, highlightbackground=THEME["border"],
                 highlightcolor=THEME["primary"], width=24
                 ).pack(side="left", padx=(4, 12), ipady=5)

        # Filtro depósito
        tk.Label(tb, text="Depósito:", font=FONT["sm"],
                 bg=THEME["bg_card"], fg=THEME["fg_light"]).pack(side="left")
        self._var_dep = tk.StringVar()
        self._combo_dep = ttk.Combobox(tb, textvariable=self._var_dep,
                                        state="readonly", font=FONT["md"], width=20)
        self._combo_dep.pack(side="left", padx=(4, 12), ipady=3)
        self._combo_dep.bind("<<ComboboxSelected>>", lambda _: self._carregar())

        # Filtro alerta
        self._var_alerta = tk.BooleanVar(value=False)
        tk.Checkbutton(tb, text="⚠ Apenas abaixo do mínimo",
                       variable=self._var_alerta,
                       font=FONT["sm"], bg=THEME["bg_card"],
                       fg=THEME["warning"], cursor="hand2",
                       command=self._carregar).pack(side="left", padx=(0, 12))

        from core.session import Session
        if Session.pode("estoque", "criar"):
            botao(tb, "📥 Entrada",       tipo="sucesso",    command=self._entrada).pack(side="right")
            botao(tb, "📤 Saída",         tipo="perigo",     command=self._saida).pack(side="right", padx=(0, 8))
            botao(tb, "🔀 Transferência", tipo="secundario", command=self._transferencia).pack(side="right", padx=(0, 8))

        self._carregar_depositos()

        # Tabela
        self._tabela = Tabela(self, colunas=[
            ("Código",    90), ("Produto",   280), ("Unid.",   55),
            ("Depósito", 130), ("Qtd.",       80), ("Custo M.",100),
            ("Val. Total",110),("Mín.",        70), ("Status",  90),
        ])
        self._tabela.pack(fill="both", expand=True)

        # Rodapé
        rodape = tk.Frame(self, bg=THEME["bg_card"], highlightthickness=1,
                          highlightbackground=THEME["border"], padx=14, pady=6)
        rodape.pack(fill="x")
        self._lbl_status = tk.Label(rodape, text="", font=FONT["sm"],
                                     bg=THEME["bg_card"], fg=THEME["fg_light"])
        self._lbl_status.pack(side="right")

    def _carregar_depositos(self):
        from models.estoque import Deposito
        self._depositos = Deposito.listar()
        self._combo_dep["values"] = ["Todos"] + [d["nome"] for d in self._depositos]
        self._combo_dep.current(0)

    def _deposito_id_sel(self):
        idx = self._combo_dep.current()
        return self._depositos[idx-1]["id"] if idx > 0 else None

    def _carregar(self):
        from models.estoque import Estoque
        rows = Estoque.posicao_completa(
            busca=self._var_busca.get().strip(),
            deposito_id=self._deposito_id_sel(),
            apenas_abaixo_minimo=self._var_alerta.get(),
        )
        self._tabela.limpar()
        alertas = 0
        for r in rows:
            qtd     = r["quantidade"]
            emin    = r["estoque_min"] or 0
            if emin > 0 and qtd <= emin:
                status = "⚠ Baixo"
                alertas += 1
            elif r["estoque_max"] and qtd >= r["estoque_max"]:
                status = "🔴 Acima máx."
            else:
                status = "✅ OK"
            self._tabela.inserir([
                r.get("codigo") or "—",
                r["nome"],
                r["unidade"],
                r["deposito_nome"],
                f"{qtd:g}",
                f"R$ {r['custo_medio']:,.2f}",
                f"R$ {r['valor_total']:,.2f}",
                f"{emin:g}" if emin else "—",
                status,
            ])
        txt = f"{len(rows)} linha(s)"
        if alertas:
            txt += f"   ⚠ {alertas} abaixo do mínimo"
        self._lbl_status.configure(text=txt)

    def _produto_deposito_sel(self):
        sel = self._tabela.selecionado()
        return sel  # [codigo, nome, unid, deposito, qtd, ...]

    def _entrada(self):
        from core.session import Session
        if not Session.pode("estoque", "criar"):
            messagebox.showwarning("Sem Permissão", "Você não tem permissão para registrar entradas.", parent=self); return
        from views.estoque.form_entrada import FormEntrada
        FormEntrada(self, ao_salvar=self._carregar)

    def _saida(self):
        from core.session import Session
        if not Session.pode("estoque", "criar"):
            messagebox.showwarning("Sem Permissão", "Você não tem permissão para registrar saídas.", parent=self); return
        sel = self._tabela.selecionado()
        from views.estoque.form_saida import FormSaida
        FormSaida(self, sel, ao_salvar=self._carregar)

    def _transferencia(self):
        from core.session import Session
        if not Session.pode("estoque", "criar"):
            messagebox.showwarning("Sem Permissão", "Você não tem permissão para transferências.", parent=self); return
        sel = self._tabela.selecionado()
        from views.estoque.form_transferencia import FormTransferencia
        FormTransferencia(self, sel, ao_salvar=self._carregar)