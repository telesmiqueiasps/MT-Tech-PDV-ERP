"""
FiscalConfigView — Painel de Configurações Fiscais (admin global).
Abas: CFOP | CST ICMS | CST PIS/COFINS | Alíquotas ICMS | Regras | Fechamentos
"""
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import datetime
from config import THEME, FONT
from views.widgets.widgets import SecaoForm, CampoEntry, botao
from views.widgets.tabela import Tabela
from models.fiscal_config import FiscalConfig
from core.session import Session


# ── utilitários ──────────────────────────────────────────────────
def _s2f(s):
    try: return float(str(s).replace(",",".") or 0)
    except: return 0.0


class FiscalConfigView(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg=THEME["bg"])
        self.pack(fill="both", expand=True)
        self._build()

    def _build(self):
        # Cabeçalho
        hdr = tk.Frame(self, bg=THEME["primary"], padx=20, pady=14)
        hdr.pack(fill="x")
        tk.Label(hdr, text="⚙  Configurações Fiscais",
                 font=FONT["title"], bg=THEME["primary"], fg="white").pack(side="left")
        tk.Label(hdr, text="Admin Global",
                 font=FONT["sm"], bg=THEME["primary"], fg="#cce").pack(side="right")

        # Notebook
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=12, pady=8)

        abas = [
            ("📋 CFOP",          AbaCFOP),
            ("🏷 CST ICMS",      AbaCST_ICMS),
            ("🧾 CST PIS/COF",   AbaCST_PIS),
            ("📊 Alíq. ICMS",    AbaAliqICMS),
            ("⚙  Regras",        AbaRegras),
            ("🔒 Fechamentos",   AbaFechamentos),
        ]
        for label, Cls in abas:
            f = tk.Frame(nb, bg=THEME["bg"])
            nb.add(f, text=label)
            Cls(f)

        # ── Barra NFC-e ───────────────────────────────────────────────
        nfce_bar = tk.Frame(self, bg=THEME["bg_card"],
                            highlightthickness=1, highlightbackground=THEME["border"],
                            padx=12, pady=8)
        nfce_bar.pack(fill="x", padx=12, pady=(0, 8))
        tk.Label(nfce_bar, text="NFC-e — Nota Fiscal de Consumidor Eletrônica:",
                 font=FONT["sm"], bg=THEME["bg_card"], fg=THEME["fg"]).pack(side="left")
        tk.Button(nfce_bar, text="⚙ Configurar NFC-e", font=FONT["sm"],
                  bg=THEME["primary"], fg="white", relief="flat", padx=12, pady=4,
                  command=self._abrir_config_nfce).pack(side="left", padx=(12, 6))
        tk.Button(nfce_bar, text="📄 Documentos NFC-e", font=FONT["sm"],
                  bg=THEME["secondary"], fg="white", relief="flat", padx=12, pady=4,
                  command=self._abrir_documentos_nfce).pack(side="left", padx=(0, 6))

    def _abrir_config_nfce(self):
        try:
            from fiscal.nfce_config_view import NfceConfigView
            NfceConfigView(self)
        except Exception as e:
            messagebox.showerror("Erro", str(e), parent=self)

    def _abrir_documentos_nfce(self):
        try:
            from fiscal.nfce_documentos_view import NfceDocumentosView
            NfceDocumentosView(self)
        except Exception as e:
            messagebox.showerror("Erro", str(e), parent=self)


# ════════════════════════════════════════════════════════════════
# Aba CFOP
# ════════════════════════════════════════════════════════════════
class AbaCFOP(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg=THEME["bg"])
        self.pack(fill="both", expand=True, padx=8, pady=8)
        self._build()
        self._carregar()

    def _build(self):
        # Filtros
        fil = tk.Frame(self, bg=THEME["bg"])
        fil.pack(fill="x", pady=(0, 6))

        self._var_busca  = tk.StringVar()
        self._var_tipo   = tk.StringVar(value="")
        self._var_sit    = tk.StringVar(value="")

        tk.Label(fil, text="Buscar:", font=FONT["sm"],
                 bg=THEME["bg"], fg=THEME["fg"]).pack(side="left")
        tk.Entry(fil, textvariable=self._var_busca, font=FONT["md"],
                 relief="flat", bg="white", fg=THEME["fg"],
                 highlightthickness=1, highlightbackground=THEME["border"],
                 width=24).pack(side="left", ipady=4, padx=(4, 12))

        tk.Label(fil, text="Tipo:", font=FONT["sm"],
                 bg=THEME["bg"], fg=THEME["fg"]).pack(side="left")
        ttk.Combobox(fil, textvariable=self._var_tipo, width=16,
                     values=["", "ENTRADA", "SAIDA", "DEV_COMPRA", "DEV_VENDA"],
                     state="readonly", font=FONT["sm"]
                     ).pack(side="left", padx=(4, 12))

        tk.Label(fil, text="Situação:", font=FONT["sm"],
                 bg=THEME["bg"], fg=THEME["fg"]).pack(side="left")
        ttk.Combobox(fil, textvariable=self._var_sit, width=14,
                     values=["", "A — Intraestadual", "B — Interestadual", "C — Exterior"],
                     state="readonly", font=FONT["sm"]
                     ).pack(side="left", padx=(4, 12))

        botao(fil, "🔍 Filtrar", tipo="secundario",
              command=self._carregar).pack(side="left")
        botao(fil, "+ Novo CFOP", tipo="primario",
              command=self._novo).pack(side="right")
        botao(fil, "✏ Editar", tipo="secundario",
              command=self._editar).pack(side="right", padx=(0, 6))
        botao(fil, "🗑 Excluir", tipo="perigo",
              command=self._excluir).pack(side="right", padx=(0, 6))

        self._tab = Tabela(self, colunas=[
            ("ID", 40), ("Código", 65), ("Tipo", 90), ("Situação", 100),
            ("Descrição", 360), ("Ativo", 50),
        ])
        self._tab.pack(fill="both", expand=True)
        self._tab.ao_duplo_clique = lambda _: self._editar()

    def _carregar(self):
        sit_raw = self._var_sit.get()
        sit = sit_raw[0] if sit_raw else ""
        rows = FiscalConfig.listar_cfop(
            tipo_op=self._var_tipo.get() or None,
            situacao=sit or None,
            busca=self._var_busca.get(),
            apenas_ativos=False,
        )
        self._dados = rows
        self._tab.limpar()
        sit_label = {"A": "Intraestadual", "B": "Interestadual", "C": "Exterior"}
        for r in rows:
            self._tab.inserir([
                r["id"], r["codigo"], r["tipo_op"],
                sit_label.get(r.get("situacao","A"), r.get("situacao","")),
                r["descricao"],
                "✅" if r.get("ativo") else "❌",
            ])

    def _novo(self):
        FormCFOP(self, ao_salvar=self._carregar)

    def _editar(self):
        idx = self._tab.selecionado_indice()
        if idx is None:
            messagebox.showwarning("Atenção", "Selecione um CFOP.", parent=self); return
        FormCFOP(self, dados=self._dados[idx], ao_salvar=self._carregar)

    def _excluir(self):
        idx = self._tab.selecionado_indice()
        if idx is None: return
        if not messagebox.askyesno("Excluir", "Excluir este CFOP?", parent=self): return
        FiscalConfig.excluir_cfop(self._dados[idx]["id"])
        self._carregar()


class FormCFOP(tk.Toplevel):
    def __init__(self, master, dados=None, ao_salvar=None):
        super().__init__(master)
        self.title("CFOP")
        self.configure(bg=THEME["bg"])
        self.resizable(False, False)
        self.grab_set()
        self._dados    = dados
        self._ao_salvar= ao_salvar
        self._build()
        if dados:
            self._preencher()

    def _build(self):
        P = 16
        tk.Label(self, text="Cadastro de CFOP", font=FONT["title"],
                 bg=THEME["bg"], fg=THEME["fg"]).pack(anchor="w", padx=P, pady=(14, 8))

        c = tk.Frame(self, bg=THEME["bg_card"], highlightthickness=1,
                     highlightbackground=THEME["border"])
        c.pack(fill="x", padx=P, pady=(0, 8))
        ci = tk.Frame(c, bg=THEME["bg_card"], padx=12, pady=10)
        ci.pack(fill="x")

        self._var_cod  = tk.StringVar()
        self._var_desc = tk.StringVar()
        self._var_tipo = tk.StringVar(value="ENTRADA")
        self._var_sit  = tk.StringVar(value="A")
        self._var_obs  = tk.StringVar()
        self._var_ativo= tk.BooleanVar(value=True)

        CampoEntry(ci, "Código CFOP *", self._var_cod).pack(fill="x", pady=(0, 6))
        CampoEntry(ci, "Descrição *", self._var_desc).pack(fill="x", pady=(0, 6))

        row = tk.Frame(ci, bg=THEME["bg_card"])
        row.pack(fill="x", pady=(0, 6))
        for lbl, var, vals in [
            ("Tipo de Operação", self._var_tipo,
             ["ENTRADA","SAIDA","DEV_COMPRA","DEV_VENDA"]),
            ("Situação", self._var_sit,
             ["A — Intraestadual","B — Interestadual","C — Exterior"]),
        ]:
            col = tk.Frame(row, bg=THEME["bg_card"])
            col.pack(side="left", fill="x", expand=True, padx=(0, 8))
            tk.Label(col, text=lbl, font=FONT["sm"],
                     bg=THEME["bg_card"], fg=THEME["fg"]).pack(anchor="w")
            ttk.Combobox(col, textvariable=var, values=vals,
                         state="readonly", font=FONT["md"]).pack(fill="x", ipady=4)

        CampoEntry(ci, "Observação", self._var_obs).pack(fill="x", pady=(0, 6))
        tk.Checkbutton(ci, text="Ativo", variable=self._var_ativo,
                       bg=THEME["bg_card"], fg=THEME["fg"],
                       font=FONT["sm"], activebackground=THEME["bg_card"]
                       ).pack(anchor="w")

        self._var_err = tk.StringVar()
        tk.Label(self, textvariable=self._var_err, font=FONT["sm"],
                 bg=THEME["bg"], fg=THEME["danger"]).pack(anchor="w", padx=P)
        botao(self, "💾 Salvar", tipo="sucesso",
              command=self._salvar).pack(fill="x", padx=P, pady=(6, 16))

    def _preencher(self):
        d = self._dados
        self._var_cod.set(d.get("codigo",""))
        self._var_desc.set(d.get("descricao",""))
        self._var_tipo.set(d.get("tipo_op","ENTRADA"))
        s = d.get("situacao","A")
        mapa = {"A":"A — Intraestadual","B":"B — Interestadual","C":"C — Exterior"}
        self._var_sit.set(mapa.get(s, s))
        self._var_obs.set(d.get("obs") or "")
        self._var_ativo.set(bool(d.get("ativo", 1)))

    def _salvar(self):
        cod  = self._var_cod.get().strip()
        desc = self._var_desc.get().strip()
        if not cod or not desc:
            self._var_err.set("Código e descrição são obrigatórios."); return
        sit_raw = self._var_sit.get()
        sit     = sit_raw[0] if sit_raw else "A"
        dados = {
            "codigo": cod, "descricao": desc,
            "tipo_op": self._var_tipo.get(),
            "situacao": sit,
            "obs": self._var_obs.get().strip() or None,
            "ativo": int(self._var_ativo.get()),
        }
        try:
            FiscalConfig.salvar_cfop(dados, id_=self._dados["id"] if self._dados else None)
            if self._ao_salvar: self._ao_salvar()
            self.destroy()
        except Exception as e:
            self._var_err.set(str(e))


# ════════════════════════════════════════════════════════════════
# Aba CST ICMS
# ════════════════════════════════════════════════════════════════
class AbaCST_ICMS(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg=THEME["bg"])
        self.pack(fill="both", expand=True, padx=8, pady=8)
        self._build(); self._carregar()

    def _build(self):
        fil = tk.Frame(self, bg=THEME["bg"])
        fil.pack(fill="x", pady=(0, 6))
        self._var_busca  = tk.StringVar()
        self._var_regime = tk.StringVar(value="")
        tk.Label(fil, text="Buscar:", font=FONT["sm"],
                 bg=THEME["bg"], fg=THEME["fg"]).pack(side="left")
        tk.Entry(fil, textvariable=self._var_busca, font=FONT["md"],
                 relief="flat", bg="white", fg=THEME["fg"],
                 highlightthickness=1, highlightbackground=THEME["border"],
                 width=22).pack(side="left", ipady=4, padx=(4, 12))
        tk.Label(fil, text="Regime:", font=FONT["sm"],
                 bg=THEME["bg"], fg=THEME["fg"]).pack(side="left")
        ttk.Combobox(fil, textvariable=self._var_regime, width=20,
                     values=["", "N — Regime Normal", "S — Simples Nacional"],
                     state="readonly", font=FONT["sm"]
                     ).pack(side="left", padx=(4, 12))
        botao(fil, "🔍 Filtrar", tipo="secundario",
              command=self._carregar).pack(side="left")
        botao(fil, "+ Novo", tipo="primario", command=self._novo).pack(side="right")
        botao(fil, "✏ Editar", tipo="secundario",
              command=self._editar).pack(side="right", padx=(0, 6))

        self._tab = Tabela(self, colunas=[
            ("ID", 40), ("Código", 65), ("Regime", 120), ("Descrição", 380),
        ])
        self._tab.pack(fill="both", expand=True)
        self._tab.ao_duplo_clique = lambda _: self._editar()

    def _carregar(self):
        r_raw = self._var_regime.get()
        regime = r_raw[0] if r_raw else None
        self._dados = FiscalConfig.listar_cst_icms(regime=regime,
                                                    busca=self._var_busca.get())
        self._tab.limpar()
        for r in self._dados:
            self._tab.inserir([r["id"], r["codigo"],
                               "Simples" if r.get("regime") == "S" else "Normal",
                               r["descricao"]])

    def _novo(self):    FormCSTICMS(self, ao_salvar=self._carregar)
    def _editar(self):
        idx = self._tab.selecionado_indice()
        if idx is None: return
        FormCSTICMS(self, dados=self._dados[idx], ao_salvar=self._carregar)


class FormCSTICMS(tk.Toplevel):
    def __init__(self, master, dados=None, ao_salvar=None):
        super().__init__(master)
        self.title("CST ICMS")
        self.configure(bg=THEME["bg"])
        self.resizable(False, False)
        self.grab_set()
        self._dados = dados; self._ao_salvar = ao_salvar; self._build()
        if dados: self._preencher()

    def _build(self):
        P = 16
        tk.Label(self, text="CST / CSOSN ICMS", font=FONT["title"],
                 bg=THEME["bg"], fg=THEME["fg"]).pack(anchor="w", padx=P, pady=(14, 8))
        c = tk.Frame(self, bg=THEME["bg_card"], highlightthickness=1,
                     highlightbackground=THEME["border"])
        c.pack(fill="x", padx=P)
        ci = tk.Frame(c, bg=THEME["bg_card"], padx=12, pady=10)
        ci.pack(fill="x")
        self._var_cod  = tk.StringVar()
        self._var_desc = tk.StringVar()
        self._var_reg  = tk.StringVar(value="N")
        CampoEntry(ci, "Código *", self._var_cod).pack(fill="x", pady=(0, 6))
        CampoEntry(ci, "Descrição *", self._var_desc).pack(fill="x", pady=(0, 6))
        tk.Label(ci, text="Regime", font=FONT["sm"],
                 bg=THEME["bg_card"], fg=THEME["fg"]).pack(anchor="w")
        ttk.Combobox(ci, textvariable=self._var_reg, state="readonly",
                     values=["N — Regime Normal","S — Simples Nacional"],
                     font=FONT["md"]).pack(fill="x", ipady=4)
        self._var_err = tk.StringVar()
        tk.Label(self, textvariable=self._var_err, font=FONT["sm"],
                 bg=THEME["bg"], fg=THEME["danger"]).pack(anchor="w", padx=P, pady=(6, 0))
        botao(self, "💾 Salvar", tipo="sucesso",
              command=self._salvar).pack(fill="x", padx=P, pady=(6, 16))

    def _preencher(self):
        self._var_cod.set(self._dados.get("codigo",""))
        self._var_desc.set(self._dados.get("descricao",""))
        r = self._dados.get("regime","N")
        self._var_reg.set("N — Regime Normal" if r == "N" else "S — Simples Nacional")

    def _salvar(self):
        cod = self._var_cod.get().strip()
        desc= self._var_desc.get().strip()
        if not cod or not desc:
            self._var_err.set("Preencha código e descrição."); return
        r_raw = self._var_reg.get()
        dados = {"codigo": cod, "descricao": desc, "regime": r_raw[0] if r_raw else "N", "ativo": 1}
        try:
            FiscalConfig.salvar_cst_icms(dados, id_=self._dados["id"] if self._dados else None)
            if self._ao_salvar: self._ao_salvar()
            self.destroy()
        except Exception as e:
            self._var_err.set(str(e))


# ════════════════════════════════════════════════════════════════
# Aba CST PIS/COFINS (leitura — seeds já vêm da migration)
# ════════════════════════════════════════════════════════════════
class AbaCST_PIS(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg=THEME["bg"])
        self.pack(fill="both", expand=True, padx=8, pady=8)
        self._tab = Tabela(self, colunas=[("Código", 65), ("Descrição", 450)])
        self._tab.pack(fill="both", expand=True)
        self._carregar()

    def _carregar(self):
        self._tab.limpar()
        for r in FiscalConfig.listar_cst_pis_cofins():
            self._tab.inserir([r["codigo"], r["descricao"]])


# ════════════════════════════════════════════════════════════════
# Aba Alíquotas ICMS
# ════════════════════════════════════════════════════════════════
class AbaAliqICMS(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg=THEME["bg"])
        self.pack(fill="both", expand=True, padx=8, pady=8)
        self._build(); self._carregar()

    def _build(self):
        fil = tk.Frame(self, bg=THEME["bg"])
        fil.pack(fill="x", pady=(0, 6))
        self._var_busca = tk.StringVar()
        tk.Label(fil, text="Filtrar UF:", font=FONT["sm"],
                 bg=THEME["bg"], fg=THEME["fg"]).pack(side="left")
        tk.Entry(fil, textvariable=self._var_busca, width=10,
                 font=FONT["md"], relief="flat", bg="white",
                 highlightthickness=1, highlightbackground=THEME["border"]
                 ).pack(side="left", ipady=4, padx=(4, 12))
        botao(fil, "🔍", tipo="secundario", command=self._carregar).pack(side="left")
        botao(fil, "+ Nova Alíquota", tipo="primario",
              command=self._nova).pack(side="right")
        botao(fil, "✏ Editar", tipo="secundario",
              command=self._editar).pack(side="right", padx=(0, 6))

        self._tab = Tabela(self, colunas=[
            ("ID", 40), ("UF Origem", 90), ("UF Destino", 90),
            ("Alíquota %", 100), ("Vigência", 100),
        ])
        self._tab.pack(fill="both", expand=True)
        self._tab.ao_duplo_clique = lambda _: self._editar()

    def _carregar(self):
        self._dados = FiscalConfig.listar_aliq_icms(busca=self._var_busca.get())
        self._tab.limpar()
        for r in self._dados:
            self._tab.inserir([
                r["id"], r["uf_origem"], r["uf_destino"],
                f"{r['aliquota']:.2f}%", r.get("vigencia") or "—",
            ])

    def _nova(self):   FormAliqICMS(self, ao_salvar=self._carregar)
    def _editar(self):
        idx = self._tab.selecionado_indice()
        if idx is None: return
        FormAliqICMS(self, dados=self._dados[idx], ao_salvar=self._carregar)


class FormAliqICMS(tk.Toplevel):
    def __init__(self, master, dados=None, ao_salvar=None):
        super().__init__(master)
        self.title("Alíquota ICMS")
        self.configure(bg=THEME["bg"])
        self.resizable(False, False)
        self.grab_set()
        self._dados = dados; self._ao_salvar = ao_salvar; self._build()
        if dados: self._preencher()

    def _build(self):
        P = 16
        tk.Label(self, text="Alíquota ICMS por UF", font=FONT["title"],
                 bg=THEME["bg"], fg=THEME["fg"]).pack(anchor="w", padx=P, pady=(14, 8))
        c = tk.Frame(self, bg=THEME["bg_card"], highlightthickness=1,
                     highlightbackground=THEME["border"])
        c.pack(fill="x", padx=P)
        ci = tk.Frame(c, bg=THEME["bg_card"], padx=12, pady=10)
        ci.pack(fill="x")
        self._var_uo   = tk.StringVar()
        self._var_ud   = tk.StringVar()
        self._var_aliq = tk.StringVar()
        row = tk.Frame(ci, bg=THEME["bg_card"])
        row.pack(fill="x", pady=(0, 6))
        CampoEntry(row, "UF Origem *", self._var_uo).pack(
            side="left", fill="x", expand=True, padx=(0, 6))
        CampoEntry(row, "UF Destino *", self._var_ud).pack(
            side="left", fill="x", expand=True)
        CampoEntry(ci, "Alíquota % *", self._var_aliq).pack(fill="x", pady=(0, 6))
        self._var_err = tk.StringVar()
        tk.Label(self, textvariable=self._var_err, font=FONT["sm"],
                 bg=THEME["bg"], fg=THEME["danger"]).pack(anchor="w", padx=P, pady=(6, 0))
        botao(self, "💾 Salvar", tipo="sucesso",
              command=self._salvar).pack(fill="x", padx=P, pady=(6, 16))

    def _preencher(self):
        self._var_uo.set(self._dados.get("uf_origem",""))
        self._var_ud.set(self._dados.get("uf_destino",""))
        self._var_aliq.set(str(self._dados.get("aliquota",0)))

    def _salvar(self):
        uo = self._var_uo.get().strip().upper()
        ud = self._var_ud.get().strip().upper()
        if not uo or not ud:
            self._var_err.set("UF origem e destino obrigatórios."); return
        try:
            aliq = float(self._var_aliq.get().replace(",","."))
            FiscalConfig.salvar_aliq_icms(uo, ud, aliq,
                id_=self._dados["id"] if self._dados else None)
            if self._ao_salvar: self._ao_salvar()
            self.destroy()
        except Exception as e:
            self._var_err.set(str(e))


# ════════════════════════════════════════════════════════════════
# Aba Regras Fiscais
# ════════════════════════════════════════════════════════════════
class AbaRegras(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg=THEME["bg"])
        self.pack(fill="both", expand=True, padx=8, pady=8)
        self._build(); self._carregar()

    def _build(self):
        fil = tk.Frame(self, bg=THEME["bg"])
        fil.pack(fill="x", pady=(0, 6))
        self._var_tipo = tk.StringVar(value="")
        tk.Label(fil, text="Tipo:", font=FONT["sm"],
                 bg=THEME["bg"], fg=THEME["fg"]).pack(side="left")
        ttk.Combobox(fil, textvariable=self._var_tipo, width=16,
                     values=["","ENTRADA","SAIDA","DEV_COMPRA","DEV_VENDA"],
                     state="readonly", font=FONT["sm"]
                     ).pack(side="left", padx=(4, 12))
        botao(fil, "🔍 Filtrar", tipo="secundario",
              command=self._carregar).pack(side="left")
        botao(fil, "+ Nova Regra", tipo="primario",
              command=self._nova).pack(side="right")
        botao(fil, "✏ Editar", tipo="secundario",
              command=self._editar).pack(side="right", padx=(0, 6))
        botao(fil, "🗑 Excluir", tipo="perigo",
              command=self._excluir).pack(side="right", padx=(0, 6))

        self._tab = Tabela(self, colunas=[
            ("ID", 36), ("Nome", 160), ("Tipo", 80), ("Sit.", 55),
            ("CFOP", 65), ("CST ICMS", 80), ("Alíq.ICMS", 80),
            ("CST PIS", 65), ("Alíq.PIS", 70),
            ("CST COF", 65), ("Alíq.COF", 70), ("Ativo", 45),
        ])
        self._tab.pack(fill="both", expand=True)
        self._tab.ao_duplo_clique = lambda _: self._editar()

    def _carregar(self):
        self._dados = FiscalConfig.listar_regras(tipo_op=self._var_tipo.get() or None)
        self._tab.limpar()
        for r in self._dados:
            self._tab.inserir([
                r["id"], r["nome"], r["tipo_op"],
                r.get("situacao","A"),
                r.get("cfop_codigo") or "—",
                r.get("cst_icms_codigo") or "—",
                f"{r.get('aliq_icms',0):.2f}%",
                r.get("cst_pis_cod") or "—",
                f"{r.get('aliq_pis',0):.2f}%",
                r.get("cst_cofins_cod") or "—",
                f"{r.get('aliq_cofins',0):.2f}%",
                "✅" if r.get("ativo") else "❌",
            ])

    def _nova(self):   FormRegra(self, ao_salvar=self._carregar)
    def _editar(self):
        idx = self._tab.selecionado_indice()
        if idx is None: return
        FormRegra(self, dados=self._dados[idx], ao_salvar=self._carregar)
    def _excluir(self):
        idx = self._tab.selecionado_indice()
        if idx is None: return
        if messagebox.askyesno("Excluir", "Excluir esta regra?", parent=self):
            FiscalConfig.excluir_regra(self._dados[idx]["id"])
            self._carregar()


class FormRegra(tk.Toplevel):
    def __init__(self, master, dados=None, ao_salvar=None):
        super().__init__(master)
        self.title("Regra Fiscal")
        self.configure(bg=THEME["bg"])
        self.resizable(True, True)
        self.geometry("560x640")
        self.grab_set()
        self._dados = dados; self._ao_salvar = ao_salvar
        self._cfops_list = FiscalConfig.listar_cfop()
        self._cst_list   = FiscalConfig.listar_cst_icms()
        self._build()
        if dados: self._preencher()

    def _build(self):
        canvas = tk.Canvas(self, bg=THEME["bg"], highlightthickness=0)
        vsb = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True)
        body = tk.Frame(canvas, bg=THEME["bg"])
        win  = canvas.create_window((0,0), window=body, anchor="nw")
        body.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(win, width=e.width))
        P = 14

        tk.Label(body, text="Regra Fiscal", font=FONT["title"],
                 bg=THEME["bg"], fg=THEME["fg"]).pack(anchor="w", padx=P, pady=(12,6))

        def campo(parent, label, var, vals=None, readonly=False):
            f = tk.Frame(parent, bg=THEME["bg_card"])
            f.pack(fill="x", pady=(0, 6))
            tk.Label(f, text=label, font=FONT["sm"],
                     bg=THEME["bg_card"], fg=THEME["fg"]).pack(anchor="w", pady=(0, 2))
            if vals is not None:
                cb = ttk.Combobox(f, textvariable=var, values=vals,
                                  state="readonly" if readonly else "normal",
                                  font=FONT["md"])
                cb.pack(fill="x", ipady=4)
            else:
                tk.Entry(f, textvariable=var, font=FONT["md"], relief="flat",
                         bg=THEME["bg"], fg=THEME["fg"],
                         highlightthickness=1,
                         highlightbackground=THEME["border"],
                         highlightcolor=THEME["primary"]
                         ).pack(fill="x", ipady=5)

        c = tk.Frame(body, bg=THEME["bg_card"], highlightthickness=1,
                     highlightbackground=THEME["border"])
        c.pack(fill="x", padx=P, pady=(0,8))
        ci = tk.Frame(c, bg=THEME["bg_card"], padx=12, pady=10)
        ci.pack(fill="x")

        self._var_nome = tk.StringVar()
        self._var_tipo = tk.StringVar(value="ENTRADA")
        self._var_sit  = tk.StringVar(value="A — Intraestadual")
        self._var_cfop = tk.StringVar()
        self._var_cst  = tk.StringVar()
        self._var_aicms= tk.StringVar(value="0.00")
        self._var_cpis = tk.StringVar(value="07")
        self._var_apis = tk.StringVar(value="0.65")
        self._var_ccof = tk.StringVar(value="07")
        self._var_acof = tk.StringVar(value="3.00")
        self._var_aipi = tk.StringVar(value="0.00")
        self._var_ativo= tk.BooleanVar(value=True)
        self._var_obs  = tk.StringVar()

        campo(ci, "Nome da Regra *", self._var_nome)
        row_tc = tk.Frame(ci, bg=THEME["bg_card"])
        row_tc.pack(fill="x", pady=(0,6))
        for lbl, var, vals in [
            ("Tipo Operação", self._var_tipo, ["ENTRADA","SAIDA","DEV_COMPRA","DEV_VENDA"]),
            ("Situação",      self._var_sit,  ["A — Intraestadual","B — Interestadual","C — Exterior"]),
        ]:
            col = tk.Frame(row_tc, bg=THEME["bg_card"])
            col.pack(side="left", fill="x", expand=True, padx=(0,6))
            tk.Label(col, text=lbl, font=FONT["sm"], bg=THEME["bg_card"], fg=THEME["fg"]).pack(anchor="w")
            ttk.Combobox(col, textvariable=var, values=vals,
                         state="readonly", font=FONT["md"]).pack(fill="x", ipady=4)

        # CFOP
        tk.Label(ci, text="CFOP Padrão", font=FONT["sm"],
                 bg=THEME["bg_card"], fg=THEME["fg"]).pack(anchor="w", pady=(6,2))
        cfop_vals = [f"{c['codigo']} — {c['descricao'][:50]}" for c in self._cfops_list]
        ttk.Combobox(ci, textvariable=self._var_cfop, values=cfop_vals,
                     state="normal", font=FONT["md"]).pack(fill="x", ipady=4, pady=(0,6))

        # CST ICMS
        tk.Label(ci, text="CST/CSOSN ICMS Padrão", font=FONT["sm"],
                 bg=THEME["bg_card"], fg=THEME["fg"]).pack(anchor="w", pady=(0,2))
        cst_vals = [f"{c['codigo']} — {c['descricao'][:50]}" for c in self._cst_list]
        ttk.Combobox(ci, textvariable=self._var_cst, values=cst_vals,
                     state="normal", font=FONT["md"]).pack(fill="x", ipady=4, pady=(0,6))

        row_aliq = tk.Frame(ci, bg=THEME["bg_card"])
        row_aliq.pack(fill="x", pady=(0,6))
        for lbl, var in [
            ("Alíq. ICMS %", self._var_aicms),
            ("Alíq. PIS %",  self._var_apis),
            ("Alíq. COF %",  self._var_acof),
            ("Alíq. IPI %",  self._var_aipi),
        ]:
            col = tk.Frame(row_aliq, bg=THEME["bg_card"])
            col.pack(side="left", fill="x", expand=True, padx=(0,4))
            CampoEntry(col, lbl, var, justify="right").pack(fill="x")

        row_pisc = tk.Frame(ci, bg=THEME["bg_card"])
        row_pisc.pack(fill="x", pady=(0,6))
        CampoEntry(row_pisc, "CST PIS", self._var_cpis).pack(
            side="left", fill="x", expand=True, padx=(0,4))
        CampoEntry(row_pisc, "CST COFINS", self._var_ccof).pack(
            side="left", fill="x", expand=True)

        campo(ci, "Observação", self._var_obs)
        tk.Checkbutton(ci, text="Ativa", variable=self._var_ativo,
                       bg=THEME["bg_card"], font=FONT["sm"],
                       activebackground=THEME["bg_card"]).pack(anchor="w")

        self._var_err = tk.StringVar()
        tk.Label(body, textvariable=self._var_err, font=FONT["sm"],
                 bg=THEME["bg"], fg=THEME["danger"]).pack(anchor="w", padx=P, pady=(4,0))
        botao(body, "💾 Salvar Regra", tipo="sucesso",
              command=self._salvar).pack(fill="x", padx=P, pady=(6,16))

    def _preencher(self):
        d = self._dados
        self._var_nome.set(d.get("nome",""))
        self._var_tipo.set(d.get("tipo_op","ENTRADA"))
        s = d.get("situacao","A")
        mapa = {"A":"A — Intraestadual","B":"B — Interestadual","C":"C — Exterior"}
        self._var_sit.set(mapa.get(s, s))
        if d.get("cfop_codigo"):
            self._var_cfop.set(
                next((f"{c['codigo']} — {c['descricao'][:50]}"
                      for c in self._cfops_list if c["codigo"]==d["cfop_codigo"]), ""))
        if d.get("cst_icms_codigo"):
            self._var_cst.set(
                next((f"{c['codigo']} — {c['descricao'][:50]}"
                      for c in self._cst_list if c["codigo"]==d["cst_icms_codigo"]), ""))
        self._var_aicms.set(str(d.get("aliq_icms",0)))
        self._var_cpis.set(d.get("cst_pis_cod","07"))
        self._var_apis.set(str(d.get("aliq_pis",0)))
        self._var_ccof.set(d.get("cst_cofins_cod","07"))
        self._var_acof.set(str(d.get("aliq_cofins",0)))
        self._var_aipi.set(str(d.get("aliq_ipi",0)))
        self._var_obs.set(d.get("obs") or "")
        self._var_ativo.set(bool(d.get("ativo",1)))

    def _salvar(self):
        nome = self._var_nome.get().strip()
        if not nome:
            self._var_err.set("Nome é obrigatório."); return
        # Resolve CFOP id
        cfop_txt = self._var_cfop.get()
        cfop_cod = cfop_txt.split(" — ")[0].strip() if cfop_txt else ""
        cfop_id  = next((c["id"] for c in self._cfops_list if c["codigo"]==cfop_cod), None)
        # Resolve CST id
        cst_txt = self._var_cst.get()
        cst_cod = cst_txt.split(" — ")[0].strip() if cst_txt else ""
        cst_id  = next((c["id"] for c in self._cst_list if c["codigo"]==cst_cod), None)
        sit_raw = self._var_sit.get()
        dados = {
            "nome":          nome,
            "tipo_op":       self._var_tipo.get(),
            "situacao":      sit_raw[0] if sit_raw else "A",
            "cfop_id":       cfop_id,
            "cst_icms_id":   cst_id,
            "cst_pis_cod":   self._var_cpis.get().strip() or None,
            "cst_cofins_cod":self._var_ccof.get().strip() or None,
            "aliq_icms":     _s2f(self._var_aicms.get()),
            "aliq_pis":      _s2f(self._var_apis.get()),
            "aliq_cofins":   _s2f(self._var_acof.get()),
            "aliq_ipi":      _s2f(self._var_aipi.get()),
            "ativo":         int(self._var_ativo.get()),
            "obs":           self._var_obs.get().strip() or None,
        }
        try:
            FiscalConfig.salvar_regra(dados,
                id_=self._dados["id"] if self._dados else None)
            if self._ao_salvar: self._ao_salvar()
            self.destroy()
        except Exception as e:
            self._var_err.set(str(e))


# ════════════════════════════════════════════════════════════════
# Aba Fechamentos Fiscais
# ════════════════════════════════════════════════════════════════
class AbaFechamentos(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg=THEME["bg"])
        self.pack(fill="both", expand=True, padx=8, pady=8)
        self._build()
        self._carregar()

    def _build(self):
        # Painel de ação
        topo = tk.Frame(self, bg=THEME["bg"])
        topo.pack(fill="x", pady=(0, 8))

        # Aviso importante
        av = tk.Frame(topo, bg="#fff3cd", highlightthickness=1,
                      highlightbackground="#ffc107")
        av.pack(fill="x", pady=(0, 8))
        ai = tk.Frame(av, bg="#fff3cd", padx=12, pady=8)
        ai.pack(fill="x")
        tk.Label(ai, text="⚠  ATENÇÃO — Operação crítica",
                 font=FONT["bold"], bg="#fff3cd", fg="#856404").pack(anchor="w")
        tk.Label(ai,
                 text="Fechar um período impede lançamentos, edições, exclusões e estornos "
                      "em notas fiscais, estoque, produtos e vendas nessa competência.\n"
                      "A reabertura exige justificativa e fica registrada em auditoria.",
                 font=FONT["sm"], bg="#fff3cd", fg="#533f03",
                 justify="left", wraplength=700).pack(anchor="w")

        # Seleção de competência
        sel = tk.Frame(topo, bg=THEME["bg"])
        sel.pack(fill="x")
        tk.Label(sel, text="Competência:", font=FONT["sm"],
                 bg=THEME["bg"], fg=THEME["fg"]).pack(side="left")
        self._var_ano = tk.StringVar(value=str(datetime.date.today().year))
        self._var_mes = tk.StringVar(value=f"{datetime.date.today().month:02d}")
        meses = [f"{i:02d} — {n}" for i, n in enumerate(
            ["","Jan","Fev","Mar","Abr","Mai","Jun",
             "Jul","Ago","Set","Out","Nov","Dez"], 0) if i > 0]
        ttk.Combobox(sel, textvariable=self._var_mes, values=meses,
                     width=12, state="readonly", font=FONT["md"]
                     ).pack(side="left", padx=(6, 4), ipady=4)
        tk.Entry(sel, textvariable=self._var_ano, width=6, font=FONT["md"],
                 relief="flat", bg="white",
                 highlightthickness=1, highlightbackground=THEME["border"]
                 ).pack(side="left", ipady=5, padx=(0, 12))

        botao(sel, "🔒 Fechar Competência", tipo="perigo",
              command=self._fechar).pack(side="left", padx=(0, 6))
        botao(sel, "🔓 Reabrir", tipo="secundario",
              command=self._reabrir).pack(side="left")
        botao(sel, "🔄 Atualizar", tipo="secundario",
              command=self._carregar).pack(side="right")

        # Tabela de histórico
        SecaoForm(self, "HISTÓRICO DE COMPETÊNCIAS").pack(fill="x", pady=(8, 4))
        self._tab = Tabela(self, colunas=[
            ("Competência", 100), ("Status", 90),
            ("Fechado em", 130), ("Fechado por", 130),
            ("Reaberto em", 130), ("Reaberto por", 130),
            ("Obs.", 200),
        ])
        self._tab.pack(fill="both", expand=True)

    def _carregar(self):
        ano = int(self._var_ano.get() or datetime.date.today().year)
        rows = FiscalConfig.listar_fechamentos(ano=ano)
        self._dados = rows
        self._tab.limpar()
        for r in rows:
            status_lbl = "🔒 FECHADO" if r["status"] == "FECHADO" else "🟢 ABERTO"
            self._tab.inserir([
                r["competencia"], status_lbl,
                r.get("fechado_em") or "—",
                r.get("fechado_por") or "—",
                r.get("reaberto_em") or "—",
                r.get("reaberto_por") or "—",
                r.get("obs") or "—",
            ])

    def _fechar(self):
        mes_raw = self._var_mes.get()
        mes = int(mes_raw.split(" — ")[0]) if mes_raw else 0
        ano = int(self._var_ano.get() or 0)
        if not mes or not ano:
            messagebox.showwarning("Atenção", "Selecione mês e ano.", parent=self); return

        comp = f"{ano:04d}-{mes:02d}"
        conf = messagebox.askyesno(
            "⚠ Confirmar Fechamento",
            f"Fechar a competência {mes:02d}/{ano}?\n\n"
            "Isso bloqueará TODOS os lançamentos, edições e exclusões "
            "em notas fiscais, estoque, produtos e vendas nesse período.\n\n"
            "Esta operação deve ser realizada apenas após conferência completa.",
            parent=self
        )
        if not conf: return

        obs = simpledialog.askstring(
            "Justificativa",
            f"Informe o motivo do fechamento de {mes:02d}/{ano}:",
            parent=self
        )
        if obs is None: return  # cancelou

        FiscalConfig.fechar(ano, mes,
                            usuario=Session.nome(),
                            obs=obs.strip())
        messagebox.showinfo("Fechado",
            f"Competência {mes:02d}/{ano} fechada com sucesso.", parent=self)
        self._carregar()

    def _reabrir(self):
        idx = self._tab.selecionado_indice()
        if idx is None:
            # Tenta usar a competência selecionada nos campos
            mes_raw = self._var_mes.get()
            mes = int(mes_raw.split(" — ")[0]) if mes_raw else 0
            ano = int(self._var_ano.get() or 0)
            comp = f"{ano:04d}-{mes:02d}" if mes and ano else None
        else:
            comp = self._dados[idx]["competencia"]
            partes = comp.split("-")
            ano, mes = int(partes[0]), int(partes[1])

        if not comp:
            messagebox.showwarning("Atenção", "Selecione uma competência.", parent=self); return

        if not FiscalConfig.competencia_fechada(ano, mes):
            messagebox.showinfo("Aviso",
                f"A competência {mes:02d}/{ano} já está aberta.", parent=self); return

        motivo = simpledialog.askstring(
            "Justificativa de Reabertura",
            f"Informe o motivo da reabertura de {mes:02d}/{ano} (obrigatório):",
            parent=self
        )
        if not motivo or not motivo.strip():
            messagebox.showwarning("Cancelado", "Reabertura cancelada.", parent=self); return

        if not messagebox.askyesno("Confirmar Reabertura",
            f"Reabrir {mes:02d}/{ano}? Esta ação ficará registrada em auditoria.",
            parent=self): return

        FiscalConfig.reabrir(ano, mes, Session.nome(), motivo.strip())
        messagebox.showinfo("Reaberto",
            f"Competência {mes:02d}/{ano} reaberta.", parent=self)
        self._carregar()