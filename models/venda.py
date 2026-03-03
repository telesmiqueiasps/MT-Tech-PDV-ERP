"""Model Venda — PDV varejo e fechamento de mesa."""
import datetime
from core.database import DatabaseManager

def _db(): return DatabaseManager.empresa()
def _agora(): return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def _proximo_numero():
    chave = f"venda_{datetime.date.today().isoformat()}"
    _db().execute(
        "INSERT INTO pdv_sequencias (chave,ultimo) VALUES (?,0)"
        " ON CONFLICT(chave) DO NOTHING", (chave,))
    _db().execute(
        "UPDATE pdv_sequencias SET ultimo=ultimo+1 WHERE chave=?", (chave,))
    return (_db().fetchone(
        "SELECT ultimo FROM pdv_sequencias WHERE chave=?", (chave,)) or {}).get("ultimo", 1)

FORMAS_LABEL = {
    "DINHEIRO": "Dinheiro", "DEBITO": "Cartão Débito",
    "CREDITO": "Cartão Crédito", "PIX": "Pix",
    "VR": "Vale-Refeição", "VA": "Vale-Alimentação", "OUTROS": "Outros",
}


class Venda:

    @staticmethod
    def criar(caixa_id, operador_id, operador_nome, mesa_id=None, pedido_id=None):
        return _db().execute(
            "INSERT INTO vendas (numero,caixa_id,mesa_id,pedido_id,"
            "operador_id,operador_nome,status) VALUES (?,?,?,?,?,?,'ABERTA')",
            (_proximo_numero(), caixa_id, mesa_id, pedido_id, operador_id, operador_nome))

    @staticmethod
    def buscar_por_id(venda_id):
        return _db().fetchone("SELECT * FROM vendas WHERE id=?", (venda_id,))

    @staticmethod
    def itens(venda_id):
        return _db().fetchall(
            "SELECT * FROM venda_itens WHERE venda_id=? ORDER BY id", (venda_id,))

    @staticmethod
    def pagamentos(venda_id):
        return _db().fetchall(
            "SELECT * FROM venda_pagamentos WHERE venda_id=? ORDER BY id", (venda_id,))

    @staticmethod
    def adicionar_item(venda_id, produto, quantidade,
                       desconto_pct=0, desconto_valor=0, obs=""):
        preco = float(produto.get("preco_venda", 0))
        desc  = desconto_valor or round(preco * quantidade * desconto_pct / 100, 2)
        sub   = round(preco * quantidade - desc, 2)
        iid = _db().execute(
            "INSERT INTO venda_itens (venda_id,produto_id,produto_codigo,produto_nome,"
            "produto_ncm,produto_cfop,produto_cst,unidade,quantidade,preco_unitario,"
            "desconto_valor,desconto_pct,subtotal,aliq_icms,aliq_pis,aliq_cofins,obs)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (venda_id, produto["id"], produto.get("codigo",""), produto.get("nome",""),
             produto.get("ncm",""), produto.get("cfop_padrao",""),
             produto.get("cst_icms",""), produto.get("unidade","UN"),
             quantidade, preco, desc, desconto_pct, sub,
             produto.get("aliq_icms",0), produto.get("aliq_pis",0),
             produto.get("aliq_cofins",0), obs))
        Venda._recalcular(venda_id)
        return iid

    @staticmethod
    def alterar_quantidade(item_id, nova_qtd):
        r = _db().fetchone(
            "SELECT venda_id,preco_unitario,desconto_valor FROM venda_itens WHERE id=?",
            (item_id,))
        if not r: return
        sub = round(float(r["preco_unitario"]) * nova_qtd
                    - float(r["desconto_valor"] or 0), 2)
        _db().execute(
            "UPDATE venda_itens SET quantidade=?,subtotal=? WHERE id=?",
            (nova_qtd, sub, item_id))
        Venda._recalcular(r["venda_id"])

    @staticmethod
    def remover_item(item_id):
        r = _db().fetchone("SELECT venda_id FROM venda_itens WHERE id=?", (item_id,))
        _db().execute("DELETE FROM venda_itens WHERE id=?", (item_id,))
        if r: Venda._recalcular(r["venda_id"])

    @staticmethod
    def aplicar_desconto_total(venda_id, desconto_pct=0, desconto_valor=0):
        r = _db().fetchone("SELECT subtotal FROM vendas WHERE id=?", (venda_id,))
        if not r: return
        sub  = float(r["subtotal"])
        desc = desconto_valor or round(sub * desconto_pct / 100, 2)
        _db().execute(
            "UPDATE vendas SET desconto_valor=?,desconto_pct=?,total=? WHERE id=?",
            (desc, desconto_pct, max(0, sub - desc), venda_id))

    @staticmethod
    def _recalcular(venda_id):
        r = _db().fetchone(
            "SELECT COALESCE(SUM(subtotal),0) AS s FROM venda_itens WHERE venda_id=?",
            (venda_id,))
        sub = float(r["s"]) if r else 0
        v = _db().fetchone(
            "SELECT desconto_valor,desconto_pct FROM vendas WHERE id=?",
            (venda_id,)) or {}
        desc = float(v.get("desconto_valor") or 0)
        if not desc and v.get("desconto_pct"):
            desc = round(sub * float(v["desconto_pct"]) / 100, 2)
        _db().execute(
            "UPDATE vendas SET subtotal=?,total=? WHERE id=?",
            (sub, max(0, sub - desc), venda_id))

    @staticmethod
    def adicionar_pagamento(venda_id, forma, valor,
                            parcelas=1, bandeira="", nsu=""):
        troco = 0.0
        if forma == "DINHEIRO":
            v = Venda.buscar_por_id(venda_id) or {}
            pago = float(_db().fetchone(
                "SELECT COALESCE(SUM(valor),0) AS t FROM venda_pagamentos WHERE venda_id=?",
                (venda_id,))["t"])
            troco = max(0.0, pago + valor - float(v.get("total", 0)))
        pid = _db().execute(
            "INSERT INTO venda_pagamentos (venda_id,forma,valor,parcelas,troco,bandeira,nsu)"
            " VALUES (?,?,?,?,?,?,?)",
            (venda_id, forma, valor, parcelas, troco, bandeira, nsu))
        total_pago = float(_db().fetchone(
            "SELECT COALESCE(SUM(valor),0) AS t FROM venda_pagamentos WHERE venda_id=?",
            (venda_id,))["t"])
        _db().execute(
            "UPDATE vendas SET total_pago=?,troco=? WHERE id=?",
            (total_pago, troco, venda_id))
        return pid

    @staticmethod
    def remover_pagamento(pagto_id):
        r = _db().fetchone(
            "SELECT venda_id FROM venda_pagamentos WHERE id=?", (pagto_id,))
        _db().execute("DELETE FROM venda_pagamentos WHERE id=?", (pagto_id,))
        if r:
            tp = float(_db().fetchone(
                "SELECT COALESCE(SUM(valor),0) AS t FROM venda_pagamentos WHERE venda_id=?",
                (r["venda_id"],))["t"])
            _db().execute(
                "UPDATE vendas SET total_pago=? WHERE id=?", (tp, r["venda_id"]))

    @staticmethod
    def valor_pendente(venda_id):
        v = Venda.buscar_por_id(venda_id) or {}
        return max(0.0, float(v.get("total", 0)) - float(v.get("total_pago", 0)))

    @staticmethod
    def finalizar(venda_id):
        venda = Venda.buscar_por_id(venda_id)
        if not venda: raise ValueError("Venda não encontrada.")
        if venda["status"] != "ABERTA":
            raise ValueError(f"Venda já está {venda['status']}.")
        pend = Venda.valor_pendente(venda_id)
        if pend > 0.01:
            raise ValueError(f"Falta R$ {pend:.2f} para finalizar.")
        _db().execute(
            "UPDATE vendas SET status='FINALIZADA',finalizada_em=? WHERE id=?",
            (_agora(), venda_id))
        for item in Venda.itens(venda_id):
            try:
                from models.estoque import EstoqueMovimento
                EstoqueMovimento.saida(
                    produto_id=item["produto_id"], deposito_id=None,
                    quantidade=item["quantidade"], motivo="VENDA_PDV",
                    ref_id=venda_id, ref_tipo="venda")
            except Exception:
                pass
        if venda.get("caixa_id"):
            _db().execute(
                "INSERT INTO caixa_movimentos"
                " (caixa_id,tipo,valor,descricao,usuario_id,usuario_nome)"
                " VALUES (?,'VENDA',?,?,?,?)",
                (venda["caixa_id"], float(venda["total"]),
                 f"Venda #{venda['numero']}",
                 venda.get("operador_id"), venda.get("operador_nome")))
        from core.audit import Audit
        Audit.insert("vendas", venda_id,
                     {"numero": venda["numero"], "total": venda["total"]},
                     modulo="pdv")

    @staticmethod
    def cancelar(venda_id, motivo=""):
        v = Venda.buscar_por_id(venda_id)
        if not v: raise ValueError("Venda não encontrada.")
        if v["status"] == "FINALIZADA":
            raise ValueError("Use estorno para vendas finalizadas.")
        _db().execute(
            "UPDATE vendas SET status='CANCELADA',cancelada_em=?,motivo_cancel=? WHERE id=?",
            (_agora(), motivo, venda_id))
        from core.audit import Audit
        Audit.delete("vendas", venda_id,
                     {"numero": v["numero"], "motivo": motivo}, modulo="pdv")

    @staticmethod
    def listar(caixa_id=None, data=None, status=None, limite=200):
        sql, p = "SELECT * FROM vendas WHERE 1=1", []
        if caixa_id: sql += " AND caixa_id=?"; p.append(caixa_id)
        if data:     sql += " AND date(criado_em)=?"; p.append(data)
        if status:   sql += " AND status=?"; p.append(status)
        return _db().fetchall(sql + f" ORDER BY criado_em DESC LIMIT {int(limite)}", tuple(p))