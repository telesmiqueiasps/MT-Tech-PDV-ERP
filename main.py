import tkinter as tk
from config import MASTER_DB, APP_NAME
from core.database import DatabaseManager
from core.session import Session


def main():
    root = tk.Tk()
    root.withdraw()
    root.title(APP_NAME)

    # Inicializa assets (ícone, logos)
    from assets import Assets
    Assets.init(root)

    DatabaseManager.init_master(MASTER_DB)

    # Primeira execução
    from database.seeds.seed import admin_existe
    if not admin_existe():
        from views.login.setup_wizard import SetupWizard
        wizard = SetupWizard(root)
        root.wait_window(wizard)
        if not admin_existe():
            root.destroy()
            return

    # Seleção de empresa → login (loop permite voltar à seleção)
    from views.login.selecionar_empresa import SelecionarEmpresa
    from views.login.login_view import LoginView
    from pathlib import Path

    def _aplicar_migrations(db_path: Path) -> bool:
        """Aplica migrations pendentes com backup. Retorna False se houve erro."""
        try:
            from updater.migrations import MigrationManager
            aplicadas, nomes = MigrationManager().aplicar_pendentes(db_path)
            if aplicadas > 0:
                print(f"[migrations] {aplicadas} migration(s) aplicada(s): {nomes}")
            return True
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror(
                "Erro de Atualização do Banco",
                f"Não foi possível atualizar o banco de dados da empresa.\n\n{e}\n\n"
                "O sistema será encerrado para proteger os dados.",
                parent=root,
            )
            return False

    def _executar_login() -> dict | None:
        """Executa seleção de empresa + login. Retorna empresa ou None."""
        while True:
            tela_empresa = SelecionarEmpresa(root)
            root.wait_window(tela_empresa)

            empresa = tela_empresa.empresa_selecionada
            if not empresa:
                return None

            if empresa["id"] != 0:
                db_path = Path(empresa["db_path"])
                # Migrations com backup antes de conectar
                if not _aplicar_migrations(db_path):
                    return None
                DatabaseManager.conectar_empresa(db_path)

            tela_login = LoginView(root, empresa)
            root.wait_window(tela_login)

            if not getattr(tela_login, "voltou", False):
                break

        return empresa if Session.ativa() else None

    empresa = _executar_login()
    if not empresa:
        root.destroy()
        return

    # ── Servidor garçom (Wi-Fi local) ─────────────────────────
    if not Session.is_admin_global():
        try:
            import socket as _socket
            from garcom.garcom_server import iniciar as _iniciar_garcom, consumir_notificacoes, set_empresa_nome

            _iniciar_garcom(porta=5000)
            set_empresa_nome(empresa.get("razao_social", ""))

            # Descobrir IP local
            _s = _socket.socket(_socket.AF_INET, _socket.SOCK_DGRAM)
            try:
                _s.connect(("8.8.8.8", 80))
                _ip = _s.getsockname()[0]
            except Exception:
                _ip = "127.0.0.1"
            finally:
                _s.close()
            print(f"[garcom] App garçom: http://{_ip}:5000/garcom/")

            def _popup_garcom(n: dict):
                """Exibe notificação de novo pedido do garçom."""
                from models.mesa import Mesa
                mesa = Mesa.buscar_por_id(n.get("mesa_id")) or {}
                popup = tk.Toplevel(root)
                popup.overrideredirect(True)
                popup.configure(bg="#1a73e8")
                popup.attributes("-topmost", True)
                sw = popup.winfo_screenwidth()
                popup.geometry(f"300x90+{sw - 316}+20")
                tk.Label(popup,
                         text=f"🔔  Mesa {mesa.get('numero','?')} — {n['produto_nome']}",
                         font=("Segoe UI", 11, "bold"),
                         bg="#1a73e8", fg="white").pack(anchor="w", padx=14, pady=(12, 2))
                tk.Label(popup,
                         text=f"Qtd: {n['quantidade']}  •  {n['garcom_nome']}  {n['hora']}",
                         font=("Segoe UI", 9),
                         bg="#1a73e8", fg="#cce0ff").pack(anchor="w", padx=14)
                popup.after(4000, popup.destroy)

            def _poll_garcom():
                try:
                    for n in consumir_notificacoes():
                        _popup_garcom(n)
                except Exception:
                    pass
                root.after(3000, _poll_garcom)

            root.after(3000, _poll_garcom)
        except Exception as _e:
            print(f"[garcom] Servidor não iniciou: {_e}")

    # Janela principal
    from views.main.main_window import MainWindow

    def _on_logout():
        """Limpa a janela principal e retorna à tela de login."""
        for w in root.winfo_children():
            w.destroy()
        root.withdraw()

        nova_empresa = _executar_login()
        if not nova_empresa:
            root.destroy()
            return

        root.deiconify()
        MainWindow(root, on_logout=_on_logout)

    def _popup_atualizacao(info: dict) -> None:
        """Exibe janela de atualização disponível."""
        from tkinter import ttk
        from updater.updater import Updater

        obrigatoria = str(info.get("obrigatoria", "false")).lower() == "true"

        win = tk.Toplevel(root)
        win.title("Atualização disponível")
        win.resizable(False, False)
        win.grab_set()
        win.configure(bg="#F0F2F5")
        win.geometry("480x360")
        win.transient(root)

        if obrigatoria:
            win.protocol("WM_DELETE_WINDOW", lambda: None)  # bloqueia fechar

        # ── Header ───────────────────────────────────────────────
        hdr = tk.Frame(win, bg="#2E86C1", height=56)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="🔄  Atualização disponível",
                 font=("Segoe UI", 13, "bold"),
                 bg="#2E86C1", fg="white").pack(side="left", padx=20, pady=14)

        # ── Corpo ─────────────────────────────────────────────────
        body = tk.Frame(win, bg="#F0F2F5", padx=24, pady=16)
        body.pack(fill="both", expand=True)

        versao_nova  = info.get("versao", "?")
        versao_atual = Updater().versao_atual()
        tk.Label(body,
                 text=f"Versão atual: {versao_atual}   →   Nova versão: {versao_nova}",
                 font=("Segoe UI", 11, "bold"), bg="#F0F2F5", fg="#1A2332").pack(anchor="w")

        if obrigatoria:
            tk.Label(body, text="⚠  Esta atualização é obrigatória.",
                     font=("Segoe UI", 10), bg="#F0F2F5", fg="#C0392B").pack(anchor="w", pady=(4, 0))

        novidades = info.get("novidades", "").strip()
        if novidades:
            tk.Label(body, text="Novidades:", font=("Segoe UI", 10, "bold"),
                     bg="#F0F2F5", fg="#1A2332").pack(anchor="w", pady=(12, 4))
            txt = tk.Text(body, height=6, font=("Segoe UI", 10),
                          bg="white", fg="#1A2332", relief="flat",
                          highlightthickness=1, highlightbackground="#D5D8DC",
                          wrap="word", state="normal", cursor="arrow")
            txt.insert("1.0", novidades)
            txt.configure(state="disabled")
            txt.pack(fill="x")

        # ── Progresso ─────────────────────────────────────────────
        frm_prog = tk.Frame(body, bg="#F0F2F5")
        frm_prog.pack(fill="x", pady=(12, 0))
        lbl_prog = tk.Label(frm_prog, text="", font=("Segoe UI", 9),
                            bg="#F0F2F5", fg="#6B7A8D")
        lbl_prog.pack(anchor="w")
        progressbar = ttk.Progressbar(frm_prog, mode="determinate", length=430)
        progressbar.pack(fill="x", pady=(4, 0))
        frm_prog.pack_forget()  # esconde até iniciar

        # ── Botões ────────────────────────────────────────────────
        frm_btn = tk.Frame(win, bg="#F0F2F5", padx=24, pady=12)
        frm_btn.pack(fill="x")

        def _iniciar_atualizacao():
            btn_atualizar.configure(state="disabled")
            btn_nao.configure(state="disabled")
            frm_prog.pack(fill="x", pady=(12, 0))
            lbl_prog.configure(text="Baixando atualização...")

            def _progresso(pct: int):
                progressbar["value"] = pct
                lbl_prog.configure(text=f"Baixando... {pct}%")
                win.update_idletasks()

            import threading
            def _baixar():
                try:
                    Updater().baixar_e_aplicar(info["url_download"], _progresso)
                except Exception as e:
                    root.after(0, lambda: (
                        tk.messagebox.showerror("Erro ao atualizar", str(e), parent=win),
                        win.destroy(),
                    ))
            threading.Thread(target=_baixar, daemon=True).start()

        btn_atualizar = tk.Button(
            frm_btn, text="Atualizar agora",
            font=("Segoe UI", 10, "bold"), bg="#2E86C1", fg="white",
            relief="flat", cursor="hand2", padx=18, pady=8,
            command=_iniciar_atualizacao,
        )
        btn_atualizar.pack(side="left")

        btn_nao = tk.Button(
            frm_btn, text="Agora não",
            font=("Segoe UI", 10), bg="#F0F2F5", fg="#6B7A8D",
            relief="flat", cursor="hand2", padx=18, pady=8,
            state="disabled" if obrigatoria else "normal",
            command=win.destroy,
        )
        btn_nao.pack(side="left", padx=(8, 0))

        if obrigatoria:
            tk.Label(frm_btn, text="Atualização obrigatória — não pode ser ignorada.",
                     font=("Segoe UI", 9), bg="#F0F2F5", fg="#C0392B").pack(side="left", padx=(12, 0))

    def _iniciar_verificacao_atualizacao() -> None:
        """Verifica atualização em background e agenda popup se houver nova versão."""
        import threading

        def _tarefa():
            from updater.updater import Updater
            info = Updater().verificar()
            if info:
                root.after(0, lambda: _popup_atualizacao(info))

        threading.Thread(target=_tarefa, daemon=True).start()

    root.deiconify()
    MainWindow(root, on_logout=_on_logout)
    _iniciar_verificacao_atualizacao()
    root.mainloop()


if __name__ == "__main__":
    main()