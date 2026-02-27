CREATE TABLE IF NOT EXISTS admin_global (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    login      TEXT UNIQUE NOT NULL,
    senha_hash TEXT NOT NULL,
    ativo      INTEGER DEFAULT 1,
    criado_em  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS empresas (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    nome         TEXT NOT NULL,
    razao_social TEXT,
    cnpj         TEXT,
    ativo        INTEGER DEFAULT 1,
    db_path      TEXT NOT NULL,
    criado_em    TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS audit_log (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    nivel        TEXT DEFAULT 'INFO',
    empresa_id   INTEGER,
    usuario_id   INTEGER,
    acao         TEXT NOT NULL,
    detalhe      TEXT,
    tabela       TEXT,
    registro_id  INTEGER,
    dados_antes  TEXT,
    dados_depois TEXT,
    criado_em    TEXT DEFAULT (datetime('now'))
);