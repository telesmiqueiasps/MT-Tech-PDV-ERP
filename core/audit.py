"""
Sistema de Auditoria — registra todas as operações relevantes no audit_log.

Uso simples:
    from core.audit import Audit
    Audit.log("UPDATE", tabela="produtos", registro_id=5,
               antes={"nome": "X"}, depois={"nome": "Y"})

Uso com contexto automático (pega Session):
    Audit.registrar(acao="DELETE", modulo="estoque",
                    tabela="estoque_movimentos", registro_id=12)

Categorias de ação:
    LOGIN, LOGOUT, LOGIN_FALHA
    INSERT, UPDATE, DELETE
    AUTORIZAR, ESTORNAR, CANCELAR
    FECHAR_PERIODO, REABRIR_PERIODO
    ATIVAR_LICENCA, CHECK_LICENCA
    ACESSO_NEGADO
"""
import json
import datetime
from core.database import DatabaseManager


def _now() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _json(obj) -> str | None:
    if obj is None:
        return None
    if isinstance(obj, str):
        return obj
    try:
        return json.dumps(obj, ensure_ascii=False, default=str)
    except Exception:
        return str(obj)


def _session_info() -> dict:
    """Tenta obter contexto da sessão atual sem falhar."""
    try:
        from core.session import Session
        if Session.ativa():
            u = Session.usuario()
            e = Session.empresa()
            return {
                "usuario_id":   u.get("id"),
                "usuario_nome": Session.nome(),
                "empresa_id":   e.get("id"),
                "empresa_nome": e.get("nome", ""),
            }
    except Exception:
        pass
    return {
        "usuario_id": None, "usuario_nome": "sistema",
        "empresa_id": None, "empresa_nome": "",
    }


class Audit:

    # ── Método principal ──────────────────────────────────────
    @staticmethod
    def registrar(
        acao:        str,
        modulo:      str  = None,
        tabela:      str  = None,
        registro_id: int  = None,
        antes:       dict = None,
        depois:      dict = None,
        detalhe:     str  = None,
        nivel:       str  = "INFO",
        origem:      str  = "APP",
        usuario_id:  int  = None,
        usuario_nome:str  = None,
        empresa_id:  int  = None,
        empresa_nome:str  = None,
    ):
        """
        Registra um evento de auditoria no banco master.
        Silencioso em caso de erro — nunca deve travar o sistema.
        """
        try:
            ctx = _session_info()
            db  = DatabaseManager.master()
            db.execute(
                """
                INSERT INTO audit_log (
                    nivel, origem,
                    empresa_id, empresa_nome,
                    usuario_id, usuario_nome,
                    acao, modulo, tabela, registro_id,
                    dados_antes, dados_depois,
                    detalhe, criado_em
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    nivel, origem,
                    empresa_id  or ctx["empresa_id"],
                    empresa_nome or ctx["empresa_nome"],
                    usuario_id  or ctx["usuario_id"],
                    usuario_nome or ctx["usuario_nome"],
                    acao, modulo, tabela, registro_id,
                    _json(antes), _json(depois),
                    detalhe, _now(),
                )
            )
        except Exception:
            pass  # auditoria nunca bloqueia o sistema

    # ── Atalhos semânticos ────────────────────────────────────
    @staticmethod
    def login(usuario_nome: str, empresa_nome: str = "", sucesso: bool = True):
        Audit.registrar(
            acao="LOGIN" if sucesso else "LOGIN_FALHA",
            modulo="auth",
            nivel="INFO" if sucesso else "WARN",
            usuario_nome=usuario_nome,
            empresa_nome=empresa_nome,
            detalhe="Login bem-sucedido" if sucesso else "Senha inválida",
            origem="APP",
        )

    @staticmethod
    def logout(usuario_nome: str = None):
        Audit.registrar(
            acao="LOGOUT",
            modulo="auth",
            usuario_nome=usuario_nome,
            detalhe="Sessão encerrada",
        )

    @staticmethod
    def acesso_negado(modulo: str, acao_tentada: str):
        Audit.registrar(
            acao="ACESSO_NEGADO",
            modulo=modulo,
            nivel="WARN",
            detalhe=f"Tentou: {acao_tentada}",
        )

    @staticmethod
    def insert(tabela: str, registro_id: int, dados: dict, modulo: str = None):
        Audit.registrar(
            acao="INSERT", modulo=modulo or tabela,
            tabela=tabela, registro_id=registro_id,
            depois=dados,
        )

    @staticmethod
    def update(tabela: str, registro_id: int,
               antes: dict, depois: dict, modulo: str = None):
        Audit.registrar(
            acao="UPDATE", modulo=modulo or tabela,
            tabela=tabela, registro_id=registro_id,
            antes=antes, depois=depois,
        )

    @staticmethod
    def delete(tabela: str, registro_id: int, dados: dict, modulo: str = None):
        Audit.registrar(
            acao="DELETE", modulo=modulo or tabela,
            tabela=tabela, registro_id=registro_id,
            antes=dados, nivel="WARN",
        )

    @staticmethod
    def fiscal(acao: str, nota_id: int, detalhe: str = ""):
        """Ações fiscais: AUTORIZAR, ESTORNAR, CANCELAR, FECHAR_PERIODO, REABRIR_PERIODO."""
        Audit.registrar(
            acao=acao, modulo="fiscal",
            tabela="notas_fiscais", registro_id=nota_id,
            detalhe=detalhe, nivel="INFO",
        )

    @staticmethod
    def periodo_fiscal(acao: str, competencia: str, obs: str = ""):
        Audit.registrar(
            acao=acao, modulo="fiscal",
            tabela="fiscal_fechamentos",
            detalhe=f"Competência {competencia} — {obs}",
            nivel="WARN" if acao == "FECHAR_PERIODO" else "INFO",
        )

    @staticmethod
    def licenca(acao: str, detalhe: str = ""):
        Audit.registrar(
            acao=acao, modulo="licenca",
            nivel="INFO", origem="LICENCA",
            detalhe=detalhe,
        )

    # ── Consultas (para a view de auditoria) ──────────────────
    @staticmethod
    def buscar(
        empresa_id:   int  = None,
        usuario_nome: str  = None,
        acao:         str  = None,
        modulo:       str  = None,
        tabela:       str  = None,
        nivel:        str  = None,
        data_de:      str  = None,
        data_ate:     str  = None,
        busca_texto:  str  = None,
        limite:       int  = 500,
    ) -> list[dict]:
        sql = "SELECT * FROM audit_log WHERE 1=1"
        p   = []
        if empresa_id:
            sql += " AND empresa_id=?"; p.append(empresa_id)
        if usuario_nome:
            sql += " AND usuario_nome LIKE ?"; p.append(f"%{usuario_nome}%")
        if acao:
            sql += " AND acao=?"; p.append(acao)
        if modulo:
            sql += " AND modulo=?"; p.append(modulo)
        if tabela:
            sql += " AND tabela=?"; p.append(tabela)
        if nivel:
            sql += " AND nivel=?"; p.append(nivel)
        if data_de:
            sql += " AND criado_em >= ?"; p.append(data_de)
        if data_ate:
            # Inclui o dia inteiro
            ate = data_ate if len(data_ate) > 10 else data_ate + " 23:59:59"
            sql += " AND criado_em <= ?"; p.append(ate)
        if busca_texto:
            sql += (" AND (detalhe LIKE ? OR tabela LIKE ? "
                    "OR usuario_nome LIKE ? OR dados_antes LIKE ? OR dados_depois LIKE ?)")
            b = f"%{busca_texto}%"
            p += [b, b, b, b, b]
        sql += f" ORDER BY criado_em DESC LIMIT {int(limite)}"
        try:
            return DatabaseManager.master().fetchall(sql, tuple(p))
        except Exception:
            return []

    @staticmethod
    def estatisticas(empresa_id: int = None, dias: int = 30) -> dict:
        """Retorna contagens agrupadas para o dashboard de auditoria."""
        try:
            db  = DatabaseManager.master()
            de  = (datetime.date.today() - datetime.timedelta(days=dias)).isoformat()
            flt = f"AND empresa_id={empresa_id}" if empresa_id else ""

            total = db.fetchone(
                f"SELECT COUNT(*) as n FROM audit_log WHERE criado_em >= ? {flt}",
                (de,)
            )["n"]

            por_acao = db.fetchall(
                f"SELECT acao, COUNT(*) as n FROM audit_log "
                f"WHERE criado_em >= ? {flt} GROUP BY acao ORDER BY n DESC LIMIT 10",
                (de,)
            )

            por_usuario = db.fetchall(
                f"SELECT usuario_nome, COUNT(*) as n FROM audit_log "
                f"WHERE criado_em >= ? {flt} AND usuario_nome IS NOT NULL "
                f"GROUP BY usuario_nome ORDER BY n DESC LIMIT 10",
                (de,)
            )

            alertas = db.fetchone(
                f"SELECT COUNT(*) as n FROM audit_log "
                f"WHERE criado_em >= ? AND nivel IN ('WARN','ERROR','CRITICAL') {flt}",
                (de,)
            )["n"]

            return {
                "total":        total,
                "alertas":      alertas,
                "por_acao":     por_acao,
                "por_usuario":  por_usuario,
                "periodo_dias": dias,
            }
        except Exception:
            return {"total": 0, "alertas": 0, "por_acao": [], "por_usuario": [], "periodo_dias": dias}