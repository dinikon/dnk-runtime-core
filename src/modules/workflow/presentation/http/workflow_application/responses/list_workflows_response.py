from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class WorkflowListItemResponseSchema(BaseModel):
    """Pydantic-схема HTTP-ответа с workflow application list item."""

    id: UUID
    created_at: datetime
    kind: str
    status: str
    title: str
    description: str | None
    icon: str
    icon_background: str


class ListWorkflowsResponseSchema(BaseModel):
    """Pydantic-схема HTTP-ответа со списком workflow applications."""

    items: list[WorkflowListItemResponseSchema]
    next_cursor: str | None


__all__ = [
    "ListWorkflowsResponseSchema",
    "WorkflowListItemResponseSchema",
]
