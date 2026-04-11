from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

FilterOperator = Literal["eq", "in", "contains", "gte", "lte"]
SortDirection = Literal["asc", "desc"]


@dataclass(frozen=True, slots=True)
class FilterSpec:
    field: str
    op: FilterOperator
    value: Any


@dataclass(frozen=True, slots=True)
class SortSpec:
    field: str
    direction: SortDirection = "asc"


@dataclass(frozen=True, slots=True)
class PageSpec:
    limit: int
    offset: int = 0


@dataclass(frozen=True, slots=True)
class FetchPlan:
    relations: tuple[str, ...] = ()
    projections: tuple[str, ...] = ()
