from src.modules.shared.domain.errors.domain_error import DomainError


class CurrencyCodeNotSupportedError(DomainError):
    """Ошибка неподдержанного кода валюты."""

    def __init__(self, value: str) -> None:
        """Формирует сообщение с неподдержанным кодом валюты."""
        super().__init__(f"currency code '{value}' is not supported")
