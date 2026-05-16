from __future__ import annotations

from src.modules.runtime_data.application.models import SortSpec
from src.modules.runtime_data.application.query.filter_dsl.errors import (
    filter_dsl_error,
)
from src.modules.runtime_data.application.query.sort_dsl.ast import SortExpressionNode
from src.modules.schema_registry.runtime import RuntimeObjectDescriptor


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
                    details={
                        "field": node.field,
                    },
                )
            if not field.is_sortable:
                raise filter_dsl_error(
                    "FIELD_IS_NOT_SORTABLE",
                    f"Field '{field.name}' is not sortable.",
                    details={
                        "field": field.name,
                    },
                )
            sorting.append(SortSpec(field=field.name, direction=node.direction))
        return tuple(sorting)


__all__ = ["SortSemanticValidator"]
