"""Model Caixa - multiplos caixas simultaneos."""
import datetime
from core.database import DatabaseManager

def _db(): return DatabaseManager.empresa()
def _agora(): return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

class Caixa:
    @staticmethod
    def listar(so_abertos=False):
        q = "SELECT * FROM caixas" + (" WHERE status='ABERTO'" if so_abertos else "")
        return _db().fetchall(q + " ORDER BY numero")
    @staticmethod
    def buscar_por_id(caixa_id):
        return _db().fetchone("SELECT * FROM caixas WHERE id=?", (caixa_id,))
    @staticmethod
    def aberto_do_operador(usuario_id):
        return _db().fetchone("SELECT * FROM caixas WHERE operador_id=? AND status='ABERTO'", (usuario_id,))
    @staticmethod
    def abrir(numero, nome, operador_id, operador_nome, valor_abertura, obs=""):
        agora = _agora()
        cid = _db().execute("INSERT INTO caixas (numero,nome,operador_id,operador_nome,status,valor_abertura,aberto_em,obs_abertura) VALUES (?,?,?,?,'ABERTO',?,?,?)", (numero,nome,operador_id,operador_nome,valor_abertura,agora,obs))
        _db().execute("INSERT INTO caixa_movimentos (caixa_id,tipo,valor,descricao,usuario_id,usuario_nome) VALUES (?,'ABERTURA',?,?,?,?)", (cid,valor_abertura,"Abertura R$ {:.2f}".format(valor_abertura),operador_id,operador_nome))
        try:
            from core.audit import Audit; Audit.insert("caixas",cid,{"numero":numero,"valor_abertura":valor_abertura},modulo="pdv")
        except Exception: pass
        return cid
    @staticmethod
    def fechar(caixa_id, valor_fechamento, operador_id, operador_nome, obs=""):
        agora = _agora()
        _db().execute("UPDATE caixas SET status='FECHADO',valor_fechamento=?,fechado_em=?,obs_fechamento=? WHERE id=?", (valor_fechamento,agora,obs,caixa_id))
        _db().execute("INSERT INTO caixa_movimentos (caixa_id,tipo,valor,descricao,usuario_id,usuario_nome) VALUES (?,'FECHAMENTO',?,?,?,?)", (caixa_id,valor_fechamento,"Fechamento R$ {:.2f}".format(valor_fechamento),operador_id,operador_nome))
        try:
            from core.audit import Audit; Audit.update("caixas",caixa_id,antes={"status":"ABERTO"},depois={"status":"FECHADO","valor_fechamento":valor_fechamento},modulo="pdv")
        except Exception: pass
    @staticmethod
    def sangria(caixa_id, valor, descricao, usuario_id, usuario_nome):
        if valor <= 0: raise ValueError("Valor deve ser positivo.")
        _db().execute("INSERT INTO caixa_movimentos (caixa_id,tipo,valor,descricao,usuario_id,usuario_nome) VALUES (?,'SANGRIA',?,?,?,?)", (caixa_id,-abs(valor),descricao or "Sangria",usuario_id,usuario_nome))
    @staticmethod
    def suprimento(caixa_id, valor, descricao, usuario_id, usuario_nome):
        if valor <= 0: raise ValueError("Valor deve ser positivo.")
        _db().execute("INSERT INTO caixa_movimentos (caixa_id,tipo,valor,descricao,usuario_id,usuario_nome) VALUES (?,'SUPRIMENTO',?,?,?,?)", (caixa_id,abs(valor),descricao or "Suprimento",usuario_id,usuario_nome))
    @staticmethod
    def saldo_atual(caixa_id):
        r = _db().fetchone("SELECT COALESCE(SUM(valor),0) AS t FROM caixa_movimentos WHERE caixa_id=?", (caixa_id,))
        return float(r["t"]) if r else 0.0
    @staticmethod
    def movimentos(caixa_id):
        return _db().fetchall("SELECT * FROM caixa_movimentos WHERE caixa_id=? ORDER BY criado_em", (caixa_id,))
    @staticmethod
    def resumo_fechamento(caixa_id):
        por_forma = _db().fetchall("SELECT vp.forma, SUM(vp.valor) AS total, COUNT(*) AS qtd FROM venda_pagamentos vp JOIN vendas v ON v.id=vp.venda_id WHERE v.caixa_id=? AND v.status='FINALIZADA' GROUP BY vp.forma ORDER BY total DESC", (caixa_id,))
        tv = _db().fetchone("SELECT COUNT(*) AS qtd, COALESCE(SUM(total),0) AS total FROM vendas WHERE caixa_id=? AND status='FINALIZADA'", (caixa_id,)) or {"qtd":0,"total":0}
        canc = (_db().fetchone("SELECT COUNT(*) AS qtd FROM vendas WHERE caixa_id=? AND status='CANCELADA'", (caixa_id,)) or {}).get("qtd",0)
        movs = _db().fetchall("SELECT tipo, SUM(valor) AS total FROM caixa_movimentos WHERE caixa_id=? AND tipo IN ('SANGRIA','SUPRIMENTO') GROUP BY tipo", (caixa_id,))
        desc = (_db().fetchone("SELECT COALESCE(SUM(desconto_valor),0) AS t FROM vendas WHERE caixa_id=? AND status='FINALIZADA'", (caixa_id,)) or {}).get("t",0)
        return {"caixa":Caixa.buscar_por_id(caixa_id) or {},"por_forma":por_forma,"total_vendas":tv,"qtd_canceladas":canc,"movimentos":movs,"total_descontos":float(desc),"saldo_sistema":Caixa.saldo_atual(caixa_id)}