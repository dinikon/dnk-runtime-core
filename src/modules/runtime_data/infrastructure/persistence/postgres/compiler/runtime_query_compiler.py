from __future__ import annotations

from collections.abc import Sequence

from src.modules.runtime_data.application.models import (
    FetchPlan,
    PageSpec,
    SortSpec,
    TypedFilterExpression,
)
from src.modules.runtime_data.application.query.query_plan import RuntimeQueryPlan
from src.modules.runtime_data.domain import RuntimeDataValidationError
from src.modules.runtime_data.infrastructure.persistence.postgres.compiler.compiled_query import (
    CompiledQuery,
)
from src.modules.runtime_data.infrastructure.persistence.postgres.compiler.filter_sql_compiler import (
    PostgresFilterSqlCompiler,
)
from src.modules.runtime_data.infrastructure.persistence.postgres.compiler.identifier import (
    ensure_descriptor_identifiers,
    qualified_descriptor_table,
)
from src.modules.runtime_data.infrastructure.persistence.postgres.compiler.projection_sql_compiler import (
    PostgresProjectionSqlCompiler,
)
from src.modules.runtime_data.infrastructure.persistence.postgres.compiler.sort_sql_compiler import (
    PostgresSortSqlCompiler,
)
from src.modules.schema_registry.runtime import RuntimeObjectDescriptor


class PostgresRuntimeQueryCompiler:
    """Compiles validated runtime query plans to PostgreSQL SQL."""

    def __init__(
        self,
        *,
        filter_compiler: PostgresFilterSqlCompiler | None = None,
        sort_compiler: PostgresSortSqlCompiler | None = None,
        projection_compiler: PostgresProjectionSqlCompiler | None = None,
    ) -> None:
        self._filter_compiler = filter_compiler or PostgresFilterSqlCompiler()
        self._sort_compiler = sort_compiler or PostgresSortSqlCompiler()
        self._projection_compiler = (
            projection_compiler or PostgresProjectionSqlCompiler()
        )

    def compile_count(self, query_plan: RuntimeQueryPlan) -> CompiledQuery:
        descriptor = query_plan.descriptor
        ensure_descriptor_identifiers(descriptor)
        where = self.compile_where(
            filters=query_plan.filters,
        )
        sql_parts = [
            "SELECT COUNT(*) AS total",
            f"FROM {qualified_descriptor_table(descriptor)}",
        ]
        if where.sql:
            sql_parts.append(where.sql)
        return CompiledQuery(
            sql=" ".join(sql_parts),
            params=dict(where.params),
            bind_fields=dict(where.bind_fields),
        )

    def compile_search(self, query_plan: RuntimeQueryPlan) -> CompiledQuery:
        descriptor = query_plan.descriptor
        page = query_plan.page
        ensure_descriptor_identifiers(descriptor)
        self._validate_page(page)

        columns = self.compile_projection(
            descriptor=descriptor,
            fetch_plan=query_plan.fetch_plan,
        )
        where = self.compile_where(
            filters=query_plan.filters,
        )
        order_sql = self.compile_sort(
            descriptor=descriptor,
            sorting=query_plan.sorting,
        )

        params = dict(where.params)
        params["page_limit"] = page.limit
        params["page_offset"] = page.offset
        sql_parts = [
            f"SELECT {', '.join(columns)}",
            f"FROM {qualified_descriptor_table(descriptor)}",
        ]
        if where.sql:
            sql_parts.append(where.sql)
        if order_sql:
            sql_parts.append(order_sql)
        sql_parts.append("LIMIT :page_limit OFFSET :page_offset")
        return CompiledQuery(
            sql=" ".join(sql_parts),
            params=params,
            bind_fields=dict(where.bind_fields),
        )

    def compile_list(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        filters: Sequence[TypedFilterExpression],
        sorting: Sequence[SortSpec],
        page: PageSpec | None,
        fetch_plan: FetchPlan | None,
    ) -> CompiledQuery:
        ensure_descriptor_identifiers(descriptor)
        if page is not None:
            self._validate_page(page)

        columns = self.compile_projection(descriptor=descriptor, fetch_plan=fetch_plan)
        where = self.compile_where(filters=filters)
        order_sql = self.compile_sort(descriptor=descriptor, sorting=sorting)

        params = dict(where.params)
        sql_parts = [
            f"SELECT {', '.join(columns)}",
            f"FROM {qualified_descriptor_table(descriptor)}",
        ]
        if where.sql:
            sql_parts.append(where.sql)
        if order_sql:
            sql_parts.append(order_sql)
        if page is not None:
            sql_parts.append("LIMIT :page_limit OFFSET :page_offset")
            params["page_limit"] = page.limit
            params["page_offset"] = page.offset

        return CompiledQuery(
            sql=" ".join(sql_parts),
            params=params,
            bind_fields=dict(where.bind_fields),
        )

    def compile_where(
        self,
        *,
        filters: Sequence[TypedFilterExpression],
    ) -> CompiledQuery:
        return self._filter_compiler.compile_where(
            filters=filters,
        )

    def compile_sort(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        sorting: Sequence[SortSpec],
    ) -> str:
        return self._sort_compiler.compile(descriptor=descriptor, sorting=sorting)

    def compile_projection(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        fetch_plan: FetchPlan | None,
    ) -> list[str]:
        return self._projection_compiler.compile(
            descriptor=descriptor,
            fetch_plan=fetch_plan,
        )

    @staticmethod
    def _validate_page(page: PageSpec) -> None:
        if page.limit < 1:
            raise RuntimeDataValidationError("Page limit must be >= 1.")
        if page.offset < 0:
            raise RuntimeDataValidationError("Page offset must be >= 0.")


__all__ = ["PostgresRuntimeQueryCompiler"]
