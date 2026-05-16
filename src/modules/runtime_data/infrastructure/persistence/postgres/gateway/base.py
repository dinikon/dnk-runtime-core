from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.runtime_data.application.models import (
    FilterExpression,
    FilterGroupSpec,
    FilterSpec,
    TypedFilterExpression,
    TypedFilterGroupSpec,
    TypedFilterSpec,
)
from src.modules.runtime_data.application.query.filter_dsl import FilterValueCoercer
from src.modules.runtime_data.application.type_policy import RuntimeFieldTypePolicy
from src.modules.runtime_data.domain import (
    RuntimeDataPolicyError,
    RuntimeDataValidationError,
)
from src.modules.runtime_data.infrastructure.persistence.postgres.compiler import (
    PostgresRuntimeQueryCompiler,
)
from src.modules.runtime_data.infrastructure.persistence.postgres.compiler.identifier import (
    ensure_descriptor_identifiers,
    quote_identifier,
)
from src.modules.runtime_data.infrastructure.persistence.postgres.execution import (
    PostgresSqlExecutor,
)
from src.modules.schema_registry.runtime import (
    RuntimeFieldDescriptor,
    RuntimeObjectDescriptor,
)

_DEFAULT_RUNTIME_ERROR_MESSAGE = (
    "Runtime data persistence failed; schema metadata may be incompatible "
    "with the physical database."
)


class PostgresRuntimeGatewayBase:
    """Shared PostgreSQL runtime gateway infrastructure."""

    def _init_runtime_gateway_base(
        self,
        *,
        session: AsyncSession,
        type_policy: RuntimeFieldTypePolicy | None = None,
        query_compiler: PostgresRuntimeQueryCompiler | None = None,
        executor: PostgresSqlExecutor | None = None,
    ) -> None:
        self._session = session
        self._type_policy = type_policy or RuntimeFieldTypePolicy()
        self._value_coercer = FilterValueCoercer(self._type_policy)
        self._query_compiler = query_compiler or PostgresRuntimeQueryCompiler()
        self._executor = executor or PostgresSqlExecutor(
            session,
            error_message=_DEFAULT_RUNTIME_ERROR_MESSAGE,
        )

    async def _execute(
        self,
        sql: str,
        params: Mapping[str, Any] | None = None,
        *,
        bind_fields: Mapping[str, RuntimeFieldDescriptor] | None = None,
    ):
        return await self._executor.execute(
            sql,
            params,
            bind_fields=bind_fields,
        )

    def _typed_filter_expressions(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        filters: Sequence[FilterExpression],
    ) -> tuple[TypedFilterExpression, ...]:
        return tuple(
            self._typed_filter_expression(descriptor=descriptor, filter_spec=item)
            for item in filters
        )

    def _typed_filter_expression(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        filter_spec: FilterExpression,
    ) -> TypedFilterExpression:
        if isinstance(filter_spec, FilterGroupSpec):
            return TypedFilterGroupSpec(
                logic=filter_spec.logic,
                items=tuple(
                    self._typed_filter_expression(
                        descriptor=descriptor,
                        filter_spec=item,
                    )
                    for item in filter_spec.items
                ),
            )

        if isinstance(filter_spec, FilterSpec):
            field = descriptor.field_by_name(filter_spec.field)
            if field is None:
                raise RuntimeDataValidationError(
                    f"Unknown filter field '{filter_spec.field}'."
                )
            return TypedFilterSpec(
                field=field,
                op=filter_spec.op,
                value=self._value_coercer.coerce(
                    field=field,
                    operator=filter_spec.op,
                    value=filter_spec.value,
                ),
            )

        raise RuntimeDataValidationError(
            f"Unsupported filter expression '{type(filter_spec).__name__}'."
        )

    def _build_set_clauses(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        patch: Mapping[str, Any],
    ) -> tuple[list[str], dict[str, Any], dict[str, RuntimeFieldDescriptor]]:
        set_clauses: list[str] = []
        params: dict[str, Any] = {}
        bind_fields: dict[str, RuntimeFieldDescriptor] = {}
        for index, (field_name, value) in enumerate(patch.items()):
            field = descriptor.fields_by_name[field_name]
            param_name = f"u_{index}"
            set_clauses.append(f"{quote_identifier(field_name)} = :{param_name}")
            params[param_name] = value
            bind_fields[param_name] = field
        if descriptor.field_by_name("updated_at") is not None:
            set_clauses.append(f'{quote_identifier("updated_at")} = CURRENT_TIMESTAMP')
        return set_clauses, params, bind_fields

    @staticmethod
    def _required_field(
        descriptor: RuntimeObjectDescriptor,
        field_name: str,
    ) -> RuntimeFieldDescriptor:
        field = descriptor.field_by_name(field_name)
        if field is None:
            raise RuntimeDataPolicyError(
                f"Descriptor does not contain required field '{field_name}'."
            )
        return field

    def _ensure_descriptor(self, descriptor: RuntimeObjectDescriptor) -> None:
        ensure_descriptor_identifiers(descriptor)
        self._required_field(descriptor, descriptor.pk)


__all__ = ["PostgresRuntimeGatewayBase"]
