-- Migration 011: colunas que faltaram na 010 por ter sido registrada com erro

ALTER TABLE produtos ADD COLUMN csosn        TEXT;
ALTER TABLE produtos ADD COLUMN cst_ipi      TEXT;
ALTER TABLE produtos ADD COLUMN unidade_trib TEXT;
ALTER TABLE produtos ADD COLUMN qtd_trib     REAL DEFAULT 1;
ALTER TABLE produtos ADD COLUMN preco_trib   REAL DEFAULT 0;
ALTER TABLE produtos ADD COLUMN margem       REAL DEFAULT 0;
ALTER TABLE produtos ADD COLUMN estoque_max  REAL DEFAULT 0;
ALTER TABLE produtos ADD COLUMN ean          TEXT;
ALTER TABLE produtos ADD COLUMN referencia   TEXT;
ALTER TABLE produtos ADD COLUMN marca        TEXT;
ALTER TABLE produtos ADD COLUMN modelo       TEXT;
ALTER TABLE produtos ADD COLUMN red_bc_icms  REAL DEFAULT 0;
ALTER TABLE produtos ADD COLUMN largura      REAL DEFAULT 0;
ALTER TABLE produtos ADD COLUMN altura       REAL DEFAULT 0;
ALTER TABLE produtos ADD COLUMN profundidade REAL DEFAULT 0;
ALTER TABLE produtos ADD COLUMN localizacao  TEXT;
ALTER TABLE produtos ADD COLUMN observacao   TEXT;
ALTER TABLE produtos ADD COLUMN foto_path    TEXT;
ALTER TABLE produtos ADD COLUMN grade        TEXT;
ALTER TABLE produtos ADD COLUMN garantia_dias INTEGER DEFAULT 0;

UPDATE produtos SET ean = codigo_barras WHERE ean IS NULL AND codigo_barras IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_produtos_ean  ON produtos(ean);
CREATE INDEX IF NOT EXISTS idx_produtos_nome ON produtos(nome);