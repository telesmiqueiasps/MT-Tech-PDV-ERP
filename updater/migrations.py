"""
MigrationManager — aplica migrations empresa_*.sql com backup automático.

Fluxo por migration pendente:
  1. Faz backup do arquivo .db  →  [nome].backup_YYYYMMDD_HHMMSS.db
  2. Executa o SQL via executescript()
  3. Registra na tabela _migrations
  4. Em caso de erro, loga e interrompe (não avança para a próxima)
"""

import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

from config import MIGRATIONS_DIR


class MigrationManager:
    # ── Conexão própria (independente do DatabaseManager) ────────

    def _abrir(self, db_path: Path) -> sqlite3.Connection:
        conn = sqlite3.connect(str(db_path), check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.row_factory = sqlite3.Row
        return conn

    def _garantir_tabela(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS _migrations "
            "(nome TEXT PRIMARY KEY, "
            " aplicada_em TEXT DEFAULT (datetime('now','localtime')))"
        )
        conn.commit()

    def _aplicada(self, conn: sqlite3.Connection, nome: str) -> bool:
        try:
            row = conn.execute(
                "SELECT 1 FROM _migrations WHERE nome=?", (nome,)
            ).fetchone()
            return row is not None
        except sqlite3.OperationalError:
            return False

    def _registrar(self, conn: sqlite3.Connection, nome: str) -> None:
        conn.execute(
            "INSERT OR IGNORE INTO _migrations (nome) VALUES (?)", (nome,)
        )
        conn.commit()

    # ── Backup ────────────────────────────────────────────────────

    def _backup(self, db_path: Path) -> Path:
        ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = db_path.parent / f"{db_path.stem}.backup_{ts}{db_path.suffix}"
        shutil.copy2(db_path, dest)
        return dest

    # ── Listagem de arquivos ──────────────────────────────────────

    def _arquivos(self) -> list[Path]:
        return sorted(MIGRATIONS_DIR.glob("empresa_*.sql"))

    # ── API pública ───────────────────────────────────────────────

    def pendentes(self, db_path: Path) -> list[str]:
        """Retorna lista de migrations ainda não aplicadas."""
        conn = self._abrir(db_path)
        try:
            self._garantir_tabela(conn)
            return [
                arq.name
                for arq in self._arquivos()
                if not self._aplicada(conn, arq.name)
            ]
        finally:
            conn.close()

    def aplicar_pendentes(self, db_path: Path) -> tuple[int, list[str]]:
        """
        Aplica todas as migrations pendentes com backup por migration.

        Retorna (quantidade_aplicada, [nomes_aplicados]).
        Lança RuntimeError em caso de falha, interrompendo o processo.
        """
        conn = self._abrir(db_path)
        try:
            self._garantir_tabela(conn)
            aplicadas: list[str] = []

            for arq in self._arquivos():
                nome = arq.name
                if self._aplicada(conn, nome):
                    continue

                # ── Backup antes de qualquer alteração ───────────
                backup_path = self._backup(db_path)
                self._log(f"Backup: {backup_path.name}")

                # ── Aplica o SQL ─────────────────────────────────
                sql = arq.read_text(encoding="utf-8")
                try:
                    conn.executescript(sql)
                    self._registrar(conn, nome)
                    aplicadas.append(nome)
                    self._log(f"Aplicada: {nome}")
                except Exception as e:
                    msg = f"Migration '{nome}' falhou: {e}"
                    self._log(msg, erro=True)
                    raise RuntimeError(msg) from e

            return len(aplicadas), aplicadas
        finally:
            conn.close()

    # ── Logger ────────────────────────────────────────────────────

    def _log(self, msg: str, erro: bool = False) -> None:
        prefixo = "[migrations] ERRO" if erro else "[migrations]"
        print(f"{prefixo} {msg}")
        try:
            from core.logger import Logger
            if erro:
                Logger.error(msg)
            else:
                Logger.info(msg)
        except Exception:
            pass
