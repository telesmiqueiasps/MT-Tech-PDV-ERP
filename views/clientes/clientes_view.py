import tkinter as tk
from tkinter import messagebox, ttk
from config import THEME, FONT
from views.base_view import BaseView
from views.widgets.tabela import Tabela
from views.widgets.widgets import PageHeader, SecaoForm, CampoEntry, botao
from views.widgets.municipio_widget import MunicipioWidget

TIPO_PESSOA = ["F — Pessoa Física", "J — Pessoa Jurídica", "E — Estrangeiro"]
IND_IE      = ["1 — Contribuinte ICMS", "2 — Contribuinte Isento", "9 — Não Contribuinte"]


class ClientesView(tk.Frame):
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
        PageHeader(self, "👥", "Clientes",
                   "Cadastro e gerenciamento de clientes."
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

        botao(toolbar, "+ Novo Cliente",  tipo="primario",   command=self._novo).pack(side="right")
        botao(toolbar, "🗑  Desativar",   tipo="perigo",     command=self._desativar).pack(side="right", padx=(0,8))
        botao(toolbar, "✏  Editar",       tipo="secundario", command=self._editar).pack(side="right", padx=(0,8))

        self._tabela = Tabela(self, colunas=[
            ("ID",48),("Tipo",60),("Nome",220),("CPF/CNPJ",140),
            ("IE",120),("Telefone",110),("Cidade",120),("UF",50),("Limite R$",100),
        ])
        self._tabela.pack(fill="both", expand=True, padx=20, pady=(1,0))
        self._tabela.ao_duplo_clique = lambda _: self._editar()

        rodape = tk.Frame(self, bg=THEME["bg_card"], highlightthickness=1,
                          highlightbackground=THEME["border"], padx=14, pady=6)
        rodape.pack(fill="x", padx=20, pady=(0,16))
        self._lbl_total = tk.Label(rodape, text="", font=FONT["sm"],
                                    bg=THEME["bg_card"], fg=THEME["fg_light"])
        self._lbl_total.pack(side="right")
        self._carregar()

    def _carregar(self):
        from models.cliente import Cliente
        lista = Cliente.listar(self._var_busca.get().strip())
        self._tabela.limpar()
        for c in lista:
            doc = c.get("cpf") or c.get("cnpj") or "—"
            self._tabela.inserir([
                c["id"], c.get("tipo_pessoa","F"), c["nome"],
                doc, c.get("ie") or "—", c.get("telefone") or "—",
                c.get("cidade") or "—", c.get("estado") or "—",
                f"R$ {c.get('limite_credito',0):,.2f}",
            ])
        self._lbl_total.configure(text=f"{len(lista)} cliente(s)")

    def _selecionado_id(self):
        sel = self._tabela.selecionado()
        return int(sel[0]) if sel else None

    def _novo(self):      FormCliente(self, None, self._carregar)
    def _editar(self):
        id_ = self._selecionado_id()
        if not id_: messagebox.showwarning("Atenção","Selecione um cliente.",parent=self); return
        FormCliente(self, id_, self._carregar)
    def _desativar(self):
        id_ = self._selecionado_id()
        if not id_: messagebox.showwarning("Atenção","Selecione um cliente.",parent=self); return
        if messagebox.askyesno("Confirmar","Desativar este cliente?",parent=self):
            from models.cliente import Cliente
            Cliente.desativar(id_); self._carregar()


class FormCliente(BaseView):
    def __init__(self, master, cliente_id, ao_salvar=None):
        titulo = "Editar Cliente" if cliente_id else "Novo Cliente"
        super().__init__(master, titulo, 600, 720, modal=True)
        self.resizable(True, True)
        self._cliente_id = cliente_id
        self._ao_salvar  = ao_salvar
        self._build()
        if cliente_id: self._preencher()

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

        tk.Label(body, text="Novo Cliente" if not self._cliente_id else "Editar Cliente",
                 font=FONT["title"], bg=THEME["bg"], fg=THEME["fg"]
                 ).pack(anchor="w", padx=P, pady=(20,16))

        # ── IDENTIFICAÇÃO ────────────────────────────────────────
        SecaoForm(body, "IDENTIFICAÇÃO").pack(fill="x", padx=P)
        c1 = self._card(body, P)

        self._var_nome = tk.StringVar()
        CampoEntry(c1, "Nome / Razão Social *", self._var_nome).pack(fill="x", pady=(0,10))

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

        # Documentos (CPF+RG ou CNPJ+IE, dinâmico)
        self._doc_row = tk.Frame(c1, bg=THEME["bg_card"])
        self._doc_row.pack(fill="x", pady=(0,10))
        self._var_cpf  = tk.StringVar()
        self._var_cnpj = tk.StringVar()
        self._var_rg   = tk.StringVar()
        self._var_ie   = tk.StringVar()
        self._campo_cpf  = CampoEntry(self._doc_row, "CPF",  self._var_cpf)
        self._campo_cnpj = CampoEntry(self._doc_row, "CNPJ", self._var_cnpj)
        self._campo_rg   = CampoEntry(self._doc_row, "RG",   self._var_rg)
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
        self._combo_ind.current(2)
        self._combo_ind.pack(fill="x", ipady=4)
        self._var_im = tk.StringVar()
        CampoEntry(row2, "Inscrição Municipal", self._var_im).pack(
            side="left", fill="x", expand=True, padx=(8,0))

        self._var_suframa = tk.StringVar()
        CampoEntry(c1, "SUFRAMA (Zona Franca)", self._var_suframa).pack(fill="x", pady=(0,4))

        # ── CONTATO ──────────────────────────────────────────────
        SecaoForm(body, "CONTATO").pack(fill="x", padx=P, pady=(8,0))
        c2 = self._card(body, P)
        row3 = tk.Frame(c2, bg=THEME["bg_card"])
        row3.pack(fill="x", pady=(0,4))
        self._var_email    = tk.StringVar()
        self._var_telefone = tk.StringVar()
        CampoEntry(row3, "E-mail (NF-e)", self._var_email).pack(
            side="left", fill="x", expand=True, padx=(0,8))
        CampoEntry(row3, "Telefone", self._var_telefone).pack(
            side="left", fill="x", expand=True, padx=(8,0))

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

        # ── FINANCEIRO ───────────────────────────────────────────
        SecaoForm(body, "FINANCEIRO").pack(fill="x", padx=P, pady=(8,0))
        c4 = self._card(body, P)
        self._var_limite = tk.StringVar(value="0.00")
        CampoEntry(c4, "Limite de Crédito (R$)", self._var_limite,
                   justify="right").pack(anchor="w", ipadx=60)

        self._var_erro = tk.StringVar()
        tk.Label(body, textvariable=self._var_erro, font=FONT["sm"],
                 bg=THEME["bg"], fg=THEME["danger"]).pack(anchor="w", padx=P, pady=(10,0))
        botao(body, "💾  Salvar Cliente", tipo="primario",
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
        for w in [self._campo_cpf, self._campo_cnpj,
                  self._campo_rg, self._campo_ie]:
            w.pack_forget()
        idx = self._combo_tipo.current()
        if idx == 0:  # PF
            self._campo_cpf.pack(side="left", fill="x", expand=True, padx=(0,8))
            self._campo_rg.pack(side="left",  fill="x", expand=True, padx=(8,0))
        else:          # PJ / E
            self._campo_cnpj.pack(side="left", fill="x", expand=True, padx=(0,8))
            self._campo_ie.pack(side="left",   fill="x", expand=True, padx=(8,0))

    def _preencher(self):
        from models.cliente import Cliente
        c = Cliente.buscar_por_id(self._cliente_id)
        if not c: return
        self._var_nome.set(c.get("nome",""))
        idx = {"F":0,"J":1,"E":2}.get(c.get("tipo_pessoa","F"),0)
        self._combo_tipo.current(idx); self._on_tipo_change()
        self._var_cpf.set(c.get("cpf") or "")
        self._var_cnpj.set(c.get("cnpj") or "")
        self._var_rg.set(c.get("rg") or "")
        self._var_ie.set(c.get("ie") or "")
        self._combo_ind.current({1:0,2:1,9:2}.get(int(c.get("ind_ie") or 9),2))
        self._var_im.set(c.get("im") or "")
        self._var_suframa.set(c.get("suframa") or "")
        self._var_email.set(c.get("email") or "")
        self._var_telefone.set(c.get("telefone") or "")
        self._var_cep.set(c.get("cep") or "")
        self._var_endereco.set(c.get("endereco") or "")
        self._var_numero.set(c.get("numero") or "")
        self._var_complemento.set(c.get("complemento") or "")
        self._var_bairro.set(c.get("bairro") or "")
        self._mun_widget.set_municipio(
            c.get("cod_municipio_ibge") or "",
            c.get("cidade") or "",
            c.get("estado") or "",
        )
        self._var_cod_pais.set(c.get("cod_pais") or "1058")
        self._var_nome_pais.set(c.get("nome_pais") or "Brasil")
        self._var_limite.set(f"{c.get('limite_credito',0):.2f}")

    def _salvar(self):
        nome = self._var_nome.get().strip()
        if not nome:
            self._var_erro.set("O nome é obrigatório."); return
        try:
            limite = float(self._var_limite.get().replace(",","."))
        except ValueError:
            self._var_erro.set("Limite de crédito inválido."); return

        idx_tipo = self._combo_tipo.current()
        dados = {
            "nome": nome,
            "tipo_pessoa": ["F","J","E"][idx_tipo],
            "cpf":  self._var_cpf.get().strip(),
            "cnpj": self._var_cnpj.get().strip(),
            "rg":   self._var_rg.get().strip(),
            "ie":   self._var_ie.get().strip(),
            "ind_ie": [1,2,9][self._combo_ind.current()],
            "im":   self._var_im.get().strip(),
            "suframa": self._var_suframa.get().strip(),
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
            "limite_credito": limite,
        }
        from models.cliente import Cliente
        if self._cliente_id: Cliente.atualizar(self._cliente_id, dados)
        else: Cliente.criar(dados)
        if self._ao_salvar: self._ao_salvar()
        self.destroy()