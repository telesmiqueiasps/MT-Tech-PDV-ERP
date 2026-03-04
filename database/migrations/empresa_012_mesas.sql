-- Migration 012: adiciona campo reserva_obs na tabela mesas
ALTER TABLE mesas ADD COLUMN reserva_obs TEXT DEFAULT '';
