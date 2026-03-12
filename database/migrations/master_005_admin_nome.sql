-- Migration: master_005_admin_nome.sql
-- Adiciona campo nome ao admin_global para exibição amigável no sistema.
ALTER TABLE admin_global ADD COLUMN nome TEXT NOT NULL DEFAULT '';
