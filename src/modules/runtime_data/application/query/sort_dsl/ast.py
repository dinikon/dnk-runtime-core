from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

SortNodeDirection = Literal["asc", "desc"]


@dataclass(frozen=True, slots=True)
class SortExpressionNode:
    """Синтаксически разобранное выражение публичного sort DSL."""

    field: str
    direction: SortNodeDirection


__all__ = ["SortExpressionNode", "SortNodeDirection"]
