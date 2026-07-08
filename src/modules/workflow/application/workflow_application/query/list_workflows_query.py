from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ListWorkflowsQuery:
    """Query application-слоя на список workflow applications tenant."""

    tenant_id: UUID | str
    limit: int = 50
    cursor: str | None = None


__all__ = ["ListWorkflowsQuery"]
