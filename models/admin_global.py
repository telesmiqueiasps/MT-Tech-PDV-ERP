from core.database import DatabaseManager
from core.auth import gerar_hash


class AdminGlobalError(Exception):
    pass


class AdminGlobal:
    @staticmethod
    def listar() -> list[dict]:
        return DatabaseManager.master().fetchall(
            "SELECT id, login, nome, ativo, criado_em "
            "FROM admin_global ORDER BY criado_em"
        )

    @staticmethod
    def criar(login: str, nome: str, senha: str) -> int:
        login = login.strip()
        nome  = nome.strip()
        if not login:
            raise AdminGlobalError("O login não pode ser vazio.")
        if len(senha) < 6:
            raise AdminGlobalError("A senha deve ter no mínimo 6 caracteres.")
        db = DatabaseManager.master()
        if db.fetchone("SELECT 1 FROM admin_global WHERE login = ?", (login,)):
            raise AdminGlobalError(f"O login '{login}' já está em uso.")
        return db.execute(
            "INSERT INTO admin_global (login, nome, senha_hash) VALUES (?, ?, ?)",
            (login, nome, gerar_hash(senha)),
        )

    @staticmethod
    def alterar_senha(admin_id: int, senha_nova: str) -> None:
        if len(senha_nova) < 6:
            raise AdminGlobalError("A senha deve ter no mínimo 6 caracteres.")
        DatabaseManager.master().execute(
            "UPDATE admin_global SET senha_hash = ? WHERE id = ?",
            (gerar_hash(senha_nova), admin_id),
        )

    @staticmethod
    def alterar_nome(admin_id: int, nome: str) -> None:
        DatabaseManager.master().execute(
            "UPDATE admin_global SET nome = ? WHERE id = ?",
            (nome.strip(), admin_id),
        )

    @staticmethod
    def desativar(admin_id: int) -> None:
        db = DatabaseManager.master()
        total = db.fetchone(
            "SELECT COUNT(*) AS c FROM admin_global WHERE ativo = 1"
        )["c"]
        if total <= 1:
            raise AdminGlobalError(
                "Não é possível desativar o único administrador ativo."
            )
        db.execute("UPDATE admin_global SET ativo = 0 WHERE id = ?", (admin_id,))

    @staticmethod
    def reativar(admin_id: int) -> None:
        DatabaseManager.master().execute(
            "UPDATE admin_global SET ativo = 1 WHERE id = ?", (admin_id,)
        )

    @staticmethod
    def login_existe(login: str, ignorar_id: int | None = None) -> bool:
        db = DatabaseManager.master()
        if ignorar_id is not None:
            row = db.fetchone(
                "SELECT 1 FROM admin_global WHERE login = ? AND id != ?",
                (login, ignorar_id),
            )
        else:
            row = db.fetchone(
                "SELECT 1 FROM admin_global WHERE login = ?", (login,)
            )
        return row is not None
