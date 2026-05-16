from __future__ import annotations

from src.modules.runtime_data.application.models import SortSpec
from src.modules.runtime_data.application.query.filter_dsl.errors import (
    filter_dsl_error,
)
from src.modules.runtime_data.application.query.sort_dsl.ast import SortExpressionNode
from src.modules.schema_registry.runtime import RuntimeObjectDescriptor

_SORTABLE_SYSTEM_FIELDS = frozenset({"id", "created_at", "updated_at"})
_UNSORTABLE_TYPES = frozenset({"json", "multiselect"})


class SortSemanticValidator:
    """Validates sort syntax AST against a runtime object descriptor."""

    def validate(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        sort_ast: tuple[SortExpressionNode, ...],
    ) -> tuple[SortSpec, ...]:
        sorting: list[SortSpec] = []
        for node in sort_ast:
            field = descriptor.field_by_name(node.field)
            if field is None:
                raise filter_dsl_error(
                    "UNKNOWN_SORT_FIELD",
                    f"Unknown sort field '{node.field}'.",
                )
            if (
                field.kind.strip().lower() == "system"
                and field.name not in _SORTABLE_SYSTEM_FIELDS
            ):
                raise filter_dsl_error(
                    "FIELD_IS_NOT_SORTABLE",
                    f"Field '{field.name}' is not sortable.",
                )
            if field.type_code in _UNSORTABLE_TYPES:
                raise filter_dsl_error(
                    "FIELD_IS_NOT_SORTABLE",
                    f"Field '{field.name}' of type '{field.type_code}' is not sortable.",
                )
            sorting.append(SortSpec(field=field.name, direction=node.direction))
        return tuple(sorting)


__all__ = ["SortSemanticValidator"]
