from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from src.modules.runtime_data.application.query.filter_dsl.errors import (
    filter_dsl_error,
)
from src.modules.runtime_data.application.query.sort_dsl.ast import SortExpressionNode


class SortDslParser:
    """Parses public sort DSL into syntax nodes."""

    def parse(self, payload: Any) -> tuple[SortExpressionNode, ...]:
        if payload is None:
            return ()
        if not isinstance(payload, Sequence) or isinstance(payload, (str, bytes)):
            raise filter_dsl_error(
                "INVALID_SORT_DSL",
                "Sort payload must be a list.",
            )

        items: list[SortExpressionNode] = []
        for item in payload:
            if not isinstance(item, Mapping):
                raise filter_dsl_error(
                    "INVALID_SORT_DSL",
                    "Sort item must be an object.",
                )
            if set(item.keys()) != {"field", "direction"}:
                raise filter_dsl_error(
                    "INVALID_SORT_DSL",
                    "Sort item must contain only field and direction.",
                )
            field_name = item["field"]
            direction = item["direction"]
            if not isinstance(field_name, str) or not field_name.strip():
                raise filter_dsl_error(
                    "INVALID_SORT_DSL",
                    "Sort item field must be a non-empty string.",
                )
            if not isinstance(direction, str):
                raise filter_dsl_error(
                    "INVALID_SORT_DSL",
                    "Sort direction must be a string.",
                )
            normalized_direction = direction.strip().lower()
            if normalized_direction not in {"asc", "desc"}:
                raise filter_dsl_error(
                    "INVALID_SORT_DSL",
                    "Sort direction must be 'asc' or 'desc'.",
                )
            items.append(
                SortExpressionNode(
                    field=field_name.strip(),
                    direction=normalized_direction,
                )
            )
        return tuple(items)


__all__ = ["SortDslParser"]
