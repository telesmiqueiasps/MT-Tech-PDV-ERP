"""
FiscalGuard — barreira centralizada de período fiscal fechado.

Uso em qualquer ponto do sistema:
    from services.fiscal_guard import FiscalGuard, FiscalBloqueado
    FiscalGuard.verificar("2025-01-15", "salvar esta nota")
    # → lança FiscalBloqueado se 2025-01 estiver fechado

    FiscalGuard.verificar_periodo(2025, 1, "excluir produto")
    # → mesmo, via ano/mês direto

IMPORTANTE: esta classe consulta DIRETAMENTE o banco para garantir
que nunca seja contornada por camadas intermediárias.
"""
import datetime
from core.database import DatabaseManager


def _esta_fechado(ano: int, mes: int) -> bool:
    """
    Consulta direta ao banco — não usa FiscalConfig para evitar
    que exceções silenciosas na camada model contornem o bloqueio.
    Retorna True se fechado, False se aberto OU se tabela não existe ainda.
    """
    comp = f"{ano:04d}-{mes:02d}"
    try:
        db  = DatabaseManager.empresa()
        row = db.fetchone(
            "SELECT status FROM fiscal_fechamentos WHERE competencia=?",
            (comp,)
        )
        return row is not None and row["status"] == "FECHADO"
    except Exception:
        # Tabela não criada ainda (migration pendente): fail-open
        return False


class FiscalBloqueado(Exception):
    """Levantada quando uma operação tenta afetar um período fiscal fechado."""
    pass


class FiscalGuard:

    @staticmethod
    def verificar(data_iso: str, operacao: str = "realizar esta operação"):
        """
        Verifica se a data pertence a um período fiscal fechado.
        Lança FiscalBloqueado se sim — NUNCA engole a exceção.
        data_iso: string AAAA-MM-DD (ou começo de datetime ISO)
        """
        if not data_iso:
            return
        try:
            d = datetime.date.fromisoformat(str(data_iso).strip()[:10])
        except (ValueError, AttributeError):
            return  # data inválida → não bloqueia

        if _esta_fechado(d.year, d.month):
            comp = f"{d.month:02d}/{d.year}"
            raise FiscalBloqueado(
                f"⛔  Período fiscal {comp} está FECHADO.\n\n"
                f"Não é possível {operacao} para competências encerradas.\n\n"
                "Para realizar alterações, solicite a reabertura do período "
                "ao administrador fiscal."
            )

    @staticmethod
    def verificar_periodo(ano: int, mes: int,
                          operacao: str = "realizar esta operação"):
        """Verifica período por ano e mês direto."""
        if _esta_fechado(ano, mes):
            comp = f"{mes:02d}/{ano}"
            raise FiscalBloqueado(
                f"⛔  Período fiscal {comp} está FECHADO.\n\n"
                f"Não é possível {operacao} para competências encerradas.\n\n"
                "Para realizar alterações, solicite a reabertura do período "
                "ao administrador fiscal."
            )

    @staticmethod
    def data_bloqueada(data_iso: str) -> bool:
        """Retorna True se a data pertence a período fechado (sem lançar exceção)."""
        if not data_iso:
            return False
        try:
            d = datetime.date.fromisoformat(str(data_iso).strip()[:10])
            return _esta_fechado(d.year, d.month)
        except (ValueError, AttributeError):
            return False

    @staticmethod
    def decorar(data_iso: str) -> str:
        """Retorna prefixo visual '⛔ ' se período fechado, '' se aberto."""
        return "⛔ " if FiscalGuard.data_bloqueada(data_iso) else ""