from __future__ import annotations

from src.modules.runtime_data.application.query.filter_dsl.errors import (
    filter_dsl_error,
)

_ALLOWED_BY_TYPE = {
    "uuid": {
        "eq",
        "neq",
        "in",
        "is_null",
        "is_not_null",
    },
    "reference": {
        "eq",
        "neq",
        "in",
        "is_null",
        "is_not_null",
    },
    "text": {
        "eq",
        "neq",
        "contains",
        "starts_with",
        "ends_with",
        "in",
        "is_null",
        "is_not_null",
    },
    "select": {
        "eq",
        "neq",
        "in",
        "is_null",
        "is_not_null",
    },
    "multiselect": {
        "contains_any",
        "contains_all",
        "not_contains_any",
        "is_empty",
        "is_not_empty",
        "is_null",
        "is_not_null",
    },
    "datetime": {
        "eq",
        "neq",
        "gt",
        "gte",
        "lt",
        "lte",
        "between",
        "is_null",
        "is_not_null",
    },
    "date": {
        "eq",
        "neq",
        "gt",
        "gte",
        "lt",
        "lte",
        "between",
        "is_null",
        "is_not_null",
    },
    "int": {
        "eq",
        "neq",
        "gt",
        "gte",
        "lt",
        "lte",
        "between",
        "is_null",
        "is_not_null",
    },
    "decimal": {
        "eq",
        "neq",
        "gt",
        "gte",
        "lt",
        "lte",
        "between",
        "is_null",
        "is_not_null",
    },
    "bool": {
        "eq",
        "neq",
        "is_null",
        "is_not_null",
    },
    "json": {
        "is_null",
        "is_not_null",
    },
}


class FilterOperatorRegistry:
    """Knows which public filter operators are valid for each runtime field type."""

    def validate(self, *, field_type: str, operator: str, field_name: str) -> None:
        allowed = _ALLOWED_BY_TYPE.get(field_type)
        if allowed is None or operator not in allowed:
            raise filter_dsl_error(
                "UNSUPPORTED_OPERATOR_FOR_FIELD_TYPE",
                (
                    f"Field '{field_name}' of type '{field_type}' "
                    f"does not support operator '{operator}'."
                ),
                details={
                    "field": field_name,
                    "field_type": field_type,
                    "operator": operator,
                },
            )


__all__ = ["FilterOperatorRegistry"]
