from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any, overload
from uuid import UUID

from src.modules.runtime_data.application.ports import (
    RuntimeCommandGateway,
    RuntimeQueryGateway,
)
from src.modules.schema_registry.runtime import (
    RuntimeObjectDescriptor,
    RuntimeObjectResolverProtocol,
)
from src.modules.shared import EntityIdVO
from src.modules.shared.domain.value_object.entity_description import (
    EntityDescriptionVO,
)
from src.modules.shared.domain.value_object.entity_title import EntityTitleVO
from src.modules.workflow.application.workflow_application.repository import (
    WorkflowApplicationCommandRepositoryProtocol,
)
from src.modules.workflow.application.workflow_definition.repository import (
    WorkflowDefinitionCommandRepositoryProtocol,
)
from src.modules.workflow.domain import (
    WorkflowApplicationEntity,
    WorkflowApplicationIdVO,
    WorkflowApplicationStatusVO,
    WorkflowDefinitionEntity,
    WorkflowDefinitionIdVO,
    WorkflowEnvironmentVO,
    WorkflowFeaturesVO,
    WorkflowGraphVO,
    WorkflowIconBackgroundVO,
    WorkflowIconVO,
    WorkflowKindVO,
    WorkflowVersionVO,
)


class WorkflowRuntimeRepository(
    WorkflowApplicationCommandRepositoryProtocol,
    WorkflowDefinitionCommandRepositoryProtocol,
):
    """Workflow repositories поверх runtime_data gateway."""

    _APPLICATION_OBJECT_NAME = "workflow_application"
    _DEFINITION_OBJECT_NAME = "workflow_definition"

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

    @overload
    async def save(
        self,
        *,
        tenant_id: EntityIdVO,
        workflow: WorkflowApplicationEntity,
        definition: None = None,
    ) -> WorkflowApplicationEntity: ...

    @overload
    async def save(
        self,
        *,
        tenant_id: EntityIdVO,
        workflow: None = None,
        definition: WorkflowDefinitionEntity,
    ) -> WorkflowDefinitionEntity: ...

    async def save(
        self,
        *,
        tenant_id: EntityIdVO,
        workflow: WorkflowApplicationEntity | None = None,
        definition: WorkflowDefinitionEntity | None = None,
    ) -> WorkflowApplicationEntity | WorkflowDefinitionEntity:
        """Сохраняет workflow application или workflow definition."""
        if workflow is not None and definition is None:
            return await self._save_workflow_application(
                tenant_id=tenant_id,
                workflow=workflow,
            )
        if definition is not None and workflow is None:
            return await self._save_workflow_definition(
                tenant_id=tenant_id,
                definition=definition,
            )
        raise ValueError("Pass exactly one of workflow or definition.")

    async def _save_workflow_application(
        self,
        *,
        tenant_id: EntityIdVO,
        workflow: WorkflowApplicationEntity,
    ) -> WorkflowApplicationEntity:
        descriptor = await self._resolve_descriptor(
            tenant_id,
            self._APPLICATION_OBJECT_NAME,
        )
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
                raise LookupError(str(workflow.id))
        return self._row_to_workflow_application(row)

    async def _save_workflow_definition(
        self,
        *,
        tenant_id: EntityIdVO,
        definition: WorkflowDefinitionEntity,
    ) -> WorkflowDefinitionEntity:
        descriptor = await self._resolve_descriptor(
            tenant_id,
            self._DEFINITION_OBJECT_NAME,
        )
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
        return self._row_to_workflow_definition(row)

    async def _resolve_descriptor(
        self,
        tenant_id: EntityIdVO,
        object_name: str,
    ) -> RuntimeObjectDescriptor:
        return await self._runtime_object_resolver.resolve(
            tenant_id=tenant_id,
            object_name=object_name,
        )

    @staticmethod
    def _row_to_workflow_application(
        row: Mapping[str, Any],
    ) -> WorkflowApplicationEntity:
        active_definition_id = WorkflowRuntimeRepository._as_optional_uuid(
            row.get("active_workflow_definition_id")
        )
        created_by = WorkflowRuntimeRepository._as_optional_uuid(row.get("created_by"))
        updated_by = WorkflowRuntimeRepository._as_optional_uuid(row.get("updated_by"))
        description = WorkflowRuntimeRepository._as_optional_str(row.get("description"))
        return WorkflowApplicationEntity(
            id=WorkflowApplicationIdVO.from_value(
                WorkflowRuntimeRepository._as_uuid(row.get("id"))
            ),
            created_at=WorkflowRuntimeRepository._as_datetime(row.get("created_at")),
            updated_at=WorkflowRuntimeRepository._as_datetime(row.get("updated_at")),
            created_by=(
                None if created_by is None else EntityIdVO.from_value(created_by)
            ),
            updated_by=(
                None if updated_by is None else EntityIdVO.from_value(updated_by)
            ),
            kind=WorkflowKindVO(WorkflowRuntimeRepository._as_str(row.get("kind"))),
            status=WorkflowApplicationStatusVO(
                WorkflowRuntimeRepository._as_str(row.get("status"))
            ),
            title=EntityTitleVO(WorkflowRuntimeRepository._as_str(row.get("title"))),
            description=(
                None if description is None else EntityDescriptionVO(description)
            ),
            icon=WorkflowIconVO(WorkflowRuntimeRepository._as_str(row.get("icon"))),
            icon_background=WorkflowIconBackgroundVO(
                WorkflowRuntimeRepository._as_str(row.get("icon_background"))
            ),
            active_workflow_definition_id=(
                None
                if active_definition_id is None
                else WorkflowDefinitionIdVO.from_value(active_definition_id)
            ),
        )

    @staticmethod
    def _row_to_workflow_definition(row: Mapping[str, Any]) -> WorkflowDefinitionEntity:
        title = WorkflowRuntimeRepository._as_optional_str(row.get("title"))
        description = WorkflowRuntimeRepository._as_optional_str(row.get("description"))
        return WorkflowDefinitionEntity(
            id=WorkflowDefinitionIdVO.from_value(
                WorkflowRuntimeRepository._as_uuid(row.get("id"))
            ),
            created_at=WorkflowRuntimeRepository._as_datetime(row.get("created_at")),
            updated_at=WorkflowRuntimeRepository._as_datetime(row.get("updated_at")),
            created_by=EntityIdVO.from_value(
                WorkflowRuntimeRepository._as_uuid(row.get("created_by"))
            ),
            updated_by=EntityIdVO.from_value(
                WorkflowRuntimeRepository._as_uuid(row.get("updated_by"))
            ),
            workflow_application_id=WorkflowApplicationIdVO.from_value(
                WorkflowRuntimeRepository._as_uuid(row.get("workflow_application_id"))
            ),
            version=WorkflowVersionVO(
                WorkflowRuntimeRepository._as_str(row.get("version"))
            ),
            graph=WorkflowGraphVO(WorkflowRuntimeRepository._as_dict(row.get("graph"))),
            features=WorkflowFeaturesVO(
                WorkflowRuntimeRepository._as_dict(row.get("features"))
            ),
            environment=WorkflowEnvironmentVO(
                WorkflowRuntimeRepository._as_dict(row.get("environment"))
            ),
            title=None if title is None else EntityTitleVO(title),
            description=(
                None if description is None else EntityDescriptionVO(description)
            ),
        )

    @staticmethod
    def _as_uuid(value: Any) -> UUID:
        if isinstance(value, UUID):
            return value
        if isinstance(value, str):
            return UUID(value)
        raise TypeError("Runtime row must contain UUID value.")

    @staticmethod
    def _as_optional_uuid(value: Any) -> UUID | None:
        if value is None:
            return None
        return WorkflowRuntimeRepository._as_uuid(value)

    @staticmethod
    def _as_datetime(value: Any) -> datetime:
        if isinstance(value, datetime):
            return value
        raise TypeError("Runtime row must contain datetime value.")

    @staticmethod
    def _as_str(value: Any) -> str:
        if isinstance(value, str):
            return value
        raise TypeError("Runtime row must contain string value.")

    @staticmethod
    def _as_optional_str(value: Any) -> str | None:
        if value is None:
            return None
        return WorkflowRuntimeRepository._as_str(value)

    @staticmethod
    def _as_dict(value: Any) -> dict[str, Any]:
        if isinstance(value, dict):
            return dict(value)
        raise TypeError("Runtime row must contain dict value.")


__all__ = ["WorkflowRuntimeRepository"]
