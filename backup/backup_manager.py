"""
BackupManager — backup automático diário dos bancos SQLite para o servidor.

Fluxo:
  verificar_e_executar_se_necessario() → roda em background, sem bloquear UI
  executar()                           → comprime ZIPem memória e envia via HTTP
  chave_licenca()                      → lê ~/.pdverp/licenca.json
"""

import io
import json
import zipfile
from datetime import date
from pathlib import Path


class BackupManager:
    _ULTIMO_BACKUP = Path.home() / ".pdverp" / "ultimo_backup.txt"

    # ── API pública ───────────────────────────────────────────────

    @classmethod
    def verificar_e_executar_se_necessario(cls, chave_licenca: str) -> None:
        """
        Verifica se já foi feito backup hoje.
        Se não, executa em thread daemon (não bloqueia a UI).
        """
        import threading
        threading.Thread(
            target=cls._tarefa_backup,
            args=(chave_licenca,),
            daemon=True,
        ).start()

    @classmethod
    def executar(cls, chave_licenca: str) -> tuple[bool, str]:
        """
        Comprime os bancos em ZIP (em memória) e envia ao servidor.
        Retorna (True, mensagem) ou (False, mensagem_de_erro).
        Nunca lança exceção.
        """
        try:
            import requests
            from models.licenca import _SERVIDOR_URL
            from core.session import Session
            from config import MASTER_DB

            empresa = Session.empresa()
            cnpj    = (empresa.get("cnpj") or "").replace(".", "").replace(
                "/", "").replace("-", "").strip()

            if not cnpj:
                return False, "CNPJ da empresa não disponível na sessão."

            # ── Monta ZIP em memória ──────────────────────────────
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, mode="w",
                                 compression=zipfile.ZIP_DEFLATED) as zf:
                # master.db
                if MASTER_DB.exists():
                    zf.write(MASTER_DB, arcname="master.db")

                # banco da empresa ativa
                db_path_str = empresa.get("db_path", "")
                if db_path_str:
                    db_path = Path(db_path_str)
                    if db_path.exists():
                        zf.write(db_path, arcname=db_path.name)

            buf.seek(0)

            # ── Envia ao servidor ─────────────────────────────────
            resp = requests.post(
                f"{_SERVIDOR_URL}/api/backup/upload",
                data={"cnpj": cnpj, "chave_licenca": chave_licenca},
                files={"arquivo": ("backup.zip", buf, "application/zip")},
                timeout=60,
            )

            if resp.status_code == 200:
                return True, "Backup realizado com sucesso."
            return False, f"Servidor retornou {resp.status_code}: {resp.text[:200]}"

        except Exception as e:
            return False, str(e)

    @classmethod
    def chave_licenca(cls) -> str:
        """Lê a chave do arquivo local ~/.pdverp/licenca.json."""
        try:
            licenca_file = Path.home() / ".pdverp" / "licenca.json"
            dados = json.loads(licenca_file.read_text(encoding="utf-8"))
            wrapper = dados if "chave" in dados else dados.get("dados", dados)
            return wrapper.get("chave", "")
        except Exception:
            return ""

    # ── Internos ──────────────────────────────────────────────────

    @classmethod
    def _tarefa_backup(cls, chave_licenca: str) -> None:
        """Executa backup se necessário e registra a data."""
        if cls._backup_feito_hoje():
            return

        ok, msg = cls.executar(chave_licenca)
        cls._log(f"{'OK' if ok else 'ERRO'}: {msg}")

        if ok:
            cls._registrar_hoje()

    @classmethod
    def _backup_feito_hoje(cls) -> bool:
        try:
            txt = cls._ULTIMO_BACKUP.read_text(encoding="utf-8").strip()
            return txt == date.today().isoformat()
        except Exception:
            return False

    @classmethod
    def _registrar_hoje(cls) -> None:
        try:
            cls._ULTIMO_BACKUP.parent.mkdir(parents=True, exist_ok=True)
            cls._ULTIMO_BACKUP.write_text(
                date.today().isoformat(), encoding="utf-8"
            )
        except Exception:
            pass

    @classmethod
    def _log(cls, msg: str) -> None:
        print(f"[backup] {msg}")
        try:
            from core.logger import Logger
            Logger.info(msg)
        except Exception:
            pass
