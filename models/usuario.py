from core.database import DatabaseManager
from core.auth import gerar_hash


class Usuario:
    @staticmethod
    def _db():
        return DatabaseManager.empresa()

    @staticmethod
    def listar() -> list[dict]:
        return Usuario._db().fetchall(
            """
            SELECT u.*, p.nome as perfil_nome
            FROM usuarios u
            LEFT JOIN perfis p ON p.id = u.perfil_id
            WHERE u.ativo = 1
            ORDER BY u.nome
            """
        )

    @staticmethod
    def buscar_por_id(id: int) -> dict | None:
        return Usuario._db().fetchone(
            """
            SELECT u.*, p.nome as perfil_nome
            FROM usuarios u
            LEFT JOIN perfis p ON p.id = u.perfil_id
            WHERE u.id = ?
            """,
            (id,)
        )

    @staticmethod
    def criar(nome: str, login: str, senha: str, perfil_id: int) -> int:
        return Usuario._db().execute(
            "INSERT INTO usuarios (nome, login, senha_hash, perfil_id) VALUES (?,?,?,?)",
            (nome, login, gerar_hash(senha), perfil_id),
        )

    @staticmethod
    def atualizar(id: int, nome: str, login: str, perfil_id: int):
        Usuario._db().execute(
            "UPDATE usuarios SET nome=?, login=?, perfil_id=? WHERE id=?",
            (nome, login, perfil_id, id),
        )

    @staticmethod
    def alterar_senha(id: int, nova_senha: str):
        Usuario._db().execute(
            "UPDATE usuarios SET senha_hash=? WHERE id=?",
            (gerar_hash(nova_senha), id),
        )

    @staticmethod
    def desativar(id: int):
        Usuario._db().execute(
            "UPDATE usuarios SET ativo=0 WHERE id=?", (id,)
        )

    @staticmethod
    def login_existe(login: str, ignorar_id: int = None) -> bool:
        if ignorar_id:
            row = Usuario._db().fetchone(
                "SELECT id FROM usuarios WHERE login=? AND id != ? AND ativo=1",
                (login, ignorar_id)
            )
        else:
            row = Usuario._db().fetchone(
                "SELECT id FROM usuarios WHERE login=? AND ativo=1", (login,)
            )
        return row is not None