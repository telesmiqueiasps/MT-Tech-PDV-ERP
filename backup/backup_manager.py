"""
BackupManager — backup automático diário dos bancos SQLite para o servidor.

Fluxo:
  verificar_e_executar_se_necessario() → verifica data e dispara daemon thread
  executar()                           → checkpoint WAL, ZIP em memória, envia
  chave_licenca()                      → lê ~/.pdverp/licenca.json (payload+sig)
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
        """Verifica se já foi feito backup hoje; se não, executa em daemon thread."""
        if cls._backup_feito_hoje():
            return

        import threading
        threading.Thread(
            target=cls._tarefa_backup,
            args=(chave_licenca,),
            daemon=True,
        ).start()

    @classmethod
    def executar(cls, chave_licenca: str) -> tuple[bool, str]:
        """
        Faz checkpoint do WAL, comprime os bancos em ZIP em memória e envia.
        Retorna (True, msg) ou (False, msg_erro). Nunca lança exceção.
        """
        try:
            import requests
            from models.licenca import _SERVIDOR_URL
            from core.session import Session
            from core.database import DatabaseManager
            from config import MASTER_DB

            empresa  = Session.empresa()
            cnpj     = (empresa.get("cnpj") or "").replace(".", "").replace(
                "/", "").replace("-", "").strip()
            nome     = empresa.get("razao_social") or empresa.get("nome") or ""
            db_path  = Path(empresa.get("db_path") or "")

            if not cnpj:
                return False, "CNPJ da empresa não disponível na sessão."

            # ── Checkpoint WAL para consistência ──────────────────
            # Garante que todos os dados do WAL estejam no arquivo principal
            # antes de copiar, evitando backup incompleto.
            try:
                DatabaseManager.master()._conn.execute("PRAGMA wal_checkpoint(FULL)")
            except Exception:
                pass
            if db_path.exists():
                try:
                    DatabaseManager.empresa()._conn.execute("PRAGMA wal_checkpoint(FULL)")
                except Exception:
                    pass

            # ── Monta ZIP em memória ──────────────────────────────
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, mode="w",
                                 compression=zipfile.ZIP_DEFLATED) as zf:
                if MASTER_DB.exists():
                    zf.write(MASTER_DB, arcname="master.db")
                if db_path.exists():
                    zf.write(db_path, arcname=db_path.name)
            buf.seek(0)

            # ── Envia ao servidor ─────────────────────────────────
            resp = requests.post(
                f"{_SERVIDOR_URL}/api/backup/upload",
                data={
                    "cnpj":          cnpj,
                    "chave_licenca": chave_licenca,
                    "cliente_nome":  nome,
                },
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
        """
        Lê a chave do arquivo local ~/.pdverp/licenca.json.

        Estrutura do arquivo (gravada por models/licenca.py):
          {"payload": "<json string com os dados>", "sig": "<hmac>"}
        O campo "chave" está dentro do payload (que é uma string JSON aninhada).
        """
        try:
            licenca_file = Path.home() / ".pdverp" / "licenca.json"
            wrapper = json.loads(licenca_file.read_text(encoding="utf-8"))
            dados   = json.loads(wrapper["payload"])
            return dados.get("chave") or ""
        except Exception:
            return ""

    # ── Internos ──────────────────────────────────────────────────

    @classmethod
    def _tarefa_backup(cls, chave_licenca: str) -> None:
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
