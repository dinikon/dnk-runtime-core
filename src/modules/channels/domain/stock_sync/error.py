from src.modules.shared.domain.domain_error import DomainError


class StockSyncError(DomainError):
    """Безопасный отказ синхронизации количества без ответа провайдера."""

    def __init__(self, code: str) -> None:
        """Сохраняет стабильный код для HTTP и Worker."""
        super().__init__(code)
        self.code = code
