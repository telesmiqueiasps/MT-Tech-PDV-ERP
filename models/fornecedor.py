from core.database import DatabaseManager

REGIMES = {
    1: "1 — Simples Nacional",
    2: "2 — Simples Nacional Excesso",
    3: "3 — Regime Normal",
}

IND_IE = {
    1: "1 — Contribuinte ICMS",
    2: "2 — Contribuinte Isento",
    9: "9 — Não Contribuinte",
}


class Fornecedor:
    @staticmethod
    def _db():
        return DatabaseManager.empresa()

    @staticmethod
    def listar(busca: str = "") -> list[dict]:
        sql    = "SELECT * FROM fornecedores WHERE ativo=1"
        params = []
        if busca:
            sql += " AND (nome LIKE ? OR cnpj LIKE ? OR cpf LIKE ? OR telefone LIKE ?)"
            params = [f"%{busca}%"] * 4
        sql += " ORDER BY nome"
        return Fornecedor._db().fetchall(sql, tuple(params))

    @staticmethod
    def buscar_por_id(id: int) -> dict | None:
        return Fornecedor._db().fetchone(
            "SELECT * FROM fornecedores WHERE id=?", (id,)
        )

    @staticmethod
    def criar(dados: dict) -> int:
        return Fornecedor._db().execute(
            """
            INSERT INTO fornecedores (
                nome, tipo_pessoa, cpf, cnpj, ie, ind_ie, im,
                suframa, email, telefone, contato, cnae,
                regime_tributario, observacoes,
                cep, endereco, numero, complemento, bairro,
                cidade, cod_municipio_ibge, estado,
                cod_pais, nome_pais
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            Fornecedor._tupla(dados)
        )

    @staticmethod
    def atualizar(id: int, dados: dict):
        Fornecedor._db().execute(
            """
            UPDATE fornecedores SET
                nome=?, tipo_pessoa=?, cpf=?, cnpj=?, ie=?, ind_ie=?, im=?,
                suframa=?, email=?, telefone=?, contato=?, cnae=?,
                regime_tributario=?, observacoes=?,
                cep=?, endereco=?, numero=?, complemento=?, bairro=?,
                cidade=?, cod_municipio_ibge=?, estado=?,
                cod_pais=?, nome_pais=?
            WHERE id=?
            """,
            Fornecedor._tupla(dados) + (id,)
        )

    @staticmethod
    def _tupla(d: dict) -> tuple:
        return (
            d["nome"],
            d.get("tipo_pessoa", "J"),
            d.get("cpf") or None,
            d.get("cnpj") or None,
            d.get("ie") or None,
            int(d.get("ind_ie", 1)),
            d.get("im") or None,
            d.get("suframa") or None,
            d.get("email") or None,
            d.get("telefone") or None,
            d.get("contato") or None,
            d.get("cnae") or None,
            int(d.get("regime_tributario", 1)),
            d.get("observacoes") or None,
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
        )

    @staticmethod
    def desativar(id: int):
        Fornecedor._db().execute(
            "UPDATE fornecedores SET ativo=0 WHERE id=?", (id,)
        )