from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, TypeAlias

FilterNodeOperator = Literal[
    "eq",
    "neq",
    "in",
    "contains",
    "gt",
    "gte",
    "lt",
    "lte",
    "between",
    "is_null",
    "is_not_null",
]
FilterNodeLogic = Literal["and", "or"]


@dataclass(frozen=True, slots=True)
class FilterConditionNode:
    """Синтаксически разобранное условие публичного filter DSL."""

    field: str
    operator: str
    value: Any


@dataclass(frozen=True, slots=True)
class FilterGroupNode:
    """Синтаксически разобранная группа публичного filter DSL."""

    logic: FilterNodeLogic
    items: tuple["FilterNode", ...]


FilterNode: TypeAlias = FilterConditionNode | FilterGroupNode


__all__ = [
    "FilterConditionNode",
    "FilterGroupNode",
    "FilterNode",
    "FilterNodeLogic",
    "FilterNodeOperator",
]
