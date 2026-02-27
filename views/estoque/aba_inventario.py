import tkinter as tk
from tkinter import ttk, messagebox
from config import THEME, FONT
from views.widgets.widgets import SecaoForm, botao
from views.base_view import BaseView
from core.session import Session


class AbaInventario(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg=THEME["bg"])
        self._itens: list[dict] = []   # [{produto_id, nome, unidade, saldo_atual, contado_var}]
        self._build()

    def _build(self):
        # Header
        header = tk.Frame(self, bg=THEME["bg_card"], highlightthickness=1,
                          highlightbackground=THEME["border"], padx=16, pady=12)
        header.pack(fill="x", pady=(0, 1))

        tk.Label(header, text="Inventário — Contagem e Ajuste em Lote",
                 font=FONT["bold"], bg=THEME["bg_card"], fg=THEME["fg"]).pack(side="left")

        botao(header, "✅  Confirmar Inventário", tipo="sucesso",
              command=self._confirmar).pack(side="right")
        botao(header, "🔄  Carregar Produtos", tipo="secundario",
              command=self._carregar_produtos).pack(side="right", padx=(0, 8))

        # Seletor de depósito
        sel_frame = tk.Frame(self, bg=THEME["bg_card"], highlightthickness=1,
                             highlightbackground=THEME["border"], padx=16, pady=8)
        sel_frame.pack(fill="x", pady=(0, 1))

        tk.Label(sel_frame, text="Depósito:", font=FONT["sm"],
                 bg=THEME["bg_card"], fg=THEME["fg"]).pack(side="left")
        self._var_dep = tk.StringVar()
        self._combo_dep = ttk.Combobox(sel_frame, textvariable=self._var_dep,
                                        state="readonly", font=FONT["md"], width=24)
        self._combo_dep.pack(side="left", padx=(8, 0), ipady=3)
        self._carregar_depositos()

        tk.Label(sel_frame,
                 text="  Preencha a quantidade contada. Campos em branco = sem alteração.",
                 font=FONT["sm"], bg=THEME["bg_card"], fg=THEME["fg_light"]).pack(side="left", padx=(16, 0))

        # Área scrollável com os itens
        outer = tk.Frame(self, bg=THEME["bg"])
        outer.pack(fill="both", expand=True)

        canvas = tk.Canvas(outer, bg=THEME["bg"], highlightthickness=0)
        scroll = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        self._lista_frame = tk.Frame(canvas, bg=THEME["bg"])
        self._lista_win   = canvas.create_window((0, 0), window=self._lista_frame, anchor="nw")
        self._lista_frame.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
            lambda e: canvas.itemconfig(self._lista_win, width=e.width))
        canvas.bind_all("<MouseWheel>",
            lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

        self._canvas = canvas

        # Rodapé
        rodape = tk.Frame(self, bg=THEME["bg_card"], highlightthickness=1,
                          highlightbackground=THEME["border"], padx=14, pady=6)
        rodape.pack(fill="x")
        self._lbl_status = tk.Label(rodape, text="Clique em 'Carregar Produtos' para iniciar.",
                                     font=FONT["sm"], bg=THEME["bg_card"], fg=THEME["fg_light"])
        self._lbl_status.pack(side="right")

    def _carregar_depositos(self):
        from models.estoque import Deposito
        self._depositos = Deposito.listar()
        self._combo_dep["values"] = [d["nome"] for d in self._depositos]
        if self._depositos:
            self._combo_dep.current(0)

    def _deposito_id_sel(self) -> int | None:
        idx = self._combo_dep.current()
        return self._depositos[idx]["id"] if 0 <= idx < len(self._depositos) else None

    def _carregar_produtos(self):
        dep_id = self._deposito_id_sel()
        if not dep_id:
            messagebox.showwarning("Atenção", "Selecione um depósito.", parent=self)
            return

        from models.estoque import Estoque
        posicao = Estoque.posicao_completa(deposito_id=dep_id)

        # Filtra por depósito selecionado
        posicao = [r for r in posicao if r["deposito_id"] == dep_id]

        for w in self._lista_frame.winfo_children():
            w.destroy()
        self._itens.clear()

        # Cabeçalho da lista
        hdr = tk.Frame(self._lista_frame, bg=THEME["primary_dark"])
        hdr.pack(fill="x", padx=2, pady=(2, 0))
        for txt, w in [("Código",80),("Produto",300),("Unid.",50),
                        ("Saldo Sistema",100),("Qtd. Contada",120),("Diferença",90)]:
            tk.Label(hdr, text=txt, font=FONT["bold"], bg=THEME["primary_dark"],
                     fg="white", width=w//7, anchor="w", padx=8, pady=6).pack(side="left")

        for i, r in enumerate(posicao):
            var_contado = tk.StringVar()
            self._itens.append({
                "produto_id": r["id"],
                "nome":       r["nome"],
                "unidade":    r["unidade"],
                "saldo":      r["quantidade"],
                "var":        var_contado,
            })
            bg = "white" if i % 2 == 0 else THEME["row_alt"]
            row = tk.Frame(self._lista_frame, bg=bg)
            row.pack(fill="x", padx=2)

            tk.Label(row, text=r.get("codigo") or "—", font=FONT["sm"],
                     bg=bg, fg=THEME["fg"], width=10, anchor="w", padx=8).pack(side="left")
            tk.Label(row, text=r["nome"], font=FONT["sm"],
                     bg=bg, fg=THEME["fg"], width=40, anchor="w", padx=4).pack(side="left")
            tk.Label(row, text=r["unidade"], font=FONT["sm"],
                     bg=bg, fg=THEME["fg_light"], width=6, anchor="w").pack(side="left")
            tk.Label(row, text=f"{r['quantidade']:g}", font=FONT["sm"],
                     bg=bg, fg=THEME["fg"], width=13, anchor="e", padx=8).pack(side="left")

            entry = tk.Entry(row, textvariable=var_contado, font=FONT["md"],
                             relief="flat", bg="white" if bg == THEME["row_alt"] else THEME["bg"],
                             fg=THEME["fg"], justify="right",
                             highlightthickness=1,
                             highlightbackground=THEME["border"],
                             highlightcolor=THEME["primary"], width=14)
            entry.pack(side="left", padx=4, ipady=4)

            # Label diferença (atualiza em tempo real)
            lbl_dif = tk.Label(row, text="—", font=FONT["sm"],
                                bg=bg, fg=THEME["fg_light"], width=11, anchor="e", padx=8)
            lbl_dif.pack(side="left")

            def _make_cb(var, saldo, lbl):
                def cb(*_):
                    try:
                        cont  = float(var.get().replace(",", "."))
                        dif   = cont - saldo
                        cor   = THEME["success"] if dif >= 0 else THEME["danger"]
                        sinal = "+" if dif > 0 else ""
                        lbl.configure(text=f"{sinal}{dif:g}", fg=cor)
                    except ValueError:
                        lbl.configure(text="—", fg=THEME["fg_light"])
                return cb

            var_contado.trace_add("write", _make_cb(var_contado, r["quantidade"], lbl_dif))

        self._lbl_status.configure(text=f"{len(posicao)} produto(s) carregado(s).")

    def _confirmar(self):
        dep_id = self._deposito_id_sel()
        if not dep_id:
            messagebox.showwarning("Atenção", "Selecione um depósito.", parent=self)
            return
        if not self._itens:
            messagebox.showwarning("Atenção", "Carregue os produtos primeiro.", parent=self)
            return

        # Coleta apenas os itens que foram preenchidos
        ajustes = []
        for item in self._itens:
            val = item["var"].get().strip()
            if not val:
                continue
            try:
                ajustes.append({
                    "produto_id":        item["produto_id"],
                    "quantidade_contada": float(val.replace(",", "."))
                })
            except ValueError:
                messagebox.showerror("Erro",
                    f"Valor inválido para '{item['nome']}': {val}", parent=self)
                return

        if not ajustes:
            messagebox.showinfo("Info", "Nenhum item alterado.", parent=self)
            return

        if not messagebox.askyesno("Confirmar Inventário",
            f"Confirmar ajuste de {len(ajustes)} produto(s) no depósito selecionado?",
            parent=self):
            return

        from models.estoque import Estoque
        Estoque.inventario(
            itens=ajustes,
            deposito_id=dep_id,
            usuario_id=Session.usuario_id(),
            usuario_nome=Session.nome(),
        )
        messagebox.showinfo("Sucesso", f"{len(ajustes)} ajuste(s) aplicado(s).", parent=self)
        self._carregar_produtos()