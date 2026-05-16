from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.runtime_data.application.models import (
    FilterExpression,
    SortSpec,
)
from src.modules.runtime_data.application.ports import (
    RuntimeCommandGateway,
    RuntimeQueryGateway,
)
from src.modules.runtime_data.application.type_policy import RuntimeFieldTypePolicy
from src.modules.runtime_data.domain import (
    RuntimeDataPolicyError,
    RuntimeDataValidationError,
)
from src.modules.runtime_data.infrastructure.persistence.postgres.compiler import (
    PostgresRuntimeQueryCompiler,
)
from src.modules.runtime_data.infrastructure.persistence.postgres.compiler.identifier import (
    qualified_descriptor_table,
    quote_identifier,
)
from src.modules.runtime_data.infrastructure.persistence.postgres.execution import (
    PostgresSqlExecutor,
)
from src.modules.runtime_data.infrastructure.persistence.postgres.gateway.base import (
    PostgresRuntimeGatewayBase,
)
from src.modules.runtime_data.infrastructure.persistence.postgres.gateway.query_gateway import (
    PostgresRuntimeQueryGateway,
)
from src.modules.schema_registry.runtime import (
    RuntimeFieldDescriptor,
    RuntimeObjectDescriptor,
)


class PostgresRuntimeCommandGateway(PostgresRuntimeGatewayBase, RuntimeCommandGateway):
    """PostgreSQL command gateway for runtime records."""

    def __init__(
        self,
        session: AsyncSession,
        type_policy: RuntimeFieldTypePolicy | None = None,
        query_compiler: PostgresRuntimeQueryCompiler | None = None,
        query_gateway: RuntimeQueryGateway | None = None,
        executor: PostgresSqlExecutor | None = None,
    ) -> None:
        self._init_runtime_gateway_base(
            session=session,
            type_policy=type_policy,
            query_compiler=query_compiler,
            executor=executor,
        )
        self._query_gateway = query_gateway or PostgresRuntimeQueryGateway(
            session=session,
            type_policy=self._type_policy,
            query_compiler=self._query_compiler,
            executor=self._executor,
        )

    async def insert(
        self,
        descriptor: RuntimeObjectDescriptor,
        payload: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        self._ensure_descriptor(descriptor)
        coerced_payload = self._type_policy.coerce_insert_payload(
            descriptor=descriptor,
            payload=payload,
        )
        table_ref = qualified_descriptor_table(descriptor)
        selected_columns = self._query_compiler.compile_projection(
            descriptor=descriptor, fetch_plan=None
        )

        if coerced_payload:
            columns: list[str] = []
            values: list[str] = []
            params: dict[str, Any] = {}
            bind_fields: dict[str, RuntimeFieldDescriptor] = {}
            for index, (field_name, value) in enumerate(coerced_payload.items()):
                field = descriptor.fields_by_name[field_name]
                columns.append(quote_identifier(field_name))
                param_name = f"v_{index}"
                values.append(f":{param_name}")
                params[param_name] = value
                bind_fields[param_name] = field
            sql = (
                f"INSERT INTO {table_ref} ({', '.join(columns)}) "
                f"VALUES ({', '.join(values)}) "
                f"RETURNING {', '.join(selected_columns)}"
            )
            result = await self._execute(sql, params, bind_fields=bind_fields)
        else:
            sql = f"INSERT INTO {table_ref} DEFAULT VALUES RETURNING {', '.join(selected_columns)}"
            result = await self._execute(sql)

        row = result.mappings().first()
        if row is None:
            raise RuntimeDataPolicyError("Insert operation did not return a row.")
        return self._type_policy.normalize_row(descriptor=descriptor, row=row)

    async def update(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        object_id: Any,
        patch: Mapping[str, Any],
    ) -> Mapping[str, Any] | None:
        self._ensure_descriptor(descriptor)
        coerced_patch = self._type_policy.coerce_patch_payload(
            descriptor=descriptor,
            patch=patch,
        )

        pk_field = self._required_field(descriptor, descriptor.pk)
        pk_value = self._type_policy.coerce_value_for_field(
            field=pk_field,
            raw_value=object_id,
        )

        set_clauses: list[str] = []
        params: dict[str, Any] = {"pk_value": pk_value}
        bind_fields: dict[str, RuntimeFieldDescriptor] = {"pk_value": pk_field}

        for index, (field_name, value) in enumerate(coerced_patch.items()):
            field = descriptor.fields_by_name[field_name]
            param_name = f"p_{index}"
            set_clauses.append(f"{quote_identifier(field_name)} = :{param_name}")
            params[param_name] = value
            bind_fields[param_name] = field

        if descriptor.field_by_name("updated_at") is not None:
            set_clauses.append(f'{quote_identifier("updated_at")} = CURRENT_TIMESTAMP')

        if not set_clauses:
            return await self._query_gateway.get_by_id(
                descriptor=descriptor,
                object_id=pk_value,
            )

        table_ref = qualified_descriptor_table(descriptor)
        selected_columns = self._query_compiler.compile_projection(
            descriptor=descriptor, fetch_plan=None
        )
        sql = (
            f"UPDATE {table_ref} "
            f"SET {', '.join(set_clauses)} "
            f"WHERE {quote_identifier(descriptor.pk)} = :pk_value "
            f"RETURNING {', '.join(selected_columns)}"
        )

        result = await self._execute(sql, params, bind_fields=bind_fields)
        row = result.mappings().first()
        if row is None:
            return None
        return self._type_policy.normalize_row(descriptor=descriptor, row=row)

    async def delete(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        object_id: Any,
    ) -> bool:
        self._ensure_descriptor(descriptor)
        pk_field = self._required_field(descriptor, descriptor.pk)
        pk_value = self._type_policy.coerce_value_for_field(
            field=pk_field,
            raw_value=object_id,
        )
        sql = (
            f"DELETE FROM {qualified_descriptor_table(descriptor)} "
            f"WHERE {quote_identifier(descriptor.pk)} = :pk_value "
            f"RETURNING {quote_identifier(descriptor.pk)}"
        )
        result = await self._execute(
            sql, {"pk_value": pk_value}, bind_fields={"pk_value": pk_field}
        )
        return result.scalar() is not None

    async def update_where(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        filters: Sequence[FilterExpression],
        patch: Mapping[str, Any],
    ) -> list[Mapping[str, Any]]:
        self._ensure_descriptor(descriptor)
        coerced_patch = self._type_policy.coerce_patch_payload(
            descriptor=descriptor,
            patch=patch,
        )
        set_clauses, params, bind_fields = self._build_set_clauses(
            descriptor=descriptor,
            patch=coerced_patch,
        )
        if not set_clauses:
            return []

        typed_filters = self._typed_filter_expressions(
            descriptor=descriptor,
            filters=filters,
        )
        where = self._query_compiler.compile_where(filters=typed_filters)
        params.update(where.params)
        bind_fields.update(where.bind_fields)
        columns = self._query_compiler.compile_projection(
            descriptor=descriptor,
            fetch_plan=None,
        )

        sql = (
            f"UPDATE {qualified_descriptor_table(descriptor)} "
            f"SET {', '.join(set_clauses)} "
            f"{where.sql} "
            f"RETURNING {', '.join(columns)}"
        )
        result = await self._execute(sql, params, bind_fields=bind_fields)
        return [
            self._type_policy.normalize_row(descriptor=descriptor, row=row)
            for row in result.mappings().all()
        ]

    async def claim(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        filters: Sequence[FilterExpression],
        patch: Mapping[str, Any],
        sorting: Sequence[SortSpec] = (),
        limit: int = 1,
    ) -> list[Mapping[str, Any]]:
        self._ensure_descriptor(descriptor)
        if limit < 1:
            raise RuntimeDataValidationError("Claim limit must be >= 1.")
        coerced_patch = self._type_policy.coerce_patch_payload(
            descriptor=descriptor,
            patch=patch,
        )
        set_clauses, params, bind_fields = self._build_set_clauses(
            descriptor=descriptor,
            patch=coerced_patch,
        )
        if not set_clauses:
            return []

        typed_filters = self._typed_filter_expressions(
            descriptor=descriptor,
            filters=filters,
        )
        where = self._query_compiler.compile_where(filters=typed_filters)
        params.update(where.params)
        bind_fields.update(where.bind_fields)
        params["claim_limit"] = limit
        order_sql = self._query_compiler.compile_sort(
            descriptor=descriptor,
            sorting=sorting,
        )
        table_ref = qualified_descriptor_table(descriptor)
        pk_sql = quote_identifier(descriptor.pk)
        columns = self._query_compiler.compile_projection(
            descriptor=descriptor,
            fetch_plan=None,
        )
        sql = (
            "WITH claimed AS ("
            f"SELECT {pk_sql} FROM {table_ref} "
            f"{where.sql} "
            f"{order_sql} "
            "LIMIT :claim_limit "
            "FOR UPDATE SKIP LOCKED"
            ") "
            f"UPDATE {table_ref} "
            f"SET {', '.join(set_clauses)} "
            f"WHERE {pk_sql} IN (SELECT {pk_sql} FROM claimed) "
            f"RETURNING {', '.join(columns)}"
        )
        result = await self._execute(sql, params, bind_fields=bind_fields)
        return [
            self._type_policy.normalize_row(descriptor=descriptor, row=row)
            for row in result.mappings().all()
        ]


__all__ = ["PostgresRuntimeCommandGateway"]
