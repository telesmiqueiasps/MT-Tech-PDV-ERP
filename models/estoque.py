"""
Model de Estoque.

Operações:
    Estoque.entrada(produto_id, deposito_id, qtd, custo, fornecedor_id, nf, motivo, usuario)
    Estoque.saida(produto_id, deposito_id, qtd, motivo, usuario)
    Estoque.transferencia(produto_id, dep_orig, dep_dest, qtd, motivo, usuario)
    Estoque.inventario(itens: list[dict], deposito_id, usuario)
    Estoque.saldo(produto_id, deposito_id) -> float
    Estoque.saldos_produto(produto_id) -> list[dict]
    Estoque.historico(produto_id, deposito_id, limite) -> list[dict]
    Estoque.alertas_minimo() -> list[dict]

Depósito:
    Deposito.listar()
    Deposito.criar(nome, descricao)
    Deposito.atualizar(id, nome, descricao)
    Deposito.desativar(id)
"""
from core.database import DatabaseManager


def _db():
    return DatabaseManager.empresa()


# ── Depósitos ────────────────────────────────────────────────────

class Deposito:
    @staticmethod
    def listar() -> list[dict]:
        return _db().fetchall(
            "SELECT * FROM depositos WHERE ativo=1 ORDER BY id"
        )

    @staticmethod
    def buscar_por_id(id: int) -> dict | None:
        return _db().fetchone("SELECT * FROM depositos WHERE id=?", (id,))

    @staticmethod
    def criar(nome: str, descricao: str = "") -> int:
        return _db().execute(
            "INSERT INTO depositos (nome, descricao) VALUES (?,?)",
            (nome, descricao or None)
        )

    @staticmethod
    def atualizar(id: int, nome: str, descricao: str = ""):
        _db().execute(
            "UPDATE depositos SET nome=?, descricao=? WHERE id=?",
            (nome, descricao or None, id)
        )

    @staticmethod
    def desativar(id: int):
        if id == 1:
            raise ValueError("O depósito principal não pode ser desativado.")
        _db().execute("UPDATE depositos SET ativo=0 WHERE id=?", (id,))


# ── Saldos ───────────────────────────────────────────────────────

class Estoque:

    @staticmethod
    def saldo(produto_id: int, deposito_id: int) -> float:
        row = _db().fetchone(
            "SELECT quantidade FROM estoque_saldos WHERE produto_id=? AND deposito_id=?",
            (produto_id, deposito_id)
        )
        return float(row["quantidade"]) if row else 0.0

    @staticmethod
    def custo_medio(produto_id: int, deposito_id: int) -> float:
        row = _db().fetchone(
            "SELECT custo_medio FROM estoque_saldos WHERE produto_id=? AND deposito_id=?",
            (produto_id, deposito_id)
        )
        return float(row["custo_medio"]) if row else 0.0

    @staticmethod
    def saldos_produto(produto_id: int) -> list[dict]:
        return _db().fetchall(
            """
            SELECT s.*, d.nome as deposito_nome
            FROM estoque_saldos s
            JOIN depositos d ON d.id = s.deposito_id
            WHERE s.produto_id = ?
            ORDER BY d.nome
            """,
            (produto_id,)
        )

    @staticmethod
    def saldo_total_produto(produto_id: int) -> float:
        row = _db().fetchone(
            "SELECT COALESCE(SUM(quantidade),0) as total FROM estoque_saldos WHERE produto_id=?",
            (produto_id,)
        )
        return float(row["total"]) if row else 0.0

    @staticmethod
    def posicao_completa(busca: str = "", deposito_id: int = None,
                          apenas_abaixo_minimo: bool = False) -> list[dict]:
        """Retorna posição de estoque por produto × depósito."""
        sql = """
            SELECT
                p.id, p.codigo, p.nome, p.unidade,
                p.estoque_min, p.estoque_max, p.preco_custo,
                d.id as deposito_id, d.nome as deposito_nome,
                COALESCE(s.quantidade, 0)  as quantidade,
                COALESCE(s.custo_medio, 0) as custo_medio,
                COALESCE(s.quantidade, 0) * COALESCE(s.custo_medio, 0) as valor_total
            FROM produtos p
            CROSS JOIN depositos d
            LEFT JOIN estoque_saldos s
                ON s.produto_id = p.id AND s.deposito_id = d.id
            WHERE p.ativo = 1 AND d.ativo = 1
        """
        params = []
        if busca:
            sql += " AND (p.nome LIKE ? OR p.codigo LIKE ?)"
            params += [f"%{busca}%", f"%{busca}%"]
        if deposito_id:
            sql += " AND d.id = ?"
            params.append(deposito_id)
        if apenas_abaixo_minimo:
            sql += " AND p.estoque_min > 0 AND COALESCE(s.quantidade,0) <= p.estoque_min"
        sql += " ORDER BY p.nome, d.nome"
        return _db().fetchall(sql, tuple(params))

    # ── Movimentações ────────────────────────────────────────────

    @staticmethod
    def entrada(produto_id: int, deposito_id: int, quantidade: float,
                custo_unitario: float, fornecedor_id: int = None,
                numero_nf: str = None, motivo: str = None,
                usuario_id: int = None, usuario_nome: str = None,
                data_ref: str = None):
        if quantidade <= 0:
            raise ValueError("Quantidade deve ser maior que zero.")

        # Bloqueia se período fiscal fechado (apenas movimentos manuais com data)
        if data_ref:
            try:
                from services.fiscal_guard import FiscalGuard, FiscalBloqueado
                FiscalGuard.verificar(data_ref, "registrar entrada no estoque")
            except FiscalBloqueado:
                raise

        saldo_ant   = Estoque.saldo(produto_id, deposito_id)
        cm_anterior = Estoque.custo_medio(produto_id, deposito_id)

        # Custo médio ponderado
        valor_anterior = saldo_ant * cm_anterior
        valor_entrada  = quantidade * custo_unitario
        novo_saldo     = saldo_ant + quantidade
        novo_cm        = (valor_anterior + valor_entrada) / novo_saldo if novo_saldo else custo_unitario

        Estoque._upsert_saldo(produto_id, deposito_id, novo_saldo, novo_cm)

        # Atualiza preco_custo no produto
        _db().execute(
            "UPDATE produtos SET preco_custo=?, estoque_atual=estoque_atual+? WHERE id=?",
            (novo_cm, quantidade, produto_id)
        )

        Estoque._registrar_mov(
            tipo="ENT", produto_id=produto_id, deposito_id=deposito_id,
            quantidade=quantidade, custo_unitario=custo_unitario,
            custo_total=valor_entrada, fornecedor_id=fornecedor_id,
            numero_nf=numero_nf, motivo=motivo,
            usuario_id=usuario_id, usuario_nome=usuario_nome,
            saldo_anterior=saldo_ant, saldo_posterior=novo_saldo
        )

    @staticmethod
    def saida(produto_id: int, deposito_id: int, quantidade: float,
              motivo: str = None, usuario_id: int = None, usuario_nome: str = None,
              data_ref: str = None):
        if quantidade <= 0:
            raise ValueError("Quantidade deve ser maior que zero.")

        if data_ref:
            try:
                from services.fiscal_guard import FiscalGuard, FiscalBloqueado
                FiscalGuard.verificar(data_ref, "registrar saída no estoque")
            except FiscalBloqueado:
                raise

        saldo_ant = Estoque.saldo(produto_id, deposito_id)
        if saldo_ant < quantidade:
            raise ValueError(
                f"Saldo insuficiente. Disponível: {saldo_ant:g}, solicitado: {quantidade:g}."
            )

        novo_saldo = saldo_ant - quantidade
        cm = Estoque.custo_medio(produto_id, deposito_id)
        Estoque._upsert_saldo(produto_id, deposito_id, novo_saldo, cm)

        _db().execute(
            "UPDATE produtos SET estoque_atual=estoque_atual-? WHERE id=?",
            (quantidade, produto_id)
        )

        Estoque._registrar_mov(
            tipo="SAI", produto_id=produto_id, deposito_id=deposito_id,
            quantidade=quantidade, custo_unitario=cm,
            custo_total=quantidade*cm, motivo=motivo,
            usuario_id=usuario_id, usuario_nome=usuario_nome,
            saldo_anterior=saldo_ant, saldo_posterior=novo_saldo
        )

    @staticmethod
    def transferencia(produto_id: int, deposito_orig: int, deposito_dest: int,
                      quantidade: float, motivo: str = None,
                      usuario_id: int = None, usuario_nome: str = None):
        if deposito_orig == deposito_dest:
            raise ValueError("Depósito de origem e destino são iguais.")
        if quantidade <= 0:
            raise ValueError("Quantidade deve ser maior que zero.")

        saldo_orig = Estoque.saldo(produto_id, deposito_orig)
        if saldo_orig < quantidade:
            raise ValueError(
                f"Saldo insuficiente no depósito de origem. Disponível: {saldo_orig:g}."
            )

        cm         = Estoque.custo_medio(produto_id, deposito_orig)
        saldo_dest = Estoque.saldo(produto_id, deposito_dest)
        cm_dest    = Estoque.custo_medio(produto_id, deposito_dest)

        novo_orig  = saldo_orig - quantidade
        valor_dest = saldo_dest * cm_dest + quantidade * cm
        novo_dest  = saldo_dest + quantidade
        novo_cm_dest = valor_dest / novo_dest if novo_dest else cm

        Estoque._upsert_saldo(produto_id, deposito_orig, novo_orig, cm)
        Estoque._upsert_saldo(produto_id, deposito_dest, novo_dest, novo_cm_dest)

        kwargs = dict(produto_id=produto_id, quantidade=quantidade,
                      custo_unitario=cm, custo_total=quantidade*cm,
                      deposito_dest_id=deposito_dest, motivo=motivo,
                      usuario_id=usuario_id, usuario_nome=usuario_nome)

        Estoque._registrar_mov(tipo="TRF_OUT", deposito_id=deposito_orig,
                               saldo_anterior=saldo_orig, saldo_posterior=novo_orig, **kwargs)
        Estoque._registrar_mov(tipo="TRF_IN",  deposito_id=deposito_dest,
                               saldo_anterior=saldo_dest, saldo_posterior=novo_dest, **kwargs)

    @staticmethod
    def inventario(itens: list[dict], deposito_id: int,
                   usuario_id: int = None, usuario_nome: str = None):
        """
        itens: [{"produto_id": int, "quantidade_contada": float}, ...]
        Gera um movimento INV para cada item onde a contagem difere do saldo atual.
        """
        for item in itens:
            pid       = item["produto_id"]
            contado   = float(item["quantidade_contada"])
            saldo_ant = Estoque.saldo(pid, deposito_id)
            diferenca = contado - saldo_ant

            if diferenca == 0:
                continue

            cm = Estoque.custo_medio(pid, deposito_id)
            Estoque._upsert_saldo(pid, deposito_id, contado, cm)

            # Atualiza estoque_atual no produto
            _db().execute(
                "UPDATE produtos SET estoque_atual = estoque_atual + ? WHERE id=?",
                (diferenca, pid)
            )

            Estoque._registrar_mov(
                tipo="INV", produto_id=pid, deposito_id=deposito_id,
                quantidade=abs(diferenca),
                custo_unitario=cm, custo_total=abs(diferenca)*cm,
                motivo=f"Ajuste inventário ({'+'if diferenca>0 else ''}{diferenca:g})",
                usuario_id=usuario_id, usuario_nome=usuario_nome,
                saldo_anterior=saldo_ant, saldo_posterior=contado
            )

    # ── Histórico ────────────────────────────────────────────────

    @staticmethod
    def historico(produto_id: int = None, deposito_id: int = None,
                  tipo: str = None, limite: int = 200) -> list[dict]:
        sql = """
            SELECT m.*,
                   p.nome  as produto_nome,  p.codigo as produto_codigo,
                   p.unidade,
                   d.nome  as deposito_nome,
                   dd.nome as deposito_dest_nome,
                   f.nome  as fornecedor_nome
            FROM estoque_movimentos m
            JOIN  produtos   p  ON p.id  = m.produto_id
            JOIN  depositos  d  ON d.id  = m.deposito_id
            LEFT JOIN depositos  dd ON dd.id = m.deposito_dest_id
            LEFT JOIN fornecedores f ON f.id = m.fornecedor_id
            WHERE 1=1
        """
        params = []
        if produto_id:
            sql += " AND m.produto_id=?";  params.append(produto_id)
        if deposito_id:
            sql += " AND m.deposito_id=?"; params.append(deposito_id)
        if tipo:
            sql += " AND m.tipo=?";        params.append(tipo)
        sql += f" ORDER BY m.criado_em DESC LIMIT {int(limite)}"
        return _db().fetchall(sql, tuple(params))

    @staticmethod
    def alertas_minimo() -> list[dict]:
        return _db().fetchall(
            """
            SELECT p.id, p.codigo, p.nome, p.unidade,
                   p.estoque_min, p.estoque_max,
                   COALESCE(SUM(s.quantidade),0) as total
            FROM produtos p
            LEFT JOIN estoque_saldos s ON s.produto_id = p.id
            WHERE p.ativo=1 AND p.estoque_min > 0
            GROUP BY p.id
            HAVING total <= p.estoque_min
            ORDER BY (total - p.estoque_min)
            """
        )

    # ── Internos ─────────────────────────────────────────────────

    @staticmethod
    def _upsert_saldo(produto_id: int, deposito_id: int,
                      quantidade: float, custo_medio: float):
        _db().execute(
            """
            INSERT INTO estoque_saldos (produto_id, deposito_id, quantidade, custo_medio)
            VALUES (?,?,?,?)
            ON CONFLICT(produto_id, deposito_id)
            DO UPDATE SET quantidade=excluded.quantidade,
                          custo_medio=excluded.custo_medio
            """,
            (produto_id, deposito_id, quantidade, custo_medio)
        )

    @staticmethod
    def _registrar_mov(**kwargs):
        _db().execute(
            """
            INSERT INTO estoque_movimentos (
                tipo, produto_id, deposito_id, deposito_dest_id,
                quantidade, custo_unitario, custo_total,
                fornecedor_id, numero_nf, motivo,
                usuario_id, usuario_nome,
                saldo_anterior, saldo_posterior
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                kwargs["tipo"],
                kwargs["produto_id"],
                kwargs["deposito_id"],
                kwargs.get("deposito_dest_id"),
                kwargs["quantidade"],
                kwargs.get("custo_unitario", 0),
                kwargs.get("custo_total", 0),
                kwargs.get("fornecedor_id"),
                kwargs.get("numero_nf"),
                kwargs.get("motivo"),
                kwargs.get("usuario_id"),
                kwargs.get("usuario_nome"),
                kwargs.get("saldo_anterior", 0),
                kwargs.get("saldo_posterior", 0),
            )
        )