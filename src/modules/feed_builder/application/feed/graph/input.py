from dataclasses import dataclass

from src.modules.feed_builder.application.feed.types import JsonObject


@dataclass(frozen=True, slots=True)
class FieldNodeInput:
    """Свойства ноды Offer до декодирования настроек зарегистрированного типа."""

    id: str
    key: str
    name: str
    type_id: str
    type_version: int
    data: JsonObject
    export: JsonObject
    ai_instruction: str | None = None


@dataclass(frozen=True, slots=True)
class CategoryTreeInput:
    """Принимает идентификатор и данные дерева из плоского графа."""

    id: str
    data: JsonObject


@dataclass(frozen=True, slots=True)
class FeedGraphInput:
    """Передаёт упорядоченный граф V2 через границу приложения."""

    fields: tuple[FieldNodeInput, ...]
    category_trees: tuple[CategoryTreeInput, ...] = ()
