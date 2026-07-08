from __future__ import annotations

from src.modules.runtime_data.application.models import (
    FetchPlan,
    PageSpec,
    SortSpec,
    TypedFilterExpression,
    TypedFilterGroupSpec,
    TypedFilterSpec,
)
from src.modules.runtime_data.application.ports import (
    RuntimeCommandGateway,
    RuntimeQueryGateway,
)
from src.modules.schema_registry.runtime import (
    RuntimeFieldDescriptor,
    RuntimeObjectDescriptor,
    RuntimeObjectResolverProtocol,
)
from src.modules.shared import EntityIdVO
from src.modules.workflow.application.workflow_application.dto import (
    WorkflowApplicationListItemDTO,
)
from src.modules.workflow.application.workflow_application.pagination import (
    WorkflowApplicationCursor,
)
from src.modules.workflow.application.workflow_application.repository import (
    WorkflowApplicationCommandRepositoryProtocol,
    WorkflowApplicationQueryRepositoryProtocol,
)
from src.modules.workflow.domain import (
    WorkflowApplicationEntity,
    WorkflowApplicationIdVO,
    WorkflowApplicationNotFoundError,
)
from src.modules.workflow.infrastructure.runtime_mapping import (
    row_to_workflow_application,
    row_to_workflow_application_list_item,
)


class WorkflowApplicationRuntimeRepository(
    WorkflowApplicationCommandRepositoryProtocol,
    WorkflowApplicationQueryRepositoryProtocol,
):
    """Runtime repository for workflow applications."""

    _OBJECT_NAME = "workflow_application"
    _LIST_PROJECTIONS = (
        "id",
        "created_at",
        "kind",
        "status",
        "title",
        "description",
        "icon",
        "icon_background",
    )

    def __init__(
        self,
        *,
        runtime_object_resolver: RuntimeObjectResolverProtocol,
        runtime_command_gateway: RuntimeCommandGateway,
        runtime_query_gateway: RuntimeQueryGateway,
    ) -> None:
        self._runtime_object_resolver = runtime_object_resolver
        self._runtime_command_gateway = runtime_command_gateway
        self._runtime_query_gateway = runtime_query_gateway

    async def load(
        self,
        *,
        tenant_id: EntityIdVO,
        workflow_id: WorkflowApplicationIdVO,
    ) -> WorkflowApplicationEntity | None:
        """Loads workflow application by id."""
        descriptor = await self._resolve_descriptor(tenant_id)
        row = await self._runtime_query_gateway.get_by_id(
            descriptor=descriptor,
            object_id=workflow_id.uuid,
        )
        if row is None:
            return None
        return row_to_workflow_application(row)

    async def save(
        self,
        *,
        tenant_id: EntityIdVO,
        workflow: WorkflowApplicationEntity,
    ) -> WorkflowApplicationEntity:
        """Persists workflow application."""
        descriptor = await self._resolve_descriptor(tenant_id)
        existing = await self._runtime_query_gateway.get_by_id(
            descriptor=descriptor,
            object_id=workflow.id.uuid,
        )
        payload = {
            "created_by": (
                None if workflow.created_by is None else workflow.created_by.uuid
            ),
            "updated_by": (
                None if workflow.updated_by is None else workflow.updated_by.uuid
            ),
            "kind": workflow.kind.value,
            "status": workflow.status.value,
            "title": workflow.title.value,
            "description": (
                None if workflow.description is None else workflow.description.value
            ),
            "icon": workflow.icon.value,
            "icon_background": workflow.icon_background.value,
            "active_workflow_definition_id": (
                None
                if workflow.active_workflow_definition_id is None
                else workflow.active_workflow_definition_id.uuid
            ),
        }
        if existing is None:
            row = await self._runtime_command_gateway.insert(
                descriptor=descriptor,
                payload={
                    "id": workflow.id.uuid,
                    "created_at": workflow.created_at,
                    "updated_at": workflow.updated_at,
                    **payload,
                },
            )
        else:
            row = await self._runtime_command_gateway.update(
                descriptor=descriptor,
                object_id=workflow.id.uuid,
                patch=payload,
            )
            if row is None:
                raise WorkflowApplicationNotFoundError(str(workflow.id.uuid))
        return row_to_workflow_application(row)

    async def list(
        self,
        *,
        tenant_id: EntityIdVO,
        limit: int,
        cursor: WorkflowApplicationCursor | None,
    ) -> list[WorkflowApplicationListItemDTO]:
        """Returns workflow applications ordered by newest first."""
        descriptor = await self._resolve_descriptor(tenant_id)
        rows = await self._runtime_query_gateway.list(
            descriptor=descriptor,
            filters=self._cursor_filters(descriptor=descriptor, cursor=cursor),
            sorting=(SortSpec("created_at", "desc"), SortSpec("id", "desc")),
            page=PageSpec(limit=limit, offset=0),
            fetch_plan=FetchPlan(projections=self._LIST_PROJECTIONS),
        )
        return [row_to_workflow_application_list_item(row) for row in rows]

    async def _resolve_descriptor(
        self,
        tenant_id: EntityIdVO,
    ) -> RuntimeObjectDescriptor:
        return await self._runtime_object_resolver.resolve(
            tenant_id=tenant_id,
            object_name=self._OBJECT_NAME,
        )

    def _cursor_filters(
        self,
        *,
        descriptor: RuntimeObjectDescriptor,
        cursor: WorkflowApplicationCursor | None,
    ) -> tuple[TypedFilterExpression, ...]:
        if cursor is None:
            return ()
        created_at = self._required_field(descriptor, "created_at")
        workflow_id = self._required_field(descriptor, "id")
        created_at_before = TypedFilterSpec(
            field=created_at,
            op="lt",
            value=cursor.created_at,
        )
        same_created_at = TypedFilterGroupSpec(
            logic="and",
            items=(
                TypedFilterSpec(field=created_at, op="eq", value=cursor.created_at),
                TypedFilterSpec(field=workflow_id, op="lt", value=cursor.uuid),
            ),
        )
        return (
            TypedFilterGroupSpec(
                logic="or",
                items=(created_at_before, same_created_at),
            ),
        )

    @staticmethod
    def _required_field(
        descriptor: RuntimeObjectDescriptor,
        field_name: str,
    ) -> RuntimeFieldDescriptor:
        field = descriptor.field_by_name(field_name)
        if field is None:
            raise LookupError(f"Runtime field '{field_name}' not found.")
        return field


__all__ = ["WorkflowApplicationRuntimeRepository"]
