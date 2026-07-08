from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class UpdateWorkflowCommand:
    """Command for updating workflow application details."""

    tenant_id: UUID | str
    updated_by: UUID | str
    workflow_id: UUID | str

    title: str
    description: str | None

    icon: str
    icon_background: str


__all__ = ["UpdateWorkflowCommand"]
