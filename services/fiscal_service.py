"""
FiscalService — regras de negócio das notas fiscais.

Centraliza:
  - Lançamento de nota (RASCUNHO → PENDENTE → AUTORIZADA)
  - Integração automática com estoque
  - Cancelamento com estorno
  - Devolução
"""
from core.database import DatabaseManager
from models.nota_fiscal import NotaFiscal
from models.estoque import Estoque
from core.session import Session


def _db():
    return DatabaseManager.empresa()


class FiscalService:

    # ── Lançamento ───────────────────────────────────────────────

    @staticmethod
    def autorizar(nota_id: int):
        """
        RASCUNHO → AUTORIZADA
        Chamado manualmente pelo usuário após conferir o rascunho.
        Valida completamente e move estoque.
        """
        nota  = NotaFiscal.buscar_por_id(nota_id)
        itens = NotaFiscal.itens(nota_id)

        if not nota:
            raise ValueError("Nota não encontrada.")
        if nota["status"] != "RASCUNHO":
            raise ValueError(f"Nota já está com status '{nota['status']}'.")
        if not itens:
            raise ValueError("A nota não possui itens.")

        # Valida período fiscal fechado
        from services.fiscal_guard import FiscalGuard, FiscalBloqueado
        data_ref = nota.get("data_entrada") or nota.get("data_emissao") or ""
        FiscalGuard.verificar(data_ref, "autorizar esta nota")

        dep_id = nota.get("deposito_id")
        if not dep_id:
            raise ValueError("Selecione o depósito antes de lançar.")

        # ── 1. Validar itens com produto vinculado
        sem_produto = [i["descricao"] for i in itens if not i.get("produto_id")]
        if sem_produto:
            raise ValueError(
                "Itens sem produto vinculado:\n"
                + "\n".join(f"  • {d}" for d in sem_produto)
                + "\n\nVincule todos os itens antes de lançar."
            )

        # ── 2. Validar terceiro cadastrado
        doc = nota.get("terceiro_doc") or ""
        tipo = nota.get("tipo")
        if doc:
            if tipo in ("ENTRADA", "DEV_COMPRA"):
                terc = NotaFiscal.buscar_fornecedor_por_cnpj(doc)
                if not terc:
                    raise ValueError(
                        f"Fornecedor com CNPJ {doc} não está cadastrado.\n"
                        "Cadastre o fornecedor antes de lançar a nota."
                    )
                # Garante vínculo
                if not nota.get("terceiro_id"):
                    NotaFiscal.atualizar(nota_id, {**nota, "terceiro_id": terc["id"]})
            else:
                terc = NotaFiscal.buscar_cliente_por_cpf_cnpj(doc)
                if not terc:
                    raise ValueError(
                        f"Cliente com CPF/CNPJ {doc} não está cadastrado.\n"
                        "Cadastre o cliente antes de lançar a nota."
                    )
                if not nota.get("terceiro_id"):
                    NotaFiscal.atualizar(nota_id, {**nota, "terceiro_id": terc["id"]})

        # ── 3. Validar duplicata (número + série + CNPJ emitente)
        numero = nota.get("numero")
        serie  = nota.get("serie") or 1
        if numero and doc:
            dup = NotaFiscal.verificar_duplicata(numero, serie, doc, nota_id_excluir=nota_id)
            if dup:
                raise ValueError(
                    f"Já existe uma nota lançada com o mesmo número {numero}/{serie} "
                    f"do fornecedor/cliente '{dup['terceiro_nome']}' (ID {dup['id']}, "
                    f"status: {dup['status']}).\n"
                    "Verifique antes de prosseguir."
                )

        # ── 4. Mover estoque
        FiscalService._movimentar_estoque(nota, itens, dep_id)

        # ── 5. Marcar autorizada
        NotaFiscal.atualizar_status(nota_id, "AUTORIZADA")

    @staticmethod
    def lancar(nota_id: int):
        """Alias de autorizar() para compatibilidade."""
        FiscalService.autorizar(nota_id)

    @staticmethod
    def emitir(nota_id: int):
        """
        RASCUNHO → PENDENTE (aguarda retorno SEFAZ)
        Stub — integração real com python-nfe / focusnfe / etc. a implementar.
        """
        nota = NotaFiscal.buscar_por_id(nota_id)
        if not nota:
            raise ValueError("Nota não encontrada.")
        if nota["status"] != "RASCUNHO":
            raise ValueError(f"Nota já está com status '{nota['status']}'.")

        # TODO: gerar XML, assinar com certificado, transmitir para SEFAZ
        # Por ora apenas muda para PENDENTE
        NotaFiscal.atualizar_status(nota_id, "PENDENTE")
        raise NotImplementedError(
            "Emissão via SEFAZ ainda não implementada.\n"
            "Use 'Lançar' para registrar a nota manualmente."
        )

    @staticmethod
    def estornar(nota_id: int, motivo: str = ""):
        """
        AUTORIZADA → RASCUNHO
        Reverte o estoque e permite edição/correção da nota.
        """
        nota  = NotaFiscal.buscar_por_id(nota_id)
        itens = NotaFiscal.itens(nota_id)

        if not nota:
            raise ValueError("Nota não encontrada.")
        if nota["status"] != "AUTORIZADA":
            raise ValueError(f"Só é possível estornar notas AUTORIZADAS. "
                             f"Status atual: '{nota['status']}'.")

        # Bloqueia estorno em período fechado
        from services.fiscal_guard import FiscalGuard, FiscalBloqueado
        data_ref = nota.get("data_entrada") or nota.get("data_emissao") or ""
        FiscalGuard.verificar(data_ref, "estornar esta nota")

        dep_id = nota.get("deposito_id")
        if dep_id and itens:
            FiscalService._estornar_estoque(nota, itens, dep_id, motivo)

        obs_atual = nota.get("observacoes") or ""
        obs_nova  = f"{obs_atual}\nESTORNO: {motivo}".strip()
        NotaFiscal.atualizar_status(nota_id, "RASCUNHO",
                                    observacoes=obs_nova)

    # ── Cancelamento ─────────────────────────────────────────────

    @staticmethod
    def cancelar(nota_id: int, motivo: str = ""):
        nota  = NotaFiscal.buscar_por_id(nota_id)
        itens = NotaFiscal.itens(nota_id)

        if not nota:
            raise ValueError("Nota não encontrada.")
        if nota["status"] not in ("AUTORIZADA", "PENDENTE"):
            raise ValueError(f"Não é possível cancelar nota com status '{nota['status']}'.")

        dep_id = nota.get("deposito_id")

        # Estorna estoque se foi lançada (AUTORIZADA)
        if nota["status"] == "AUTORIZADA" and dep_id:
            FiscalService._estornar_estoque(nota, itens, dep_id, motivo)

        obs = f"CANCELAMENTO: {motivo}" if motivo else "CANCELAMENTO"
        NotaFiscal.atualizar_status(nota_id, "CANCELADA",
                                    observacoes=f"{nota.get('observacoes') or ''}\n{obs}".strip())

    # ── Devolução ────────────────────────────────────────────────

    @staticmethod
    def criar_devolucao(nota_ref_id: int) -> int:
        """Cria uma nota de devolução baseada na nota original."""
        nota_orig = NotaFiscal.buscar_por_id(nota_ref_id)
        if not nota_orig:
            raise ValueError("Nota de referência não encontrada.")
        if nota_orig["status"] != "AUTORIZADA":
            raise ValueError("Só é possível devolver notas autorizadas.")

        tipo_dev = {
            "ENTRADA": "DEV_COMPRA",
            "SAIDA":   "DEV_VENDA",
        }.get(nota_orig["tipo"])

        if not tipo_dev:
            raise ValueError("Nota de referência já é uma devolução.")

        # CFOP de devolução conforme estado
        cfop_map = {
            "DEV_COMPRA": "5202",  # ajustar conforme inter/intra
            "DEV_VENDA":  "1202",
        }

        itens_orig = NotaFiscal.itens(nota_ref_id)

        dados_dev = {
            "tipo":          tipo_dev,
            "modelo":        nota_orig["modelo"],
            "status":        "RASCUNHO",
            "terceiro_id":   nota_orig["terceiro_id"],
            "terceiro_tipo": nota_orig["terceiro_tipo"],
            "terceiro_nome": nota_orig["terceiro_nome"],
            "terceiro_doc":  nota_orig["terceiro_doc"],
            "deposito_id":   nota_orig["deposito_id"],
            "nota_ref_id":   nota_ref_id,
            "observacoes":   f"Devolução da NF {nota_orig.get('numero') or nota_ref_id}",
            "usuario_id":    Session.usuario_id(),
            "usuario_nome":  Session.nome(),
        }

        dev_id = NotaFiscal.criar(dados_dev)

        for ordem, item in enumerate(itens_orig, 1):
            item_dev = dict(item)
            item_dev["ordem"]    = ordem
            item_dev["cfop"]     = cfop_map[tipo_dev]
            item_dev.pop("id", None)
            item_dev.pop("nota_id", None)
            NotaFiscal.salvar_item(dev_id, item_dev)

        return dev_id

    # ── Integração estoque (interno) ─────────────────────────────

    @staticmethod
    def _movimentar_estoque(nota: dict, itens: list, dep_id: int):
        tipo = nota["tipo"]
        uid  = nota.get("usuario_id") or Session.usuario_id()
        unome= nota.get("usuario_nome") or Session.nome()
        nf   = str(nota.get("numero") or nota["id"])

        sem_produto = [i["descricao"] for i in itens if not i.get("produto_id")]
        if sem_produto:
            raise ValueError(
                f"Os seguintes itens não estão vinculados a um produto cadastrado:\n"
                + "\n".join(f"  • {d}" for d in sem_produto)
                + "\n\nVincule os itens antes de lançar."
            )

        for item in itens:
            pid = item.get("produto_id")
            if not pid:
                continue
            qtd  = float(item["quantidade"])
            custo= float(item["valor_unitario"])

            if tipo == "ENTRADA":
                Estoque.entrada(
                    produto_id=pid, deposito_id=dep_id,
                    quantidade=qtd, custo_unitario=custo,
                    fornecedor_id=nota.get("terceiro_id"),
                    numero_nf=nf,
                    motivo=f"Entrada NF {nf}",
                    usuario_id=uid, usuario_nome=unome,
                )
            elif tipo == "SAIDA":
                Estoque.saida(
                    produto_id=pid, deposito_id=dep_id,
                    quantidade=qtd,
                    motivo=f"Saída NF {nf}",
                    usuario_id=uid, usuario_nome=unome,
                )
            elif tipo == "DEV_COMPRA":
                # Devolução de compra → saída do estoque
                Estoque.saida(
                    produto_id=pid, deposito_id=dep_id,
                    quantidade=qtd,
                    motivo=f"Devolução compra NF {nf}",
                    usuario_id=uid, usuario_nome=unome,
                )
            elif tipo == "DEV_VENDA":
                # Devolução de venda → entrada no estoque
                Estoque.entrada(
                    produto_id=pid, deposito_id=dep_id,
                    quantidade=qtd, custo_unitario=custo,
                    numero_nf=nf,
                    motivo=f"Devolução venda NF {nf}",
                    usuario_id=uid, usuario_nome=unome,
                )

    @staticmethod
    def _estornar_estoque(nota: dict, itens: list, dep_id: int, motivo: str):
        """Inverte a movimentação de estoque ao cancelar."""
        tipo = nota["tipo"]
        uid  = nota.get("usuario_id") or Session.usuario_id()
        unome= nota.get("usuario_nome") or Session.nome()
        nf   = str(nota.get("numero") or nota["id"])
        obs  = f"Estorno cancelamento NF {nf}" + (f" — {motivo}" if motivo else "")

        for item in itens:
            pid = item.get("produto_id")
            if not pid:
                continue
            qtd  = float(item["quantidade"])
            custo= float(item["valor_unitario"])

            # Estorno: inverte a operação original
            if tipo in ("ENTRADA", "DEV_VENDA"):
                Estoque.saida(produto_id=pid, deposito_id=dep_id,
                              quantidade=qtd, motivo=obs,
                              usuario_id=uid, usuario_nome=unome)
            elif tipo in ("SAIDA", "DEV_COMPRA"):
                Estoque.entrada(produto_id=pid, deposito_id=dep_id,
                                quantidade=qtd, custo_unitario=custo,
                                numero_nf=nf, motivo=obs,
                                usuario_id=uid, usuario_nome=unome)