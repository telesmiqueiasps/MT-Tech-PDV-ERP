"""
AbaLicencas — painel de licenças dentro do AdminView (PDV, admin global).
Mostra todas as empresas com status da licença de cada uma.
Permite: ver detalhes, gerar chave, revogar, reativar.
"""
import tkinter as tk
from tkinter import ttk, messagebox
import datetime
import json
from config import THEME, FONT
from views.widgets.widgets import SecaoForm, CampoEntry, botao
from views.widgets.tabela import Tabela


STATUS_COR = {
    "ATIVA":     "#2dce89",
    "TRIAL":     "#4f8ef7",
    "GRACE":     "#f4b942",
    "PENDENTE":  "#f4b942",
    "EXPIRADA":  "#f5365c",
    "BLOQUEADA": "#f5365c",
    "INVALIDA":  "#888",
    "SEM_DADOS": "#888",
}

PLANOS = ["TRIAL", "BASICO", "PRO", "ENTERPRISE"]


class AbaLicencas(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg=THEME["bg"])
        self.pack(fill="both", expand=True)
        self._licencas: list[dict] = []  # dados do servidor
        self._build()
        self._carregar()

    def _build(self):
        # ── Toolbar ─────────────────────────────────────────
        topo = tk.Frame(self, bg=THEME["bg"], padx=16, pady=10)
        topo.pack(fill="x")

        botao(topo, "🔄 Atualizar", tipo="secundario",
              command=self._carregar).pack(side="left")
        botao(topo, "➕ Nova Licença", tipo="primario",
              command=self._nova_licenca).pack(side="left", padx=(8, 0))

        self._lbl_servidor = tk.Label(
            topo, text="", font=FONT["sm"],
            bg=THEME["bg"], fg=THEME["fg_light"])
        self._lbl_servidor.pack(side="right")

        # ── Cards de resumo ──────────────────────────────────
        self._frm_cards = tk.Frame(self, bg=THEME["bg"], padx=16)
        self._frm_cards.pack(fill="x", pady=(0, 8))

        # ── Tabela de empresas e licenças ────────────────────
        self._tab = Tabela(self, colunas=[
            ("Empresa",      160),
            ("CNPJ",         120),
            ("Plano",         70),
            ("Status",        80),
            ("Validade",      90),
            ("Dias rest.",    70),
            ("Máx. usuários", 80),
            ("Ativada em",    100),
        ])
        self._tab.pack(fill="both", expand=True, padx=16, pady=(0, 12))
        self._tab.ao_duplo_clique = lambda _: self._ver_detalhe()

        # Botões de ação
        acao = tk.Frame(self, bg=THEME["bg"], padx=16, pady=8)
        acao.pack(fill="x")
        botao(acao, "📋 Detalhes",      tipo="secundario", command=self._ver_detalhe).pack(side="left")
        botao(acao, "🔑 Ativar Licença", tipo="sucesso",  command=self._ativar_licenca).pack(side="left", padx=(8, 0))
        botao(acao, "🚫 Revogar",       tipo="perigo",    command=self._revogar).pack(side="left", padx=(8, 0))
        botao(acao, "✅ Reativar",       tipo="sucesso",   command=self._reativar).pack(side="left", padx=(8, 0))
        botao(acao, "🖥 Reset Máq.",    tipo="secundario", command=self._reset_maquina).pack(side="left", padx=(8, 0))
        botao(acao, "🗑 Excluir",       tipo="perigo",    command=self._excluir).pack(side="right")

    def _carregar(self):
        """Tenta buscar licenças do servidor Flask. Se offline, lê dados locais."""
        self._tab.limpar()
        self._licencas = []

        try:
            from models.licenca import Licenca, _SERVIDOR_URL, ADMIN_API_KEY_LOCAL
            import urllib.request
            req = urllib.request.Request(
                f"{_SERVIDOR_URL}/api/admin/licencas",
                headers={"X-Admin-Key": ADMIN_API_KEY_LOCAL},
                method="GET"
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                self._licencas = json.loads(resp.read())
            self._lbl_servidor.configure(
                text=f"Servidor: {_SERVIDOR_URL}", fg=THEME.get("success", "#2dce89"))
        except Exception as e:
            self._lbl_servidor.configure(
                text=f"Servidor offline — dados locais", fg="#f4b942")
            self._carregar_local()
            return

        self._renderizar()
        self._atualizar_cards()

    def _carregar_local(self):
        """Fallback: lê empresas do banco master e status do arquivo local."""
        from core.database import DatabaseManager
        try:
            empresas = DatabaseManager.master().fetchall(
                "SELECT * FROM empresas WHERE ativo=1 ORDER BY nome")
        except Exception:
            empresas = []

        hoje = datetime.date.today().isoformat()
        for emp in empresas:
            # Tenta ler arquivo de licença da empresa (se existir)
            self._licencas.append({
                "id":           emp.get("id"),
                "cliente_nome": emp.get("nome", ""),
                "cnpj_empresa": emp.get("cnpj", ""),
                "plano":        "—",
                "status":       "SEM_DADOS",
                "validade_ate": None,
                "ativada_em":   None,
                "max_usuarios": "—",
            })
        self._renderizar()
        self._atualizar_cards()

    def _renderizar(self):
        self._tab.limpar()
        hoje = datetime.date.today().isoformat()
        for l in self._licencas:
            val = l.get("validade_ate") or ""
            if val:
                try:
                    dias_r = (datetime.date.fromisoformat(val) -
                               datetime.date.today()).days
                    dias_str = str(max(0, dias_r))
                except Exception:
                    dias_str = "—"
            else:
                dias_str = "∞"

            self._tab.inserir([
                l.get("cliente_nome", "—"),
                self._fmt_cnpj(l.get("cnpj_empresa", "") or ""),
                l.get("plano", "—"),
                l.get("status", "—"),
                val or "Sem exp.",
                dias_str,
                str(l.get("max_usuarios", "—")),
                (l.get("ativada_em") or "—")[:10],
            ])

    def _atualizar_cards(self):
        for w in self._frm_cards.winfo_children():
            w.destroy()

        total    = len(self._licencas)
        ativas   = sum(1 for l in self._licencas if l.get("status") == "ATIVA")
        trials   = sum(1 for l in self._licencas if l.get("status") == "TRIAL")
        bloqueadas=sum(1 for l in self._licencas if l.get("status") == "BLOQUEADA")
        hoje     = datetime.date.today().isoformat()
        expirando= sum(1 for l in self._licencas
                       if l.get("validade_ate") and l.get("status") == "ATIVA"
                       and l["validade_ate"] > hoje
                       and (datetime.date.fromisoformat(l["validade_ate"])
                            - datetime.date.today()).days <= 30)

        for label, valor, cor in [
            ("Total",            total,     THEME["primary"]),
            ("Ativas",           ativas,    "#2dce89"),
            ("Trial",            trials,    "#4f8ef7"),
            ("Bloqueadas",       bloqueadas,"#f5365c"),
            ("Exp. em 30 dias",  expirando, "#f4b942"),
        ]:
            card = tk.Frame(self._frm_cards, bg=THEME["bg_card"],
                            highlightthickness=1,
                            highlightbackground=THEME["border"])
            card.pack(side="left", padx=(0, 8), ipadx=14, ipady=8)
            tk.Label(card, text=str(valor),
                     font=("TkDefaultFont", 20, "bold"),
                     bg=THEME["bg_card"], fg=cor).pack()
            tk.Label(card, text=label, font=FONT["sm"],
                     bg=THEME["bg_card"], fg=THEME["fg_light"]).pack()

    def _selecionado(self) -> dict | None:
        idx = self._tab.selecionado_indice()
        if idx is None or idx >= len(self._licencas):
            messagebox.showwarning("Atenção", "Selecione uma licença.", parent=self)
            return None
        return self._licencas[idx]

    def _ver_detalhe(self):
        l = self._selecionado()
        if l:
            DetalheModal(self, l)

    def _revogar(self):
        l = self._selecionado()
        if not l:
            return
        if l.get("status") == "BLOQUEADA":
            messagebox.showinfo("Info", "Já está bloqueada.", parent=self)
            return
        motivo = self._pedir_motivo("Revogar licença",
                                     f"Bloquear licença de '{l.get('cliente_nome')}'?")
        if motivo is None:
            return
        self._acao_servidor(f"/api/admin/licencas/{l['id']}/revogar",
                             {"motivo": motivo}, "Licença revogada.")

    def _reativar(self):
        l = self._selecionado()
        if not l:
            return
        motivo = self._pedir_motivo("Reativar licença",
                                     f"Reativar licença de '{l.get('cliente_nome')}'?")
        if motivo is None:
            return
        self._acao_servidor(f"/api/admin/licencas/{l['id']}/reativar",
                             {"motivo": motivo}, "Licença reativada.")

    def _reset_maquina(self):
        l = self._selecionado()
        if not l:
            return
        motivo = self._pedir_motivo("Reset de máquina",
                                     f"Remover vínculo de máquina de '{l.get('cliente_nome')}'?\n"
                                     "O cliente poderá reativar em um novo computador.")
        if motivo is None:
            return
        self._acao_servidor(f"/api/admin/licencas/{l['id']}/resetar-maquina",
                             {"motivo": motivo}, "Vínculo removido.")

    def _excluir(self):
        l = self._selecionado()
        if not l:
            return
        status = l.get("status", "")
        permitidos = {"BLOQUEADA", "EXPIRADA", "INVALIDA", "SEM_DADOS"}
        if status not in permitidos:
            messagebox.showwarning(
                "Não permitido",
                f"Só é possível excluir licenças com status: "
                f"Bloqueada, Expirada ou Inválida.\n\nStatus atual: {status}",
                parent=self,
            )
            return
        if not messagebox.askyesno(
            "Confirmar exclusão",
            f"Excluir definitivamente a licença de '{l.get('cliente_nome')}'?\n\n"
            f"Status: {status}\n\n"
            "Esta ação não pode ser desfeita.",
            icon="warning",
            parent=self,
        ):
            return
        try:
            from models.licenca import _SERVIDOR_URL, ADMIN_API_KEY_LOCAL
            import urllib.request
            req = urllib.request.Request(
                f"{_SERVIDOR_URL}/api/admin/licencas/{l['id']}",
                headers={"X-Admin-Key": ADMIN_API_KEY_LOCAL,
                         "Content-Type": "application/json"},
                method="DELETE",
            )
            with urllib.request.urlopen(req, timeout=10):
                pass
            messagebox.showinfo("Excluído", "Licença excluída com sucesso.", parent=self)
            self._carregar()
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao excluir no servidor:\n{e}", parent=self)

    def _ativar_licenca(self):
        l = self._selecionado()
        if l:
            AtivarLicencaModal(self, l, ao_ativar=self._carregar)

    def _nova_licenca(self):
        NovaLicencaModal(self, ao_criar=self._carregar)

    def _acao_servidor(self, path: str, payload: dict, msg_ok: str):
        try:
            from models.licenca import _SERVIDOR_URL, ADMIN_API_KEY_LOCAL
            import urllib.request
            data = json.dumps(payload).encode()
            req  = urllib.request.Request(
                f"{_SERVIDOR_URL}{path}",
                data=data,
                headers={"Content-Type": "application/json",
                         "X-Admin-Key": ADMIN_API_KEY_LOCAL},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=10):
                pass
            messagebox.showinfo("Sucesso", msg_ok, parent=self)
            self._carregar()
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao comunicar com o servidor:\n{e}", parent=self)

    @staticmethod
    def _fmt_cnpj(v: str) -> str:
        v = "".join(c for c in v if c.isdigit())
        if len(v) == 14:
            return f"{v[:2]}.{v[2:5]}.{v[5:8]}/{v[8:12]}-{v[12:]}"
        return v or "—"

    @staticmethod
    def _pedir_motivo(titulo: str, pergunta: str) -> str | None:
        """Abre diálogo pedindo motivo. Retorna None se cancelado."""
        import tkinter.simpledialog as sd
        # Não usamos simpledialog para ter mais controle; usamos messagebox + confirm
        if not messagebox.askyesno(titulo, pergunta):
            return None
        return ""  # motivo vazio OK


# ════════════════════════════════════════════════════════════════
# Modal de detalhe da licença
# ════════════════════════════════════════════════════════════════
class DetalheModal(tk.Toplevel):
    def __init__(self, master, licenca: dict):
        super().__init__(master)
        self.title(f"Licença — {licenca.get('cliente_nome','')}")
        self.configure(bg=THEME["bg"])
        self.grab_set()
        self.transient(master.winfo_toplevel())
        from assets import Assets
        Assets.setup_toplevel(self, 500, 560)
        self._l = licenca
        self._build()

    def _build(self):
        l = self._l
        status = l.get("status", "—")
        cor = STATUS_COR.get(status, "#888")

        # Banner
        banner = tk.Frame(self, bg=cor, padx=20, pady=12)
        banner.pack(fill="x")
        tk.Label(banner, text=f"{l.get('plano','—')}  —  {status}",
                 font=FONT["bold"], bg=cor, fg="white").pack(side="left")
        tk.Label(banner, text=f"#{l.get('id','?')}",
                 font=FONT["sm"], bg=cor, fg="white").pack(side="right")

        body = tk.Frame(self, bg=THEME["bg"], padx=20, pady=16)
        body.pack(fill="both", expand=True)

        def linha(label, valor):
            r = tk.Frame(body, bg=THEME["bg"])
            r.pack(fill="x", pady=3)
            tk.Label(r, text=f"{label}:", font=FONT["sm"],
                     bg=THEME["bg"], fg=THEME["fg_light"],
                     width=16, anchor="e").pack(side="left", padx=(0, 8))
            tk.Label(r, text=str(valor or "—"), font=FONT["sm"],
                     bg=THEME["bg"], fg=THEME["fg"],
                     anchor="w", wraplength=320).pack(side="left")

        linha("Cliente",       l.get("cliente_nome"))
        linha("CNPJ",          AbaLicencas._fmt_cnpj(l.get("cnpj_empresa") or ""))
        linha("E-mail",        l.get("cliente_email"))
        linha("Chave",         l.get("chave"))
        linha("Validade",      l.get("validade_ate") or "Sem expiração")
        linha("Ativada em",    (l.get("ativada_em") or "—")[:16])
        linha("Último check",  (l.get("ultimo_check") or "—")[:16])
        linha("Grace period",  l.get("grace_ate") or "—")
        linha("Máx. usuários", l.get("max_usuarios"))
        linha("Obs.",          l.get("obs"))

        # Chave copiável
        SecaoForm(body, "CHAVE DE ATIVAÇÃO").pack(fill="x", pady=(12, 4))
        frm_chave = tk.Frame(body, bg=THEME["bg_card"],
                              highlightthickness=1,
                              highlightbackground=THEME["border"])
        frm_chave.pack(fill="x")
        tk.Label(frm_chave, text=l.get("chave", "N/A"),
                 font=("Consolas", 11), bg=THEME["bg_card"],
                 fg=THEME["primary"], padx=12, pady=8).pack(side="left")
        botao(frm_chave, "📋", tipo="secundario",
              command=lambda: self._copiar(l.get("chave", ""))).pack(
              side="right", padx=8)

        botao(body, "Fechar", tipo="secundario",
              command=self.destroy).pack(fill="x", pady=(16, 0))

    def _copiar(self, texto: str):
        self.clipboard_clear()
        self.clipboard_append(texto)
        messagebox.showinfo("Copiado", "Chave copiada!", parent=self)


# ════════════════════════════════════════════════════════════════
# Modal de nova licença
# ════════════════════════════════════════════════════════════════
class NovaLicencaModal(tk.Toplevel):
    def __init__(self, master, ao_criar=None):
        super().__init__(master)
        self.title("Nova Licença")
        self.configure(bg=THEME["bg"])
        self.grab_set()
        self.transient(master.winfo_toplevel())
        from assets import Assets
        Assets.setup_toplevel(self, 480, 520)
        self._ao_criar = ao_criar
        self._build()

    def _build(self):
        hdr = tk.Frame(self, bg=THEME["primary"], padx=20, pady=12)
        hdr.pack(fill="x")
        tk.Label(hdr, text="➕ Gerar Nova Licença",
                 font=FONT["bold"], bg=THEME["primary"], fg="white").pack(anchor="w")

        body = tk.Frame(self, bg=THEME["bg"], padx=20, pady=16)
        body.pack(fill="both", expand=True)

        self._var_nome  = tk.StringVar()
        self._var_cnpj  = tk.StringVar()
        self._var_email = tk.StringVar()
        self._var_plano = tk.StringVar(value="BASICO")
        self._var_maxu  = tk.StringVar(value="3")
        self._var_val   = tk.StringVar(value="365")
        self._var_obs   = tk.StringVar()

        CampoEntry(body, "Nome do cliente *", self._var_nome).pack(fill="x", pady=(0, 8))

        row = tk.Frame(body, bg=THEME["bg"])
        row.pack(fill="x", pady=(0, 8))
        CampoEntry(row, "CNPJ", self._var_cnpj).pack(side="left", fill="x", expand=True, padx=(0, 8))
        CampoEntry(row, "E-mail", self._var_email).pack(side="left", fill="x", expand=True)

        row2 = tk.Frame(body, bg=THEME["bg"])
        row2.pack(fill="x", pady=(0, 8))

        col_p = tk.Frame(row2, bg=THEME["bg"])
        col_p.pack(side="left", fill="x", expand=True, padx=(0, 8))
        tk.Label(col_p, text="Plano", font=FONT["sm"],
                 bg=THEME["bg"], fg=THEME["fg"]).pack(anchor="w")
        ttk.Combobox(col_p, textvariable=self._var_plano,
                     values=PLANOS, state="readonly",
                     font=FONT["md"]).pack(fill="x", ipady=4)

        col_u = tk.Frame(row2, bg=THEME["bg"])
        col_u.pack(side="left", fill="x", expand=True, padx=(0, 8))
        tk.Label(col_u, text="Máx. usuários", font=FONT["sm"],
                 bg=THEME["bg"], fg=THEME["fg"]).pack(anchor="w")
        ttk.Combobox(col_u, textvariable=self._var_maxu,
                     values=["1","2","3","5","10","20","0"],
                     state="readonly", font=FONT["md"]).pack(fill="x", ipady=4)

        col_v = tk.Frame(row2, bg=THEME["bg"])
        col_v.pack(side="left", fill="x", expand=True)
        tk.Label(col_v, text="Validade (dias)", font=FONT["sm"],
                 bg=THEME["bg"], fg=THEME["fg"]).pack(anchor="w")
        ttk.Combobox(col_v, textvariable=self._var_val,
                     values=["30","90","180","365","730",""],
                     state="readonly", font=FONT["md"]).pack(fill="x", ipady=4)

        CampoEntry(body, "Obs. internas", self._var_obs).pack(fill="x", pady=(8, 0))

        # Resultado
        self._lbl_chave = tk.Label(body, text="",
                                    font=("Consolas", 12),
                                    bg=THEME["bg_card"], fg=THEME["primary"],
                                    padx=12, pady=8, wraplength=440)
        self._lbl_chave.pack(fill="x", pady=(12, 4))

        self._var_err = tk.StringVar()
        tk.Label(body, textvariable=self._var_err, font=FONT["sm"],
                 bg=THEME["bg"], fg=THEME["danger"],
                 wraplength=440).pack(anchor="w")

        row_btn = tk.Frame(body, bg=THEME["bg"])
        row_btn.pack(fill="x", pady=(8, 0))
        botao(row_btn, "⚡ Gerar", tipo="primario",
              command=self._gerar).pack(side="left")
        botao(row_btn, "📋 Copiar", tipo="secundario",
              command=self._copiar).pack(side="left", padx=(8, 0))
        botao(row_btn, "Fechar", tipo="secundario",
              command=self.destroy).pack(side="right")

        self._chave_gerada = ""

    def _gerar(self):
        nome = self._var_nome.get().strip()
        if not nome:
            self._var_err.set("Nome obrigatório.")
            return
        try:
            from models.licenca import _SERVIDOR_URL, ADMIN_API_KEY_LOCAL
            import urllib.request
            payload = json.dumps({
                "cliente_nome":  nome,
                "cliente_email": self._var_email.get().strip(),
                "cnpj_empresa":  self._var_cnpj.get().replace(".", "").replace("/", "").replace("-", ""),
                "plano":         self._var_plano.get(),
                "max_usuarios":  int(self._var_maxu.get() or 3),
                "validade_dias": int(self._var_val.get()) if self._var_val.get() else None,
                "obs":           self._var_obs.get().strip(),
            }, default=str).encode()
            req = urllib.request.Request(
                f"{_SERVIDOR_URL}/api/admin/licencas",
                data=payload,
                headers={"Content-Type": "application/json",
                         "X-Admin-Key": ADMIN_API_KEY_LOCAL},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                res = json.loads(resp.read())
            self._chave_gerada = res["chave"]
            self._lbl_chave.configure(text=f"Chave: {self._chave_gerada}")
            self._var_err.set("")
            if self._ao_criar:
                self._ao_criar()
        except Exception as e:
            self._var_err.set(f"Erro: {e}")

    def _copiar(self):
        if self._chave_gerada:
            self.clipboard_clear()
            self.clipboard_append(self._chave_gerada)
            messagebox.showinfo("Copiado", "Chave copiada!", parent=self)


# ════════════════════════════════════════════════════════════════
# Modal de ativação de licença para uma empresa selecionada
# ════════════════════════════════════════════════════════════════
class AtivarLicencaModal(tk.Toplevel):
    def __init__(self, master, licenca: dict, ao_ativar=None):
        super().__init__(master)
        self.title(f"Ativar Licença — {licenca.get('cliente_nome', '')}")
        self.configure(bg=THEME["bg"])
        self.grab_set()
        self.transient(master.winfo_toplevel())
        from assets import Assets
        Assets.setup_toplevel(self, 500, 420)
        self._l        = licenca
        self._ao_ativar = ao_ativar
        self._ativando  = False
        self._build()

    def _build(self):
        l = self._l
        status = l.get("status", "—")
        cor_banner = STATUS_COR.get(status, THEME["primary"])

        # ── Cabeçalho ──────────────────────────────────────
        hdr = tk.Frame(self, bg=cor_banner, padx=20, pady=14)
        hdr.pack(fill="x")
        tk.Label(hdr, text="🔑  Ativar Licença",
                 font=FONT["title"], bg=cor_banner, fg="white").pack(anchor="w")
        tk.Label(hdr,
                 text=f"{l.get('cliente_nome', '—')}  •  {AbaLicencas._fmt_cnpj(l.get('cnpj_empresa') or '')}",
                 font=FONT["sm"], bg=cor_banner, fg="white").pack(anchor="w")

        body = tk.Frame(self, bg=THEME["bg"], padx=24, pady=20)
        body.pack(fill="both", expand=True)

        # Info do status atual
        frm_status = tk.Frame(body, bg=THEME["bg_card"],
                               highlightthickness=1,
                               highlightbackground=THEME["border"])
        frm_status.pack(fill="x", pady=(0, 16))
        tk.Label(frm_status,
                 text=f"Status atual:  {status}   |   Plano:  {l.get('plano', '—')}",
                 font=FONT["sm"], bg=THEME["bg_card"],
                 fg=STATUS_COR.get(status, THEME["fg"]),
                 padx=12, pady=8).pack(anchor="w")

        # Campo da chave
        tk.Label(body, text="Chave de licença",
                 font=FONT["bold"], bg=THEME["bg"], fg=THEME["fg"]).pack(anchor="w")
        tk.Label(body,
                 text="Cole abaixo a chave gerada para esta empresa:",
                 font=FONT["sm"], bg=THEME["bg"], fg=THEME["fg_light"]).pack(anchor="w", pady=(2, 6))

        self._var_chave = tk.StringVar()
        self._ent_chave = tk.Entry(
            body, textvariable=self._var_chave,
            font=("Consolas", 12), relief="flat",
            bg=THEME["bg_card"], fg=THEME["fg"],
            insertbackground=THEME["fg"],
            highlightthickness=2,
            highlightbackground=THEME["border"],
            highlightcolor=THEME["primary"],
        )
        self._ent_chave.pack(fill="x", ipady=8, pady=(0, 4))
        self._ent_chave.focus_set()

        tk.Label(body, text="Formato: XXXX-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX",
                 font=("Consolas", 8), bg=THEME["bg"],
                 fg=THEME["fg_light"]).pack(anchor="w", pady=(0, 12))

        # Mensagem de retorno
        self._var_msg = tk.StringVar()
        self._lbl_msg = tk.Label(body, textvariable=self._var_msg,
                                  font=FONT["sm"], bg=THEME["bg"],
                                  fg=THEME["danger"], wraplength=450,
                                  justify="left")
        self._lbl_msg.pack(anchor="w", pady=(0, 8))

        # Botões
        btn_row = tk.Frame(body, bg=THEME["bg"])
        btn_row.pack(fill="x")
        self._btn_ativar = botao(btn_row, "🔑  Ativar",
                                  tipo="sucesso", command=self._ativar)
        self._btn_ativar.pack(side="left")
        botao(btn_row, "Fechar", tipo="secundario",
              command=self.destroy).pack(side="right")

        self.bind("<Return>", lambda _: self._ativar())

    def _ativar(self):
        if self._ativando:
            return
        chave = self._var_chave.get().strip()
        if not chave:
            self._set_msg("Cole a chave de licença antes de ativar.", erro=True)
            return

        cnpj = (self._l.get("cnpj_empresa") or "").replace(".", "").replace("/", "").replace("-", "")

        self._ativando = True
        self._btn_ativar.configure(state="disabled", text="⏳  Ativando...")
        self._set_msg("Conectando ao servidor de licenças...", erro=False)
        self.update()

        import threading
        def _worker():
            try:
                from models.licenca import (
                    _SERVIDOR_URL, _salvar_local, _assinar_chave,
                    Licenca, LicencaStatus, PLANOS,
                )
                import urllib.request
                import json as _json
                import datetime

                # Ativa no servidor sem fingerprint (admin atua em nome da empresa)
                payload = _json.dumps({
                    "chave":        chave,
                    "fingerprint":  "",   # sem fingerprint — admin não é a máquina do cliente
                    "versao":       "1.0.0",
                    "cnpj_empresa": cnpj,
                }).encode()
                req = urllib.request.Request(
                    f"{_SERVIDOR_URL}/api/v1/ativar",
                    data=payload,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    resultado = _json.loads(resp.read())

                if not resultado.get("valida"):
                    motivo = (resultado.get("motivo")
                              or resultado.get("message")
                              or resultado.get("error")
                              or "Chave inválida.")
                    self.after(0, lambda: self._pos_ativacao(False, motivo))
                    return

                # Salva arquivo de licença local para que o login da empresa funcione.
                # fingerprint vazio → inicializar() ignora verificação de máquina.
                hoje = datetime.date.today()
                dados_locais = {
                    "chave":        chave,
                    "chave_hash":   _assinar_chave(chave),
                    "plano":        resultado.get("plano", "BASICO"),
                    "modulos":      resultado.get("modulos", PLANOS["BASICO"]["modulos"]),
                    "max_empresas": resultado.get("max_empresas", 1),
                    "max_usuarios": resultado.get("max_usuarios", 3),
                    "emitida_em":   resultado.get("emitida_em", hoje.isoformat()),
                    "validade_ate": resultado.get("validade_ate"),
                    "fingerprint":  "",   # sem vínculo de máquina — admin ativou pelo painel
                    "ativada_em":   hoje.isoformat(),
                    "ultimo_check": hoje.isoformat(),
                    "grace_ate":    (hoje + datetime.timedelta(days=7)).isoformat(),
                    "cnpj_empresa": cnpj,
                }
                _salvar_local(dados_locais)
                Licenca._dados  = dados_locais
                Licenca._status = LicencaStatus.ATIVA
                Licenca._motivo = ""

                plano = resultado.get("plano", "?")
                self.after(0, lambda: self._pos_ativacao(
                    True,
                    f"Licença {plano} ativada com sucesso!\n"
                    f"A empresa já pode acessar o sistema.",
                ))
            except Exception as e:
                self.after(0, lambda: self._pos_ativacao(False, str(e)))

        threading.Thread(target=_worker, daemon=True).start()

    def _pos_ativacao(self, sucesso: bool, msg: str):
        self._ativando = False
        self._btn_ativar.configure(state="normal", text="🔑  Ativar")
        if sucesso:
            self._set_msg(f"✓ {msg}", erro=False)
            messagebox.showinfo("Licença Ativada", msg, parent=self)
            if self._ao_ativar:
                self._ao_ativar()
            self.destroy()
        else:
            self._set_msg(msg, erro=True)

    def _set_msg(self, msg: str, erro: bool = True):
        self._var_msg.set(msg)
        self._lbl_msg.configure(
            fg=THEME.get("danger", "red") if erro else THEME.get("success", "green"))