from __future__ import annotations

from src.modules.runtime_data.application.ports import (
    RuntimeCommandGateway,
    RuntimeQueryGateway,
)
from src.modules.schema_registry.runtime import (
    RuntimeObjectDescriptor,
    RuntimeObjectResolverProtocol,
)
from src.modules.shared import EntityIdVO
from src.modules.workflow.application.workflow_definition.repository import (
    WorkflowDefinitionCommandRepositoryProtocol,
)
from src.modules.workflow.domain import WorkflowDefinitionEntity
from src.modules.workflow.infrastructure.runtime_mapping import (
    row_to_workflow_definition,
)


class WorkflowDefinitionRuntimeRepository(WorkflowDefinitionCommandRepositoryProtocol):
    """Runtime repository for workflow definitions."""

    _OBJECT_NAME = "workflow_definition"

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

    async def save(
        self,
        *,
        tenant_id: EntityIdVO,
        definition: WorkflowDefinitionEntity,
    ) -> WorkflowDefinitionEntity:
        """Persists workflow definition."""
        descriptor = await self._resolve_descriptor(tenant_id)
        existing = await self._runtime_query_gateway.get_by_id(
            descriptor=descriptor,
            object_id=definition.id.uuid,
        )
        payload = {
            "created_by": definition.created_by.uuid,
            "updated_by": definition.updated_by.uuid,
            "workflow_application_id": definition.workflow_application_id.uuid,
            "version": definition.version.value,
            "graph": definition.graph.value,
            "features": definition.features.value,
            "environment": definition.environment.value,
            "title": None if definition.title is None else definition.title.value,
            "description": (
                None if definition.description is None else definition.description.value
            ),
        }
        if existing is None:
            row = await self._runtime_command_gateway.insert(
                descriptor=descriptor,
                payload={
                    "id": definition.id.uuid,
                    "created_at": definition.created_at,
                    "updated_at": definition.updated_at,
                    **payload,
                },
            )
        else:
            row = await self._runtime_command_gateway.update(
                descriptor=descriptor,
                object_id=definition.id.uuid,
                patch=payload,
            )
            if row is None:
                raise LookupError(str(definition.id))
        return row_to_workflow_definition(row)

    async def _resolve_descriptor(
        self,
        tenant_id: EntityIdVO,
    ) -> RuntimeObjectDescriptor:
        return await self._runtime_object_resolver.resolve(
            tenant_id=tenant_id,
            object_name=self._OBJECT_NAME,
        )


__all__ = ["WorkflowDefinitionRuntimeRepository"]
