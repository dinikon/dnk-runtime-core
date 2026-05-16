from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, TypeAlias

FilterNodeOperator = Literal[
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
FilterNodeLogic = Literal["and", "or"]


@dataclass(frozen=True, slots=True)
class FilterConditionNode:
    """Syntax node for one public filter DSL condition.

    The public condition shape is always exactly `{field, op, value}`.
    Nullary operators such as `is_null` and `is_not_null` still require
    an explicit JSON `value: null`; the parser validates only this syntax
    contract and does not know whether the field or operator is meaningful
    for a runtime object descriptor.
    """

    field: str
    operator: str
    value: Any


@dataclass(frozen=True, slots=True)
class FilterGroupNode:
    """Syntax node for an `and` or `or` group in public filter DSL."""

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
