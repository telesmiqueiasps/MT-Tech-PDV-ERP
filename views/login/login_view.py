import tkinter as tk
from tkinter import ttk
from views.base_view import BaseView
from config import THEME, FONT
from assets import Assets


class LoginView(BaseView):
    def __init__(self, master, empresa: dict):
        super().__init__(master, "Login - MT Tech", 480, 580, modal=True)
        self.resizable(False, False)
        Assets.icon(self)
        self._empresa       = empresa
        self._admin_global  = empresa.get("id") == 0
        self._usuario_selecionado = None
        self._build()

    def _build(self):
        # ── Header ───────────────────────────────────────────────
        header = tk.Frame(self, bg=THEME["primary_dark"], height=130)
        header.pack(fill="x")
        header.pack_propagate(False)

        logo = Assets.logo_branca(altura=40)
        if logo:
            self._logo_img = logo
            tk.Label(header, image=logo,
                     bg=THEME["primary_dark"]).pack(pady=(18, 4))

        tk.Label(header, text="ERP & PDV", font=("Segoe UI", 10),
                 bg=THEME["primary_dark"], fg=THEME["fg_white"]).pack()

        # ── Body ─────────────────────────────────────────────────
        body = tk.Frame(self, bg=THEME["bg"])
        body.pack(fill="both", expand=True, padx=30, pady=24)

        nome_empresa = ("Administração Global" if self._admin_global
                        else self._empresa.get("nome", ""))
        tk.Label(body, text=nome_empresa, font=FONT["lg"],
                 bg=THEME["bg"], fg=THEME["primary"]).pack(pady=(0, 16))

        if self._admin_global:
            self._build_form_direto(body)
        else:
            self._build_selecao_usuario(body)

    # ── Modo admin global: form direto ───────────────────────────
    def _build_form_direto(self, parent):
        card = tk.Frame(parent, bg="white",
                        highlightthickness=1,
                        highlightbackground=THEME["border"])
        card.pack(fill="x", pady=(0, 8))
        inner = tk.Frame(card, bg="white", padx=24, pady=20)
        inner.pack(fill="x")

        self._var_login = tk.StringVar()
        self._campo_entry(inner, "Usuário", self._var_login, focus=True)
        self._var_senha = tk.StringVar()
        self._campo_entry(inner, "Senha", self._var_senha, show="•")

        self._var_erro = tk.StringVar()
        tk.Label(parent, textvariable=self._var_erro, font=FONT["sm"],
                 bg=THEME["bg"], fg=THEME["danger"]).pack()

        tk.Button(parent, text="Entrar no Sistema →",
                  font=FONT["bold"], bg=THEME["primary"], fg="white",
                  relief="flat", cursor="hand2", pady=11,
                  command=self._login_admin).pack(fill="x", pady=(8, 0))

        self.bind("<Return>", lambda _: self._login_admin())

    # ── Modo empresa: cards de usuário ───────────────────────────
    def _build_selecao_usuario(self, parent):
        self._frame_usuarios = parent
        self._frame_senha    = None

        # Título
        tk.Label(parent, text="Quem vai entrar?", font=FONT["sm"],
                 bg=THEME["bg"], fg=THEME["fg_light"]).pack(anchor="w", pady=(0, 8))

        # Área scrollável de cards
        outer = tk.Frame(parent, bg=THEME["bg"])
        outer.pack(fill="both", expand=True)

        canvas = tk.Canvas(outer, bg=THEME["bg"],
                           highlightthickness=0, height=260)
        scroll = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        self._cards_frame = tk.Frame(canvas, bg=THEME["bg"])
        self._cards_win   = canvas.create_window(
            (0, 0), window=self._cards_frame, anchor="nw")

        self._cards_frame.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
            lambda e: canvas.itemconfig(self._cards_win, width=e.width))
        def _scroll(e):
            try:
                canvas.yview_scroll(int(-1*(e.delta/120)), "units")
            except tk.TclError:
                pass

        canvas.bind_all("<MouseWheel>", _scroll)
        canvas.bind("<Destroy>", lambda e: canvas.unbind_all("<MouseWheel>"))

        self._var_erro = tk.StringVar()
        tk.Label(parent, textvariable=self._var_erro, font=FONT["sm"],
                 bg=THEME["bg"], fg=THEME["danger"]).pack(pady=(6, 0))

        self._carregar_usuarios(self._cards_frame)

    def _carregar_usuarios(self, parent):
        for w in parent.winfo_children():
            w.destroy()

        try:
            from models.usuario import Usuario
            from core.database import DatabaseManager
            from pathlib import Path
            DatabaseManager.conectar_empresa(Path(self._empresa["db_path"]))
            usuarios = Usuario.listar()
        except Exception:
            usuarios = []

        if not usuarios:
            tk.Label(parent, text="Nenhum usuário cadastrado.",
                     font=FONT["sm"], bg=THEME["bg"],
                     fg=THEME["fg_light"]).pack(pady=20)
            return

        for u in usuarios:
            self._card_usuario(parent, u)

    def _card_usuario(self, parent, usuario: dict):
        """Card clicável para cada usuário."""
        frame = tk.Frame(parent, bg="white",
                         highlightthickness=1,
                         highlightbackground=THEME["border"],
                         cursor="hand2")
        frame.pack(fill="x", pady=(0, 8))

        inner = tk.Frame(frame, bg="white", padx=16, pady=12)
        inner.pack(fill="x")

        # Avatar com inicial
        inicial = (usuario.get("nome") or usuario.get("login", "?"))[0].upper()
        avatar  = tk.Frame(inner, bg=THEME["primary"], width=40, height=40)
        avatar.pack(side="left", padx=(0, 12))
        avatar.pack_propagate(False)
        tk.Label(avatar, text=inicial, font=("Segoe UI", 14, "bold"),
                 bg=THEME["primary"], fg="white").place(relx=0.5, rely=0.5,
                                                         anchor="center")

        # Texto
        info = tk.Frame(inner, bg="white")
        info.pack(side="left", fill="x", expand=True)
        tk.Label(info, text=usuario.get("nome") or usuario.get("login"),
                 font=FONT["bold"], bg="white",
                 fg=THEME["fg"]).pack(anchor="w")
        tk.Label(info, text=f"@{usuario.get('login')}  •  {usuario.get('perfil_nome','—')}",
                 font=FONT["sm"], bg="white",
                 fg=THEME["fg_light"]).pack(anchor="w")

        # Seta
        tk.Label(inner, text="›", font=("Segoe UI", 18),
                 bg="white", fg=THEME["fg_light"]).pack(side="right")

        # Hover
        def on_enter(e, f=frame, i=inner, av=avatar, inf=info):
            f.configure(highlightbackground=THEME["primary"])
            i.configure(bg=THEME["hover"])
            av.configure(bg=THEME["primary_dark"])
            for w in inf.winfo_children():
                w.configure(bg=THEME["hover"])

        def on_leave(e, f=frame, i=inner, av=avatar, inf=info):
            f.configure(highlightbackground=THEME["border"])
            i.configure(bg="white")
            av.configure(bg=THEME["primary"])
            for w in inf.winfo_children():
                w.configure(bg="white")

        for widget in [frame, inner, avatar, info] + list(info.winfo_children()):
            widget.bind("<Enter>", on_enter)
            widget.bind("<Leave>", on_leave)
            widget.bind("<Button-1>",
                lambda e, u=usuario: self._selecionar_usuario(u))

    def _selecionar_usuario(self, usuario: dict):
        """Ao clicar num card, mostra o painel de senha."""
        self._usuario_selecionado = usuario
        self._var_erro.set("")

        # Esconde área de cards
        for w in self._frame_usuarios.winfo_children():
            w.pack_forget()

        # Painel de senha
        painel = tk.Frame(self._frame_usuarios, bg=THEME["bg"])
        painel.pack(fill="both", expand=True)
        self._frame_senha = painel

        # Card do usuário selecionado (menor, não clicável)
        card_sel = tk.Frame(painel, bg=THEME["primary_light"],
                            highlightthickness=1,
                            highlightbackground=THEME["primary"])
        card_sel.pack(fill="x", pady=(0, 20))
        inner_sel = tk.Frame(card_sel, bg=THEME["primary_light"], padx=16, pady=10)
        inner_sel.pack(fill="x")

        inicial = (usuario.get("nome") or usuario.get("login","?"))[0].upper()
        av = tk.Frame(inner_sel, bg=THEME["primary"], width=36, height=36)
        av.pack(side="left", padx=(0,10))
        av.pack_propagate(False)
        tk.Label(av, text=inicial, font=("Segoe UI",13,"bold"),
                 bg=THEME["primary"], fg="white").place(relx=0.5,rely=0.5,anchor="center")

        info = tk.Frame(inner_sel, bg=THEME["primary_light"])
        info.pack(side="left", fill="x", expand=True)
        tk.Label(info, text=usuario.get("nome") or usuario.get("login"),
                 font=FONT["bold"], bg=THEME["primary_light"],
                 fg=THEME["primary_dark"]).pack(anchor="w")
        tk.Label(info, text=f"@{usuario.get('login')}",
                 font=FONT["sm"], bg=THEME["primary_light"],
                 fg=THEME["primary"]).pack(anchor="w")

        # Botão trocar usuário
        tk.Button(inner_sel, text="↩ Trocar", font=FONT["sm"],
                  bg=THEME["primary_light"], fg=THEME["primary"],
                  relief="flat", cursor="hand2",
                  command=self._voltar_selecao).pack(side="right")

        # Campo senha
        tk.Label(painel, text="Digite sua senha", font=FONT["sm"],
                 bg=THEME["bg"], fg=THEME["fg"]).pack(anchor="w", pady=(0,4))

        senha_frame = tk.Frame(painel, bg=THEME["bg"])
        senha_frame.pack(fill="x", pady=(0, 4))

        self._var_senha = tk.StringVar()
        entry_senha = tk.Entry(senha_frame, textvariable=self._var_senha,
                               show="•", font=FONT["md"],
                               relief="flat", bg="white", fg=THEME["fg"],
                               highlightthickness=1,
                               highlightbackground=THEME["border"],
                               highlightcolor=THEME["primary"])
        entry_senha.pack(fill="x", ipady=9)
        entry_senha.focus_set()

        # Erro
        self._var_erro = tk.StringVar()
        tk.Label(painel, textvariable=self._var_erro, font=FONT["sm"],
                 bg=THEME["bg"], fg=THEME["danger"]).pack(pady=(4,0))

        # Botão entrar
        tk.Button(painel, text="Entrar no Sistema →",
                  font=FONT["bold"], bg=THEME["primary"], fg="white",
                  relief="flat", cursor="hand2", pady=11,
                  command=self._login_usuario).pack(fill="x", pady=(12, 0))

        self.bind("<Return>", lambda _: self._login_usuario())

    def _voltar_selecao(self):
        """Volta para a lista de usuários."""
        self._usuario_selecionado = None
        if self._frame_senha:
            self._frame_senha.destroy()
            self._frame_senha = None
        self.unbind("<Return>")

        # Reconstrói a lista
        for w in self._frame_usuarios.winfo_children():
            w.pack_forget()

        self._build_selecao_usuario(self._frame_usuarios)

    # ── Login ────────────────────────────────────────────────────
    def _login_usuario(self):
        senha = self._var_senha.get()
        if not senha:
            self._var_erro.set("Digite sua senha."); return
        try:
            from core.auth import Auth, LicencaAuthError
            Auth.login_empresa(
                self._usuario_selecionado["login"],
                senha,
                self._empresa,
            )
            self.destroy()
        except LicencaAuthError as e:
            from tkinter import messagebox
            messagebox.showerror("Acesso Bloqueado", str(e), parent=self)
            self.destroy()
        except Exception as e:
            self._var_erro.set(str(e))
            self._var_senha.set("")

    def _login_admin(self):
        login = self._var_login.get().strip()
        senha = self._var_senha.get()
        if not login or not senha:
            self._var_erro.set("Preencha usuário e senha."); return
        try:
            from core.auth import Auth
            Auth.login_admin_global(login, senha)
            self.destroy()
        except Exception as e:
            self._var_erro.set(str(e))
            self._var_senha.set("")

    # ── Helpers ──────────────────────────────────────────────────
    def _campo_entry(self, parent, label, var, show="", focus=False):
        tk.Label(parent, text=label, font=FONT["sm"],
                 bg="white", fg=THEME["fg"]).pack(anchor="w", pady=(0,4))
        e = tk.Entry(parent, textvariable=var, show=show, font=FONT["md"],
                     relief="flat", bg="#f9fafb", fg=THEME["fg"],
                     highlightthickness=1,
                     highlightbackground=THEME["border"],
                     highlightcolor=THEME["primary"])
        e.pack(fill="x", ipady=9, pady=(0,12))
        if focus: e.focus_set()