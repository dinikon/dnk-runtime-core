from typing import Protocol

from src.modules.shared import EntityIdVO
from src.modules.workflow.domain import WorkflowApplicationEntity


class WorkflowApplicationCommandRepositoryProtocol(Protocol):
    """Command repository port for workflow applications."""

    async def save(
        self,
        *,
        tenant_id: EntityIdVO,
        workflow: WorkflowApplicationEntity,
    ) -> WorkflowApplicationEntity:
        """Persists workflow application."""
        ...


__all__ = ["WorkflowApplicationCommandRepositoryProtocol"]
