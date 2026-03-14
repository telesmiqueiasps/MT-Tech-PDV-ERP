"""
NfceConfig — lê e grava configuração NFC-e diretamente na tabela
`empresas` do banco master, eliminando duplicidade com nfce_config.

Mapeamento de campos master → chaves usadas no fiscal:
  empresas.ambiente_fiscal  → config["ambiente"]
  empresas.serie_nfce       → config["serie"]
  empresas.prox_nfce        → config["proximo_numero"]
  empresas.id_csc           → config["id_csc"] / config["csc_id"]
  empresas.csc_token        → config["csc_token"]
  empresas.cert_path        → config["cert_path"]
  empresas.cert_senha       → config["cert_senha"]
"""
from core.database import DatabaseManager
from core.session import Session


class NfceConfig:

    @staticmethod
    def _empresa_id() -> int:
        return Session.empresa()["id"]

    @staticmethod
    def carregar() -> dict | None:
        """Retorna configuração NFC-e da empresa atual (lida do master)."""
        row = DatabaseManager.master().fetchone(
            "SELECT * FROM empresas WHERE id=?", (NfceConfig._empresa_id(),)
        )
        if not row:
            return None
        return {
            "ambiente":        row.get("ambiente_fiscal", 2),
            "serie":           row.get("serie_nfce", 1),
            "proximo_numero":  row.get("prox_nfce", 1),
            "id_csc":          row.get("id_csc") or "",
            "csc_id":          row.get("id_csc") or "",
            "csc_token":       row.get("csc_token") or "",
            "cert_path":       row.get("cert_path") or "",
            "cert_senha":      row.get("cert_senha") or "",
            "versao_nfe":      "4.00",
            "ativo":           row.get("ativo", 1),
        }

    @staticmethod
    def salvar(dados: dict) -> None:
        """Persiste configuração NFC-e no master (tabela empresas)."""
        campos_map = {
            "ambiente":       "ambiente_fiscal",
            "serie":          "serie_nfce",
            "proximo_numero": "prox_nfce",
            "id_csc":         "id_csc",
            "csc_token":      "csc_token",
            "cert_path":      "cert_path",
            "cert_senha":     "cert_senha",
        }
        sets  = []
        vals  = []
        for chave_config, coluna in campos_map.items():
            if chave_config in dados:
                sets.append(f"{coluna}=?")
                vals.append(dados[chave_config])
        if not sets:
            return
        vals.append(NfceConfig._empresa_id())
        DatabaseManager.master().execute(
            f"UPDATE empresas SET {', '.join(sets)} WHERE id=?",
            tuple(vals),
        )

    @staticmethod
    def proximo_numero() -> int:
        """Retorna e incrementa atomicamente o próximo número da NFC-e."""
        db  = DatabaseManager.master()
        eid = NfceConfig._empresa_id()
        db.execute(
            "UPDATE empresas SET prox_nfce = prox_nfce + 1 WHERE id=?", (eid,)
        )
        row = db.fetchone("SELECT prox_nfce FROM empresas WHERE id=?", (eid,))
        return (row["prox_nfce"] - 1) if row else 1

    @staticmethod
    def ambiente_label() -> str:
        cfg = NfceConfig.carregar()
        if cfg and cfg.get("ambiente") == 1:
            return "Produção"
        return "Homologação"
