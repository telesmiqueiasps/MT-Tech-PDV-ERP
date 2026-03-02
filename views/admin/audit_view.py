"""
AuditView — Painel de Auditoria completo (admin global apenas).
Abas: Log em Tempo Real | Filtros Avançados | Estatísticas | Licença
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import datetime
import json
from config import THEME, FONT
from views.widgets.widgets import SecaoForm, CampoEntry, botao
from views.widgets.tabela import Tabela
from views.widgets.date_entry import DateEntry
from core.audit import Audit


NIVEL_COR = {
    "INFO":     "#1a7a3a",
    "WARN":     "#aa6600",
    "ERROR":    "#cc2200",
    "CRITICAL": "#7b0000",
}

ACOES_DISPONIVEIS = [
    "", "LOGIN", "LOGIN_FALHA", "LOGOUT", "ACESSO_NEGADO",
    "INSERT", "UPDATE", "DELETE",
    "AUTORIZAR", "ESTORNAR", "CANCELAR",
    "FECHAR_PERIODO", "REABRIR_PERIODO",
    "ATIVACAO_OK", "ATIVACAO_FALHA", "CHECK_OK", "CHECK_FAIL",
    "TRIAL_CRIADO", "LICENCA_BLOQUEADA",
]

MODULOS_DISPONIVEIS = [
    "", "auth", "produtos", "clientes", "fornecedores",
    "estoque", "fiscal", "pdv", "relatorios", "licenca",
]


class AuditView(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg=THEME["bg"])
        self.pack(fill="both", expand=True)
        self._build()

    def _build(self):
        # Cabeçalho
        hdr = tk.Frame(self, bg=THEME["primary"], padx=20, pady=14)
        hdr.pack(fill="x")
        tk.Label(hdr, text="🔍  Auditoria do Sistema",
                 font=FONT["title"], bg=THEME["primary"], fg="white").pack(side="left")
        tk.Label(hdr, text="Admin Global — somente leitura",
                 font=FONT["sm"], bg=THEME["primary"], fg="#cce").pack(side="right")

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=12, pady=8)

        for label, Cls in [
            ("📋 Log de Eventos",   AbaLog),
            ("📊 Estatísticas",     AbaEstatisticas),
            ("🔑 Licença",          AbaLicenca),
        ]:
            f = tk.Frame(nb, bg=THEME["bg"])
            nb.add(f, text=label)
            Cls(f)


# ════════════════════════════════════════════════════════════════
# Aba Log de Eventos — filtros + tabela
# ════════════════════════════════════════════════════════════════
class AbaLog(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg=THEME["bg"])
        self.pack(fill="both", expand=True)
        self._dados = []
        self._build()
        self._buscar()

    def _build(self):
        # ── Painel de filtros ─────────────────────────────────
        fil = tk.Frame(self, bg=THEME["bg_card"],
                       highlightthickness=1, highlightbackground=THEME["border"],
                       padx=12, pady=10)
        fil.pack(fill="x", padx=8, pady=(8, 4))

        # Linha 1: período + texto + nível
        l1 = tk.Frame(fil, bg=THEME["bg_card"])
        l1.pack(fill="x", pady=(0, 6))

        tk.Label(l1, text="De:", font=FONT["sm"],
                 bg=THEME["bg_card"], fg=THEME["fg"]).pack(side="left")
        self._de_de = DateEntry(l1)
        self._de_de.pack(side="left", padx=(4, 12))
        # Padrão: últimos 7 dias
        self._de_de.set(
            (datetime.date.today() - datetime.timedelta(days=7)).isoformat())

        tk.Label(l1, text="Até:", font=FONT["sm"],
                 bg=THEME["bg_card"], fg=THEME["fg"]).pack(side="left")
        self._de_ate = DateEntry(l1)
        self._de_ate.pack(side="left", padx=(4, 12))
        self._de_ate.set(datetime.date.today().isoformat())

        tk.Label(l1, text="Texto:", font=FONT["sm"],
                 bg=THEME["bg_card"], fg=THEME["fg"]).pack(side="left")
        self._var_texto = tk.StringVar()
        tk.Entry(l1, textvariable=self._var_texto, font=FONT["md"],
                 relief="flat", bg="white", width=20,
                 highlightthickness=1, highlightbackground=THEME["border"]
                 ).pack(side="left", ipady=4, padx=(4, 12))

        tk.Label(l1, text="Nível:", font=FONT["sm"],
                 bg=THEME["bg_card"], fg=THEME["fg"]).pack(side="left")
        self._var_nivel = tk.StringVar()
        ttk.Combobox(l1, textvariable=self._var_nivel, width=10,
                     values=["", "INFO", "WARN", "ERROR", "CRITICAL"],
                     state="readonly", font=FONT["sm"]
                     ).pack(side="left", padx=(4, 12))

        # Linha 2: ação + módulo + usuário + limite
        l2 = tk.Frame(fil, bg=THEME["bg_card"])
        l2.pack(fill="x")

        tk.Label(l2, text="Ação:", font=FONT["sm"],
                 bg=THEME["bg_card"], fg=THEME["fg"]).pack(side="left")
        self._var_acao = tk.StringVar()
        ttk.Combobox(l2, textvariable=self._var_acao, width=18,
                     values=ACOES_DISPONIVEIS, state="readonly", font=FONT["sm"]
                     ).pack(side="left", padx=(4, 12))

        tk.Label(l2, text="Módulo:", font=FONT["sm"],
                 bg=THEME["bg_card"], fg=THEME["fg"]).pack(side="left")
        self._var_modulo = tk.StringVar()
        ttk.Combobox(l2, textvariable=self._var_modulo, width=14,
                     values=MODULOS_DISPONIVEIS, state="readonly", font=FONT["sm"]
                     ).pack(side="left", padx=(4, 12))

        tk.Label(l2, text="Usuário:", font=FONT["sm"],
                 bg=THEME["bg_card"], fg=THEME["fg"]).pack(side="left")
        self._var_usuario = tk.StringVar()
        tk.Entry(l2, textvariable=self._var_usuario, font=FONT["md"],
                 relief="flat", bg="white", width=14,
                 highlightthickness=1, highlightbackground=THEME["border"]
                 ).pack(side="left", ipady=4, padx=(4, 12))

        tk.Label(l2, text="Limite:", font=FONT["sm"],
                 bg=THEME["bg_card"], fg=THEME["fg"]).pack(side="left")
        self._var_limite = tk.StringVar(value="500")
        ttk.Combobox(l2, textvariable=self._var_limite, width=6,
                     values=["100", "250", "500", "1000", "5000"],
                     state="readonly", font=FONT["sm"]
                     ).pack(side="left", padx=(4, 12))

        botao(l2, "🔍 Buscar", tipo="primario",
              command=self._buscar).pack(side="left")
        botao(l2, "🔄 Limpar", tipo="secundario",
              command=self._limpar_filtros).pack(side="left", padx=(6, 0))
        botao(l2, "📥 Exportar CSV", tipo="secundario",
              command=self._exportar).pack(side="right")

        # Contador
        self._lbl_total = tk.Label(fil, text="",
                                    font=FONT["sm"], bg=THEME["bg_card"],
                                    fg=THEME["fg_light"])
        self._lbl_total.pack(anchor="e")

        # ── Tabela ───────────────────────────────────────────
        self._tab = Tabela(self, colunas=[
            ("Data/Hora",    130),
            ("Nível",         55),
            ("Ação",          90),
            ("Módulo",        80),
            ("Tabela",        90),
            ("Reg. ID",       55),
            ("Usuário",       100),
            ("Empresa",       110),
            ("Detalhe",       250),
        ])
        self._tab.pack(fill="both", expand=True, padx=8, pady=(4, 8))
        self._tab.ao_duplo_clique = lambda _: self._ver_detalhe()

    def _buscar(self):
        self._dados = Audit.buscar(
            acao=self._var_acao.get() or None,
            modulo=self._var_modulo.get() or None,
            nivel=self._var_nivel.get() or None,
            usuario_nome=self._var_usuario.get().strip() or None,
            data_de=self._de_de.get() or None,
            data_ate=self._de_ate.get() or None,
            busca_texto=self._var_texto.get().strip() or None,
            limite=int(self._var_limite.get() or 500),
        )
        self._tab.limpar()
        for r in self._dados:
            self._tab.inserir([
                r.get("criado_em", "")[:19],
                r.get("nivel", "INFO"),
                r.get("acao", ""),
                r.get("modulo", "") or "—",
                r.get("tabela", "") or "—",
                r.get("registro_id", "") or "—",
                r.get("usuario_nome", "") or "—",
                r.get("empresa_nome", "") or "—",
                (r.get("detalhe", "") or "")[:80],
            ])
        total = len(self._dados)
        self._lbl_total.configure(
            text=f"{total} registro{'s' if total != 1 else ''} encontrado{'s' if total != 1 else ''}"
        )

    def _limpar_filtros(self):
        self._var_acao.set("")
        self._var_modulo.set("")
        self._var_nivel.set("")
        self._var_usuario.set("")
        self._var_texto.set("")
        self._var_limite.set("500")
        self._de_de.set(
            (datetime.date.today() - datetime.timedelta(days=7)).isoformat())
        self._de_ate.set(datetime.date.today().isoformat())
        self._buscar()

    def _ver_detalhe(self):
        idx = self._tab.selecionado_indice()
        if idx is None or idx >= len(self._dados):
            return
        r = self._dados[idx]
        DetalheAudit(self, r)

    def _exportar(self):
        if not self._dados:
            messagebox.showinfo("Sem dados",
                "Faça uma busca antes de exportar.", parent=self)
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv"), ("Todos", "*.*")],
            initialfile=f"auditoria_{datetime.date.today()}.csv",
            parent=self,
        )
        if not path:
            return
        import csv
        campos = ["criado_em","nivel","origem","acao","modulo","tabela",
                  "registro_id","usuario_nome","empresa_nome",
                  "dados_antes","dados_depois","detalhe"]
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=campos, extrasaction="ignore")
            w.writeheader()
            w.writerows(self._dados)
        messagebox.showinfo("Exportado",
            f"{len(self._dados)} registros exportados para:\n{path}", parent=self)


class DetalheAudit(tk.Toplevel):
    def __init__(self, master, registro: dict):
        super().__init__(master)
        self.title("Detalhe do Evento")
        self.configure(bg=THEME["bg"])
        self.geometry("640x500")
        self.grab_set()
        self._build(registro)

    def _build(self, r: dict):
        cor = NIVEL_COR.get(r.get("nivel", "INFO"), "#333")

        hdr = tk.Frame(self, bg=cor, padx=16, pady=10)
        hdr.pack(fill="x")
        tk.Label(hdr, text=f"{r.get('nivel','INFO')}  —  {r.get('acao','')}",
                 font=FONT["bold"], bg=cor, fg="white").pack(side="left")
        tk.Label(hdr, text=r.get("criado_em", "")[:19],
                 font=FONT["sm"], bg=cor, fg="white").pack(side="right")

        body = tk.Frame(self, bg=THEME["bg"])
        body.pack(fill="both", expand=True, padx=16, pady=12)

        def campo(label, valor):
            row = tk.Frame(body, bg=THEME["bg"])
            row.pack(fill="x", pady=2)
            tk.Label(row, text=f"{label}:", font=FONT["bold"],
                     bg=THEME["bg"], fg=THEME["fg"], width=14,
                     anchor="e").pack(side="left", padx=(0, 8))
            tk.Label(row, text=str(valor or "—"), font=FONT["md"],
                     bg=THEME["bg"], fg=THEME["fg"], anchor="w",
                     wraplength=400, justify="left").pack(side="left")

        campo("Módulo",   r.get("modulo"))
        campo("Tabela",   r.get("tabela"))
        campo("Reg. ID",  r.get("registro_id"))
        campo("Usuário",  r.get("usuario_nome"))
        campo("Empresa",  r.get("empresa_nome"))
        campo("Origem",   r.get("origem"))
        campo("IP",       r.get("ip"))
        campo("Detalhe",  r.get("detalhe"))

        # Dados antes/depois
        for label, key in [("Antes", "dados_antes"), ("Depois", "dados_depois")]:
            raw = r.get(key)
            if not raw:
                continue
            tk.Label(body, text=label, font=FONT["bold"],
                     bg=THEME["bg"], fg=THEME["fg"]).pack(anchor="w", pady=(8, 2))
            txt = tk.Text(body, height=5, font=("Consolas", 9),
                          relief="flat", bg="#f8f8f8", fg="#333",
                          highlightthickness=1,
                          highlightbackground=THEME["border"])
            txt.pack(fill="x")
            try:
                formatado = json.dumps(json.loads(raw), ensure_ascii=False, indent=2)
            except Exception:
                formatado = raw
            txt.insert("1.0", formatado)
            txt.configure(state="disabled")

        botao(self, "Fechar", tipo="secundario",
              command=self.destroy).pack(padx=16, pady=(8, 16))


# ════════════════════════════════════════════════════════════════
# Aba Estatísticas
# ════════════════════════════════════════════════════════════════
class AbaEstatisticas(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg=THEME["bg"])
        self.pack(fill="both", expand=True)
        self._build()
        self._atualizar()

    def _build(self):
        topo = tk.Frame(self, bg=THEME["bg"])
        topo.pack(fill="x", padx=12, pady=8)
        tk.Label(topo, text="Período:", font=FONT["sm"],
                 bg=THEME["bg"], fg=THEME["fg"]).pack(side="left")
        self._var_dias = tk.StringVar(value="30")
        ttk.Combobox(topo, textvariable=self._var_dias, width=8,
                     values=["7", "15", "30", "60", "90"],
                     state="readonly", font=FONT["sm"]
                     ).pack(side="left", padx=(4, 12))
        tk.Label(topo, text="dias", font=FONT["sm"],
                 bg=THEME["bg"], fg=THEME["fg"]).pack(side="left")
        botao(topo, "🔄 Atualizar", tipo="secundario",
              command=self._atualizar).pack(side="left", padx=12)

        # Cards de resumo
        self._frm_cards = tk.Frame(self, bg=THEME["bg"])
        self._frm_cards.pack(fill="x", padx=12, pady=(0, 8))

        # Tabelas lado a lado
        cols = tk.Frame(self, bg=THEME["bg"])
        cols.pack(fill="both", expand=True, padx=12)

        # Ações
        col_a = tk.Frame(cols, bg=THEME["bg"])
        col_a.pack(side="left", fill="both", expand=True, padx=(0, 8))
        SecaoForm(col_a, "TOP AÇÕES").pack(fill="x")
        self._tab_acoes = Tabela(col_a, colunas=[("Ação", 140), ("Qtd.", 60)])
        self._tab_acoes.pack(fill="both", expand=True)

        # Usuários
        col_u = tk.Frame(cols, bg=THEME["bg"])
        col_u.pack(side="left", fill="both", expand=True)
        SecaoForm(col_u, "TOP USUÁRIOS").pack(fill="x")
        self._tab_users = Tabela(col_u, colunas=[("Usuário", 140), ("Qtd.", 60)])
        self._tab_users.pack(fill="both", expand=True)

    def _atualizar(self):
        dias = int(self._var_dias.get() or 30)
        stats = Audit.estatisticas(dias=dias)

        # Limpar e recriar cards
        for w in self._frm_cards.winfo_children():
            w.destroy()

        for label, valor, cor in [
            ("Total de Eventos",   stats["total"],    THEME["primary"]),
            ("Alertas (WARN+)",    stats["alertas"],  "#cc2200"),
            ("Período (dias)",     stats["periodo_dias"], "#555"),
        ]:
            card = tk.Frame(self._frm_cards, bg="white",
                            highlightthickness=1,
                            highlightbackground=THEME["border"])
            card.pack(side="left", padx=(0, 8), ipadx=16, ipady=8)
            tk.Label(card, text=str(valor), font=("TkDefaultFont", 22, "bold"),
                     bg="white", fg=cor).pack()
            tk.Label(card, text=label, font=FONT["sm"],
                     bg="white", fg=THEME["fg_light"]).pack()

        # Preencher tabelas
        self._tab_acoes.limpar()
        for r in stats["por_acao"]:
            self._tab_acoes.inserir([r["acao"], r["n"]])

        self._tab_users.limpar()
        for r in stats["por_usuario"]:
            self._tab_users.inserir([r["usuario_nome"] or "—", r["n"]])


# ════════════════════════════════════════════════════════════════
# Aba Licença
# ════════════════════════════════════════════════════════════════
class AbaLicenca(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg=THEME["bg"])
        self.pack(fill="both", expand=True)
        self._build()
        self._atualizar()

    def _build(self):
        # Painel de status atual
        self._frm_status = tk.Frame(self, bg=THEME["bg_card"],
                                     highlightthickness=1,
                                     highlightbackground=THEME["border"])
        self._frm_status.pack(fill="x", padx=12, pady=12)
        fi = tk.Frame(self._frm_status, bg=THEME["bg_card"], padx=16, pady=12)
        fi.pack(fill="x")

        self._lbl_plano    = tk.Label(fi, text="", font=FONT["title"],
                                       bg=THEME["bg_card"], fg=THEME["primary"])
        self._lbl_plano.pack(anchor="w")
        self._lbl_status   = tk.Label(fi, text="", font=FONT["bold"],
                                       bg=THEME["bg_card"], fg="#555")
        self._lbl_status.pack(anchor="w")
        self._lbl_validade = tk.Label(fi, text="", font=FONT["sm"],
                                       bg=THEME["bg_card"], fg=THEME["fg_light"])
        self._lbl_validade.pack(anchor="w")
        self._lbl_modulos  = tk.Label(fi, text="", font=FONT["sm"],
                                       bg=THEME["bg_card"], fg=THEME["fg_light"],
                                       wraplength=500, justify="left")
        self._lbl_modulos.pack(anchor="w")
        self._lbl_fp       = tk.Label(fi, text="", font=("Consolas", 8),
                                       bg=THEME["bg_card"], fg=THEME["fg_light"])
        self._lbl_fp.pack(anchor="w", pady=(4, 0))

        # Seção de ativação
        SecaoForm(self, "ATIVAR / RENOVAR LICENÇA").pack(
            fill="x", padx=12, pady=(8, 4))
        ativ = tk.Frame(self, bg=THEME["bg_card"],
                        highlightthickness=1, highlightbackground=THEME["border"])
        ativ.pack(fill="x", padx=12)
        ai = tk.Frame(ativ, bg=THEME["bg_card"], padx=16, pady=12)
        ai.pack(fill="x")

        tk.Label(ai, text="Chave de Licença:", font=FONT["sm"],
                 bg=THEME["bg_card"], fg=THEME["fg"]).pack(anchor="w", pady=(0, 4))
        self._var_chave = tk.StringVar()
        tk.Entry(ai, textvariable=self._var_chave, font=("Consolas", 11),
                 relief="flat", bg="white", fg=THEME["fg"],
                 highlightthickness=1, highlightbackground=THEME["border"]
                 ).pack(fill="x", ipady=6, pady=(0, 8))

        self._var_msg_ativ = tk.StringVar()
        tk.Label(ai, textvariable=self._var_msg_ativ, font=FONT["sm"],
                 bg=THEME["bg_card"], fg=THEME["danger"],
                 wraplength=500).pack(anchor="w", pady=(0, 4))

        botao(ai, "🔑 Ativar Licença", tipo="sucesso",
              command=self._ativar).pack(anchor="w")

        # Gerador de chave (admin pode gerar para clientes)
        SecaoForm(self, "GERAR CHAVE PARA CLIENTE").pack(
            fill="x", padx=12, pady=(16, 4))
        gen = tk.Frame(self, bg=THEME["bg_card"],
                       highlightthickness=1, highlightbackground=THEME["border"])
        gen.pack(fill="x", padx=12)
        gi = tk.Frame(gen, bg=THEME["bg_card"], padx=16, pady=12)
        gi.pack(fill="x")

        row = tk.Frame(gi, bg=THEME["bg_card"])
        row.pack(fill="x", pady=(0, 8))

        from models.licenca import PLANOS
        tk.Label(row, text="Plano:", font=FONT["sm"],
                 bg=THEME["bg_card"], fg=THEME["fg"]).pack(side="left")
        self._var_plano_gen = tk.StringVar(value="BASICO")
        ttk.Combobox(row, textvariable=self._var_plano_gen, width=12,
                     values=list(PLANOS.keys()), state="readonly",
                     font=FONT["md"]).pack(side="left", padx=(4, 16))

        tk.Label(row, text="Validade (dias):", font=FONT["sm"],
                 bg=THEME["bg_card"], fg=THEME["fg"]).pack(side="left")
        self._var_val_gen = tk.StringVar(value="365")
        ttk.Combobox(row, textvariable=self._var_val_gen, width=8,
                     values=["30", "90", "180", "365", "730", ""],
                     state="readonly", font=FONT["md"]
                     ).pack(side="left", padx=(4, 16))

        tk.Label(row, text="(vazio = sem expiração)", font=FONT["sm"],
                 bg=THEME["bg_card"], fg=THEME["fg_light"]).pack(side="left")

        # CNPJ do cliente — vincula a licença à empresa
        row2 = tk.Frame(gi, bg=THEME["bg_card"])
        row2.pack(fill="x", pady=(0, 8))
        tk.Label(row2, text="CNPJ do cliente:", font=FONT["sm"],
                 bg=THEME["bg_card"], fg=THEME["fg"]).pack(side="left")
        self._var_cnpj_gen = tk.StringVar()
        tk.Entry(row2, textvariable=self._var_cnpj_gen, font=FONT["md"],
                 relief="flat", bg="white", width=20,
                 highlightthickness=1, highlightbackground=THEME["border"]
                 ).pack(side="left", ipady=4, padx=(4, 8))
        tk.Label(row2, text="(vincula licença ao CNPJ — recomendado)",
                 font=FONT["sm"], bg=THEME["bg_card"],
                 fg=THEME["fg_light"]).pack(side="left")

        tk.Label(row2, text="Máx. usuários:", font=FONT["sm"],
                 bg=THEME["bg_card"], fg=THEME["fg"]).pack(side="left", padx=(16,0))
        self._var_maxu_gen = tk.StringVar(value="3")
        ttk.Combobox(row2, textvariable=self._var_maxu_gen, width=5,
                     values=["1","2","3","5","10","20","0"],
                     state="readonly", font=FONT["md"]
                     ).pack(side="left", padx=(4, 4))
        tk.Label(row2, text="(0=ilimitado)", font=FONT["sm"],
                 bg=THEME["bg_card"], fg=THEME["fg_light"]).pack(side="left")

        self._txt_chave_gerada = tk.Text(gi, height=3, font=("Consolas", 10),
                                          relief="flat", bg="#f8f8f8",
                                          highlightthickness=1,
                                          highlightbackground=THEME["border"],
                                          state="disabled")
        self._txt_chave_gerada.pack(fill="x", pady=(0, 8))

        botao(gi, "⚙ Gerar Nova Chave", tipo="primario",
              command=self._gerar).pack(anchor="w")

    def _atualizar(self):
        from models.licenca import Licenca, PLANOS, LicencaStatus
        r = Licenca.resumo()

        plano_info = PLANOS.get(r["plano"], {})
        cor = plano_info.get("cor", THEME["primary"])

        self._lbl_plano.configure(
            text=f"Plano: {plano_info.get('nome', r['plano'])}", fg=cor)

        status_txt = {
            LicencaStatus.ATIVA:     "✅  ATIVA",
            LicencaStatus.TRIAL:     "🕐  TRIAL",
            LicencaStatus.GRACE:     "⚠️  GRACE PERIOD",
            LicencaStatus.EXPIRADA:  "❌  EXPIRADA",
            LicencaStatus.BLOQUEADA: "🚫  BLOQUEADA",
            LicencaStatus.INVALIDA:  "⛔  INVÁLIDA",
        }.get(r["status"], r["status"])
        self._lbl_status.configure(text=status_txt)

        val_txt = ""
        if r["validade"]:
            dias = r.get("dias_restantes")
            val_txt = f"Validade: {r['validade']}"
            if dias is not None:
                val_txt += f"  ({dias} dia{'s' if dias != 1 else ''} restante{'s' if dias != 1 else ''})"
        else:
            val_txt = "Validade: Sem expiração"
        self._lbl_validade.configure(text=val_txt)

        mods = r.get("modulos", [])
        self._lbl_modulos.configure(
            text="Módulos: " + (", ".join(mods) if mods != ["*"] else "Todos"))
        self._lbl_fp.configure(
            text=f"Fingerprint: {r.get('fingerprint', '')}  |  "
                 f"Usuários: {r['max_usuarios'] or '∞'}  |  "
                 f"Empresas: {r['max_empresas'] or '∞'}")

        if r.get("motivo"):
            self._var_msg_ativ.set(r["motivo"])

    def _ativar(self):
        chave = self._var_chave.get().strip()
        if not chave:
            self._var_msg_ativ.set("Digite a chave de licença.")
            return
        self._var_msg_ativ.set("Ativando... aguarde.")
        self.update()
        from models.licenca import Licenca
        sucesso, msg = Licenca.ativar(chave)
        self._var_msg_ativ.set(msg)
        if sucesso:
            self._atualizar()
            messagebox.showinfo("Licença Ativada", msg, parent=self)
        else:
            messagebox.showerror("Falha na Ativação", msg, parent=self)

    def _gerar(self):
        from models.licenca import Licenca
        plano    = self._var_plano_gen.get()
        val_raw  = self._var_val_gen.get().strip()
        dias     = int(val_raw) if val_raw else None
        cnpj     = self._var_cnpj_gen.get().strip()
        max_u    = int(self._var_maxu_gen.get() or 3)
        dados    = Licenca.gerar_chave(plano=plano, validade_dias=dias,
                                       cnpj_empresa=cnpj, max_usuarios=max_u)

        texto = (
            f"Chave:        {dados['chave']}\n"
            f"Plano:        {dados['plano']}\n"
            f"CNPJ cliente: {dados.get('cnpj_empresa') or 'não vinculado'}\n"
            f"Validade:     {dados.get('validade_ate') or 'Sem expiração'}\n"
            f"Máx. usuários:{dados['max_usuarios']}\n"
            f"Hash interno: {dados['chave_hash']}"
        )
        self._txt_chave_gerada.configure(state="normal")
        self._txt_chave_gerada.delete("1.0", "end")
        self._txt_chave_gerada.insert("1.0", texto)
        self._txt_chave_gerada.configure(state="disabled")

        # Copia a chave para o clipboard
        self.clipboard_clear()
        self.clipboard_append(dados["chave"])

        from core.audit import Audit
        Audit.licenca("CHAVE_GERADA",
                      f"Plano {plano}, validade {dias} dias")

        messagebox.showinfo(
            "Chave Gerada",
            f"Chave copiada para a área de transferência:\n\n"
            f"{dados['chave']}\n\n"
            "Envie esta chave ao cliente para ativação.",
            parent=self
        )