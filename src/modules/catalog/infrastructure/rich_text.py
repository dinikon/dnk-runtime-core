import nh3


class Nh3RichTextSanitizer:
    """Очищает HTML перед передачей значений доменной политике."""

    def clean(self, value: str) -> str:
        """Удаляет исполняемые элементы, обработчики и опасные URL."""
        return nh3.clean(
            value,
            tags={
                "p",
                "br",
                "strong",
                "em",
                "b",
                "i",
                "ul",
                "ol",
                "li",
                "blockquote",
                "a",
                "h2",
                "h3",
                "code",
                "pre",
            },
            attributes={"a": {"href", "title"}},
            url_schemes={"http", "https", "mailto"},
            link_rel="noopener noreferrer",
        )
