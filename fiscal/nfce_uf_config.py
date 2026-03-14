"""
NfceUfConfig — lê e grava configuração NFC-e por UF na tabela
`nfce_uf_config` do banco master.

URLs e parâmetros que variam por estado (e que antes estavam hardcoded):
  - c_uf             : código IBGE do estado (ex: '25' para PB)
  - fuso_horario     : offset UTC (ex: '-03:00')
  - url_qrcode_hom   : URL base do QR Code em homologação
  - url_qrcode_prod  : URL base do QR Code em produção
  - ws_*             : URLs dos WebServices SEFAZ (NULL = usar SVRS centralizado)
"""
from core.database import DatabaseManager


# ── Fallback SVRS centralizado (usado pela maioria dos estados) ───────────
SVRS_HOм = "https://nfce-homologacao.svrs.rs.gov.br/ws"
SVRS_PROD = "https://nfce.svrs.rs.gov.br/ws"

SVRS_URLS = {
    "homologacao": {
        "NFeAutorizacao":       f"{SVRS_HOм}/NfeAutorizacao/NFeAutorizacao4.asmx",
        "NFeRetAutorizacao":    f"{SVRS_HOм}/NfeRetAutorizacao/NFeRetAutorizacao4.asmx",
        "NFeInutilizacao":      f"{SVRS_HOм}/nfeinutilizacao/nfeinutilizacao4.asmx",
        "NFeConsultaProtocolo": f"{SVRS_HOм}/NfeConsulta/NfeConsulta4.asmx",
        "NFeStatusServico":     f"{SVRS_HOм}/NfeStatusServico/NfeStatusServico4.asmx",
        "RecepcaoEvento":       f"{SVRS_HOм}/recepcaoevento/recepcaoevento4.asmx",
    },
    "producao": {
        "NFeAutorizacao":       f"{SVRS_PROD}/NfeAutorizacao/NFeAutorizacao4.asmx",
        "NFeRetAutorizacao":    f"{SVRS_PROD}/NfeRetAutorizacao/NFeRetAutorizacao4.asmx",
        "NFeInutilizacao":      f"{SVRS_PROD}/nfeinutilizacao/nfeinutilizacao4.asmx",
        "NFeConsultaProtocolo": f"{SVRS_PROD}/NfeConsulta/NfeConsulta4.asmx",
        "NFeStatusServico":     f"{SVRS_PROD}/NfeStatusServico/NfeStatusServico4.asmx",
        "RecepcaoEvento":       f"{SVRS_PROD}/recepcaoevento/recepcaoevento4.asmx",
    },
}


class NfceUfConfig:

    @staticmethod
    def _db():
        return DatabaseManager.master()

    @staticmethod
    def buscar(uf: str) -> dict | None:
        """Retorna configuração da UF. None se não cadastrada."""
        return NfceUfConfig._db().fetchone(
            "SELECT * FROM nfce_uf_config WHERE uf=?", (uf.upper(),)
        )

    @staticmethod
    def listar() -> list[dict]:
        return NfceUfConfig._db().fetchall(
            "SELECT * FROM nfce_uf_config ORDER BY uf"
        )

    @staticmethod
    def salvar(uf: str, dados: dict) -> None:
        """Insere ou atualiza configuração de uma UF."""
        campos = [
            "c_uf", "fuso_horario",
            "url_qrcode_hom", "url_qrcode_prod",
            "ws_autorizacao_hom", "ws_autorizacao_prod",
            "ws_ret_autorizacao_hom", "ws_ret_autorizacao_prod",
            "ws_status_hom", "ws_status_prod",
            "ws_evento_hom", "ws_evento_prod",
            "obs",
        ]
        db = NfceUfConfig._db()
        existente = db.fetchone("SELECT uf FROM nfce_uf_config WHERE uf=?", (uf.upper(),))
        if existente:
            sets = ", ".join(f"{c}=?" for c in campos if c in dados)
            vals = [dados[c] for c in campos if c in dados] + [uf.upper()]
            db.execute(f"UPDATE nfce_uf_config SET {sets} WHERE uf=?", tuple(vals))
        else:
            cols = ["uf"] + [c for c in campos if c in dados]
            placeholders = ", ".join("?" * len(cols))
            vals = [uf.upper()] + [dados[c] for c in campos if c in dados]
            db.execute(
                f"INSERT INTO nfce_uf_config ({', '.join(cols)}) VALUES ({placeholders})",
                tuple(vals),
            )

    @staticmethod
    def url_qrcode(uf: str, ambiente: int) -> str | None:
        """Retorna URL base do QR Code para a UF e ambiente informados."""
        cfg = NfceUfConfig.buscar(uf)
        if not cfg:
            return None
        chave = "url_qrcode_hom" if ambiente == 2 else "url_qrcode_prod"
        return cfg.get(chave)

    @staticmethod
    def c_uf(uf: str) -> str:
        """Retorna o código IBGE da UF. Usa mapa interno como fallback."""
        cfg = NfceUfConfig.buscar(uf)
        if cfg and cfg.get("c_uf"):
            return cfg["c_uf"]
        return _UF_C_UF_MAP.get(uf.upper(), "99")

    @staticmethod
    def fuso_horario(uf: str) -> str:
        """Retorna o fuso horário da UF (ex: '-03:00')."""
        cfg = NfceUfConfig.buscar(uf)
        if cfg and cfg.get("fuso_horario"):
            return cfg["fuso_horario"]
        return "-03:00"

    @staticmethod
    def ws_urls(uf: str, ambiente: int) -> dict:
        """
        Retorna dict com URLs dos WebServices para a UF e ambiente.
        Campos nulos na tabela fazem fallback para o SVRS centralizado.
        """
        amb_key = "homologacao" if ambiente == 2 else "producao"
        svrs    = SVRS_URLS[amb_key]
        cfg     = NfceUfConfig.buscar(uf) or {}

        sufixo = "_hom" if ambiente == 2 else "_prod"
        return {
            "NFeAutorizacao":       cfg.get(f"ws_autorizacao{sufixo}")      or svrs["NFeAutorizacao"],
            "NFeRetAutorizacao":    cfg.get(f"ws_ret_autorizacao{sufixo}")  or svrs["NFeRetAutorizacao"],
            "NFeConsultaProtocolo": svrs["NFeConsultaProtocolo"],            # centralizado sempre
            "NFeStatusServico":     cfg.get(f"ws_status{sufixo}")           or svrs["NFeStatusServico"],
            "RecepcaoEvento":       cfg.get(f"ws_evento{sufixo}")           or svrs["RecepcaoEvento"],
        }


# Mapa de fallback (caso o banco ainda não tenha sido migrado)
_UF_C_UF_MAP = {
    "RO": "11", "AC": "12", "AM": "13", "RR": "14", "PA": "15",
    "AP": "16", "TO": "17", "MA": "21", "PI": "22", "CE": "23",
    "RN": "24", "PB": "25", "PE": "26", "AL": "27", "SE": "28",
    "BA": "29", "MG": "31", "ES": "32", "RJ": "33", "SP": "35",
    "PR": "41", "SC": "42", "RS": "43", "MS": "50", "MT": "51",
    "GO": "52", "DF": "53",
}
