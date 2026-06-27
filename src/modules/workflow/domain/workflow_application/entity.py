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
)
from src.modules.workflow.domain.workflow_application.value_object import (
    WorkflowApplicationIdVO,
    WorkflowApplicationStatusVO,
    WorkflowIconBackgroundVO,
    WorkflowIconVO,
    WorkflowKindVO,
)


@dataclass(slots=True)
class WorkflowApplicationEntity:
    id: WorkflowApplicationIdVO

    created_at: datetime
    updated_at: datetime

    created_by: EntityIdVO | None
    updated_by: EntityIdVO | None

    kind: WorkflowKindVO
    status: WorkflowApplicationStatusVO

    title: EntityTitleVO
    description: EntityDescriptionVO | None

    icon: WorkflowIconVO
    icon_background: WorkflowIconBackgroundVO

    active_workflow_definition_id: WorkflowDefinitionIdVO | None

    @classmethod
    def create(
        cls,
        entity_id: WorkflowApplicationIdVO,
        kind: WorkflowKindVO,
        title: EntityTitleVO,
        description: EntityDescriptionVO | None,
        icon: WorkflowIconVO,
        icon_background: WorkflowIconBackgroundVO,
        created_by: EntityIdVO,
        now: datetime,
    ) -> "WorkflowApplicationEntity":
        return cls(
            id=entity_id,
            created_at=now,
            updated_at=now,
            created_by=created_by,
            updated_by=created_by,
            kind=kind,
            status=WorkflowApplicationStatusVO.NORMAL,
            title=title,
            description=description,
            icon=icon,
            icon_background=icon_background,
            active_workflow_definition_id=None,
        )

    def rename(self, title: EntityTitleVO, clock: datetime) -> None:
        self.title = title
        self.updated_at = clock

    def set_active_workflow_definition(
        self,
        workflow_definition_id: WorkflowDefinitionIdVO,
        clock: datetime,
    ) -> None:
        self.active_workflow_definition_id = workflow_definition_id
        self.updated_at = clock


__all__ = ["WorkflowApplicationEntity"]
