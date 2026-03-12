import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from config import THEME, FONT
from views.base_view import BaseView
from views.widgets.tabela import Tabela
from views.widgets.widgets import PageHeader, botao
from models.nota_fiscal import STATUS_LABELS, TIPO_LABELS


class NotasView(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg=THEME["bg"])
        self.pack(fill="both", expand=True)
        try:
            from core.database import DatabaseManager
            DatabaseManager.empresa()
        except Exception:
            tk.Label(self, text="⚠  Selecione uma empresa.",
                     font=FONT["lg"], bg=THEME["bg"],
                     fg=THEME["warning"]).pack(expand=True)
            return
        self._build()

    def _build(self):
        PageHeader(self, "🧾", "Notas Fiscais",
                   "NF-e entrada, saída e devoluções."
                   ).pack(fill="x", padx=20, pady=(16, 0))

        style = ttk.Style()
        style.configure("NF.TNotebook", background=THEME["bg"], borderwidth=0)
        style.configure("NF.TNotebook.Tab",
                        background=THEME["bg_card"], foreground=THEME["fg"],
                        font=FONT["bold"], padding=(16, 8))
        style.map("NF.TNotebook.Tab",
                  background=[("selected", THEME["primary_dark"])],
                  foreground=[("selected", "white")])

        nb = ttk.Notebook(self, style="NF.TNotebook")
        nb.pack(fill="both", expand=True, padx=20, pady=12)

        self._aba_entrada   = AbaNota(nb, tipo="ENTRADA",    label="📥 Entradas")
        self._aba_saida     = AbaNota(nb, tipo="SAIDA",      label="📤 Saídas")
        self._aba_dev_compra= AbaNota(nb, tipo="DEV_COMPRA", label="↩️ Dev. Compra")
        self._aba_dev_venda = AbaNota(nb, tipo="DEV_VENDA",  label="↪️ Dev. Venda")

        nb.add(self._aba_entrada,    text="  📥 Entradas  ")
        nb.add(self._aba_saida,      text="  📤 Saídas  ")
        nb.add(self._aba_dev_compra, text="  ↩️ Dev. Compra  ")
        nb.add(self._aba_dev_venda,  text="  ↪️ Dev. Venda  ")


class AbaNota(tk.Frame):
    def __init__(self, master, tipo: str, label: str):
        super().__init__(master, bg=THEME["bg"])
        self._tipo  = tipo
        self._label = label
        self._build()
        self._carregar()

    def _build(self):
        tb = tk.Frame(self, bg=THEME["bg_card"], highlightthickness=1,
                      highlightbackground=THEME["border"], padx=14, pady=10)
        tb.pack(fill="x", pady=(0, 1))

        tk.Label(tb, text="🔍", font=("Segoe UI", 11),
                 bg=THEME["bg_card"], fg=THEME["fg_light"]).pack(side="left")
        self._var_busca = tk.StringVar()
        self._var_busca.trace_add("write", lambda *_: self._carregar())
        tk.Entry(tb, textvariable=self._var_busca, font=FONT["md"],
                 relief="flat", bg=THEME["bg"], fg=THEME["fg"],
                 highlightthickness=1, highlightbackground=THEME["border"],
                 highlightcolor=THEME["primary"], width=26
                 ).pack(side="left", padx=(4, 12), ipady=5)

        # Filtro status
        tk.Label(tb, text="Status:", font=FONT["sm"],
                 bg=THEME["bg_card"], fg=THEME["fg_light"]).pack(side="left")
        self._var_status = tk.StringVar()
        self._combo_status = ttk.Combobox(
            tb, textvariable=self._var_status, state="readonly",
            font=FONT["md"], width=14,
            values=["Todos", "RASCUNHO", "PENDENTE", "AUTORIZADA", "CANCELADA", "INUTILIZADA"]
        )
        self._combo_status.current(0)
        self._combo_status.pack(side="left", padx=(4, 12), ipady=3)
        self._combo_status.bind("<<ComboboxSelected>>", lambda _: self._carregar())

        # Botões
        from core.session import Session
        botao(tb, "🔍 Visualizar",     tipo="secundario", command=self._visualizar).pack(side="right", padx=(0, 8))
        if Session.pode("fiscal", "criar"):
            botao(tb, "+ Nova Nota",      tipo="primario",   command=self._nova).pack(side="right")
            botao(tb, "📂 Importar XML",  tipo="secundario", command=self._importar_xml).pack(side="right", padx=(0, 8))
        if Session.pode("fiscal", "editar"):
            botao(tb, "✅ Autorizar",     tipo="sucesso",    command=self._autorizar).pack(side="right", padx=(0, 8))
            botao(tb, "↩️ Estornar",     tipo="secundario", command=self._estornar).pack(side="right", padx=(0, 8))
            botao(tb, "✏ Editar",        tipo="secundario", command=self._editar).pack(side="right", padx=(0, 8))
            if self._tipo != "ENTRADA":
                botao(tb, "🚫 Cancelar", tipo="perigo",     command=self._cancelar).pack(side="right", padx=(0, 8))
        if Session.pode("fiscal", "deletar"):
            botao(tb, "🗑 Excluir",      tipo="perigo",     command=self._excluir).pack(side="right", padx=(0, 8))

        self._tabela = Tabela(self, colunas=[
            ("Nº",      70), ("Série",  50), ("Status",    110),
            ("Data",    100), ("Fornec./Cliente", 200),
            ("Doc.",    130), ("Depósito", 110),
            ("Total R$",110), ("Criado em", 130),
        ])
        self._tabela.pack(fill="both", expand=True)
        if Session.pode("fiscal", "editar"):
            self._tabela.ao_duplo_clique = lambda _: self._editar()

        rodape = tk.Frame(self, bg=THEME["bg_card"], highlightthickness=1,
                          highlightbackground=THEME["border"], padx=14, pady=6)
        rodape.pack(fill="x")
        self._lbl_total = tk.Label(rodape, text="", font=FONT["sm"],
                                    bg=THEME["bg_card"], fg=THEME["fg_light"])
        self._lbl_total.pack(side="right")

    def _carregar(self):
        from models.nota_fiscal import NotaFiscal
        status = self._var_status.get()
        lista  = NotaFiscal.listar(
            tipo=self._tipo,
            status=None if status == "Todos" else status,
            busca=self._var_busca.get().strip(),
        )
        self._tabela.limpar()
        for n in lista:
            sl, _ = STATUS_LABELS.get(n["status"], (n["status"], ""))
            self._tabela.inserir([
                n.get("numero") or "—",
                n.get("serie") or 1,
                sl,
                (n.get("data_emissao") or "")[:10],
                n.get("terceiro_nome") or "—",
                n.get("terceiro_doc") or "—",
                n.get("deposito_nome") or "—",
                f"R$ {n['total_nf']:,.2f}",
                (n.get("criado_em") or "")[:16],
            ])
        self._lbl_total.configure(text=f"{len(lista)} nota(s)")

    def _sel_id(self):
        sel = self._tabela.selecionado()
        if not sel:
            return None
        # Busca pelo número na lista atual
        from models.nota_fiscal import NotaFiscal
        status = self._var_status.get()
        lista  = NotaFiscal.listar(tipo=self._tipo,
                                    status=None if status == "Todos" else status,
                                    busca=self._var_busca.get().strip())
        idx = self._tabela.selecionado_indice()
        return lista[idx]["id"] if idx is not None and idx < len(lista) else None

    def _nova(self):
        from views.fiscal.form_nota import FormNota
        FormNota(self, tipo=self._tipo, nota_id=None, ao_salvar=self._carregar)

    def _editar(self):
        id_ = self._sel_id()
        if not id_:
            messagebox.showwarning("Atenção", "Selecione uma nota.", parent=self); return
        from views.fiscal.form_nota import FormNota
        FormNota(self, tipo=self._tipo, nota_id=id_, ao_salvar=self._carregar)

    def _cancelar(self):
        id_ = self._sel_id()
        if not id_:
            messagebox.showwarning("Atenção", "Selecione uma nota.", parent=self); return
        motivo = simpledialog.askstring(
            "Motivo do Cancelamento",
            "Informe o motivo do cancelamento:",
            parent=self
        ) or ""
        try:
            from services.fiscal_service import FiscalService
            FiscalService.cancelar(id_, motivo)
            self._carregar()
        except Exception as e:
            messagebox.showerror("Erro", str(e), parent=self)

    def _visualizar(self):
        id_ = self._sel_id()
        if not id_:
            messagebox.showwarning("Atenção", "Selecione uma nota.", parent=self); return
        from views.fiscal.danfe_view import DanfeView
        DanfeView(self, nota_id=id_)

    def _excluir(self):
        id_ = self._sel_id()
        if not id_:
            messagebox.showwarning("Atenção", "Selecione uma nota.", parent=self); return
        from models.nota_fiscal import NotaFiscal
        nota = NotaFiscal.buscar_por_id(id_)
        if not nota: return
        if nota["status"] != "RASCUNHO":
            messagebox.showerror("Erro",
                f"Só é possível excluir notas em Rascunho.\n"
                f"Esta nota está com status '{nota['status']}'.", parent=self)
            return
        if not messagebox.askyesno("Confirmar Exclusão",
            f"Excluir definitivamente a nota ID {id_}?\n"
            "Esta ação não pode ser desfeita.", parent=self):
            return
        try:
            NotaFiscal.excluir(id_)
            self._carregar()
        except Exception as e:
            messagebox.showerror("Erro", str(e), parent=self)

    def _autorizar(self):
        """Autoriza um rascunho: move estoque e marca AUTORIZADA."""
        id_ = self._sel_id()
        if not id_:
            messagebox.showwarning("Atenção", "Selecione uma nota.", parent=self); return
        from models.nota_fiscal import NotaFiscal
        nota = NotaFiscal.buscar_por_id(id_)
        if not nota: return
        if nota["status"] != "RASCUNHO":
            messagebox.showerror("Erro",
                f"Só é possível autorizar notas em Rascunho.\n"
                f"Status atual: {nota['status']}.", parent=self)
            return
        if not messagebox.askyesno("Confirmar Autorização",
            f"Autorizar a NF {nota.get('numero') or id_}?\n\n"
            "O estoque será atualizado e a nota não poderá ser editada.",
            parent=self):
            return
        try:
            from services.fiscal_service import FiscalService
            FiscalService.autorizar(id_)
            messagebox.showinfo("Autorizada", "Nota autorizada! Estoque atualizado.", parent=self)
            self._carregar()
        except Exception as e:
            messagebox.showerror("Erro ao autorizar", str(e), parent=self)

    def _estornar(self):
        """Estorna nota AUTORIZADA de volta para RASCUNHO (reverte estoque)."""
        id_ = self._sel_id()
        if not id_:
            messagebox.showwarning("Atenção", "Selecione uma nota.", parent=self); return
        from models.nota_fiscal import NotaFiscal
        nota = NotaFiscal.buscar_por_id(id_)
        if not nota: return
        if nota["status"] != "AUTORIZADA":
            messagebox.showerror("Erro",
                f"Só é possível estornar notas AUTORIZADAS.\n"
                f"Status atual: {nota['status']}.", parent=self)
            return
        motivo = simpledialog.askstring(
            "Motivo do Estorno",
            "Informe o motivo do estorno (obrigatório):",
            parent=self
        )
        if not motivo or not motivo.strip():
            return
        if not messagebox.askyesno("Confirmar Estorno",
            "Estornar a nota? O estoque será revertido e a nota voltará para Rascunho.",
            parent=self):
            return
        try:
            from services.fiscal_service import FiscalService
            FiscalService.estornar(id_, motivo.strip())
            messagebox.showinfo("Estornada",
                "Nota estornada! Estoque revertido. A nota voltou para Rascunho.",
                parent=self)
            self._carregar()
        except Exception as e:
            messagebox.showerror("Erro ao estornar", str(e), parent=self)

    def _devolver(self):
        id_ = self._sel_id()
        if not id_:
            messagebox.showwarning("Atenção", "Selecione uma nota.", parent=self); return
        if not messagebox.askyesno("Confirmar",
            "Criar nota de devolução baseada nesta nota?", parent=self):
            return
        try:
            from services.fiscal_service import FiscalService
            dev_id = FiscalService.criar_devolucao(id_)
            messagebox.showinfo("Sucesso",
                f"Nota de devolução criada (ID {dev_id}).\nAbra a aba correspondente para editar e lançar.",
                parent=self)
            self._carregar()
        except Exception as e:
            messagebox.showerror("Erro", str(e), parent=self)

    def _importar_xml(self):
        if self._tipo != "ENTRADA":
            messagebox.showinfo("Atenção",
                "A importação por XML nesta tela é específica para Entradas (Compras).\n"
                "Saídas e devoluções utilizam fluxo manual.",
                parent=self)
            return

        path = filedialog.askopenfilename(
            title="Selecionar XML NF-e",
            filetypes=[("XML NF-e", "*.xml"), ("Todos", "*.*")],
            parent=self,
        )
        if not path:
            return
        try:
            from services.xml_parser import parse_nfe_xml
            parsed = parse_nfe_xml(path)
            from views.fiscal.wizard_entrada_xml import WizardEntradaXML
            WizardEntradaXML(self, parsed, ao_salvar=self._carregar)
        except Exception as e:
            messagebox.showerror("Erro ao ler XML", str(e), parent=self)