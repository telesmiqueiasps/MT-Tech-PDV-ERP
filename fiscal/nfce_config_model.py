from core.database import DatabaseManager


class NfceConfig:
    @staticmethod
    def _db():
        return DatabaseManager.empresa()

    @staticmethod
    def carregar() -> dict | None:
        return NfceConfig._db().fetchone("SELECT * FROM nfce_config WHERE ativo=1 LIMIT 1")

    @staticmethod
    def salvar(dados: dict) -> None:
        db = NfceConfig._db()
        atual = db.fetchone("SELECT id FROM nfce_config LIMIT 1")
        campos = ["ambiente", "serie", "csc_id", "csc_token", "cert_path",
                  "cert_senha", "versao_nfe", "id_csc", "ativo"]
        if atual:
            sets = ", ".join(f"{c}=?" for c in campos if c in dados)
            sets += ", atualizado_em=datetime('now','localtime')"
            vals = [dados[c] for c in campos if c in dados] + [atual["id"]]
            db.execute(f"UPDATE nfce_config SET {sets} WHERE id=?", tuple(vals))
        else:
            cols = list(dados.keys())
            placeholders = ", ".join("?" * len(cols))
            db.execute(
                f"INSERT INTO nfce_config ({', '.join(cols)}) VALUES ({placeholders})",
                tuple(dados.values()),
            )

    @staticmethod
    def proximo_numero() -> int:
        """Retorna e incrementa atomicamente o próximo número da NFC-e."""
        db = NfceConfig._db()
        db.execute("UPDATE nfce_config SET proximo_numero = proximo_numero + 1 WHERE ativo=1")
        row = db.fetchone("SELECT proximo_numero FROM nfce_config WHERE ativo=1 LIMIT 1")
        return (row["proximo_numero"] - 1) if row else 1

    @staticmethod
    def ambiente_label() -> str:
        cfg = NfceConfig.carregar()
        if cfg and cfg.get("ambiente") == 1:
            return "Produção"
        return "Homologação"
