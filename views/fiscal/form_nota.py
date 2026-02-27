"""
FormNota — formulário de entrada/saída manual de NF-e.
Melhorias:
  - DateEntry com máscara DD/MM/AAAA e calendário
  - SearchEntry para fornecedor/cliente e produto (busca por nome ou código)
  - CFOPs e CSTs carregados do banco (fiscal_config)
  - Campos fiscais completos no FormItem (CST ICMS/PIS/COFINS, BC, alíquotas)
  - Scroll com mouse sem conflito entre painéis
  - Responsividade: painel esquerdo scrollável, direito expansível
  - Bloqueio de período fiscal fechado
"""
import tkinter as tk
from tkinter import ttk, messagebox
import datetime
from config import THEME, FONT
from views.base_view import BaseView
from views.widgets.widgets import SecaoForm, CampoEntry, botao
from views.widgets.tabela import Tabela
from views.widgets.date_entry import DateEntry
from views.widgets.search_entry import SearchEntry
from models.nota_fiscal import STATUS_LABELS, TIPO_LABELS, NotaFiscal
from models.fiscal_config import FiscalConfig
from core.session import Session


def _f2s(v):
    try:
        return f"{float(v or 0):.2f}"
    except (ValueError, TypeError):
        return "0.00"


def _s2f(s):
    try:
        return float(str(s).replace(",", ".") or 0)
    except (ValueError, TypeError):
        return 0.0


class FormNota(BaseView):
    def __init__(self, master, tipo, nota_id=None, ao_salvar=None):
        titulo = f"{'Editar' if nota_id else 'Nova'} Nota — {TIPO_LABELS.get(tipo, tipo)}"
        super().__init__(master, titulo, 1100, 760, modal=True)
        self.resizable(True, True)
        self._tipo       = tipo
        self._nota_id    = nota_id
        self._ao_salvar  = ao_salvar
        self._itens      = []
        self._readonly   = False
        self._terc_tipo  = "FORNECEDOR" if tipo in ("ENTRADA", "DEV_COMPRA") else "CLIENTE"
        self._uf_empresa = Session.empresa().get("estado", "")

        # Dados carregados
        self._depositos   = []
        self._terceiros   = []    # fornecedores ou clientes
        self._produtos    = []
        self._cfops       = []
        self._cst_icms    = []
        self._cst_pisc    = []

        self._build()
        self._carregar_dados()
        if nota_id:
            self._preencher()
        else:
            hoje = datetime.date.today().isoformat()
            self._de_emissao.set(hoje)
            self._de_entrada.set(hoje)

    # ────────────────────────────────────────────────────────────
    # Layout principal
    # ────────────────────────────────────────────────────────────
    def _build(self):
        # Rodapé primeiro (fixo na parte de baixo)
        self._build_rodape()

        main = tk.Frame(self, bg=THEME["bg"])
        main.pack(fill="both", expand=True, padx=16, pady=(8, 0))

        # Painel esquerdo fixo
        left_wrap = tk.Frame(main, bg=THEME["bg"], width=380)
        left_wrap.pack(side="left", fill="y", padx=(0, 10))
        left_wrap.pack_propagate(False)
        self._build_esquerda(left_wrap)

        # Painel direito expansível
        right = tk.Frame(main, bg=THEME["bg"])
        right.pack(side="left", fill="both", expand=True)
        self._build_itens(right)

    # ── Painel esquerdo (scrollável) ─────────────────────────────
    def _build_esquerda(self, parent):
        canvas = tk.Canvas(parent, bg=THEME["bg"], highlightthickness=0)
        vsb = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True)

        body = tk.Frame(canvas, bg=THEME["bg"])
        win  = canvas.create_window((0, 0), window=body, anchor="nw")
        body.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
            lambda e: canvas.itemconfig(win, width=e.width))

        # Scroll só quando o mouse está sobre este canvas
        def _scroll(e):
            canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")

        canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", _scroll))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

        # Título e status
        tk.Label(body, text=TIPO_LABELS.get(self._tipo, self._tipo),
                 font=FONT["title"], bg=THEME["bg"], fg=THEME["primary"]
                 ).pack(anchor="w", pady=(4, 0))
        self._lbl_status = tk.Label(body, text="✏️ Rascunho",
                                     font=FONT["bold"], bg=THEME["bg"], fg="#6C757D")
        self._lbl_status.pack(anchor="w", pady=(0, 6))

        self._build_cabecalho(body)
        self._build_terceiro(body)
        self._build_deposito(body)
        self._build_totais(body)
        self._build_obs(body)

    # ── Cabeçalho ────────────────────────────────────────────────
    def _build_cabecalho(self, body):
        SecaoForm(body, "CABEÇALHO").pack(fill="x")
        c = self._card(body)

        # Número + Série
        row1 = tk.Frame(c, bg=THEME["bg_card"])
        row1.pack(fill="x", pady=(0, 8))
        self._var_numero = tk.StringVar()
        self._var_serie  = tk.StringVar(value="1")
        CampoEntry(row1, "Número NF", self._var_numero).pack(
            side="left", fill="x", expand=True, padx=(0, 6))
        col_s = tk.Frame(row1, bg=THEME["bg_card"], width=70)
        col_s.pack(side="left"); col_s.pack_propagate(False)
        CampoEntry(col_s, "Série", self._var_serie).pack(fill="x")

        # Datas com DateEntry
        row2 = tk.Frame(c, bg=THEME["bg_card"])
        row2.pack(fill="x", pady=(0, 8))
        col_e = tk.Frame(row2, bg=THEME["bg_card"])
        col_e.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self._de_emissao = DateEntry(col_e, label="Dt. Emissão")
        self._de_emissao.pack(fill="x")

        col_en = tk.Frame(row2, bg=THEME["bg_card"])
        col_en.pack(side="left", fill="x", expand=True)
        self._de_entrada = DateEntry(col_en, label="Dt. Entrada/Saída")
        self._de_entrada.pack(fill="x")

        # Chave e modelo
        self._var_chave  = tk.StringVar()
        self._var_modelo = tk.StringVar(value="55")
        CampoEntry(c, "Chave de Acesso (44 dígitos)",
                   self._var_chave).pack(fill="x", pady=(0, 8))

        mod_frame = tk.Frame(c, bg=THEME["bg_card"])
        mod_frame.pack(fill="x")
        tk.Label(mod_frame, text="Modelo", font=FONT["sm"],
                 bg=THEME["bg_card"], fg=THEME["fg"]).pack(anchor="w", pady=(0, 3))
        self._combo_modelo = ttk.Combobox(
            mod_frame, textvariable=self._var_modelo,
            values=["55 — NF-e", "65 — NFC-e"],
            state="readonly", font=FONT["md"])
        self._combo_modelo.current(0)
        self._combo_modelo.pack(fill="x", ipady=4)

    # ── Terceiro (fornecedor / cliente) ──────────────────────────
    def _build_terceiro(self, body):
        label_sec = "FORNECEDOR" if self._terc_tipo == "FORNECEDOR" else "CLIENTE"
        SecaoForm(body, label_sec).pack(fill="x", pady=(8, 0))
        c = self._card(body)

        # SearchEntry
        tk.Label(c, text=f"Buscar {label_sec.title()} (nome ou CNPJ/CPF)",
                 font=FONT["sm"], bg=THEME["bg_card"], fg=THEME["fg"]
                 ).pack(anchor="w", pady=(0, 3))
        self._se_terc = SearchEntry(
            c,
            placeholder=f"Digite o nome ou documento...",
            key_display=lambda d: f"{d['nome']}  —  {d.get('cnpj') or d.get('cpf') or d.get('cpf_cnpj','')}"[:60],
            key_search=lambda d: f"{d.get('nome','')} {d.get('cnpj','') or d.get('cpf','') or d.get('cpf_cnpj','')}",
            ao_selecionar=self._on_terc_select,
        )
        self._se_terc.pack(fill="x", pady=(0, 8))

        # Campos manuais (preenchidos automaticamente ou editáveis)
        self._var_terc_id   = tk.IntVar(value=0)
        self._var_terc_nome = tk.StringVar()
        self._var_terc_doc  = tk.StringVar()
        self._var_terc_uf   = tk.StringVar()

        CampoEntry(c, "Nome / Razão Social", self._var_terc_nome).pack(fill="x", pady=(0, 6))
        row_doc = tk.Frame(c, bg=THEME["bg_card"])
        row_doc.pack(fill="x")
        CampoEntry(row_doc, "CNPJ / CPF", self._var_terc_doc).pack(
            side="left", fill="x", expand=True, padx=(0, 6))
        col_uf = tk.Frame(row_doc, bg=THEME["bg_card"], width=65)
        col_uf.pack(side="left"); col_uf.pack_propagate(False)
        CampoEntry(col_uf, "UF", self._var_terc_uf).pack(fill="x")

    # ── Depósito ─────────────────────────────────────────────────
    def _build_deposito(self, body):
        SecaoForm(body, "DEPÓSITO").pack(fill="x", pady=(8, 0))
        c = self._card(body)
        tk.Label(c, text="Depósito *", font=FONT["sm"],
                 bg=THEME["bg_card"], fg=THEME["fg"]).pack(anchor="w", pady=(0, 3))
        self._var_dep = tk.StringVar()
        self._combo_dep = ttk.Combobox(c, textvariable=self._var_dep,
                                        state="readonly", font=FONT["md"])
        self._combo_dep.pack(fill="x", ipady=4)

    # ── Totais ────────────────────────────────────────────────────
    def _build_totais(self, body):
        SecaoForm(body, "TOTAIS DA NOTA").pack(fill="x", pady=(8, 0))
        c = self._card(body)
        self._vars_totais = {}
        linhas = [
            ("total_produtos", "Produtos R$",   False, False),
            ("total_frete",    "Frete R$",      True,  False),
            ("total_seguro",   "Seguro R$",     True,  False),
            ("total_desconto", "Desconto R$",   True,  False),
            ("total_outros",   "Outras Desp R$",True,  False),
            ("total_ipi",      "IPI R$",        False, False),
            ("total_icms",     "ICMS R$",       False, False),
            ("total_icms_st",  "ICMS-ST R$",    False, False),
            ("total_pis",      "PIS R$",        False, False),
            ("total_cofins",   "COFINS R$",     False, False),
            ("total_nf",       "TOTAL NF R$",   False, True),
        ]
        for campo, label, editavel, bold in linhas:
            var = tk.StringVar(value="0,00")
            self._vars_totais[campo] = var
            row = tk.Frame(c, bg=THEME["bg_card"])
            row.pack(fill="x", pady=2)
            tk.Label(row, text=label,
                     font=FONT["bold"] if bold else FONT["sm"],
                     bg=THEME["bg_card"],
                     fg=THEME["fg"] if bold else THEME["fg_light"]
                     ).pack(side="left")
            if editavel:
                e = tk.Entry(row, textvariable=var, font=FONT["sm"],
                             relief="flat", bg=THEME["bg"], fg=THEME["fg"],
                             justify="right", width=10,
                             highlightthickness=1,
                             highlightbackground=THEME["border"],
                             highlightcolor=THEME["primary"])
                e.pack(side="right", ipady=3)
                var.trace_add("write", self._recalcular_total_nf)
            else:
                tk.Label(row, textvariable=var,
                         font=FONT["bold"] if bold else FONT["sm"],
                         bg=THEME["bg_card"],
                         fg=THEME["primary"] if bold else THEME["fg"]
                         ).pack(side="right")

    # ── Observações ───────────────────────────────────────────────
    def _build_obs(self, body):
        SecaoForm(body, "OBSERVAÇÕES / INF. COMPLEMENTARES").pack(fill="x", pady=(8, 0))
        c = self._card(body)
        self._txt_obs = tk.Text(c, font=FONT["md"], height=3,
                                 relief="flat", bg="white", fg=THEME["fg"],
                                 highlightthickness=1,
                                 highlightbackground=THEME["border"], wrap="word")
        self._txt_obs.pack(fill="x")

    # ── Painel de itens (direita) ─────────────────────────────────
    def _build_itens(self, parent):
        hdr = tk.Frame(parent, bg=THEME["bg_card"], highlightthickness=1,
                       highlightbackground=THEME["border"], padx=12, pady=8)
        hdr.pack(fill="x")
        tk.Label(hdr, text="Itens da Nota", font=FONT["bold"],
                 bg=THEME["bg_card"], fg=THEME["fg"]).pack(side="left")

        self._btn_add_item = botao(hdr, "+ Adicionar Item", tipo="primario",
                                    command=self._add_item)
        self._btn_add_item.pack(side="right")
        self._btn_rem_item = botao(hdr, "✕ Remover", tipo="perigo",
                                    command=self._rem_item)
        self._btn_rem_item.pack(side="right", padx=(0, 6))

        self._tab = Tabela(parent, colunas=[
            ("#",         28),
            ("Produto",   180),
            ("Código",    65),
            ("Unid.",     42),
            ("Qtd.",      60),
            ("V.Unit.",   82),
            ("Desc.",     65),
            ("IPI",       55),
            ("ICMS",      60),
            ("Total",     85),
            ("CFOP",      52),
            ("CST",       42),
        ])
        self._tab.pack(fill="both", expand=True, pady=(4, 0))
        self._tab.ao_duplo_clique = lambda _: self._editar_item()

        # Scroll do mouse exclusivo para a tabela
        def _scroll_tab(e):
            try:
                self._tab._canvas.yview_scroll(int(-1*(e.delta/120)), "units")
            except Exception:
                pass
        self._tab.bind("<Enter>",
            lambda e: self._tab.bind_all("<MouseWheel>", _scroll_tab))
        self._tab.bind("<Leave>",
            lambda e: self._tab.unbind_all("<MouseWheel>"))

    # ── Rodapé ────────────────────────────────────────────────────
    def _build_rodape(self):
        rod = tk.Frame(self, bg=THEME["bg_card"], highlightthickness=1,
                       highlightbackground=THEME["border"], padx=16, pady=10)
        rod.pack(fill="x", side="bottom")

        self._var_erro = tk.StringVar()
        tk.Label(rod, textvariable=self._var_erro, font=FONT["sm"],
                 bg=THEME["bg_card"], fg=THEME["danger"]).pack(side="left")

        self._btn_lancar = botao(rod, "✅ Autorizar Lançamento",
                                  tipo="sucesso", command=self._lancar)
        self._btn_lancar.pack(side="right")

        botao(rod, "💾 Salvar Rascunho", tipo="primario",
              command=self._salvar).pack(side="right", padx=(0, 8))

        self._btn_excluir = botao(rod, "🗑 Excluir", tipo="perigo",
                                   command=self._excluir)
        self._btn_excluir.pack(side="left", padx=(8, 0))
        if not self._nota_id:
            self._btn_excluir.configure(state="disabled")

    # ────────────────────────────────────────────────────────────
    # Carregamento de dados
    # ────────────────────────────────────────────────────────────
    def _carregar_dados(self):
        from models.estoque import Deposito
        self._depositos = Deposito.listar()
        self._combo_dep["values"] = [d["nome"] for d in self._depositos]
        if self._depositos:
            self._combo_dep.current(0)

        # Terceiros
        db = __import__("core.database", fromlist=["DatabaseManager"]).DatabaseManager.empresa()
        if self._terc_tipo == "FORNECEDOR":
            self._terceiros = db.fetchall("SELECT * FROM fornecedores WHERE ativo=1 ORDER BY nome", ())
        else:
            self._terceiros = db.fetchall("SELECT * FROM clientes WHERE ativo=1 ORDER BY nome", ())
        self._se_terc.set_items(self._terceiros)

        # Produtos
        db2 = __import__("core.database", fromlist=["DatabaseManager"]).DatabaseManager.empresa()
        self._produtos = db2.fetchall("SELECT * FROM produtos WHERE ativo=1 ORDER BY nome", ())

        # CFOP do banco
        self._cfops   = FiscalConfig.listar_cfop(tipo_op=self._tipo)
        if not self._cfops:  # fallback se banco vazio
            self._cfops = FiscalConfig.listar_cfop()
        self._cst_icms = FiscalConfig.listar_cst_icms()
        self._cst_pisc = FiscalConfig.listar_cst_pis_cofins()

    def _on_terc_select(self, d: dict):
        self._var_terc_id.set(d.get("id") or 0)
        self._var_terc_nome.set(d.get("nome") or "")
        doc = d.get("cnpj") or d.get("cpf") or d.get("cpf_cnpj") or ""
        self._var_terc_doc.set(doc)
        uf = d.get("estado") or d.get("uf") or ""
        self._var_terc_uf.set(uf)

    # ────────────────────────────────────────────────────────────
    # Cálculos
    # ────────────────────────────────────────────────────────────
    def _recalcular_totais(self):
        tot_prod = sum(_s2f(i.get("valor_total")) for i in self._itens)
        tot_ipi  = sum(_s2f(i.get("valor_ipi"))   for i in self._itens)
        tot_icms = sum(_s2f(i.get("valor_icms"))  for i in self._itens)
        tot_icst = sum(_s2f(i.get("valor_icms_st",0)) for i in self._itens)
        tot_pis  = sum(_s2f(i.get("valor_pis",0)) for i in self._itens)
        tot_cof  = sum(_s2f(i.get("valor_cofins",0)) for i in self._itens)
        self._vars_totais["total_produtos"].set(f"{tot_prod:,.2f}")
        self._vars_totais["total_ipi"].set(f"{tot_ipi:,.2f}")
        self._vars_totais["total_icms"].set(f"{tot_icms:,.2f}")
        self._vars_totais["total_icms_st"].set(f"{tot_icst:,.2f}")
        self._vars_totais["total_pis"].set(f"{tot_pis:,.2f}")
        self._vars_totais["total_cofins"].set(f"{tot_cof:,.2f}")
        self._recalcular_total_nf()

    def _recalcular_total_nf(self, *_):
        try:
            def _v(k): return _s2f(self._vars_totais[k].get().replace(",",""))
            total = (_v("total_produtos") + _v("total_frete") +
                     _v("total_seguro") + _v("total_outros") +
                     _v("total_ipi") - _v("total_desconto"))
            self._vars_totais["total_nf"].set(f"{total:,.2f}")
        except Exception:
            pass

    def _atualizar_tab_itens(self):
        self._tab.limpar()
        for i, item in enumerate(self._itens, 1):
            self._tab.inserir([
                i,
                item.get("descricao") or "",
                item.get("codigo") or "—",
                item.get("unidade") or "—",
                f"{_s2f(item.get('quantidade')):g}",
                f"{_s2f(item.get('valor_unitario')):,.4f}",
                f"{_s2f(item.get('desconto',0)):,.2f}" if _s2f(item.get("desconto")) else "—",
                f"{_s2f(item.get('valor_ipi',0)):,.2f}" if _s2f(item.get("valor_ipi")) else "—",
                f"{_s2f(item.get('valor_icms',0)):,.2f}" if _s2f(item.get("valor_icms")) else "—",
                f"R$ {_s2f(item.get('valor_total')):,.2f}",
                item.get("cfop") or "—",
                item.get("cst_icms") or "—",
            ])

    # ────────────────────────────────────────────────────────────
    # Itens
    # ────────────────────────────────────────────────────────────
    def _add_item(self):
        # Situação intra/inter para sugerir CFOP/CST
        uf_terc = self._var_terc_uf.get().strip().upper()
        situacao = "A" if (not uf_terc or uf_terc == self._uf_empresa.upper()) else "B"
        regra = FiscalConfig.regra_para(self._tipo, situacao)

        FormItem(self, self._produtos, self._tipo,
                 cfops=self._cfops,
                 cst_icms=self._cst_icms,
                 cst_pisc=self._cst_pisc,
                 regra_padrao=regra,
                 ao_confirmar=self._on_item_add)

    def _on_item_add(self, item: dict):
        self._itens.append(item)
        self._atualizar_tab_itens()
        self._recalcular_totais()

    def _rem_item(self):
        idx = self._tab.selecionado_indice()
        if idx is None:
            messagebox.showwarning("Atenção", "Selecione um item.", parent=self); return
        if not messagebox.askyesno("Confirmar", "Remover este item?", parent=self): return
        item = self._itens.pop(idx)
        if item.get("_id"):
            NotaFiscal.remover_item(item["_id"])
        self._atualizar_tab_itens()
        self._recalcular_totais()

    def _editar_item(self):
        idx = self._tab.selecionado_indice()
        if idx is None: return
        uf_terc  = self._var_terc_uf.get().strip().upper()
        situacao = "A" if (not uf_terc or uf_terc == self._uf_empresa.upper()) else "B"
        regra    = FiscalConfig.regra_para(self._tipo, situacao)
        FormItem(self, self._produtos, self._tipo,
                 item=self._itens[idx],
                 cfops=self._cfops,
                 cst_icms=self._cst_icms,
                 cst_pisc=self._cst_pisc,
                 regra_padrao=regra,
                 ao_confirmar=lambda it, i=idx: self._on_item_edit(i, it))

    def _on_item_edit(self, idx: int, item: dict):
        self._itens[idx] = item
        self._atualizar_tab_itens()
        self._recalcular_totais()

    # ────────────────────────────────────────────────────────────
    # Preencher nota existente
    # ────────────────────────────────────────────────────────────
    def _preencher(self):
        nota  = NotaFiscal.buscar_por_id(self._nota_id)
        itens = NotaFiscal.itens(self._nota_id)
        if not nota: return

        self._var_numero.set(str(nota.get("numero") or ""))
        self._var_serie.set(str(nota.get("serie") or 1))
        self._de_emissao.set(nota.get("data_emissao") or "")
        self._de_entrada.set(nota.get("data_entrada") or "")
        self._var_chave.set(nota.get("chave_acesso") or "")

        # Terceiro
        self._var_terc_nome.set(nota.get("terceiro_nome") or "")
        self._var_terc_doc.set(nota.get("terceiro_doc") or "")
        # Tenta re-selecionar no SearchEntry
        tid = nota.get("terceiro_id")
        if tid:
            for t in self._terceiros:
                if t["id"] == tid:
                    self._se_terc.set_item(t)
                    self._var_terc_uf.set(t.get("estado") or t.get("uf") or "")
                    break

        # Depósito
        dep_id = nota.get("deposito_id")
        for i, d in enumerate(self._depositos):
            if d["id"] == dep_id:
                self._combo_dep.current(i); break

        # Totais
        for campo in self._vars_totais:
            v = nota.get(campo) or 0
            self._vars_totais[campo].set(f"{float(v):,.2f}")

        # Obs
        self._txt_obs.delete("1.0", "end")
        self._txt_obs.insert("1.0", nota.get("observacoes") or "")

        # Itens
        for item in itens:
            item["_id"] = item.get("id")
            self._itens.append(dict(item))
        self._atualizar_tab_itens()

        # Status
        sl, cor = STATUS_LABELS.get(nota.get("status", ""), ("?", "gray"))
        self._lbl_status.configure(text=sl, fg=cor)

        # Readonly se não for rascunho
        if nota.get("status") != "RASCUNHO":
            self._set_readonly()

        self._btn_excluir.configure(state="normal")

    # ────────────────────────────────────────────────────────────
    # Readonly
    # ────────────────────────────────────────────────────────────
    def _set_readonly(self):
        self._readonly = True
        for w in [self._btn_add_item, self._btn_rem_item,
                  self._btn_lancar, self._btn_excluir]:
            try: w.configure(state="disabled")
            except Exception: pass

    # ────────────────────────────────────────────────────────────
    # Coletar dados
    # ────────────────────────────────────────────────────────────
    def _coletar(self) -> dict | None:
        terc_item = self._se_terc.get_item()
        terc_id   = terc_item["id"] if terc_item else None
        terc_nome = self._var_terc_nome.get().strip() or (terc_item or {}).get("nome", "")
        terc_doc  = self._var_terc_doc.get().strip()

        dep_idx = self._combo_dep.current()
        dep_id  = self._depositos[dep_idx]["id"] if dep_idx >= 0 else None

        def _tv(k): return _s2f(self._vars_totais[k].get().replace(",",""))

        return {
            "tipo":          self._tipo,
            "modelo":        "55",
            "status":        "RASCUNHO",
            "numero":        int(self._var_numero.get() or 0) or None,
            "serie":         int(self._var_serie.get() or 1),
            "chave_acesso":  self._var_chave.get().strip() or None,
            "data_emissao":  self._de_emissao.get(),
            "data_entrada":  self._de_entrada.get(),
            "terceiro_id":   terc_id,
            "terceiro_tipo": self._terc_tipo,
            "terceiro_nome": terc_nome,
            "terceiro_doc":  terc_doc,
            "deposito_id":   dep_id,
            "total_produtos":_tv("total_produtos"),
            "total_frete":   _tv("total_frete"),
            "total_seguro":  _tv("total_seguro"),
            "total_desconto":_tv("total_desconto"),
            "total_outros":  _tv("total_outros"),
            "total_ipi":     _tv("total_ipi"),
            "total_icms":    _tv("total_icms"),
            "total_icms_st": _tv("total_icms_st"),
            "total_pis":     _tv("total_pis"),
            "total_cofins":  _tv("total_cofins"),
            "total_nf":      _tv("total_nf"),
            "observacoes":   self._txt_obs.get("1.0", "end-1c").strip() or None,
            "usuario_id":    Session.usuario_id(),
            "usuario_nome":  Session.nome(),
        }

    # ────────────────────────────────────────────────────────────
    # Salvar / Lançar / Excluir
    # ────────────────────────────────────────────────────────────
    def _salvar(self) -> int | None:
        self._var_erro.set("")
        dados = self._coletar()
        if not dados: return None

        # Verificar período fiscal
        from services.fiscal_guard import FiscalGuard, FiscalBloqueado
        try:
            FiscalGuard.verificar(dados.get("data_emissao") or dados.get("data_entrada"),
                                   "salvar esta nota")
        except FiscalBloqueado as e:
            messagebox.showerror("Período Fechado", str(e), parent=self)
            return None

        try:
            if self._nota_id:
                NotaFiscal.atualizar(self._nota_id, dados)
                nota_id = self._nota_id
                NotaFiscal.remover_todos_itens(nota_id)
            else:
                nota_id = NotaFiscal.criar(dados)
                self._nota_id = nota_id
                self._btn_excluir.configure(state="normal")

            for item in self._itens:
                item_save = {k: v for k, v in item.items()
                             if not k.startswith("_")}
                NotaFiscal.salvar_item(nota_id, item_save)

            if self._ao_salvar:
                self._ao_salvar()
            return nota_id
        except Exception as e:
            self._var_erro.set(str(e))
            messagebox.showerror("Erro ao salvar", str(e), parent=self)
            return None

    def _excluir(self):
        if not self._nota_id: return
        if not messagebox.askyesno("Excluir", "Excluir esta nota?", parent=self): return
        try:
            NotaFiscal.excluir(self._nota_id)
            if self._ao_salvar: self._ao_salvar()
            self.destroy()
        except Exception as e:
            messagebox.showerror("Erro", str(e), parent=self)

    def _lancar(self):
        if self._readonly:
            self._var_erro.set("Nota já lançada."); return
        if not self._itens:
            self._var_erro.set("Adicione ao menos um item."); return

        sem_prod = [i["descricao"] for i in self._itens if not i.get("produto_id")]
        if sem_prod:
            messagebox.showerror("Itens sem produto",
                "Vincule todos os itens a um produto cadastrado:\n\n" +
                "\n".join(f"  • {d}" for d in sem_prod), parent=self)
            return

        nota_id = self._salvar()
        if nota_id is None: return

        if not messagebox.askyesno("Confirmar Autorização",
            "Autorizar a nota? O estoque será atualizado e a nota não poderá ser editada.",
            parent=self):
            return
        try:
            from services.fiscal_service import FiscalService
            FiscalService.autorizar(nota_id)
            messagebox.showinfo("Autorizada", "Nota autorizada! Estoque atualizado.", parent=self)
            if self._ao_salvar: self._ao_salvar()
            self.destroy()
        except Exception as e:
            self._var_erro.set(str(e))
            messagebox.showerror("Erro", str(e), parent=self)

    # ── Utilitários ───────────────────────────────────────────────
    def _card(self, parent):
        f = tk.Frame(parent, bg=THEME["bg_card"],
                     highlightthickness=1,
                     highlightbackground=THEME["border"])
        f.pack(fill="x", pady=(0, 4))
        inner = tk.Frame(f, bg=THEME["bg_card"], padx=12, pady=10)
        inner.pack(fill="x")
        return inner


# ════════════════════════════════════════════════════════════════
# FormItem — item individual com campos fiscais completos
# ════════════════════════════════════════════════════════════════
class FormItem(BaseView):
    def __init__(self, master, produtos, tipo_nota,
                 item=None, cfops=None, cst_icms=None, cst_pisc=None,
                 regra_padrao=None, ao_confirmar=None):
        super().__init__(master, "📦 Item da Nota Fiscal", 600, 680, modal=True)
        self.resizable(True, True)
        self._produtos    = produtos or []
        self._tipo_nota   = tipo_nota
        self._item        = item or {}
        self._cfops       = cfops or []
        self._cst_icms    = cst_icms or []
        self._cst_pisc    = cst_pisc or []
        self._regra       = regra_padrao
        self._ao_confirmar= ao_confirmar
        self._build()
        if item:
            self._preencher()
        elif regra_padrao:
            self._aplicar_regra(regra_padrao)

    def _build(self):
        # Canvas scrollável
        canvas = tk.Canvas(self, bg=THEME["bg"], highlightthickness=0)
        vsb = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True)
        body = tk.Frame(canvas, bg=THEME["bg"])
        win  = canvas.create_window((0, 0), window=body, anchor="nw")
        body.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
            lambda e: canvas.itemconfig(win, width=e.width))

        def _scroll(e): canvas.yview_scroll(int(-1*(e.delta/120)), "units")
        canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", _scroll))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

        P = 16
        tk.Label(body, text="Item da Nota", font=FONT["title"],
                 bg=THEME["bg"], fg=THEME["fg"]).pack(anchor="w", padx=P, pady=(14, 6))

        # ── Produto (SearchEntry) ──────────────────────────────────
        c1 = self._card(body, P)
        tk.Label(c1, text="Produto Cadastrado (busca por nome ou código)",
                 font=FONT["sm"], bg=THEME["bg_card"], fg=THEME["fg"]
                 ).pack(anchor="w", pady=(0, 3))
        self._se_prod = SearchEntry(
            c1,
            placeholder="Digite o nome ou código...",
            items=self._produtos,
            key_display=lambda p: f"{p.get('codigo','—')} — {p['nome']} ({p.get('unidade','UN')})",
            key_search=lambda p: f"{p.get('codigo','')} {p['nome']} {p.get('ncm','')}",
            ao_selecionar=self._on_prod_select,
        )
        self._se_prod.pack(fill="x", pady=(0, 10))

        # Campos descritivos
        self._var_desc   = tk.StringVar()
        self._var_codigo = tk.StringVar()
        self._var_ncm    = tk.StringVar()
        self._var_cest   = tk.StringVar()
        self._var_unid   = tk.StringVar(value="UN")

        CampoEntry(c1, "Descrição *", self._var_desc).pack(fill="x", pady=(0, 6))

        row1 = tk.Frame(c1, bg=THEME["bg_card"])
        row1.pack(fill="x", pady=(0, 6))
        CampoEntry(row1, "Código", self._var_codigo).pack(
            side="left", fill="x", expand=True, padx=(0, 6))
        col_u = tk.Frame(row1, bg=THEME["bg_card"], width=80)
        col_u.pack(side="left"); col_u.pack_propagate(False)
        CampoEntry(col_u, "Unidade *", self._var_unid).pack(fill="x")

        row2 = tk.Frame(c1, bg=THEME["bg_card"])
        row2.pack(fill="x", pady=(0, 6))
        CampoEntry(row2, "NCM", self._var_ncm).pack(
            side="left", fill="x", expand=True, padx=(0, 6))
        CampoEntry(row2, "CEST", self._var_cest).pack(
            side="left", fill="x", expand=True)

        # ── Quantidades e valores ──────────────────────────────────
        c2 = self._card(body, P)
        SecaoForm(c2, "QUANTIDADES E VALORES").pack(fill="x", pady=(0, 8))

        row_qv = tk.Frame(c2, bg=THEME["bg_card"])
        row_qv.pack(fill="x", pady=(0, 6))
        self._var_qtd  = tk.StringVar(value="1")
        self._var_vun  = tk.StringVar(value="0.0000")
        CampoEntry(row_qv, "Quantidade *", self._var_qtd,
                   justify="right").pack(side="left", fill="x", expand=True, padx=(0, 6))
        CampoEntry(row_qv, "Valor Unitário *", self._var_vun,
                   justify="right").pack(side="left", fill="x", expand=True)

        row_df = tk.Frame(c2, bg=THEME["bg_card"])
        row_df.pack(fill="x", pady=(0, 6))
        self._var_desconto = tk.StringVar(value="0.00")
        self._var_frete    = tk.StringVar(value="0.00")
        CampoEntry(row_df, "Desconto R$", self._var_desconto,
                   justify="right").pack(side="left", fill="x", expand=True, padx=(0, 6))
        CampoEntry(row_df, "Frete R$", self._var_frete,
                   justify="right").pack(side="left", fill="x", expand=True)

        self._lbl_total = tk.Label(c2, text="Total: R$ 0,00",
                                    font=FONT["bold"], bg=THEME["bg_card"],
                                    fg=THEME["primary"])
        self._lbl_total.pack(anchor="e", pady=(4, 0))

        # ── Fiscal ────────────────────────────────────────────────
        c3 = self._card(body, P)
        SecaoForm(c3, "DADOS FISCAIS").pack(fill="x", pady=(0, 8))

        # CFOP (SearchEntry)
        tk.Label(c3, text="CFOP", font=FONT["sm"],
                 bg=THEME["bg_card"], fg=THEME["fg"]).pack(anchor="w", pady=(0, 3))
        cfop_items = [{"id": c["id"], "codigo": c["codigo"],
                        "label": f"{c['codigo']} — {c['descricao'][:60]}"}
                       for c in self._cfops]
        self._se_cfop = SearchEntry(
            c3,
            placeholder="Buscar CFOP...",
            items=cfop_items,
            key_display=lambda d: d["label"],
            key_search=lambda d: d["label"],
            ao_selecionar=lambda d: self._var_cfop.set(d["codigo"]),
        )
        self._se_cfop.pack(fill="x", pady=(0, 2))
        self._var_cfop = tk.StringVar()
        tk.Label(c3, textvariable=self._var_cfop, font=("Consolas", 9),
                 bg=THEME["bg_card"], fg=THEME["fg_light"]).pack(anchor="e", pady=(0, 8))

        # Origem
        row_or = tk.Frame(c3, bg=THEME["bg_card"])
        row_or.pack(fill="x", pady=(0, 6))
        self._var_origem = tk.StringVar(value="0")
        tk.Label(row_or, text="Origem", font=FONT["sm"],
                 bg=THEME["bg_card"], fg=THEME["fg"]).pack(anchor="w", pady=(0, 3))
        orig_vals = ["0 — Nacional","1 — Estrangeira (import. direta)",
                     "2 — Estrangeira (adquirida merc. interno)",
                     "3 — Nacional c/ +40% conteúdo estrangeiro",
                     "4 — Nacional — processo produtivo básico",
                     "5 — Nacional c/ ≤40% conteúdo estrangeiro",
                     "6 — Estrangeira — import. direta sem similar",
                     "7 — Estrangeira — adquirida merc. interno sem similar",
                     "8 — Nacional — Rec. Basic Prod. para exportação"]
        ttk.Combobox(row_or, textvariable=self._var_origem,
                     values=orig_vals, state="readonly",
                     font=FONT["md"]).pack(fill="x", ipady=4)

        # CST ICMS
        row_cst = tk.Frame(c3, bg=THEME["bg_card"])
        row_cst.pack(fill="x", pady=(0, 6))
        tk.Label(row_cst, text="CST/CSOSN ICMS", font=FONT["sm"],
                 bg=THEME["bg_card"], fg=THEME["fg"]).pack(anchor="w", pady=(0, 3))
        cst_items = [{"codigo": c["codigo"],
                       "label": f"{c['codigo']} — {c['descricao'][:55]}  [{c.get('regime','N')}]"}
                      for c in self._cst_icms]
        self._se_cst = SearchEntry(
            row_cst,
            placeholder="Buscar CST ICMS...",
            items=cst_items,
            key_display=lambda d: d["label"],
            key_search=lambda d: d["label"],
            ao_selecionar=lambda d: self._var_cst_icms.set(d["codigo"]),
        )
        self._se_cst.pack(fill="x", pady=(0, 2))
        self._var_cst_icms = tk.StringVar()

        # BC ICMS + Alíq + Valor ICMS
        row_icms = tk.Frame(c3, bg=THEME["bg_card"])
        row_icms.pack(fill="x", pady=(0, 6))
        self._var_bc_icms    = tk.StringVar(value="0.00")
        self._var_aliq_icms  = tk.StringVar(value="0.00")
        self._var_valor_icms = tk.StringVar(value="0.00")
        for lbl, var, w in [
            ("BC ICMS R$",     self._var_bc_icms,    None),
            ("Alíq. ICMS %",   self._var_aliq_icms,  None),
            ("Valor ICMS R$",  self._var_valor_icms, None),
        ]:
            col = tk.Frame(row_icms, bg=THEME["bg_card"])
            col.pack(side="left", fill="x", expand=True, padx=(0, 4))
            CampoEntry(col, lbl, var, justify="right").pack(fill="x")
        self._var_aliq_icms.trace_add("write", self._calc_icms)
        self._var_bc_icms.trace_add("write", self._calc_icms)

        # IPI
        row_ipi = tk.Frame(c3, bg=THEME["bg_card"])
        row_ipi.pack(fill="x", pady=(0, 6))
        self._var_cst_ipi  = tk.StringVar()
        self._var_aliq_ipi = tk.StringVar(value="0.00")
        self._var_val_ipi  = tk.StringVar(value="0.00")
        CampoEntry(row_ipi, "CST IPI", self._var_cst_ipi).pack(
            side="left", fill="x", expand=True, padx=(0, 4))
        CampoEntry(row_ipi, "Alíq. IPI %", self._var_aliq_ipi,
                   justify="right").pack(side="left", fill="x", expand=True, padx=(0, 4))
        CampoEntry(row_ipi, "Valor IPI R$", self._var_val_ipi,
                   justify="right").pack(side="left", fill="x", expand=True)
        self._var_aliq_ipi.trace_add("write", self._calc_total)

        # CST PIS
        row_pis = tk.Frame(c3, bg=THEME["bg_card"])
        row_pis.pack(fill="x", pady=(0, 6))
        self._var_cst_pis   = tk.StringVar(value="07")
        self._var_aliq_pis  = tk.StringVar(value="0.65")
        self._var_val_pis   = tk.StringVar(value="0.00")
        pisc_items = [{"codigo": c["codigo"],
                        "label": f"{c['codigo']} — {c['descricao'][:50]}"}
                       for c in self._cst_pisc]
        tk.Label(c3, text="CST PIS", font=FONT["sm"],
                 bg=THEME["bg_card"], fg=THEME["fg"]).pack(anchor="w", pady=(0, 2))
        SearchEntry(c3, placeholder="CST PIS...", items=pisc_items,
                    key_display=lambda d: d["label"],
                    key_search=lambda d: d["label"],
                    ao_selecionar=lambda d: self._var_cst_pis.set(d["codigo"])
                    ).pack(fill="x", pady=(0, 6))

        row_pis2 = tk.Frame(c3, bg=THEME["bg_card"])
        row_pis2.pack(fill="x", pady=(0, 6))
        CampoEntry(row_pis2, "Alíq. PIS %", self._var_aliq_pis,
                   justify="right").pack(side="left", fill="x", expand=True, padx=(0, 4))
        CampoEntry(row_pis2, "Valor PIS R$", self._var_val_pis,
                   justify="right").pack(side="left", fill="x", expand=True)
        self._var_aliq_pis.trace_add("write", self._calc_pis_cofins)

        # CST COFINS
        self._var_cst_cof  = tk.StringVar(value="07")
        self._var_aliq_cof = tk.StringVar(value="3.00")
        self._var_val_cof  = tk.StringVar(value="0.00")
        tk.Label(c3, text="CST COFINS", font=FONT["sm"],
                 bg=THEME["bg_card"], fg=THEME["fg"]).pack(anchor="w", pady=(0, 2))
        SearchEntry(c3, placeholder="CST COFINS...", items=pisc_items,
                    key_display=lambda d: d["label"],
                    key_search=lambda d: d["label"],
                    ao_selecionar=lambda d: self._var_cst_cof.set(d["codigo"])
                    ).pack(fill="x", pady=(0, 6))

        row_cof2 = tk.Frame(c3, bg=THEME["bg_card"])
        row_cof2.pack(fill="x", pady=(0, 0))
        CampoEntry(row_cof2, "Alíq. COFINS %", self._var_aliq_cof,
                   justify="right").pack(side="left", fill="x", expand=True, padx=(0, 4))
        CampoEntry(row_cof2, "Valor COFINS R$", self._var_val_cof,
                   justify="right").pack(side="left", fill="x", expand=True)
        self._var_aliq_cof.trace_add("write", self._calc_pis_cofins)

        # Erro + Confirmar
        self._var_erro = tk.StringVar()
        tk.Label(body, textvariable=self._var_erro, font=FONT["sm"],
                 bg=THEME["bg"], fg=THEME["danger"]).pack(anchor="w", padx=P, pady=(4, 0))
        botao(body, "✅ Confirmar Item", tipo="sucesso",
              command=self._confirmar).pack(fill="x", padx=P, pady=(8, 16))

        # Traces para cálculo automático
        for v in [self._var_qtd, self._var_vun, self._var_desconto, self._var_aliq_ipi]:
            v.trace_add("write", self._calc_total)

    def _card(self, parent, padx=16):
        f = tk.Frame(parent, bg=THEME["bg_card"],
                     highlightthickness=1, highlightbackground=THEME["border"])
        f.pack(fill="x", padx=padx, pady=(0, 8))
        inner = tk.Frame(f, bg=THEME["bg_card"], padx=12, pady=10)
        inner.pack(fill="x")
        return inner

    # ── Auto-preenchimento ao selecionar produto ──────────────────
    def _on_prod_select(self, p: dict):
        self._var_codigo.set(p.get("codigo") or "")
        self._var_desc.set(p["nome"])
        self._var_ncm.set(p.get("ncm") or "")
        self._var_cest.set(p.get("cest") or "")
        self._var_unid.set(p.get("unidade") or "UN")
        preco = p.get("preco_custo") or p.get("preco_venda") or 0
        self._var_vun.set(f"{float(preco):.4f}")
        self._var_cst_icms.set(p.get("cst_icms") or "")
        self._var_aliq_icms.set(_f2s(p.get("aliq_icms") or 0))
        self._var_aliq_ipi.set(_f2s(p.get("aliq_ipi") or 0))
        self._var_aliq_pis.set(_f2s(p.get("aliq_pis") or "0.65"))
        self._var_aliq_cof.set(_f2s(p.get("aliq_cofins") or "3.00"))
        self._item["produto_id"] = p["id"]
        self._calc_total()

    # ── Aplicar regra padrão do banco ────────────────────────────
    def _aplicar_regra(self, regra: dict):
        if regra.get("cfop_codigo"):
            self._var_cfop.set(regra["cfop_codigo"])
            # Seleciona no SearchEntry
            for item in self._se_cfop._items:
                if item["codigo"] == regra["cfop_codigo"]:
                    self._se_cfop.set_item(item)
                    break
        if regra.get("cst_icms_codigo"):
            self._var_cst_icms.set(regra["cst_icms_codigo"])
        if regra.get("aliq_icms"):
            self._var_aliq_icms.set(_f2s(regra["aliq_icms"]))
        if regra.get("cst_pis_cod"):
            self._var_cst_pis.set(regra["cst_pis_cod"])
        if regra.get("aliq_pis"):
            self._var_aliq_pis.set(_f2s(regra["aliq_pis"]))
        if regra.get("cst_cofins_cod"):
            self._var_cst_cof.set(regra["cst_cofins_cod"])
        if regra.get("aliq_cofins"):
            self._var_aliq_cof.set(_f2s(regra["aliq_cofins"]))

    # ── Cálculos automáticos ──────────────────────────────────────
    def _calc_total(self, *_):
        try:
            qtd  = _s2f(self._var_qtd.get())
            vun  = _s2f(self._var_vun.get())
            desc = _s2f(self._var_desconto.get())
            aipi = _s2f(self._var_aliq_ipi.get())
            base  = qtd * vun - desc
            vipi  = round(base * aipi / 100, 2)
            total = round(base + vipi, 2)
            self._var_val_ipi.set(f"{vipi:.2f}")
            self._lbl_total.configure(
                text=f"Base: R$ {base:,.2f}  |  IPI: R$ {vipi:,.2f}  |  Total: R$ {total:,.2f}")
            # Atualiza BC ICMS automaticamente se vazio
            bc = _s2f(self._var_bc_icms.get())
            if bc == 0:
                self._var_bc_icms.set(f"{base:.2f}")
            self._calc_pis_cofins()
        except Exception:
            self._lbl_total.configure(text="Total: —")

    def _calc_icms(self, *_):
        try:
            bc   = _s2f(self._var_bc_icms.get())
            aliq = _s2f(self._var_aliq_icms.get())
            v    = round(bc * aliq / 100, 2)
            self._var_valor_icms.set(f"{v:.2f}")
        except Exception:
            pass

    def _calc_pis_cofins(self, *_):
        try:
            qtd = _s2f(self._var_qtd.get())
            vun = _s2f(self._var_vun.get())
            desc= _s2f(self._var_desconto.get())
            base = qtd * vun - desc
            apis = _s2f(self._var_aliq_pis.get())
            acof = _s2f(self._var_aliq_cof.get())
            self._var_val_pis.set(f"{round(base * apis / 100, 2):.2f}")
            self._var_val_cof.set(f"{round(base * acof / 100, 2):.2f}")
        except Exception:
            pass

    # ── Preencher edição ──────────────────────────────────────────
    def _preencher(self):
        item = self._item
        self._var_desc.set(item.get("descricao") or "")
        self._var_codigo.set(item.get("codigo") or "")
        self._var_ncm.set(item.get("ncm") or "")
        self._var_cest.set(item.get("cest") or "")
        self._var_unid.set(item.get("unidade") or "UN")
        self._var_qtd.set(str(item.get("quantidade") or 1))
        self._var_vun.set(str(item.get("valor_unitario") or 0))
        self._var_desconto.set(_f2s(item.get("desconto")))
        self._var_frete.set(_f2s(item.get("frete")))
        self._var_cfop.set(item.get("cfop") or "")
        self._var_origem.set(str(item.get("origem") or 0))
        self._var_cst_icms.set(item.get("cst_icms") or "")
        self._var_bc_icms.set(_f2s(item.get("bc_icms")))
        self._var_aliq_icms.set(_f2s(item.get("aliq_icms")))
        self._var_valor_icms.set(_f2s(item.get("valor_icms")))
        self._var_cst_ipi.set(item.get("cst_ipi") or "")
        self._var_aliq_ipi.set(_f2s(item.get("aliq_ipi")))
        self._var_val_ipi.set(_f2s(item.get("valor_ipi")))
        self._var_cst_pis.set(item.get("cst_pis") or "07")
        self._var_aliq_pis.set(_f2s(item.get("aliq_pis")))
        self._var_val_pis.set(_f2s(item.get("valor_pis")))
        self._var_cst_cof.set(item.get("cst_cofins") or "07")
        self._var_aliq_cof.set(_f2s(item.get("aliq_cofins")))
        self._var_val_cof.set(_f2s(item.get("valor_cofins")))
        # Reconectar produto
        pid = item.get("produto_id")
        if pid:
            for p in self._produtos:
                if p["id"] == pid:
                    self._se_prod.set_item(p)
                    break
        # Reconectar CFOP
        cfop_cod = item.get("cfop") or ""
        for ci in self._se_cfop._items:
            if ci["codigo"] == cfop_cod:
                self._se_cfop.set_item(ci)
                break

    # ── Confirmar ─────────────────────────────────────────────────
    def _confirmar(self):
        desc = self._var_desc.get().strip()
        if not desc:
            self._var_erro.set("Descrição é obrigatória."); return
        try:
            qtd  = _s2f(self._var_qtd.get())
            vun  = _s2f(self._var_vun.get())
            desc_val = _s2f(self._var_desconto.get())
            aipi = _s2f(self._var_aliq_ipi.get())
        except ValueError:
            self._var_erro.set("Valores numéricos inválidos."); return
        if qtd <= 0:
            self._var_erro.set("Quantidade deve ser maior que zero."); return

        base  = round(qtd * vun - desc_val, 4)
        vipi  = round(base * aipi / 100, 4)
        total = round(base + vipi, 4)

        orig_raw = self._var_origem.get()
        orig_num = int(orig_raw[0]) if orig_raw and orig_raw[0].isdigit() else 0

        item_out = {
            **self._item,
            "produto_id":     self._item.get("produto_id"),
            "codigo":         self._var_codigo.get().strip(),
            "descricao":      desc,
            "ncm":            self._var_ncm.get().strip(),
            "cest":           self._var_cest.get().strip(),
            "cfop":           self._var_cfop.get().strip(),
            "unidade":        self._var_unid.get().strip() or "UN",
            "quantidade":     qtd,
            "valor_unitario": vun,
            "desconto":       desc_val,
            "frete":          _s2f(self._var_frete.get()),
            "valor_total":    total,
            "origem":         orig_num,
            "cst_icms":       self._var_cst_icms.get().strip(),
            "bc_icms":        _s2f(self._var_bc_icms.get()),
            "aliq_icms":      _s2f(self._var_aliq_icms.get()),
            "valor_icms":     _s2f(self._var_valor_icms.get()),
            "cst_ipi":        self._var_cst_ipi.get().strip(),
            "aliq_ipi":       aipi,
            "valor_ipi":      vipi,
            "cst_pis":        self._var_cst_pis.get().strip() or "07",
            "aliq_pis":       _s2f(self._var_aliq_pis.get()),
            "valor_pis":      _s2f(self._var_val_pis.get()),
            "cst_cofins":     self._var_cst_cof.get().strip() or "07",
            "aliq_cofins":    _s2f(self._var_aliq_cof.get()),
            "valor_cofins":   _s2f(self._var_val_cof.get()),
        }
        if self._ao_confirmar:
            self._ao_confirmar(item_out)
        self.destroy()