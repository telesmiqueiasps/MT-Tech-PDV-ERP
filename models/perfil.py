from core.database import DatabaseManager
from config import PERMISSOES


class Perfil:
    @staticmethod
    def _db():
        return DatabaseManager.empresa()

    @staticmethod
    def listar() -> list[dict]:
        return Perfil._db().fetchall(
            "SELECT * FROM perfis WHERE ativo=1 ORDER BY nome"
        )

    @staticmethod
    def buscar_por_id(id: int) -> dict | None:
        return Perfil._db().fetchone(
            "SELECT * FROM perfis WHERE id=?", (id,)
        )

    @staticmethod
    def buscar_permissoes(perfil_id: int) -> dict[str, bool]:
        rows = Perfil._db().fetchall(
            "SELECT modulo, acao FROM permissoes WHERE perfil_id=? AND permitido=1",
            (perfil_id,)
        )
        return {f"{r['modulo']}:{r['acao']}": True for r in rows}

    @staticmethod
    def criar(nome: str, descricao: str = "") -> int:
        return Perfil._db().execute(
            "INSERT INTO perfis (nome, descricao) VALUES (?,?)",
            (nome, descricao)
        )

    @staticmethod
    def atualizar(id: int, nome: str, descricao: str = ""):
        Perfil._db().execute(
            "UPDATE perfis SET nome=?, descricao=? WHERE id=?",
            (nome, descricao, id)
        )

    @staticmethod
    def salvar_permissoes(perfil_id: int, permissoes: dict[str, bool]):
        db = Perfil._db()
        db.execute("DELETE FROM permissoes WHERE perfil_id=?", (perfil_id,))
        rows = [
            (perfil_id, chave.split(":")[0], chave.split(":")[1], 1)
            for chave, ok in permissoes.items() if ok
        ]
        if rows:
            db.executemany(
                "INSERT INTO permissoes (perfil_id, modulo, acao, permitido) VALUES (?,?,?,?)",
                rows
            )

    @staticmethod
    def desativar(id: int):
        Perfil._db().execute(
            "UPDATE perfis SET ativo=0 WHERE id=?", (id,)
        )

    @staticmethod
    def em_uso(id: int) -> bool:
        row = Perfil._db().fetchone(
            "SELECT COUNT(*) as total FROM usuarios WHERE perfil_id=? AND ativo=1", (id,)
        )
        return row["total"] > 0