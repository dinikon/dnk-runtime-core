from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CreateWorkflowCommand:
    """Command for creating a default workflow application."""

    tenant_id: UUID | str
    created_by: UUID | str

    title: str
    description: str | None

    icon: str
    icon_background: str


__all__ = ["CreateWorkflowCommand"]
