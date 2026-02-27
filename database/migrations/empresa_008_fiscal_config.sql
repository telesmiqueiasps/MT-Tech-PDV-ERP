-- ══════════════════════════════════════════════════════════════════════════
-- Migration 008 — Configurações Fiscais & Fechamentos (schema unificado)
-- O sistema de migrations ignora "duplicate column" e "table already exists"
-- ══════════════════════════════════════════════════════════════════════════

-- ── Tabela CFOP ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS fiscal_cfop (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo      TEXT NOT NULL UNIQUE,
    descricao   TEXT NOT NULL,
    tipo_op     TEXT NOT NULL,        -- ENTRADA | SAIDA | DEV_COMPRA | DEV_VENDA
    situacao    TEXT NOT NULL DEFAULT 'A', -- A=Intraestadual B=Inter C=Exterior
    ativo       INTEGER DEFAULT 1,
    obs         TEXT
);

-- ── Tabela CST ICMS / CSOSN ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS fiscal_cst_icms (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo      TEXT NOT NULL UNIQUE,
    regime      TEXT NOT NULL DEFAULT 'N',  -- N=Normal S=Simples
    descricao   TEXT NOT NULL,
    ativo       INTEGER DEFAULT 1
);

-- ── Tabela CST PIS / COFINS ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS fiscal_cst_pis_cofins (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo      TEXT NOT NULL UNIQUE,
    descricao   TEXT NOT NULL,
    ativo       INTEGER DEFAULT 1
);

-- ── Alíquotas ICMS por par UF ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS fiscal_aliq_icms (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    uf_origem   TEXT NOT NULL,
    uf_destino  TEXT NOT NULL,
    aliquota    REAL NOT NULL DEFAULT 0,
    vigencia    TEXT,
    ativo       INTEGER DEFAULT 1,
    UNIQUE(uf_origem, uf_destino)
);

-- ── Regras fiscais de negócio ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS fiscal_regras (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    nome            TEXT NOT NULL,
    tipo_op         TEXT NOT NULL,
    situacao        TEXT NOT NULL DEFAULT 'A',
    cfop_id         INTEGER REFERENCES fiscal_cfop(id),
    cst_icms_id     INTEGER REFERENCES fiscal_cst_icms(id),
    cst_pis_cod     TEXT,
    cst_cofins_cod  TEXT,
    aliq_icms       REAL DEFAULT 0,
    aliq_pis        REAL DEFAULT 0,
    aliq_cofins     REAL DEFAULT 0,
    aliq_ipi        REAL DEFAULT 0,
    ativo           INTEGER DEFAULT 1,
    obs             TEXT
);

-- ── Fechamentos fiscais mensais ───────────────────────────────────────────
CREATE TABLE IF NOT EXISTS fiscal_fechamentos (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    competencia  TEXT NOT NULL UNIQUE,   -- "AAAA-MM"
    status       TEXT NOT NULL DEFAULT 'ABERTO',
    fechado_em   TEXT,
    fechado_por  TEXT,
    reaberto_em  TEXT,
    reaberto_por TEXT,
    obs          TEXT,
    criado_em    TEXT DEFAULT (datetime('now','localtime'))
);

-- ══════════════════════════════════════════════════════════════════════════
-- SEEDS — CFOPs de Entrada (Intraestadual)
-- ══════════════════════════════════════════════════════════════════════════
INSERT OR IGNORE INTO fiscal_cfop (codigo,descricao,tipo_op,situacao) VALUES
 ('1101','Compra p/ industrialização','ENTRADA','A'),
 ('1102','Compra p/ comercialização','ENTRADA','A'),
 ('1111','Compra p/ indust. fora do prazo de validade','ENTRADA','A'),
 ('1116','Compra p/ indust. em zona de processamento de exportação','ENTRADA','A'),
 ('1122','Compra p/ industrialização — zona franca','ENTRADA','A'),
 ('1151','Transferência p/ industrialização','ENTRADA','A'),
 ('1152','Transferência p/ comercialização','ENTRADA','A'),
 ('1201','Devolução de venda de produção própria','ENTRADA','A'),
 ('1202','Devolução de venda de mercadoria adquirida','ENTRADA','A'),
 ('1401','Compra p/ comercialização em operação c/ ST','ENTRADA','A'),
 ('1403','Compra p/ comercialização — merc. sujeita ST','ENTRADA','A'),
 ('1407','Compra de merc. p/ uso/consumo cuja operação tem ST','ENTRADA','A'),
 ('1411','Devolução de venda de merc. adquirida c/ ST','ENTRADA','A'),
 ('1552','Transferência de bem do ativo imobilizado','ENTRADA','A'),
 ('1556','Compra de material p/ uso/consumo','ENTRADA','A'),
 ('1557','Compra de bem p/ ativo imobilizado','ENTRADA','A'),
 ('1601','Recebimento pelo processo de ST, de mercadoria c/ ST retida','ENTRADA','A'),
 ('1603','Ressarcimento de ICMS retido por ST','ENTRADA','A'),
 -- Entrada Interestadual
 ('2101','Compra p/ industrialização','ENTRADA','B'),
 ('2102','Compra p/ comercialização','ENTRADA','B'),
 ('2111','Compra p/ indust. fora do prazo de validade','ENTRADA','B'),
 ('2152','Transferência p/ comercialização','ENTRADA','B'),
 ('2201','Devolução de venda de produção própria','ENTRADA','B'),
 ('2202','Devolução de venda de mercadoria adquirida','ENTRADA','B'),
 ('2401','Compra p/ comercialização em operação c/ ST','ENTRADA','B'),
 ('2403','Compra p/ comercialização — merc. sujeita ST','ENTRADA','B'),
 ('2407','Compra de merc. p/ uso/consumo c/ ST','ENTRADA','B'),
 ('2411','Devolução de venda de merc. adquirida c/ ST','ENTRADA','B'),
 ('2556','Compra de material p/ uso/consumo','ENTRADA','B'),
 ('2557','Compra de bem p/ ativo imobilizado','ENTRADA','B'),
 ('2603','Ressarcimento de ICMS retido por ST','ENTRADA','B'),
 -- Saídas Intraestadual
 ('5101','Venda de produção do estabelecimento','SAIDA','A'),
 ('5102','Venda de mercadoria adquirida','SAIDA','A'),
 ('5103','Venda de produção do estab. — zona franca','SAIDA','A'),
 ('5104','Venda de merc. adquirida — zona franca','SAIDA','A'),
 ('5109','Venda de produção de terceiros','SAIDA','A'),
 ('5110','Venda de merc. adquirida — exportação','SAIDA','A'),
 ('5401','Venda de produção c/ ST — contribuinte substituto','SAIDA','A'),
 ('5403','Venda de merc. adquirida c/ ST — contribuinte substituto','SAIDA','A'),
 ('5405','Venda de merc. adquirida c/ ST — contribuinte substituído','SAIDA','A'),
 ('5501','Remessa de produção p/ industrialização','SAIDA','A'),
 ('5503','Remessa de merc. adquirida p/ industrialização','SAIDA','A'),
 ('5551','Venda de bem do ativo imobilizado','SAIDA','A'),
 ('5553','Devolução de compra de energia elétrica','SAIDA','A'),
 ('5556','Venda de material de uso/consumo','SAIDA','A'),
 ('5605','Transferência de saldo de ICMS-ST','SAIDA','A'),
 -- Saídas Interestadual
 ('6101','Venda de produção do estabelecimento','SAIDA','B'),
 ('6102','Venda de mercadoria adquirida','SAIDA','B'),
 ('6104','Venda de merc. adquirida — zona franca','SAIDA','B'),
 ('6109','Venda de produção de terceiros','SAIDA','B'),
 ('6401','Venda de produção c/ ST','SAIDA','B'),
 ('6403','Venda de merc. adquirida c/ ST','SAIDA','B'),
 ('6501','Remessa de produção p/ industrialização','SAIDA','B'),
 ('6551','Venda de bem do ativo imobilizado','SAIDA','B'),
 ('6556','Venda de material de uso/consumo','SAIDA','B'),
 -- Devoluções de compra
 ('5201','Devolução de compra de produção própria','DEV_COMPRA','A'),
 ('5202','Devolução de compra de merc. adquirida','DEV_COMPRA','A'),
 ('5410','Devolução de compra c/ ST — contribuinte substituto','DEV_COMPRA','A'),
 ('5411','Devolução de compra c/ ST — contribuinte substituído','DEV_COMPRA','A'),
 ('6201','Devolução de compra de produção própria','DEV_COMPRA','B'),
 ('6202','Devolução de compra de merc. adquirida','DEV_COMPRA','B'),
 ('6410','Devolução de compra c/ ST','DEV_COMPRA','B'),
 -- Devoluções de venda
 ('1201','Devolução de venda de produção própria','DEV_VENDA','A'),
 ('1202','Devolução de venda de merc. adquirida','DEV_VENDA','A'),
 ('2201','Devolução de venda de produção própria','DEV_VENDA','B'),
 ('2202','Devolução de venda de merc. adquirida','DEV_VENDA','B');

-- ══════════════════════════════════════════════════════════════════════════
-- SEEDS — CST ICMS Regime Normal
-- ══════════════════════════════════════════════════════════════════════════
INSERT OR IGNORE INTO fiscal_cst_icms (codigo,regime,descricao) VALUES
 ('00','N','00 — Tributada integralmente'),
 ('10','N','10 — Tributada e c/ cobrança de ICMS-ST'),
 ('20','N','20 — Com redução de base de cálculo'),
 ('30','N','30 — Isenta/não tributada e c/ cobrança de ICMS-ST'),
 ('40','N','40 — Isenta'),
 ('41','N','41 — Não tributada'),
 ('50','N','50 — Suspensão'),
 ('51','N','51 — Diferimento'),
 ('60','N','60 — ICMS cobrado anteriormente por ST'),
 ('70','N','70 — Com redução de BC e c/ cobrança de ICMS-ST'),
 ('90','N','90 — Outros — Regime Normal');

-- SEEDS — CSOSN Simples Nacional
INSERT OR IGNORE INTO fiscal_cst_icms (codigo,regime,descricao) VALUES
 ('101','S','101 — Tributada pelo SN c/ permissão de crédito'),
 ('102','S','102 — Tributada pelo SN s/ permissão de crédito'),
 ('103','S','103 — Isenção do ICMS p/ faixa de receita bruta'),
 ('201','S','201 — SN c/ permissão de crédito e c/ ST'),
 ('202','S','202 — SN s/ permissão de crédito e c/ ST'),
 ('203','S','203 — Isenção do ICMS e c/ ST'),
 ('300','S','300 — Imune'),
 ('400','S','400 — Não tributada pelo Simples Nacional'),
 ('500','S','500 — ICMS cobrado anteriormente por ST ou antecipação'),
 ('900','S','900 — Outros — Simples Nacional');

-- ══════════════════════════════════════════════════════════════════════════
-- SEEDS — CST PIS / COFINS
-- ══════════════════════════════════════════════════════════════════════════
INSERT OR IGNORE INTO fiscal_cst_pis_cofins (codigo,descricao) VALUES
 ('01','01 — Operação tributável — alíquota básica'),
 ('02','02 — Operação tributável — alíquota diferenciada'),
 ('03','03 — Operação tributável — alíquota por unidade de medida'),
 ('04','04 — Operação tributável — monofásica — alíquota zero'),
 ('05','05 — Operação tributável — substituição tributária'),
 ('06','06 — Operação tributável — alíquota zero'),
 ('07','07 — Operação isenta da contribuição'),
 ('08','08 — Operação s/ incidência da contribuição'),
 ('09','09 — Operação c/ suspensão da contribuição'),
 ('49','49 — Outras operações de saída'),
 ('50','50 — Op. c/ direito a crédito — receita tributada mercado interno'),
 ('51','51 — Op. c/ direito a crédito — receita não tributada mercado interno'),
 ('52','52 — Op. c/ direito a crédito — receita de exportação'),
 ('53','53 — Op. c/ direito a crédito — receita tributada e não tributada'),
 ('54','54 — Op. c/ direito a crédito — receita tributada e exportação'),
 ('55','55 — Op. c/ direito a crédito — receita não tributada e exportação'),
 ('56','56 — Op. c/ direito a crédito — todas as receitas'),
 ('60','60 — Crédito presumido — op. de aquisição vinculada receita tributada'),
 ('61','61 — Crédito presumido — op. de aquisição vinculada receita não tributada'),
 ('62','62 — Crédito presumido — op. de aquisição vinculada a todas as receitas'),
 ('63','63 — Crédito presumido — outras situações'),
 ('70','70 — Op. de aquisição s/ direito a crédito'),
 ('71','71 — Op. de aquisição c/ isenção'),
 ('72','72 — Op. de aquisição c/ suspensão'),
 ('73','73 — Op. de aquisição a alíquota zero'),
 ('74','74 — Op. de aquisição s/ incidência'),
 ('75','75 — Op. de aquisição por ST'),
 ('98','98 — Outras operações de entrada'),
 ('99','99 — Outras operações');

-- ══════════════════════════════════════════════════════════════════════════
-- SEEDS — Alíquotas ICMS internas (operações dentro do mesmo estado)
-- ══════════════════════════════════════════════════════════════════════════
INSERT OR IGNORE INTO fiscal_aliq_icms (uf_origem,uf_destino,aliquota) VALUES
 ('AC','AC',17), ('AL','AL',19), ('AM','AM',20), ('AP','AP',18),
 ('BA','BA',19), ('CE','CE',18), ('DF','DF',18), ('ES','ES',17),
 ('GO','GO',17), ('MA','MA',20), ('MG','MG',18), ('MS','MS',17),
 ('MT','MT',17), ('PA','PA',19), ('PB','PB',18), ('PE','PE',20.5),
 ('PI','PI',21), ('PR','PR',19), ('RJ','RJ',20), ('RN','RN',18),
 ('RO','RO',17.5),('RR','RR',17),('RS','RS',17), ('SC','SC',17),
 ('SE','SE',19), ('SP','SP',18), ('TO','TO',20);

-- Alíquotas interestaduais (tabela ICMS de referência 2024)
-- SP/MG/RS/PR/SC → demais = 7%
-- Demais estados → demais = 12% (simplificado, ajuste conforme legislação vigente)
INSERT OR IGNORE INTO fiscal_aliq_icms (uf_origem,uf_destino,aliquota) VALUES
 ('SP','RJ',7),('SP','MG',12),('SP','BA',7),('SP','GO',7),('SP','PR',12),
 ('MG','SP',12),('MG','RJ',12),('MG','BA',7),('MG','GO',12),
 ('RS','SP',7),('RS','MG',7),('RS','PR',12),('RS','SC',12),('RS','RJ',7),
 ('PR','SP',12),('PR','MG',12),('PR','RS',12),('PR','SC',12),
 ('SC','SP',7),('SC','MG',7),('SC','PR',12),('SC','RS',12);

-- ══════════════════════════════════════════════════════════════════════════
-- SEEDS — Regras de negócio padrão
-- ══════════════════════════════════════════════════════════════════════════
INSERT OR IGNORE INTO fiscal_regras
 (nome,tipo_op,situacao,cfop_id,cst_icms_id,cst_pis_cod,cst_cofins_cod,aliq_icms,aliq_pis,aliq_cofins)
SELECT
 'Compra p/ comercialização — Intraestadual',
 'ENTRADA','A',
 (SELECT id FROM fiscal_cfop WHERE codigo='1102' LIMIT 1),
 (SELECT id FROM fiscal_cst_icms WHERE codigo='00' LIMIT 1),
 '50','50', 18.0, 0.65, 3.00
WHERE NOT EXISTS (SELECT 1 FROM fiscal_regras WHERE nome='Compra p/ comercialização — Intraestadual');

INSERT OR IGNORE INTO fiscal_regras
 (nome,tipo_op,situacao,cfop_id,cst_icms_id,cst_pis_cod,cst_cofins_cod,aliq_icms,aliq_pis,aliq_cofins)
SELECT
 'Compra p/ comercialização — Interestadual',
 'ENTRADA','B',
 (SELECT id FROM fiscal_cfop WHERE codigo='2102' LIMIT 1),
 (SELECT id FROM fiscal_cst_icms WHERE codigo='00' LIMIT 1),
 '50','50', 12.0, 0.65, 3.00
WHERE NOT EXISTS (SELECT 1 FROM fiscal_regras WHERE nome='Compra p/ comercialização — Interestadual');

INSERT OR IGNORE INTO fiscal_regras
 (nome,tipo_op,situacao,cfop_id,cst_icms_id,cst_pis_cod,cst_cofins_cod,aliq_icms,aliq_pis,aliq_cofins)
SELECT
 'Venda de mercadoria — Intraestadual',
 'SAIDA','A',
 (SELECT id FROM fiscal_cfop WHERE codigo='5102' LIMIT 1),
 (SELECT id FROM fiscal_cst_icms WHERE codigo='00' LIMIT 1),
 '01','01', 18.0, 0.65, 3.00
WHERE NOT EXISTS (SELECT 1 FROM fiscal_regras WHERE nome='Venda de mercadoria — Intraestadual');

INSERT OR IGNORE INTO fiscal_regras
 (nome,tipo_op,situacao,cfop_id,cst_icms_id,cst_pis_cod,cst_cofins_cod,aliq_icms,aliq_pis,aliq_cofins)
SELECT
 'Venda de mercadoria — Interestadual',
 'SAIDA','B',
 (SELECT id FROM fiscal_cfop WHERE codigo='6102' LIMIT 1),
 (SELECT id FROM fiscal_cst_icms WHERE codigo='00' LIMIT 1),
 '01','01', 12.0, 0.65, 3.00
WHERE NOT EXISTS (SELECT 1 FROM fiscal_regras WHERE nome='Venda de mercadoria — Interestadual');

INSERT OR IGNORE INTO fiscal_regras
 (nome,tipo_op,situacao,cfop_id,cst_icms_id,cst_pis_cod,cst_cofins_cod,aliq_icms,aliq_pis,aliq_cofins)
SELECT
 'Devolução de compra — Intraestadual',
 'DEV_COMPRA','A',
 (SELECT id FROM fiscal_cfop WHERE codigo='5202' LIMIT 1),
 (SELECT id FROM fiscal_cst_icms WHERE codigo='00' LIMIT 1),
 '01','01', 18.0, 0.65, 3.00
WHERE NOT EXISTS (SELECT 1 FROM fiscal_regras WHERE nome='Devolução de compra — Intraestadual');

INSERT OR IGNORE INTO fiscal_regras
 (nome,tipo_op,situacao,cfop_id,cst_icms_id,cst_pis_cod,cst_cofins_cod,aliq_icms,aliq_pis,aliq_cofins)
SELECT
 'Devolução de venda — Intraestadual',
 'DEV_VENDA','A',
 (SELECT id FROM fiscal_cfop WHERE codigo='1202' LIMIT 1),
 (SELECT id FROM fiscal_cst_icms WHERE codigo='00' LIMIT 1),
 '50','50', 18.0, 0.65, 3.00
WHERE NOT EXISTS (SELECT 1 FROM fiscal_regras WHERE nome='Devolução de venda — Intraestadual');