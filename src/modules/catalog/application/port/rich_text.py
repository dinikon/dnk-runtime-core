from typing import Protocol


class RichTextSanitizerPort(Protocol):
    """Очистка HTML до передачи содержимого доменной политике."""

    def clean(self, value: str) -> str:
        """Возвращает безопасное HTML-содержимое."""
        ...
