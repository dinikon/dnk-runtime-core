from src.modules.shared.domain.domain_error import DomainError


class ContentDeliveryError(DomainError):
    """Передаёт безопасную причину отказа исходящей доставки."""

    def __init__(self, code: str, *, conflict: bool = False) -> None:
        """Не сохраняет запрос, секреты или исходное исключение площадки."""
        self.code = code
        self.conflict = conflict
        super().__init__(code)
