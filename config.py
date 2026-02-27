from pathlib import Path

# ── Diretórios ────────────────────────────────────────────────
BASE_DIR       = Path(__file__).resolve().parent
DATA_DIR       = BASE_DIR / "database" / "empresas"
MIGRATIONS_DIR = BASE_DIR / "database" / "migrations"

DATA_DIR.mkdir(parents=True, exist_ok=True)

MASTER_DB = DATA_DIR / "master.db"

# ── App ───────────────────────────────────────────────────────
APP_NAME    = "MT Tech - PDV & ERP"
APP_VERSION = "1.0.0"

# ── Tema ─────────────────────────────────────────────────────
THEME = {
    # Fundos
    "bg":           "#F0F2F5",
    "bg_card":      "#FFFFFF",
    "bg_sidebar":   "#2C78AC",
    "bg_input":     "#FFFFFF",
    # Texto
    "fg":           "#1A2332",
    "fg_light":     "#6B7A8D",
    "fg_white":     "#FFFFFF",
    # Marca
    "primary":      "#2E86C1",
    "primary_dark": "#2C78AC",
    "primary_light":"#D6EAF8",
    # Status
    "success":      "#1E8449",
    "success_light":"#D5F5E3",
    "warning":      "#D68910",
    "warning_light":"#FEF9E7",
    "danger":       "#C0392B",
    "danger_light": "#FADBD8",
    # Estrutura
    "border":       "#D5D8DC",
    "border_dark":  "#AEB6BF",
    "hover":        "#EBF5FB",
    "row_alt":      "#F5F7FA",
    # Seções de formulário
    "section_bg":   "#EBF5FB",
    "section_fg":   "#2C78AC",
}

FONT = {
    "xs":    ("Segoe UI", 9),
    "sm":    ("Segoe UI", 10),
    "md":    ("Segoe UI", 11),
    "lg":    ("Segoe UI", 13),
    "xl":    ("Segoe UI", 16),
    "bold":  ("Segoe UI", 11, "bold"),
    "title": ("Segoe UI", 16, "bold"),
    "mono":  ("Consolas", 10),
}

# ── Permissões ────────────────────────────────────────────────
PERMISSOES = {
    "pdv":          ["ver", "vender", "desconto", "cancelar"],
    "produtos":     ["ver", "criar", "editar", "deletar"],
    "clientes":     ["ver", "criar", "editar", "deletar"],
    "fornecedores": ["ver", "criar", "editar", "deletar"],
    "estoque":      ["ver", "criar", "editar", "ajuste"],
    "fiscal":       ["ver", "criar", "editar", "deletar"],
    "financeiro":   ["ver", "criar", "editar", "fechar_caixa"],
    "relatorios":   ["ver", "exportar"],
    "admin":        ["ver", "usuarios", "perfis", "empresas"],
    "fiscal_cfg":   ["ver", "criar", "editar", "deletar"],
}