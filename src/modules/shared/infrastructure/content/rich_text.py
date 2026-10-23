import nh3


def sanitize_rich_text(value: str) -> str:
    """Удаляет исполняемый HTML и оставляет общее форматирование текстового редактора."""
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
