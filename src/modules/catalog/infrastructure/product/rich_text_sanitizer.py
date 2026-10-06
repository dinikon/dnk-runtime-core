import nh3


class Nh3RichTextSanitizer:
    """Очищает HTML до набора разметки редактора каталога."""

    def clean(self, value: str) -> str:
        return nh3.clean(
            value,
            tags={
                "p",
                "br",
                "strong",
                "em",
                "ul",
                "ol",
                "li",
                "blockquote",
                "h2",
                "h3",
                "a",
            },
            attributes={"a": {"href", "title"}},
            url_schemes={"http", "https"},
            clean_content_tags={"script", "style", "iframe", "object"},
            link_rel="noopener noreferrer",
        ).strip()
