from core.database import DatabaseManager


class Produto:
    @staticmethod
    def _db():
        return DatabaseManager.empresa()

    @staticmethod
    def listar(busca: str = "", categoria_id: int = None) -> list[dict]:
        sql = """
            SELECT p.*, c.nome as categoria_nome
            FROM produtos p
            LEFT JOIN categorias c ON c.id = p.categoria_id
            WHERE p.ativo = 1
        """
        params = []
        if busca:
            sql += " AND (p.nome LIKE ? OR p.codigo LIKE ? OR p.codigo_barras LIKE ?)"
            params += [f"%{busca}%", f"%{busca}%", f"%{busca}%"]
        if categoria_id:
            sql += " AND p.categoria_id = ?"
            params.append(categoria_id)
        sql += " ORDER BY p.nome"
        return Produto._db().fetchall(sql, tuple(params))

    @staticmethod
    def buscar_por_id(id: int) -> dict | None:
        return Produto._db().fetchone(
            """
            SELECT p.*, c.nome as categoria_nome
            FROM produtos p
            LEFT JOIN categorias c ON c.id = p.categoria_id
            WHERE p.id = ?
            """,
            (id,)
        )

    @staticmethod
    def buscar_por_codigo(codigo: str) -> dict | None:
        return Produto._db().fetchone(
            "SELECT * FROM produtos WHERE (codigo=? OR codigo_barras=?) AND ativo=1",
            (codigo, codigo)
        )


    @staticmethod
    def proximo_codigo() -> str:
        row = Produto._db().fetchone(
            "SELECT MAX(CAST(codigo AS INTEGER)) as ultimo FROM produtos WHERE codigo GLOB '[0-9]*'"
        )
        ultimo = row["ultimo"] if row and row["ultimo"] else 0
        return str(ultimo + 1).zfill(6)

    @staticmethod
    def criar(dados: dict) -> int:
        return Produto._db().execute(
            """
            INSERT INTO produtos
                (codigo, codigo_barras, nome, categoria_id, ncm, unidade,
                 preco_custo, preco_venda, margem,
                 estoque_atual, estoque_min, estoque_max)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                dados.get("codigo") or None,
                dados.get("codigo_barras") or None,
                dados["nome"],
                dados.get("categoria_id") or None,
                dados.get("ncm") or None,
                dados.get("unidade", "UN"),
                float(dados.get("preco_custo", 0)),
                float(dados.get("preco_venda", 0)),
                float(dados.get("margem", 0)),
                float(dados.get("estoque_atual", 0)),
                float(dados.get("estoque_min", 0)),
                float(dados.get("estoque_max", 0)),
            )
        )

    @staticmethod
    def atualizar(id: int, dados: dict):
        Produto._db().execute(
            """
            UPDATE produtos SET
                codigo=?, codigo_barras=?, nome=?, categoria_id=?, ncm=?, unidade=?,
                preco_custo=?, preco_venda=?, margem=?,
                estoque_min=?, estoque_max=?
            WHERE id=?
            """,
            (
                dados.get("codigo") or None,
                dados.get("codigo_barras") or None,
                dados["nome"],
                dados.get("categoria_id") or None,
                dados.get("ncm") or None,
                dados.get("unidade", "UN"),
                float(dados.get("preco_custo", 0)),
                float(dados.get("preco_venda", 0)),
                float(dados.get("margem", 0)),
                float(dados.get("estoque_min", 0)),
                float(dados.get("estoque_max", 0)),
                id,
            )
        )

    @staticmethod
    def desativar(id: int):
        Produto._db().execute("UPDATE produtos SET ativo=0 WHERE id=?", (id,))

    @staticmethod
    def codigo_existe(codigo: str, ignorar_id: int = None) -> bool:
        if ignorar_id:
            row = Produto._db().fetchone(
                "SELECT id FROM produtos WHERE codigo=? AND id!=? AND ativo=1",
                (codigo, ignorar_id)
            )
        else:
            row = Produto._db().fetchone(
                "SELECT id FROM produtos WHERE codigo=? AND ativo=1", (codigo,)
            )
        return row is not None


class Categoria:
    @staticmethod
    def _db():
        return DatabaseManager.empresa()

    @staticmethod
    def listar() -> list[dict]:
        return Categoria._db().fetchall(
            "SELECT * FROM categorias WHERE ativo=1 ORDER BY nome"
        )

    @staticmethod
    def criar(nome: str) -> int:
        return Categoria._db().execute(
            "INSERT INTO categorias (nome) VALUES (?)", (nome,)
        )

    @staticmethod
    def atualizar(id: int, nome: str):
        Categoria._db().execute(
            "UPDATE categorias SET nome=? WHERE id=?", (nome, id)
        )

    @staticmethod
    def desativar(id: int):
        Categoria._db().execute(
            "UPDATE categorias SET ativo=0 WHERE id=?", (id,)
        )

    @staticmethod
    def em_uso(id: int) -> bool:
        row = Categoria._db().fetchone(
            "SELECT COUNT(*) as total FROM produtos WHERE categoria_id=? AND ativo=1", (id,)
        )
        return row["total"] > 0