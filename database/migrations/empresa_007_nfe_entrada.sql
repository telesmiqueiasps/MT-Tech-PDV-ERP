-- Complementa tabela notas_fiscais com campos faltantes da NF-e
-- O sistema de migrations ignora erros "duplicate column" automaticamente

ALTER TABLE notas_fiscais ADD COLUMN total_bc_icms     REAL DEFAULT 0;
ALTER TABLE notas_fiscais ADD COLUMN total_bc_icms_st  REAL DEFAULT 0;
ALTER TABLE notas_fiscais ADD COLUMN total_icms_st     REAL DEFAULT 0;
ALTER TABLE notas_fiscais ADD COLUMN cond_pagamento    TEXT;
ALTER TABLE notas_fiscais ADD COLUMN info_complementar TEXT;
ALTER TABLE notas_fiscais ADD COLUMN transp_cnpj       TEXT;
ALTER TABLE notas_fiscais ADD COLUMN transp_nome       TEXT;
ALTER TABLE notas_fiscais ADD COLUMN transp_placa      TEXT;
ALTER TABLE notas_fiscais ADD COLUMN transp_uf         TEXT;

-- Complementa itens
ALTER TABLE notas_fiscais_itens ADD COLUMN codigo_fornecedor TEXT;
ALTER TABLE notas_fiscais_itens ADD COLUMN cest              TEXT;
ALTER TABLE notas_fiscais_itens ADD COLUMN bc_icms           REAL DEFAULT 0;
ALTER TABLE notas_fiscais_itens ADD COLUMN bc_icms_st        REAL DEFAULT 0;
ALTER TABLE notas_fiscais_itens ADD COLUMN valor_icms_st     REAL DEFAULT 0;

-- Complementa fornecedores com campos do emitente NF-e
ALTER TABLE fornecedores ADD COLUMN fantasia    TEXT;
ALTER TABLE fornecedores ADD COLUMN logradouro  TEXT;
ALTER TABLE fornecedores ADD COLUMN numero_end  TEXT;
ALTER TABLE fornecedores ADD COLUMN complemento TEXT;
ALTER TABLE fornecedores ADD COLUMN bairro      TEXT;
ALTER TABLE fornecedores ADD COLUMN cidade      TEXT;
ALTER TABLE fornecedores ADD COLUMN cep         TEXT;
ALTER TABLE fornecedores ADD COLUMN fone        TEXT;