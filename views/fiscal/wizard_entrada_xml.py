"""
WizardEntradaXML — importação de NF-e em 3 etapas.

Etapa 1 — Cabeçalho & Fornecedor
  - Dados completos da nota (somente-leitura, editável apenas data entrada)
  - Dados do emitente com status de cadastro + ação (cadastrar agora)
  - Transporte e condição de pagamento

Etapa 2 — Produtos
  - Tabela de itens com vínculo a produtos cadastrados
  - Auto-match por código; produtos novos podem ser cadastrados na hora
  - CFOP já convertido (saída→entrada)

Etapa 3 — Conferência & Gravação
  - Totais completos lado a lado XML vs calculado
  - Escolha de depósito
  - Botão "Salvar como Rascunho" (NUNCA lança automaticamente)
"""
import tkinter as tk
from tkinter import ttk, messagebox
from config import THEME, FONT
from views.base_view import BaseView
from views.widgets.widgets import SecaoForm, CampoEntry, botao
from views.widgets.date_entry import DateEntry
from core.session import Session


# ────────────────────────────────────────────────────────────────
class WizardEntradaXML(BaseView):
    def __init__(self, master, parsed: dict, ao_salvar=None):
        super().__init__(master, "📂 Importar NF-e por XML", 1100, 780, modal=True)
        self.resizable(True, True)
        self._parsed    = parsed
        self._ao_salvar = ao_salvar
        self._etapa     = 0          # 0=Cabeçalho, 1=Produtos, 2=Conferência
        self._fornecedor_id   = None  # id após cadastrar/localizar
        self._itens_vinc      = []    # lista de dicts enriquecidos da etapa 2
        self._depositos       = []
        self._produtos_cad    = []

        self._carregar_dados_base()
        self._build()
        self._ir_etapa(0)

    def _carregar_dados_base(self):
        from models.estoque import Deposito
        from models.produto import Produto
        self._depositos    = Deposito.listar()
        self._produtos_cad = Produto.listar()

        # Tenta localizar fornecedor pelo CNPJ do emitente
        from models.nota_fiscal import NotaFiscal
        doc = self._parsed["emitente"].get("doc", "")
        self._fornecedor_cad = NotaFiscal.buscar_fornecedor_por_cnpj(doc)
        self._fornecedor_id  = self._fornecedor_cad["id"] if self._fornecedor_cad else None

        # Pré-vincula itens por código do produto cadastrado
        cod_map = {}
        for p in self._produtos_cad:
            cod = str(p.get("codigo") or "").strip()
            if cod:
                cod_map[cod] = p
        self._itens_vinc = []
        for item in self._parsed["itens"]:
            item = dict(item)
            cod_forn = str(item.get("codigo_fornecedor") or "").strip()
            if cod_forn in cod_map:
                p = cod_map[cod_forn]
                item["produto_id"]    = p["id"]
                item["codigo"]        = p.get("codigo", cod_forn)
                item["produto_nome"]  = p["nome"]
                item["status_vinc"]   = "✅ Vinculado"
            else:
                item["produto_id"]   = None
                item["codigo"]       = ""
                item["produto_nome"] = ""
                item["status_vinc"]  = "⚠ Novo"
            self._itens_vinc.append(item)

    # ── Layout principal ─────────────────────────────────────────
    def _build(self):
        # Barra de progresso no topo
        top = tk.Frame(self, bg=THEME["bg_card"], highlightthickness=1,
                       highlightbackground=THEME["border"])
        top.pack(fill="x")
        self._etapa_labels = []
        etapas = ["① Cabeçalho & Fornecedor", "② Produtos", "③ Conferência & Gravar"]
        for i, txt in enumerate(etapas):
            lbl = tk.Label(top, text=txt, font=FONT["sm"],
                           bg=THEME["bg_card"], fg=THEME["fg_light"],
                           padx=20, pady=10)
            lbl.pack(side="left")
            self._etapa_labels.append(lbl)
            if i < len(etapas)-1:
                tk.Label(top, text="▶", font=FONT["sm"],
                         bg=THEME["bg_card"], fg=THEME["fg_light"]).pack(side="left")

        # Chave de acesso sempre visível
        chave = self._parsed.get("chave", "")
        chave_frame = tk.Frame(self, bg="#1a1a2e", padx=12, pady=6)
        chave_frame.pack(fill="x")
        tk.Label(chave_frame, text=f"🔑 Chave: {chave}",
                 font=("Consolas", 9), bg="#1a1a2e", fg="#7ec8e3"
                 ).pack(side="left")
        prot = self._parsed.get("protocolo") or "—"
        tk.Label(chave_frame, text=f"  |  Protocolo: {prot}",
                 font=("Consolas", 9), bg="#1a1a2e", fg="#9be99b"
                 ).pack(side="left")

        # Container das etapas
        self._container = tk.Frame(self, bg=THEME["bg"])
        self._container.pack(fill="both", expand=True)

        # Rodapé de navegação
        nav = tk.Frame(self, bg=THEME["bg_card"], highlightthickness=1,
                       highlightbackground=THEME["border"], padx=16, pady=10)
        nav.pack(fill="x")
        self._var_msg = tk.StringVar()
        tk.Label(nav, textvariable=self._var_msg, font=FONT["sm"],
                 bg=THEME["bg_card"], fg=THEME["danger"]).pack(side="left")
        self._btn_prox  = botao(nav, "Próximo ▶", tipo="primario",  command=self._avancar)
        self._btn_prox.pack(side="right")
        self._btn_ant   = botao(nav, "◀ Anterior", tipo="secundario", command=self._voltar)
        self._btn_ant.pack(side="right", padx=(0, 8))
        self._btn_gravar = botao(nav, "💾 Salvar como Rascunho", tipo="sucesso",
                                  command=self._gravar)
        self._btn_gravar.pack(side="right", padx=(0, 8))
        self._btn_gravar.pack_forget()

    # ── Navegação entre etapas ───────────────────────────────────
    def _ir_etapa(self, idx: int):
        self._etapa = idx
        for widget in self._container.winfo_children():
            widget.destroy()
        self._var_msg.set("")

        # Destaca etapa atual
        for i, lbl in enumerate(self._etapa_labels):
            lbl.configure(
                bg=THEME["primary"] if i == idx else THEME["bg_card"],
                fg="white" if i == idx else THEME["fg_light"],
                font=FONT["bold"] if i == idx else FONT["sm"],
            )

        [self._build_etapa1, self._build_etapa2, self._build_etapa3][idx]()

        self._btn_ant.configure(state="normal" if idx > 0 else "disabled")
        if idx < 2:
            self._btn_prox.pack(side="right")
            self._btn_gravar.pack_forget()
        else:
            self._btn_prox.pack_forget()
            self._btn_gravar.pack(side="right", padx=(0, 8))

    def _avancar(self):
        if self._etapa == 0:
            if not self._validar_etapa1():
                return
        elif self._etapa == 1:
            if not self._validar_etapa2():
                return
        self._ir_etapa(self._etapa + 1)

    def _voltar(self):
        if self._etapa > 0:
            self._ir_etapa(self._etapa - 1)

    # ────────────────────────────────────────────────────────────
    # ETAPA 1 — Cabeçalho & Fornecedor
    # ────────────────────────────────────────────────────────────
    def _build_etapa1(self):
        p = self._parsed
        nota = p["nota"]
        emit = p["emitente"]
        trans= p["transporte"]
        pag  = p["pagamento"]

        outer = tk.Frame(self._container, bg=THEME["bg"])
        outer.pack(fill="both", expand=True, padx=16, pady=12)

        # Dois paineis lado a lado
        col_l = tk.Frame(outer, bg=THEME["bg"])
        col_l.pack(side="left", fill="both", expand=True, padx=(0, 8))
        col_r = tk.Frame(outer, bg=THEME["bg"], width=380)
        col_r.pack(side="left", fill="y")
        col_r.pack_propagate(False)

        # ── Coluna esquerda: dados da nota ───────────────────────
        SecaoForm(col_l, "DADOS DA NOTA FISCAL").pack(fill="x")
        card = self._card(col_l)

        campos_nota = [
            ("Modelo",        nota.get("modelo")),
            ("Série",         nota.get("serie")),
            ("Número",        nota.get("numero")),
            ("Data Emissão",  nota.get("data_emissao")),
            ("Chave Acesso",  (p.get("chave") or "")[:22] + "..."),
            ("Protocolo",     p.get("protocolo") or "Sem autorização"),
        ]
        for lbl, val in campos_nota:
            row = tk.Frame(card, bg=THEME["bg_card"])
            row.pack(fill="x", pady=2)
            tk.Label(row, text=lbl + ":", font=FONT["sm"],
                     bg=THEME["bg_card"], fg=THEME["fg_light"],
                     width=14, anchor="w").pack(side="left")
            tk.Label(row, text=str(val or "—"), font=FONT["bold"],
                     bg=THEME["bg_card"], fg=THEME["fg"]).pack(side="left")

        # Data entrada — editável com DateEntry
        sep = tk.Frame(card, bg=THEME["bg_card"], height=1)
        sep.pack(fill="x", pady=(8, 4))
        row_dt = tk.Frame(card, bg=THEME["bg_card"])
        row_dt.pack(fill="x")
        tk.Label(row_dt, text="Data Entrada *", font=FONT["sm"],
                 bg=THEME["bg_card"], fg=THEME["fg"],
                 width=14, anchor="w").pack(side="left")
        self._date_entrada = DateEntry(row_dt, value=nota.get("data_entrada") or "")
        self._date_entrada.pack(side="left", padx=(4, 0))

        # Transporte
        SecaoForm(col_l, "TRANSPORTE").pack(fill="x", pady=(8, 0))
        card_t = self._card(col_l)
        transp_campos = [
            ("Modalidade", trans.get("modalidade_label")),
            ("Transportadora", trans.get("nome")),
            ("Placa", trans.get("placa")),
            ("Peso Bruto kg", trans.get("peso_bruto")),
        ]
        for lbl, val in transp_campos:
            if val:
                row = tk.Frame(card_t, bg=THEME["bg_card"])
                row.pack(fill="x", pady=1)
                tk.Label(row, text=lbl + ":", font=FONT["sm"],
                         bg=THEME["bg_card"], fg=THEME["fg_light"],
                         width=16, anchor="w").pack(side="left")
                tk.Label(row, text=str(val), font=FONT["md"],
                         bg=THEME["bg_card"], fg=THEME["fg"]).pack(side="left")

        # Condição de pagamento
        if pag:
            SecaoForm(col_l, "PAGAMENTO").pack(fill="x", pady=(8, 0))
            card_p = self._card(col_l)
            tk.Label(card_p, text=pag.get("descricao") or "—",
                     font=FONT["md"], bg=THEME["bg_card"], fg=THEME["fg"]
                     ).pack(anchor="w")
            if pag.get("duplicatas"):
                for dup in pag["duplicatas"]:
                    tk.Label(card_p,
                             text=f"  Parcela {dup['numero']} — "
                                  f"Venc: {dup['vencimento']} — "
                                  f"R$ {dup['valor']:,.2f}",
                             font=FONT["sm"], bg=THEME["bg_card"],
                             fg=THEME["fg_light"]).pack(anchor="w")

        # Informações complementares
        if p.get("info_complementar"):
            SecaoForm(col_l, "INFORMAÇÕES COMPLEMENTARES").pack(fill="x", pady=(8, 0))
            card_ic = self._card(col_l)
            txt = tk.Text(card_ic, font=("Consolas", 8), height=4,
                          relief="flat", bg=THEME["bg"], fg=THEME["fg"],
                          wrap="word", state="normal")
            txt.insert("1.0", p["info_complementar"])
            txt.configure(state="disabled")
            txt.pack(fill="x")

        # ── Coluna direita: emitente ─────────────────────────────
        SecaoForm(col_r, "EMITENTE (FORNECEDOR)").pack(fill="x")
        card_e = self._card(col_r)

        # Status cadastro
        if self._fornecedor_cad:
            status_txt = f"✅ Cadastrado — ID {self._fornecedor_cad['id']}"
            status_cor = THEME.get("success", "#1E8449")
        else:
            status_txt = "⚠ Não cadastrado — será incluído"
            status_cor = THEME.get("warning", "#D68910")

        tk.Label(card_e, text=status_txt, font=FONT["bold"],
                 bg=THEME["bg_card"], fg=status_cor).pack(anchor="w", pady=(0, 8))

        campos_emit = [
            ("CNPJ",         emit.get("cnpj")),
            ("CPF",          emit.get("cpf")),
            ("Razão Social", emit.get("nome")),
            ("Fantasia",     emit.get("fantasia")),
            ("IE",           emit.get("ie")),
            ("CRT",          {"1":"1-Simples Nacional","2":"2-Simples Excesso","3":"3-Regime Normal"}.get(emit.get("crt",""), emit.get("crt"))),
            ("Logradouro",   emit.get("logradouro")),
            ("Número",       emit.get("numero")),
            ("Bairro",       emit.get("bairro")),
            ("Cidade/UF",    f"{emit.get('cidade','')} / {emit.get('uf','')}"),
            ("CEP",          emit.get("cep")),
            ("Telefone",     emit.get("fone")),
        ]
        for lbl, val in campos_emit:
            if val:
                row = tk.Frame(card_e, bg=THEME["bg_card"])
                row.pack(fill="x", pady=1)
                tk.Label(row, text=lbl + ":", font=FONT["sm"],
                         bg=THEME["bg_card"], fg=THEME["fg_light"],
                         width=12, anchor="w").pack(side="left")
                tk.Label(row, text=str(val), font=FONT["md"],
                         bg=THEME["bg_card"], fg=THEME["fg"],
                         wraplength=220, justify="left").pack(side="left")

        if not self._fornecedor_cad:
            botao(card_e, "📋 Cadastrar Fornecedor Agora", tipo="primario",
                  command=self._cadastrar_fornecedor).pack(fill="x", pady=(12, 0))
        else:
            tk.Label(card_e,
                     text="Dados já cadastrados — serão preservados.",
                     font=FONT["sm"], bg=THEME["bg_card"],
                     fg=THEME["fg_light"]).pack(anchor="w", pady=(8, 0))

    def _validar_etapa1(self) -> bool:
        # Se fornecedor não cadastrado, cadastra automaticamente
        if not self._fornecedor_id:
            try:
                self._cadastrar_fornecedor_automatico()
            except Exception as e:
                self._var_msg.set(f"Erro ao cadastrar fornecedor: {e}")
                return False
        return True

    def _cadastrar_fornecedor(self):
        """Abre form de fornecedor pré-preenchido com dados do XML."""
        try:
            self._cadastrar_fornecedor_automatico()
            messagebox.showinfo("Fornecedor cadastrado",
                f"Fornecedor '{self._parsed['emitente']['nome']}' "
                f"cadastrado com sucesso (ID {self._fornecedor_id}).", parent=self)
            # Rebuild etapa para atualizar status
            self._ir_etapa(0)
        except Exception as e:
            messagebox.showerror("Erro", str(e), parent=self)

    def _cadastrar_fornecedor_automatico(self):
        """Cria fornecedor com dados do emitente XML."""
        emit = self._parsed["emitente"]
        db   = __import__("core.database", fromlist=["DatabaseManager"]).DatabaseManager.empresa()
        fid  = db.execute(
            """
            INSERT INTO fornecedores (
                nome, fantasia, cnpj, cpf, ie, ind_ie,
                regime_tributario, logradouro, numero_end,
                complemento, bairro, cidade, estado, cep, fone,
                cod_municipio_ibge, ativo
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1)
            """,
            (
                emit.get("nome") or "Fornecedor Importado XML",
                emit.get("fantasia") or "",
                emit.get("cnpj") or "",
                emit.get("cpf") or "",
                emit.get("ie") or "",
                1,
                int(emit.get("crt") or 1),
                emit.get("logradouro") or "",
                emit.get("numero") or "",
                emit.get("complemento") or "",
                emit.get("bairro") or "",
                emit.get("cidade") or "",
                emit.get("uf") or "",
                emit.get("cep") or "",
                emit.get("fone") or "",
                emit.get("cod_ibge") or "",
            )
        )
        self._fornecedor_id  = fid
        self._fornecedor_cad = {"id": fid, "nome": emit.get("nome")}

    # ────────────────────────────────────────────────────────────
    # ETAPA 2 — Produtos
    # ────────────────────────────────────────────────────────────
    def _build_etapa2(self):
        outer = tk.Frame(self._container, bg=THEME["bg"])
        outer.pack(fill="both", expand=True, padx=16, pady=8)

        # Legenda
        leg = tk.Frame(outer, bg=THEME["bg_card"], padx=12, pady=6,
                       highlightthickness=1, highlightbackground=THEME["border"])
        leg.pack(fill="x", pady=(0, 8))
        tk.Label(leg, text="✅ Vinculado = produto já cadastrado encontrado pelo código  |  "
                           "⚠ Novo = código não localizado — vincule ou cadastre  |  "
                           "Duplo clique para editar vínculo",
                 font=FONT["sm"], bg=THEME["bg_card"], fg=THEME["fg_light"]).pack(side="left")

        # Tabela
        from views.widgets.tabela import Tabela
        self._tab_prod = Tabela(outer, colunas=[
            ("#",        32),
            ("Cód.Forn.", 80),
            ("Descrição NF", 220),
            ("NCM",      72),
            ("Unid.",    48),
            ("Qtd.",     62),
            ("V.Unit.",  82),
            ("Total",    90),
            ("CFOP",     55),
            ("CST",      45),
            ("Produto Vinculado", 160),
            ("Status",   90),
        ])
        self._tab_prod.pack(fill="both", expand=True)
        self._tab_prod.ao_duplo_clique = lambda _: self._editar_vinculo()

        self._atualizar_tab_produtos()

        # Rodapé da etapa
        rod = tk.Frame(outer, bg=THEME["bg_card"], padx=12, pady=6,
                       highlightthickness=1, highlightbackground=THEME["border"])
        rod.pack(fill="x", pady=(6, 0))
        vinculados = sum(1 for i in self._itens_vinc if i.get("produto_id"))
        total      = len(self._itens_vinc)
        cor = THEME.get("success", "#1E8449") if vinculados == total else THEME.get("warning", "#D68910")
        tk.Label(rod, text=f"{vinculados}/{total} itens vinculados a produtos cadastrados",
                 font=FONT["bold"], bg=THEME["bg_card"], fg=cor).pack(side="left")
        botao(rod, "🔗 Editar Vínculo", tipo="secundario",
              command=self._editar_vinculo).pack(side="right")
        botao(rod, "📦 Cadastrar Produto Novo", tipo="primario",
              command=self._cadastrar_produto_novo).pack(side="right", padx=(0, 8))

    def _atualizar_tab_produtos(self):
        self._tab_prod.limpar()
        for i, item in enumerate(self._itens_vinc, 1):
            self._tab_prod.inserir([
                i,
                item.get("codigo_fornecedor") or "—",
                item.get("descricao") or "",
                item.get("ncm") or "—",
                item.get("unidade") or "—",
                f"{float(item.get('quantidade',0)):g}",
                f"{float(item.get('valor_unitario',0)):,.4f}",
                f"R$ {float(item.get('valor_total',0)):,.2f}",
                item.get("cfop") or "—",
                item.get("cst_icms") or "—",
                item.get("produto_nome") or "—",
                item.get("status_vinc") or "—",
            ])

    def _validar_etapa2(self) -> bool:
        nao_vinc = [i["descricao"] for i in self._itens_vinc if not i.get("produto_id")]
        if nao_vinc:
            resp = messagebox.askyesno(
                "Itens não vinculados",
                f"{len(nao_vinc)} item(ns) ainda não vinculados:\n\n"
                + "\n".join(f"  • {d}" for d in nao_vinc[:8])
                + ("\n  ..." if len(nao_vinc) > 8 else "")
                + "\n\nProsseguir assim mesmo? O estoque NÃO será atualizado "
                  "para esses itens ao autorizar.",
                parent=self
            )
            return resp
        return True

    def _editar_vinculo(self):
        idx = self._tab_prod.selecionado_indice()
        if idx is None:
            messagebox.showwarning("Atenção", "Selecione um item.", parent=self)
            return
        DialogVinculo(self, self._itens_vinc[idx], self._produtos_cad,
                      ao_confirmar=lambda item, i=idx: self._aplicar_vinculo(i, item))

    def _aplicar_vinculo(self, idx: int, item: dict):
        self._itens_vinc[idx] = item
        self._ir_etapa(1)  # rebuild

    def _cadastrar_produto_novo(self):
        idx = self._tab_prod.selecionado_indice()
        item_xml = self._itens_vinc[idx] if idx is not None else None
        DialogNovoProduto(self, item_xml, self._produtos_cad,
                          ao_salvar=self._on_produto_cadastrado)

    def _on_produto_cadastrado(self, produto_novo: dict, idx_item: int | None):
        """Callback após cadastrar produto novo."""
        # Atualiza lista de produtos
        from models.produto import Produto
        self._produtos_cad = Produto.listar()
        if idx_item is not None and produto_novo:
            it = self._itens_vinc[idx_item]
            it["produto_id"]   = produto_novo["id"]
            it["codigo"]       = produto_novo.get("codigo", "")
            it["produto_nome"] = produto_novo["nome"]
            it["status_vinc"]  = "✅ Vinculado"
        self._ir_etapa(1)

    # ────────────────────────────────────────────────────────────
    # ETAPA 3 — Conferência & Gravar
    # ────────────────────────────────────────────────────────────
    def _build_etapa3(self):
        outer = tk.Frame(self._container, bg=THEME["bg"])
        outer.pack(fill="both", expand=True, padx=16, pady=8)

        col_l = tk.Frame(outer, bg=THEME["bg"])
        col_l.pack(side="left", fill="both", expand=True, padx=(0, 12))
        col_r = tk.Frame(outer, bg=THEME["bg"], width=340)
        col_r.pack(side="left", fill="y")
        col_r.pack_propagate(False)

        # ── Totais comparativos ───────────────────────────────────
        SecaoForm(col_l, "CONFERÊNCIA DE TOTAIS").pack(fill="x")
        card = self._card(col_l)

        tot_xml  = self._parsed["totais"]
        tot_calc = {
            "total_produtos": sum(float(i.get("valor_total",0))  for i in self._itens_vinc),
            "total_desconto": sum(float(i.get("desconto",0))     for i in self._itens_vinc),
            "total_ipi":      sum(float(i.get("valor_ipi",0))    for i in self._itens_vinc),
            "total_icms":     sum(float(i.get("valor_icms",0))   for i in self._itens_vinc),
            "total_icms_st":  sum(float(i.get("valor_icms_st",0))for i in self._itens_vinc),
            "total_pis":      sum(float(i.get("valor_pis",0))    for i in self._itens_vinc),
            "total_cofins":   sum(float(i.get("valor_cofins",0)) for i in self._itens_vinc),
        }

        hdr = tk.Frame(card, bg=THEME["bg_card"])
        hdr.pack(fill="x", pady=(0, 6))
        for txt, w in [("Campo", 160), ("XML (NF-e)", 110), ("Calculado", 110), ("Dif.", 90)]:
            tk.Label(hdr, text=txt, font=FONT["bold"],
                     bg=THEME["bg_card"], fg=THEME["fg"],
                     width=w//7, anchor="w").pack(side="left")

        linhas = [
            ("Produtos R$",       "total_produtos"),
            ("Frete R$",          "total_frete"),
            ("Seguro R$",         "total_seguro"),
            ("Desconto R$",       "total_desconto"),
            ("Outras Despesas R$","total_outros"),
            ("IPI R$",            "total_ipi"),
            ("ICMS R$",           "total_icms"),
            ("ICMS-ST R$",        "valor_icms_st"),
            ("PIS R$",            "total_pis"),
            ("COFINS R$",         "total_cofins"),
            ("TOTAL NF R$",       "total_nf"),
        ]
        for lbl, campo in linhas:
            vxml  = float(tot_xml.get(campo) or 0)
            vcalc = float(tot_calc.get(campo) or 0)
            dif   = vxml - vcalc
            bold  = campo == "total_nf"
            cor_dif = (THEME.get("danger","red") if abs(dif) > 0.02
                       else THEME.get("success","green"))

            row = tk.Frame(card, bg=THEME["bg_card"])
            row.pack(fill="x", pady=1)
            tk.Label(row, text=lbl, font=FONT["bold"] if bold else FONT["sm"],
                     bg=THEME["bg_card"], fg=THEME["fg"],
                     width=22, anchor="w").pack(side="left")
            tk.Label(row, text=f"R$ {vxml:>11,.2f}",
                     font=FONT["bold"] if bold else FONT["md"],
                     bg=THEME["bg_card"], fg=THEME["fg"],
                     width=16, anchor="e").pack(side="left")
            tk.Label(row, text=f"R$ {vcalc:>11,.2f}" if vcalc else "—",
                     font=FONT["sm"], bg=THEME["bg_card"],
                     fg=THEME["fg_light"],
                     width=16, anchor="e").pack(side="left")
            tk.Label(row, text=f"{dif:+.2f}" if abs(dif) > 0.001 else "✅ OK",
                     font=FONT["sm"], bg=THEME["bg_card"],
                     fg=cor_dif,
                     width=12, anchor="e").pack(side="left")

        # Resumo de itens
        SecaoForm(col_l, "RESUMO DE PRODUTOS").pack(fill="x", pady=(8, 0))
        card_r = self._card(col_l)
        vinc  = sum(1 for i in self._itens_vinc if i.get("produto_id"))
        total = len(self._itens_vinc)
        cor   = THEME.get("success","green") if vinc == total else THEME.get("warning","orange")
        tk.Label(card_r,
                 text=f"{'✅' if vinc==total else '⚠'} {vinc}/{total} itens vinculados a produtos cadastrados.",
                 font=FONT["bold"], bg=THEME["bg_card"], fg=cor).pack(anchor="w")
        if vinc < total:
            tk.Label(card_r,
                     text=f"⚠ {total-vinc} item(ns) sem vínculo NÃO movimentarão o estoque.",
                     font=FONT["sm"], bg=THEME["bg_card"],
                     fg=THEME.get("warning","orange")).pack(anchor="w", pady=(4,0))

        # ── Coluna direita ────────────────────────────────────────
        SecaoForm(col_r, "CONFIGURAÇÕES DE ENTRADA").pack(fill="x")
        card_cfg = self._card(col_r)

        # Depósito
        tk.Label(card_cfg, text="Depósito de entrada *", font=FONT["sm"],
                 bg=THEME["bg_card"], fg=THEME["fg"]).pack(anchor="w", pady=(0, 3))
        self._var_dep = tk.StringVar()
        self._combo_dep = ttk.Combobox(card_cfg, textvariable=self._var_dep,
                                        values=[d["nome"] for d in self._depositos],
                                        state="readonly", font=FONT["md"])
        if self._depositos:
            self._combo_dep.current(0)
        self._combo_dep.pack(fill="x", ipady=5, pady=(0, 10))

        # Data entrada (compartilha o mesmo DateEntry da etapa 1)
        tk.Label(card_cfg, text="Data de Entrada", font=FONT["sm"],
                 bg=THEME["bg_card"], fg=THEME["fg"]).pack(anchor="w", pady=(0, 3))
        if hasattr(self, "_date_entrada"):
            # Recria o DateEntry na etapa 3 com o valor atual
            de3 = DateEntry(card_cfg, value=self._date_entrada.get())
            de3.pack(fill="x", pady=(0, 10))
            self._date_entrada = de3  # atualiza referência
        else:
            import datetime
            de3 = DateEntry(card_cfg, value=datetime.date.today().isoformat())
            de3.pack(fill="x", pady=(0, 10))
            self._date_entrada = de3

        # Observações
        tk.Label(card_cfg, text="Observações (opcional)", font=FONT["sm"],
                 bg=THEME["bg_card"], fg=THEME["fg"]).pack(anchor="w", pady=(0, 3))
        self._txt_obs = tk.Text(card_cfg, font=FONT["md"], height=4,
                                 relief="flat", bg="white", fg=THEME["fg"],
                                 highlightthickness=1,
                                 highlightbackground=THEME["border"], wrap="word")
        self._txt_obs.pack(fill="x", pady=(0, 10))

        # Aviso sobre rascunho
        SecaoForm(col_r, "ATENÇÃO").pack(fill="x", pady=(12, 0))
        av = self._card(col_r)
        tk.Label(av,
                 text="A nota será salva como RASCUNHO.\n\n"
                      "Você poderá consultá-la, conferir os dados\n"
                      "e só então AUTORIZAR o lançamento.\n\n"
                      "Ao autorizar, o estoque será atualizado\n"
                      "automaticamente.",
                 font=FONT["sm"], bg=THEME["bg_card"],
                 fg=THEME["fg"], justify="left").pack(anchor="w")

        # Fornecedor que será vinculado
        SecaoForm(col_r, "FORNECEDOR").pack(fill="x", pady=(12, 0))
        card_f = self._card(col_r)
        nome_f = (self._fornecedor_cad or {}).get("nome") or self._parsed["emitente"]["nome"]
        id_f   = self._fornecedor_id
        tk.Label(card_f,
                 text=f"{'✅' if id_f else '⚠'} {nome_f}\n"
                      f"ID: {id_f or 'não cadastrado'}",
                 font=FONT["sm"], bg=THEME["bg_card"],
                 fg=THEME["fg"]).pack(anchor="w")

    def _gravar(self):
        """Salva nota como RASCUNHO. Nunca lança automaticamente."""
        dep_idx = getattr(self, "_combo_dep", None)
        if dep_idx is None:
            self._var_msg.set("Vá até a etapa 3 para escolher o depósito.")
            return
        idx = self._combo_dep.current()
        if idx < 0:
            self._var_msg.set("Selecione o depósito.")
            return

        # ── Bloquear período fiscal fechado ANTES de qualquer operação ──
        from services.fiscal_guard import FiscalGuard, FiscalBloqueado
        nota_aux = self._parsed.get("nota", {})
        data_ref = (
            self._date_entrada.get()
            if hasattr(self, "_date_entrada") and self._date_entrada.get()
            else nota_aux.get("data_entrada") or nota_aux.get("data_emissao") or ""
        )
        try:
            FiscalGuard.verificar(data_ref, "importar esta nota fiscal")
        except FiscalBloqueado as e:
            messagebox.showerror("Período Fiscal Fechado", str(e), parent=self)
            return

        from models.nota_fiscal import NotaFiscal

        # Validação de duplicata
        nota_d = dict(self._parsed["nota"])
        doc    = nota_d.get("terceiro_doc") or ""
        numero = nota_d.get("numero")
        serie  = nota_d.get("serie") or 1
        if numero and doc:
            dup = NotaFiscal.verificar_duplicata(numero, serie, doc)
            if dup:
                messagebox.showerror(
                    "Nota duplicada — operação bloqueada",
                    f"Já existe a NF {numero}/{serie} do fornecedor "
                    f"'{nota_d.get('terceiro_nome')}' com status '{dup['status']}' "
                    f"(ID {dup['id']}) no sistema.\n\n"
                    "Não é possível dar entrada na mesma nota duas vezes.",
                    parent=self
                )
                return

        # Monta dados
        obs = self._txt_obs.get("1.0", "end-1c").strip() if hasattr(self, "_txt_obs") else ""
        nota_d.update({
            "status":       "RASCUNHO",
            "terceiro_id":  self._fornecedor_id,
            "deposito_id":  self._depositos[idx]["id"],
            "data_entrada": self._date_entrada.get() if hasattr(self, "_date_entrada") else "",
            "observacoes":  obs or None,
            "usuario_id":   Session.usuario_id(),
            "usuario_nome": Session.nome(),
        })

        try:
            nota_id = NotaFiscal.criar(nota_d)
            for item in self._itens_vinc:
                item_save = dict(item)
                item_save.pop("status_vinc", None)
                item_save.pop("produto_nome", None)
                item_save.pop("cfop_original", None)
                item_save.pop("outros", None)
                NotaFiscal.salvar_item(nota_id, item_save)

            nf_label = f"NF {nota_d.get('numero') or nota_id}/{serie}"
            vinc = sum(1 for i in self._itens_vinc if i.get("produto_id"))
            tot  = len(self._itens_vinc)

            msg = (f"✅ {nf_label} gravada como RASCUNHO com sucesso!\n\n"
                   f"• {vinc}/{tot} itens vinculados a produtos.\n"
                   f"• Fornecedor: {nota_d.get('terceiro_nome')}\n\n"
                   f"Consulte a nota na lista e autorize o lançamento "
                   f"quando estiver tudo conferido.")
            messagebox.showinfo("Nota gravada", msg, parent=self)

            if self._ao_salvar:
                self._ao_salvar()
            self.destroy()

        except Exception as e:
            messagebox.showerror("Erro ao gravar", str(e), parent=self)

    def _card(self, parent):
        f = tk.Frame(parent, bg=THEME["bg_card"], highlightthickness=1,
                     highlightbackground=THEME["border"])
        f.pack(fill="x", pady=(0, 4))
        inner = tk.Frame(f, bg=THEME["bg_card"], padx=12, pady=10)
        inner.pack(fill="x")
        return inner


# ── Dialog de vínculo de produto ────────────────────────────────
class DialogVinculo(BaseView):
    """Permite vincular um item do XML a um produto cadastrado."""
    def __init__(self, master, item: dict, produtos: list, ao_confirmar=None):
        super().__init__(master, "🔗 Vincular Produto", 560, 420, modal=True)
        self._item = dict(item)
        self._produtos = produtos
        self._ao_confirmar = ao_confirmar
        self._build()

    def _build(self):
        P = 20
        tk.Label(self, text="Vincular Item da NF a Produto Cadastrado",
                 font=FONT["title"], bg=THEME["bg"], fg=THEME["fg"]
                 ).pack(anchor="w", padx=P, pady=(16, 4))

        # Info do item
        card = tk.Frame(self, bg=THEME["bg_card"], highlightthickness=1,
                        highlightbackground=THEME["border"])
        card.pack(fill="x", padx=P, pady=(0, 10))
        inner = tk.Frame(card, bg=THEME["bg_card"], padx=12, pady=8)
        inner.pack(fill="x")
        tk.Label(inner, text=f"Item NF: {self._item.get('descricao','')}",
                 font=FONT["bold"], bg=THEME["bg_card"], fg=THEME["fg"]
                 ).pack(anchor="w")
        tk.Label(inner,
                 text=f"Cód. Fornecedor: {self._item.get('codigo_fornecedor','')}  |  "
                      f"NCM: {self._item.get('ncm','')}  |  "
                      f"Qtd: {self._item.get('quantidade',0)}  "
                      f"Un: {self._item.get('unidade','')}",
                 font=FONT["sm"], bg=THEME["bg_card"], fg=THEME["fg_light"]
                 ).pack(anchor="w")

        # Busca de produto
        tk.Label(self, text="Buscar produto cadastrado:",
                 font=FONT["sm"], bg=THEME["bg"],
                 fg=THEME["fg"]).pack(anchor="w", padx=P, pady=(8, 3))
        self._var_busca = tk.StringVar()
        self._var_busca.trace_add("write", self._filtrar)
        tk.Entry(self, textvariable=self._var_busca, font=FONT["md"],
                 relief="flat", bg="white", fg=THEME["fg"],
                 highlightthickness=1,
                 highlightbackground=THEME["border"],
                 highlightcolor=THEME["primary"]
                 ).pack(fill="x", padx=P, ipady=6)

        from views.widgets.tabela import Tabela
        self._tab = Tabela(self, colunas=[
            ("ID", 40), ("Código", 70), ("Nome", 250),
            ("Unid.", 48), ("NCM", 72),
        ])
        self._tab.pack(fill="both", expand=True, padx=P, pady=8)
        self._tab.ao_duplo_clique = lambda _: self._confirmar()

        self._filtrar()

        # Campos editáveis de ICMS
        card_icms = tk.Frame(self, bg=THEME["bg_card"], highlightthickness=1,
                             highlightbackground=THEME["border"])
        card_icms.pack(fill="x", padx=P, pady=(0, 6))
        ic = tk.Frame(card_icms, bg=THEME["bg_card"], padx=12, pady=8)
        ic.pack(fill="x")
        tk.Label(ic, text="Valores de ICMS (editáveis — use 0 para zerar):",
                 font=FONT["sm"], bg=THEME["bg_card"],
                 fg=THEME["fg_light"]).pack(anchor="w", pady=(0, 6))
        row_icms = tk.Frame(ic, bg=THEME["bg_card"])
        row_icms.pack(fill="x")
        self._var_bc_icms    = tk.StringVar(value=f"{float(self._item.get('bc_icms') or 0):.2f}")
        self._var_valor_icms = tk.StringVar(value=f"{float(self._item.get('valor_icms') or 0):.2f}")
        self._var_aliq_icms  = tk.StringVar(value=f"{float(self._item.get('aliq_icms') or 0):.2f}")
        for lbl, var, w in [
            ("BC ICMS R$", self._var_bc_icms, 90),
            ("Alíq. %",    self._var_aliq_icms, 70),
            ("Vlr. ICMS R$",self._var_valor_icms, 90),
        ]:
            col = tk.Frame(row_icms, bg=THEME["bg_card"])
            col.pack(side="left", padx=(0, 12))
            tk.Label(col, text=lbl, font=FONT["sm"],
                     bg=THEME["bg_card"], fg=THEME["fg"]).pack(anchor="w")
            tk.Entry(col, textvariable=var, font=FONT["md"],
                     width=w//7, relief="flat",
                     bg=THEME["bg"], fg=THEME["fg"],
                     justify="right",
                     highlightthickness=1,
                     highlightbackground=THEME["border"],
                     highlightcolor=THEME["primary"]
                     ).pack(ipady=4)

        rodape = tk.Frame(self, bg=THEME["bg"], padx=P, pady=8)
        rodape.pack(fill="x")
        botao(rodape, "✅ Vincular Selecionado", tipo="sucesso",
              command=self._confirmar).pack(side="right")
        botao(rodape, "🚫 Remover Vínculo", tipo="perigo",
              command=self._remover_vinculo).pack(side="right", padx=(0, 8))

    def _filtrar(self, *_):
        busca = self._var_busca.get().lower()
        self._tab.limpar()
        self._filtrados = []
        for p in self._produtos:
            if (busca in (p.get("nome") or "").lower() or
                busca in (p.get("codigo") or "").lower() or
                busca in (p.get("ncm") or "").lower()):
                self._filtrados.append(p)
                self._tab.inserir([
                    p["id"],
                    p.get("codigo") or "—",
                    p["nome"],
                    p.get("unidade") or "UN",
                    p.get("ncm") or "—",
                ])

    def _confirmar(self):
        idx = self._tab.selecionado_indice()
        if idx is None:
            messagebox.showwarning("Atenção", "Selecione um produto.", parent=self)
            return
        p = self._filtrados[idx]
        self._item["produto_id"]   = p["id"]
        self._item["codigo"]       = p.get("codigo", "")
        self._item["produto_nome"] = p["nome"]
        self._item["status_vinc"]  = "✅ Vinculado"
        # Aplica edições de ICMS
        try:
            self._item["bc_icms"]    = float(self._var_bc_icms.get().replace(",",".") or 0)
            self._item["aliq_icms"]  = float(self._var_aliq_icms.get().replace(",",".") or 0)
            self._item["valor_icms"] = float(self._var_valor_icms.get().replace(",",".") or 0)
        except (ValueError, AttributeError):
            pass
        if self._ao_confirmar:
            self._ao_confirmar(self._item)
        self.destroy()

    def _remover_vinculo(self):
        self._item["produto_id"]   = None
        self._item["codigo"]       = ""
        self._item["produto_nome"] = ""
        self._item["status_vinc"]  = "⚠ Novo"
        if self._ao_confirmar:
            self._ao_confirmar(self._item)
        self.destroy()


# ── Dialog de cadastro de produto novo ──────────────────────────
class DialogNovoProduto(BaseView):
    """Cadastra produto novo pré-preenchido com dados do item XML."""
    def __init__(self, master, item_xml: dict | None, produtos: list, ao_salvar=None):
        super().__init__(master, "📦 Cadastrar Novo Produto", 520, 560, modal=True)
        self.resizable(True, True)
        self._item_xml  = item_xml or {}
        self._produtos  = produtos
        self._ao_salvar = ao_salvar
        self._idx_item  = None  # para propagar o vínculo de volta
        self._build()

    def _build(self):
        P = 20
        tk.Label(self, text="Cadastrar Novo Produto",
                 font=FONT["title"], bg=THEME["bg"], fg=THEME["fg"]
                 ).pack(anchor="w", padx=P, pady=(16, 4))

        if self._item_xml:
            info = tk.Frame(self, bg="#e8f4f8", padx=12, pady=8)
            info.pack(fill="x", padx=P, pady=(0, 8))
            tk.Label(info, text=f"Pré-preenchido com dados da NF: "
                                f"{self._item_xml.get('descricao','')}",
                     font=FONT["sm"], bg="#e8f4f8", fg="#0c5460").pack(anchor="w")

        card = tk.Frame(self, bg=THEME["bg_card"], highlightthickness=1,
                        highlightbackground=THEME["border"])
        card.pack(fill="x", padx=P)
        c = tk.Frame(card, bg=THEME["bg_card"], padx=14, pady=12)
        c.pack(fill="x")

        # Próximo código disponível
        from models.produto import Produto
        try:
            ultimos = Produto.listar()
            codigos_num = [int(p.get("codigo") or 0)
                           for p in ultimos if str(p.get("codigo") or "").isdigit()]
            prox_cod = str(max(codigos_num) + 1) if codigos_num else "1"
        except Exception:
            prox_cod = ""

        self._vars = {}
        campos = [
            ("codigo",    "Código interno *", prox_cod),
            ("nome",      "Nome *", self._item_xml.get("descricao", "")),
            ("ncm",       "NCM", self._item_xml.get("ncm", "")),
            ("cest",      "CEST", self._item_xml.get("cest", "")),
            ("unidade",   "Unidade", self._item_xml.get("unidade", "UN")),
            ("preco_custo","Custo R$", f"{float(self._item_xml.get('valor_unitario',0)):.4f}"),
            ("preco_venda","Venda R$", "0.00"),
            ("cst_icms",  "CST ICMS", self._item_xml.get("cst_icms", "")),
            ("aliq_icms", "Alíq. ICMS %",
             str(self._item_xml.get("aliq_icms", "0"))),
        ]
        for chave, label, default in campos:
            var = tk.StringVar(value=default)
            self._vars[chave] = var
            CampoEntry(c, label, var).pack(fill="x", pady=(0, 6))

        self._var_erro = tk.StringVar()
        tk.Label(self, textvariable=self._var_erro, font=FONT["sm"],
                 bg=THEME["bg"], fg=THEME["danger"]).pack(anchor="w", padx=P, pady=(4, 0))
        botao(self, "💾 Cadastrar e Vincular", tipo="sucesso",
              command=self._salvar).pack(fill="x", padx=P, pady=(8, 16))

    def _salvar(self):
        nome = self._vars["nome"].get().strip()
        cod  = self._vars["codigo"].get().strip()
        if not nome:
            self._var_erro.set("Nome é obrigatório."); return
        if not cod:
            self._var_erro.set("Código é obrigatório."); return

        try:
            db = __import__("core.database", fromlist=["DatabaseManager"]).DatabaseManager.empresa()
            pid = db.execute(
                """
                INSERT INTO produtos (
                    codigo, nome, ncm, cest, unidade,
                    preco_custo, preco_venda,
                    cst_icms, aliq_icms, ativo
                ) VALUES (?,?,?,?,?,?,?,?,?,1)
                """,
                (
                    cod,
                    nome,
                    self._vars["ncm"].get().strip() or None,
                    self._vars["cest"].get().strip() or None,
                    self._vars["unidade"].get().strip() or "UN",
                    float(self._vars["preco_custo"].get().replace(",",".") or 0),
                    float(self._vars["preco_venda"].get().replace(",",".") or 0),
                    self._vars["cst_icms"].get().strip() or None,
                    float(self._vars["aliq_icms"].get().replace(",",".") or 0),
                )
            )
            produto_novo = {"id": pid, "nome": nome, "codigo": cod}
            if self._ao_salvar:
                self._ao_salvar(produto_novo, self._idx_item)
            self.destroy()
        except Exception as e:
            self._var_erro.set(str(e))