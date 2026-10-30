from src.modules.shared.infrastructure.content.rich_text import sanitize_rich_text


class RepresentationRichTextSanitizer:
    """Адаптирует общую очистку без импорта внутренностей Catalog."""

    def clean(self, value: str) -> str:
        """Применяет ту же техническую политику HTML, что и Catalog."""
        return sanitize_rich_text(value)
