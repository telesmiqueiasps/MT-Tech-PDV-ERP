import hashlib
import secrets
from core.database import DatabaseManager
from core.session import Session


class AuthError(Exception):
    pass


class LicencaAuthError(AuthError):
    """Levantado quando o login falha exclusivamente por problema de licença."""
    pass


def gerar_hash(senha: str) -> str:
    salt = secrets.token_hex(16)
    h    = hashlib.sha256(f"{salt}{senha}".encode()).hexdigest()
    return f"{salt}${h}"


def verificar_senha(senha: str, senha_hash: str) -> bool:
    try:
        salt, _ = senha_hash.split("$")
        h = hashlib.sha256(f"{salt}{senha}".encode()).hexdigest()
        return f"{salt}${h}" == senha_hash
    except Exception:
        return False


class Auth:
    @classmethod
    def login_admin_global(cls, login: str, senha: str):
        from core.audit import Audit
        db  = DatabaseManager.master()
        row = db.fetchone(
            "SELECT * FROM admin_global WHERE login = ? AND ativo = 1", (login,)
        )
        if not row or not verificar_senha(senha, row["senha_hash"]):
            Audit.registrar(
                acao="LOGIN_FALHA", modulo="auth", nivel="WARN",
                usuario_nome=login, empresa_nome="Administração Global",
                detalhe="Senha inválida ou usuário não encontrado",
            )
            raise AuthError("Login ou senha inválidos.")

        Session.iniciar(
            usuario    = {**row, "is_admin_global": True},
            empresa    = {"id": 0, "nome": "Administração Global"},
            permissoes = {},
        )
        Audit.registrar(
            acao="LOGIN", modulo="auth", nivel="INFO",
            usuario_nome=login, empresa_nome="Administração Global",
            detalhe="Login admin global",
        )

    @classmethod
    def login_empresa(cls, login: str, senha: str, empresa: dict):
        from core.audit import Audit
        db  = DatabaseManager.empresa()
        row = db.fetchone(
            """
            SELECT u.*, p.nome as perfil_nome
            FROM usuarios u
            LEFT JOIN perfis p ON p.id = u.perfil_id
            WHERE u.login = ? AND u.ativo = 1
            """,
            (login,),
        )
        if not row or not verificar_senha(senha, row["senha_hash"]):
            Audit.registrar(
                acao="LOGIN_FALHA", modulo="auth", nivel="WARN",
                usuario_nome=login,
                empresa_id=empresa.get("id"),
                empresa_nome=empresa.get("nome", ""),
                detalhe="Senha inválida ou usuário não encontrado",
            )
            raise AuthError("Login ou senha inválidos.")

        permissoes = cls._carregar_permissoes(row["perfil_id"])

        Session.iniciar(
            usuario    = {**row, "is_admin_global": False},
            empresa    = empresa,
            permissoes = permissoes,
        )
        Audit.registrar(
            acao="LOGIN", modulo="auth", nivel="INFO",
            usuario_id=row["id"], usuario_nome=row.get("nome") or login,
            empresa_id=empresa.get("id"),
            empresa_nome=empresa.get("nome", ""),
            detalhe=f"Perfil: {row.get('perfil_nome', '—')}",
        )

        # ── Verifica licença para esta empresa ──────────────
        try:
            from models.licenca import Licenca
            cnpj = empresa.get("cnpj") or ""
            Licenca.inicializar(cnpj_empresa=cnpj)
            Licenca.verificar_online()   # check síncrono: garante bloqueios do servidor
            if not Licenca.ativa():
                raise LicencaAuthError(
                    f"Licença inativa: {Licenca.motivo()}\n\n"
                    "Ative ou renove a licença para continuar."
                )
            if not Licenca.validar_cnpj(cnpj):
                raise LicencaAuthError(
                    "Esta licença não está autorizada para esta empresa.\n"
                    f"CNPJ da licença: {Licenca.cnpj_licenciado() or 'não vinculado'}\n"
                    "Contate o suporte."
                )
        except AuthError:
            Session.encerrar()
            raise

    @classmethod
    def _carregar_permissoes(cls, perfil_id: int) -> dict[str, bool]:
        rows = DatabaseManager.empresa().fetchall(
            "SELECT modulo, acao FROM permissoes WHERE perfil_id = ? AND permitido = 1",
            (perfil_id,),
        )
        return {f"{r['modulo']}:{r['acao']}": True for r in rows}

    @classmethod
    def logout(cls):
        from core.audit import Audit
        nome = ""
        try:
            from core.session import Session as S
            nome = S.nome()
        except Exception:
            pass
        Audit.registrar(
            acao="LOGOUT", modulo="auth",
            usuario_nome=nome,
            detalhe="Sessão encerrada pelo usuário",
        )
        Session.encerrar()
        DatabaseManager.fechar_empresa()