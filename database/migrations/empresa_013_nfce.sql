-- Migration 013 — NFC-e: configuração, documentos e log de comunicação SEFAZ
CREATE TABLE IF NOT EXISTS nfce_config (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ambiente        INTEGER NOT NULL DEFAULT 2,
    serie           INTEGER NOT NULL DEFAULT 1,
    proximo_numero  INTEGER NOT NULL DEFAULT 1,
    csc_id          TEXT,
    csc_token       TEXT,
    cert_path       TEXT,
    cert_senha      TEXT,
    versao_nfe      TEXT NOT NULL DEFAULT '4.00',
    id_csc          TEXT,
    ativo           INTEGER DEFAULT 1,
    atualizado_em   TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS nfce_documentos (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    venda_id         INTEGER REFERENCES vendas(id),
    numero           INTEGER NOT NULL,
    serie            INTEGER NOT NULL DEFAULT 1,
    chave_acesso     TEXT UNIQUE,
    ambiente         INTEGER NOT NULL DEFAULT 2,
    status           TEXT NOT NULL DEFAULT 'PENDENTE',
    xml_envio        TEXT,
    xml_retorno      TEXT,
    xml_protocolo    TEXT,
    protocolo        TEXT,
    motivo_rejeicao  TEXT,
    qrcode_url       TEXT,
    url_consulta     TEXT,
    danfe_path       TEXT,
    data_emissao     TEXT,
    data_autorizacao TEXT,
    valor_total      REAL,
    criado_em        TEXT DEFAULT (datetime('now','localtime')),
    atualizado_em    TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS nfce_log (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    documento_id INTEGER REFERENCES nfce_documentos(id),
    operacao     TEXT,
    status_http  INTEGER,
    request_xml  TEXT,
    response_xml TEXT,
    erro         TEXT,
    criado_em    TEXT DEFAULT (datetime('now','localtime'))
);

CREATE INDEX IF NOT EXISTS idx_nfce_venda  ON nfce_documentos(venda_id);
CREATE INDEX IF NOT EXISTS idx_nfce_chave  ON nfce_documentos(chave_acesso);
CREATE INDEX IF NOT EXISTS idx_nfce_status ON nfce_documentos(status);
