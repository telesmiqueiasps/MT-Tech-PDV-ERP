DROP TABLE IF EXISTS estoque_movimentos;
DROP TABLE IF EXISTS estoque_saldos;
DROP TABLE IF EXISTS depositos;

CREATE TABLE depositos (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nome        TEXT    NOT NULL,
    descricao   TEXT,
    ativo       INTEGER DEFAULT 1,
    criado_em   TEXT    DEFAULT (datetime('now','localtime'))
);

CREATE TABLE estoque_saldos (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    produto_id  INTEGER NOT NULL REFERENCES produtos(id),
    deposito_id INTEGER NOT NULL REFERENCES depositos(id),
    quantidade  REAL    DEFAULT 0,
    custo_medio REAL    DEFAULT 0,
    UNIQUE(produto_id, deposito_id)
);

CREATE TABLE estoque_movimentos (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo             TEXT    NOT NULL,
    produto_id       INTEGER NOT NULL REFERENCES produtos(id),
    deposito_id      INTEGER NOT NULL REFERENCES depositos(id),
    deposito_dest_id INTEGER REFERENCES depositos(id),
    quantidade       REAL    NOT NULL,
    custo_unitario   REAL    DEFAULT 0,
    custo_total      REAL    DEFAULT 0,
    fornecedor_id    INTEGER REFERENCES fornecedores(id),
    numero_nf        TEXT,
    motivo           TEXT,
    usuario_id       INTEGER,
    usuario_nome     TEXT,
    saldo_anterior   REAL    DEFAULT 0,
    saldo_posterior  REAL    DEFAULT 0,
    criado_em        TEXT    DEFAULT (datetime('now','localtime'))
);

CREATE INDEX idx_mov_produto   ON estoque_movimentos(produto_id);
CREATE INDEX idx_mov_deposito  ON estoque_movimentos(deposito_id);
CREATE INDEX idx_mov_criado_em ON estoque_movimentos(criado_em);
CREATE INDEX idx_saldo_produto ON estoque_saldos(produto_id);