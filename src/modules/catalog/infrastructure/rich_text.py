from src.modules.shared.infrastructure.content.rich_text import sanitize_rich_text


class Nh3RichTextSanitizer:
    """Адаптирует общую техническую sanitization к порту Catalog."""

    def clean(self, value: str) -> str:
        """Очищает HTML перед проверкой схемы Catalog."""
        return sanitize_rich_text(value)
