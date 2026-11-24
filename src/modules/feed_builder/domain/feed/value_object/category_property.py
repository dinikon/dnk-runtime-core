from dataclasses import dataclass
from typing import Literal

from src.modules.feed_builder.domain.feed.error import InvalidFeedValueError
from src.modules.feed_builder.domain.feed.field_type_validation import (
    valid_text_characters,
)
from src.modules.feed_builder.domain.feed.validation import is_xml_text
from src.modules.feed_builder.domain.feed.value_object.export_name import ExportNameVO

type CategoryScalar = str | int | bool


@dataclass(frozen=True, slots=True)
class CategoryPropertyVO:
    """Описывает свойство записи и его отображение в XML."""

    key: ExportNameVO
    kind: Literal["string", "text", "integer", "boolean"]
    required: bool
    placement: Literal["ATTRIBUTE", "ELEMENT", "TEXT", "NONE"]
    name: ExportNameVO
    source: Literal["CATALOG_NAME"] | None = None

    def __post_init__(self) -> None:
        """Проверяет тип, источник и безопасную позицию XML."""
        if (
            not isinstance(self.key, ExportNameVO)
            or not isinstance(self.name, ExportNameVO)
            or self.kind not in ("string", "text", "integer", "boolean")
            or type(self.required) is not bool
            or self.placement not in ("ATTRIBUTE", "ELEMENT", "TEXT", "NONE")
            or self.placement == "ATTRIBUTE"
            and self.name.value == "xmlns"
            or self.source not in (None, "CATALOG_NAME")
            or self.source is not None
            and self.kind not in ("string", "text")
        ):
            raise InvalidFeedValueError("Некорректное свойство категории.")

    def accepts(self, value: object) -> bool:
        """Проверяет строго типизированное значение записи."""
        if self.kind == "boolean":
            return type(value) is bool
        if self.kind == "integer":
            return type(value) is int and abs(value) <= 2**53 - 1
        return (
            isinstance(value, str)
            and len(value) <= 10000
            and is_xml_text(value)
            and valid_text_characters(value, multiline=self.kind == "text")
            and (not self.required or bool(value.strip()))
        )
