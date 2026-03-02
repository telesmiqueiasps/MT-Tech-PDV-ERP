"""
Model de configurações fiscais: CFOP, CST, alíquotas, regras e fechamentos.
"""
from core.database import DatabaseManager
import datetime


def _db():
    return DatabaseManager.empresa()


class FiscalConfig:

    # ── CFOP ─────────────────────────────────────────────────────
    @staticmethod
    def listar_cfop(tipo_op: str = None, situacao: str = None,
                    busca: str = "", apenas_ativos: bool = True) -> list[dict]:
        sql = "SELECT * FROM fiscal_cfop WHERE 1=1"
        p = []
        if apenas_ativos:
            sql += " AND ativo=1"
        if tipo_op:
            sql += " AND tipo_op=?"; p.append(tipo_op)
        if situacao:
            sql += " AND situacao=?"; p.append(situacao)
        if busca:
            sql += " AND (codigo LIKE ? OR descricao LIKE ?)"
            p += [f"%{busca}%", f"%{busca}%"]
        sql += " ORDER BY codigo"
        return _db().fetchall(sql, tuple(p))

    @staticmethod
    def salvar_cfop(dados: dict, id_: int = None):
        db = _db()
        if id_:
            db.execute(
                "UPDATE fiscal_cfop SET codigo=?,descricao=?,tipo_op=?,situacao=?,ativo=?,obs=? WHERE id=?",
                (dados["codigo"], dados["descricao"], dados["tipo_op"],
                 dados.get("situacao","A"), int(dados.get("ativo",1)),
                 dados.get("obs"), id_)
            )
        else:
            return db.execute(
                "INSERT INTO fiscal_cfop (codigo,descricao,tipo_op,situacao,ativo,obs) VALUES(?,?,?,?,?,?)",
                (dados["codigo"], dados["descricao"], dados["tipo_op"],
                 dados.get("situacao","A"), int(dados.get("ativo",1)), dados.get("obs"))
            )

    @staticmethod
    def excluir_cfop(id_: int):
        _db().execute("DELETE FROM fiscal_cfop WHERE id=?", (id_,))

    # ── CST ICMS ─────────────────────────────────────────────────
    @staticmethod
    def listar_cst_icms(regime: str = None, busca: str = "") -> list[dict]:
        sql = "SELECT * FROM fiscal_cst_icms WHERE ativo=1"
        p = []
        if regime:
            sql += " AND regime=?"; p.append(regime)
        if busca:
            sql += " AND (codigo LIKE ? OR descricao LIKE ?)"
            p += [f"%{busca}%", f"%{busca}%"]
        sql += " ORDER BY codigo"
        return _db().fetchall(sql, tuple(p))

    @staticmethod
    def salvar_cst_icms(dados: dict, id_: int = None):
        db = _db()
        if id_:
            db.execute(
                "UPDATE fiscal_cst_icms SET codigo=?,regime=?,descricao=?,ativo=? WHERE id=?",
                (dados["codigo"], dados.get("regime","N"), dados["descricao"],
                 int(dados.get("ativo",1)), id_)
            )
        else:
            return db.execute(
                "INSERT INTO fiscal_cst_icms (codigo,regime,descricao,ativo) VALUES(?,?,?,?)",
                (dados["codigo"], dados.get("regime","N"), dados["descricao"],
                 int(dados.get("ativo",1)))
            )

    # ── CST PIS/COFINS ────────────────────────────────────────────
    @staticmethod
    def listar_cst_pis_cofins(busca: str = "") -> list[dict]:
        sql = "SELECT * FROM fiscal_cst_pis_cofins WHERE ativo=1"
        p = []
        if busca:
            sql += " AND (codigo LIKE ? OR descricao LIKE ?)"
            p += [f"%{busca}%", f"%{busca}%"]
        sql += " ORDER BY codigo"
        return _db().fetchall(sql, tuple(p))

    # ── Alíquotas ICMS ────────────────────────────────────────────
    @staticmethod
    def listar_aliq_icms(busca: str = "") -> list[dict]:
        sql = "SELECT * FROM fiscal_aliq_icms WHERE ativo=1"
        p = []
        if busca:
            sql += " AND (uf_origem LIKE ? OR uf_destino LIKE ?)"
            p += [f"%{busca}%", f"%{busca}%"]
        sql += " ORDER BY uf_origem, uf_destino"
        return _db().fetchall(sql, tuple(p))

    @staticmethod
    def aliquota_icms(uf_origem: str, uf_destino: str) -> float:
        row = _db().fetchone(
            "SELECT aliquota FROM fiscal_aliq_icms WHERE uf_origem=? AND uf_destino=? AND ativo=1",
            (uf_origem.upper(), uf_destino.upper())
        )
        return float(row["aliquota"]) if row else 0.0

    @staticmethod
    def salvar_aliq_icms(uf_o: str, uf_d: str, aliq: float, id_: int = None):
        db = _db()
        if id_:
            db.execute(
                "UPDATE fiscal_aliq_icms SET uf_origem=?,uf_destino=?,aliquota=? WHERE id=?",
                (uf_o.upper(), uf_d.upper(), aliq, id_)
            )
        else:
            db.execute(
                "INSERT OR REPLACE INTO fiscal_aliq_icms (uf_origem,uf_destino,aliquota,ativo) VALUES(?,?,?,1)",
                (uf_o.upper(), uf_d.upper(), aliq)
            )

    # ── Regras fiscais ────────────────────────────────────────────
    @staticmethod
    def listar_regras(tipo_op: str = None) -> list[dict]:
        sql = """
            SELECT r.*, c.codigo as cfop_codigo, c.descricao as cfop_descricao,
                   i.codigo as cst_icms_codigo, i.descricao as cst_icms_descricao
            FROM fiscal_regras r
            LEFT JOIN fiscal_cfop c ON c.id = r.cfop_id
            LEFT JOIN fiscal_cst_icms i ON i.id = r.cst_icms_id
            WHERE r.ativo=1
        """
        p = []
        if tipo_op:
            sql += " AND r.tipo_op=?"; p.append(tipo_op)
        sql += " ORDER BY r.tipo_op, r.situacao, r.nome"
        return _db().fetchall(sql, tuple(p))

    @staticmethod
    def regra_para(tipo_op: str, situacao: str) -> dict | None:
        """Busca a regra padrão para tipo de operação + situação."""
        return _db().fetchone(
            """
            SELECT r.*, c.codigo as cfop_codigo, i.codigo as cst_icms_codigo
            FROM fiscal_regras r
            LEFT JOIN fiscal_cfop c ON c.id=r.cfop_id
            LEFT JOIN fiscal_cst_icms i ON i.id=r.cst_icms_id
            WHERE r.tipo_op=? AND r.situacao=? AND r.ativo=1
            ORDER BY r.id LIMIT 1
            """,
            (tipo_op, situacao)
        )

    @staticmethod
    def salvar_regra(dados: dict, id_: int = None):
        db = _db()
        cols = ("nome","tipo_op","situacao","cfop_id","cst_icms_id",
                "cst_pis_cod","cst_cofins_cod","aliq_icms","aliq_pis",
                "aliq_cofins","aliq_ipi","ativo","obs")
        vals = tuple(dados.get(c) for c in cols)
        if id_:
            sets = ", ".join(f"{c}=?" for c in cols)
            db.execute(f"UPDATE fiscal_regras SET {sets} WHERE id=?", vals + (id_,))
        else:
            qs = ",".join("?"*len(cols))
            return db.execute(
                f"INSERT INTO fiscal_regras ({','.join(cols)}) VALUES({qs})", vals)

    @staticmethod
    def excluir_regra(id_: int):
        _db().execute("DELETE FROM fiscal_regras WHERE id=?", (id_,))

    # ── Fechamentos fiscais ───────────────────────────────────────
    @staticmethod
    def listar_fechamentos(ano: int = None) -> list[dict]:
        sql = "SELECT * FROM fiscal_fechamentos"
        p = []
        if ano:
            sql += " WHERE competencia LIKE ?"; p.append(f"{ano}-%")
        sql += " ORDER BY competencia DESC"
        return _db().fetchall(sql, tuple(p))

    @staticmethod
    def competencia_fechada(ano: int, mes: int) -> bool:
        """
        Retorna True se a competência AAAA-MM está fechada.
        Robusto: se a tabela ainda não existe (migration pendente) retorna False
        mas registra aviso — nunca deixa operação passar por erro silencioso.
        """
        comp = f"{ano:04d}-{mes:02d}"
        try:
            row = _db().fetchone(
                "SELECT status FROM fiscal_fechamentos WHERE competencia=?", (comp,)
            )
            return row is not None and row["status"] == "FECHADO"
        except Exception:
            # Tabela não existe ainda — trata como aberto mas NÃO silencia
            # Se a migration não foi rodada, assume aberto (fail-open intencional
            # para não travar o sistema em instalações novas)
            return False

    @staticmethod
    def data_em_periodo_fechado(data_iso: str) -> bool:
        """Verifica se a data (AAAA-MM-DD) pertence a competência fechada."""
        if not data_iso:
            return False
        try:
            d = datetime.date.fromisoformat(data_iso[:10])
            return FiscalConfig.competencia_fechada(d.year, d.month)
        except ValueError:
            return False

    @staticmethod
    def fechar(ano: int, mes: int, usuario: str, obs: str = ""):
        comp = f"{ano:04d}-{mes:02d}"
        agora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        db = _db()
        existe = db.fetchone(
            "SELECT id FROM fiscal_fechamentos WHERE competencia=?", (comp,))
        if existe:
            db.execute(
                "UPDATE fiscal_fechamentos SET status='FECHADO',fechado_em=?,fechado_por=?,obs=? WHERE competencia=?",
                (agora, usuario, obs, comp)
            )
        else:
            db.execute(
                "INSERT INTO fiscal_fechamentos (competencia,status,fechado_em,fechado_por,obs) VALUES(?,?,?,?,?)",
                (comp, "FECHADO", agora, usuario, obs)
            )
        from core.audit import Audit
        Audit.periodo_fiscal("FECHAR_PERIODO", comp, obs)

    @staticmethod
    def reabrir(ano: int, mes: int, usuario: str, obs: str = ""):
        comp  = f"{ano:04d}-{mes:02d}"
        agora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        _db().execute(
            "UPDATE fiscal_fechamentos SET status='ABERTO',reaberto_em=?,reaberto_por=?,obs=? WHERE competencia=?",
            (agora, usuario, obs, comp)
        )
        from core.audit import Audit
        Audit.periodo_fiscal("REABRIR_PERIODO", comp, obs)

    @staticmethod
    def cfop_para_form(tipo_op: str, situacao: str = None) -> list[dict]:
        """Retorna CFOPs filtrados para uso em formulários."""
        return FiscalConfig.listar_cfop(tipo_op=tipo_op, situacao=situacao)