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

    # Janela principal
    from views.main.main_window import MainWindow
    root.deiconify()
    MainWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()