from typing import Protocol

from src.modules.shared import EntityIdVO
from src.modules.workflow.domain import (
    WorkflowApplicationEntity,
    WorkflowApplicationIdVO,
)


class WorkflowApplicationCommandRepositoryProtocol(Protocol):
    """Command repository port for workflow applications."""

    async def load(
        self,
        *,
        tenant_id: EntityIdVO,
        workflow_id: WorkflowApplicationIdVO,
    ) -> WorkflowApplicationEntity | None:
        """Loads workflow application by id."""
        ...

    async def save(
        self,
        *,
        tenant_id: EntityIdVO,
        workflow: WorkflowApplicationEntity,
    ) -> WorkflowApplicationEntity:
        """Persists workflow application."""
        ...


__all__ = ["WorkflowApplicationCommandRepositoryProtocol"]
