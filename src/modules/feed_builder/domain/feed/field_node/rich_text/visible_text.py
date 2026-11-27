from html.parser import HTMLParser


class _VisibleText(HTMLParser):
    """Читает текстовые узлы и декодирует сущности HTML."""

    def __init__(self) -> None:
        """Открывает сбор видимого текста."""
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        """Сохраняет текст без разметки."""
        self.parts.append(data)


def visible_html_text(value: str) -> str:
    """Возвращает текст очищенного HTML для обязательности и границ длины."""
    parser = _VisibleText()
    parser.feed(value)
    parser.close()
    return "".join(parser.parts).strip()
