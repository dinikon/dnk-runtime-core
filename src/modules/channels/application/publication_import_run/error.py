class PublicationImportUnavailableError(Exception):
    """Платформа или активность канала не позволяют запустить импорт."""


class PublicationSourceError(Exception):
    """Передаёт безопасный код внешнего отказа без ответа и credentials."""

    def __init__(self, code: str, *, retryable: bool = False) -> None:
        """Сохраняет только код причины и возможность повторения."""
        super().__init__(code)
        self.code = code
        self.retryable = retryable
