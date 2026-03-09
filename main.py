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

    while True:
        tela_empresa = SelecionarEmpresa(root)
        root.wait_window(tela_empresa)

        empresa = tela_empresa.empresa_selecionada
        if not empresa:
            root.destroy()
            return

        if empresa["id"] != 0:
            DatabaseManager.conectar_empresa(Path(empresa["db_path"]))

        tela_login = LoginView(root, empresa)
        root.wait_window(tela_login)

        if not getattr(tela_login, "voltou", False):
            break

    if not Session.ativa():
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
    root.deiconify()
    MainWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()