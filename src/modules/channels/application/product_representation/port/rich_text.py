from typing import Protocol


class RepresentationRichTextPort(Protocol):
    """Отделяет техническую HTML-очистку от бизнес-модели Channels."""

    def clean(self, value: str) -> str:
        """Возвращает очищенный HTML без I/O."""
        ...
