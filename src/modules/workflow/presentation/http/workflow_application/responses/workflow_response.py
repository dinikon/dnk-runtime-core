from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class WorkflowResponseSchema(BaseModel):
    """Pydantic-схема HTTP-ответа с workflow application."""

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


__all__ = ["WorkflowResponseSchema"]
