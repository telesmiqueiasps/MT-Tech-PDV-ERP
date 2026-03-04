import tkinter as tk
from config import THEME, FONT, APP_NAME
from core.session import Session
from core.auth import Auth


class MainWindow:
    def __init__(self, root: tk.Tk):
        self._root = root
        self._root.title(APP_NAME)
        self._root.geometry("1280x768")
        self._root.minsize(1024, 600)
        self._root.configure(bg=THEME["bg"])
        self._centralizar()
        self._build()
        self._abrir_dashboard()

    def _centralizar(self):
        self._root.update_idletasks()
        x = (self._root.winfo_screenwidth()  - 1280) // 2
        y = (self._root.winfo_screenheight() - 768)  // 2
        self._root.geometry(f"1280x768+{x}+{y}")

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
        logo = tk.Frame(self._sidebar, bg=THEME["primary"], height=64)
        logo.pack(fill="x")
        logo.pack_propagate(False)
        tk.Label(logo, text=f"🏪  {APP_NAME}", font=FONT["bold"],
                 bg=THEME["primary"], fg=THEME["fg_white"]).pack(expand=True)

        info = tk.Frame(self._sidebar, bg=THEME["bg_sidebar"], pady=12)
        info.pack(fill="x")
        tk.Label(info, text=Session.usuario()["login"], font=FONT["bold"],
                 bg=THEME["bg_sidebar"], fg=THEME["fg_white"]).pack()
        tk.Label(info, text=Session.empresa()["nome"], font=FONT["sm"],
                 bg=THEME["bg_sidebar"], fg="#7F8C8D").pack()

        tk.Frame(self._sidebar, bg="#2C3E50", height=1).pack(fill="x")

        self._btns: dict[str, tk.Button] = {}
        for item in self._menu_items():
            if item is None:
                tk.Frame(self._sidebar, bg="#2C3E50", height=1).pack(fill="x", pady=4)
                continue
            btn = tk.Button(
                self._sidebar, text=item["texto"],
                font=FONT["sm"], anchor="w", padx=20, pady=10,
                bg=THEME["bg_sidebar"], fg="white",
                relief="flat", cursor="hand2",
                activebackground=THEME["primary"],
                activeforeground="white",
                command=item["cmd"],
            )
            btn.pack(fill="x")
            self._btns[item["id"]] = btn

        tk.Frame(self._sidebar, bg="#2C3E50", height=1).pack(fill="x", side="bottom")
        tk.Button(
            self._sidebar, text="⇠  Sair",
            font=FONT["sm"], anchor="w", padx=20, pady=10,
            bg=THEME["bg_sidebar"], fg=THEME["danger"],
            relief="flat", cursor="hand2",
            activebackground="#2C3E50",
            command=self._sair,
        ).pack(fill="x", side="bottom")

    def _menu_items(self) -> list:
        pode = Session.pode
        # Admin global só acessa Administração
        if Session.is_admin_global():
            return [
                {"id": "admin",       "texto": "⚙  Administração",    "cmd": self._abrir_admin},
                {"id": "fiscal_cfg",  "texto": "🧾  Config. Fiscal",  "cmd": self._abrir_fiscal_config},
                {"id": "auditoria",   "texto": "🔍  Auditoria",       "cmd": self._abrir_auditoria},
            ]

        itens = [
            {"id": "dashboard", "texto": "⊞  Dashboard", "cmd": self._abrir_dashboard},
        ]

        # ── PDV ──
        if pode("pdv", "ver"):
            itens.append(None)
            itens.append({"id": "pdv",   "texto": "🛒  PDV — Frente de Caixa", "cmd": self._abrir_pdv})
            itens.append({"id": "mesas", "texto": "🍽️  Mesas / Comandas",      "cmd": self._abrir_mesas})
            itens.append({"id": "caixa", "texto": "💵  Controle de Caixa",     "cmd": self._abrir_caixa})
            itens.append({"id": "vendas", "texto": "🧾  Vendas",     "cmd": self._abrir_vendas})

        itens.append(None)
        if pode("produtos", "ver"):
            itens.append({"id": "produtos",     "texto": "📦  Produtos",      "cmd": self._abrir_produtos})
        if pode("clientes", "ver"):
            itens.append({"id": "clientes",     "texto": "👥  Clientes",      "cmd": self._abrir_clientes})
        if pode("fornecedores", "ver"):
            itens.append({"id": "fornecedores", "texto": "🏭  Fornecedores",  "cmd": self._abrir_fornecedores})
        if pode("estoque", "ver"):
            itens.append({"id": "estoque",      "texto": "📊  Estoque",       "cmd": self._abrir_estoque})
        if pode("fiscal", "ver"):
            itens.append({"id": "fiscal",       "texto": "🧾  Notas Fiscais", "cmd": self._abrir_fiscal})
        itens.append(None)
        if pode("financeiro", "ver"):
            itens.append({"id": "financeiro",   "texto": "💰  Financeiro",    "cmd": self._em_breve})
        if pode("relatorios", "ver"):
            itens.append({"id": "relatorios",   "texto": "📈  Relatórios",    "cmd": self._em_breve})
        if pode("licenca", "ver"):
            itens.append({"id": "licenca",      "texto": "📋  Licenças",      "cmd": self._abrir_licencas})
        if Session.is_admin_global():
            itens.append({"id": "fiscal_gestao","texto": "⚖️  Gestão Fiscal", "cmd": self._abrir_gestao_fiscal})
        if Session.is_admin_global() or pode("admin", "ver"):
            itens.append(None)
            itens.append({"id": "admin",        "texto": "⚙  Administração",  "cmd": self._abrir_admin})
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
        Dashboard(self._conteudo)

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
        from views.pdv.pdv_view import PDVView
        PDVView(self._root, caixa)

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
            self._root.destroy()