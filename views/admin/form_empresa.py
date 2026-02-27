import tkinter as tk
from tkinter import ttk, filedialog
from config import THEME, FONT
from views.base_view import BaseView
from views.widgets.widgets import SecaoForm, CampoEntry, botao
from views.widgets.municipio_widget import MunicipioWidget

REGIMES   = ["1 — Simples Nacional", "2 — Simples Nacional Excesso", "3 — Regime Normal"]
AMBIENTES = ["2 — Homologação", "1 — Produção"]


class FormEmpresa(BaseView):
    def __init__(self, master, empresa_id: int | None, ao_salvar=None):
        titulo = "Editar Empresa" if empresa_id else "Nova Empresa"
        super().__init__(master, titulo, 620, 720, modal=True)
        self.resizable(True, True)
        self._empresa_id = empresa_id
        self._ao_salvar  = ao_salvar
        self._build()
        if empresa_id:
            self._preencher()

    def _build(self):
        canvas = tk.Canvas(self, bg=THEME["bg"], highlightthickness=0)
        scroll = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True)
        body = tk.Frame(canvas, bg=THEME["bg"])
        win  = canvas.create_window((0, 0), window=body, anchor="nw")
        body.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
            lambda e: canvas.itemconfig(win, width=e.width))
        canvas.bind_all("<MouseWheel>",
            lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

        P = 24
        tk.Label(body, text="Editar Empresa" if self._empresa_id else "Nova Empresa",
                 font=FONT["title"], bg=THEME["bg"],
                 fg=THEME["fg"]).pack(anchor="w", padx=P, pady=(20, 16))

        # ── IDENTIFICAÇÃO ────────────────────────────────────────
        SecaoForm(body, "IDENTIFICAÇÃO").pack(fill="x", padx=P)
        c1 = self._card(body, P)

        self._var_nome  = tk.StringVar()
        self._var_razao = tk.StringVar()
        CampoEntry(c1, "Nome Fantasia *",  self._var_nome).pack(fill="x", pady=(0, 10))
        CampoEntry(c1, "Razão Social *",   self._var_razao).pack(fill="x", pady=(0, 10))

        row1 = tk.Frame(c1, bg=THEME["bg_card"])
        row1.pack(fill="x", pady=(0, 10))
        self._var_cnpj = tk.StringVar()
        self._var_ie   = tk.StringVar()
        CampoEntry(row1, "CNPJ *", self._var_cnpj).pack(
            side="left", fill="x", expand=True, padx=(0, 8))
        CampoEntry(row1, "Inscrição Estadual", self._var_ie).pack(
            side="left", fill="x", expand=True, padx=(8, 0))

        row2 = tk.Frame(c1, bg=THEME["bg_card"])
        row2.pack(fill="x", pady=(0, 10))
        self._var_im   = tk.StringVar()
        self._var_cnae = tk.StringVar()
        CampoEntry(row2, "Inscrição Municipal", self._var_im).pack(
            side="left", fill="x", expand=True, padx=(0, 8))
        CampoEntry(row2, "CNAE Principal", self._var_cnae).pack(
            side="left", fill="x", expand=True, padx=(8, 0))

        row3 = tk.Frame(c1, bg=THEME["bg_card"])
        row3.pack(fill="x", pady=(0, 4))

        col_reg = tk.Frame(row3, bg=THEME["bg_card"])
        col_reg.pack(side="left", fill="x", expand=True, padx=(0, 8))
        tk.Label(col_reg, text="Regime Tributário *", font=FONT["sm"],
                 bg=THEME["bg_card"], fg=THEME["fg"]).pack(anchor="w", pady=(0, 3))
        self._var_regime = tk.StringVar()
        self._combo_regime = ttk.Combobox(col_reg, textvariable=self._var_regime,
                                           values=REGIMES, state="readonly", font=FONT["md"])
        self._combo_regime.current(0)
        self._combo_regime.pack(fill="x", ipady=4)

        col_amb = tk.Frame(row3, bg=THEME["bg_card"])
        col_amb.pack(side="left", fill="x", expand=True, padx=(8, 0))
        tk.Label(col_amb, text="Ambiente Fiscal", font=FONT["sm"],
                 bg=THEME["bg_card"], fg=THEME["fg"]).pack(anchor="w", pady=(0, 3))
        self._var_ambiente = tk.StringVar()
        self._combo_amb = ttk.Combobox(col_amb, textvariable=self._var_ambiente,
                                        values=AMBIENTES, state="readonly", font=FONT["md"])
        self._combo_amb.current(0)
        self._combo_amb.pack(fill="x", ipady=4)

        # ── CONTATO ──────────────────────────────────────────────
        SecaoForm(body, "CONTATO").pack(fill="x", padx=P, pady=(8, 0))
        c2 = self._card(body, P)
        row4 = tk.Frame(c2, bg=THEME["bg_card"])
        row4.pack(fill="x", pady=(0, 4))
        self._var_email    = tk.StringVar()
        self._var_telefone = tk.StringVar()
        CampoEntry(row4, "E-mail", self._var_email).pack(
            side="left", fill="x", expand=True, padx=(0, 8))
        CampoEntry(row4, "Telefone", self._var_telefone).pack(
            side="left", fill="x", expand=True, padx=(8, 0))

        # ── ENDEREÇO ─────────────────────────────────────────────
        SecaoForm(body, "ENDEREÇO").pack(fill="x", padx=P, pady=(8, 0))
        c3 = self._card(body, P)

        row_cep = tk.Frame(c3, bg=THEME["bg_card"])
        row_cep.pack(fill="x", pady=(0, 10))
        self._var_cep = tk.StringVar()
        CampoEntry(row_cep, "CEP", self._var_cep).pack(
            side="left", fill="x", expand=True, padx=(0, 8))
        col_num = tk.Frame(row_cep, bg=THEME["bg_card"], width=100)
        col_num.pack(side="left")
        col_num.pack_propagate(False)
        self._var_numero = tk.StringVar()
        CampoEntry(col_num, "Número", self._var_numero).pack(fill="x")

        row_end = tk.Frame(c3, bg=THEME["bg_card"])
        row_end.pack(fill="x", pady=(0, 10))
        self._var_endereco = tk.StringVar()
        self._var_bairro   = tk.StringVar()
        CampoEntry(row_end, "Logradouro", self._var_endereco).pack(
            side="left", fill="x", expand=True, padx=(0, 8))
        CampoEntry(row_end, "Bairro", self._var_bairro).pack(
            side="left", fill="x", expand=True, padx=(8, 0))

        self._var_complemento = tk.StringVar()
        CampoEntry(c3, "Complemento", self._var_complemento).pack(fill="x", pady=(0, 10))

        self._mun_widget = MunicipioWidget(c3)
        self._mun_widget.pack(fill="x", pady=(0, 4))

        row_pais = tk.Frame(c3, bg=THEME["bg_card"])
        row_pais.pack(fill="x", pady=(10, 0))
        self._var_cod_pais  = tk.StringVar(value="1058")
        self._var_nome_pais = tk.StringVar(value="Brasil")
        CampoEntry(row_pais, "Código País", self._var_cod_pais).pack(
            side="left", fill="x", expand=True, padx=(0, 8))
        CampoEntry(row_pais, "Nome País", self._var_nome_pais).pack(
            side="left", fill="x", expand=True, padx=(8, 0))

        # ── NUMERAÇÃO DOS DOCUMENTOS FISCAIS ─────────────────────
        SecaoForm(body, "NUMERAÇÃO DOS DOCUMENTOS FISCAIS").pack(fill="x", padx=P, pady=(8, 0))
        c4 = self._card(body, P)

        for label, attr_s, attr_p in [
            ("NF-e",  "serie_nfe",  "prox_nfe"),
            ("NFC-e", "serie_nfce", "prox_nfce"),
            ("NFS-e", "serie_nfse", "prox_nfse"),
            ("CT-e",  "serie_cte",  "prox_cte"),
        ]:
            row_doc = tk.Frame(c4, bg=THEME["bg_card"])
            row_doc.pack(fill="x", pady=(0, 8))
            tk.Label(row_doc, text=f"{label}:", font=FONT["bold"],
                     bg=THEME["bg_card"], fg=THEME["fg"],
                     width=6, anchor="w").pack(side="left", padx=(0, 8))
            var_s = tk.StringVar(value="1")
            var_p = tk.StringVar(value="1")
            setattr(self, f"_var_{attr_s}", var_s)
            setattr(self, f"_var_{attr_p}", var_p)
            CampoEntry(row_doc, "Série", var_s).pack(
                side="left", fill="x", expand=True, padx=(0, 8))
            CampoEntry(row_doc, "Próximo número", var_p).pack(
                side="left", fill="x", expand=True)

        # ── CERTIFICADO DIGITAL ──────────────────────────────────
        SecaoForm(body, "CERTIFICADO DIGITAL (A1 — .pfx)").pack(fill="x", padx=P, pady=(8, 0))
        c5 = self._card(body, P)

        self._var_cert = tk.StringVar()
        cert_row = tk.Frame(c5, bg=THEME["bg_card"])
        cert_row.pack(fill="x", pady=(0, 8))
        tk.Label(cert_row, text="Arquivo .pfx", font=FONT["sm"],
                 bg=THEME["bg_card"], fg=THEME["fg"]).pack(anchor="w", pady=(0, 3))
        tk.Entry(cert_row, textvariable=self._var_cert, font=FONT["md"],
                 state="readonly", relief="flat",
                 bg=THEME["row_alt"], fg=THEME["fg"],
                 highlightthickness=1,
                 highlightbackground=THEME["border"]
                 ).pack(side="left", fill="x", expand=True, ipady=7)
        tk.Button(cert_row, text="📂  Selecionar", font=FONT["sm"],
                  bg=THEME["primary_light"], fg=THEME["primary"],
                  relief="flat", cursor="hand2", padx=10, pady=7,
                  command=self._selecionar_cert).pack(side="left", padx=(8, 0))

        self._var_cert_senha = tk.StringVar()
        CampoEntry(c5, "Senha do Certificado", self._var_cert_senha,
                   show="•").pack(fill="x")

        # ── Erro e botão ─────────────────────────────────────────
        self._var_erro = tk.StringVar()
        tk.Label(body, textvariable=self._var_erro, font=FONT["sm"],
                 bg=THEME["bg"], fg=THEME["danger"]).pack(
                 anchor="w", padx=P, pady=(10, 0))
        botao(body, "💾  Salvar Empresa", tipo="primario",
              command=self._salvar).pack(fill="x", padx=P, pady=(8, 24))

    def _card(self, parent, P):
        frame = tk.Frame(parent, bg=THEME["bg_card"],
                         highlightthickness=1, highlightbackground=THEME["border"])
        frame.pack(fill="x", padx=P, pady=(0, 4))
        inner = tk.Frame(frame, bg=THEME["bg_card"], padx=16, pady=14)
        inner.pack(fill="x")
        return inner

    def _selecionar_cert(self):
        path = filedialog.askopenfilename(
            title="Selecionar Certificado Digital",
            filetypes=[("Certificado A1", "*.pfx"), ("Todos", "*.*")]
        )
        if path:
            self._var_cert.set(path)

    def _preencher(self):
        from models.empresa import Empresa
        e = Empresa.buscar_por_id(self._empresa_id)
        if not e: return
        self._var_nome.set(e.get("nome") or "")
        self._var_razao.set(e.get("razao_social") or "")
        self._var_cnpj.set(e.get("cnpj") or "")
        self._var_ie.set(e.get("ie") or "")
        self._var_im.set(e.get("im") or "")
        self._var_cnae.set(e.get("cnae") or "")
        self._combo_regime.current(int(e.get("regime_tributario") or 1) - 1)
        self._combo_amb.current(0 if int(e.get("ambiente_fiscal") or 2) == 2 else 1)
        self._var_email.set(e.get("email") or "")
        self._var_telefone.set(e.get("telefone") or "")
        self._var_cep.set(e.get("cep") or "")
        self._var_endereco.set(e.get("endereco") or "")
        self._var_numero.set(e.get("numero") or "")
        self._var_complemento.set(e.get("complemento") or "")
        self._var_bairro.set(e.get("bairro") or "")
        self._mun_widget.set_municipio(
            e.get("cod_municipio_ibge") or "",
            e.get("cidade") or "",
            e.get("estado") or "",
        )
        self._var_cod_pais.set(e.get("cod_pais") or "1058")
        self._var_nome_pais.set(e.get("nome_pais") or "Brasil")
        self._var_serie_nfe.set(str(e.get("serie_nfe") or 1))
        self._var_prox_nfe.set(str(e.get("prox_nfe") or 1))
        self._var_serie_nfce.set(str(e.get("serie_nfce") or 1))
        self._var_prox_nfce.set(str(e.get("prox_nfce") or 1))
        self._var_serie_nfse.set(str(e.get("serie_nfse") or 1))
        self._var_prox_nfse.set(str(e.get("prox_nfse") or 1))
        self._var_serie_cte.set(str(e.get("serie_cte") or 1))
        self._var_prox_cte.set(str(e.get("prox_cte") or 1))
        self._var_cert.set(e.get("cert_path") or "")
        self._var_cert_senha.set(e.get("cert_senha") or "")

    def _to_int(self, var, campo):
        try:
            return int(var.get())
        except ValueError:
            self._var_erro.set(f"Valor inválido em '{campo}'.")
            return None

    def _salvar(self):
        nome  = self._var_nome.get().strip()
        razao = self._var_razao.get().strip()
        cnpj  = self._var_cnpj.get().strip()
        if not nome or not razao or not cnpj:
            self._var_erro.set("Nome fantasia, razão social e CNPJ são obrigatórios.")
            return

        for attr, campo in [
            ("_var_serie_nfe",  "Série NF-e"),  ("_var_prox_nfe",  "Próx. NF-e"),
            ("_var_serie_nfce", "Série NFC-e"), ("_var_prox_nfce", "Próx. NFC-e"),
            ("_var_serie_nfse", "Série NFS-e"), ("_var_prox_nfse", "Próx. NFS-e"),
            ("_var_serie_cte",  "Série CT-e"),  ("_var_prox_cte",  "Próx. CT-e"),
        ]:
            if self._to_int(getattr(self, attr), campo) is None:
                return

        regime  = self._combo_regime.current() + 1
        ambient = 2 if self._combo_amb.current() == 0 else 1

        dados = {
            "nome": nome, "razao_social": razao, "cnpj": cnpj,
            "ie":   self._var_ie.get().strip(),
            "im":   self._var_im.get().strip(),
            "cnae": self._var_cnae.get().strip(),
            "regime_tributario": regime, "crt": regime,
            "ambiente_fiscal":   ambient,
            "email":    self._var_email.get().strip(),
            "telefone": self._var_telefone.get().strip(),
            "cep":      self._var_cep.get().strip(),
            "endereco": self._var_endereco.get().strip(),
            "numero":   self._var_numero.get().strip(),
            "complemento": self._var_complemento.get().strip(),
            "bairro":   self._var_bairro.get().strip(),
            "cidade":   self._mun_widget.nome_municipio,
            "cod_municipio_ibge": self._mun_widget.cod_municipio,
            "estado":   self._mun_widget.uf,
            "cod_pais":   self._var_cod_pais.get().strip(),
            "nome_pais":  self._var_nome_pais.get().strip(),
            "serie_nfe":  self._var_serie_nfe.get(),
            "prox_nfe":   self._var_prox_nfe.get(),
            "serie_nfce": self._var_serie_nfce.get(),
            "prox_nfce":  self._var_prox_nfce.get(),
            "serie_nfse": self._var_serie_nfse.get(),
            "prox_nfse":  self._var_prox_nfse.get(),
            "serie_cte":  self._var_serie_cte.get(),
            "prox_cte":   self._var_prox_cte.get(),
            "cert_path":  self._var_cert.get(),
            "cert_senha": self._var_cert_senha.get(),
        }

        if self._empresa_id:
            from models.empresa import Empresa
            Empresa.atualizar(self._empresa_id, dados)
        else:
            from database.seeds.seed import criar_empresa
            criar_empresa(nome, cnpj, razao)

        if self._ao_salvar:
            self._ao_salvar()
        self.destroy()