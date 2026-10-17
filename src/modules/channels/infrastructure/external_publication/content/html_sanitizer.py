import nh3


class PublicationHtmlSanitizer:
    """Очищает описания адаптером nh3 с ограниченным набором элементов."""

    def clean(self, value: str) -> str:
        """Удаляет scripts, события, стили и опасные URL из внешнего HTML."""
        return nh3.clean(
            value,
            tags={
                "p",
                "br",
                "strong",
                "b",
                "em",
                "i",
                "u",
                "ul",
                "ol",
                "li",
                "h2",
                "h3",
                "h4",
                "blockquote",
                "a",
                "table",
                "thead",
                "tbody",
                "tr",
                "th",
                "td",
            },
            attributes={"a": {"href", "title"}},
            url_schemes={"https", "http"},
            clean_content_tags={"script", "style", "iframe"},
            link_rel="noopener noreferrer",
        )
