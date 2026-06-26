from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from src.modules.shared import EntityIdVO
from src.modules.workflow.domain.error import WorkflowValidationError
from src.modules.workflow.domain.workflow.value_object import WorkflowGraphVO
from src.modules.workflow.domain.workflow_run.value_object import (
    ElapsedTimeVO,
    TotalStepsVO,
    TriggeredFromVO,
    WorkflowErrorVO,
    WorkflowPayloadVO,
    WorkflowRunStatusVO,
)


@dataclass(slots=True)
class WorkflowRunEntity:
    id: EntityIdVO

    created_at: datetime
    updated_at: datetime

    finished_at: datetime

    app_id: EntityIdVO
    workflow_id: EntityIdVO

    triggered_from: TriggeredFromVO

    graph: WorkflowGraphVO

    status: WorkflowRunStatusVO
    inputs: WorkflowPayloadVO
    outputs: WorkflowPayloadVO
    error: WorkflowErrorVO

    elapsed_time: ElapsedTimeVO
    total_steps: TotalStepsVO


__all__ = ["WorkflowRunEntity"]
