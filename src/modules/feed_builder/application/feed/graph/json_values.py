from decimal import Decimal
from typing import cast
from src.modules.feed_builder.application.feed.types import JsonObject, JsonValue
from src.modules.feed_builder.application.feed.graph.error import (
    InvalidFeedSchemaDocumentError,
)


def document(
    value: object, required: set[str], optional: set[str] | frozenset[str] = frozenset()
) -> JsonObject:
    """Требует объект с известными ключами, не игнорируя неизвестные настройки."""
    if (
        not isinstance(value, dict)
        or not required <= value.keys()
        or value.keys() - required - optional
    ):
        raise InvalidFeedSchemaDocumentError("Некорректные свойства документа.")
    return cast(JsonObject, value)


def string(value: object) -> str:
    """Требует строку без неявного преобразования чисел и null."""
    if not isinstance(value, str):
        raise InvalidFeedSchemaDocumentError("Ожидалась строка в документе.")
    return value


def array(value: object, maximum: int) -> list[JsonValue]:
    """Требует JSON-массив ограниченного размера."""
    if not isinstance(value, list) or len(value) > maximum:
        raise InvalidFeedSchemaDocumentError("Некорректный размер массива документа.")
    return cast(list[JsonValue], value)


def optional_decimal(value: object) -> Decimal | None:
    """Восстанавливает точный Decimal только из ограниченной строки."""
    if value is None:
        return None
    text = string(value)
    if len(text) > 256:
        raise InvalidFeedSchemaDocumentError("Слишком длинная числовая строка.")
    return Decimal(text)
