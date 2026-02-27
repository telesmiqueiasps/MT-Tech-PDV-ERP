from core.database import DatabaseManager

IND_IE = {
    1: "1 — Contribuinte ICMS",
    2: "2 — Contribuinte Isento",
    9: "9 — Não Contribuinte",
}

TIPO_PESSOA = {
    "F": "Pessoa Física",
    "J": "Pessoa Jurídica",
    "E": "Estrangeiro",
}


class Cliente:
    @staticmethod
    def _db():
        return DatabaseManager.empresa()

    @staticmethod
    def listar(busca: str = "") -> list[dict]:
        sql    = "SELECT * FROM clientes WHERE ativo=1"
        params = []
        if busca:
            sql += " AND (nome LIKE ? OR cpf LIKE ? OR cnpj LIKE ? OR telefone LIKE ?)"
            params = [f"%{busca}%"] * 4
        sql += " ORDER BY nome"
        return Cliente._db().fetchall(sql, tuple(params))

    @staticmethod
    def buscar_por_id(id: int) -> dict | None:
        return Cliente._db().fetchone(
            "SELECT * FROM clientes WHERE id=?", (id,)
        )

    @staticmethod
    def criar(dados: dict) -> int:
        return Cliente._db().execute(
            """
            INSERT INTO clientes (
                nome, tipo_pessoa, cpf, cnpj, rg, ie, ind_ie, im,
                suframa, email, telefone,
                cep, endereco, numero, complemento, bairro,
                cidade, cod_municipio_ibge, estado,
                cod_pais, nome_pais, limite_credito
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            Cliente._tupla(dados)
        )

    @staticmethod
    def atualizar(id: int, dados: dict):
        Cliente._db().execute(
            """
            UPDATE clientes SET
                nome=?, tipo_pessoa=?, cpf=?, cnpj=?, rg=?, ie=?, ind_ie=?, im=?,
                suframa=?, email=?, telefone=?,
                cep=?, endereco=?, numero=?, complemento=?, bairro=?,
                cidade=?, cod_municipio_ibge=?, estado=?,
                cod_pais=?, nome_pais=?, limite_credito=?
            WHERE id=?
            """,
            Cliente._tupla(dados) + (id,)
        )

    @staticmethod
    def _tupla(d: dict) -> tuple:
        return (
            d["nome"],
            d.get("tipo_pessoa", "F"),
            d.get("cpf") or None,
            d.get("cnpj") or None,
            d.get("rg") or None,
            d.get("ie") or None,
            int(d.get("ind_ie", 9)),
            d.get("im") or None,
            d.get("suframa") or None,
            d.get("email") or None,
            d.get("telefone") or None,
            d.get("cep") or None,
            d.get("endereco") or None,
            d.get("numero") or None,
            d.get("complemento") or None,
            d.get("bairro") or None,
            d.get("cidade") or None,
            d.get("cod_municipio_ibge") or None,
            d.get("estado") or None,
            d.get("cod_pais", "1058"),
            d.get("nome_pais", "Brasil"),
            float(d.get("limite_credito") or 0),
        )

    @staticmethod
    def desativar(id: int):
        Cliente._db().execute(
            "UPDATE clientes SET ativo=0 WHERE id=?", (id,)
        )

    @staticmethod
    def doc_existe(campo: str, valor: str, ignorar_id: int = None) -> bool:
        if not valor:
            return False
        sql = f"SELECT id FROM clientes WHERE {campo}=? AND ativo=1"
        params = [valor]
        if ignorar_id:
            sql += " AND id!=?"
            params.append(ignorar_id)
        return Cliente._db().fetchone(sql, tuple(params)) is not None