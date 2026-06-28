from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class WorkflowApplicationListItemDTO:
    """DTO for workflow application list item."""

    id: UUID
    created_at: datetime
    kind: str
    status: str
    title: str
    description: str | None
    icon: str
    icon_background: str


@dataclass(frozen=True, slots=True)
class WorkflowApplicationListDTO:
    """DTO for workflow application list result."""

    items: tuple[WorkflowApplicationListItemDTO, ...]
    next_cursor: str | None


__all__ = [
    "WorkflowApplicationListDTO",
    "WorkflowApplicationListItemDTO",
]
