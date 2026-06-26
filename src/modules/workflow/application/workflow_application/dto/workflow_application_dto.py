from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class WorkflowApplicationDTO:
    """DTO for workflow application data."""

    id: UUID

    created_at: datetime
    updated_at: datetime

    created_by: UUID | None
    updated_by: UUID | None

    kind: str
    status: str

    title: str
    description: str | None

    icon: str
    icon_background: str

    active_workflow_definition_id: UUID | None


__all__ = ["WorkflowApplicationDTO"]
