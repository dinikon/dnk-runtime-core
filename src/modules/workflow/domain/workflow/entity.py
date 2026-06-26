from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.modules.shared import EntityIdVO
from src.modules.shared.domain.value_object.entity_description import (
    EntityDescriptionVO,
)
from src.modules.shared.domain.value_object.entity_title import EntityTitleVO
from src.modules.workflow.domain.workflow.value_object import (
    WorkflowEnvironmentVO,
    WorkflowFeaturesVO,
    WorkflowGraphVO,
    WorkflowVersionVO,
)
from src.modules.workflow.domain.workflow.value_object.workflow_id import WorkflowIdVO


@dataclass(slots=True)
class WorkflowEntity:

    id: WorkflowIdVO

    created_at: datetime
    updated_at: datetime

    created_by: EntityIdVO
    updated_by: EntityIdVO

    app_id: EntityIdVO

    version: WorkflowVersionVO
    graph: WorkflowGraphVO

    features: WorkflowFeaturesVO

    environment: WorkflowEnvironmentVO

    title: EntityTitleVO
    description: EntityDescriptionVO | None

    @classmethod
    def create_draft(
        cls,
        workflow_id: WorkflowIdVO,
        app_id: EntityIdVO,
        graph: WorkflowGraphVO,
        features: WorkflowFeaturesVO,
        environment: WorkflowEnvironmentVO,
        title: EntityTitleVO,
        description: EntityDescriptionVO | None,
        created_by: EntityIdVO,
        now: datetime,
    ) -> "WorkflowEntity":
        return cls(
            id=workflow_id,
            created_at=now,
            updated_at=now,
            created_by=created_by,
            updated_by=created_by,
            app_id=app_id,
            version=WorkflowVersionVO.first(),
            graph=graph,
            features=features,
            environment=environment,
            title=title,
            description=description,
        )


__all__ = ["WorkflowEntity"]
