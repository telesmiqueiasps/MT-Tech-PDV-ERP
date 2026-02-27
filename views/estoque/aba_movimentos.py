import tkinter as tk
from tkinter import ttk
from config import THEME, FONT
from views.widgets.tabela import Tabela

TIPOS = {
    "ENT":     ("📥 Entrada",       "#1E8449"),
    "SAI":     ("📤 Saída",         "#C0392B"),
    "TRF_OUT": ("🔀 Transf. Saída", "#D68910"),
    "TRF_IN":  ("🔀 Transf. Entrada","#1A5276"),
    "INV":     ("📋 Inventário",    "#6C3483"),
}


class AbaMovimentos(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg=THEME["bg"])
        self._build()
        self._carregar()

    def _build(self):
        tb = tk.Frame(self, bg=THEME["bg_card"], highlightthickness=1,
                      highlightbackground=THEME["border"], padx=14, pady=10)
        tb.pack(fill="x", pady=(0, 1))

        # Filtro tipo
        tk.Label(tb, text="Tipo:", font=FONT["sm"],
                 bg=THEME["bg_card"], fg=THEME["fg_light"]).pack(side="left")
        self._var_tipo = tk.StringVar()
        self._combo_tipo = ttk.Combobox(tb, textvariable=self._var_tipo,
                                         state="readonly", font=FONT["md"], width=18)
        self._combo_tipo["values"] = ["Todos", "Entrada", "Saída",
                                       "Transf. Saída", "Transf. Entrada", "Inventário"]
        self._combo_tipo.current(0)
        self._combo_tipo.pack(side="left", padx=(4, 12), ipady=3)
        self._combo_tipo.bind("<<ComboboxSelected>>", lambda _: self._carregar())

        # Filtro depósito
        tk.Label(tb, text="Depósito:", font=FONT["sm"],
                 bg=THEME["bg_card"], fg=THEME["fg_light"]).pack(side="left")
        self._var_dep = tk.StringVar()
        self._combo_dep = ttk.Combobox(tb, textvariable=self._var_dep,
                                        state="readonly", font=FONT["md"], width=18)
        self._combo_dep.pack(side="left", padx=(4, 12), ipady=3)
        self._combo_dep.bind("<<ComboboxSelected>>", lambda _: self._carregar())
        self._carregar_depositos()

        tk.Button(tb, text="↻ Atualizar", font=FONT["sm"],
                  bg=THEME["bg_card"], fg=THEME["primary"],
                  relief="flat", cursor="hand2",
                  command=self._carregar).pack(side="right")

        self._tabela = Tabela(self, colunas=[
            ("Data/Hora",  130), ("Tipo",      120), ("Produto",   200),
            ("Depósito",   120), ("Qtd.",        70), ("Custo Unit.",100),
            ("Total R$",   100), ("NF",          80), ("Usuário",   110),
            ("Obs.",       180),
        ])
        self._tabela.pack(fill="both", expand=True)

        rodape = tk.Frame(self, bg=THEME["bg_card"], highlightthickness=1,
                          highlightbackground=THEME["border"], padx=14, pady=6)
        rodape.pack(fill="x")
        self._lbl_total = tk.Label(rodape, text="", font=FONT["sm"],
                                    bg=THEME["bg_card"], fg=THEME["fg_light"])
        self._lbl_total.pack(side="right")

    def _carregar_depositos(self):
        from models.estoque import Deposito
        self._depositos = Deposito.listar()
        self._combo_dep["values"] = ["Todos"] + [d["nome"] for d in self._depositos]
        self._combo_dep.current(0)

    def _tipo_cod(self):
        mapa = {
            "Entrada": "ENT", "Saída": "SAI",
            "Transf. Saída": "TRF_OUT", "Transf. Entrada": "TRF_IN",
            "Inventário": "INV",
        }
        return mapa.get(self._var_tipo.get())

    def _carregar(self):
        from models.estoque import Estoque
        idx_dep  = self._combo_dep.current()
        dep_id   = self._depositos[idx_dep-1]["id"] if idx_dep > 0 else None
        movs = Estoque.historico(deposito_id=dep_id, tipo=self._tipo_cod(), limite=500)
        self._tabela.limpar()
        for m in movs:
            tipo_label, _ = TIPOS.get(m["tipo"], (m["tipo"], THEME["fg"]))
            sinal = "+" if m["tipo"] in ("ENT","TRF_IN") else "-"
            self._tabela.inserir([
                m["criado_em"],
                tipo_label,
                m.get("produto_nome",""),
                m.get("deposito_nome",""),
                f"{sinal}{m['quantidade']:g}",
                f"R$ {m['custo_unitario']:,.2f}",
                f"R$ {m['custo_total']:,.2f}",
                m.get("numero_nf") or "—",
                m.get("usuario_nome") or "—",
                m.get("motivo") or "—",
            ])
        self._lbl_total.configure(text=f"{len(movs)} movimento(s)")