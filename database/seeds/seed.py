"""
Executado na primeira inicialização para criar o admin global
e os perfis padrão com permissões.
"""
import re
from core.database import DatabaseManager
from core.auth import gerar_hash


def criar_admin_global(login: str, senha: str) -> None:
    db = DatabaseManager.master()
    db.execute(
        "INSERT OR IGNORE INTO admin_global (login, senha_hash) VALUES (?, ?)",
        (login, gerar_hash(senha)),
    )


def criar_empresa(nome: str, cnpj: str = "", razao_social: str = "") -> int:
    from config import DATA_DIR
    db = DatabaseManager.master()

    slug = re.sub(r"[^\w]", "_", nome.lower())[:30]
    existing_ids = db.fetchall("SELECT id FROM empresas")
    suffix = len(existing_ids) + 1
    db_path = DATA_DIR / f"empresa_{slug}_{suffix}.db"

    empresa_id = db.execute(
        "INSERT INTO empresas (nome, razao_social, cnpj, db_path) VALUES (?, ?, ?, ?)",
        (nome, razao_social, cnpj, str(db_path)),
    )

    DatabaseManager.conectar_empresa(db_path)
    return empresa_id


def admin_existe() -> bool:
    db = DatabaseManager.master()
    row = db.fetchone("SELECT COUNT(*) as total FROM admin_global WHERE ativo = 1")
    return row["total"] > 0


def criar_perfis_padrao() -> None:
    from config import PERMISSOES
    db = DatabaseManager.empresa()

    perfis = [
        ("Administrador", "Acesso total ao sistema"),
        ("Gerente",       "Acesso a vendas, estoque e relatórios"),
        ("Vendedor",      "Acesso ao PDV e cadastros básicos"),
        ("Estoquista",    "Acesso ao estoque e produtos"),
        ("Financeiro",    "Acesso ao financeiro e relatórios"),
    ]

    permissoes_por_perfil = {
        # Administrador: tudo que existe em PERMISSOES
        "Administrador": {
            f"{m}:{a}": True
            for m, acoes in PERMISSOES.items()
            for a in acoes
        },
        # Gerente: PDV completo + estoque + produtos + clientes + relatórios
        "Gerente": {
            # PDV
            "pdv:ver": True, "pdv:vender": True, "pdv:desconto": True,
            "pdv:cancelar": True, "pdv:abrir_caixa": True,
            "pdv:fechar_caixa": True, "pdv:sangria": True, "pdv:mesas": True,
            # Estoque
            "estoque:ver": True, "estoque:criar": True, "estoque:editar": True,
            "estoque:ajuste": True,
            # Produtos / Clientes / Fornecedores
            "produtos:ver": True, "produtos:criar": True, "produtos:editar": True,
            "clientes:ver": True, "clientes:criar": True, "clientes:editar": True,
            "fornecedores:ver": True,
            # Financeiro / Relatórios
            "financeiro:ver": True, "financeiro:criar": True,
            "relatorios:ver": True, "relatorios:exportar": True,
        },
        # Vendedor: PDV básico + mesas + cadastros de consulta
        "Vendedor": {
            "pdv:ver": True, "pdv:vender": True, "pdv:mesas": True,
            "produtos:ver": True,
            "clientes:ver": True, "clientes:criar": True,
        },
        # Estoquista: estoque e produtos
        "Estoquista": {
            "estoque:ver": True, "estoque:criar": True,
            "estoque:editar": True, "estoque:ajuste": True,
            "produtos:ver": True, "produtos:criar": True, "produtos:editar": True,
            "fornecedores:ver": True,
        },
        # Financeiro: financeiro + relatórios + caixa
        "Financeiro": {
            "financeiro:ver": True, "financeiro:criar": True,
            "financeiro:editar": True, "financeiro:fechar_caixa": True,
            "pdv:ver": True, "pdv:abrir_caixa": True,
            "pdv:fechar_caixa": True, "pdv:sangria": True,
            "relatorios:ver": True, "relatorios:exportar": True,
        },
    }

    for nome, descricao in perfis:
        existing = db.fetchone("SELECT id FROM perfis WHERE nome = ?", (nome,))
        if existing:
            perfil_id = existing["id"]
        else:
            perfil_id = db.lastrowid(
                "INSERT INTO perfis (nome, descricao) VALUES (?, ?)",
                (nome, descricao),
            )

        db.execute("DELETE FROM permissoes WHERE perfil_id = ?", (perfil_id,))
        for chave, permitido in permissoes_por_perfil.get(nome, {}).items():
            modulo, acao = chave.split(":", 1)
            db.execute(
                "INSERT INTO permissoes (perfil_id, modulo, acao, permitido) VALUES (?, ?, ?, ?)",
                (perfil_id, modulo, acao, int(permitido)),
            )