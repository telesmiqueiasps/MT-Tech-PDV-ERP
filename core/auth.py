import hashlib
import secrets
from core.database import DatabaseManager
from core.session import Session


class AuthError(Exception):
    pass


def gerar_hash(senha: str) -> str:
    salt = secrets.token_hex(16)
    h    = hashlib.sha256(f"{salt}{senha}".encode()).hexdigest()
    return f"{salt}${h}"


def verificar_senha(senha: str, senha_hash: str) -> bool:
    try:
        salt, _ = senha_hash.split("$")
        h = hashlib.sha256(f"{salt}{senha}".encode()).hexdigest()
        return f"{salt}${h}" == senha_hash
    except Exception:
        return False


class Auth:
    @classmethod
    def login_admin_global(cls, login: str, senha: str):
        db  = DatabaseManager.master()
        row = db.fetchone(
            "SELECT * FROM admin_global WHERE login = ? AND ativo = 1", (login,)
        )
        if not row or not verificar_senha(senha, row["senha_hash"]):
            raise AuthError("Login ou senha inválidos.")

        Session.iniciar(
            usuario    = {**row, "is_admin_global": True},
            empresa    = {"id": 0, "nome": "Administração Global"},
            permissoes = {},
        )

    @classmethod
    def login_empresa(cls, login: str, senha: str, empresa: dict):
        db  = DatabaseManager.empresa()
        row = db.fetchone(
            """
            SELECT u.*, p.nome as perfil_nome
            FROM usuarios u
            LEFT JOIN perfis p ON p.id = u.perfil_id
            WHERE u.login = ? AND u.ativo = 1
            """,
            (login,),
        )
        if not row or not verificar_senha(senha, row["senha_hash"]):
            raise AuthError("Login ou senha inválidos.")

        permissoes = cls._carregar_permissoes(row["perfil_id"])

        Session.iniciar(
            usuario    = {**row, "is_admin_global": False},
            empresa    = empresa,
            permissoes = permissoes,
        )

    @classmethod
    def _carregar_permissoes(cls, perfil_id: int) -> dict[str, bool]:
        rows = DatabaseManager.empresa().fetchall(
            "SELECT modulo, acao FROM permissoes WHERE perfil_id = ? AND permitido = 1",
            (perfil_id,),
        )
        return {f"{r['modulo']}:{r['acao']}": True for r in rows}

    @classmethod
    def logout(cls):
        Session.encerrar()
        DatabaseManager.fechar_empresa()