from config import PERMISSOES, DATA_DIR
from core.database import DatabaseManager
from core.auth import gerar_hash


def admin_existe() -> bool:
    row = DatabaseManager.master().fetchone(
        "SELECT COUNT(*) as total FROM admin_global WHERE ativo = 1"
    )
    return row["total"] > 0


def criar_admin_global(login: str, senha: str):
    DatabaseManager.master().execute(
        "INSERT OR IGNORE INTO admin_global (login, senha_hash) VALUES (?, ?)",
        (login, gerar_hash(senha)),
    )


def criar_empresa(nome: str, cnpj: str = "", razao_social: str = "") -> dict:
    slug    = nome.lower().replace(" ", "_")[:30]
    db_dir  = DATA_DIR / f"empresa_{slug}"
    db_dir.mkdir(parents=True, exist_ok=True)
    db_path = db_dir / "dados.db"

    empresa_id = DatabaseManager.master().execute(
        "INSERT INTO empresas (nome, cnpj, razao_social, db_path) VALUES (?, ?, ?, ?)",
        (nome, cnpj, razao_social, str(db_path)),
    )

    DatabaseManager.conectar_empresa(db_path)
    criar_perfis_padrao()

    return {"id": empresa_id, "nome": nome, "db_path": str(db_path)}


def criar_perfis_padrao():
    db = DatabaseManager.empresa()

    perfis = {
        "Administrador": {f"{m}:{a}": True for m, acoes in PERMISSOES.items() for a in acoes},
        "Gerente": {
            "pdv:ver": True, "pdv:vender": True, "pdv:desconto": True, "pdv:cancelar": True,
            "produtos:ver": True, "produtos:criar": True, "produtos:editar": True,
            "clientes:ver": True, "clientes:criar": True, "clientes:editar": True,
            "estoque:ver": True, "estoque:criar": True, "estoque:editar": True,
            "financeiro:ver": True,
            "relatorios:ver": True, "relatorios:exportar": True,
        },
        "Operador de Caixa": {
            "pdv:ver": True, "pdv:vender": True,
            "produtos:ver": True,
            "clientes:ver": True, "clientes:criar": True,
        },
        "Estoquista": {
            "produtos:ver": True, "produtos:criar": True, "produtos:editar": True,
            "estoque:ver": True, "estoque:criar": True, "estoque:editar": True, "estoque:ajuste": True,
            "fornecedores:ver": True,
        },
    }

    for nome_perfil, permissoes in perfis.items():
        existing = db.fetchone("SELECT id FROM perfis WHERE nome = ?", (nome_perfil,))
        if existing:
            perfil_id = existing["id"]
        else:
            perfil_id = db.execute(
                "INSERT INTO perfis (nome) VALUES (?)", (nome_perfil,)
            )

        db.execute("DELETE FROM permissoes WHERE perfil_id = ?", (perfil_id,))
        rows = [
            (perfil_id, chave.split(":")[0], chave.split(":")[1], 1)
            for chave, ok in permissoes.items() if ok
        ]
        if rows:
            db.executemany(
                "INSERT INTO permissoes (perfil_id, modulo, acao, permitido) VALUES (?,?,?,?)",
                rows,
            )

    # Cria usuário admin padrão da empresa
    perfil_admin = db.fetchone("SELECT id FROM perfis WHERE nome = 'Administrador'")
    if perfil_admin and not db.fetchone("SELECT id FROM usuarios WHERE login = 'admin'"):
        db.execute(
            "INSERT INTO usuarios (nome, login, senha_hash, perfil_id) VALUES (?,?,?,?)",
            ("Administrador", "admin", gerar_hash("admin123"), perfil_admin["id"]),
        )