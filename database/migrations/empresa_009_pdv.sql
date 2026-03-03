-- Migration 009 -- PDV: Caixas, Vendas, Mesas, Pedidos
-- DROP das tabelas PDV caso existam versoes antigas incompletas

DROP TABLE IF EXISTS pedido_divisao;
DROP TABLE IF EXISTS pedido_itens;
DROP TABLE IF EXISTS pedidos;
DROP TABLE IF EXISTS venda_pagamentos;
DROP TABLE IF EXISTS venda_itens;
DROP TABLE IF EXISTS vendas;
DROP TABLE IF EXISTS caixa_movimentos;
DROP TABLE IF EXISTS caixas;
DROP TABLE IF EXISTS mesas;
DROP TABLE IF EXISTS pdv_sequencias;

CREATE TABLE IF NOT EXISTS caixas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero INTEGER NOT NULL DEFAULT 1,
    nome TEXT, operador_id INTEGER, operador_nome TEXT,
    status TEXT NOT NULL DEFAULT 'FECHADO',
    valor_abertura REAL DEFAULT 0, valor_fechamento REAL,
    aberto_em TEXT, fechado_em TEXT, obs_abertura TEXT, obs_fechamento TEXT,
    criado_em TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS caixa_movimentos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    caixa_id INTEGER NOT NULL REFERENCES caixas(id),
    tipo TEXT NOT NULL, valor REAL NOT NULL,
    descricao TEXT, usuario_id INTEGER, usuario_nome TEXT,
    criado_em TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS vendas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero INTEGER NOT NULL,
    caixa_id INTEGER REFERENCES caixas(id),
    mesa_id INTEGER, pedido_id INTEGER,
    cliente_id INTEGER, cliente_nome TEXT, cliente_doc TEXT,
    status TEXT NOT NULL DEFAULT 'ABERTA',
    subtotal REAL NOT NULL DEFAULT 0,
    desconto_valor REAL DEFAULT 0, desconto_pct REAL DEFAULT 0,
    acrescimo REAL DEFAULT 0, total REAL NOT NULL DEFAULT 0,
    total_pago REAL DEFAULT 0, troco REAL DEFAULT 0,
    observacoes TEXT, operador_id INTEGER, operador_nome TEXT,
    finalizada_em TEXT, cancelada_em TEXT, motivo_cancel TEXT,
    nfce_status TEXT DEFAULT 'NAO_EMITIDA',
    nfce_numero INTEGER, nfce_serie INTEGER, nfce_chave TEXT,
    criado_em TEXT DEFAULT (datetime('now','localtime'))
);

CREATE INDEX IF NOT EXISTS idx_vendas_caixa  ON vendas(caixa_id, criado_em DESC);
CREATE INDEX IF NOT EXISTS idx_vendas_data   ON vendas(criado_em DESC);
CREATE INDEX IF NOT EXISTS idx_vendas_status ON vendas(status);

CREATE TABLE IF NOT EXISTS venda_itens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    venda_id INTEGER NOT NULL REFERENCES vendas(id) ON DELETE CASCADE,
    produto_id INTEGER NOT NULL,
    produto_codigo TEXT, produto_nome TEXT NOT NULL,
    produto_ncm TEXT, produto_cfop TEXT, produto_cst TEXT,
    unidade TEXT DEFAULT 'UN',
    quantidade REAL NOT NULL DEFAULT 1, preco_unitario REAL NOT NULL,
    desconto_valor REAL DEFAULT 0, desconto_pct REAL DEFAULT 0,
    subtotal REAL NOT NULL,
    aliq_icms REAL DEFAULT 0, aliq_pis REAL DEFAULT 0, aliq_cofins REAL DEFAULT 0,
    obs TEXT, criado_em TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS venda_pagamentos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    venda_id INTEGER NOT NULL REFERENCES vendas(id) ON DELETE CASCADE,
    forma TEXT NOT NULL, valor REAL NOT NULL,
    parcelas INTEGER DEFAULT 1, troco REAL DEFAULT 0,
    bandeira TEXT, nsu TEXT,
    criado_em TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS mesas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero INTEGER NOT NULL UNIQUE,
    nome TEXT, capacidade INTEGER DEFAULT 4,
    status TEXT DEFAULT 'LIVRE', setor TEXT, ativo INTEGER DEFAULT 1,
    criado_em TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS pedidos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mesa_id INTEGER NOT NULL REFERENCES mesas(id),
    numero INTEGER NOT NULL, status TEXT DEFAULT 'ABERTO',
    pessoas INTEGER DEFAULT 1, garcom_id INTEGER, garcom_nome TEXT,
    subtotal REAL DEFAULT 0, desconto_valor REAL DEFAULT 0, total REAL DEFAULT 0,
    observacoes TEXT,
    aberto_em TEXT DEFAULT (datetime('now','localtime')),
    fechado_em TEXT, criado_em TEXT DEFAULT (datetime('now','localtime'))
);

CREATE INDEX IF NOT EXISTS idx_pedidos_mesa   ON pedidos(mesa_id, status);
CREATE INDEX IF NOT EXISTS idx_pedidos_status ON pedidos(status);

CREATE TABLE IF NOT EXISTS pedido_itens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pedido_id INTEGER NOT NULL REFERENCES pedidos(id) ON DELETE CASCADE,
    produto_id INTEGER NOT NULL,
    produto_codigo TEXT, produto_nome TEXT NOT NULL,
    unidade TEXT DEFAULT 'UN',
    quantidade REAL NOT NULL DEFAULT 1, preco_unitario REAL NOT NULL,
    desconto_valor REAL DEFAULT 0, subtotal REAL NOT NULL,
    obs TEXT, status TEXT DEFAULT 'PENDENTE', impresso INTEGER DEFAULT 0,
    criado_em TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS pedido_divisao (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pedido_id INTEGER NOT NULL REFERENCES pedidos(id),
    pessoa INTEGER NOT NULL, nome TEXT,
    total REAL DEFAULT 0, pago INTEGER DEFAULT 0,
    criado_em TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS pdv_sequencias (
    chave TEXT PRIMARY KEY, ultimo INTEGER DEFAULT 0
);

INSERT OR IGNORE INTO mesas (numero, nome, capacidade, setor) VALUES
 (1,'Mesa 1',4,'Salao'),(2,'Mesa 2',4,'Salao'),(3,'Mesa 3',4,'Salao'),
 (4,'Mesa 4',4,'Salao'),(5,'Mesa 5',6,'Salao'),(6,'Mesa 6',6,'Salao'),
 (7,'Mesa 7',2,'Varanda'),(8,'Mesa 8',2,'Varanda'),
 (9,'Balcao 1',1,'Balcao'),(10,'Balcao 2',1,'Balcao');