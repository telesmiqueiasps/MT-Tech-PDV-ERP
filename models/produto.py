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
            sql += " AND (p.nome LIKE ? OR p.codigo LIKE ? OR p.codigo_barras LIKE ? OR p.ean LIKE ?)"
            params += [f"%{busca}%"] * 4
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
            """, (id,)
        )

    @staticmethod
    def buscar_por_codigo(codigo: str) -> dict | None:
        return Produto._db().fetchone(
            "SELECT * FROM produtos WHERE (codigo=? OR codigo_barras=? OR ean=?) AND ativo=1",
            (codigo, codigo, codigo)
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
            INSERT INTO produtos (
                codigo, codigo_barras, ean, nome, categoria_id,
                ncm, cest, cfop_padrao, cst_icms, csosn,
                cst_pis, cst_cofins, cst_ipi, origem,
                aliq_icms, aliq_ipi, aliq_pis, aliq_cofins,
                unidade, unidade_trib, qtd_trib, preco_trib,
                peso_bruto, peso_liquido,
                preco_custo, preco_venda, margem,
                estoque_atual, estoque_min, estoque_max
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            _campos_produto(dados)
        )

    @staticmethod
    def atualizar(id: int, dados: dict):
        Produto._db().execute(
            """
            UPDATE produtos SET
                codigo=?, codigo_barras=?, ean=?, nome=?, categoria_id=?,
                ncm=?, cest=?, cfop_padrao=?, cst_icms=?, csosn=?,
                cst_pis=?, cst_cofins=?, cst_ipi=?, origem=?,
                aliq_icms=?, aliq_ipi=?, aliq_pis=?, aliq_cofins=?,
                unidade=?, unidade_trib=?, qtd_trib=?, preco_trib=?,
                peso_bruto=?, peso_liquido=?,
                preco_custo=?, preco_venda=?, margem=?,
                estoque_min=?, estoque_max=?
            WHERE id=?
            """,
            _campos_produto(dados, update=True) + (id,)
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


def _campos_produto(d: dict, update: bool = False) -> tuple:
    base = (
        d.get("codigo") or None,
        d.get("codigo_barras") or None,
        d.get("ean") or None,
        d["nome"],
        d.get("categoria_id") or None,
        d.get("ncm") or None,
        d.get("cest") or None,
        d.get("cfop_padrao") or None,
        d.get("cst_icms") or None,
        d.get("csosn") or None,
        d.get("cst_pis", "07"),
        d.get("cst_cofins", "07"),
        d.get("cst_ipi") or None,
        int(d.get("origem", 0)),
        float(d.get("aliq_icms", 0)),
        float(d.get("aliq_ipi", 0)),
        float(d.get("aliq_pis", 0)),
        float(d.get("aliq_cofins", 0)),
        d.get("unidade", "UN"),
        d.get("unidade_trib") or d.get("unidade", "UN"),
        float(d.get("qtd_trib", 1)),
        float(d.get("preco_trib", 0)),
        float(d.get("peso_bruto", 0)),
        float(d.get("peso_liquido", 0)),
        float(d.get("preco_custo", 0)),
        float(d.get("preco_venda", 0)),
        float(d.get("margem", 0)),
    )
    if not update:
        base += (float(d.get("estoque_atual", 0)),)
    base += (
        float(d.get("estoque_min", 0)),
        float(d.get("estoque_max", 0)),
    )
    return base


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