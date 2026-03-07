import tkinter as tk
from tkinter import ttk
from datetime import date, datetime
from config import THEME, FONT
from core.session import Session

_DIAS   = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
_MESES  = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
           "Jul", "Ago", "Set", "Out", "Nov", "Dez"]


class Dashboard(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg=THEME["bg"])
        self.pack(fill="both", expand=True)
        self._after_id = None
        self._build()

    def _build(self):
        if Session.is_admin_global():
            self._build_admin()
        else:
            self._build_empresa()

    # ── Admin global ─────────────────────────────────────────────
    def _build_admin(self):
        wrap = tk.Frame(self, bg=THEME["bg"])
        wrap.pack(fill="both", expand=True, padx=32, pady=24)

        self._build_header(wrap)

        # Stats admin
        stats = self._stats_admin()
        row = tk.Frame(wrap, bg=THEME["bg"])
        row.pack(fill="x", pady=(20, 0))
        for i, s in enumerate(stats):
            self._stat_card(row, s, col=i)
            row.columnconfigure(i, weight=1)

        # Banner info
        banner = tk.Frame(wrap, bg=THEME["primary_light"],
                          highlightthickness=1,
                          highlightbackground=THEME["primary"])
        banner.pack(fill="x", pady=(24, 0))
        inner = tk.Frame(banner, bg=THEME["primary_light"], padx=20, pady=14)
        inner.pack(fill="x")
        tk.Label(inner, text="🔑  Administrador Global",
                 font=FONT["bold"], bg=THEME["primary_light"],
                 fg=THEME["primary"]).pack(anchor="w")
        tk.Label(inner, text="Acesse Administração no menu lateral para gerenciar empresas, "
                             "usuários e licenças.",
                 font=FONT["sm"], bg=THEME["primary_light"],
                 fg=THEME["fg"]).pack(anchor="w", pady=(2, 0))

    def _stats_admin(self) -> list[dict]:
        try:
            from core.database import DatabaseManager
            db = DatabaseManager.master()
            total_emp = (db.fetchone("SELECT COUNT(*) AS t FROM empresas") or {}).get("t", 0)
        except Exception:
            total_emp = 0
        return [
            {"icone": "🏢", "titulo": "Empresas",    "valor": str(total_emp),
             "sub": "cadastradas", "cor": THEME["primary"]},
        ]

    # ── Empresa ──────────────────────────────────────────────────
    def _build_empresa(self):
        # Área de rolagem
        outer = tk.Frame(self, bg=THEME["bg"])
        outer.pack(fill="both", expand=True)

        canvas = tk.Canvas(outer, bg=THEME["bg"], highlightthickness=0)
        vsb    = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        wrap = tk.Frame(canvas, bg=THEME["bg"])
        win  = canvas.create_window((0, 0), window=wrap, anchor="nw")

        def _on_cfg(e):
            canvas.configure(scrollregion=canvas.bbox("all"))
        def _on_resize(e):
            canvas.itemconfig(win, width=e.width)
        def _scroll(e):
            try:
                canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
            except tk.TclError:
                pass

        wrap.bind("<Configure>", _on_cfg)
        canvas.bind("<Configure>", _on_resize)
        canvas.bind_all("<MouseWheel>", _scroll)
        canvas.bind("<Destroy>", lambda e: canvas.unbind_all("<MouseWheel>"))

        pad = tk.Frame(wrap, bg=THEME["bg"])
        pad.pack(fill="both", expand=True, padx=32, pady=24)

        self._build_header(pad)
        self._build_stats(pad)
        self._build_corpo(pad)

    def _build_stats(self, parent):
        stats = self._stats_empresa()
        row = tk.Frame(parent, bg=THEME["bg"])
        row.pack(fill="x", pady=(20, 0))
        for i, s in enumerate(stats):
            self._stat_card(row, s, col=i)
            row.columnconfigure(i, weight=1)

    def _build_corpo(self, parent):
        row = tk.Frame(parent, bg=THEME["bg"])
        row.pack(fill="both", expand=True, pady=(20, 0))
        row.columnconfigure(0, weight=3)
        row.columnconfigure(1, weight=2)

        self._build_vendas_recentes(row)
        self._build_alertas(row)

    # ── Header ───────────────────────────────────────────────────
    def _build_header(self, parent):
        hora = datetime.now().hour
        saudacao = "Bom dia" if hora < 12 else "Boa tarde" if hora < 18 else "Boa noite"
        nome = Session.usuario().get("nome") or Session.usuario().get("login", "")

        hdr = tk.Frame(parent, bg=THEME["bg"])
        hdr.pack(fill="x")

        esq = tk.Frame(hdr, bg=THEME["bg"])
        esq.pack(side="left", fill="x", expand=True)

        tk.Label(esq, text=f"{saudacao}, {nome}!",
                 font=("Segoe UI", 22, "bold"),
                 bg=THEME["bg"], fg=THEME["fg"]).pack(anchor="w")

        hoje = date.today()
        dia_semana = _DIAS[hoje.weekday()]
        data_fmt   = f"{dia_semana}, {hoje.day} de {_MESES[hoje.month - 1]}. de {hoje.year}"
        empresa_nm = Session.empresa().get("nome", "")
        sub_text   = f"{empresa_nm}  •  {data_fmt}" if empresa_nm else data_fmt

        tk.Label(esq, text=sub_text, font=FONT["sm"],
                 bg=THEME["bg"], fg=THEME["fg_light"]).pack(anchor="w", pady=(3, 0))

        # Relógio ao vivo
        self._lbl_hora = tk.Label(hdr, text="",
                                  font=("Segoe UI", 26, "bold"),
                                  bg=THEME["bg"], fg=THEME["primary"])
        self._lbl_hora.pack(side="right")
        self._tick()

    def _tick(self):
        if self._lbl_hora.winfo_exists():
            self._lbl_hora.configure(text=datetime.now().strftime("%H:%M:%S"))
            self._after_id = self._lbl_hora.after(1000, self._tick)

    # ── Stat cards ───────────────────────────────────────────────
    def _stat_card(self, parent, dados: dict, col: int):
        cor = dados["cor"]

        outer = tk.Frame(parent, bg=THEME["border"])
        outer.grid(row=0, column=col, padx=(0, 14), sticky="nsew", ipadx=1, ipady=1)

        card = tk.Frame(outer, bg=THEME["bg_card"])
        card.pack(fill="both", expand=True)

        # Barra de acento lateral
        tk.Frame(card, bg=cor, width=5).pack(side="left", fill="y")

        body = tk.Frame(card, bg=THEME["bg_card"], padx=18, pady=16)
        body.pack(side="left", fill="both", expand=True)

        # Ícone + valor na mesma linha
        topo = tk.Frame(body, bg=THEME["bg_card"])
        topo.pack(fill="x")

        def _lighten(hex_cor: str) -> str:
            try:
                r = int(hex_cor[1:3], 16)
                g = int(hex_cor[3:5], 16)
                b = int(hex_cor[5:7], 16)
                r = r + (255 - r) * 4 // 5
                g = g + (255 - g) * 4 // 5
                b = b + (255 - b) * 4 // 5
                return f"#{r:02X}{g:02X}{b:02X}"
            except Exception:
                return THEME["primary_light"]

        badge_bg = _lighten(cor) if cor.startswith("#") else THEME["primary_light"]
        badge = tk.Frame(topo, bg=badge_bg, width=42, height=42)
        badge.pack(side="left")
        badge.pack_propagate(False)
        tk.Label(badge, text=dados["icone"], font=("Segoe UI", 18),
                 bg=badge_bg).place(relx=0.5, rely=0.5, anchor="center")

        val_frame = tk.Frame(topo, bg=THEME["bg_card"])
        val_frame.pack(side="right", anchor="e")
        tk.Label(val_frame, text=dados["valor"],
                 font=("Segoe UI", 26, "bold"),
                 bg=THEME["bg_card"], fg=cor).pack(anchor="e")

        tk.Frame(body, bg=THEME["border"], height=1).pack(fill="x", pady=(10, 8))

        rodape = tk.Frame(body, bg=THEME["bg_card"])
        rodape.pack(fill="x")
        tk.Label(rodape, text=dados["titulo"], font=FONT["bold"],
                 bg=THEME["bg_card"], fg=THEME["fg"]).pack(side="left")
        tk.Label(rodape, text=dados["sub"], font=FONT["sm"],
                 bg=THEME["bg_card"], fg=THEME["fg_light"]).pack(side="right")

    # ── Stats empresa ─────────────────────────────────────────────
    def _stats_empresa(self) -> list[dict]:
        try:
            from core.database import DatabaseManager
            db   = DatabaseManager.empresa()
            hoje = date.today().isoformat()
            v = db.fetchone(
                "SELECT COUNT(*) AS total, COALESCE(SUM(total),0) AS valor "
                "FROM vendas WHERE DATE(criado_em)=? AND status='FINALIZADA'", (hoje,)
            ) or {"total": 0, "valor": 0}
            ticket = (v["valor"] / v["total"]) if v["total"] else 0
            produtos = (db.fetchone("SELECT COUNT(*) AS t FROM produtos WHERE ativo=1") or {}).get("t", 0)
            clientes = (db.fetchone("SELECT COUNT(*) AS t FROM clientes WHERE ativo=1") or {}).get("t", 0)
            baixo    = (db.fetchone(
                "SELECT COUNT(*) AS t FROM produtos "
                "WHERE ativo=1 AND estoque_atual <= estoque_min AND estoque_min > 0"
            ) or {}).get("t", 0)
        except Exception:
            v = {"total": 0, "valor": 0}
            ticket = 0
            produtos = clientes = baixo = 0

        return [
            {"icone": "🛒", "titulo": "Vendas Hoje",   "valor": str(v["total"]),
             "sub": f"R$ {v['valor']:,.2f}",            "cor": THEME["primary"]},
            {"icone": "💲", "titulo": "Ticket Médio",  "valor": f"R${ticket:,.0f}",
             "sub": "por venda",                        "cor": "#1ABC9C"},
            {"icone": "📦", "titulo": "Produtos",       "valor": str(produtos),
             "sub": "cadastrados",                      "cor": THEME["success"]},
            {"icone": "👥", "titulo": "Clientes",       "valor": str(clientes),
             "sub": "ativos",                           "cor": "#8E44AD"},
            {"icone": "⚠",  "titulo": "Estoque Baixo", "valor": str(baixo),
             "sub": "produtos",                         "cor": THEME["warning"]},
        ]

    # ── Vendas recentes ───────────────────────────────────────────
    def _build_vendas_recentes(self, parent):
        card = self._section_card(parent, col=0, titulo="🧾  Vendas de Hoje")

        cols = ("Hora", "Cliente", "Itens", "Total")
        widths = (60, 160, 50, 90)

        tree = ttk.Treeview(card, columns=cols, show="headings",
                            height=10, selectmode="none")
        for c, w in zip(cols, widths):
            tree.heading(c, text=c, anchor="w")
            tree.column(c, width=w, minwidth=w, anchor="w")

        style = ttk.Style()
        style.configure("Dashboard.Treeview",
                        background=THEME["bg_card"],
                        fieldbackground=THEME["bg_card"],
                        rowheight=28,
                        font=FONT["sm"])
        style.configure("Dashboard.Treeview.Heading",
                        font=FONT["bold"],
                        background=THEME["row_alt"],
                        foreground=THEME["fg"])
        style.map("Dashboard.Treeview", background=[("selected", THEME["primary_light"])])
        tree.configure(style="Dashboard.Treeview")

        vsb = ttk.Scrollbar(card, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        tree.pack(fill="both", expand=True)

        tree.tag_configure("alt", background=THEME["row_alt"])

        rows = self._vendas_hoje()
        if not rows:
            tree.insert("", "end", values=("—", "Nenhuma venda registrada hoje", "", ""))
        else:
            for i, r in enumerate(rows):
                tag = ("alt",) if i % 2 else ()
                tree.insert("", "end", values=r, tags=tag)

    def _vendas_hoje(self) -> list[tuple]:
        try:
            from core.database import DatabaseManager
            db   = DatabaseManager.empresa()
            hoje = date.today().isoformat()
            rows = db.fetchall(
                "SELECT v.criado_em, COALESCE(c.nome,'—') AS cliente, "
                "       (SELECT COUNT(*) FROM itens_venda WHERE venda_id=v.id) AS itens, "
                "       v.total "
                "FROM vendas v LEFT JOIN clientes c ON c.id=v.cliente_id "
                "WHERE DATE(v.criado_em)=? AND v.status='FINALIZADA' "
                "ORDER BY v.criado_em DESC LIMIT 30", (hoje,)
            ) or []
            return [
                (r["criado_em"][11:16],
                 (r["cliente"] or "—")[:22],
                 r["itens"],
                 f"R$ {float(r['total']):,.2f}")
                for r in rows
            ]
        except Exception:
            return []

    # ── Alertas de estoque ────────────────────────────────────────
    def _build_alertas(self, parent):
        card = self._section_card(parent, col=1, titulo="⚠  Estoque Baixo")

        itens = self._estoque_baixo()
        if not itens:
            tk.Label(card, text="✓  Nenhum produto em estoque crítico",
                     font=FONT["sm"], bg=THEME["bg_card"],
                     fg=THEME["success"]).pack(anchor="w", pady=12)
            return

        for p in itens:
            row = tk.Frame(card, bg=THEME["bg_card"])
            row.pack(fill="x", pady=3)

            # Bolinha de cor
            nivel_cor = THEME["danger"] if p["atual"] == 0 else THEME["warning"]
            tk.Frame(row, bg=nivel_cor, width=8, height=8).pack(side="left",
                                                                  padx=(0, 8),
                                                                  pady=6)
            txt = tk.Frame(row, bg=THEME["bg_card"])
            txt.pack(side="left", fill="x", expand=True)
            tk.Label(txt, text=p["nome"][:28], font=FONT["sm"],
                     bg=THEME["bg_card"], fg=THEME["fg"],
                     anchor="w").pack(anchor="w")

            quant_txt = "Sem estoque" if p["atual"] == 0 else f"Restam: {p['atual']}"
            tk.Label(txt, text=f"{quant_txt}  (mín: {p['minimo']})",
                     font=FONT["xs"], bg=THEME["bg_card"],
                     fg=THEME["fg_light"], anchor="w").pack(anchor="w")

            tk.Frame(card, bg=THEME["border"], height=1).pack(fill="x")

    def _estoque_baixo(self) -> list[dict]:
        try:
            from core.database import DatabaseManager
            rows = DatabaseManager.empresa().fetchall(
                "SELECT nome, estoque_atual AS atual, estoque_min AS minimo "
                "FROM produtos "
                "WHERE ativo=1 AND estoque_atual <= estoque_min AND estoque_min > 0 "
                "ORDER BY estoque_atual ASC LIMIT 15"
            ) or []
            return [dict(r) for r in rows]
        except Exception:
            return []

    # ── Helper: section card ──────────────────────────────────────
    def _section_card(self, parent, col: int, titulo: str) -> tk.Frame:
        outer = tk.Frame(parent, bg=THEME["border"])
        outer.grid(row=0, column=col, padx=(0, 14) if col == 0 else 0,
                   sticky="nsew", ipadx=1, ipady=1)
        parent.rowconfigure(0, weight=1)

        card = tk.Frame(outer, bg=THEME["bg_card"])
        card.pack(fill="both", expand=True)

        hdr = tk.Frame(card, bg=THEME["row_alt"], padx=16, pady=10)
        hdr.pack(fill="x")
        tk.Label(hdr, text=titulo, font=FONT["bold"],
                 bg=THEME["row_alt"], fg=THEME["fg"]).pack(anchor="w")

        tk.Frame(card, bg=THEME["border"], height=1).pack(fill="x")

        body = tk.Frame(card, bg=THEME["bg_card"], padx=12, pady=10)
        body.pack(fill="both", expand=True)
        return body