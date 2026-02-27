import sqlite3
from pathlib import Path
from config import MIGRATIONS_DIR


class DatabaseError(Exception):
    pass


class Conexao:
    def __init__(self, path: Path):
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.row_factory = sqlite3.Row

    def fetchone(self, sql: str, params: tuple = ()) -> dict | None:
        cur = self._conn.execute(sql, params)
        row = cur.fetchone()
        return dict(row) if row else None

    def fetchall(self, sql: str, params: tuple = ()) -> list[dict]:
        cur = self._conn.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]

    def execute(self, sql: str, params: tuple = ()) -> int:
        cur = self._conn.execute(sql, params)
        self._conn.commit()
        return cur.lastrowid

    def executemany(self, sql: str, params_list: list) -> None:
        self._conn.executemany(sql, params_list)
        self._conn.commit()

    def executescript(self, sql: str) -> None:
        self._conn.executescript(sql)

    def tabela_existe(self, nome: str) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (nome,)
        ).fetchone()
        return row is not None

    def migration_aplicada(self, nome: str) -> bool:
        if not self.tabela_existe("_migrations"):
            return False
        row = self._conn.execute(
            "SELECT 1 FROM _migrations WHERE nome=?", (nome,)
        ).fetchone()
        return row is not None

    def registrar_migration(self, nome: str) -> None:
        self._conn.execute(
            "INSERT OR IGNORE INTO _migrations (nome) VALUES (?)", (nome,)
        )
        self._conn.commit()

    def criar_tabela_migrations(self) -> None:
        # Verifica se a tabela existe com a coluna correta
        try:
            self._conn.execute("SELECT nome FROM _migrations LIMIT 1")
        except sqlite3.OperationalError:
            # Tabela não existe ou tem estrutura errada — recria
            self._conn.execute("DROP TABLE IF EXISTS _migrations")
            self._conn.execute(
                "CREATE TABLE _migrations "
                "(nome TEXT PRIMARY KEY, "
                " aplicada_em TEXT DEFAULT (datetime('now','localtime')))"
            )
            self._conn.commit()

    def executescript_seguro(self, sql: str) -> None:
        """
        Executa cada statement individualmente, ignorando erros de
        coluna duplicada (duplicate column) — necessário para ALTER TABLE
        em SQLite sem suporte a IF NOT EXISTS.
        """
        statements = [s.strip() for s in sql.split(";") if s.strip()]
        for stmt in statements:
            try:
                self._conn.execute(stmt)
                self._conn.commit()
            except sqlite3.OperationalError as e:
                msg = str(e).lower()
                # Ignora apenas erros de coluna já existente
                if "duplicate column" in msg:
                    continue
                raise

    def close(self):
        self._conn.close()


class DatabaseManager:
    _master:  Conexao | None = None
    _empresa: Conexao | None = None

    @classmethod
    def init_master(cls, path: Path):
        cls._master = Conexao(path)
        cls._aplicar_migrations(cls._master, "master")

    @classmethod
    def conectar_empresa(cls, path: Path):
        if cls._empresa:
            try:
                cls._empresa.close()
            except Exception:
                pass
        cls._empresa = Conexao(path)
        cls._aplicar_migrations(cls._empresa, "empresa")

    @classmethod
    def master(cls) -> Conexao:
        if not cls._master:
            raise DatabaseError("Master não inicializado.")
        return cls._master

    @classmethod
    def fechar_empresa(cls):
        if cls._empresa:
            try:
                cls._empresa.close()
            except Exception:
                pass
            cls._empresa = None

    @classmethod
    def empresa(cls) -> Conexao:
        if not cls._empresa:
            raise DatabaseError("Nenhuma empresa conectada.")
        return cls._empresa

    @classmethod
    def _aplicar_migrations(cls, db: Conexao, tipo: str):
        """
        Aplica cada migration apenas uma vez, rastreando pelo nome do arquivo
        na tabela _migrations do próprio banco.
        Executa SEMPRE statement por statement para evitar problemas com
        COMMIT implícito do executescript do SQLite.
        """
        db.criar_tabela_migrations()

        padrao   = f"{tipo}_*.sql"
        arquivos = sorted(MIGRATIONS_DIR.glob(padrao))

        for arq in arquivos:
            nome = arq.name
            if db.migration_aplicada(nome):
                continue

            sql        = arq.read_text(encoding="utf-8")
            statements = [s.strip() for s in sql.split(";") if s.strip()]

            for stmt in statements:
                try:
                    db._conn.execute(stmt)
                    db._conn.commit()
                except sqlite3.OperationalError as e:
                    msg = str(e).lower()
                    stmt_upper = stmt.upper().lstrip()
                    # Para ALTER TABLE: ignora coluna duplicada
                    if stmt_upper.startswith("ALTER TABLE") and "duplicate column" in msg:
                        continue
                    # Para CREATE TABLE/INDEX: ignora "already exists"
                    if any(stmt_upper.startswith(p) for p in ("CREATE TABLE", "CREATE INDEX", "CREATE UNIQUE")) and "already exists" in msg:
                        continue
                    # INSERT OR IGNORE nunca deve falhar por isso
                    raise sqlite3.OperationalError(
                        f"Migration '{nome}' falhou:\n"
                        f"Statement: {stmt[:200]}\n"
                        f"Erro: {e}"
                    ) from e

            db.registrar_migration(nome)