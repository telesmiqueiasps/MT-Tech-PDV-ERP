from core.database import DatabaseManager


class Municipio:
    @staticmethod
    def _db():
        return DatabaseManager.master()

    @staticmethod
    def buscar(termo: str, uf: str = "") -> list[dict]:
        """Retorna até 50 municípios que contenham o termo no nome."""
        sql    = "SELECT * FROM municipios WHERE nome_municipio LIKE ?"
        params = [f"%{termo}%"]
        if uf:
            sql += " AND nome_uf = ?"
            params.append(uf.upper())
        sql += " ORDER BY nome_uf, nome_municipio LIMIT 50"
        return Municipio._db().fetchall(sql, tuple(params))

    @staticmethod
    def buscar_por_codigo(cod_municipio: str) -> dict | None:
        return Municipio._db().fetchone(
            "SELECT * FROM municipios WHERE cod_municipio = ?", (cod_municipio,)
        )

    @staticmethod
    def ufs() -> list[str]:
        rows = Municipio._db().fetchall(
            "SELECT DISTINCT uf FROM municipios ORDER BY uf"
        )
        return [r["uf"] for r in rows]