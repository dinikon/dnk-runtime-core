from __future__ import annotations

from src.modules.runtime_data.application.models import (
    TypedFilterExpression,
    TypedFilterGroupSpec,
    TypedFilterSpec,
)
from src.modules.runtime_data.application.query.filter_dsl.ast import (
    FilterConditionNode,
    FilterGroupNode,
    FilterNode,
)
from src.modules.runtime_data.application.query.filter_dsl.errors import (
    filter_dsl_error,
)
from src.modules.runtime_data.application.query.filter_dsl.operator_registry import (
    FilterOperatorRegistry,
)
from src.modules.runtime_data.application.query.filter_dsl.value_coercer import (
    FilterValueCoercer,
)
from src.modules.schema_registry.runtime import RuntimeObjectDescriptor


class FilterSemanticValidator:
    """Validates filter syntax AST against a runtime object descriptor."""

    def __init__(
        self,
        *,
        operator_registry: FilterOperatorRegistry | None = None,
        value_coercer: FilterValueCoercer | None = None,
    ) -> None:
        self._operator_registry = operator_registry or FilterOperatorRegistry()
        self._value_coercer = value_coercer or FilterValueCoercer()

    def validate(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        filter_ast: tuple[FilterNode, ...],
    ) -> tuple[TypedFilterExpression, ...]:
        return tuple(
            self._validate_node(descriptor=descriptor, node=node) for node in filter_ast
        )

    def _validate_node(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        node: FilterNode,
    ) -> TypedFilterExpression:
        if isinstance(node, FilterGroupNode):
            return TypedFilterGroupSpec(
                logic=node.logic,
                items=tuple(
                    self._validate_node(descriptor=descriptor, node=item)
                    for item in node.items
                ),
            )

        if isinstance(node, FilterConditionNode):
            field = descriptor.field_by_name(node.field)
            if field is None:
                raise filter_dsl_error(
                    "UNKNOWN_FILTER_FIELD",
                    f"Unknown filter field '{node.field}'.",
                    details={
                        "field": node.field,
                    },
                )
            if not field.is_filterable:
                raise filter_dsl_error(
                    "FIELD_IS_NOT_FILTERABLE",
                    f"Field '{field.name}' is not filterable.",
                    details={
                        "field": field.name,
                    },
                )
            self._operator_registry.validate(
                field_type=field.type_code,
                operator=node.operator,
                field_name=field.name,
            )
            coerced_value = self._value_coercer.coerce(
                field=field,
                operator=node.operator,
                value=node.value,
            )
            return TypedFilterSpec(
                field=field,
                op=node.operator,
                value=coerced_value,
            )

        raise filter_dsl_error(
            "INVALID_FILTER_DSL",
            f"Unsupported filter AST node '{type(node).__name__}'.",
            details={
                "node_type": type(node).__name__,
            },
        )


__all__ = ["FilterSemanticValidator"]
