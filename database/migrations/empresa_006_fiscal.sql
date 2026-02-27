CREATE TABLE notas_fiscais (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo            TEXT    NOT NULL,
        -- ENTRADA=compra, SAIDA=venda, DEV_COMPRA=devolução compra, DEV_VENDA=devolução venda
    modelo          TEXT    NOT NULL DEFAULT '55',
        -- 55=NF-e, 65=NFC-e
    status          TEXT    NOT NULL DEFAULT 'RASCUNHO',
        -- RASCUNHO, PENDENTE, AUTORIZADA, CANCELADA, INUTILIZADA
    numero          INTEGER,
    serie           INTEGER DEFAULT 1,
    chave_acesso    TEXT,
    protocolo       TEXT,
    -- Emitente (sempre a empresa)
    emitente_id     INTEGER,
    -- Destinatário/Remetente
    terceiro_id     INTEGER,
        -- cliente_id para saída, fornecedor_id para entrada
    terceiro_tipo   TEXT,
        -- CLIENTE ou FORNECEDOR
    terceiro_nome   TEXT,
    terceiro_doc    TEXT,
    -- Datas
    data_emissao    TEXT,
    data_entrada    TEXT,
    -- Totais
    total_produtos  REAL DEFAULT 0,
    total_frete     REAL DEFAULT 0,
    total_seguro    REAL DEFAULT 0,
    total_desconto  REAL DEFAULT 0,
    total_outros    REAL DEFAULT 0,
    total_ipi       REAL DEFAULT 0,
    total_icms      REAL DEFAULT 0,
    total_pis       REAL DEFAULT 0,
    total_cofins    REAL DEFAULT 0,
    total_nf        REAL DEFAULT 0,
    -- Transporte
    frete_modalidade INTEGER DEFAULT 9,
        -- 0=Emitente, 1=Destinatário, 2=Terceiros, 9=Sem frete
    transportadora  TEXT,
    -- Referências
    nota_ref_id     INTEGER REFERENCES notas_fiscais(id),
        -- para devoluções
    deposito_id     INTEGER REFERENCES depositos(id),
    -- Controle
    xml_entrada     TEXT,
    xml_autorizado  TEXT,
    xml_cancelamento TEXT,
    observacoes     TEXT,
    usuario_id      INTEGER,
    usuario_nome    TEXT,
    criado_em       TEXT DEFAULT (datetime('now','localtime')),
    atualizado_em   TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE notas_fiscais_itens (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    nota_id         INTEGER NOT NULL REFERENCES notas_fiscais(id) ON DELETE CASCADE,
    ordem           INTEGER DEFAULT 1,
    produto_id      INTEGER REFERENCES produtos(id),
    codigo          TEXT,
    descricao       TEXT    NOT NULL,
    ncm             TEXT,
    cfop            TEXT,
    unidade         TEXT,
    quantidade      REAL    DEFAULT 0,
    valor_unitario  REAL    DEFAULT 0,
    valor_total     REAL    DEFAULT 0,
    desconto        REAL    DEFAULT 0,
    frete           REAL    DEFAULT 0,
    -- Tributação
    origem          INTEGER DEFAULT 0,
    cst_icms        TEXT,
    aliq_icms       REAL    DEFAULT 0,
    valor_icms      REAL    DEFAULT 0,
    cst_pis         TEXT    DEFAULT '07',
    aliq_pis        REAL    DEFAULT 0,
    valor_pis       REAL    DEFAULT 0,
    cst_cofins      TEXT    DEFAULT '07',
    aliq_cofins     REAL    DEFAULT 0,
    valor_cofins    REAL    DEFAULT 0,
    cst_ipi         TEXT,
    aliq_ipi        REAL    DEFAULT 0,
    valor_ipi       REAL    DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_nf_tipo    ON notas_fiscais(tipo);
CREATE INDEX IF NOT EXISTS idx_nf_status  ON notas_fiscais(status);
CREATE INDEX IF NOT EXISTS idx_nf_numero  ON notas_fiscais(numero);
CREATE INDEX IF NOT EXISTS idx_nfi_nota   ON notas_fiscais_itens(nota_id);
CREATE INDEX IF NOT EXISTS idx_nfi_prod   ON notas_fiscais_itens(produto_id);