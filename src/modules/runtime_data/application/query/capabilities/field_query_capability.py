from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class FieldFilterCapability:
    """Frontend-facing filter capability for one runtime field."""

    enabled: bool
    operators: tuple[str, ...]
    input: str
    value_type: str
    options: tuple[Mapping[str, Any], ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class FieldSortCapability:
    """Frontend-facing sort capability for one runtime field."""

    enabled: bool


@dataclass(frozen=True, slots=True)
class FieldQueryCapability:
    """Frontend-facing query capability for one runtime field."""

    field_name: str
    filter: FieldFilterCapability
    sort: FieldSortCapability


def disabled_filter_capability(
    *,
    input: str = "text",
    value_type: str = "string",
    options: tuple[Mapping[str, Any], ...] = (),
) -> FieldFilterCapability:
    """Build a disabled filter capability with stable response shape."""
    return FieldFilterCapability(
        enabled=False,
        operators=(),
        input=input,
        value_type=value_type,
        options=options,
    )


def disabled_sort_capability() -> FieldSortCapability:
    """Build a disabled sort capability with stable response shape."""
    return FieldSortCapability(enabled=False)


__all__ = [
    "FieldFilterCapability",
    "FieldQueryCapability",
    "FieldSortCapability",
    "disabled_filter_capability",
    "disabled_sort_capability",
]
