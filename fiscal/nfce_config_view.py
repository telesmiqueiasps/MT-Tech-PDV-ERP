"""Janela de configuração da NFC-e."""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from config import THEME, FONT


class NfceConfigView(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Configuração NFC-e")
        self.configure(bg=THEME["bg"])
        self.resizable(True, True)
        self.grab_set()
        self._build()
        self._centralizar(520, 680)
        self._carregar()

    def _centralizar(self, w, h):
        self.update_idletasks()
        x = (self.winfo_screenwidth()  - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _build(self):
        header = tk.Frame(self, bg=THEME["primary"], pady=14)
        header.pack(fill="x")
        tk.Label(header, text="Configuração NFC-e", font=FONT["lg_bold"],
                 bg=THEME["primary"], fg="white").pack()

        body = tk.Frame(self, bg=THEME["bg"], padx=24, pady=16)
        body.pack(fill="both", expand=True)

        def campo(parent, label_text, var, show=None, readonly=False):
            tk.Label(parent, text=label_text, font=FONT["sm"],
                     bg=THEME["bg"], fg=THEME["fg"]).pack(anchor="w", pady=(8, 2))
            kwargs = {}
            if show:
                kwargs["show"] = show
            e = tk.Entry(parent, textvariable=var, font=FONT["md"], relief="flat",
                         bg=THEME["bg_input"], fg=THEME["fg"],
                         highlightthickness=1, highlightbackground=THEME["border"],
                         highlightcolor=THEME["primary"],
                         **kwargs)
            if readonly:
                e.configure(state="readonly")
            e.pack(fill="x", ipady=6)
            return e

        # ── Ambiente ─────────────────────────────────────────────────
        tk.Label(body, text="Ambiente", font=FONT["sm"],
                 bg=THEME["bg"], fg=THEME["fg"]).pack(anchor="w", pady=(8, 2))
        amb_frame = tk.Frame(body, bg=THEME["bg"])
        amb_frame.pack(anchor="w")
        self._var_amb = tk.IntVar(value=2)
        tk.Radiobutton(amb_frame, text="Homologação (teste)",
                       variable=self._var_amb, value=2,
                       bg=THEME["bg"], fg=THEME["fg"],
                       activebackground=THEME["bg"],
                       font=FONT["sm"]).pack(side="left")
        rb_prod = tk.Radiobutton(amb_frame, text="Produção",
                                  variable=self._var_amb, value=1,
                                  bg=THEME["bg"], fg=THEME["fg_light"],
                                  activebackground=THEME["bg"],
                                  font=FONT["sm"], state="disabled")
        rb_prod.pack(side="left", padx=(16, 0))
        tk.Label(amb_frame, text="(ative somente após homologação aprovada)",
                 font=FONT["xs"], bg=THEME["bg"], fg=THEME["fg_light"]).pack(side="left", padx=(4, 0))

        # ── Campos ───────────────────────────────────────────────────
        self._var_serie  = tk.StringVar()
        self._var_num    = tk.StringVar()
        self._var_csc_id = tk.StringVar()
        self._var_csc_tk = tk.StringVar()
        self._var_cert   = tk.StringVar()
        self._var_senha  = tk.StringVar()

        campo(body, "Série", self._var_serie)
        campo(body, "Próximo Número", self._var_num)
        campo(body, "CSC ID (6 dígitos — portal SEFAZ)", self._var_csc_id)
        campo(body, "CSC Token", self._var_csc_tk)

        # Certificado
        tk.Label(body, text="Certificado Digital (.pfx)", font=FONT["sm"],
                 bg=THEME["bg"], fg=THEME["fg"]).pack(anchor="w", pady=(8, 2))
        cert_row = tk.Frame(body, bg=THEME["bg"])
        cert_row.pack(fill="x")
        tk.Entry(cert_row, textvariable=self._var_cert, font=FONT["md"],
                 relief="flat", bg=THEME["bg_input"], fg=THEME["fg"],
                 highlightthickness=1, highlightbackground=THEME["border"],
                 state="readonly").pack(side="left", fill="x", expand=True, ipady=6)
        tk.Button(cert_row, text="Selecionar", font=FONT["sm"],
                  bg=THEME["primary"], fg="white", relief="flat", padx=8,
                  command=self._selecionar_cert).pack(side="left", padx=(6, 0))

        campo(body, "Senha do Certificado", self._var_senha, show="•")

        # ── Botões de teste ──────────────────────────────────────────
        btn_frame = tk.Frame(body, bg=THEME["bg"])
        btn_frame.pack(fill="x", pady=(12, 0))
        tk.Button(btn_frame, text="Testar Certificado", font=FONT["sm"],
                  bg=THEME["secondary"], fg="white", relief="flat", padx=10,
                  command=self._testar_cert).pack(side="left")
        tk.Button(btn_frame, text="Testar Conexão SEFAZ", font=FONT["sm"],
                  bg=THEME["secondary"], fg="white", relief="flat", padx=10,
                  command=self._testar_sefaz).pack(side="left", padx=(8, 0))

        # ── Rodapé ───────────────────────────────────────────────────
        rodape = tk.Frame(self, bg=THEME["bg_card"],
                          highlightthickness=1, highlightbackground=THEME["border"],
                          padx=16, pady=10)
        rodape.pack(fill="x", side="bottom")
        tk.Button(rodape, text="Salvar", font=FONT["bold"],
                  bg=THEME["primary"], fg="white", relief="flat", padx=20, pady=6,
                  command=self._salvar).pack(side="right")
        tk.Button(rodape, text="Cancelar", font=FONT["sm"],
                  bg=THEME["bg_card"], fg=THEME["fg_light"], relief="flat", padx=14,
                  command=self.destroy).pack(side="right", padx=(0, 8))

    def _carregar(self):
        try:
            from fiscal.nfce_config_model import NfceConfig
            cfg = NfceConfig.carregar()
            if cfg:
                self._var_amb.set(cfg.get("ambiente", 2))
                self._var_serie.set(str(cfg.get("serie", 1)))
                self._var_num.set(str(cfg.get("proximo_numero", 1)))
                self._var_csc_id.set(cfg.get("id_csc") or cfg.get("csc_id") or "")
                self._var_csc_tk.set(cfg.get("csc_token") or "")
                self._var_cert.set(cfg.get("cert_path") or "")
        except Exception:
            pass

    def _selecionar_cert(self):
        path = filedialog.askopenfilename(
            parent=self,
            title="Selecionar Certificado .pfx",
            filetypes=[("Certificado PKCS#12", "*.pfx *.p12"), ("Todos", "*.*")],
        )
        if path:
            self._var_cert.set(path)

    def _testar_cert(self):
        cert_path = self._var_cert.get().strip()
        senha     = self._var_senha.get()
        if not cert_path:
            messagebox.showwarning("Atenção", "Selecione o arquivo .pfx primeiro.", parent=self)
            return
        try:
            from fiscal.certificado import Certificado
            cnpj     = Certificado.cnpj_certificado(cert_path, senha)
            validade = Certificado.validade(cert_path, senha)
            messagebox.showinfo(
                "Certificado OK",
                f"CNPJ: {cnpj}\nVálido até: {validade.strftime('%d/%m/%Y')}",
                parent=self,
            )
        except Exception as e:
            messagebox.showerror("Erro no Certificado", str(e), parent=self)

    def _testar_sefaz(self):
        try:
            from fiscal.nfce_service import NfceService
            result = NfceService().consultar_status_sefaz()
            if result.get("online"):
                messagebox.showinfo("SEFAZ", f"Conexão OK\n{result.get('motivo','')}", parent=self)
            else:
                messagebox.showwarning("SEFAZ", f"Falha na conexão:\n{result.get('motivo','')}", parent=self)
        except Exception as e:
            messagebox.showerror("Erro", str(e), parent=self)

    def _salvar(self):
        try:
            dados = {
                "ambiente":        self._var_amb.get(),
                "serie":           int(self._var_serie.get() or 1),
                "proximo_numero":  int(self._var_num.get() or 1),
                "id_csc":          self._var_csc_id.get().strip(),
                "csc_token":       self._var_csc_tk.get().strip(),
                "cert_path":       self._var_cert.get().strip(),
                "ativo":           1,
            }
            if self._var_senha.get():
                dados["cert_senha"] = self._var_senha.get()
            from fiscal.nfce_config_model import NfceConfig
            NfceConfig.salvar(dados)
            messagebox.showinfo("Salvo", "Configuração NFC-e salva com sucesso.", parent=self)
            self.destroy()
        except Exception as e:
            messagebox.showerror("Erro", str(e), parent=self)
