"""
Painel de Vendas — listagem completa, filtros, detalhes e reimpressão de cupom.
Caminho: views/pdv/vendas_view.py
"""
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import datetime
from config import THEME, FONT
from views.widgets.widgets import botao


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
STATUS_COR = {
    "ABERTA":     "#f4b942",
    "FINALIZADA": "#2dce89",
    "CANCELADA":  "#f5365c",
}

STATUS_LABEL = {
    "ABERTA":     "🔄 Aberta",
    "FINALIZADA": "✅ Finalizada",
    "CANCELADA":  "❌ Cancelada",
}

FORMAS_LABEL = {
    "DINHEIRO": "Dinheiro",
    "DEBITO":   "Cartão Débito",
    "CREDITO":  "Cartão Crédito",
    "PIX":      "Pix",
    "VR":       "Vale-Refeição",
    "VA":       "Vale-Alimentação",
    "OUTROS":   "Outros",
}


def _hoje():
    return datetime.date.today().isoformat()


# ─────────────────────────────────────────────────────────────────────────────
# View principal
# ─────────────────────────────────────────────────────────────────────────────
class VendasView(tk.Frame):
    """Painel de vendas — integra ao menu lateral como qualquer outra view."""

    def __init__(self, master):
        super().__init__(master, bg=THEME["bg"])
        self._build()
        self._carregar()

    # ── build ──────────────────────────────────────────────────────────────
    def _build(self):
        body = tk.Frame(self, bg=THEME["bg"])
        body.pack(fill="both", expand=True, padx=24, pady=(16, 8))

        # Título
        tk.Label(body, text="🧾  Painel de Vendas",
                 font=FONT["title"], bg=THEME["bg"],
                 fg=THEME["fg"]).pack(anchor="w", pady=(0, 14))

        # ── Filtros ────────────────────────────────────────────────────────
        filt = tk.Frame(body, bg=THEME["bg_card"],
                        highlightthickness=1,
                        highlightbackground=THEME["border"])
        filt.pack(fill="x", pady=(0, 10))
        inner = tk.Frame(filt, bg=THEME["bg_card"], padx=14, pady=10)
        inner.pack(fill="x")

        # Data inicial
        tk.Label(inner, text="De:", font=FONT["sm"],
                 bg=THEME["bg_card"], fg=THEME["fg"]).grid(
                 row=0, column=0, sticky="w", padx=(0, 4))
        self._var_data_ini = tk.StringVar(value=_hoje())
        tk.Entry(inner, textvariable=self._var_data_ini,
                 font=FONT["md"], width=12, relief="flat",
                 bg=THEME["row_alt"], fg=THEME["fg"]).grid(
                 row=0, column=1, padx=(0, 14), ipady=5)

        # Data final
        tk.Label(inner, text="Até:", font=FONT["sm"],
                 bg=THEME["bg_card"], fg=THEME["fg"]).grid(
                 row=0, column=2, sticky="w", padx=(0, 4))
        self._var_data_fim = tk.StringVar(value=_hoje())
        tk.Entry(inner, textvariable=self._var_data_fim,
                 font=FONT["md"], width=12, relief="flat",
                 bg=THEME["row_alt"], fg=THEME["fg"]).grid(
                 row=0, column=3, padx=(0, 14), ipady=5)

        # Status
        tk.Label(inner, text="Status:", font=FONT["sm"],
                 bg=THEME["bg_card"], fg=THEME["fg"]).grid(
                 row=0, column=4, sticky="w", padx=(0, 4))
        self._var_status = tk.StringVar(value="TODOS")
        ttk.Combobox(inner, textvariable=self._var_status,
                     values=["TODOS", "FINALIZADA", "ABERTA", "CANCELADA"],
                     state="readonly", font=FONT["md"], width=14).grid(
                     row=0, column=5, padx=(0, 14))

        # Operador / busca livre
        tk.Label(inner, text="Operador:", font=FONT["sm"],
                 bg=THEME["bg_card"], fg=THEME["fg"]).grid(
                 row=0, column=6, sticky="w", padx=(0, 4))
        self._var_busca = tk.StringVar()
        tk.Entry(inner, textvariable=self._var_busca,
                 font=FONT["md"], width=16, relief="flat",
                 bg=THEME["row_alt"], fg=THEME["fg"]).grid(
                 row=0, column=7, padx=(0, 14), ipady=5)

        botao(inner, "🔍  Filtrar", tipo="primario",
              command=self._carregar).grid(row=0, column=8, padx=(0, 8))
        botao(inner, "📅  Hoje", tipo="secundario",
              command=self._filtrar_hoje).grid(row=0, column=9, padx=(0, 8))
        botao(inner, "📆  Este mês", tipo="secundario",
              command=self._filtrar_mes).grid(row=0, column=10)

        # ── Tabela ─────────────────────────────────────────────────────────
        tabframe = tk.Frame(body, bg=THEME["bg"])
        tabframe.pack(fill="both", expand=True)

        cols = ("numero", "data", "operador", "cliente",
                "itens", "total", "pago", "status")
        self._tree = ttk.Treeview(tabframe, columns=cols,
                                  show="headings", selectmode="browse")

        heads = {
            "numero":   ("Nº", 60),
            "data":     ("Data/Hora", 140),
            "operador": ("Operador", 130),
            "cliente":  ("Cliente", 150),
            "itens":    ("Itens", 60),
            "total":    ("Total", 90),
            "pago":     ("Pago", 90),
            "status":   ("Status", 110),
        }
        for c, (h, w) in heads.items():
            self._tree.heading(c, text=h,
                               command=lambda col=c: self._ordenar(col))
            self._tree.column(c, width=w,
                              anchor="e" if c in ("total","pago","itens","numero") else "w")

        vsb = ttk.Scrollbar(tabframe, orient="vertical",
                            command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        self._tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        self._tree.bind("<<TreeviewSelect>>", self._on_selecionar)
        self._tree.bind("<Double-1>", lambda e: self._ver_detalhes())

        # ── Rodapé: totalizadores + botões ─────────────────────────────────
        rodape = tk.Frame(body, bg=THEME["bg_card"],
                          highlightthickness=1,
                          highlightbackground=THEME["border"])
        rodape.pack(fill="x", pady=(8, 0))
        rin = tk.Frame(rodape, bg=THEME["bg_card"], padx=14, pady=8)
        rin.pack(fill="x")

        self._lbl_qtd     = tk.Label(rin, text="Vendas: 0",
                                     font=FONT["bold"],
                                     bg=THEME["bg_card"], fg=THEME["fg"])
        self._lbl_qtd.pack(side="left", padx=(0, 24))

        self._lbl_total   = tk.Label(rin, text="Total: R$ 0,00",
                                     font=FONT["bold"],
                                     bg=THEME["bg_card"], fg="#2dce89")
        self._lbl_total.pack(side="left", padx=(0, 24))

        self._lbl_canceladas = tk.Label(rin, text="Canceladas: 0",
                                         font=FONT["sm"],
                                         bg=THEME["bg_card"], fg="#f5365c")
        self._lbl_canceladas.pack(side="left")

        # Botões de ação
        self._btn_detalhes = botao(rin, "🔎  Detalhes",
                                   tipo="secundario",
                                   command=self._ver_detalhes,
                                   state="disabled")
        self._btn_detalhes.pack(side="right", padx=(8, 0))

        self._btn_cupom = botao(rin, "🖨  Reimprimir Cupom",
                                tipo="primario",
                                command=self._reimprimir_cupom,
                                state="disabled")
        self._btn_cupom.pack(side="right", padx=(8, 0))

        self._btn_cancelar = botao(rin, "❌  Cancelar Venda",
                                   tipo="perigo",
                                   command=self._cancelar_venda,
                                   state="disabled")
        self._btn_cancelar.pack(side="right", padx=(8, 0))

        self._btn_retornar = botao(rin, "🔁  Retornar ao PDV",
                                   tipo="primario",
                                   command=self._retornar_pdv,
                                   state="disabled")
        self._btn_retornar.pack(side="right", padx=(8, 0))

        self._venda_sel = None

    # ── Carregar / filtrar ─────────────────────────────────────────────────
    def _carregar(self):
        from models.venda import Venda
        from core.database import DatabaseManager

        data_ini = self._var_data_ini.get().strip()
        data_fim = self._var_data_fim.get().strip()
        status   = self._var_status.get()
        busca    = self._var_busca.get().strip().lower()

        db = DatabaseManager.empresa()

        # Monta query com range de datas
        sql = "SELECT * FROM vendas WHERE 1=1"
        p   = []
        if data_ini:
            sql += " AND date(criado_em) >= ?"; p.append(data_ini)
        if data_fim:
            sql += " AND date(criado_em) <= ?"; p.append(data_fim)
        if status != "TODOS":
            sql += " AND status = ?"; p.append(status)
        sql += " ORDER BY criado_em DESC LIMIT 500"

        try:
            vendas = db.fetchall(sql, tuple(p))
        except Exception as e:
            messagebox.showerror("Erro", str(e))
            return

        # Filtro de operador (client-side)
        if busca:
            vendas = [v for v in vendas
                      if busca in (v.get("operador_nome") or "").lower()
                      or busca in (v.get("cliente_nome") or "").lower()]

        # Conta itens por venda (batch)
        ids = [v["id"] for v in vendas]
        contagem = {}
        if ids:
            placeholders = ",".join("?" * len(ids))
            rows = db.fetchall(
                f"SELECT venda_id, COUNT(*) as n FROM venda_itens "
                f"WHERE venda_id IN ({placeholders}) GROUP BY venda_id",
                tuple(ids)
            )
            contagem = {r["venda_id"]: r["n"] for r in rows}

        # Preenche tree
        self._tree.delete(*self._tree.get_children())
        total_geral = 0.0
        qtd_final   = 0
        qtd_cancel  = 0

        for v in vendas:
            st  = v.get("status", "")
            tot = float(v.get("total", 0))
            pago= float(v.get("total_pago", 0))
            dt  = (v.get("criado_em") or "")[:16]
            n_it = contagem.get(v["id"], 0)

            tag = st.lower()
            self._tree.insert("", "end",
                iid=str(v["id"]),
                values=(
                    v.get("numero", ""),
                    dt,
                    v.get("operador_nome", ""),
                    v.get("cliente_nome", "") or "—",
                    n_it,
                    f"R$ {tot:,.2f}",
                    f"R$ {pago:,.2f}",
                    STATUS_LABEL.get(st, st),
                ),
                tags=(tag,)
            )
            if st == "FINALIZADA":
                total_geral += tot
                qtd_final   += 1
            elif st == "CANCELADA":
                qtd_cancel  += 1

        # Tags de cor
        self._tree.tag_configure("finalizada", foreground="#2dce89")
        self._tree.tag_configure("cancelada",  foreground="#f5365c")
        self._tree.tag_configure("aberta",     foreground="#f4b942")

        # Rodapé
        self._lbl_qtd.config(
            text=f"Finalizadas: {qtd_final}  |  Total: {len(vendas)}")
        self._lbl_total.config(
            text=f"Total vendido: R$ {total_geral:,.2f}")
        self._lbl_canceladas.config(
            text=f"Canceladas: {qtd_cancel}")

        self._venda_sel = None
        self._btn_detalhes.config(state="disabled")
        self._btn_cupom.config(state="disabled")
        self._btn_cancelar.config(state="disabled")
        self._btn_retornar.config(state="disabled")

    def _filtrar_hoje(self):
        hoje = _hoje()
        self._var_data_ini.set(hoje)
        self._var_data_fim.set(hoje)
        self._var_status.set("TODOS")
        self._carregar()

    def _filtrar_mes(self):
        hoje = datetime.date.today()
        ini  = hoje.replace(day=1).isoformat()
        self._var_data_ini.set(ini)
        self._var_data_fim.set(hoje.isoformat())
        self._var_status.set("TODOS")
        self._carregar()

    # ── Seleção ────────────────────────────────────────────────────────────
    def _on_selecionar(self, event=None):
        sel = self._tree.selection()
        if not sel:
            self._venda_sel = None
            self._btn_detalhes.config(state="disabled")
            self._btn_cupom.config(state="disabled")
            self._btn_cancelar.config(state="disabled")
            self._btn_retornar.config(state="disabled")
            return

        venda_id = int(sel[0])
        from models.venda import Venda
        self._venda_sel = Venda.buscar_por_id(venda_id)
        st = (self._venda_sel or {}).get("status", "")

        self._btn_detalhes.config(state="normal")
        self._btn_cupom.config(
            state="normal" if st == "FINALIZADA" else "disabled")
        self._btn_cancelar.config(
            state="normal" if st == "ABERTA" else "disabled")
        self._btn_retornar.config(
            state="normal" if st == "ABERTA" else "disabled")

    # ── Ações ──────────────────────────────────────────────────────────────
    def _ver_detalhes(self):
        if not self._venda_sel:
            return
        DetalhesVendaModal(self, self._venda_sel)

    def _reimprimir_cupom(self):
        if not self._venda_sel:
            return
        venda = self._venda_sel
        from models.venda import Venda
        from services.cupom import gerar_cupom_pdf
        from core.database import DatabaseManager
        from core.session import Session

        try:
            empresa = DatabaseManager.master().fetchone(
                "SELECT * FROM empresas WHERE id=?",
                (Session.empresa()["id"],)
            ) or {}
        except Exception:
            empresa = {}

        try:
            itens = Venda.itens(venda["id"])
            pags  = Venda.pagamentos(venda["id"])
            path  = gerar_cupom_pdf(venda, itens, pags, empresa)
            import subprocess, sys
            if sys.platform == "win32":
                subprocess.Popen(["start", "", path], shell=True)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as e:
            messagebox.showerror("Erro ao gerar cupom", str(e))

    def _cancelar_venda(self):
        if not self._venda_sel:
            return
        venda = self._venda_sel
        if venda.get("status") != "ABERTA":
            messagebox.showwarning("Aviso",
                "Apenas vendas em ABERTA podem ser canceladas aqui.")
            return

        motivo = simpledialog.askstring(
            "Cancelar Venda",
            f"Motivo do cancelamento da venda #{venda['numero']}:",
            parent=self
        ) or ""

        if not messagebox.askyesno("Confirmar",
                f"Cancelar venda #{venda['numero']}?"):
            return

        try:
            from models.venda import Venda
            Venda.cancelar(venda["id"], motivo)
            messagebox.showinfo("Sucesso",
                f"Venda #{venda['numero']} cancelada.")
            self._carregar()
        except Exception as e:
            messagebox.showerror("Erro", str(e))

    def _retornar_pdv(self):
        if not self._venda_sel:
            return
        venda = self._venda_sel
        if venda.get("status") != "ABERTA":
            return

        from core.database import DatabaseManager
        caixa = DatabaseManager.empresa().fetchone(
            "SELECT * FROM caixas WHERE id=?", (venda.get("caixa_id"),))
        if not caixa:
            from views.pdv.caixa_view import selecionar_caixa
            caixa = selecionar_caixa(self)
        if not caixa:
            messagebox.showwarning("Aviso", "Nenhum caixa disponível.")
            return

        from views.pdv.pdv_view import PDVView
        PDVView(self.winfo_toplevel(), caixa, venda_id=venda["id"])

    # ── Ordenação ──────────────────────────────────────────────────────────
    _sort_col = None
    _sort_rev = False

    def _ordenar(self, col):
        items = [(self._tree.set(k, col), k)
                 for k in self._tree.get_children("")]
        reverse = (self._sort_col == col and not self._sort_rev)
        self._sort_col = col
        self._sort_rev = reverse
        try:
            items.sort(key=lambda t: float(t[0].replace("R$","").replace(",","").strip()),
                       reverse=reverse)
        except Exception:
            items.sort(key=lambda t: t[0], reverse=reverse)
        for i, (_, k) in enumerate(items):
            self._tree.move(k, "", i)


# ─────────────────────────────────────────────────────────────────────────────
# Modal de detalhes
# ─────────────────────────────────────────────────────────────────────────────
class DetalhesVendaModal(tk.Toplevel):

    def __init__(self, master, venda: dict):
        super().__init__(master)
        self.title(f"Detalhes — Venda #{venda.get('numero','')}")
        self.configure(bg=THEME["bg"])
        self.geometry("640x560")
        self.resizable(True, True)
        self.grab_set()
        self._venda = venda
        self._build()

    def _build(self):
        from models.venda import Venda

        v = self._venda
        itens = Venda.itens(v["id"])
        pags  = Venda.pagamentos(v["id"])

        P = 20
        canvas = tk.Canvas(self, bg=THEME["bg"], highlightthickness=0)
        vsb    = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True)
        body = tk.Frame(canvas, bg=THEME["bg"])
        win  = canvas.create_window((0, 0), window=body, anchor="nw")
        body.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
            lambda e: canvas.itemconfig(win, width=e.width))
        canvas.bind_all("<MouseWheel>",
            lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

        # Cabeçalho
        st  = v.get("status","")
        cor = STATUS_COR.get(st, THEME["fg"])
        tk.Label(body, text=f"Venda #{v.get('numero','')}",
                 font=FONT["title"], bg=THEME["bg"],
                 fg=THEME["fg"]).pack(anchor="w", padx=P, pady=(16, 2))
        tk.Label(body,
                 text=STATUS_LABEL.get(st, st),
                 font=FONT["bold"], bg=THEME["bg"], fg=cor).pack(
                 anchor="w", padx=P, pady=(0, 10))

        def campo(parent, label, valor):
            row = tk.Frame(parent, bg=THEME["bg_card"])
            row.pack(fill="x", pady=1)
            tk.Label(row, text=label, font=FONT["sm"], width=18,
                     anchor="w", bg=THEME["bg_card"],
                     fg=THEME["fg_light"]).pack(side="left")
            tk.Label(row, text=str(valor or "—"), font=FONT["md"],
                     anchor="w", bg=THEME["bg_card"],
                     fg=THEME["fg"]).pack(side="left")

        def card(title):
            tk.Label(body, text=title, font=FONT["bold"],
                     bg=THEME["bg"], fg=THEME["fg_light"]).pack(
                     anchor="w", padx=P, pady=(10, 2))
            f = tk.Frame(body, bg=THEME["bg_card"],
                         highlightthickness=1,
                         highlightbackground=THEME["border"],
                         padx=14, pady=10)
            f.pack(fill="x", padx=P)
            return f

        # Informações gerais
        c = card("INFORMAÇÕES GERAIS")
        campo(c, "Data/Hora:",     (v.get("criado_em",""))[:16])
        campo(c, "Operador:",      v.get("operador_nome",""))
        campo(c, "Cliente:",       v.get("cliente_nome","") or "—")
        campo(c, "Caixa ID:",      v.get("caixa_id","—"))
        if v.get("finalizada_em"):
            campo(c, "Finalizada em:", v["finalizada_em"][:16])
        if v.get("cancelada_em"):
            campo(c, "Cancelada em:",  v["cancelada_em"][:16])
        if v.get("motivo_cancel"):
            campo(c, "Motivo:",        v["motivo_cancel"])

        # Itens
        ic = card(f"ITENS ({len(itens)})")
        hdr = tk.Frame(ic, bg=THEME["bg_card"])
        hdr.pack(fill="x", pady=(0, 4))
        for txt, w in [("Produto", 200), ("Qtd", 60),
                       ("Unit.", 80), ("Desc.", 70), ("Subtotal", 80)]:
            tk.Label(hdr, text=txt, font=FONT["bold"],
                     bg=THEME["bg_card"], fg=THEME["fg_light"],
                     width=w//7, anchor="w").pack(side="left")

        for it in itens:
            row = tk.Frame(ic, bg=THEME["bg_card"])
            row.pack(fill="x", pady=1)
            dados = [
                (str(it.get("produto_nome",""))[:28], 200),
                (f"{float(it.get('quantidade',1)):.2f}", 60),
                (f"R${float(it.get('preco_unitario',0)):.2f}", 80),
                (f"R${float(it.get('desconto_valor',0)):.2f}", 70),
                (f"R${float(it.get('subtotal',0)):.2f}", 80),
            ]
            for txt, w in dados:
                tk.Label(row, text=txt, font=FONT["sm"],
                         bg=THEME["bg_card"], fg=THEME["fg"],
                         width=w//7, anchor="w").pack(side="left")

        # Totais
        tc = card("TOTAIS")
        sub  = float(v.get("subtotal", 0))
        desc = float(v.get("desconto_valor", 0))
        tot  = float(v.get("total", 0))
        troco= float(v.get("troco", 0))
        campo(tc, "Subtotal:",     f"R$ {sub:,.2f}")
        if desc > 0:
            campo(tc, "Desconto:",  f"- R$ {desc:,.2f}")
        campo(tc, "TOTAL:",        f"R$ {tot:,.2f}")
        campo(tc, "Total pago:",   f"R$ {float(v.get('total_pago',0)):,.2f}")
        if troco > 0:
            campo(tc, "Troco:",    f"R$ {troco:,.2f}")

        # Pagamentos
        if pags:
            pc = card(f"PAGAMENTOS ({len(pags)})")
            for pg in pags:
                forma = FORMAS_LABEL.get(pg.get("forma",""), pg.get("forma",""))
                parc  = int(pg.get("parcelas", 1))
                label = forma + (f" {parc}x" if parc > 1 else "")
                campo(pc, label + ":", f"R$ {float(pg.get('valor',0)):,.2f}")

        tk.Button(body, text="Fechar", font=FONT["md"],
                  bg=THEME["primary"], fg="white",
                  relief="flat", cursor="hand2",
                  padx=20, pady=8,
                  command=self.destroy).pack(pady=16)