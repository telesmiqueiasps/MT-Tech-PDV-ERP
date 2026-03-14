import tkinter as tk
from config import THEME, FONT, APP_NAME, APP_VERSION
from core.session import Session
from core.auth import Auth


class MainWindow:
    def __init__(self, root: tk.Tk, on_logout=None):
        self._root = root
        self._on_logout = on_logout
        self._root.title(APP_NAME)
        self._root.geometry("1280x768")
        self._root.minsize(1024, 600)
        self._root.configure(bg=THEME["bg"])
        self._root.geometry("1280x768")
        self._root.state("zoomed")
        self._build()
        self._abrir_dashboard()

    def _build(self):
        self._sidebar = tk.Frame(self._root, bg=THEME["bg_sidebar"], width=220)
        self._sidebar.pack(side="left", fill="y")
        self._sidebar.pack_propagate(False)

        self._area = tk.Frame(self._root, bg=THEME["bg"])
        self._area.pack(side="left", fill="both", expand=True)

        self._build_sidebar()
        self._build_topbar()

        self._conteudo = tk.Frame(self._area, bg=THEME["bg"])
        self._conteudo.pack(fill="both", expand=True)

    def _build_sidebar(self):
        self._collapsed = False

        # ── Logo (fixo) ───────────────────────────────────────────
        self._logo_frame = tk.Frame(self._sidebar, bg=THEME["primary"], height=64)
        self._logo_frame.pack(fill="x")
        self._logo_frame.pack_propagate(False)

        from assets import Assets
        img_logo = Assets.logo_branca(altura=36)

        self._logo_wrap = tk.Frame(self._logo_frame, bg=THEME["primary"])
        self._logo_wrap.pack(side="left", fill="both", expand=True)
        if img_logo:
            lbl_logo = tk.Label(self._logo_wrap, image=img_logo, bg=THEME["primary"])
            lbl_logo._img = img_logo
            lbl_logo.pack(expand=True)
        else:
            tk.Label(self._logo_wrap, text=APP_NAME, font=FONT["bold"],
                     bg=THEME["primary"], fg=THEME["fg_white"]).pack(expand=True)

        self._btn_toggle = tk.Button(
            self._logo_frame, text="◀",
            font=("Segoe UI", 11, "bold"),
            bg=THEME["primary"], fg="white",
            relief="flat", cursor="hand2",
            activebackground=THEME["primary_dark"],
            activeforeground="white",
            command=self._toggle_sidebar,
        )
        self._btn_toggle.pack(side="right", padx=6)

        # ── Seção recolhível (info + busca) ──────────────────────
        self._sidebar_extras = tk.Frame(self._sidebar, bg=THEME["bg_sidebar"])
        self._sidebar_extras.pack(fill="x")

        info = tk.Frame(self._sidebar_extras, bg=THEME["bg_sidebar"], pady=12)
        info.pack(fill="x")
        tk.Label(info, text=Session.usuario()["login"], font=FONT["bold"],
                 bg=THEME["bg_sidebar"], fg=THEME["fg_white"]).pack()
        tk.Label(info, text=Session.empresa()["nome"], font=FONT["sm"],
                 bg=THEME["bg_sidebar"], fg="#BDD7EE").pack()

        tk.Frame(self._sidebar_extras, bg="#2C3E50", height=1).pack(fill="x")

        search_wrap = tk.Frame(self._sidebar_extras, bg=THEME["bg_sidebar"], padx=12, pady=8)
        search_wrap.pack(fill="x")

        search_box = tk.Frame(search_wrap, bg="#3A8AC4",
                              highlightthickness=1,
                              highlightbackground="#4A9AD4")
        search_box.pack(fill="x")

        tk.Label(search_box, text="🔍", font=("Segoe UI", 10),
                 bg="#3A8AC4", fg="#BDD7EE").pack(side="left", padx=(8, 0))

        self._var_busca = tk.StringVar()
        self._var_busca.trace_add("write", self._filtrar_menu)
        tk.Entry(search_box, textvariable=self._var_busca,
                 font=FONT["sm"], relief="flat",
                 bg="#3A8AC4", fg="white",
                 insertbackground="white",
                 highlightthickness=0).pack(side="left", fill="x",
                                            expand=True, ipady=6, padx=6)

        tk.Frame(self._sidebar_extras, bg="#2C3E50", height=1).pack(fill="x")

        # ── Sair (fixo, embaixo) ──────────────────────────────────
        _sair_container = tk.Frame(self._sidebar, bg="#1a4f75")
        _sair_container.pack(fill="x", side="bottom")
        tk.Frame(_sair_container, bg="#143f5f", height=1).pack(fill="x")
        self._lbl_versao = tk.Label(
            _sair_container, text=f"v{APP_VERSION}",
            font=("Segoe UI", 8), bg="#1a4f75", fg="#7aafc8",
        )
        self._lbl_versao.pack(pady=(5, 0))
        self._btn_sair = tk.Button(
            _sair_container, text="⏻  Sair do Sistema",
            font=("Segoe UI", 10, "bold"), anchor="w", padx=20, pady=11,
            bg="#1a4f75", fg="#FF6B6B",
            relief="flat", cursor="hand2",
            activebackground="#143f5f",
            activeforeground="#FF8E8E",
            command=self._sair,
        )
        self._btn_sair.pack(fill="x")
        self._btn_sair.bind("<Enter>", lambda _: self._btn_sair.configure(bg="#143f5f"))
        self._btn_sair.bind("<Leave>", lambda _: self._btn_sair.configure(bg="#1a4f75"))
        self._sair_container = _sair_container

        # ── Área scrollável dos itens de menu ─────────────────────
        self._menu_canvas = tk.Canvas(self._sidebar, bg=THEME["bg_sidebar"],
                                      highlightthickness=0)
        self._menu_canvas.pack(fill="both", expand=True)

        self._menu_frame = tk.Frame(self._menu_canvas, bg=THEME["bg_sidebar"])
        self._menu_canvas_win = self._menu_canvas.create_window(
            (0, 0), window=self._menu_frame, anchor="nw")

        self._menu_frame.bind("<Configure>", self._on_menu_configure)
        self._menu_canvas.bind("<Configure>",
            lambda e: self._menu_canvas.itemconfig(
                self._menu_canvas_win, width=e.width))

        # Mouse wheel no canvas e nos botões
        for widget in (self._menu_canvas, self._menu_frame):
            widget.bind("<MouseWheel>", self._scroll_menu)
            widget.bind("<Enter>",
                lambda _, w=widget: w.bind_all("<MouseWheel>", self._scroll_menu))
            widget.bind("<Leave>",
                lambda _, w=widget: w.unbind_all("<MouseWheel>"))

        # Monta os botões
        self._btns: dict[str, tk.Button] = {}
        self._all_items = self._menu_items()
        self._separadores: list[tk.Frame] = []
        self._item_widgets: list[tuple] = []  # (item_dict | None, widget)

        for item in self._all_items:
            if item is None:
                sep = tk.Frame(self._menu_frame, bg="#2C3E50", height=1)
                sep.pack(fill="x", pady=4)
                self._separadores.append(sep)
                self._item_widgets.append((None, sep))
                continue

            img = Assets.icone_menu(item["icone"], tamanho=22) if item.get("icone") else None
            btn_kw = dict(
                text=item["texto"],
                font=FONT["sm"], anchor="w", padx=16, pady=9,
                bg=THEME["bg_sidebar"], fg="white",
                relief="flat", cursor="hand2",
                activebackground=THEME["primary"],
                activeforeground="white",
                command=item["cmd"],
            )
            if img:
                btn_kw["image"]    = img
                btn_kw["compound"] = "left"
            btn = tk.Button(self._menu_frame, **btn_kw)
            if img:
                btn._img = img   # evita GC
            btn.pack(fill="x")
            btn.bind("<MouseWheel>", self._scroll_menu)
            self._btns[item["id"]] = btn
            self._item_widgets.append((item, btn))

    def _toggle_sidebar(self):
        self._collapsed = not self._collapsed

        if self._collapsed:
            self._sidebar.configure(width=56)
            self._logo_wrap.pack_forget()
            self._sidebar_extras.pack_forget()
            self._btn_toggle.configure(text="▶")
            self._btn_sair.configure(text="⏻", anchor="center", padx=0)
            self._lbl_versao.pack_forget()
            for item, widget in self._item_widgets:
                if item is None:
                    continue
                if item.get("icone"):
                    widget.configure(text="", anchor="center", padx=0, compound="center")
                else:
                    # Extrai emoji do início do texto (ex: "🔍  Auditoria" → "🔍")
                    emoji = item["texto"].strip()[:2]
                    widget.configure(text=emoji, anchor="center", padx=0, compound="none")
        else:
            self._sidebar.configure(width=220)
            self._logo_wrap.pack(side="left", fill="both", expand=True,
                                 before=self._btn_toggle)
            self._sidebar_extras.pack(fill="x", after=self._logo_frame)
            self._btn_toggle.configure(text="◀")
            self._btn_sair.configure(text="⏻  Sair do Sistema", anchor="w", padx=20)
            self._lbl_versao.pack(pady=(5, 0), before=self._btn_sair)
            for item, widget in self._item_widgets:
                if item is None:
                    continue
                widget.configure(
                    text=item["texto"],
                    anchor="w",
                    padx=16,
                    compound="left" if item.get("icone") else "none",
                )

    def _on_menu_configure(self, _=None):
        self._menu_canvas.configure(
            scrollregion=self._menu_canvas.bbox("all"))

    def _scroll_menu(self, event):
        try:
            self._menu_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        except tk.TclError:
            pass

    def _filtrar_menu(self, *_):
        termo = self._var_busca.get().strip().lower()
        filtrando = bool(termo)

        # Remove todos primeiro para preservar a ordem original ao reempacotar
        for _, widget in self._item_widgets:
            widget.pack_forget()

        for item, widget in self._item_widgets:
            if item is None:
                if not filtrando:
                    widget.pack(fill="x", pady=4)
                continue
            texto_limpo = item["texto"].strip().lower()
            if not filtrando or termo in texto_limpo:
                widget.pack(fill="x")

        self._menu_frame.update_idletasks()
        self._on_menu_configure()

    def _menu_items(self) -> list:
        pode = Session.pode
        # Admin global só acessa Administração
        if Session.is_admin_global():
            return [
                {"id": "admin",     "icone": "config", "texto": "  Administração", "cmd": self._abrir_admin},
                {"id": "auditoria", "icone": None,     "texto": "🔍  Auditoria",   "cmd": self._abrir_auditoria},
            ]

        itens = [
            {"id": "dashboard", "icone": "dashboard", "texto": "  Dashboard", "cmd": self._abrir_dashboard},
        ]

        # ── PDV ──
        pdv_block = []
        if pode("pdv", "ver"):
            pdv_block.append({"id": "pdv",    "icone": "pdv",    "texto": "  Ponto de Venda (PDV)", "cmd": self._abrir_pdv})
        if pode("mesas", "ver"):
            pdv_block.append({"id": "mesas",  "icone": "mesa",   "texto": "  Mesas & Comandas",      "cmd": self._abrir_mesas})
        if pode("caixa", "ver"):
            pdv_block.append({"id": "caixa",  "icone": "caixa",  "texto": "  Controle de Caixa",     "cmd": self._abrir_caixa})
        if pode("vendas", "ver"):
            pdv_block.append({"id": "vendas", "icone": "vendas", "texto": "  Vendas",                "cmd": self._abrir_vendas})
        if pdv_block:
            itens.append(None)
            itens.extend(pdv_block)

        itens.append(None)
        if pode("produtos", "ver"):
            itens.append({"id": "produtos",     "icone": "produtos",     "texto": "  Produtos",      "cmd": self._abrir_produtos})
        if pode("clientes", "ver"):
            itens.append({"id": "clientes",     "icone": "clientes",     "texto": "  Clientes",      "cmd": self._abrir_clientes})
        if pode("fornecedores", "ver"):
            itens.append({"id": "fornecedores", "icone": "fornecedores", "texto": "  Fornecedores",  "cmd": self._abrir_fornecedores})
        if pode("estoque", "ver"):
            itens.append({"id": "estoque",      "icone": "estoque",      "texto": "  Estoque",       "cmd": self._abrir_estoque})
        if pode("fiscal", "ver"):
            itens.append({"id": "fiscal",       "icone": "notas",        "texto": "  Notas Fiscais",  "cmd": self._abrir_fiscal})
        if pode("fiscal_cfg", "ver"):
            itens.append({"id": "fiscal_cfg",   "icone": "ajustar",      "texto": "  Config. Fiscal", "cmd": self._abrir_fiscal_config})
        itens.append(None)
        if pode("financeiro", "ver"):
            itens.append({"id": "financeiro",   "icone": "financeiro",   "texto": "  Financeiro",    "cmd": self._em_breve})
        if pode("relatorios", "ver"):
            itens.append({"id": "relatorios",   "icone": "relatorios",   "texto": "  Relatórios",    "cmd": self._em_breve})
        if pode("licenca", "ver"):
            itens.append({"id": "licenca",      "icone": "licença",      "texto": "  Licenças",      "cmd": self._abrir_licencas})
        if Session.is_admin_global() or pode("admin", "ver"):
            itens.append(None)
            itens.append({"id": "admin",        "icone": "config",       "texto": "  Administração", "cmd": self._abrir_admin})
        return itens

    def _build_topbar(self):
        topbar = tk.Frame(self._area, bg=THEME["bg_card"], height=48)
        topbar.pack(fill="x")
        topbar.pack_propagate(False)
        tk.Frame(topbar, bg=THEME["border"], height=1).pack(fill="x", side="bottom")
        self._lbl_modulo = tk.Label(topbar, text="Dashboard",
                                     font=FONT["bold"], bg=THEME["bg_card"], fg=THEME["fg"])
        self._lbl_modulo.pack(side="left", padx=20)

    def _set_ativo(self, id_btn: str, titulo: str):
        self._lbl_modulo.configure(text=titulo)
        for bid, btn in self._btns.items():
            btn.configure(bg=THEME["primary"] if bid == id_btn else THEME["bg_sidebar"])

    def _limpar(self):
        for w in self._conteudo.winfo_children():
            w.destroy()

    # ── Navegação existente ───────────────────────────────────

    def _abrir_dashboard(self):
        self._limpar()
        self._set_ativo("dashboard", "Dashboard")
        from views.main.dashboard import Dashboard
        nav = {
            "pdv":          self._abrir_pdv,
            "mesas":        self._abrir_mesas,
            "caixa":        self._abrir_caixa,
            "vendas":       self._abrir_vendas,
            "produtos":     self._abrir_produtos,
            "clientes":     self._abrir_clientes,
            "fornecedores": self._abrir_fornecedores,
            "estoque":      self._abrir_estoque,
            "fiscal":       self._abrir_fiscal,
            "admin":        self._abrir_admin,
        }
        Dashboard(self._conteudo, navegacao=nav)

    def _abrir_admin(self):
        self._limpar()
        self._set_ativo("admin", "Administração")
        from views.admin.admin_view import AdminView
        AdminView(self._conteudo)

    def _abrir_produtos(self):
        self._limpar()
        self._set_ativo("produtos", "Produtos")
        from views.produtos.produtos_view import ProdutosView
        ProdutosView(self._conteudo)

    def _abrir_licencas(self):
        self._limpar()
        self._set_ativo("licenca", "Licenças")
        from views.fiscal.licenca_view import TelaLicenca
        TelaLicenca(self._conteudo)

    def _abrir_fiscal_config(self):
        self._limpar()
        self._set_ativo("fiscal_cfg", "Configurações Fiscais")
        from views.fiscal.fiscal_config_view import FiscalConfigView
        FiscalConfigView(self._conteudo)

    def _abrir_auditoria(self):
        self._limpar()
        self._set_ativo("auditoria", "Auditoria do Sistema")
        from views.admin.audit_view import AuditView
        AuditView(self._conteudo)

    def _abrir_fiscal(self):
        self._limpar()
        self._set_ativo("fiscal", "Notas Fiscais")
        from views.fiscal.notas_view import NotasView
        NotasView(self._conteudo)

    def _abrir_gestao_fiscal(self):
        self._limpar()
        self._set_ativo("fiscal_gestao", "Gestão Fiscal")
        from views.fiscal.fiscal_config_view import GestaoFiscalView
        GestaoFiscalView(self._conteudo)

    def _abrir_estoque(self):
        self._limpar()
        self._set_ativo("estoque", "Estoque")
        from views.estoque.estoque_view import EstoqueView
        EstoqueView(self._conteudo)

    def _abrir_clientes(self):
        self._limpar()
        self._set_ativo("clientes", "Clientes")
        from views.clientes.clientes_view import ClientesView
        ClientesView(self._conteudo)

    def _abrir_fornecedores(self):
        self._limpar()
        self._set_ativo("fornecedores", "Fornecedores")
        from views.fornecedores.fornecedores_view import FornecedoresView
        FornecedoresView(self._conteudo)

    # ── PDV (novos) ───────────────────────────────────────────

    def _abrir_pdv(self):
        """Abre o PDV varejo. Verifica se operador tem caixa aberto."""
        from models.caixa import Caixa
        # Session.usuario() retorna o dict do usuário logado
        usuario = Session.usuario()
        usuario_id = usuario.get("id")

        caixa = Caixa.aberto_do_operador(usuario_id)
        if not caixa:
            from tkinter import messagebox
            if not messagebox.askyesno(
                "Caixa não aberto",
                "Você não tem um caixa aberto.\nDeseja abrir o caixa agora?",
                parent=self._root,
            ):
                return
            self._abrir_caixa()
            return
        self._limpar()
        self._set_ativo("pdv", "Ponto de Venda (PDV)")
        from views.pdv.pdv_view import PDVView
        PDVView(self._conteudo, caixa).pack(fill="both", expand=True)

    def _abrir_mesas(self):
        self._limpar()
        self._set_ativo("mesas", "Mesas / Comandas")
        from views.pdv.mesas_view import MesasView
        MesasView(self._conteudo).pack(fill="both", expand=True)

    def _abrir_caixa(self):
        self._limpar()
        self._set_ativo("caixa", "Controle de Caixa")
        from views.pdv.caixa_view import CaixaView
        CaixaView(self._conteudo).pack(fill="both", expand=True)

    def _abrir_vendas(self):
        self._limpar()
        self._set_ativo("vendas", "Vendas")
        from views.pdv.vendas_view import VendasView
        VendasView(self._conteudo).pack(fill="both", expand=True)

    # ── Utilitários ───────────────────────────────────────────

    def _em_breve(self):
        self._limpar()
        tk.Label(self._conteudo, text="🚧  Módulo em desenvolvimento",
                 font=FONT["title"], bg=THEME["bg"],
                 fg=THEME["fg_light"]).pack(expand=True)

    def _sair(self):
        from tkinter import messagebox
        if messagebox.askyesno("Sair", "Deseja encerrar a sessão?", parent=self._root):
            Auth.logout()
            if self._on_logout:
                self._on_logout()
            else:
                self._root.destroy()