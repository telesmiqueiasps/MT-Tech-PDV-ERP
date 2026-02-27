CREATE TABLE IF NOT EXISTS municipios (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    cod_uf          TEXT NOT NULL,        -- 2 dígitos: 11, 12...
    uf              TEXT NOT NULL,        -- SP, RJ, MG...
    nome_uf         TEXT NOT NULL,        -- São Paulo, Rio de Janeiro...
    cod_municipio   TEXT NOT NULL UNIQUE, -- 7 dígitos IBGE
    nome_municipio  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_mun_uf   ON municipios(uf);
CREATE INDEX IF NOT EXISTS idx_mun_nome ON municipios(nome_municipio);
CREATE INDEX IF NOT EXISTS idx_mun_cod  ON municipios(cod_municipio);