from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Self

from src.modules.shared import EntityIdVO
from src.modules.shared.domain.value_object.entity_description import (
    EntityDescriptionVO,
)
from src.modules.shared.domain.value_object.entity_title import EntityTitleVO
from src.modules.workflow.domain.error import WorkflowValidationError
from src.modules.workflow.domain.workflow.value_object.workflow_id import WorkflowIdVO
from src.modules.workflow.domain.workflow_app.value_object import (
    WorkflowApplicationStatusVO,
    WorkflowIconBackgroundVO,
    WorkflowIconVO,
    WorkflowKindVO,
)
from src.modules.workflow.domain.workflow_app.value_object.workflow_application_id import (
    WorkflowApplicationIdVO,
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

    active_workflow_id: WorkflowIdVO | None

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
            active_workflow_id=None,
        )

    def rename(self, title: EntityTitleVO, clock: datetime) -> None:
        self.title = title
        self.updated_at = clock

    def set_active_workflow(self, workflow_id: WorkflowIdVO, clock: datetime) -> None:
        self.active_workflow_id = workflow_id
        self.updated_at = clock


__all__ = ["WorkflowApplicationEntity"]
