"""Model Mesa e Pedido - sistema de comandas."""
import datetime
from core.database import DatabaseManager

def _db(): return DatabaseManager.empresa()
def _agora(): return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def _proximo_pedido():
    chave = "pedido_" + datetime.date.today().isoformat()
    _db().execute("INSERT INTO pdv_sequencias (chave,ultimo) VALUES (?,0) ON CONFLICT(chave) DO NOTHING", (chave,))
    _db().execute("UPDATE pdv_sequencias SET ultimo=ultimo+1 WHERE chave=?", (chave,))
    return (_db().fetchone("SELECT ultimo FROM pdv_sequencias WHERE chave=?", (chave,)) or {}).get("ultimo", 1)

class Mesa:
    STATUS_COR = {"LIVRE":"#2dce89","OCUPADA":"#f5365c","RESERVADA":"#f4b942","INATIVA":"#aaa"}

    @staticmethod
    def listar(so_ativas=True):
        q = "SELECT * FROM mesas" + (" WHERE ativo=1" if so_ativas else "")
        return _db().fetchall(q + " ORDER BY setor, numero")

    @staticmethod
    def buscar_por_id(mesa_id):
        return _db().fetchone("SELECT * FROM mesas WHERE id=?", (mesa_id,))

    @staticmethod
    def atualizar_status(mesa_id, status):
        _db().execute("UPDATE mesas SET status=? WHERE id=?", (status, mesa_id))

    @staticmethod
    def proximo_numero():
        r = _db().fetchone("SELECT COALESCE(MAX(numero),0)+1 AS prox FROM mesas")
        return r["prox"] if r else 1

    @staticmethod
    def criar(numero, nome, capacidade=4, setor="Salao"):
        return _db().execute("INSERT INTO mesas (numero,nome,capacidade,setor) VALUES (?,?,?,?)", (numero, nome, capacidade, setor))

    @staticmethod
    def editar(mesa_id, numero, nome, capacidade, setor):
        _db().execute("UPDATE mesas SET numero=?,nome=?,capacidade=?,setor=? WHERE id=?", (numero, nome, capacidade, setor, mesa_id))

    @staticmethod
    def reservar(mesa_id, obs=""):
        _db().execute("UPDATE mesas SET status='RESERVADA', reserva_obs=? WHERE id=?", (obs, mesa_id))

    @staticmethod
    def liberar(mesa_id):
        _db().execute("UPDATE mesas SET status='LIVRE', reserva_obs='' WHERE id=?", (mesa_id,))

    @staticmethod
    def inativar(mesa_id):
        _db().execute("UPDATE mesas SET ativo=0, status='INATIVA' WHERE id=?", (mesa_id,))

    @staticmethod
    def ativar(mesa_id):
        _db().execute("UPDATE mesas SET ativo=1, status='LIVRE' WHERE id=?", (mesa_id,))

    @staticmethod
    def deletar(mesa_id):
        _db().execute("DELETE FROM mesas WHERE id=?", (mesa_id,))

    @staticmethod
    def pedido_aberto(mesa_id):
        return _db().fetchone("SELECT * FROM pedidos WHERE mesa_id=? AND status='ABERTO' ORDER BY id DESC LIMIT 1", (mesa_id,))

class Pedido:

    @staticmethod
    def abrir(mesa_id, garcom_id, garcom_nome, pessoas=1, obs=""):
        pid = _db().execute(
            "INSERT INTO pedidos (mesa_id,numero,status,pessoas,garcom_id,garcom_nome,observacoes)"
            " VALUES (?,?,'ABERTO',?,?,?,?)",
            (mesa_id, _proximo_pedido(), pessoas, garcom_id, garcom_nome, obs))
        Mesa.atualizar_status(mesa_id, "OCUPADA")
        return pid

    @staticmethod
    def buscar_por_id(pedido_id):
        return _db().fetchone("SELECT * FROM pedidos WHERE id=?", (pedido_id,))

    @staticmethod
    def itens(pedido_id):
        return _db().fetchall("SELECT * FROM pedido_itens WHERE pedido_id=? ORDER BY id", (pedido_id,))

    @staticmethod
    def _recalcular(pedido_id):
        r = _db().fetchone("SELECT COALESCE(SUM(subtotal),0) AS s FROM pedido_itens WHERE pedido_id=?", (pedido_id,))
        sub  = float(r["s"]) if r else 0.0
        ped  = _db().fetchone("SELECT desconto_valor FROM pedidos WHERE id=?", (pedido_id,)) or {}
        desc = float(ped.get("desconto_valor") or 0)
        _db().execute("UPDATE pedidos SET subtotal=?,total=? WHERE id=?", (sub, max(0, sub-desc), pedido_id))

    @staticmethod
    def adicionar_item(pedido_id, produto, quantidade, obs=""):
        preco = float(produto.get("preco_venda", 0))
        sub   = round(preco * quantidade, 2)
        iid = _db().execute(
            "INSERT INTO pedido_itens (pedido_id,produto_id,produto_codigo,produto_nome,unidade,quantidade,preco_unitario,subtotal,obs)"
            " VALUES (?,?,?,?,?,?,?,?,?)",
            (pedido_id, produto["id"], produto.get("codigo",""), produto.get("nome",""), produto.get("unidade","UN"), quantidade, preco, sub, obs))
        Pedido._recalcular(pedido_id)
        return iid

    @staticmethod
    def alterar_quantidade(item_id, nova_qtd):
        r = _db().fetchone("SELECT pedido_id,preco_unitario FROM pedido_itens WHERE id=?", (item_id,))
        if not r: return
        sub = round(float(r["preco_unitario"]) * nova_qtd, 2)
        _db().execute("UPDATE pedido_itens SET quantidade=?,subtotal=? WHERE id=?", (nova_qtd, sub, item_id))
        Pedido._recalcular(r["pedido_id"])

    @staticmethod
    def remover_item(item_id):
        r = _db().fetchone("SELECT pedido_id FROM pedido_itens WHERE id=?", (item_id,))
        _db().execute("DELETE FROM pedido_itens WHERE id=?", (item_id,))
        if r: Pedido._recalcular(r["pedido_id"])

    @staticmethod
    def aplicar_desconto(pedido_id, valor):
        r = _db().fetchone("SELECT subtotal FROM pedidos WHERE id=?", (pedido_id,))
        if not r: return
        _db().execute("UPDATE pedidos SET desconto_valor=?,total=? WHERE id=?", (valor, max(0, float(r["subtotal"])-valor), pedido_id))

    @staticmethod
    def itens_novos(pedido_id):
        return _db().fetchall("SELECT * FROM pedido_itens WHERE pedido_id=? AND impresso=0 ORDER BY id", (pedido_id,))

    @staticmethod
    def marcar_impresso(pedido_id):
        _db().execute("UPDATE pedido_itens SET impresso=1 WHERE pedido_id=? AND impresso=0", (pedido_id,))

    @staticmethod
    def fechar(pedido_id):
        _db().execute("UPDATE pedidos SET status='FECHANDO',fechado_em=? WHERE id=?", (_agora(), pedido_id))

    @staticmethod
    def calcular_divisao(pedido_id, pessoas):
        ped   = Pedido.buscar_por_id(pedido_id) or {}
        total = float(ped.get("total", 0))
        parte = round(total / max(1, pessoas), 2)
        return [{"pessoa": i+1, "total": parte if i < pessoas-1 else round(total - parte*(pessoas-1), 2)} for i in range(pessoas)]

    @staticmethod
    def converter_para_venda(pedido_id, caixa_id, operador_id, operador_nome):
        from models.venda import Venda
        ped   = Pedido.buscar_por_id(pedido_id)
        itens = Pedido.itens(pedido_id)
        if not ped:   raise ValueError("Pedido nao encontrado.")
        if not itens: raise ValueError("Pedido sem itens.")
        vid = Venda.criar(caixa_id=caixa_id, operador_id=operador_id, operador_nome=operador_nome, mesa_id=ped["mesa_id"], pedido_id=pedido_id)
        for it in itens:
            _db().execute(
                "INSERT INTO venda_itens (venda_id,produto_id,produto_codigo,produto_nome,unidade,quantidade,preco_unitario,subtotal,obs) VALUES (?,?,?,?,?,?,?,?,?)",
                (vid, it["produto_id"], it["produto_codigo"], it["produto_nome"], it["unidade"], it["quantidade"], it["preco_unitario"], it["subtotal"], it.get("obs","")))
        Venda._recalcular(vid)
        if float(ped.get("desconto_valor") or 0) > 0:
            Venda.aplicar_desconto_total(vid, desconto_valor=float(ped["desconto_valor"]))
        return vid

    @staticmethod
    def pagar(pedido_id):
        ped = Pedido.buscar_por_id(pedido_id)
        if not ped: return
        _db().execute("UPDATE pedidos SET status='PAGO' WHERE id=?", (pedido_id,))
        Mesa.atualizar_status(ped["mesa_id"], "LIVRE")

    @staticmethod
    def cancelar(pedido_id, motivo=""):
        ped = Pedido.buscar_por_id(pedido_id)
        if not ped: raise ValueError("Pedido nao encontrado.")
        _db().execute("UPDATE pedidos SET status='CANCELADO' WHERE id=?", (pedido_id,))
        Mesa.atualizar_status(ped["mesa_id"], "LIVRE")