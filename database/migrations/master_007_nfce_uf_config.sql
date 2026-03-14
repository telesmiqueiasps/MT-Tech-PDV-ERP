-- Configuração NFC-e por UF (estado)
-- Permite que cada empresa/estado tenha suas URLs e parâmetros próprios
-- sem necessidade de alteração de código.
--
-- Campos WS (WebService): NULL = usar SVRS centralizado (padrão nacional).
-- Campos URL QR Code: URL base da SEFAZ do estado para QR Code / consulta.
-- A maioria dos estados usa o SVRS do RS como centralizador de NFC-e.
-- Exceções conhecidas: SP, MG, AM (têm WebServices próprios).

CREATE TABLE IF NOT EXISTS nfce_uf_config (
    uf                      TEXT PRIMARY KEY,   -- sigla: 'PB', 'SP', etc.
    c_uf                    TEXT NOT NULL,       -- código IBGE: '25', '35', etc.
    fuso_horario            TEXT NOT NULL DEFAULT '-03:00',  -- offset UTC
    url_qrcode_hom          TEXT,               -- URL base QR Code homologação
    url_qrcode_prod         TEXT,               -- URL base QR Code produção
    ws_autorizacao_hom      TEXT,               -- NULL = SVRS padrão
    ws_autorizacao_prod     TEXT,               -- NULL = SVRS padrão
    ws_ret_autorizacao_hom  TEXT,               -- NULL = SVRS padrão
    ws_ret_autorizacao_prod TEXT,               -- NULL = SVRS padrão
    ws_status_hom           TEXT,               -- NULL = SVRS padrão
    ws_status_prod          TEXT,               -- NULL = SVRS padrão
    ws_evento_hom           TEXT,               -- NULL = SVRS padrão
    ws_evento_prod          TEXT,               -- NULL = SVRS padrão
    obs                     TEXT
);

-- ── Seed: todos os 27 estados ─────────────────────────────────────────────
-- Fonte QR Codes: Portal SEFAZ de cada UF / NT 2019.001
-- WS NULL = centralizado SVRS (nfce-homologacao.svrs.rs.gov.br)
-- Estados com WS próprio: SP, MG, AM (preencher manualmente se necessário)

INSERT OR IGNORE INTO nfce_uf_config (uf, c_uf, fuso_horario, url_qrcode_hom, url_qrcode_prod) VALUES
  -- Norte
  ('AC', '12', '-05:00', 'https://www.sefaznet.ac.gov.br/nfce/qrcode', 'https://www.sefaznet.ac.gov.br/nfce/qrcode'),
  ('AM', '13', '-04:00', 'https://homnfce.sefaz.am.gov.br/nfceweb/fornarfce.do', 'https://nfce.sefaz.am.gov.br/nfceweb/fornarfce.do'),
  ('AP', '16', '-03:00', NULL, NULL),
  ('PA', '15', '-03:00', NULL, NULL),
  ('RO', '11', '-04:00', NULL, NULL),
  ('RR', '14', '-04:00', NULL, NULL),
  ('TO', '17', '-03:00', NULL, NULL),
  -- Nordeste
  ('AL', '27', '-03:00', NULL, NULL),
  ('BA', '29', '-03:00', 'http://nfe.sefaz.ba.gov.br/servicos/nfce/qrcode.aspx', 'http://nfe.sefaz.ba.gov.br/servicos/nfce/qrcode.aspx'),
  ('CE', '23', '-03:00', 'http://nfceh.sefaz.ce.gov.br/pages/showNFCe.html', 'http://nfce.sefaz.ce.gov.br/pages/showNFCe.html'),
  ('MA', '21', '-03:00', NULL, NULL),
  ('PB', '25', '-03:00', 'http://www.sefaz.pb.gov.br/nfcehom', 'http://www.sefaz.pb.gov.br/nfce'),
  ('PE', '26', '-03:00', 'http://nfcehomolog.sefaz.pe.gov.br/nfce-web/consulta', 'http://nfce.sefaz.pe.gov.br/nfce-web/consulta'),
  ('PI', '22', '-03:00', NULL, NULL),
  ('RN', '24', '-03:00', NULL, NULL),
  ('SE', '28', '-03:00', NULL, NULL),
  -- Centro-Oeste
  ('DF', '53', '-03:00', NULL, NULL),
  ('GO', '52', '-03:00', 'http://homolog.sefaz.go.gov.br/nfeweb/sites/nfce/danfeNFCe.html', 'http://nfe.sefaz.go.gov.br/nfeweb/sites/nfce/danfeNFCe.html'),
  ('MS', '50', '-04:00', NULL, NULL),
  ('MT', '51', '-04:00', NULL, NULL),
  -- Sudeste
  ('ES', '32', '-03:00', NULL, NULL),
  ('MG', '31', '-03:00', 'https://hnfce.fazenda.mg.gov.br/nfce/consulta', 'https://nfce.fazenda.mg.gov.br/nfce/consulta'),
  ('RJ', '33', '-03:00', NULL, NULL),
  ('SP', '35', '-03:00', 'https://www.homologacao.nfce.fazenda.sp.gov.br/qrcode', 'https://www.nfce.fazenda.sp.gov.br/qrcode'),
  -- Sul
  ('PR', '41', '-03:00', NULL, NULL),
  ('RS', '43', '-03:00', 'https://www.sefaz.rs.gov.br/NFCE/NFCE-COM.aspx', 'https://www.sefaz.rs.gov.br/NFCE/NFCE-COM.aspx'),
  ('SC', '42', '-03:00', NULL, NULL);

-- WebServices próprios para SP, MG, AM
-- (preencher se necessário — NULL usa SVRS centralizado como fallback)
-- UPDATE nfce_uf_config SET
--   ws_autorizacao_hom='https://homologacao.nfce.fazenda.sp.gov.br/ws/NFeAutorizacao4.asmx',
--   ws_autorizacao_prod='https://nfce.fazenda.sp.gov.br/ws/NFeAutorizacao4.asmx'
-- WHERE uf='SP';
