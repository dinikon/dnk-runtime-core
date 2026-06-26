from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.modules.shared import EntityIdVO
from src.modules.shared.domain.value_object.entity_title import EntityTitleVO
from src.modules.workflow.domain.workflow_run.value_object import (
    ElapsedTimeVO,
    NodeExecutionStatusVO,
    NodeIdVO,
    NodeIndexVO,
    NodeTypeVO,
    WorkflowErrorVO,
    WorkflowPayloadVO,
)


@dataclass(frozen=True)
class NodeExecutionEntity:
    id: EntityIdVO
    created_at: datetime
    updated_at: datetime

    finished_at: datetime

    app_id: EntityIdVO
    workflow_id: EntityIdVO
    run_id: EntityIdVO

    index: NodeIndexVO

    status: NodeExecutionStatusVO

    node_id: NodeIdVO
    node_type: NodeTypeVO
    node_title: EntityTitleVO

    inputs: WorkflowPayloadVO
    process_data: WorkflowPayloadVO
    outputs: WorkflowPayloadVO

    error: WorkflowErrorVO

    elapsed_time: ElapsedTimeVO


__all__ = ["NodeExecutionEntity"]
