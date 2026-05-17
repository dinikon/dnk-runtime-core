from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from src.modules.runtime_data.application.models import (
    FilterLogic,
    TypedFilterExpression,
    TypedFilterGroupSpec,
    TypedFilterSpec,
)
from src.modules.runtime_data.application.query.filter_dsl.ast import (
    FilterConditionNode,
)
from src.modules.runtime_data.application.query.filter_dsl.operator_registry import (
    FilterOperatorRegistry,
)
from src.modules.runtime_data.application.query.filter_dsl.semantic_validator import (
    FilterSemanticValidator,
)
from src.modules.runtime_data.application.query.filter_dsl.value_coercer import (
    FilterValueCoercer,
)
from src.modules.runtime_data.domain.error import RuntimeDataValidationError
from src.modules.schema_registry.runtime import RuntimeObjectDescriptor


class RuntimeTypedFilterBuilder:
    """Builds typed runtime filters for internal application repositories.

    Public search requests should still go through FilterDslParser first. This
    helper is for trusted internal filters that already know the desired field
    and operator, while keeping descriptor lookup, operator policy, and value
    coercion in application code rather than PostgreSQL infrastructure.
    """

    def __init__(
        self,
        *,
        operator_registry: FilterOperatorRegistry | None = None,
        value_coercer: FilterValueCoercer | None = None,
    ) -> None:
        self._semantic_validator = FilterSemanticValidator(
            operator_registry=operator_registry,
            value_coercer=value_coercer,
        )

    def condition(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        field: str,
        op: str,
        value: Any,
    ) -> TypedFilterSpec:
        expression = self._semantic_validator.validate(
            descriptor=descriptor,
            filter_ast=(FilterConditionNode(field=field, operator=op, value=value),),
        )[0]
        if not isinstance(expression, TypedFilterSpec):
            raise RuntimeDataValidationError(
                "Internal runtime filter builder produced a non-condition filter."
            )
        return expression

    def group(
        self,
        *,
        logic: FilterLogic,
        items: Sequence[TypedFilterExpression],
    ) -> TypedFilterGroupSpec:
        if not items:
            raise RuntimeDataValidationError(
                "Internal runtime filter group requires at least one item."
            )
        return TypedFilterGroupSpec(logic=logic, items=tuple(items))


__all__ = ["RuntimeTypedFilterBuilder"]
