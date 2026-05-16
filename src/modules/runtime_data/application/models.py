from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal, TypeAlias

from src.modules.schema_registry.runtime import RuntimeFieldDescriptor

FilterOperator = Literal[
    "eq",
    "neq",
    "in",
    "contains",
    "starts_with",
    "ends_with",
    "gt",
    "gte",
    "lt",
    "lte",
    "between",
    "is_null",
    "is_not_null",
    "contains_any",
    "contains_all",
    "not_contains_any",
    "is_empty",
    "is_not_empty",
]
FilterLogic = Literal["and", "or"]
SortDirection = Literal["asc", "desc"]

DEFAULT_SEARCH_LIMIT = 50
MAX_SEARCH_LIMIT = 500


@dataclass(frozen=True, slots=True)
class FilterSpec:
    """Описание одного runtime-фильтра для списка объектов."""

    field: str
    op: FilterOperator
    value: Any


@dataclass(frozen=True, slots=True)
class FilterGroupSpec:
    """Группа runtime-фильтров с явным AND/OR оператором."""

    logic: FilterLogic
    items: tuple["FilterExpression", ...]


FilterExpression: TypeAlias = FilterSpec | FilterGroupSpec


@dataclass(frozen=True, slots=True)
class TypedFilterSpec:
    """Semantically validated runtime filter with resolved field descriptor."""

    field: RuntimeFieldDescriptor
    op: str
    value: Any


@dataclass(frozen=True, slots=True)
class TypedFilterGroupSpec:
    """Semantically validated runtime filter group."""

    logic: FilterLogic
    items: tuple["TypedFilterExpression", ...]


TypedFilterExpression: TypeAlias = TypedFilterSpec | TypedFilterGroupSpec


@dataclass(frozen=True, slots=True)
class SortSpec:
    """Описание сортировки runtime-запроса по одному полю."""

    field: str
    direction: SortDirection = "asc"


@dataclass(frozen=True, slots=True)
class PageSpec:
    """Параметры limit/offset пагинации runtime-запроса."""

    limit: int
    offset: int = 0


@dataclass(frozen=True, slots=True)
class RuntimeRowsPage:
    """Страница runtime-строк с total count по тем же фильтрам."""

    rows: tuple[Mapping[str, Any], ...]
    total: int


@dataclass(frozen=True, slots=True)
class FetchPlan:
    """План выборки runtime-данных: relations и projection полей."""

    relations: tuple[str, ...] = ()
    projections: tuple[str, ...] = ()
