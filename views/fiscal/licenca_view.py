"""
Tela de Ativação de Licença — exibida ao cliente quando:
  1. Trial expirou
  2. Licença bloqueada
  3. Usuário acessa Ajuda → Licença

Fluxo:
  1. Mostra status atual (badge colorido + dias restantes)
  2. Campo para colar a chave
  3. Botão Ativar → chama Licenca.ativar()
  4. Sucesso → fecha e continua
"""
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import datetime
from config import THEME, FONT
from views.base_view import BaseView
from views.widgets.widgets import botao


COR_STATUS = {
    "TRIAL":     ("#1a1f3a", "#4f8ef7"),
    "ATIVA":     ("#0d3324", "#2dce89"),
    "GRACE":     ("#2a2010", "#f4b942"),
    "EXPIRADA":  ("#2d0f18", "#f5365c"),
    "BLOQUEADA": ("#2d0f18", "#f5365c"),
    "INVALIDA":  ("#1a1a1a", "#888"),
}

ICONE_STATUS = {
    "TRIAL":    "🕐",
    "ATIVA":    "✅",
    "GRACE":    "⚠️",
    "EXPIRADA": "❌",
    "BLOQUEADA":"🚫",
    "INVALIDA": "⛔",
}


class TelaLicenca(BaseView):
    """
    Modal de ativação/visualização de licença.
    Parâmetro `bloqueante=True` → só fecha se a licença estiver ativa.
    """
    def __init__(self, master, bloqueante: bool = False):
        super().__init__(master, "🔑 Licença do Software", 520, 580, modal=True)
        self.resizable(False, False)
        self._bloqueante = bloqueante
        self._ativando   = False
        self._build()
        self._atualizar_status()

    def _build(self):
        from models.licenca import PLANOS

        bg = THEME["bg"]
        P  = 28

        # ── Banner de status ───────────────────────────────
        self._frm_banner = tk.Frame(self, height=80)
        self._frm_banner.pack(fill="x")
        self._frm_banner.pack_propagate(False)

        self._lbl_icone = tk.Label(self._frm_banner, text="",
                                    font=("TkDefaultFont", 28))
        self._lbl_icone.place(x=P, rely=0.5, anchor="w")

        self._lbl_status = tk.Label(self._frm_banner, text="",
                                     font=FONT["title"])
        self._lbl_status.place(x=P + 52, rely=0.35, anchor="w")

        self._lbl_sub = tk.Label(self._frm_banner, text="",
                                  font=FONT["sm"])
        self._lbl_sub.place(x=P + 52, rely=0.72, anchor="w")

        # ── Corpo ─────────────────────────────────────────
        body = tk.Frame(self, bg=bg)
        body.pack(fill="both", expand=True, padx=P, pady=16)

        # Cards de info
        self._frm_info = tk.Frame(body, bg=bg)
        self._frm_info.pack(fill="x", pady=(0, 16))

        # ── Seção de ativação ──────────────────────────────
        sep = tk.Frame(body, bg=THEME["border"], height=1)
        sep.pack(fill="x", pady=(0, 16))

        tk.Label(body, text="ATIVAR / RENOVAR LICENÇA",
                 font=("TkDefaultFont", 9, "bold"),
                 bg=bg, fg=THEME["fg_light"]).pack(anchor="w", pady=(0, 8))

        tk.Label(body,
                 text="Cole abaixo a chave fornecida pelo suporte após a compra:",
                 font=FONT["sm"], bg=bg, fg=THEME["fg"]).pack(anchor="w", pady=(0, 6))

        # Campo da chave
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
        self._ent_chave.pack(fill="x", ipady=8, pady=(0, 6))

        # Exemplo de formato
        tk.Label(body, text="Formato: XXXX-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX",
                 font=("Consolas", 8), bg=bg,
                 fg=THEME["fg_light"]).pack(anchor="w", pady=(0, 12))

        # Mensagem de retorno
        self._var_msg = tk.StringVar()
        self._lbl_msg = tk.Label(body, textvariable=self._var_msg,
                                  font=FONT["sm"], bg=bg,
                                  fg=THEME["danger"], wraplength=460,
                                  justify="left")
        self._lbl_msg.pack(anchor="w", pady=(0, 8))

        # Botão ativar
        self._btn_ativar = botao(body, "🔑  Ativar Licença",
                                  tipo="sucesso", command=self._ativar)
        self._btn_ativar.pack(fill="x", pady=(0, 8))

        # Rodapé
        sep2 = tk.Frame(body, bg=THEME["border"], height=1)
        sep2.pack(fill="x", pady=(8, 12))

        rodape = tk.Frame(body, bg=bg)
        rodape.pack(fill="x")
        tk.Label(rodape, text="Precisa de ajuda?  ",
                 font=FONT["sm"], bg=bg,
                 fg=THEME["fg_light"]).pack(side="left")
        tk.Label(rodape, text="suporte@seu-sistema.com.br",
                 font=FONT["sm"], bg=bg, fg=THEME["primary"],
                 cursor="hand2").pack(side="left")

        if not self._bloqueante:
            botao(body, "Fechar", tipo="secundario",
                  command=self.destroy).pack(fill="x", pady=(4, 0))

        # Intercepta fechar janela se bloqueante
        if self._bloqueante:
            self.protocol("WM_DELETE_WINDOW", self._tentar_fechar)

    def _atualizar_status(self):
        from models.licenca import Licenca, LicencaStatus, PLANOS
        r = Licenca.resumo()

        status = r["status"]
        bg_cor, fg_cor = COR_STATUS.get(status, ("#111", "#aaa"))

        self._frm_banner.configure(bg=bg_cor)
        self._lbl_icone.configure(text=ICONE_STATUS.get(status, "?"),
                                   bg=bg_cor)
        self._lbl_status.configure(bg=bg_cor, fg=fg_cor,
                                    text=f"  {r['plano_nome']}")
        self._lbl_sub.configure(bg=bg_cor, fg=fg_cor,
                                 text=f"  {r['motivo'] or status}")

        # Cards de info
        for w in self._frm_info.winfo_children():
            w.destroy()

        infos = []
        if r["validade"]:
            dias = r.get("dias_restantes")
            infos.append(("Validade",
                          f"{r['validade']}  ({dias} dia{'s' if dias!=1 else ''} restante{'s' if dias!=1 else ''})"))
        else:
            infos.append(("Validade", "Sem expiração"))

        infos.append(("Máx. usuários",
                      str(r["max_usuarios"]) if r["max_usuarios"] else "Ilimitado"))
        mods = r.get("modulos", [])
        infos.append(("Módulos",
                      ", ".join(mods) if mods != ["*"] else "Todos"))
        infos.append(("Fingerprint", r.get("fingerprint", "—")))

        for label, valor in infos:
            row = tk.Frame(self._frm_info, bg=THEME["bg"])
            row.pack(fill="x", pady=2)
            tk.Label(row, text=f"{label}:", font=FONT["sm"],
                     bg=THEME["bg"], fg=THEME["fg_light"],
                     width=16, anchor="e").pack(side="left", padx=(0, 8))
            tk.Label(row, text=valor, font=FONT["sm"],
                     bg=THEME["bg"], fg=THEME["fg"],
                     anchor="w").pack(side="left")

    def _ativar(self):
        if self._ativando:
            return
        chave = self._var_chave.get().strip()
        if not chave:
            self._set_msg("Digite a chave de licença.", erro=True)
            return

        self._ativando = True
        self._btn_ativar.configure(state="disabled",
                                    text="⏳  Ativando, aguarde...")
        self._set_msg("Conectando ao servidor de licenças...", erro=False)
        self.update()

        def _worker():
            from models.licenca import Licenca
            try:
                sucesso, msg = Licenca.ativar(chave)
                self.after(0, lambda: self._pos_ativacao(sucesso, msg))
            except Exception as e:
                self.after(0, lambda: self._pos_ativacao(False, str(e)))

        threading.Thread(target=_worker, daemon=True).start()

    def _pos_ativacao(self, sucesso: bool, msg: str):
        self._ativando = False
        self._btn_ativar.configure(state="normal", text="🔑  Ativar Licença")

        if sucesso:
            self._set_msg("", erro=False)
            self._atualizar_status()
            messagebox.showinfo("Licença Ativada", msg, parent=self)
            if not self._bloqueante:
                self.destroy()
        else:
            self._set_msg(msg, erro=True)

    def _set_msg(self, msg: str, erro: bool = True):
        self._var_msg.set(msg)
        self._lbl_msg.configure(
            fg=THEME.get("danger", "red") if erro else THEME.get("success", "green"))

    def _tentar_fechar(self):
        from models.licenca import Licenca
        if Licenca.ativa():
            self.destroy()
        else:
            messagebox.showwarning(
                "Licença necessária",
                "Ative uma licença para continuar usando o sistema.\n\n"
                "Se você já comprou, verifique o e-mail com a chave de ativação.",
                parent=self,
            )