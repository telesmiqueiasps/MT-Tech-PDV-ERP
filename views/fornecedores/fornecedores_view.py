import tkinter as tk
from tkinter import messagebox, ttk
from config import THEME, FONT
from views.base_view import BaseView
from views.widgets.tabela import Tabela
from views.widgets.widgets import PageHeader, SecaoForm, CampoEntry, botao
from views.widgets.municipio_widget import MunicipioWidget

TIPO_PESSOA = ["J — Pessoa Jurídica", "F — Pessoa Física", "E — Estrangeiro"]
IND_IE      = ["1 — Contribuinte ICMS", "2 — Contribuinte Isento", "9 — Não Contribuinte"]
REGIMES     = ["1 — Simples Nacional", "2 — Simples Nacional Excesso", "3 — Regime Normal"]


class FornecedoresView(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg=THEME["bg"])
        self.pack(fill="both", expand=True)
        try:
            from core.database import DatabaseManager
            DatabaseManager.empresa()
        except Exception:
            tk.Label(self, text="⚠  Selecione uma empresa.",
                     font=FONT["lg"], bg=THEME["bg"], fg=THEME["warning"]).pack(expand=True)
            return
        self._build()

    def _build(self):
        PageHeader(self, "🏭", "Fornecedores",
                   "Cadastro e gerenciamento de fornecedores."
                   ).pack(fill="x", padx=20, pady=(16,0))

        toolbar = tk.Frame(self, bg=THEME["bg_card"], highlightthickness=1,
                           highlightbackground=THEME["border"], padx=14, pady=10)
        toolbar.pack(fill="x", padx=20, pady=(12,0))

        tk.Label(toolbar, text="🔍", font=("Segoe UI",11),
                 bg=THEME["bg_card"], fg=THEME["fg_light"]).pack(side="left")
        self._var_busca = tk.StringVar()
        self._var_busca.trace_add("write", lambda *_: self._carregar())
        tk.Entry(toolbar, textvariable=self._var_busca, font=FONT["md"],
                 relief="flat", bg=THEME["bg"], fg=THEME["fg"],
                 highlightthickness=1, highlightbackground=THEME["border"],
                 highlightcolor=THEME["primary"], width=28
                 ).pack(side="left", padx=(4,0), ipady=5)

        from core.session import Session
        if Session.pode("fornecedores", "criar"):
            botao(toolbar, "+ Novo Fornecedor", tipo="primario",   command=self._novo).pack(side="right")
        if Session.pode("fornecedores", "deletar"):
            botao(toolbar, "🗑  Desativar",      tipo="perigo",     command=self._desativar).pack(side="right", padx=(0,8))
        if Session.pode("fornecedores", "editar"):
            botao(toolbar, "✏  Editar",          tipo="secundario", command=self._editar).pack(side="right", padx=(0,8))

        self._tabela = Tabela(self, colunas=[
            ("ID",48),("Tipo",60),("Nome",220),("CNPJ",140),
            ("IE",110),("Telefone",110),("Contato",130),("Cidade",110),("UF",50),
        ])
        self._tabela.pack(fill="both", expand=True, padx=20, pady=(1,0))
        if Session.pode("fornecedores", "editar"):
            self._tabela.ao_duplo_clique = lambda _: self._editar()

        rodape = tk.Frame(self, bg=THEME["bg_card"], highlightthickness=1,
                          highlightbackground=THEME["border"], padx=14, pady=6)
        rodape.pack(fill="x", padx=20, pady=(0,16))
        self._lbl_total = tk.Label(rodape, text="", font=FONT["sm"],
                                    bg=THEME["bg_card"], fg=THEME["fg_light"])
        self._lbl_total.pack(side="right")
        self._carregar()

    def _carregar(self):
        from models.fornecedor import Fornecedor
        lista = Fornecedor.listar(self._var_busca.get().strip())
        self._tabela.limpar()
        for f in lista:
            doc = f.get("cnpj") or f.get("cpf") or "—"
            self._tabela.inserir([
                f["id"], f.get("tipo_pessoa","J"), f["nome"],
                doc, f.get("ie") or "—", f.get("telefone") or "—",
                f.get("contato") or "—", f.get("cidade") or "—",
                f.get("estado") or "—",
            ])
        self._lbl_total.configure(text=f"{len(lista)} fornecedor(es)")

    def _selecionado_id(self):
        sel = self._tabela.selecionado()
        return int(sel[0]) if sel else None

    def _novo(self):
        from core.session import Session
        if not Session.pode("fornecedores", "criar"):
            messagebox.showwarning("Sem Permissão", "Você não tem permissão para criar fornecedores.", parent=self); return
        FormFornecedor(self, None, self._carregar)

    def _editar(self):
        from core.session import Session
        if not Session.pode("fornecedores", "editar"):
            messagebox.showwarning("Sem Permissão", "Você não tem permissão para editar fornecedores.", parent=self); return
        id_ = self._selecionado_id()
        if not id_: messagebox.showwarning("Atenção","Selecione um fornecedor.",parent=self); return
        FormFornecedor(self, id_, self._carregar)

    def _desativar(self):
        from core.session import Session
        if not Session.pode("fornecedores", "deletar"):
            messagebox.showwarning("Sem Permissão", "Você não tem permissão para desativar fornecedores.", parent=self); return
        id_ = self._selecionado_id()
        if not id_: messagebox.showwarning("Atenção","Selecione um fornecedor.",parent=self); return
        if messagebox.askyesno("Confirmar","Desativar este fornecedor?",parent=self):
            from models.fornecedor import Fornecedor
            Fornecedor.desativar(id_); self._carregar()


class FormFornecedor(BaseView):
    def __init__(self, master, fornecedor_id, ao_salvar=None):
        titulo = "Editar Fornecedor" if fornecedor_id else "Novo Fornecedor"
        super().__init__(master, titulo, 600, 720, modal=True)
        self.resizable(True, True)
        self._fornecedor_id = fornecedor_id
        self._ao_salvar     = ao_salvar
        self._build()
        if fornecedor_id: self._preencher()

    def _build(self):
        canvas = tk.Canvas(self, bg=THEME["bg"], highlightthickness=0)
        scroll = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True)
        body = tk.Frame(canvas, bg=THEME["bg"])
        win  = canvas.create_window((0,0), window=body, anchor="nw")
        body.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(win, width=e.width))
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1*(e.delta/120)),"units"))
        P = 24

        tk.Label(body, text="Novo Fornecedor" if not self._fornecedor_id else "Editar Fornecedor",
                 font=FONT["title"], bg=THEME["bg"], fg=THEME["fg"]
                 ).pack(anchor="w", padx=P, pady=(20,16))

        # ── IDENTIFICAÇÃO ────────────────────────────────────────
        SecaoForm(body, "IDENTIFICAÇÃO").pack(fill="x", padx=P)
        c1 = self._card(body, P)

        self._var_nome = tk.StringVar()
        CampoEntry(c1, "Razão Social / Nome *", self._var_nome).pack(fill="x", pady=(0,10))

        tipo_row = tk.Frame(c1, bg=THEME["bg_card"])
        tipo_row.pack(fill="x", pady=(0,10))
        tk.Label(tipo_row, text="Tipo de Pessoa *", font=FONT["sm"],
                 bg=THEME["bg_card"], fg=THEME["fg"]).pack(anchor="w", pady=(0,3))
        self._var_tipo = tk.StringVar()
        self._combo_tipo = ttk.Combobox(tipo_row, textvariable=self._var_tipo,
                                         values=TIPO_PESSOA, state="readonly", font=FONT["md"])
        self._combo_tipo.current(0)
        self._combo_tipo.pack(fill="x", ipady=4)
        self._combo_tipo.bind("<<ComboboxSelected>>", self._on_tipo_change)

        self._doc_row = tk.Frame(c1, bg=THEME["bg_card"])
        self._doc_row.pack(fill="x", pady=(0,10))
        self._var_cpf  = tk.StringVar()
        self._var_cnpj = tk.StringVar()
        self._var_ie   = tk.StringVar()
        self._campo_cpf  = CampoEntry(self._doc_row, "CPF",  self._var_cpf)
        self._campo_cnpj = CampoEntry(self._doc_row, "CNPJ", self._var_cnpj)
        self._campo_ie   = CampoEntry(self._doc_row, "Inscrição Estadual", self._var_ie)

        row2 = tk.Frame(c1, bg=THEME["bg_card"])
        row2.pack(fill="x", pady=(0,10))
        col_ind = tk.Frame(row2, bg=THEME["bg_card"])
        col_ind.pack(side="left", fill="x", expand=True, padx=(0,8))
        tk.Label(col_ind, text="Indicador IE", font=FONT["sm"],
                 bg=THEME["bg_card"], fg=THEME["fg"]).pack(anchor="w", pady=(0,3))
        self._var_ind_ie = tk.StringVar()
        self._combo_ind  = ttk.Combobox(col_ind, textvariable=self._var_ind_ie,
                                         values=IND_IE, state="readonly", font=FONT["md"])
        self._combo_ind.current(0)
        self._combo_ind.pack(fill="x", ipady=4)
        self._var_im = tk.StringVar()
        CampoEntry(row2, "Inscrição Municipal", self._var_im).pack(
            side="left", fill="x", expand=True, padx=(8,0))

        row3 = tk.Frame(c1, bg=THEME["bg_card"])
        row3.pack(fill="x", pady=(0,10))
        self._var_cnae = tk.StringVar()
        CampoEntry(row3, "CNAE", self._var_cnae).pack(
            side="left", fill="x", expand=True, padx=(0,8))
        col_reg = tk.Frame(row3, bg=THEME["bg_card"])
        col_reg.pack(side="left", fill="x", expand=True, padx=(8,0))
        tk.Label(col_reg, text="Regime Tributário", font=FONT["sm"],
                 bg=THEME["bg_card"], fg=THEME["fg"]).pack(anchor="w", pady=(0,3))
        self._var_regime = tk.StringVar()
        self._combo_reg  = ttk.Combobox(col_reg, textvariable=self._var_regime,
                                         values=REGIMES, state="readonly", font=FONT["md"])
        self._combo_reg.current(0)
        self._combo_reg.pack(fill="x", ipady=4)

        self._var_suframa = tk.StringVar()
        CampoEntry(c1, "SUFRAMA (Zona Franca)", self._var_suframa).pack(fill="x", pady=(0,4))

        # ── CONTATO ──────────────────────────────────────────────
        SecaoForm(body, "CONTATO").pack(fill="x", padx=P, pady=(8,0))
        c2 = self._card(body, P)
        row4 = tk.Frame(c2, bg=THEME["bg_card"])
        row4.pack(fill="x", pady=(0,10))
        self._var_email    = tk.StringVar()
        self._var_telefone = tk.StringVar()
        CampoEntry(row4, "E-mail (NF-e)", self._var_email).pack(
            side="left", fill="x", expand=True, padx=(0,8))
        CampoEntry(row4, "Telefone", self._var_telefone).pack(
            side="left", fill="x", expand=True, padx=(8,0))
        self._var_contato = tk.StringVar()
        CampoEntry(c2, "Nome do Contato", self._var_contato).pack(fill="x", pady=(0,4))

        # ── ENDEREÇO ─────────────────────────────────────────────
        SecaoForm(body, "ENDEREÇO").pack(fill="x", padx=P, pady=(8,0))
        c3 = self._card(body, P)

        row_cep = tk.Frame(c3, bg=THEME["bg_card"])
        row_cep.pack(fill="x", pady=(0,10))
        self._var_cep = tk.StringVar()
        CampoEntry(row_cep, "CEP", self._var_cep).pack(
            side="left", fill="x", expand=True, padx=(0,8))
        col_num = tk.Frame(row_cep, bg=THEME["bg_card"], width=100)
        col_num.pack(side="left"); col_num.pack_propagate(False)
        self._var_numero = tk.StringVar()
        CampoEntry(col_num, "Número", self._var_numero).pack(fill="x")

        row_end = tk.Frame(c3, bg=THEME["bg_card"])
        row_end.pack(fill="x", pady=(0,10))
        self._var_endereco = tk.StringVar()
        self._var_bairro   = tk.StringVar()
        CampoEntry(row_end, "Logradouro", self._var_endereco).pack(
            side="left", fill="x", expand=True, padx=(0,8))
        CampoEntry(row_end, "Bairro", self._var_bairro).pack(
            side="left", fill="x", expand=True, padx=(8,0))

        self._var_complemento = tk.StringVar()
        CampoEntry(c3, "Complemento", self._var_complemento).pack(fill="x", pady=(0,10))

        self._mun_widget = MunicipioWidget(c3)
        self._mun_widget.pack(fill="x", pady=(0,4))

        row_pais = tk.Frame(c3, bg=THEME["bg_card"])
        row_pais.pack(fill="x", pady=(10,0))
        self._var_cod_pais  = tk.StringVar(value="1058")
        self._var_nome_pais = tk.StringVar(value="Brasil")
        CampoEntry(row_pais, "Código País", self._var_cod_pais).pack(
            side="left", fill="x", expand=True, padx=(0,8))
        CampoEntry(row_pais, "Nome País", self._var_nome_pais).pack(
            side="left", fill="x", expand=True, padx=(8,0))

        # ── OBSERVAÇÕES ──────────────────────────────────────────
        SecaoForm(body, "OBSERVAÇÕES").pack(fill="x", padx=P, pady=(8,0))
        c4 = self._card(body, P)
        tk.Label(c4, text="Observações", font=FONT["sm"],
                 bg=THEME["bg_card"], fg=THEME["fg"]).pack(anchor="w", pady=(0,3))
        self._txt_obs = tk.Text(c4, font=FONT["md"], height=4, relief="flat",
                                 bg=THEME["bg_input"], fg=THEME["fg"],
                                 highlightthickness=1, highlightbackground=THEME["border"],
                                 highlightcolor=THEME["primary"], wrap="word")
        self._txt_obs.pack(fill="x")

        self._var_erro = tk.StringVar()
        tk.Label(body, textvariable=self._var_erro, font=FONT["sm"],
                 bg=THEME["bg"], fg=THEME["danger"]).pack(anchor="w", padx=P, pady=(10,0))
        botao(body, "💾  Salvar Fornecedor", tipo="primario",
              command=self._salvar).pack(fill="x", padx=P, pady=(8,24))

        self._on_tipo_change()

    def _card(self, parent, P):
        frame = tk.Frame(parent, bg=THEME["bg_card"], highlightthickness=1,
                         highlightbackground=THEME["border"])
        frame.pack(fill="x", padx=P, pady=(0,4))
        inner = tk.Frame(frame, bg=THEME["bg_card"], padx=16, pady=14)
        inner.pack(fill="x")
        return inner

    def _on_tipo_change(self, _=None):
        for w in [self._campo_cpf, self._campo_cnpj, self._campo_ie]:
            w.pack_forget()
        idx = self._combo_tipo.current()
        if idx == 1:  # PF
            self._campo_cpf.pack(side="left", fill="x", expand=True, padx=(0,8))
        else:
            self._campo_cnpj.pack(side="left", fill="x", expand=True, padx=(0,8))
            self._campo_ie.pack(side="left",   fill="x", expand=True, padx=(8,0))

    def _preencher(self):
        from models.fornecedor import Fornecedor
        f = Fornecedor.buscar_por_id(self._fornecedor_id)
        if not f: return
        self._var_nome.set(f.get("nome",""))
        idx = {"J":0,"F":1,"E":2}.get(f.get("tipo_pessoa","J"),0)
        self._combo_tipo.current(idx); self._on_tipo_change()
        self._var_cpf.set(f.get("cpf") or "")
        self._var_cnpj.set(f.get("cnpj") or "")
        self._var_ie.set(f.get("ie") or "")
        self._combo_ind.current({1:0,2:1,9:2}.get(int(f.get("ind_ie") or 1),0))
        self._var_im.set(f.get("im") or "")
        self._var_cnae.set(f.get("cnae") or "")
        self._combo_reg.current(int(f.get("regime_tributario") or 1)-1)
        self._var_suframa.set(f.get("suframa") or "")
        self._var_email.set(f.get("email") or "")
        self._var_telefone.set(f.get("telefone") or "")
        self._var_contato.set(f.get("contato") or "")
        self._var_cep.set(f.get("cep") or "")
        self._var_endereco.set(f.get("endereco") or "")
        self._var_numero.set(f.get("numero") or "")
        self._var_complemento.set(f.get("complemento") or "")
        self._var_bairro.set(f.get("bairro") or "")
        self._mun_widget.set_municipio(
            f.get("cod_municipio_ibge") or "",
            f.get("cidade") or "",
            f.get("estado") or "",
        )
        self._var_cod_pais.set(f.get("cod_pais") or "1058")
        self._var_nome_pais.set(f.get("nome_pais") or "Brasil")
        if f.get("observacoes"):
            self._txt_obs.insert("1.0", f["observacoes"])

    def _salvar(self):
        nome = self._var_nome.get().strip()
        if not nome:
            self._var_erro.set("O nome é obrigatório."); return
        idx_tipo = self._combo_tipo.current()
        dados = {
            "nome": nome,
            "tipo_pessoa": ["J","F","E"][idx_tipo],
            "cpf":  self._var_cpf.get().strip(),
            "cnpj": self._var_cnpj.get().strip(),
            "ie":   self._var_ie.get().strip(),
            "ind_ie": [1,2,9][self._combo_ind.current()],
            "im":   self._var_im.get().strip(),
            "cnae": self._var_cnae.get().strip(),
            "regime_tributario": self._combo_reg.current()+1,
            "suframa":  self._var_suframa.get().strip(),
            "email":    self._var_email.get().strip(),
            "telefone": self._var_telefone.get().strip(),
            "contato":  self._var_contato.get().strip(),
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
            "observacoes": self._txt_obs.get("1.0","end-1c").strip(),
        }
        from models.fornecedor import Fornecedor
        if self._fornecedor_id: Fornecedor.atualizar(self._fornecedor_id, dados)
        else: Fornecedor.criar(dados)
        if self._ao_salvar: self._ao_salvar()
        self.destroy()