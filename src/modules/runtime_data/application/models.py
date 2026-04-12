from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

FilterOperator = Literal["eq", "in", "contains", "gte", "lte"]
SortDirection = Literal["asc", "desc"]


@dataclass(frozen=True, slots=True)
class FilterSpec:
    """Описание одного runtime-фильтра для списка объектов."""

    field: str
    op: FilterOperator
    value: Any


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
class FetchPlan:
    """План выборки runtime-данных: relations и projection полей."""

    relations: tuple[str, ...] = ()
    projections: tuple[str, ...] = ()
