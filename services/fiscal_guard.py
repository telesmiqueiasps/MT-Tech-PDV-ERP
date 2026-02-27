"""
FiscalGuard — barreira centralizada de período fiscal fechado.

Uso em qualquer ponto do sistema:
    from services.fiscal_guard import FiscalGuard, FiscalBloqueado
    FiscalGuard.verificar("2025-01-15", "salvar esta nota")
    # → lança FiscalBloqueado se 2025-01 estiver fechado

    FiscalGuard.verificar_periodo(2025, 1, "excluir produto")
    # → mesmo, via ano/mês direto
"""
import datetime
from models.fiscal_config import FiscalConfig


class FiscalBloqueado(Exception):
    """Levantada quando uma operação tenta afetar um período fiscal fechado."""
    pass


class FiscalGuard:

    @staticmethod
    def verificar(data_iso: str, operacao: str = "realizar esta operação"):
        """
        Verifica se a data pertence a um período fiscal fechado.
        Lança FiscalBloqueado se sim.
        data_iso: string AAAA-MM-DD (ou começo de datetime ISO)
        """
        if not data_iso:
            return
        try:
            d = datetime.date.fromisoformat(str(data_iso).strip()[:10])
        except (ValueError, AttributeError):
            return

        if FiscalConfig.competencia_fechada(d.year, d.month):
            comp = f"{d.month:02d}/{d.year}"
            raise FiscalBloqueado(
                f"⛔ Período fiscal {comp} está FECHADO.\n\n"
                f"Não é possível {operacao} para competências encerradas.\n\n"
                "Para realizar alterações, solicite a reabertura do período "
                "ao administrador fiscal."
            )

    @staticmethod
    def verificar_periodo(ano: int, mes: int, operacao: str = "realizar esta operação"):
        """Verifica período por ano e mês."""
        if FiscalConfig.competencia_fechada(ano, mes):
            comp = f"{mes:02d}/{ano}"
            raise FiscalBloqueado(
                f"⛔ Período fiscal {comp} está FECHADO.\n\n"
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
            return FiscalConfig.competencia_fechada(d.year, d.month)
        except (ValueError, AttributeError):
            return False

    @staticmethod
    def decorar(data_iso: str) -> str:
        """Retorna prefixo visual de aviso se período fechado."""
        return "⛔ " if FiscalGuard.data_bloqueada(data_iso) else ""