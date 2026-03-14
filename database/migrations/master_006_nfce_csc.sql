-- Adiciona campos CSC (Código de Segurança do Contribuinte) da NFC-e à tabela empresas
-- Consolida configuração NFC-e no master, eliminando duplicidade com nfce_config no banco empresa

ALTER TABLE empresas ADD COLUMN id_csc   TEXT;
ALTER TABLE empresas ADD COLUMN csc_token TEXT;
