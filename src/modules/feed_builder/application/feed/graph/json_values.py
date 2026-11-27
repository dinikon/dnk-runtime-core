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


def boolean(value: object, path: tuple[str | int, ...] = ()) -> bool:
    """Читает логическое значение без приведения строк и чисел."""
    if not isinstance(value, bool):
        raise InvalidFeedSchemaDocumentError("Ожидалось true или false.", path=path)
    return value


def integer(value: object, path: tuple[str | int, ...] = ()) -> int:
    """Читает целое число, исключая логические значения."""
    if type(value) is not int:
        raise InvalidFeedSchemaDocumentError("Ожидалось целое число.", path=path)
    return value


def optional_integer(value: object, path: tuple[str | int, ...] = ()) -> int | None:
    """Читает необязательное целое число."""
    return None if value is None else integer(value, path)


def choice[T: str](
    value: object, allowed: tuple[T, ...], path: tuple[str | int, ...] = ()
) -> T:
    """Возвращает один из допустимых строковых кодов."""
    for option in allowed:
        if value == option:
            return option
    raise InvalidFeedSchemaDocumentError("Неизвестное значение настройки.", path=path)


def decimal_value(value: object) -> Decimal:
    """Читает обязательное число из Decimal-строки."""
    result = optional_decimal(value)
    if result is None:
        raise InvalidFeedSchemaDocumentError("Ожидалась Decimal-строка.")
    return result
