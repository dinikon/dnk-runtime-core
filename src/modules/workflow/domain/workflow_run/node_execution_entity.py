from dataclasses import dataclass
from datetime import datetime

from src.modules.shared import EntityIdVO
from src.modules.shared.domain.value_object.entity_title import EntityTitleVO


@dataclass(frozen=True)
class NodeExecutionEntity:
    id: EntityIdVO
    created_at: datetime
    updated_at: datetime

    finished_at: datetime

    app_id: EntityIdVO
    workflow_id: EntityIdVO
    run_id: EntityIdVO

    index: str

    status: str

    node_id: str
    node_type: str
    node_title: EntityTitleVO

    inputs: dict
    process_data: dict
    outputs: dict

    error: str

    elapsed_time: float
