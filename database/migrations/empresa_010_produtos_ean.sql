-- Migration 010: Adiciona colunas novas à tabela produtos
-- Usa ALTER TABLE (não recria) para preservar dados existentes.
-- SQLite ignora ADD COLUMN se a migration já foi aplicada (controle por _migrations).

-- EAN / código de barras (novo nome usado pelo form_produto.py)
ALTER TABLE produtos ADD COLUMN ean              TEXT;

-- Campos fiscais usados pelo produto.py (INSERT/UPDATE)
ALTER TABLE produtos ADD COLUMN csosn            TEXT;
ALTER TABLE produtos ADD COLUMN cst_ipi          TEXT;
ALTER TABLE produtos ADD COLUMN unidade_trib     TEXT;
ALTER TABLE produtos ADD COLUMN qtd_trib         REAL DEFAULT 1;
ALTER TABLE produtos ADD COLUMN preco_trib       REAL DEFAULT 0;

-- Campos de precificação
ALTER TABLE produtos ADD COLUMN margem           REAL DEFAULT 0;
ALTER TABLE produtos ADD COLUMN estoque_max      REAL DEFAULT 0;

-- Campos de identificação complementares
ALTER TABLE produtos ADD COLUMN referencia       TEXT;
ALTER TABLE produtos ADD COLUMN marca            TEXT;
ALTER TABLE produtos ADD COLUMN modelo           TEXT;

-- Fiscal
ALTER TABLE produtos ADD COLUMN ncm              TEXT;
ALTER TABLE produtos ADD COLUMN cfop_padrao      TEXT DEFAULT '5102';
ALTER TABLE produtos ADD COLUMN cst_icms         TEXT DEFAULT '00';
ALTER TABLE produtos ADD COLUMN cst_pis          TEXT DEFAULT '07';
ALTER TABLE produtos ADD COLUMN cst_cofins       TEXT DEFAULT '07';
ALTER TABLE produtos ADD COLUMN origem           INTEGER DEFAULT 0;
ALTER TABLE produtos ADD COLUMN aliq_icms        REAL DEFAULT 0;
ALTER TABLE produtos ADD COLUMN aliq_ipi         REAL DEFAULT 0;
ALTER TABLE produtos ADD COLUMN aliq_pis         REAL DEFAULT 0.65;
ALTER TABLE produtos ADD COLUMN aliq_cofins      REAL DEFAULT 3.0;
ALTER TABLE produtos ADD COLUMN red_bc_icms      REAL DEFAULT 0;

-- Logística
ALTER TABLE produtos ADD COLUMN peso_bruto       REAL DEFAULT 0;
ALTER TABLE produtos ADD COLUMN peso_liquido     REAL DEFAULT 0;
ALTER TABLE produtos ADD COLUMN largura          REAL DEFAULT 0;
ALTER TABLE produtos ADD COLUMN altura           REAL DEFAULT 0;
ALTER TABLE produtos ADD COLUMN profundidade     REAL DEFAULT 0;

-- Extras
ALTER TABLE produtos ADD COLUMN localizacao      TEXT;
ALTER TABLE produtos ADD COLUMN observacao       TEXT;
ALTER TABLE produtos ADD COLUMN foto_path        TEXT;
ALTER TABLE produtos ADD COLUMN grade            TEXT;
ALTER TABLE produtos ADD COLUMN garantia_dias    INTEGER DEFAULT 0;

-- Copia codigo_barras → ean para produtos já cadastrados
UPDATE produtos SET ean = codigo_barras WHERE ean IS NULL AND codigo_barras IS NOT NULL;

-- Índices de busca rápida
CREATE INDEX IF NOT EXISTS idx_produtos_ean       ON produtos(ean);
CREATE INDEX IF NOT EXISTS idx_produtos_codigo    ON produtos(codigo);
CREATE INDEX IF NOT EXISTS idx_produtos_ncm       ON produtos(ncm);
CREATE INDEX IF NOT EXISTS idx_produtos_nome      ON produtos(nome);