from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any
from uuid import UUID

from src.modules.shared import EntityIdVO
from src.modules.shared.domain.value_object.entity_description import (
    EntityDescriptionVO,
)
from src.modules.shared.domain.value_object.entity_title import EntityTitleVO
from src.modules.workflow.application.workflow_application.dto import (
    WorkflowApplicationListItemDTO,
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


def row_to_workflow_application(row: Mapping[str, Any]) -> WorkflowApplicationEntity:
    active_definition_id = as_optional_uuid(row.get("active_workflow_definition_id"))
    created_by = as_optional_uuid(row.get("created_by"))
    updated_by = as_optional_uuid(row.get("updated_by"))
    description = as_optional_str(row.get("description"))
    return WorkflowApplicationEntity(
        id=WorkflowApplicationIdVO.from_value(as_uuid(row.get("id"))),
        created_at=as_datetime(row.get("created_at")),
        updated_at=as_datetime(row.get("updated_at")),
        created_by=None if created_by is None else EntityIdVO.from_value(created_by),
        updated_by=None if updated_by is None else EntityIdVO.from_value(updated_by),
        kind=WorkflowKindVO(as_str(row.get("kind"))),
        status=WorkflowApplicationStatusVO(as_str(row.get("status"))),
        title=EntityTitleVO(as_str(row.get("title"))),
        description=None if description is None else EntityDescriptionVO(description),
        icon=WorkflowIconVO(as_str(row.get("icon"))),
        icon_background=WorkflowIconBackgroundVO(as_str(row.get("icon_background"))),
        active_workflow_definition_id=(
            None
            if active_definition_id is None
            else WorkflowDefinitionIdVO.from_value(active_definition_id)
        ),
    )


def row_to_workflow_application_list_item(
    row: Mapping[str, Any],
) -> WorkflowApplicationListItemDTO:
    return WorkflowApplicationListItemDTO(
        id=as_uuid(row.get("id")),
        created_at=as_datetime(row.get("created_at")),
        kind=as_str(row.get("kind")),
        status=as_str(row.get("status")),
        title=as_str(row.get("title")),
        description=as_optional_str(row.get("description")),
        icon=as_str(row.get("icon")),
        icon_background=as_str(row.get("icon_background")),
    )


def row_to_workflow_definition(row: Mapping[str, Any]) -> WorkflowDefinitionEntity:
    title = as_optional_str(row.get("title"))
    description = as_optional_str(row.get("description"))
    return WorkflowDefinitionEntity(
        id=WorkflowDefinitionIdVO.from_value(as_uuid(row.get("id"))),
        created_at=as_datetime(row.get("created_at")),
        updated_at=as_datetime(row.get("updated_at")),
        created_by=EntityIdVO.from_value(as_uuid(row.get("created_by"))),
        updated_by=EntityIdVO.from_value(as_uuid(row.get("updated_by"))),
        workflow_application_id=WorkflowApplicationIdVO.from_value(
            as_uuid(row.get("workflow_application_id"))
        ),
        version=WorkflowVersionVO(as_str(row.get("version"))),
        graph=WorkflowGraphVO(as_dict(row.get("graph"))),
        features=WorkflowFeaturesVO(as_dict(row.get("features"))),
        environment=WorkflowEnvironmentVO(as_dict(row.get("environment"))),
        title=None if title is None else EntityTitleVO(title),
        description=None if description is None else EntityDescriptionVO(description),
    )


def as_uuid(value: Any) -> UUID:
    if isinstance(value, UUID):
        return value
    if isinstance(value, str):
        return UUID(value)
    raise TypeError("Runtime row must contain UUID value.")


def as_optional_uuid(value: Any) -> UUID | None:
    if value is None:
        return None
    return as_uuid(value)


def as_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    raise TypeError("Runtime row must contain datetime value.")


def as_str(value: Any) -> str:
    if isinstance(value, str):
        return value
    raise TypeError("Runtime row must contain string value.")


def as_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    return as_str(value)


def as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    raise TypeError("Runtime row must contain dict value.")


__all__ = [
    "as_datetime",
    "as_dict",
    "as_optional_str",
    "as_optional_uuid",
    "as_str",
    "as_uuid",
    "row_to_workflow_application",
    "row_to_workflow_application_list_item",
    "row_to_workflow_definition",
]
