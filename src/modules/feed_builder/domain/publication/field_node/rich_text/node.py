from collections.abc import Callable

from src.modules.feed_builder.domain.feed.field_node.rich_text.value_object.data import (
    RichTextNodeDataVO,
)
from src.modules.feed_builder.domain.feed.field_node.rich_text.visible_text import (
    visible_html_text,
)
from src.modules.feed_builder.domain.feed.types import TextFieldType
from src.modules.feed_builder.domain.publication.field_node.text.node import TextNode


class RichTextNode(TextNode):
    """Разрешает HTML и проверяет ограничения по видимому тексту."""

    data_type = (RichTextNodeDataVO,)

    def __init__(self, clean: Callable[[str], str]) -> None:
        """Принимает функцию очистки HTML от внешней сборки."""
        self._clean = clean

    def translation_available(self, value: str | None) -> bool:
        """Пропускает пустую разметку при поиске перевода."""
        return bool(value and visible_html_text(self._clean(value)))

    def prepare_text(self, value: str, settings: TextFieldType) -> str:
        """Очищает любое выбранное значение и сохраняет форматирование."""
        html = super().prepare_text(self._clean(value), settings)
        return html if visible_html_text(html) else ""

    def input_length(self, value: str) -> int:
        """Считает длину безопасного ручного значения без разметки."""
        return len(visible_html_text(self._clean(value)))

    def constraint_text(self, value: str) -> str:
        """Проверяет длину и обязательность видимого текста."""
        return visible_html_text(value)
