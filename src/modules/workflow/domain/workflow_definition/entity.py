from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.modules.shared import EntityIdVO
from src.modules.shared.domain.value_object.entity_description import (
    EntityDescriptionVO,
)
from src.modules.shared.domain.value_object.entity_title import EntityTitleVO
from src.modules.workflow.domain.workflow_definition.value_object import (
    WorkflowDefinitionIdVO,
    WorkflowEnvironmentVO,
    WorkflowFeaturesVO,
    WorkflowGraphVO,
    WorkflowVersionVO,
)


@dataclass(slots=True)
class WorkflowDefinitionEntity:

    id: WorkflowDefinitionIdVO

    created_at: datetime
    updated_at: datetime

    created_by: EntityIdVO
    updated_by: EntityIdVO

    workflow_application_id: EntityIdVO

    version: WorkflowVersionVO
    graph: WorkflowGraphVO

    features: WorkflowFeaturesVO

    environment: WorkflowEnvironmentVO

    title: EntityTitleVO
    description: EntityDescriptionVO | None

    @classmethod
    def create_draft(
        cls,
        workflow_definition_id: WorkflowDefinitionIdVO,
        workflow_application_id: EntityIdVO,
        graph: WorkflowGraphVO,
        features: WorkflowFeaturesVO,
        environment: WorkflowEnvironmentVO,
        title: EntityTitleVO,
        description: EntityDescriptionVO | None,
        created_by: EntityIdVO,
        now: datetime,
    ) -> "WorkflowDefinitionEntity":
        return cls(
            id=workflow_definition_id,
            created_at=now,
            updated_at=now,
            created_by=created_by,
            updated_by=created_by,
            workflow_application_id=workflow_application_id,
            version=WorkflowVersionVO.first(),
            graph=graph,
            features=features,
            environment=environment,
            title=title,
            description=description,
        )


__all__ = ["WorkflowDefinitionEntity"]
