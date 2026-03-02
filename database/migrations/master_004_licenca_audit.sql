-- ══════════════════════════════════════════════════════════════
-- Migration 004 — Sistema de Licenças + Auditoria Completa
-- ══════════════════════════════════════════════════════════════

-- ── Licenças ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS licencas (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    empresa_id      INTEGER REFERENCES empresas(id),
    chave           TEXT NOT NULL UNIQUE,       -- chave pública (exibida ao cliente)
    chave_hash      TEXT NOT NULL,              -- HMAC-SHA256 da chave
    plano           TEXT NOT NULL DEFAULT 'BASICO', -- BASICO | PRO | ENTERPRISE
    modulos         TEXT NOT NULL DEFAULT '[]', -- JSON: ["pdv","fiscal","estoque",...]
    max_usuarios    INTEGER DEFAULT 3,
    max_empresas    INTEGER DEFAULT 1,
    emitida_em      TEXT DEFAULT (datetime('now','localtime')),
    validade_ate    TEXT,                       -- NULL = sem expiração
    ativada_em      TEXT,
    ultimo_check    TEXT,
    grace_ate       TEXT,                       -- até quando funciona offline
    status          TEXT DEFAULT 'PENDENTE',    -- PENDENTE|ATIVA|EXPIRADA|BLOQUEADA|TRIAL
    fingerprint     TEXT,                       -- hash da máquina ativada
    observacoes     TEXT
);

-- ── Eventos de licença (ativações, renovações, bloqueios) ─────
CREATE TABLE IF NOT EXISTS licenca_eventos (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    licenca_id  INTEGER REFERENCES licencas(id),
    tipo        TEXT NOT NULL,  -- EMISSAO|ATIVACAO|RENOVACAO|BLOQUEIO|CHECK_OK|CHECK_FAIL
    detalhe     TEXT,
    ip          TEXT,
    fingerprint TEXT,
    criado_em   TEXT DEFAULT (datetime('now','localtime'))
);

-- ── Audit log (expandido) ─────────────────────────────────────
-- Recria com mais campos se ainda não existir expandido
CREATE TABLE IF NOT EXISTS audit_log (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    nivel        TEXT DEFAULT 'INFO',   -- INFO|WARN|ERROR|CRITICAL
    origem       TEXT DEFAULT 'APP',    -- APP|SISTEMA|LICENCA
    empresa_id   INTEGER,
    empresa_nome TEXT,
    usuario_id   INTEGER,
    usuario_nome TEXT,
    acao         TEXT NOT NULL,         -- ex: INSERT, UPDATE, DELETE, LOGIN, LOGOUT
    modulo       TEXT,                  -- ex: produtos, notas_fiscais, estoque
    tabela       TEXT,
    registro_id  INTEGER,
    dados_antes  TEXT,                  -- JSON
    dados_depois TEXT,                  -- JSON
    ip           TEXT,
    sessao_id    TEXT,
    detalhe      TEXT,
    criado_em    TEXT DEFAULT (datetime('now','localtime'))
);

CREATE INDEX IF NOT EXISTS idx_audit_empresa   ON audit_log(empresa_id, criado_em DESC);
CREATE INDEX IF NOT EXISTS idx_audit_usuario   ON audit_log(usuario_id, criado_em DESC);
CREATE INDEX IF NOT EXISTS idx_audit_tabela    ON audit_log(tabela, criado_em DESC);
CREATE INDEX IF NOT EXISTS idx_audit_acao      ON audit_log(acao, criado_em DESC);
CREATE INDEX IF NOT EXISTS idx_audit_nivel     ON audit_log(nivel, criado_em DESC);

-- ── Adicionar colunas novas ao audit_log se migration anterior ─
-- SQLite não suporta IF NOT EXISTS em ALTER TABLE.
-- O database.py ignora erros de "duplicate column" automaticamente.
ALTER TABLE audit_log ADD COLUMN origem       TEXT DEFAULT 'APP';
ALTER TABLE audit_log ADD COLUMN empresa_nome TEXT;
ALTER TABLE audit_log ADD COLUMN usuario_nome TEXT;
ALTER TABLE audit_log ADD COLUMN modulo       TEXT;
ALTER TABLE audit_log ADD COLUMN ip           TEXT;
ALTER TABLE audit_log ADD COLUMN sessao_id    TEXT;

-- ── Configurações do sistema (chave/valor global) ─────────────
CREATE TABLE IF NOT EXISTS config_sistema (
    chave     TEXT PRIMARY KEY,
    valor     TEXT,
    descricao TEXT,
    atualizado_em TEXT DEFAULT (datetime('now','localtime'))
);

INSERT OR IGNORE INTO config_sistema (chave, valor, descricao) VALUES
 ('licenca_modo', 'TRIAL', 'Modo atual: TRIAL | ATIVA | OFFLINE'),
 ('trial_dias', '30', 'Dias de trial gratuito'),
 ('grace_period_dias', '7', 'Dias de grace period offline'),
 ('servidor_licenca', 'https://licenca.seu-sistema.com.br', 'URL do servidor de licenças'),
 ('versao_app', '1.0.0', 'Versão atual do aplicativo'),
 ('build', '20260228', 'Build atual');