from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.modules.runtime_data.application.query.capabilities.field_query_capability import (
    FieldFilterCapability,
    FieldQueryCapability,
    FieldSortCapability,
)
from src.modules.runtime_data.application.query.filter_dsl import FilterOperatorRegistry
from src.modules.schema_registry.runtime import (
    RuntimeFieldDescriptor,
    RuntimeObjectDescriptor,
)

_INPUT_BY_TYPE: dict[str, str] = {
    "uuid": "text",
    "reference": "text",
    "text": "text",
    "select": "select",
    "multiselect": "multiselect",
    "datetime": "datetime",
    "date": "date",
    "int": "number",
    "decimal": "number",
    "bool": "checkbox",
    "json": "json",
}

_VALUE_TYPE_BY_TYPE: dict[str, str] = {
    "uuid": "string",
    "reference": "string",
    "text": "string",
    "select": "string",
    "multiselect": "string[]",
    "datetime": "datetime",
    "date": "date",
    "int": "number",
    "decimal": "number",
    "bool": "boolean",
    "json": "json",
}


class QueryCapabilityResolver:
    """Resolves frontend query capabilities from runtime descriptor policy."""

    def __init__(
        self,
        *,
        operator_registry: FilterOperatorRegistry | None = None,
    ) -> None:
        self._operator_registry = operator_registry or FilterOperatorRegistry()

    def resolve_for_descriptor(
        self,
        descriptor: RuntimeObjectDescriptor,
    ) -> tuple[FieldQueryCapability, ...]:
        """Return query capabilities for every field in descriptor order."""
        return tuple(self.resolve_for_field(field) for field in descriptor.fields)

    def resolve_for_field(
        self,
        field: RuntimeFieldDescriptor,
    ) -> FieldQueryCapability:
        """Return query capability for one runtime field."""
        input_type = _INPUT_BY_TYPE.get(field.type_code, "text")
        value_type = _VALUE_TYPE_BY_TYPE.get(field.type_code, "string")
        options = self._options_for(field)
        operators = self._operator_registry.operators_for(field.type_code)
        filter_enabled = field.is_filterable and bool(operators)

        return FieldQueryCapability(
            field_name=field.name,
            filter=FieldFilterCapability(
                enabled=filter_enabled,
                operators=operators if filter_enabled else (),
                input=input_type,
                value_type=value_type,
                options=options,
            ),
            sort=FieldSortCapability(enabled=field.is_sortable),
        )

    @staticmethod
    def _options_for(
        field: RuntimeFieldDescriptor,
    ) -> tuple[Mapping[str, Any], ...]:
        if field.type_code not in {"select", "multiselect"}:
            return ()
        return tuple(
            {"value": value, "label": label} for value, label in field.options.items()
        )


__all__ = ["QueryCapabilityResolver"]
