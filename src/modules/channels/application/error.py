"""Ошибки внешней проверки, безопасные для worker и пользователя."""


class VerificationFailure(Exception):
    """Ожидаемый ответ API либо временная недоступность."""

    def __init__(self, code: str, *, retryable: bool = False) -> None:
        """Принимает код без тела ответа или значений credentials."""
        super().__init__(code)
        self.code = code
        self.retryable = retryable


class ChannelInputError(Exception):
    """Ошибка входных настроек платформы с безопасными деталями для границы API."""

    def __init__(self, code: str, *, field: str | None = None) -> None:
        """Сохраняет код и известное поле, не включая входное значение."""
        super().__init__(code)
        self.code = code
        self.field = field
