CREATE TABLE IF NOT EXISTS perfis (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    nome      TEXT NOT NULL,
    descricao TEXT,
    ativo     INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS permissoes (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    perfil_id INTEGER NOT NULL REFERENCES perfis(id),
    modulo    TEXT NOT NULL,
    acao      TEXT NOT NULL,
    permitido INTEGER DEFAULT 0,
    UNIQUE(perfil_id, modulo, acao)
);

CREATE TABLE IF NOT EXISTS usuarios (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    nome       TEXT NOT NULL,
    login      TEXT UNIQUE NOT NULL,
    senha_hash TEXT NOT NULL,
    perfil_id  INTEGER REFERENCES perfis(id),
    ativo      INTEGER DEFAULT 1,
    criado_em  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS categorias (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    nome  TEXT NOT NULL,
    ativo INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS produtos (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo        TEXT UNIQUE,
    codigo_barras TEXT,
    nome          TEXT NOT NULL,
    categoria_id  INTEGER REFERENCES categorias(id),
    ncm           TEXT,
    unidade       TEXT DEFAULT 'UN',
    preco_custo   REAL DEFAULT 0,
    preco_venda   REAL DEFAULT 0,
    margem        REAL DEFAULT 0,
    estoque_atual REAL DEFAULT 0,
    estoque_min   REAL DEFAULT 0,
    estoque_max   REAL DEFAULT 0,
    ativo         INTEGER DEFAULT 1,
    criado_em     TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS clientes (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    nome      TEXT NOT NULL,
    cpf_cnpj  TEXT,
    telefone  TEXT,
    email     TEXT,
    ativo     INTEGER DEFAULT 1,
    criado_em TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS fornecedores (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    nome      TEXT NOT NULL,
    cnpj      TEXT,
    telefone  TEXT,
    email     TEXT,
    ativo     INTEGER DEFAULT 1,
    criado_em TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS vendas (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    numero     INTEGER NOT NULL,
    cliente_id INTEGER REFERENCES clientes(id),
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
    subtotal   REAL DEFAULT 0,
    desconto   REAL DEFAULT 0,
    total      REAL DEFAULT 0,
    forma_pgto TEXT,
    troco      REAL DEFAULT 0,
    status     TEXT DEFAULT 'finalizada',
    criado_em  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS venda_itens (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    venda_id   INTEGER NOT NULL REFERENCES vendas(id),
    produto_id INTEGER NOT NULL REFERENCES produtos(id),
    quantidade REAL NOT NULL,
    preco_unit REAL NOT NULL,
    desconto   REAL DEFAULT 0,
    total      REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS estoque_movimentos (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    produto_id   INTEGER NOT NULL REFERENCES produtos(id),
    tipo         TEXT NOT NULL,
    quantidade   REAL NOT NULL,
    estoque_ant  REAL,
    estoque_novo REAL,
    motivo       TEXT,
    usuario_id   INTEGER REFERENCES usuarios(id),
    criado_em    TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS caixas (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id       INTEGER NOT NULL REFERENCES usuarios(id),
    abertura_valor   REAL DEFAULT 0,
    fechamento_valor REAL,
    total_vendas     REAL DEFAULT 0,
    status           TEXT DEFAULT 'aberto',
    aberto_em        TEXT DEFAULT (datetime('now')),
    fechado_em       TEXT
);

CREATE TABLE IF NOT EXISTS contas_pagar (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    descricao     TEXT NOT NULL,
    fornecedor_id INTEGER REFERENCES fornecedores(id),
    valor         REAL NOT NULL,
    vencimento    TEXT NOT NULL,
    pago_em       TEXT,
    valor_pago    REAL,
    status        TEXT DEFAULT 'aberta',
    criado_em     TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS contas_receber (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    descricao   TEXT NOT NULL,
    cliente_id  INTEGER REFERENCES clientes(id),
    venda_id    INTEGER REFERENCES vendas(id),
    valor       REAL NOT NULL,
    vencimento  TEXT NOT NULL,
    recebido_em TEXT,
    status      TEXT DEFAULT 'aberta',
    criado_em   TEXT DEFAULT (datetime('now'))
);