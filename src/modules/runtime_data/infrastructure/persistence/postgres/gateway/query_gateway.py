from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.runtime_data.application.models import (
    FetchPlan,
    FilterExpression,
    PageSpec,
    RuntimeRowsPage,
    SortSpec,
)
from src.modules.runtime_data.application.ports import (
    RuntimeQueryGateway,
    RuntimeRelationLoader,
)
from src.modules.runtime_data.application.query.query_plan import RuntimeQueryPlan
from src.modules.runtime_data.application.type_policy import RuntimeFieldTypePolicy
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
from src.modules.runtime_data.infrastructure.persistence.postgres.gateway.relation_loader import (
    PostgresRuntimeRelationLoader,
)
from src.modules.schema_registry.runtime import RuntimeObjectDescriptor


class PostgresRuntimeQueryGateway(PostgresRuntimeGatewayBase, RuntimeQueryGateway):
    """PostgreSQL query gateway for runtime records."""

    def __init__(
        self,
        session: AsyncSession,
        type_policy: RuntimeFieldTypePolicy | None = None,
        query_compiler: PostgresRuntimeQueryCompiler | None = None,
        relation_loader: RuntimeRelationLoader | None = None,
        executor: PostgresSqlExecutor | None = None,
    ) -> None:
        self._init_runtime_gateway_base(
            session=session,
            type_policy=type_policy,
            query_compiler=query_compiler,
            executor=executor,
        )
        self._relation_loader = relation_loader or PostgresRuntimeRelationLoader(
            session=session,
        )

    async def get_by_id(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        object_id: Any,
        fetch_plan: FetchPlan | None = None,
    ) -> Mapping[str, Any] | None:
        self._ensure_descriptor(descriptor)
        pk_field = self._required_field(descriptor, descriptor.pk)
        pk_value = self._type_policy.coerce_value_for_field(
            field=pk_field,
            raw_value=object_id,
        )

        columns = self._query_compiler.compile_projection(
            descriptor=descriptor,
            fetch_plan=fetch_plan,
        )
        sql = (
            f"SELECT {', '.join(columns)} "
            f"FROM {qualified_descriptor_table(descriptor)} "
            f"WHERE {quote_identifier(descriptor.pk)} = :pk_value "
            "LIMIT 1"
        )
        result = await self._execute(
            sql, {"pk_value": pk_value}, bind_fields={"pk_value": pk_field}
        )
        row = result.mappings().first()
        if row is None:
            return None
        normalized = self._type_policy.normalize_row(descriptor=descriptor, row=row)
        rows = await self._load_relations_if_needed(
            descriptor=descriptor,
            rows=[normalized],
            fetch_plan=fetch_plan,
        )
        return rows[0] if rows else None

    async def list(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        filters: Sequence[FilterExpression] = (),
        sorting: Sequence[SortSpec] = (),
        page: PageSpec | None = None,
        fetch_plan: FetchPlan | None = None,
    ) -> list[Mapping[str, Any]]:
        self._ensure_descriptor(descriptor)
        typed_filters = self._typed_filter_expressions(
            descriptor=descriptor,
            filters=filters,
        )
        compiled = self._query_compiler.compile_list(
            descriptor=descriptor,
            filters=typed_filters,
            sorting=sorting,
            page=page,
            fetch_plan=fetch_plan,
        )

        result = await self._execute(
            compiled.sql,
            compiled.params,
            bind_fields=compiled.bind_fields,
        )
        rows = result.mappings().all()
        normalized_rows = [
            self._type_policy.normalize_row(descriptor=descriptor, row=row)
            for row in rows
        ]
        return await self._load_relations_if_needed(
            descriptor=descriptor,
            rows=normalized_rows,
            fetch_plan=fetch_plan,
        )

    async def search(
        self,
        query_plan: RuntimeQueryPlan,
    ) -> RuntimeRowsPage:
        descriptor = query_plan.descriptor
        fetch_plan = query_plan.fetch_plan

        self._ensure_descriptor(descriptor)

        compiled_count = self._query_compiler.compile_count(query_plan)
        count_result = await self._execute(
            compiled_count.sql,
            compiled_count.params,
            bind_fields=compiled_count.bind_fields,
        )
        total = int(count_result.scalar() or 0)

        compiled_page = self._query_compiler.compile_search(query_plan)
        result = await self._execute(
            compiled_page.sql,
            compiled_page.params,
            bind_fields=compiled_page.bind_fields,
        )
        rows = result.mappings().all()
        normalized_rows = [
            self._type_policy.normalize_row(descriptor=descriptor, row=row)
            for row in rows
        ]
        loaded_rows = await self._load_relations_if_needed(
            descriptor=descriptor,
            rows=normalized_rows,
            fetch_plan=fetch_plan,
        )
        return RuntimeRowsPage(rows=tuple(loaded_rows), total=total)

    async def _load_relations_if_needed(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        rows: Sequence[Mapping[str, Any]],
        fetch_plan: FetchPlan | None,
    ) -> list[Mapping[str, Any]]:
        if fetch_plan is None or not fetch_plan.relations or not rows:
            return [dict(row) for row in rows]
        return await self._relation_loader.load(
            descriptor=descriptor,
            rows=rows,
            fetch_plan=fetch_plan,
        )


__all__ = ["PostgresRuntimeQueryGateway"]
