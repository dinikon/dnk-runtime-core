from typing import Protocol


class PublicationHtmlSanitizerPort(Protocol):
    """Очищает внешнее описание перед сохранением отображаемого документа."""

    def clean(self, value: str) -> str:
        """Возвращает разрешённый HTML без исполняемого содержимого."""
        ...
