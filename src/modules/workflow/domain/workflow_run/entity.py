from dataclasses import dataclass
from datetime import datetime

from src.modules.shared import EntityIdVO


@dataclass(slots=True)
class WorkFlowRunEntity:
    id: EntityIdVO

    created_at: datetime
    updated_at: datetime

    finished_at: datetime

    app_id: EntityIdVO
    workflow_id: EntityIdVO

    triggered_from: str

    graph: str

    status: str
    inputs: dict
    outputs: dict
    error: str

    elapsed_time: str
    total_steps: str