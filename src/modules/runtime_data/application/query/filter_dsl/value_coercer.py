from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from src.modules.runtime_data.application.query.filter_dsl.errors import (
    filter_dsl_error,
)
from src.modules.runtime_data.application.type_policy import RuntimeFieldTypePolicy
from src.modules.runtime_data.domain import RuntimeDataValidationError
from src.modules.schema_registry.runtime import RuntimeFieldDescriptor


class FilterValueCoercer:
    """Coerces public filter values to runtime Python values."""

    def __init__(self, type_policy: RuntimeFieldTypePolicy | None = None) -> None:
        self._type_policy = type_policy or RuntimeFieldTypePolicy()

    def coerce(
        self,
        *,
        field: RuntimeFieldDescriptor,
        operator: str,
        value: Any,
    ) -> Any:
        if operator in {"is_null", "is_not_null"}:
            return None

        if operator == "in":
            if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
                raise filter_dsl_error(
                    "INVALID_FILTER_VALUE_TYPE",
                    f"Field '{field.name}' with operator 'in' requires a list.",
                )
            values = list(value)
            if not values:
                raise filter_dsl_error(
                    "INVALID_FILTER_VALUE_TYPE",
                    f"Field '{field.name}' with operator 'in' requires at least one value.",
                )
            return [self._coerce_single(field=field, value=item) for item in values]

        if operator == "between":
            if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
                raise filter_dsl_error(
                    "INVALID_FILTER_VALUE_TYPE",
                    f"Field '{field.name}' with operator 'between' requires a two-item list.",
                )
            values = list(value)
            if len(values) != 2:
                raise filter_dsl_error(
                    "INVALID_FILTER_VALUE_TYPE",
                    f"Field '{field.name}' with operator 'between' requires exactly two values.",
                )
            return tuple(
                self._coerce_single(field=field, value=item) for item in values
            )

        return self._coerce_single(field=field, value=value)

    def _coerce_single(self, *, field: RuntimeFieldDescriptor, value: Any) -> Any:
        if field.type_code == "select" and field.options and value not in field.options:
            raise filter_dsl_error(
                "INVALID_FIELD_OPTION",
                f"Field '{field.name}' does not allow option '{value}'.",
            )
        try:
            return self._type_policy.coerce_value_for_field(
                field=field,
                raw_value=value,
            )
        except RuntimeDataValidationError as exc:
            raise filter_dsl_error(
                "INVALID_FILTER_VALUE_TYPE",
                f"Field '{field.name}' has invalid value for type '{field.type_code}'.",
            ) from exc


__all__ = ["FilterValueCoercer"]
