"""
Model de Nota Fiscal.
Operações de escrita ficam no FiscalService para manter regras de negócio centralizadas.
"""
from core.database import DatabaseManager


def _db():
    return DatabaseManager.empresa()


STATUS_LABELS = {
    "RASCUNHO":   ("✏️ Rascunho",   "#6C757D"),
    "PENDENTE":   ("⏳ Pendente",   "#D68910"),
    "AUTORIZADA": ("✅ Autorizada", "#1E8449"),
    "CANCELADA":  ("🚫 Cancelada",  "#C0392B"),
    "INUTILIZADA":("⛔ Inutilizada","#922B21"),
}

TIPO_LABELS = {
    "ENTRADA":    "📥 Entrada (Compra)",
    "SAIDA":      "📤 Saída (Venda)",
    "DEV_COMPRA": "↩️ Devolução Compra",
    "DEV_VENDA":  "↪️ Devolução Venda",
}

CFOP_ENTRADA = {
    "1102": "1.102 — Compra p/ comercialização (dentro do estado)",
    "2102": "2.102 — Compra p/ comercialização (fora do estado)",
    "1403": "1.403 — Compra p/ comercialização — Subst. Tributária",
    "1556": "1.556 — Compra de material p/ uso/consumo",
    "1202": "1.202 — Devolução de venda (dentro do estado)",
    "2202": "2.202 — Devolução de venda (fora do estado)",
}

CFOP_SAIDA = {
    "5102": "5.102 — Venda de mercadoria (dentro do estado)",
    "6102": "6.102 — Venda de mercadoria (fora do estado)",
    "5405": "5.405 — Venda merc. com ST (dentro do estado)",
    "5202": "5.202 — Devolução de compra (dentro do estado)",
    "6202": "6.202 — Devolução de compra (fora do estado)",
}


class NotaFiscal:

    @staticmethod
    def listar(tipo: str = None, status: str = None,
               busca: str = "") -> list[dict]:
        sql = """
            SELECT n.*,
                   d.nome as deposito_nome
            FROM notas_fiscais n
            LEFT JOIN depositos d ON d.id = n.deposito_id
            WHERE 1=1
        """
        params = []
        if tipo:
            sql += " AND n.tipo=?";   params.append(tipo)
        if status:
            sql += " AND n.status=?"; params.append(status)
        if busca:
            sql += """ AND (
                n.numero LIKE ? OR n.terceiro_nome LIKE ?
                OR n.terceiro_doc LIKE ? OR n.chave_acesso LIKE ?
            )"""
            params += [f"%{busca}%"] * 4
        sql += " ORDER BY n.criado_em DESC"
        return _db().fetchall(sql, tuple(params))

    @staticmethod
    def buscar_por_id(id: int) -> dict | None:
        return _db().fetchone(
            """
            SELECT n.*, d.nome as deposito_nome
            FROM notas_fiscais n
            LEFT JOIN depositos d ON d.id = n.deposito_id
            WHERE n.id=?
            """, (id,)
        )

    @staticmethod
    def itens(nota_id: int) -> list[dict]:
        return _db().fetchall(
            """
            SELECT i.*, p.nome as produto_nome_cadastro
            FROM notas_fiscais_itens i
            LEFT JOIN produtos p ON p.id = i.produto_id
            WHERE i.nota_id=?
            ORDER BY i.ordem
            """, (nota_id,)
        )

    @staticmethod
    def criar(dados: dict) -> int:
        return _db().execute(
            """
            INSERT INTO notas_fiscais (
                tipo, modelo, status, numero, serie,
                terceiro_id, terceiro_tipo, terceiro_nome, terceiro_doc,
                data_emissao, data_entrada,
                total_produtos, total_frete, total_seguro,
                total_desconto, total_outros, total_ipi,
                total_icms, total_pis, total_cofins, total_nf,
                frete_modalidade, transportadora,
                nota_ref_id, deposito_id,
                observacoes, usuario_id, usuario_nome
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            NotaFiscal._tupla(dados)
        )

    @staticmethod
    def atualizar(id: int, dados: dict):
        _db().execute(
            """
            UPDATE notas_fiscais SET
                tipo=?, modelo=?, status=?, numero=?, serie=?,
                terceiro_id=?, terceiro_tipo=?, terceiro_nome=?, terceiro_doc=?,
                data_emissao=?, data_entrada=?,
                total_produtos=?, total_frete=?, total_seguro=?,
                total_desconto=?, total_outros=?, total_ipi=?,
                total_icms=?, total_pis=?, total_cofins=?, total_nf=?,
                frete_modalidade=?, transportadora=?,
                nota_ref_id=?, deposito_id=?,
                observacoes=?, usuario_id=?, usuario_nome=?,
                atualizado_em=datetime('now','localtime')
            WHERE id=?
            """,
            NotaFiscal._tupla(dados) + (id,)
        )

    @staticmethod
    def _tupla(d: dict) -> tuple:
        return (
            d.get("tipo"), d.get("modelo", "55"),
            d.get("status", "RASCUNHO"),
            d.get("numero") or None,
            int(d.get("serie") or 1),
            d.get("terceiro_id") or None,
            d.get("terceiro_tipo"),
            d.get("terceiro_nome"),
            d.get("terceiro_doc"),
            d.get("data_emissao"),
            d.get("data_entrada"),
            float(d.get("total_produtos") or 0),
            float(d.get("total_frete") or 0),
            float(d.get("total_seguro") or 0),
            float(d.get("total_desconto") or 0),
            float(d.get("total_outros") or 0),
            float(d.get("total_ipi") or 0),
            float(d.get("total_icms") or 0),
            float(d.get("total_pis") or 0),
            float(d.get("total_cofins") or 0),
            float(d.get("total_nf") or 0),
            int(d.get("frete_modalidade") or 9),
            d.get("transportadora"),
            d.get("nota_ref_id") or None,
            d.get("deposito_id") or None,
            d.get("observacoes"),
            d.get("usuario_id"),
            d.get("usuario_nome"),
        )

    @staticmethod
    def salvar_item(nota_id: int, item: dict, item_id: int = None) -> int:
        if item_id:
            _db().execute(
                """
                UPDATE notas_fiscais_itens SET
                    ordem=?, produto_id=?, codigo=?, descricao=?,
                    ncm=?, cfop=?, unidade=?,
                    quantidade=?, valor_unitario=?, valor_total=?,
                    desconto=?, frete=?,
                    origem=?, cst_icms=?, aliq_icms=?, valor_icms=?,
                    cst_pis=?, aliq_pis=?, valor_pis=?,
                    cst_cofins=?, aliq_cofins=?, valor_cofins=?,
                    cst_ipi=?, aliq_ipi=?, valor_ipi=?
                WHERE id=?
                """,
                NotaFiscal._tupla_item(nota_id, item) + (item_id,)
            )
            return item_id
        else:
            return _db().execute(
                """
                INSERT INTO notas_fiscais_itens (
                    nota_id, ordem, produto_id, codigo, descricao,
                    ncm, cfop, unidade,
                    quantidade, valor_unitario, valor_total,
                    desconto, frete,
                    origem, cst_icms, aliq_icms, valor_icms,
                    cst_pis, aliq_pis, valor_pis,
                    cst_cofins, aliq_cofins, valor_cofins,
                    cst_ipi, aliq_ipi, valor_ipi
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                NotaFiscal._tupla_item(nota_id, item)
            )

    @staticmethod
    def _tupla_item(nota_id: int, i: dict) -> tuple:
        return (
            nota_id,
            int(i.get("ordem") or 1),
            i.get("produto_id") or None,
            i.get("codigo"),
            i.get("descricao", ""),
            i.get("ncm"),
            i.get("cfop"),
            i.get("unidade"),
            float(i.get("quantidade") or 0),
            float(i.get("valor_unitario") or 0),
            float(i.get("valor_total") or 0),
            float(i.get("desconto") or 0),
            float(i.get("frete") or 0),
            int(i.get("origem") or 0),
            i.get("cst_icms"),
            float(i.get("aliq_icms") or 0),
            float(i.get("valor_icms") or 0),
            i.get("cst_pis", "07"),
            float(i.get("aliq_pis") or 0),
            float(i.get("valor_pis") or 0),
            i.get("cst_cofins", "07"),
            float(i.get("aliq_cofins") or 0),
            float(i.get("valor_cofins") or 0),
            i.get("cst_ipi"),
            float(i.get("aliq_ipi") or 0),
            float(i.get("valor_ipi") or 0),
        )

    @staticmethod
    def remover_item(item_id: int):
        _db().execute("DELETE FROM notas_fiscais_itens WHERE id=?", (item_id,))

    @staticmethod
    def remover_todos_itens(nota_id: int):
        _db().execute("DELETE FROM notas_fiscais_itens WHERE nota_id=?", (nota_id,))

    @staticmethod
    def atualizar_status(id: int, status: str, **kwargs):
        campos  = ["status=?", "atualizado_em=datetime('now','localtime')"]
        valores = [status]
        for k, v in kwargs.items():
            campos.append(f"{k}=?")
            valores.append(v)
        valores.append(id)
        _db().execute(
            f"UPDATE notas_fiscais SET {', '.join(campos)} WHERE id=?",
            tuple(valores)
        )


    @staticmethod
    def excluir(id: int):
        """Só permite excluir RASCUNHO."""
        nota = NotaFiscal.buscar_por_id(id)
        if not nota:
            raise ValueError("Nota não encontrada.")
        if nota["status"] != "RASCUNHO":
            raise ValueError(
                f"Só é possível excluir notas em Rascunho. "
                f"Esta está com status '{nota['status']}'."
            )
        _db().execute("DELETE FROM notas_fiscais_itens WHERE nota_id=?", (id,))
        _db().execute("DELETE FROM notas_fiscais WHERE id=?", (id,))

    @staticmethod
    def verificar_duplicata(numero: int, serie: int,
                             terceiro_doc: str, nota_id_excluir: int = None) -> dict | None:
        """Retorna nota duplicada se existir (mesmo número + série + CNPJ/CPF do emitente)."""
        sql = """
            SELECT id, numero, serie, status, terceiro_nome
            FROM notas_fiscais
            WHERE numero=? AND serie=? AND terceiro_doc=?
              AND status NOT IN ('CANCELADA','INUTILIZADA')
        """
        params = [numero, serie, terceiro_doc]
        if nota_id_excluir:
            sql += " AND id != ?"
            params.append(nota_id_excluir)
        return _db().fetchone(sql, tuple(params))

    @staticmethod
    def buscar_fornecedor_por_cnpj(cnpj: str) -> dict | None:
        cnpj_limpo = "".join(c for c in (cnpj or "") if c.isdigit())
        if not cnpj_limpo:
            return None
        rows = _db().fetchall(
            "SELECT * FROM fornecedores WHERE cnpj IS NOT NULL", ()
        )
        for r in rows:
            if "".join(c for c in (r.get("cnpj") or "") if c.isdigit()) == cnpj_limpo:
                return r
        return None

    @staticmethod
    def buscar_cliente_por_cpf_cnpj(doc: str) -> dict | None:
        doc_limpo = "".join(c for c in (doc or "") if c.isdigit())
        if not doc_limpo:
            return None
        rows = _db().fetchall(
            "SELECT * FROM clientes WHERE cnpj IS NOT NULL OR cpf IS NOT NULL", ()
        )
        for r in rows:
            cad = "".join(c for c in (r.get("cnpj") or r.get("cpf") or "") if c.isdigit())
            if cad == doc_limpo:
                return r
        return None

    @staticmethod
    def proximo_numero(serie: int = 1) -> int:
        row = _db().fetchone(
            "SELECT MAX(numero) as m FROM notas_fiscais WHERE serie=? AND status != 'INUTILIZADA'",
            (serie,)
        )
        return int(row["m"] or 0) + 1 if row else 1