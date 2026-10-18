from src.modules.currency.application.error import ExchangeRateSourceError


class NbuResponseError(ExchangeRateSourceError):
    """Ответ NBU не соответствует контракту полного согласованного снимка."""


class NbuTransportError(ExchangeRateSourceError):
    """Сетевой запрос NBU завершился ошибкой либо timeout."""


class NbuHttpError(ExchangeRateSourceError):
    """NBU вернул неуспешный HTTP-статус без сохранения тела ответа в ошибке."""

    def __init__(self, status_code: int) -> None:
        """Сохраняет только безопасный код статуса."""
        super().__init__("NBU HTTP request failed.")
        self.status_code = status_code


class NbuRateLimitError(NbuHttpError):
    """NBU ограничил частоту; задержка доступна будущему jobs-механизму."""

    def __init__(self, retry_after_seconds: float | None) -> None:
        """Передаёт статус 429 и разобранную задержку без сырых заголовков."""
        super().__init__(429)
        self.retry_after_seconds = retry_after_seconds
