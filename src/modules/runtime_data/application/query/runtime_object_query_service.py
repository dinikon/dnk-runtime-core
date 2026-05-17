from __future__ import annotations

from src.modules.runtime_data.application.models import (
    MAX_SEARCH_LIMIT,
    PageSpec,
    SortSpec,
)
from src.modules.runtime_data.application.ports import RuntimeQueryGateway
from src.modules.runtime_data.application.query.filter_dsl.parser import FilterDslParser
from src.modules.runtime_data.application.query.filter_dsl.semantic_validator import (
    FilterSemanticValidator,
)
from src.modules.runtime_data.application.query.query import RuntimeSearchRecordsQuery
from src.modules.runtime_data.application.query.query_plan import RuntimeQueryPlan
from src.modules.runtime_data.application.query.result import (
    RuntimeRecordDTO,
    RuntimeSearchRecordsResult,
)
from src.modules.runtime_data.application.query.sort_dsl.parser import SortDslParser
from src.modules.runtime_data.application.query.sort_dsl.validator import (
    SortSemanticValidator,
)
from src.modules.runtime_data.domain.error import RuntimeDataValidationError
from src.modules.schema_registry.runtime import (
    RuntimeObjectDescriptor,
    RuntimeObjectResolverProtocol,
)


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
        if query.limit > MAX_SEARCH_LIMIT:
            raise RuntimeDataValidationError(
                f"Search limit must be <= {MAX_SEARCH_LIMIT}."
            )
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
        if not sorting:
            sorting = self._default_sorting(descriptor)

        query_plan = RuntimeQueryPlan(
            descriptor=descriptor,
            filters=filters,
            sorting=sorting,
            page=PageSpec(limit=query.limit, offset=query.offset),
        )
        page = await self._runtime_query_gateway.search(query_plan)

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

    def _default_sorting(
        self,
        descriptor: RuntimeObjectDescriptor,
    ) -> tuple[SortSpec, ...]:
        sorting: list[SortSpec] = []
        created_at = descriptor.field_by_name("created_at")
        if created_at is not None and created_at.is_sortable:
            sorting.append(SortSpec(field=created_at.name, direction="desc"))

        pk_field = descriptor.field_by_name(descriptor.pk)
        if pk_field is not None and pk_field.is_sortable:
            seen_fields = {sort.field for sort in sorting}
            if pk_field.name not in seen_fields:
                sorting.append(SortSpec(field=pk_field.name, direction="desc"))

        if not sorting:
            raise RuntimeDataValidationError(
                "Runtime object descriptor must contain a sortable field for default "
                "search ordering."
            )
        return tuple(sorting)


__all__ = ["RuntimeObjectQueryService"]
