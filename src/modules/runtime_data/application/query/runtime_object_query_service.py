from __future__ import annotations

from src.modules.runtime_data.application.models import PageSpec
from src.modules.runtime_data.application.ports import RuntimeQueryGateway
from src.modules.runtime_data.application.query.filter_dsl import (
    FilterDslParser,
    FilterSemanticValidator,
)
from src.modules.runtime_data.application.query.query import RuntimeSearchRecordsQuery
from src.modules.runtime_data.application.query.query_plan import RuntimeQueryPlan
from src.modules.runtime_data.application.query.result import (
    RuntimeRecordDTO,
    RuntimeSearchRecordsResult,
)
from src.modules.runtime_data.application.query.sort_dsl import (
    SortDslParser,
    SortSemanticValidator,
)
from src.modules.runtime_data.domain import RuntimeDataValidationError
from src.modules.schema_registry.runtime import RuntimeObjectResolverProtocol


class RuntimeObjectQueryService:
    """Application service that owns runtime object search semantics."""

    def __init__(
        self,
        *,
        runtime_object_resolver: RuntimeObjectResolverProtocol,
        runtime_query_gateway: RuntimeQueryGateway,
        filter_parser: FilterDslParser | None = None,
        filter_validator: FilterSemanticValidator | None = None,
        sort_parser: SortDslParser | None = None,
        sort_validator: SortSemanticValidator | None = None,
    ) -> None:
        self._runtime_object_resolver = runtime_object_resolver
        self._runtime_query_gateway = runtime_query_gateway
        self._filter_parser = filter_parser or FilterDslParser()
        self._filter_validator = filter_validator or FilterSemanticValidator()
        self._sort_parser = sort_parser or SortDslParser()
        self._sort_validator = sort_validator or SortSemanticValidator()

    async def search_records(
        self,
        query: RuntimeSearchRecordsQuery,
    ) -> RuntimeSearchRecordsResult:
        """Searches runtime records by public filter/sort DSL and pagination."""

        if query.limit < 1:
            raise RuntimeDataValidationError("Search limit must be >= 1.")
        if query.offset < 0:
            raise RuntimeDataValidationError("Search offset must be >= 0.")

        descriptor = await self._runtime_object_resolver.resolve(
            tenant_id=query.tenant_id,
            object_name=query.object_name,
        )

        filter_ast = self._filter_parser.parse(query.filter_dsl)
        sort_ast = self._sort_parser.parse(query.sort_dsl)
        filters = self._filter_validator.validate(
            descriptor=descriptor,
            filter_ast=filter_ast,
        )
        sorting = self._sort_validator.validate(
            descriptor=descriptor,
            sort_ast=sort_ast,
        )

        query_plan = RuntimeQueryPlan(
            descriptor=descriptor,
            filters=filters,
            sorting=sorting,
            page=PageSpec(limit=query.limit, offset=query.offset),
        )
        page = await self._runtime_query_gateway.search(
            descriptor=query_plan.descriptor,
            filters=query_plan.filters,
            sorting=query_plan.sorting,
            page=query_plan.page,
        )

        return RuntimeSearchRecordsResult(
            rows=tuple(
                RuntimeRecordDTO(
                    id=row.get(descriptor.pk),
                    values=dict(row),
                )
                for row in page.rows
            ),
            total=page.total,
            limit=query.limit,
            offset=query.offset,
        )


__all__ = ["RuntimeObjectQueryService"]
