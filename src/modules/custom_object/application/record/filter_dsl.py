from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from src.modules.custom_object.domain import CustomObjectValidationError
from src.modules.runtime_data import (
    FilterExpression,
    FilterGroupSpec,
    FilterSpec,
    SortSpec,
)

_SUPPORTED_OPERATORS = {"eq", "in", "contains", "gte", "lte"}


def parse_filter_payload(payload: Any) -> tuple[FilterExpression, ...]:
    """Парсит public Filter DSL в runtime_data filter expressions."""
    if payload is None or payload == {}:
        return ()

    if isinstance(payload, list):
        return tuple(_parse_filter_expression(item) for item in payload)

    return (_parse_filter_expression(payload),)


def parse_sort_payload(payload: Mapping[str, str] | None) -> tuple[SortSpec, ...]:
    """Парсит public sort map в стабильный список SortSpec."""
    if not payload:
        return ()

    sorting: list[SortSpec] = []
    for field_name, raw_direction in payload.items():
        direction = str(raw_direction).strip().lower()
        if direction not in {"asc", "desc"}:
            raise CustomObjectValidationError(
                f"Unsupported sort direction '{raw_direction}'."
            )
        sorting.append(SortSpec(field=field_name, direction=direction))
    return tuple(sorting)


def _parse_filter_expression(payload: Any) -> FilterExpression:
    if not isinstance(payload, Mapping):
        raise CustomObjectValidationError("Filter expression must be an object.")

    has_and = "and" in payload
    has_or = "or" in payload
    if has_and or has_or:
        if has_and and has_or:
            raise CustomObjectValidationError(
                "Filter group must contain only one of 'and' or 'or'."
            )
        if len(payload) != 1:
            raise CustomObjectValidationError(
                "Filter group cannot mix group operator with condition fields."
            )
        logic = "and" if has_and else "or"
        raw_items = payload[logic]
        if not isinstance(raw_items, Sequence) or isinstance(raw_items, (str, bytes)):
            raise CustomObjectValidationError(
                f"Filter group '{logic}' requires a list of expressions."
            )
        items = tuple(_parse_filter_expression(item) for item in raw_items)
        if not items:
            raise CustomObjectValidationError(
                f"Filter group '{logic}' requires at least one expression."
            )
        return FilterGroupSpec(logic=logic, items=items)

    field_name = payload.get("field")
    operator = payload.get("op")
    if not isinstance(field_name, str) or not field_name.strip():
        raise CustomObjectValidationError("Filter condition requires field.")
    if (
        not isinstance(operator, str)
        or operator.strip().lower() not in _SUPPORTED_OPERATORS
    ):
        raise CustomObjectValidationError(f"Unsupported filter operator '{operator}'.")
    if "value" not in payload:
        raise CustomObjectValidationError("Filter condition requires value.")

    return FilterSpec(
        field=field_name,
        op=operator.strip().lower(),
        value=payload["value"],
    )


__all__ = ["parse_filter_payload", "parse_sort_payload"]
