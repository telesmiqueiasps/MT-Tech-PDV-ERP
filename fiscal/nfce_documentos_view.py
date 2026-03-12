"""Tela de gestão de documentos NFC-e emitidos."""
import tkinter as tk
from tkinter import messagebox, ttk
from config import THEME, FONT
from views.widgets.tabela import Tabela


class NfceDocumentosView(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Documentos NFC-e")
        self.configure(bg=THEME["bg"])
        self.grab_set()
        self._build()
        self._centralizar(900, 540)
        self._carregar()

    def _centralizar(self, w, h):
        self.update_idletasks()
        x = (self.winfo_screenwidth()  - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _build(self):
        # Toolbar
        tb = tk.Frame(self, bg=THEME["bg_card"],
                      highlightthickness=1, highlightbackground=THEME["border"],
                      padx=12, pady=8)
        tb.pack(fill="x")
        tk.Label(tb, text="Documentos NFC-e", font=FONT["lg_bold"],
                 bg=THEME["bg_card"], fg=THEME["fg"]).pack(side="left")

        tk.Button(tb, text="↻ Consultar SEFAZ", font=FONT["sm"],
                  bg=THEME["bg_card"], fg=THEME["primary"], relief="flat",
                  command=self._consultar_sefaz).pack(side="right", padx=(4, 0))
        tk.Button(tb, text="Reimprimir DANFE", font=FONT["sm"],
                  bg=THEME["bg_card"], fg=THEME["fg"], relief="flat",
                  command=self._reimprimir).pack(side="right", padx=(4, 0))
        tk.Button(tb, text="Reemitir", font=FONT["sm"],
                  bg=THEME["warning"], fg="white", relief="flat", padx=8,
                  command=self._reemitir).pack(side="right", padx=(4, 0))
        tk.Button(tb, text="Cancelar NFC-e", font=FONT["sm"],
                  bg=THEME["danger"], fg="white", relief="flat", padx=8,
                  command=self._cancelar).pack(side="right", padx=(4, 0))

        # Tabela
        self._tabela = Tabela(self, colunas=[
            ("ID",       40),
            ("Número",   70),
            ("Série",    50),
            ("Data",    120),
            ("Venda",    60),
            ("Status",  100),
            ("Chave",   340),
            ("Valor",    90),
        ])
        self._tabela.pack(fill="both", expand=True)

    def _carregar(self):
        from core.database import DatabaseManager
        docs = DatabaseManager.empresa().fetchall(
            "SELECT * FROM nfce_documentos ORDER BY criado_em DESC LIMIT 200"
        )
        self._tabela.limpar()
        for d in docs:
            self._tabela.inserir([
                d["id"],
                d["numero"],
                d["serie"],
                (d.get("data_emissao") or d.get("criado_em") or "")[:16],
                d.get("venda_id") or "—",
                d["status"],
                d.get("chave_acesso") or "—",
                f"R$ {d.get('valor_total', 0):,.2f}",
            ])

    def _selecionado(self) -> dict | None:
        sel = self._tabela.selecionado()
        if not sel:
            messagebox.showwarning("Atenção", "Selecione um documento.", parent=self)
            return None
        from core.database import DatabaseManager
        return DatabaseManager.empresa().fetchone(
            "SELECT * FROM nfce_documentos WHERE id=?", (int(sel[0]),)
        )

    def _consultar_sefaz(self):
        doc = self._selecionado()
        if not doc:
            return
        try:
            from fiscal.nfce_config_model import NfceConfig
            from fiscal.nfce_sefaz import NfceSefaz
            cfg = NfceConfig.carregar()
            if not cfg:
                messagebox.showerror("Erro", "NFC-e não configurada.", parent=self)
                return
            sefaz  = NfceSefaz(cfg["cert_path"], cfg.get("cert_senha", ""), cfg.get("ambiente", 2))
            result = sefaz.consultar(doc["chave_acesso"])
            messagebox.showinfo("Consulta SEFAZ", result.get("motivo", ""), parent=self)
        except Exception as e:
            messagebox.showerror("Erro", str(e), parent=self)

    def _reimprimir(self):
        doc = self._selecionado()
        if not doc:
            return
        danfe = doc.get("danfe_path")
        if not danfe:
            messagebox.showwarning("Atenção", "DANFE não encontrado para este documento.", parent=self)
            return
        import os
        if os.path.exists(danfe):
            if hasattr(os, "startfile"):
                os.startfile(danfe)
            else:
                import subprocess
                subprocess.Popen(["xdg-open", danfe])
        else:
            messagebox.showwarning("Arquivo não encontrado", danfe, parent=self)

    def _cancelar(self):
        doc = self._selecionado()
        if not doc:
            return
        if doc["status"] != "AUTORIZADA":
            messagebox.showwarning("Atenção", "Apenas documentos AUTORIZADOS podem ser cancelados.", parent=self)
            return
        win = tk.Toplevel(self)
        win.title("Cancelar NFC-e")
        win.configure(bg=THEME["bg"])
        win.grab_set()
        win.geometry("420x220")
        tk.Label(win, text="Motivo do cancelamento (mín. 15 caracteres):",
                 font=FONT["sm"], bg=THEME["bg"], fg=THEME["fg"]).pack(anchor="w", padx=20, pady=(20, 4))
        var_motivo = tk.StringVar()
        tk.Entry(win, textvariable=var_motivo, font=FONT["md"], relief="flat",
                 bg=THEME["bg_input"], fg=THEME["fg"],
                 highlightthickness=1, highlightbackground=THEME["border"]).pack(fill="x", padx=20, ipady=7)

        def confirmar():
            motivo = var_motivo.get().strip()
            if len(motivo) < 15:
                messagebox.showwarning("Atenção", "O motivo deve ter no mínimo 15 caracteres.", parent=win)
                return
            try:
                from fiscal.nfce_service import NfceService
                result = NfceService().cancelar(doc["id"], motivo)
                if result.get("ok"):
                    messagebox.showinfo("Cancelado", "NFC-e cancelada com sucesso.", parent=win)
                    win.destroy()
                    self._carregar()
                else:
                    messagebox.showerror("Erro", result.get("motivo", ""), parent=win)
            except Exception as e:
                messagebox.showerror("Erro", str(e), parent=win)

        tk.Button(win, text="Confirmar Cancelamento", bg=THEME["danger"], fg="white",
                  font=FONT["bold"], relief="flat", pady=8,
                  command=confirmar).pack(fill="x", padx=20, pady=16)

    def _reemitir(self):
        doc = self._selecionado()
        if not doc:
            return
        if doc["status"] not in ("REJEITADA", "PENDENTE"):
            messagebox.showwarning("Atenção", "Apenas documentos REJEITADOS ou PENDENTES podem ser reemitidos.", parent=self)
            return
        venda_id = doc.get("venda_id")
        if not venda_id:
            messagebox.showwarning("Atenção", "Venda não associada a este documento.", parent=self)
            return
        try:
            from fiscal.nfce_service import NfceService
            result = NfceService().emitir(venda_id)
            if result["autorizada"]:
                messagebox.showinfo("Sucesso", f"NFC-e autorizada!\nProtocolo: {result.get('protocolo','')}", parent=self)
            else:
                messagebox.showwarning("Rejeitada", result.get("motivo", ""), parent=self)
            self._carregar()
        except Exception as e:
            messagebox.showerror("Erro", str(e), parent=self)
