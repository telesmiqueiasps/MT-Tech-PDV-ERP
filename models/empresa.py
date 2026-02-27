from core.database import DatabaseManager

REGIMES = {
    1: "Simples Nacional",
    2: "Simples Nacional — Excesso Sublimite",
    3: "Regime Normal",
}

AMBIENTES = {
    1: "Produção",
    2: "Homologação",
}


class Empresa:
    @staticmethod
    def _db():
        return DatabaseManager.master()

    @staticmethod
    def listar() -> list[dict]:
        return Empresa._db().fetchall(
            "SELECT * FROM empresas WHERE ativo=1 ORDER BY nome"
        )

    @staticmethod
    def buscar_por_id(id: int) -> dict | None:
        return Empresa._db().fetchone(
            "SELECT * FROM empresas WHERE id=?", (id,)
        )

    @staticmethod
    def criar(dados: dict) -> int:
        from database.seeds.seed import criar_empresa
        return criar_empresa(
            dados["nome"],
            dados.get("cnpj", ""),
            dados.get("razao_social", ""),
        )

    @staticmethod
    def atualizar(id: int, dados: dict):
        Empresa._db().execute(
            """
            UPDATE empresas SET
                nome=?, razao_social=?, cnpj=?, ie=?, im=?, cnae=?,
                regime_tributario=?, crt=?, email=?, telefone=?,
                cep=?, endereco=?, numero=?, complemento=?, bairro=?,
                cidade=?, cod_municipio_ibge=?, estado=?,
                cod_pais=?, nome_pais=?,
                serie_nfe=?, prox_nfe=?, serie_nfce=?, prox_nfce=?,
                serie_nfse=?, prox_nfse=?, serie_cte=?, prox_cte=?,
                ambiente_fiscal=?, cert_path=?, cert_senha=?
            WHERE id=?
            """,
            (
                dados.get("nome"),
                dados.get("razao_social"),
                dados.get("cnpj"),
                dados.get("ie"),
                dados.get("im"),
                dados.get("cnae"),
                int(dados.get("regime_tributario", 1)),
                int(dados.get("crt", 1)),
                dados.get("email"),
                dados.get("telefone"),
                dados.get("cep"),
                dados.get("endereco"),
                dados.get("numero"),
                dados.get("complemento"),
                dados.get("bairro"),
                dados.get("cidade"),
                dados.get("cod_municipio_ibge"),
                dados.get("estado"),
                dados.get("cod_pais", "1058"),
                dados.get("nome_pais", "Brasil"),
                int(dados.get("serie_nfe", 1)),
                int(dados.get("prox_nfe", 1)),
                int(dados.get("serie_nfce", 1)),
                int(dados.get("prox_nfce", 1)),
                int(dados.get("serie_nfse", 1)),
                int(dados.get("prox_nfse", 1)),
                int(dados.get("serie_cte", 1)),
                int(dados.get("prox_cte", 1)),
                int(dados.get("ambiente_fiscal", 2)),
                dados.get("cert_path"),
                dados.get("cert_senha"),
                id,
            )
        )

    @staticmethod
    def desativar(id: int):
        Empresa._db().execute(
            "UPDATE empresas SET ativo=0 WHERE id=?", (id,)
        )